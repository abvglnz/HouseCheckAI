from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    if sys.platform == "darwin":
        DATA_DIR = Path.home() / "Library" / "Application Support" / "HouseCheck AI"
    elif sys.platform == "win32":
        DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "HouseCheck AI"
    else:
        DATA_DIR = Path.home() / ".local" / "share" / "HouseCheck AI"
else:
    DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "housecheck.sqlite3"


def load_local_env() -> None:
    """Минимальный загрузчик .env без дополнительной зависимости."""
    for env_path in [ROOT_DIR / ".env", DATA_DIR / ".env"]:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def google_maps_api_key() -> str:
    load_local_env()
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def google_places_api_key() -> str:
    load_local_env()
    return os.getenv("GOOGLE_PLACES_API_KEY", "").strip()

