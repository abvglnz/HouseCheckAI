"""Демо-набор для презентации HouseCheck AI.

ВНИМАНИЕ: отзывы ниже сгенерированы для демонстрации продукта и НЕ являются
реальными отзывами жителей. Они сохраняются с источником DEMO_SOURCE, чтобы их
можно было отличить от Google Maps / импорта и удалить (HOUSECHECK_SEED_DEMO=0).
Адреса, цены и координаты — ориентировочные.
"""

from __future__ import annotations

import random
import urllib.parse

DEMO_SOURCE = "Демо-данные"

# name, district, address, lat, lng, class, year, floors, units, rent, purchase, profile
# profile: качество по категориям 0..1 — Транспорт, Тишина, Двор, Безопасность, Сервис
COMPLEXES = [
    ("BI City", "Есильский район", "пр. Кабанбай батыра, 58", 51.1052, 71.4056, "Комфорт", 2021, 12, 1450, 260000, 32000000, (0.75, 0.55, 0.7, 0.7, 0.6)),
    ("BI City Seoul", "Есильский район", "ул. Сыганак, 32", 51.0986, 71.4182, "Комфорт+", 2022, 16, 980, 300000, 38500000, (0.7, 0.75, 0.85, 0.8, 0.75)),
    ("BI City Tokyo", "Есильский район", "ул. Хусейн бен Талал, 25", 51.1021, 71.3962, "Комфорт", 2023, 14, 870, 280000, 35000000, (0.6, 0.8, 0.75, 0.75, 0.7)),
    ("Capital Park", "Есильский район", "пр. Мангилик Ел, 19", 51.1236, 71.4321, "Бизнес", 2019, 18, 640, 420000, 56000000, (0.85, 0.6, 0.65, 0.9, 0.85)),
    ("Grand Opera", "Есильский район", "ул. Кунаева, 14", 51.1362, 71.4143, "Премиум", 2018, 22, 410, 550000, 82000000, (0.9, 0.5, 0.6, 0.95, 0.9)),
    ("Expo Boulevard", "Есильский район", "пр. Туран, 55", 51.0893, 71.4141, "Бизнес", 2020, 20, 720, 390000, 51000000, (0.8, 0.65, 0.8, 0.85, 0.7)),
    ("Promenade Expo", "Есильский район", "ул. Е-10, 17", 51.0842, 71.4254, "Комфорт+", 2021, 15, 560, 330000, 43000000, (0.65, 0.85, 0.9, 0.75, 0.65)),
    ("Green Quarter", "Алматинский район", "ул. Тлендиева, 8", 51.1468, 71.4688, "Комфорт", 2020, 12, 1100, 230000, 27500000, (0.55, 0.85, 0.95, 0.65, 0.55)),
    ("Al-Farabi", "Есильский район", "пр. Аль-Фараби, 21", 51.1302, 71.3984, "Бизнес", 2017, 16, 380, 360000, 47000000, (0.7, 0.7, 0.6, 0.8, 0.45)),
    ("Arman Qala", "Алматинский район", "ул. Жиенкулова, 3", 51.1553, 71.4706, "Комфорт", 2022, 10, 900, 210000, 24000000, (0.5, 0.75, 0.7, 0.6, 0.6)),
    ("Nova City", "Сарыаркинский район", "пр. Богенбай батыра, 62", 51.1782, 71.4053, "Эконом", 2016, 9, 1300, 180000, 19500000, (0.8, 0.4, 0.45, 0.5, 0.4)),
    ("Highvill Astana", "Есильский район", "ул. Ахмета Байтурсынова, 1", 51.1214, 71.4182, "Премиум", 2019, 24, 1200, 480000, 69000000, (0.75, 0.7, 0.9, 0.95, 0.8)),
    ("Riviera Esil", "Байконурский район", "наб. Есиля, 12", 51.1630, 71.4352, "Бизнес", 2023, 17, 450, 370000, 49000000, (0.7, 0.8, 0.8, 0.85, 0.8)),
    ("Shanyrak Park", "район Нура", "ул. Кайым Мухамедханова, 40", 51.0702, 71.4486, "Комфорт", 2024, 12, 820, 200000, 23500000, (0.45, 0.9, 0.85, 0.7, 0.7)),
]

AUTHORS = [
    "Айдана К.", "Ерлан С.", "Мадина Т.", "Данияр Б.", "Алия Н.", "Тимур Ж.", "Асель М.", "Нурлан А.",
    "Ольга П.", "Сергей В.", "Дана Е.", "Арман К.", "Жанар О.", "Руслан И.", "Камила Ш.", "Бауыржан Д.",
    "Айгерим С.", "Максим Л.", "Сабина Р.", "Ержан Т.", "Гульнара А.", "Алексей Н.", "Томирис Б.", "Ильяс М.",
]

POS = {
    "Транспорт": ["До остановки две минуты, автобусы ходят часто — до центра доезжаю за 15 минут.",
                  "Удобный выезд на проспект, до работы добираюсь быстро даже в часы пик.",
                  "Рядом транспорт и LRT, ребёнок сам ездит в школу."],
    "Тишина": ["Очень тихо по ночам, шум дороги не слышно — окна во двор.",
               "Спокойный район, соседи адекватные, тишина в подъезде.",
               "Хорошая шумоизоляция, тихо даже рядом с проспектом."],
    "Двор": ["Закрытый двор без машин, детская площадка большая и современная.",
             "Много озеленения, летом во дворе как в парке. Парковка подземная.",
             "Двор ухоженный, есть площадки для детей и воркаут."],
    "Безопасность": ["Охрана на въезде, консьерж и камеры — за ребёнка спокойно.",
                     "Безопасно: домофон с камерой, по двору работает охрана круглосуточно.",
                     "Чужие во двор не заходят, охрана быстро реагирует."],
    "Сервис": ["Управляющая компания быстро решает заявки, в подъезде чисто.",
               "Уборка каждый день, сервис на уровне, приложение для заявок удобное.",
               "КСК работает хорошо: зимой снег убирают быстро, всё чисто."],
}
NEG = {
    "Транспорт": ["Утром пробки на выезде, до центра далеко без машины.",
                  "Остановка далеко, трудно добираться общественным транспортом."],
    "Тишина": ["Слышно шум дороги и стройку по соседству, летом окна не откроешь.",
               "Громкие соседи сверху, шумоизоляция слабая."],
    "Двор": ["Парковки не хватает, во дворе машин много и тесно.",
             "Двор маленький, площадка тесная, зелени почти нет."],
    "Безопасность": ["Подъезд вечером тёмный, лифт не работает по выходным.",
                     "Охраны фактически нет, в подъезд заходят посторонние."],
    "Сервис": ["Управляющая плохая: заявки висят неделями, не убирают подъезд.",
               "После дождя течет в паркинге, ремонт делают медленно."],
}
CATS = ["Транспорт", "Тишина", "Двор", "Безопасность", "Сервис"]


def maps_url(name: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{name}, Астана, Казахстан")


def reviews_for(name: str, profile: tuple) -> list[dict]:
    rnd = random.Random(f"housecheck-demo-{name}")
    result = []
    count = rnd.randint(7, 11)
    for i in range(count):
        cats = rnd.sample(CATS, k=rnd.choice([2, 2, 3]))
        parts, score = [], 0.0
        for cat in cats:
            q = profile[CATS.index(cat)]
            good = rnd.random() < q ** 1.15
            parts.append(rnd.choice(POS[cat] if good else NEG[cat]))
            score += 1 if good else -1
        avg_q = sum(profile) / len(profile)
        rating = max(1, min(5, round(3.0 + score * 0.6 + (avg_q - 0.65) * 4 + rnd.uniform(-0.5, 0.5))))
        month = rnd.randint(1, 11)
        year = 2026 if month <= 10 else 2025
        result.append({
            "source": DEMO_SOURCE,
            "rating": rating,
            "author": rnd.choice(AUTHORS),
            "text": " ".join(parts),
            "published_at": f"{year}-{month:02d}-{rnd.randint(1, 28):02d}",
        })
    return result


def seed(connection) -> int:
    """Заполняет/обновляет демо-ЖК и демо-отзывы. Возвращает число добавленных отзывов."""
    added = 0
    for (name, district, address, lat, lng, klass, year, floors, units, rent, purchase, profile) in COMPLEXES:
        row = connection.execute("SELECT id, address FROM developments WHERE name = ?", (name,)).fetchone()
        if row is None:
            cur = connection.execute(
                """INSERT INTO developments (name, city, district, address, lat, lng, deal_type, price_from, units, source,
                   rental_price, purchase_price, google_maps_url, notes) VALUES (?, 'Астана', ?, ?, ?, ?, 'Покупка', ?, ?, 'demo', ?, ?, ?, '')""",
                (name, district, address, lat, lng, purchase, units, rent, purchase, maps_url(name)),
            )
            dev_id = cur.lastrowid
        else:
            dev_id = row["id"]
            if not row["address"]:
                connection.execute(
                    """UPDATE developments SET district=?, address=?, lat=?, lng=?, price_from=?, units=?, rental_price=?,
                       purchase_price=?, notes=CASE WHEN notes LIKE 'Каталожная запись%' THEN '' ELSE notes END WHERE id=?""",
                    (district, address, lat, lng, purchase, units, rent, purchase, dev_id),
                )
        connection.execute(
            "UPDATE developments SET housing_class=?, year_built=?, floors=? WHERE id=? AND (housing_class='' OR housing_class IS NULL)",
            (klass, year, floors, dev_id),
        )
        has = connection.execute("SELECT COUNT(*) FROM reviews WHERE development_id=? AND source=?", (dev_id, DEMO_SOURCE)).fetchone()[0]
        if not has:
            for r in reviews_for(name, profile):
                connection.execute(
                    "INSERT INTO reviews (development_id, source, rating, author, text, published_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (dev_id, r["source"], r["rating"], r["author"], r["text"], r["published_at"]),
                )
                added += 1
    connection.commit()
    return added


def remove(connection) -> None:
    connection.execute("DELETE FROM reviews WHERE source = ?", (DEMO_SOURCE,))
    connection.execute("DELETE FROM developments WHERE source = 'demo'")
    connection.commit()
