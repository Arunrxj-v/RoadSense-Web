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


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
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

    MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY", "")
    MAPTILER_GEOCODING_URL = os.getenv(
        "MAPTILER_GEOCODING_URL", "https://api.maptiler.com/geocoding"
    )
    # Origin-restricted MapTiler keys need the approved site origin. Prefer a
    # server key without origin restrictions when one is available.
    MAPTILER_REFERER = os.getenv("MAPTILER_REFERER", "")
    REVERSE_GEOCODING_ENABLED = _bool("REVERSE_GEOCODING_ENABLED", True)
    REVERSE_GEOCODING_ASYNC = _bool("REVERSE_GEOCODING_ASYNC", True)
    REVERSE_GEOCODING_LANGUAGE = os.getenv("REVERSE_GEOCODING_LANGUAGE", "en")
    REVERSE_GEOCODING_TIMEOUT_SECONDS = _int(
        "REVERSE_GEOCODING_TIMEOUT_SECONDS", 8
    )
    REVERSE_GEOCODING_MIN_INTERVAL_SECONDS = _float(
        "REVERSE_GEOCODING_MIN_INTERVAL_SECONDS", 0.25
    )
    REVERSE_GEOCODING_MAX_ATTEMPTS = _int("REVERSE_GEOCODING_MAX_ATTEMPTS", 6)
    REVERSE_GEOCODING_RETRY_BASE_SECONDS = _int(
        "REVERSE_GEOCODING_RETRY_BASE_SECONDS", 900
    )
    REVERSE_GEOCODING_RETRY_MAX_SECONDS = _int(
        "REVERSE_GEOCODING_RETRY_MAX_SECONDS", 86400
    )
    REVERSE_GEOCODING_NO_RESULT_RETRY_SECONDS = _int(
        "REVERSE_GEOCODING_NO_RESULT_RETRY_SECONDS", 604800
    )
    REVERSE_GEOCODING_BATCH_LIMIT = _int("REVERSE_GEOCODING_BATCH_LIMIT", 100)

    PUBLIC_DEFAULT_LIMIT = _int("PUBLIC_DEFAULT_LIMIT", 500)
    PUBLIC_MAX_LIMIT = _int("PUBLIC_MAX_LIMIT", 2000)
    PUBLIC_DETAIL_LIMIT = _int("PUBLIC_DETAIL_LIMIT", 25)

    RESEARCH_ENABLED = _bool("RESEARCH_ENABLED", True)
    RESEARCH_ADMIN_KEY = os.getenv("RESEARCH_ADMIN_KEY", "")
    SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
    SEARXNG_ENGINES = os.getenv("SEARXNG_ENGINES", "yep")
    SEARXNG_TIMEOUT_SECONDS = _int("SEARXNG_TIMEOUT_SECONDS", 15)
    SEARXNG_RESULTS_PER_QUERY = _int("SEARXNG_RESULTS_PER_QUERY", 5)
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
    RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "qwen3:0.6b")
    RESEARCH_OLLAMA_TIMEOUT_SECONDS = _int("RESEARCH_OLLAMA_TIMEOUT_SECONDS", 120)
    RESEARCH_OLLAMA_NUM_CTX = _int("RESEARCH_OLLAMA_NUM_CTX", 4096)
    RESEARCH_OLLAMA_NUM_PREDICT = _int("RESEARCH_OLLAMA_NUM_PREDICT", 512)
    RESEARCH_MAX_QUERIES = _int("RESEARCH_MAX_QUERIES", 10)
    RESEARCH_MAX_FETCHES = _int("RESEARCH_MAX_FETCHES", 5)
    RESEARCH_MAX_SOURCE_CHARS = _int("RESEARCH_MAX_SOURCE_CHARS", 3000)
    RESEARCH_MAX_CONTEXT_CHARS = _int("RESEARCH_MAX_CONTEXT_CHARS", 9000)
    RESEARCH_MAX_HTML_BYTES = _int("RESEARCH_MAX_HTML_BYTES", 3000000)
    RESEARCH_MAX_PDF_BYTES = _int("RESEARCH_MAX_PDF_BYTES", 8000000)
    RESEARCH_MAX_DURATION_SECONDS = _int("RESEARCH_MAX_DURATION_SECONDS", 180)
    RESEARCH_SEARCH_DELAY_SECONDS = _float("RESEARCH_SEARCH_DELAY_SECONDS", 0.8)
    RESEARCH_FETCH_DELAY_SECONDS = _float("RESEARCH_FETCH_DELAY_SECONDS", 1.2)
    RESEARCH_CACHE_DAYS = _int("RESEARCH_CACHE_DAYS", 30)
    RESEARCH_FAILED_RETRY_SECONDS = _int("RESEARCH_FAILED_RETRY_SECONDS", 3600)
    RESEARCH_WORKER_POLL_SECONDS = _int("RESEARCH_WORKER_POLL_SECONDS", 5)
    RESEARCH_USER_AGENT = os.getenv(
        "RESEARCH_USER_AGENT",
        "RoadSenseResearch/1.0 (public road records research; contact: admin@roadsense.local)",
    )
    RESEARCH_ALLOWED_PORTS = {
        int(port.strip())
        for port in os.getenv("RESEARCH_ALLOWED_PORTS", "80,443").split(",")
        if port.strip().isdigit()
    }
