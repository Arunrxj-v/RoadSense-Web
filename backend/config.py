"""Runtime configuration for the RoadSense public API.

Every deployment-specific value is supplied through the environment. The
defaults are safe for local development only; production must provide a
PostgreSQL/PostGIS URL, restrictive CORS origins, and an ingest key.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'instance' / 'roadsense.db'}"
    )
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    JSON_SORT_KEYS = False
    AUTO_INIT_DB = _bool("AUTO_INIT_DB", True)

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://100.104.179.69:5173,http://localhost:5174,"
            "http://127.0.0.1:5174,http://100.104.179.69:5174,"
            "http://localhost:8091,http://127.0.0.1:8091,"
            "http://100.104.179.69:8091",
        ).split(",")
        if origin.strip()
    ]

    INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")
    DEDUPE_RADIUS_M = _int("DEDUPE_RADIUS_M", 25)
    DEDUPE_WINDOW_DAYS = _int("DEDUPE_WINDOW_DAYS", 45)
    ROAD_MATCH_RADIUS_M = _int("ROAD_MATCH_RADIUS_M", 30)

    GEOCODING_PROVIDER_URL = os.getenv(
        "GEOCODING_PROVIDER_URL", "https://nominatim.openstreetmap.org/search"
    )
    GEOCODING_USER_AGENT = os.getenv(
        "GEOCODING_USER_AGENT",
        "RoadSenseVision/2.0 (public road condition map; contact: admin@roadsense.local)",
    )
    GEOCODING_TIMEOUT_SECONDS = _int("GEOCODING_TIMEOUT_SECONDS", 8)
    GEOCODING_CACHE_SECONDS = _int("GEOCODING_CACHE_SECONDS", 86400)

    PUBLIC_DEFAULT_LIMIT = _int("PUBLIC_DEFAULT_LIMIT", 500)
    PUBLIC_MAX_LIMIT = _int("PUBLIC_MAX_LIMIT", 2000)
    PUBLIC_DETAIL_LIMIT = _int("PUBLIC_DETAIL_LIMIT", 25)
