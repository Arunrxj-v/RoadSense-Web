"""Server-side Indian PIN code geocoding.

Nominatim is used by default because it requires no private key and can resolve
Indian postal codes. The public web client never contacts the provider directly,
so usage policy, caching and the User-Agent live on the server.
"""
import threading
import time

import requests
from flask import current_app

_CACHE = {}
_CACHE_LOCK = threading.Lock()
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0


class GeocodeError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def _cache_get(pincode):
    with _CACHE_LOCK:
        item = _CACHE.get(pincode)
    if not item:
        return None
    expires_at, payload = item
    if expires_at < time.time():
        with _CACHE_LOCK:
            _CACHE.pop(pincode, None)
        return None
    return payload


def _cache_set(pincode, payload):
    ttl = current_app.config["GEOCODING_CACHE_SECONDS"]
    with _CACHE_LOCK:
        _CACHE[pincode] = (time.time() + ttl, payload)


def _request(params):
    global _LAST_REQUEST_AT
    # Nominatim asks clients to make at most one request per second.
    with _REQUEST_LOCK:
        wait = 1.0 - (time.time() - _LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_AT = time.time()
    return requests.get(
        current_app.config["GEOCODING_PROVIDER_URL"],
        params=params,
        headers={
            "User-Agent": current_app.config["GEOCODING_USER_AGENT"],
            "Accept": "application/json",
            "Accept-Language": "en",
        },
        timeout=current_app.config["GEOCODING_TIMEOUT_SECONDS"],
    )


def resolve_pincode(pincode):
    cached = _cache_get(pincode)
    if cached:
        return cached

    common = {
        "format": "jsonv2",
        "addressdetails": 1,
        "countrycodes": "in",
        "limit": 1,
    }
    attempts = [
        dict(common, postalcode=pincode, country="India"),
        dict(common, q="{0}, India".format(pincode)),
    ]

    result = None
    try:
        for params in attempts:
            response = _request(params)
            if response.status_code == 429:
                raise GeocodeError(
                    "The location service is busy. Please try again in a moment.", 503
                )
            if response.status_code >= 500:
                raise GeocodeError(
                    "The location service is temporarily unavailable.", 502
                )
            if response.status_code != 200:
                continue
            payload = response.json()
            if isinstance(payload, list) and payload:
                result = payload[0]
                break
    except requests.Timeout:
        raise GeocodeError("The location service timed out. Please try again.", 504)
    except requests.RequestException:
        raise GeocodeError(
            "The location service could not be reached. Please try again.", 502
        )

    if not result:
        raise GeocodeError("No location was found for that PIN code.", 404)

    try:
        latitude = float(result["lat"])
        longitude = float(result["lon"])
    except (KeyError, TypeError, ValueError):
        raise GeocodeError("The location service returned an invalid result.", 502)

    if not (6.0 <= latitude <= 38.0 and 68.0 <= longitude <= 98.0):
        raise GeocodeError("No location was found for that PIN code.", 404)

    payload = {
        "pincode": pincode,
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "display_name": result.get("display_name"),
        "source": "OpenStreetMap Nominatim",
    }
    _cache_set(pincode, payload)
    return payload


def valid_pincode(value):
    return bool(value) and len(value) == 6 and value.isdigit() and value[0] != "0"
