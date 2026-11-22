from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from config import load_local_env


class GooglePlacesError(RuntimeError):
    pass


def api_key() -> str:
    load_local_env()
    return os.getenv("GOOGLE_PLACES_API_KEY", "").strip()


def _request(url: str, payload: dict | None, field_mask: str) -> dict:
    key = api_key()
    if not key:
        raise GooglePlacesError("Добавь GOOGLE_PLACES_API_KEY в файл .env")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": field_mask,
    }
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8") if payload is not None else None, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise GooglePlacesError(f"Google Places API: {error.code} {detail[:240]}") from error
    except urllib.error.URLError as error:
        raise GooglePlacesError(f"Нет соединения с Google Places API: {error.reason}") from error


def search_place(query: str) -> list[dict]:
    result = _request(
        "https://places.googleapis.com/v1/places:searchText",
        {"textQuery": query, "languageCode": "ru", "pageSize": 5},
        "places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri,places.rating,places.userRatingCount",
    )
    return result.get("places", [])


def get_place_details(place_id: str) -> dict:
    encoded = urllib.parse.quote(place_id, safe="/")
    return _request(
        f"https://places.googleapis.com/v1/{encoded}",
        None,
        "id,displayName,formattedAddress,location,googleMapsUri,rating,userRatingCount,reviews",
    )


def normalize_reviews(place: dict) -> list[dict]:
    normalized = []
    for review in place.get("reviews", [])[:5]:
        text = review.get("text", {}).get("text", "").strip()
        if not text:
            continue
        normalized.append({
            "source": "Google Maps",
            "rating": int(round(float(review.get("rating", 0) or 0))),
            "author": review.get("authorAttribution", {}).get("displayName", "Пользователь Google Maps"),
            "text": text,
            "published_at": review.get("relativePublishTimeDescription", ""),
        })
    return normalized

