"""Глобальные токены и загрузчик темы HouseCheck AI (стиль NGIJIH / Figma)."""

from __future__ import annotations

import sys
from pathlib import Path


def _resource_dir() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent


LIGHT = {
    "bg": "#FFF6EE", "bg2": "#FFEFE2", "surface": "#FFFFFF", "surface_muted": "#FFF4EA",
    "ink": "#17233F", "text": "#17233F", "text_muted": "#7A8498", "text_soft": "#A3ABBB",
    "accent": "#F28A3C", "accent_hover": "#E5782A", "accent_soft": "#FFE6D2", "accent_glow": "#FFB37A",
    "lime": "#B9F36B", "sky": "#DCEEFF", "peach": "#FFE1CE", "mint": "#DBF5E6", "lilac": "#ECE6FF",
    "danger": "#E0584B", "danger_soft": "#FDE3E0", "border": "#F0E3D8", "border_strong": "#E4D2C3",
    "shadow": "#8A5A3A", "nav": "#17233F", "nav2": "#22305A", "nav_text": "#F7FAFF", "nav_muted": "#9AA6C0",
    "positive": "#3F9B5A", "positive_soft": "#DDF3E3", "warning": "#D9822B", "warning_soft": "#FFF0DC",
    "white": "#FFFFFF", "field": "#FFFFFF", "grid": "#F6ECE4", "selection": "#FFE0C9",
    "map_land": "#F7EFE6", "map_park": "#D9EFD3", "map_water": "#B9DCF5", "map_road": "#FFFFFF",
    "font_family": '"Poppins", "Nunito", "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial',
}

DARK = {
    **LIGHT,
    "bg": "#0F1426", "bg2": "#141A31", "surface": "#1A2140", "surface_muted": "#212A4D",
    "ink": "#F4F6FF", "text": "#F4F6FF", "text_muted": "#A6B0C9", "text_soft": "#6E7898",
    "accent_soft": "#3B2A2A", "accent_glow": "#C46A2B", "sky": "#1F3352", "peach": "#3A2A2A",
    "mint": "#1D3A2E", "lilac": "#2B2850", "danger_soft": "#3D2026",
    "border": "#2A3358", "border_strong": "#36406A", "shadow": "#000000",
    "nav": "#0A0F1F", "nav2": "#161D38", "positive": "#7FD99A", "positive_soft": "#1C3A2A",
    "warning": "#F4B36E", "warning_soft": "#3A2E1E", "field": "#212A4D", "grid": "#263056",
    "selection": "#4A3328", "map_land": "#1A2140", "map_park": "#1F3A33", "map_water": "#24446B",
    "map_road": "#283160",
}

THEMES = {"light": LIGHT, "dark": DARK}

# Текущие токены — меняются при смене темы (UI перестраивается целиком).
T: dict[str, str] = dict(LIGHT)


def set_theme(name: str) -> None:
    T.clear()
    T.update(THEMES["dark" if name == "dark" else "light"])


def tokens_for(theme: str) -> dict[str, str]:
    return THEMES["dark" if theme == "dark" else "light"]


def load_theme_stylesheet(theme: str) -> str:
    source = (_resource_dir() / "theme.qss").read_text(encoding="utf-8")
    source = source.replace("@assets@", (_resource_dir() / "assets").as_posix())
    for name, value in sorted(tokens_for(theme).items(), key=lambda kv: -len(kv[0])):
        source = source.replace(f"@{name}@", value)
    return source
