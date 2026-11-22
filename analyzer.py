from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisResult:
    overall: int
    categories: dict[str, int]
    pros: list[str]
    cons: list[str]
    mood: str
    keywords: list[str]


CATEGORY_KEYWORDS = {
    "Транспорт": {
        "positive": ["метро", "автобус", "останов", "транспорт", "lrt", "выезд", "добираюсь быстро", "доезжаю"],
        "negative": ["пробк", "далеко", "трудно добираться"],
    },
    "Тишина": {
        "positive": ["тихо", "тишин", "спокойн", "шум не слышно", "шумоизоляция", "не слышно"],
        "negative": ["шум дороги и", "стройк", "громк", "шумоизоляция слабая"],
    },
    "Двор": {
        "positive": ["двор", "детск", "площадк", "озелен", "парковка подземная", "закрыт", "воркаут"],
        "negative": ["парковки не хватает", "грязн", "тесн", "машин много", "зелени почти нет", "маленький"],
    },
    "Безопасность": {
        "positive": ["охрана", "консьерж", "домофон", "камер", "безопас"],
        "negative": ["лифт не работает", "тёмный", "темно", "небезопас", "посторонние", "охраны фактически нет"],
    },
    "Сервис": {
        "positive": ["управляющая компания быстро", "уборк", "чисто", "сервис", "быстро решают", "кск работает хорошо", "заявок удобное"],
        "negative": ["управляющая плохая", "не убирают", "течет", "ремонт делают медленно", "висят"],
    },
}

SIGNAL_LABELS = {
    "Транспорт": ("удобный транспорт", "пробки и дорога"),
    "Тишина": ("тихо и спокойно", "шум"),
    "Двор": ("уютный двор", "тесный двор/парковка"),
    "Безопасность": ("охрана и камеры", "безопасность подъезда"),
    "Сервис": ("хорошая управляющая", "работа УК"),
}


def _hits(text: str, phrases: list[str]) -> int:
    return sum(1 for phrase in phrases if phrase in text)


def analyze_reviews(reviews: list[dict]) -> AnalysisResult:
    if not reviews:
        return AnalysisResult(0, {key: 0 for key in CATEGORY_KEYWORDS}, [], [], "Нет данных", [])

    ratings = [max(0, min(5, int(item.get("rating", 0) or 0))) for item in reviews]
    avg = sum(ratings) / max(len(ratings), 1)
    baseline = 20 + (avg - 1) / 4 * 72  # 1★ → 20, 5★ → 96

    categories: dict[str, int] = {}
    pos_total: dict[str, int] = {}
    neg_total: dict[str, int] = {}
    for category, words in CATEGORY_KEYWORDS.items():
        samples: list[float] = []
        pos_total[category] = neg_total[category] = 0
        for item, rating in zip(reviews, ratings):
            text = str(item.get("text", "")).lower()
            pos = _hits(text, words["positive"])
            neg = _hits(text, words["negative"])
            if not pos and not neg:
                continue
            pos_total[category] += pos
            neg_total[category] += neg
            local = 20 + (rating - 1) / 4 * 72 if rating else baseline
            samples.append(local + 4 * min(pos, 2) - 13 * min(neg, 2))
        if samples:
            score = (sum(samples) + baseline) / (len(samples) + 1)
        else:
            score = baseline * 0.92
        categories[category] = int(max(30, min(98, round(score))))

    overall = round(sum(categories.values()) / len(categories))
    total_pos = sum(pos_total.values())
    total_neg = sum(neg_total.values())
    if avg >= 4 and total_pos >= total_neg * 1.5:
        mood = "Преимущественно положительный фон"
    elif avg < 3 or total_neg > total_pos:
        mood = "Есть повторяющиеся проблемы"
    else:
        mood = "Смешанные впечатления"

    ranked = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
    pros = [SIGNAL_LABELS[c][0] for c, v in ranked if v >= 70 and pos_total[c] > 0][:3]
    cons = [SIGNAL_LABELS[c][1] for c, v in reversed(ranked) if neg_total[c] > 0 and v < 72][:3]
    all_text = " ".join(str(item.get("text", "")) for item in reviews).lower()
    keywords = [word for word, _ in Counter(re.findall(r"[а-яёәіңғүұқөһ]{5,}", all_text)).most_common(8)]
    return AnalysisResult(overall, categories, pros, cons, mood, keywords)
