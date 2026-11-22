"""Мозг ИИ-помощника Доми.

1) Локальный движок: отвечает по данным SQLite (рейтинги, отзывы, цены, профиль комфорта)
   без интернета и ключей.
2) Если в .env задан ANTHROPIC_API_KEY и установлен пакет `anthropic`, ответы
   формирует Claude на основе тех же данных (контекст передаётся в system prompt).
"""

from __future__ import annotations

import os
import re

from config import load_local_env

CATS = ["Транспорт", "Тишина", "Двор", "Безопасность", "Сервис"]

# Как 12 критериев профиля комфорта соотносятся с 5 категориями анализа отзывов.
CRITERIA_MAP = {
    "Тишина": "Тишина", "Транспорт": "Транспорт", "Зелень и воздух": "Двор", "Безопасность": "Безопасность",
    "Парковка": "Двор", "Двор и условия для детей": "Двор", "Школы и детские сады": "Двор",
    "Магазины": "Транспорт", "Дом и инженерные коммуникации": "Сервис", "Управление домом": "Сервис",
    "Доступная среда": "Двор", "Интернет и связь": "Сервис",
}

CAT_LABEL = {
    "ru": {"Транспорт": "транспорт", "Тишина": "тишина", "Двор": "двор", "Безопасность": "безопасность", "Сервис": "сервис УК"},
    "kk": {"Транспорт": "көлік", "Тишина": "тыныштық", "Двор": "аула", "Безопасность": "қауіпсіздік", "Сервис": "қызмет"},
    "en": {"Транспорт": "transport", "Тишина": "quietness", "Двор": "courtyard", "Безопасность": "safety", "Сервис": "management"},
}

TXT = {
    "ru": {
        "hello": "Привет! Я Доми — ваш ИИ-помощник по жилью в Астане 🏡\nЯ прочитал {reviews} отзывов о {count} ЖК и могу подобрать дом под ваш образ жизни.",
        "help": "Вот что я умею:\n• подобрать ЖК под ваш профиль комфорта\n• найти самый тихий, безопасный или удобный по транспорту\n• рассказать о конкретном ЖК и его минусах\n• сравнить два-три комплекса\n• отфильтровать по бюджету — например, «до 40 млн»",
        "top": "По вашему профилю комфорта лучше всего подходят:",
        "top_default": "Лидеры по индексу комфорта прямо сейчас:",
        "best_cat": "Лучшие ЖК по критерию «{cat}»:",
        "budget": "Варианты до {budget} — отсортировал по комфорту:",
        "budget_none": "В пределах {budget} ничего не нашёл. Самый доступный вариант — {name} ({price}).",
        "district": "ЖК в районе «{district}»:",
        "summary": "{name} — {klass}, {district}.\nИндекс комфорта: {score}/100 · {mood}.\nСильные стороны: {pros}.\nНа что обратить внимание: {cons}.",
        "quote": "Из отзывов: «{text}» — {author}, ★{rating}",
        "compare": "Сравнение {names}:",
        "compare_win": "По сумме критериев выигрывает {name} ✨",
        "unknown": "Пока не уверен, что понял вопрос 🤔 Попробуйте спросить по-другому или выберите подсказку ниже.",
        "nothing": "нет явных минусов в отзывах",
        "match": "совпадение {m}%",
        "demo_note": "Отзывы в базе — демонстрационные (источник «Демо-данные»).",
        "chips": ["Подбери ЖК для семьи", "Самый тихий ЖК", "Что до 35 млн?", "Сравни BI City Seoul и Highvill Astana", "Что умеешь?"],
        "price": "покупка", "rent": "аренда",
    },
    "kk": {
        "hello": "Сәлем! Мен Домимін — Астанадағы тұрғын үй бойынша ИИ-көмекшіңіз 🏡\nМен {count} ТҮК туралы {reviews} пікірді оқыдым.",
        "help": "Мен не істей аламын:\n• жайлылық профиліңізге сай ТҮК таңдау\n• ең тыныш, қауіпсіз немесе көлікке ыңғайлысын табу\n• нақты ТҮК туралы айту\n• екі-үш кешенді салыстыру\n• бюджет бойынша сүзу — мысалы, «40 млн-ға дейін»",
        "top": "Сіздің профиліңізге ең сәйкесі:",
        "top_default": "Жайлылық индексі бойынша көшбасшылар:",
        "best_cat": "«{cat}» бойынша үздік ТҮК:",
        "budget": "{budget} дейінгі нұсқалар:",
        "budget_none": "{budget} шегінде ештеңе таппадым. Ең қолжетімдісі — {name} ({price}).",
        "district": "«{district}» ауданындағы ТҮК:",
        "summary": "{name} — {klass}, {district}.\nЖайлылық индексі: {score}/100 · {mood}.\nКүшті жақтары: {pros}.\nНазар аударыңыз: {cons}.",
        "quote": "Пікірлерден: «{text}» — {author}, ★{rating}",
        "compare": "Салыстыру: {names}",
        "compare_win": "Жалпы критерийлер бойынша {name} озады ✨",
        "unknown": "Сұрақты түсінбедім 🤔 Төмендегі кеңестердің бірін таңдаңыз.",
        "nothing": "пікірлерде айқын кемшілік жоқ",
        "match": "сәйкестік {m}%",
        "demo_note": "Базадағы пікірлер — демонстрациялық («Демо-данные»).",
        "chips": ["Отбасыға ТҮК таңда", "Ең тыныш ТҮК", "35 млн-ға дейін не бар?", "BI City Seoul пен Highvill Astana салыстыр", "Не істей аласың?"],
        "price": "сатып алу", "rent": "жалға алу",
    },
    "en": {
        "hello": "Hi! I'm Domi — your AI housing assistant for Astana 🏡\nI've read {reviews} reviews about {count} residential complexes.",
        "help": "Here's what I can do:\n• match complexes to your comfort profile\n• find the quietest, safest or best-connected one\n• summarise a specific complex and its downsides\n• compare two or three complexes\n• filter by budget — e.g. “under 40 mln”",
        "top": "Best matches for your comfort profile:",
        "top_default": "Current comfort index leaders:",
        "best_cat": "Top complexes for {cat}:",
        "budget": "Options under {budget}, sorted by comfort:",
        "budget_none": "Nothing within {budget}. The most affordable is {name} ({price}).",
        "district": "Complexes in {district}:",
        "summary": "{name} — {klass}, {district}.\nComfort index: {score}/100 · {mood}.\nStrengths: {pros}.\nWatch out for: {cons}.",
        "quote": "From reviews: “{text}” — {author}, ★{rating}",
        "compare": "Comparing {names}:",
        "compare_win": "Overall winner: {name} ✨",
        "unknown": "I'm not sure I got that 🤔 Try rephrasing or pick a suggestion below.",
        "nothing": "no clear downsides in reviews",
        "match": "{m}% match",
        "demo_note": "Reviews in the database are demo data (source “Демо-данные”).",
        "chips": ["Pick a complex for a family", "The quietest complex", "What's under 35 mln?", "Compare BI City Seoul and Highvill Astana", "What can you do?"],
        "price": "purchase", "rent": "rent",
    },
}

DISTRICTS = {"есил": "Есильский район", "esil": "Есильский район", "алматин": "Алматинский район", "almaty": "Алматинский район",
             "сарыарк": "Сарыаркинский район", "saryarka": "Сарыаркинский район", "байконур": "Байконурский район",
             "baikonur": "Байконурский район", "нура": "район Нура", "nura": "район Нура"}

CAT_WORDS = {
    "Тишина": ["тих", "тиш", "шум", "спокой", "quiet", "noise", "тыныш"],
    "Транспорт": ["транспорт", "метро", "lrt", "добира", "дорог", "центр", "transport", "commute", "көлік"],
    "Безопасность": ["безопас", "охран", "камер", "safe", "secur", "қауіпсіз"],
    "Двор": ["двор", "площадк", "парков", "зелен", "court", "yard", "park", "аула"],
    "Сервис": ["сервис", "ук", "управля", "кск", "чист", "service", "manage", "қызмет"],
}


def personal_score(db, dev_id: int, prefs: dict[str, int]) -> int:
    analysis = db.analysis_for(dev_id)
    if not analysis.overall:
        return 0
    weights = {c: 0.0 for c in CATS}
    for criterion, importance in (prefs or {}).items():
        cat = CRITERIA_MAP.get(criterion)
        if cat and importance:
            weights[cat] += importance
    total = sum(weights.values())
    if not total:
        return analysis.overall
    return round(sum(analysis.categories.get(c, 0) * w for c, w in weights.items()) / total)


def _price_text(item: dict, lang: str) -> str:
    from ui_kit import money
    return money(item.get("purchase_price") or item.get("price_from"))


class LocalEngine:
    def __init__(self, db):
        self.db = db

    def _ranked(self, prefs, key=None, items=None):
        items = items if items is not None else self.db.developments()
        scored = []
        for it in items:
            a = self.db.analysis_for(it["id"])
            if not a.overall:
                continue
            value = a.categories.get(key, 0) if key else personal_score(self.db, it["id"], prefs)
            scored.append((value, it, a))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _find_names(self, q: str) -> list[dict]:
        found = []
        items = sorted(self.db.developments(), key=lambda x: -len(x["name"]))
        rest = q
        for it in items:
            n = it["name"].lower()
            if n in rest:
                found.append(it)
                rest = rest.replace(n, " ")
        aliases = {"сеул": "BI City Seoul", "токио": "BI City Tokyo", "хайвил": "Highvill Astana", "гранд опер": "Grand Opera", "нова сити": "Nova City"}
        for alias, name in aliases.items():
            if alias in q and all(f["name"] != name for f in found):
                it = next((x for x in items if x["name"] == name), None)
                if it:
                    found.append(it)
        found.sort(key=lambda it: q.find(it["name"].lower()) if it["name"].lower() in q else len(q))
        return found

    def answer(self, question: str, prefs: dict, lang: str = "ru") -> dict:
        L = TXT.get(lang, TXT["ru"])
        labels = CAT_LABEL.get(lang, CAT_LABEL["ru"])
        q = " " + question.lower().strip() + " "
        devs = self.db.developments()
        out = {"text": "", "cards": [], "chips": L["chips"][:4], "mood": "talk"}

        if not q.strip() or re.search(r"\b(привет|здравствуй|салем|сәлем|hello|hi|hey)\b", q):
            out["text"] = L["hello"].format(reviews=self.db.total_reviews(), count=len(devs)) + "\n\n" + L["help"]
            out["mood"] = "happy"
            return out
        if any(w in q for w in ["умеешь", "помощь", "help", "can you", "не істей", "что ты"]):
            out["text"] = L["help"]
            return out

        names = self._find_names(q)
        if len(names) >= 2 or (names and any(w in q for w in ["сравн", " vs ", "compare", "салыстыр", " или "])):
            if len(names) >= 2:
                return self._compare(names[:3], L, labels, out)
        if len(names) == 1:
            return self._summary(names[0], L, labels, out, lang)

        budget = self._budget(q)
        if budget:
            rent = any(w in q for w in ["аренд", "rent", "жалға", "в месяц"])
            field = "rental_price" if rent else "purchase_price"
            items = [d for d in devs if 0 < int(d.get(field) or 0) <= budget]
            from ui_kit import money
            if not items:
                cheapest = min((d for d in devs if d.get(field)), key=lambda d: d[field], default=None)
                out["text"] = L["budget_none"].format(budget=money(budget), name=cheapest["name"] if cheapest else "—", price=money(cheapest[field]) if cheapest else "—")
                if cheapest:
                    out["cards"] = [cheapest["id"]]
                return out
            ranked = self._ranked(prefs, items=items)[:4]
            out["text"] = L["budget"].format(budget=money(budget)) + "\n" + "\n".join(
                f"{i + 1}. {it['name']} — {money(it[field])} · {a.overall}/100" for i, (_, it, a) in enumerate(ranked))
            out["cards"] = [it["id"] for _, it, _ in ranked]
            return out

        for stem, district in DISTRICTS.items():
            if stem in q:
                items = [d for d in devs if d.get("district") == district]
                ranked = self._ranked(prefs, items=items)[:5]
                out["text"] = L["district"].format(district=district) + "\n" + "\n".join(
                    f"• {it['name']} — {a.overall}/100" for _, it, a in ranked)
                out["cards"] = [it["id"] for _, it, _ in ranked[:3]]
                return out

        family = any(w in q for w in ["сем", "дет", "ребён", "ребен", "family", "kids", "отбасы", "бала"])
        cat = next((c for c, words in CAT_WORDS.items() if any(w in q for w in words)), None)
        if family:
            prefs = {"Двор и условия для детей": 5, "Безопасность": 5, "Школы и детские сады": 4, "Тишина": 3}
            cat = None
        if cat and not family:
            ranked = self._ranked(prefs, key=cat)[:3]
            out["text"] = L["best_cat"].format(cat=labels[cat]) + "\n" + "\n".join(
                f"{i + 1}. {it['name']} — {v}/100 ({it.get('district', '')})" for i, (v, it, _) in enumerate(ranked))
            best = ranked[0] if ranked else None
            if best:
                quote = self._quote(best[1]["id"], cat)
                if quote:
                    out["text"] += "\n\n" + L["quote"].format(**quote)
            out["cards"] = [it["id"] for _, it, _ in ranked]
            return out

        if family or any(w in q for w in ["лучш", "топ", "посовет", "рекоменд", "подбер", "подойд", "best", "recommend", "top", "match", "таңда", "үздік"]):
            has_prefs = family or any((prefs or {}).values())
            ranked = self._ranked(prefs)[:3]
            out["text"] = (L["top"] if has_prefs else L["top_default"]) + "\n" + "\n".join(
                f"{i + 1}. {it['name']} — {L['match'].format(m=v)} · {', '.join(a.pros[:2]) or '—'}" for i, (v, it, a) in enumerate(ranked))
            out["cards"] = [it["id"] for _, it, _ in ranked]
            out["mood"] = "happy"
            return out

        out["text"] = L["unknown"]
        out["mood"] = "think"
        out["chips"] = L["chips"]
        return out

    @staticmethod
    def _budget(q: str) -> int:
        m = re.search(r"(\d+[.,]?\d*)\s*(млн|mln|million|m\b|миллион)", q)
        if m:
            return int(float(m.group(1).replace(",", ".")) * 1_000_000)
        m = re.search(r"(\d+)\s*(тыс|k\b|мың)", q)
        if m:
            return int(m.group(1)) * 1000
        m = re.search(r"\b(\d{6,10})\b", q.replace(" ", ""))
        if m and any(w in q for w in ["до", "under", "дейін", "бюджет", "budget"]):
            return int(m.group(1))
        if any(w in q for w in ["дешев", "недорог", "бюджет", "cheap", "affordable", "арзан"]):
            return 30_000_000
        return 0

    def _quote(self, dev_id: int, cat: str | None = None):
        reviews = self.db.reviews_for(dev_id)
        words = CAT_WORDS.get(cat, []) if cat else []
        best = None
        for r in sorted(reviews, key=lambda r: -int(r["rating"])):
            if not words or any(w in r["text"].lower() for w in words):
                best = r
                break
        if not best and reviews:
            best = reviews[0]
        if not best:
            return None
        text = best["text"]
        if len(text) > 140:
            text = text[:137].rsplit(" ", 1)[0] + "…"
        return {"text": text, "author": best["author"], "rating": best["rating"]}

    def _summary(self, item, L, labels, out, lang):
        a = self.db.analysis_for(item["id"])
        out["text"] = L["summary"].format(
            name=item["name"], klass=item.get("housing_class") or "ЖК", district=item.get("district") or "Астана",
            score=a.overall or "—", mood=a.mood, pros=", ".join(a.pros) or "—", cons=", ".join(a.cons) or L["nothing"])
        quote = self._quote(item["id"])
        if quote:
            out["text"] += "\n\n" + L["quote"].format(**quote)
        out["cards"] = [item["id"]]
        return out

    def _compare(self, items, L, labels, out):
        lines = [L["compare"].format(names=" · ".join(i["name"] for i in items))]
        results = [(i, self.db.analysis_for(i["id"])) for i in items]
        for cat in CATS:
            vals = [a.categories.get(cat, 0) for _, a in results]
            best = max(vals)
            row = "   ".join(f"{v}{' 🏆' if v == best and vals.count(best) == 1 else ''}" for v in vals)
            lines.append(f"• {labels[cat]}: {row}")
        winner = max(results, key=lambda x: x[1].overall)[0]
        lines.append("\n" + L["compare_win"].format(name=winner["name"]))
        out["text"] = "\n".join(lines)
        out["cards"] = [i["id"] for i in items]
        return out


class ClaudeEngine:
    """Опциональный режим: ответы формирует Claude по данным HouseCheck AI."""

    MODEL = "claude-opus-5-5"

    def __init__(self):
        load_local_env()
        self.key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.client = None
        if self.key:
            try:
                import anthropic
                self._anthropic = anthropic
                self.client = anthropic.Anthropic(api_key=self.key)
            except Exception:
                self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    @staticmethod
    def build_context(db, prefs) -> str:
        lines = []
        for d in db.developments():
            a = db.analysis_for(d["id"])
            if not a.overall:
                continue
            quotes = [f"«{r['text'][:160]}» ({r['rating']}★, источник: {r['source']})" for r in db.reviews_for(d["id"])[:3]]
            lines.append(
                f"- {d['name']} | {d.get('district', '')} | класс {d.get('housing_class') or '—'} | покупка от {d.get('purchase_price') or 0} ₸ | "
                f"аренда {d.get('rental_price') or 0} ₸/мес | индекс {a.overall} | " + ", ".join(f"{k} {v}" for k, v in a.categories.items())
                + f" | плюсы: {', '.join(a.pros) or '—'} | минусы: {', '.join(a.cons) or '—'}\n  " + "\n  ".join(quotes))
        pref_text = ", ".join(f"{k}: {v}/5" for k, v in (prefs or {}).items() if v) or "не задан"
        return "Профиль комфорта пользователя: " + pref_text + "\n\nДанные ЖК Астаны:\n" + "\n".join(lines)

    def ask(self, history: list[dict], context: str, lang: str) -> str:
        language = {"ru": "русском", "kk": "казахском", "en": "английском"}.get(lang, "русском")
        system = (
            "Ты — Доми, дружелюбный ИИ-помощник приложения HouseCheck AI для выбора жилых комплексов в Астане. "
            "Отвечай только на основе данных ниже; если данных нет — честно скажи об этом и не выдумывай факты. "
            "Называй ЖК точно так же, как в данных. Пиши кратко (до 120 слов), живо, с конкретными цифрами индекса. "
            "Если опираешься на отзывы с источником «Демо-данные», можешь упомянуть, что это демонстрационные данные. "
            f"Отвечай на {language} языке.\n\n" + context
        )
        response = self.client.beta.messages.create(
            model=self.MODEL,
            max_tokens=2000,
            system=system,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=history[-12:],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude отказался отвечать на этот запрос")
        return "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
