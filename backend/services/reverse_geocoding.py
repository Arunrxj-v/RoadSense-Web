"""MapTiler reverse geocoding for canonical pothole coordinates.

Coordinates are the source of truth. This module only translates a coordinate
pair into provider-returned address/road fields; it never moves or rewrites the
canonical point. Requests are server-side so the provider key and usage policy
stay out of the browser.
"""
from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from flask import current_app

PROVIDER_NAME = "maptiler"
PROVIDER_ATTRIBUTION = "MapTiler / OpenStreetMap contributors"

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0


class ReverseGeocodeError(Exception):
    def __init__(self, code, retryable=True, retry_after_seconds=None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class ReverseGeocodeResult:
    road_name: str | None = None
    road_number: str | None = None
    classification: str | None = None
    locality: str | None = None
    pincode: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    authority: str | None = None
    administrative_area: str | None = None
    suburb: str | None = None
    municipality: str | None = None
    operator: str | None = None
    provider: str = PROVIDER_NAME
    provider_place_id: str | None = None


def valid_coordinate(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _clean_text(value, max_length):
    if not isinstance(value, str):
        return None
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if not cleaned:
        return None
    return cleaned[:max_length]


def _normalize_pincode(value):
    cleaned = _clean_text(value, 16)
    if not cleaned:
        return None
    compact = re.sub(r"\s+", "", cleaned)
    if compact.isdigit() and len(compact) == 6:
        return compact
    if 3 <= len(cleaned) <= 16:
        return cleaned
    return None


def _normalize_route_ref(value):
    cleaned = _clean_text(value, 64)
    if not cleaned:
        return None
    if cleaned.lower().startswith("osm:"):
        return None
    return cleaned


def _context_value(context, *prefixes):
    for item in context or []:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or "." not in item_id:
            continue
        prefix = item_id.split(".", 1)[0]
        if prefix in prefixes:
            return _clean_text(item.get("text_en") or item.get("text"), 255)
    return None


def _feature_score(feature):
    if not isinstance(feature, dict):
        return -1
    properties = feature.get("properties") or {}
    types = set()
    for key in ("place_type", "place_type_name"):
        values = feature.get(key) or []
        if isinstance(values, list):
            types.update(value for value in values if isinstance(value, str))
    score = 0
    if "address" in types:
        score += 100
    if "street" in types or "road" in types:
        score += 80
    if properties.get("kind") in {"street", "road"}:
        score += 60
    if _context_value(feature.get("context"), "postal_code"):
        score += 10
    return score


def _parse_maptiler(payload):
    if not isinstance(payload, dict):
        raise ReverseGeocodeError("invalid_response")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ReverseGeocodeError("invalid_response")
    features = [feature for feature in features if isinstance(feature, dict)]
    if not features:
        return None

    feature = max(features, key=_feature_score)
    properties = feature.get("properties") or {}
    tags = feature.get("feature_tags") or {}
    context = feature.get("context") or []
    types = set()
    for key in ("place_type", "place_type_name"):
        values = feature.get(key) or []
        if isinstance(values, list):
            types.update(value for value in values if isinstance(value, str))
    kind = properties.get("kind")
    is_road = kind in {"street", "road"} or bool(
        types.intersection({"address", "street", "road"})
    )

    road_name = None
    if is_road:
        road_name = _clean_text(feature.get("text_en") or feature.get("text"), 255)

    road_number = _normalize_route_ref(properties.get("ref"))
    if road_number is None:
        road_number = _normalize_route_ref(tags.get("ref"))

    classification = _clean_text(tags.get("highway"), 128)
    operator = _clean_text(tags.get("operator"), 255)
    authority = _clean_text(tags.get("authority"), 255)

    county = _context_value(context, "county")
    subregion = _context_value(context, "subregion")
    district = subregion or county
    administrative_area = county if county and county != district else None

    result = ReverseGeocodeResult(
        road_name=road_name,
        road_number=road_number,
        classification=classification,
        locality=_context_value(context, "place", "locality"),
        pincode=_normalize_pincode(_context_value(context, "postal_code")),
        district=district,
        state=_context_value(context, "region"),
        country=_context_value(context, "country"),
        authority=authority,
        administrative_area=administrative_area,
        suburb=_context_value(context, "neighbourhood", "suburb"),
        municipality=_context_value(context, "localadmin", "municipality"),
        operator=operator,
        provider=PROVIDER_NAME,
        provider_place_id=_clean_text(feature.get("id"), 128),
    )

    if not any(
        value
        for value in (
            result.road_name,
            result.road_number,
            result.classification,
            result.locality,
            result.pincode,
            result.district,
            result.state,
            result.country,
            result.authority,
            result.administrative_area,
            result.suburb,
            result.municipality,
            result.operator,
        )
    ):
        return None
    return result


def _throttle():
    interval = float(
        current_app.config.get("REVERSE_GEOCODING_MIN_INTERVAL_SECONDS") or 0
    )
    if interval <= 0:
        return
    global _LAST_REQUEST_AT
    with _REQUEST_LOCK:
        wait = interval - (time.monotonic() - _LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_AT = time.monotonic()


def _retry_after_seconds(response):
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0, int(raw.strip()))
    except (TypeError, ValueError):
        return None


def _fetch_maptiler(latitude, longitude):
    if not current_app.config.get("REVERSE_GEOCODING_ENABLED", True):
        raise ReverseGeocodeError("disabled", retryable=False)

    key = current_app.config.get("MAPTILER_API_KEY")
    if not key:
        raise ReverseGeocodeError("provider_not_configured", retryable=False)

    base_url = (
        current_app.config.get("MAPTILER_GEOCODING_URL")
        or "https://api.maptiler.com/geocoding"
    ).rstrip("/")
    url = "{0}/{1:.7f},{2:.7f}.json".format(base_url, longitude, latitude)
    headers = {
        "Accept": "application/json",
        "User-Agent": current_app.config.get("GEOCODING_USER_AGENT", "RoadSense"),
    }
    referer = current_app.config.get("MAPTILER_REFERER")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            headers["Referer"] = referer

    _throttle()
    try:
        response = requests.get(
            url,
            params={
                "key": key,
                "language": current_app.config.get("REVERSE_GEOCODING_LANGUAGE", "en"),
            },
            headers=headers,
            timeout=current_app.config.get("REVERSE_GEOCODING_TIMEOUT_SECONDS", 8),
        )
    except requests.Timeout:
        raise ReverseGeocodeError("timeout", retryable=True)
    except requests.RequestException:
        raise ReverseGeocodeError("network_error", retryable=True)

    if response.status_code == 429:
        raise ReverseGeocodeError(
            "rate_limited",
            retryable=True,
            retry_after_seconds=_retry_after_seconds(response),
        )
    if response.status_code in {401, 403}:
        raise ReverseGeocodeError("provider_forbidden", retryable=True)
    if response.status_code >= 500:
        raise ReverseGeocodeError("provider_unavailable", retryable=True)
    if response.status_code != 200:
        raise ReverseGeocodeError("provider_error", retryable=True)

    try:
        payload = response.json()
    except ValueError:
        raise ReverseGeocodeError("invalid_response", retryable=True)
    return _parse_maptiler(payload)


def reverse_geocode(latitude, longitude):
    if not valid_coordinate(latitude, longitude):
        raise ReverseGeocodeError("invalid_coordinates", retryable=False)
    return _fetch_maptiler(float(latitude), float(longitude))
