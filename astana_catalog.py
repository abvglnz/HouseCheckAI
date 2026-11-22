"""Стартовый каталог названий ЖК Астаны без выдуманных цен и отзывов.

Названия собраны из открытых каталогов застройщиков и реестров. Адрес,
координаты и отзывы уточняются через Google Places после добавления ключа.
"""

from __future__ import annotations

import urllib.parse


ASTANA_DEVELOPMENTS = [
    "BI City",
    "BI City Seoul",
    "BI City Tokyo",
    "Capital Park",
    "Grand Opera",
    "Expo Boulevard",
    "Promenade Expo",
    "Green Quarter",
    "Al-Farabi",
    "Arman Qala",
    "Nova City",
    "Highvill Astana",
]


def rows() -> list[dict]:
    result = []
    for name in ASTANA_DEVELOPMENTS:
        query = urllib.parse.quote(f"{name}, Астана, Казахстан")
        result.append({
            "name": name,
            "city": "Астана",
            "district": "",
            "address": "",
            "lat": 51.1694,
            "lng": 71.4491,
            "deal_type": "Покупка",
            "price_from": 0,
            "rental_price": 0,
            "purchase_price": 0,
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={query}",
            "notes": "Каталожная запись. Адрес, цены и отзывы не заполнены автоматически; уточняются через Google Places.",
        })
    return result
