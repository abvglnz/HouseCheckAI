from __future__ import annotations

import csv
import hashlib
import json
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Iterable

from analyzer import analyze_reviews
from astana_catalog import rows as astana_rows
import demo_data
from config import DATA_DIR, DB_PATH


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        self._analysis_cache: dict[int, object] = {}
        if os.getenv("HOUSECHECK_SEED_ASTANA", "1").strip() == "1":
            self._seed_astana_catalog_if_empty()
        # Режим презентации: демо-отзывы с явным источником «Демо-данные».
        if os.getenv("HOUSECHECK_SEED_DEMO", "1").strip() == "1":
            demo_data.seed(self.connection)
        else:
            demo_data.remove(self.connection)

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS developments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
                address TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                deal_type TEXT NOT NULL DEFAULT 'Покупка',
                price_from INTEGER NOT NULL DEFAULT 0,
                units INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'demo',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                development_id INTEGER NOT NULL REFERENCES developments(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                rating INTEGER NOT NULL DEFAULT 0,
                author TEXT NOT NULL DEFAULT 'Анонимный пользователь',
                text TEXT NOT NULL,
                published_at TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS comfort_preferences (
                criterion TEXT PRIMARY KEY,
                importance INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._ensure_columns("developments", {
            "rental_price": "INTEGER NOT NULL DEFAULT 0",
            "purchase_price": "INTEGER NOT NULL DEFAULT 0",
            "google_maps_url": "TEXT NOT NULL DEFAULT ''",
            "two_gis_url": "TEXT NOT NULL DEFAULT ''",
            "google_place_id": "TEXT NOT NULL DEFAULT ''",
            "favorite": "INTEGER NOT NULL DEFAULT 0",
            "notes": "TEXT NOT NULL DEFAULT ''",
            "housing_class": "TEXT NOT NULL DEFAULT ''",
            "year_built": "INTEGER NOT NULL DEFAULT 0",
            "floors": "INTEGER NOT NULL DEFAULT 0",
        })
        self._ensure_super_admin()
        self.connection.commit()

    @staticmethod
    def _password_hash(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
        return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"

    @classmethod
    def _password_matches(cls, password: str, stored: str) -> bool:
        if stored.startswith("pbkdf2_sha256$"):
            try:
                _, salt_hex, digest_hex = stored.split("$", 2)
                digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 240_000)
                return secrets.compare_digest(digest.hex(), digest_hex)
            except (ValueError, TypeError):
                return False
        # Совместимость с самым первым локальным прототипом; при входе хеш будет обновлён.
        return secrets.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)

    def _ensure_super_admin(self) -> None:
        row = self.connection.execute("SELECT id FROM users WHERE username = ?", ("super_admin",)).fetchone()
        if not row:
            self.connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("super_admin", self._password_hash("super_admin"), "super_admin"),
            )

    def authenticate(self, username: str, password: str) -> dict | None:
        row = self.connection.execute(
            "SELECT * FROM users WHERE username = ? AND active = 1",
            (username.strip(),),
        ).fetchone()
        if row and self._password_matches(password, row["password_hash"]):
            if not row["password_hash"].startswith("pbkdf2_sha256$"):
                self.connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (self._password_hash(password), row["id"]))
                self.connection.commit()
            return dict(row)
        return None

    def users(self) -> list[dict]:
        return [dict(row) for row in self.connection.execute("SELECT id, username, role, active, created_at FROM users ORDER BY username")]

    def add_user(self, username: str, password: str, role: str) -> int:
        cursor = self.connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), self._password_hash(password), role),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def reset_user_password(self, user_id: int, password: str) -> None:
        self.connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (self._password_hash(password), user_id))
        self.connection.commit()

    def delete_user(self, user_id: int) -> None:
        self.connection.execute("DELETE FROM users WHERE id != 1 AND id = ?", (user_id,))
        self.connection.commit()

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _seed_demo_data_if_empty(self) -> None:
        if self.connection.execute("SELECT COUNT(*) FROM developments").fetchone()[0]:
            return
        samples = [
            {
                "name": "Северный парк",
                "city": "Алматы",
                "district": "Бостандыкский район",
                "address": "ул. Тимирязева, 42",
                "lat": 43.2183,
                "lng": 76.8954,
                "deal_type": "Аренда",
                "price_from": 280000,
                "units": 420,
                "reviews": [
                    (5, "Айдана", "Тихий закрытый двор, рядом остановка и магазины. В подъезде чисто, охрана быстро реагирует."),
                    (4, "Марат", "До центра удобно добираться, но вечером бывают пробки. Парковка организована хорошо."),
                    (3, "Ольга", "Дом комфортный, однако лифт иногда долго ждёшь в часы пик."),
                ],
            },
            {
                "name": "Riverside Residence",
                "city": "Алматы",
                "district": "Медеуский район",
                "address": "пр. Достык, 128",
                "lat": 43.2389,
                "lng": 76.9562,
                "deal_type": "Покупка",
                "price_from": 76000000,
                "units": 188,
                "reviews": [
                    (5, "Ермек", "Очень красивый двор и озеленение. Тихо, окна не выходят на шумную дорогу."),
                    (4, "Сауле", "Сервис управляющей компании хороший, заявки решают быстро. Рядом школы и кафе."),
                    (3, "Илья", "Слабое место — мало гостевой парковки и далеко до метро."),
                ],
            },
            {
                "name": "Жетысу Hills",
                "city": "Алматы",
                "district": "Алмалинский район",
                "address": "ул. Жибек Жолы, 91",
                "lat": 43.2606,
                "lng": 76.9237,
                "deal_type": "Покупка",
                "price_from": 49500000,
                "units": 640,
                "reviews": [
                    (4, "Наталья", "Хорошая локация, транспорт рядом, но по утрам бывают пробки."),
                    (2, "Данияр", "Во дворе тесно, машин много. После дождя в паркинге была вода."),
                    (3, "Алина", "В целом удобно, но хотелось бы лучше уборку в подъезде."),
                ],
            },
        ]
        for sample in samples:
            development_id = self.add_development(sample, source="demo")
            for rating, author, text in sample["reviews"]:
                self.add_review(development_id, "Демонстрационные данные", rating, author, text, "2026-09-01")

    def _remove_demo_data(self) -> None:
        """Не показываем синтетические записи в рабочем режиме."""
        self.connection.execute("DELETE FROM developments WHERE source = 'demo'")
        self.connection.commit()

    def _seed_astana_catalog_if_empty(self) -> None:
        if self.connection.execute("SELECT COUNT(*) FROM developments").fetchone()[0]:
            return
        for item in astana_rows():
            self.add_development(item, source="astana_catalog")

    def add_development(self, item: dict, source: str = "import") -> int:
        city = str(item.get("city", "Астана") or "Астана").strip()
        if source != "demo" and city.casefold() not in {"астана", "astana"}:
            raise ValueError("HouseCheck AI сейчас работает только с ЖК города Астана.")
        cursor = self.connection.execute(
            """
            INSERT INTO developments (name, city, district, address, lat, lng, deal_type, price_from, units, source,
                                      rental_price, purchase_price, google_maps_url, two_gis_url, google_place_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("name", "Без названия"), "Астана", item.get("district", ""),
                item.get("address", ""), float(item.get("lat", 43.238)), float(item.get("lng", 76.945)),
                item.get("deal_type", "Покупка"), int(item.get("price_from", 0) or 0), int(item.get("units", 0) or 0), source,
                int(item.get("rental_price", item.get("price_from", 0)) or 0), int(item.get("purchase_price", 0) or 0),
                item.get("google_maps_url", ""), item.get("two_gis_url", ""), item.get("google_place_id", ""), item.get("notes", ""),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def update_development(self, development_id: int, item: dict) -> None:
        self.connection.execute(
            """
            UPDATE developments SET name=?, city=?, district=?, address=?, lat=?, lng=?, deal_type=?, price_from=?,
            rental_price=?, purchase_price=?, google_maps_url=?, two_gis_url=?, google_place_id=?, notes=? WHERE id=?
            """,
            (
                item.get("name", ""), item.get("city", ""), item.get("district", ""), item.get("address", ""),
                float(item.get("lat", 0) or 0), float(item.get("lng", 0) or 0), item.get("deal_type", "Покупка"),
                int(item.get("price_from", item.get("rental_price", 0)) or 0), int(item.get("rental_price", 0) or 0),
                int(item.get("purchase_price", 0) or 0), item.get("google_maps_url", ""), item.get("two_gis_url", ""),
                item.get("google_place_id", ""), item.get("notes", ""), development_id,
            ),
        )
        self.connection.commit()

    def delete_development(self, development_id: int) -> None:
        self.connection.execute("DELETE FROM developments WHERE id = ?", (development_id,))
        self.connection.commit()
        self._analysis_cache.pop(development_id, None)

    def toggle_favorite(self, development_id: int) -> bool:
        self.connection.execute("UPDATE developments SET favorite = CASE favorite WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (development_id,))
        self.connection.commit()
        return bool(self.connection.execute("SELECT favorite FROM developments WHERE id = ?", (development_id,)).fetchone()[0])

    def favorites(self) -> list[dict]:
        rows = self.connection.execute("SELECT * FROM developments WHERE favorite = 1 ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def set_preference(self, criterion: str, importance: int) -> None:
        self.connection.execute("INSERT INTO comfort_preferences (criterion, importance) VALUES (?, ?) ON CONFLICT(criterion) DO UPDATE SET importance=excluded.importance", (criterion, int(importance)))
        self.connection.commit()

    def preferences(self) -> dict[str, int]:
        return {row["criterion"]: int(row["importance"]) for row in self.connection.execute("SELECT criterion, importance FROM comfort_preferences")}

    def add_review(self, development_id: int, source: str, rating: int, author: str, text: str, published_at: str = "") -> None:
        self.connection.execute(
            "INSERT INTO reviews (development_id, source, rating, author, text, published_at) VALUES (?, ?, ?, ?, ?, ?)",
            (development_id, source, int(rating), author or "Анонимный пользователь", text, published_at),
        )
        self.connection.commit()
        self._analysis_cache.pop(development_id, None)

    def clear_reviews_for_source(self, development_id: int, source: str) -> None:
        self.connection.execute(
            "DELETE FROM reviews WHERE development_id = ? AND source = ?",
            (development_id, source),
        )
        self.connection.commit()
        self._analysis_cache.pop(development_id, None)

    def developments(self, search: str = "", deal_type: str = "Все", city: str = "Все", favorites_only: bool = False) -> list[dict]:
        query = "SELECT * FROM developments WHERE 1=1"
        params: list[object] = []
        if search.strip():
            query += " AND (name LIKE ? OR district LIKE ? OR address LIKE ?)"
            like = f"%{search.strip()}%"
            params.extend([like, like, like])
        if deal_type != "Все":
            query += " AND deal_type = ?"
            params.append(deal_type)
        if city != "Все":
            query += " AND city = ?"
            params.append(city)
        if favorites_only:
            query += " AND favorite = 1"
        query += " ORDER BY name"
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_development(self, development_id: int) -> dict | None:
        row = self.connection.execute("SELECT * FROM developments WHERE id = ?", (development_id,)).fetchone()
        return dict(row) if row else None

    def reviews_for(self, development_id: int) -> list[dict]:
        rows = self.connection.execute("SELECT * FROM reviews WHERE development_id = ? ORDER BY published_at DESC, id DESC", (development_id,)).fetchall()
        return [dict(row) for row in rows]

    def analysis_for(self, development_id: int):
        if development_id not in self._analysis_cache:
            self._analysis_cache[development_id] = analyze_reviews(self.reviews_for(development_id))
        return self._analysis_cache[development_id]

    def review_count(self, development_id: int) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM reviews WHERE development_id = ?", (development_id,)).fetchone()[0])

    def avg_rating(self, development_id: int) -> float:
        row = self.connection.execute("SELECT AVG(rating) FROM reviews WHERE development_id = ?", (development_id,)).fetchone()
        return float(row[0] or 0)

    def all_reviews(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT r.*, d.name AS development_name FROM reviews r JOIN developments d ON d.id = r.development_id ORDER BY r.published_at DESC, r.id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def total_reviews(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0])

    def import_file(self, path: Path) -> tuple[int, int]:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            developments = payload if isinstance(payload, list) else payload.get("developments", [])
        else:
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                developments = list(csv.DictReader(file))

        created_developments = 0
        created_reviews = 0
        for item in developments:
            if str(item.get("city", "Астана") or "Астана").strip().casefold() not in {"астана", "astana"}:
                continue
            reviews = item.pop("reviews", []) if isinstance(item, dict) else []
            if isinstance(reviews, str):
                reviews = json.loads(reviews)
            development_id = self.add_development(item, source="import")
            created_developments += 1
            for review in reviews:
                self.add_review(
                    development_id,
                    review.get("source", "Импорт"),
                    review.get("rating", 0),
                    review.get("author", "Анонимный пользователь"),
                    review.get("text", ""),
                    review.get("published_at", ""),
                )
                created_reviews += 1
        return created_developments, created_reviews

    def close(self) -> None:
        self.connection.close()

