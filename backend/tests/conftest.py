"""Test-only fixtures.

Synthetic observations exist solely to exercise spatial queries, deduplication
and provenance rules. They are never loaded into a production database.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("AUTO_INIT_DB", "true")

from app import create_app  # noqa: E402
from db import db  # noqa: E402
from models import CanonicalPothole, DetectionReport, RoadProject, RoadSegment  # noqa: E402


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    AUTO_INIT_DB = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = ""
    CORS_ORIGINS = ["http://localhost:5173"]
    INGEST_API_KEY = "test-ingest-key"
    DEDUPE_RADIUS_M = 25
    DEDUPE_WINDOW_DAYS = 45
    ROAD_MATCH_RADIUS_M = 30
    GEOCODING_PROVIDER_URL = "https://nominatim.test/search"
    GEOCODING_USER_AGENT = "RoadSenseTest/1.0"
    GEOCODING_TIMEOUT_SECONDS = 2
    GEOCODING_CACHE_SECONDS = 60
    MAPTILER_API_KEY = "test-maptiler-key"
    MAPTILER_GEOCODING_URL = "https://api.maptiler.test/geocoding"
    MAPTILER_REFERER = "https://roadsense.test/"
    REVERSE_GEOCODING_ENABLED = True
    REVERSE_GEOCODING_ASYNC = False
    REVERSE_GEOCODING_LANGUAGE = "en"
    REVERSE_GEOCODING_TIMEOUT_SECONDS = 2
    REVERSE_GEOCODING_MIN_INTERVAL_SECONDS = 0
    REVERSE_GEOCODING_MAX_ATTEMPTS = 6
    REVERSE_GEOCODING_RETRY_BASE_SECONDS = 900
    REVERSE_GEOCODING_RETRY_MAX_SECONDS = 86400
    REVERSE_GEOCODING_NO_RESULT_RETRY_SECONDS = 604800
    REVERSE_GEOCODING_BATCH_LIMIT = 100
    PUBLIC_DEFAULT_LIMIT = 500
    PUBLIC_MAX_LIMIT = 2000
    PUBLIC_DETAIL_LIMIT = 25
    RESEARCH_ENABLED = False
    RESEARCH_ADMIN_KEY = "test-research-key"
    SEARXNG_URL = "http://searxng.test"
    SEARXNG_TIMEOUT_SECONDS = 2
    SEARXNG_RESULTS_PER_QUERY = 5
    OLLAMA_URL = "http://ollama.test"
    RESEARCH_MODEL = "qwen3:0.6b"
    RESEARCH_OLLAMA_TIMEOUT_SECONDS = 2
    RESEARCH_OLLAMA_NUM_CTX = 4096
    RESEARCH_OLLAMA_NUM_PREDICT = 512
    RESEARCH_MAX_QUERIES = 9
    RESEARCH_MAX_FETCHES = 5
    RESEARCH_MAX_SOURCE_CHARS = 3000
    RESEARCH_MAX_CONTEXT_CHARS = 9000
    RESEARCH_MAX_HTML_BYTES = 3000000
    RESEARCH_MAX_PDF_BYTES = 8000000
    RESEARCH_MAX_DURATION_SECONDS = 30
    RESEARCH_SEARCH_DELAY_SECONDS = 0
    RESEARCH_FETCH_DELAY_SECONDS = 0
    RESEARCH_CACHE_DAYS = 30
    RESEARCH_FAILED_RETRY_SECONDS = 3600
    RESEARCH_WORKER_POLL_SECONDS = 1
    RESEARCH_USER_AGENT = "RoadSenseTest/1.0"
    RESEARCH_ALLOWED_PORTS = {80, 443}


@pytest.fixture()
def app():
    handle, path = tempfile.mkstemp(prefix="roadsense-test-", suffix=".db")
    os.close(handle)
    TestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///{0}".format(path)
    application = create_app(TestConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
    os.unlink(path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded(app):
    with app.app_context():
        now = datetime.now(timezone.utc)

        verified_project = RoadProject(
            project_name="MC Road resurfacing — Chinnakkada reach",
            tender_id="PWD/KL/2025/00124",
            work_order_ref="WO-2025-0142",
            authority="Kerala PWD (Roads Division, Kollam)",
            contractor_name="Example Infrastructure Ltd",
            work_year=2025,
            source_name="Kerala eTendering",
            source_url="https://etenders.kerala.gov.in/example/2025/00124",
            verification_status="verified",
        )
        unknown_project = RoadProject(
            project_name="Unconfirmed road work record",
            authority="Unknown authority",
            contractor_name="Should Not Be Displayed Ltd",
            work_year=2024,
            verification_status="unknown",
        )
        db.session.add_all([verified_project, unknown_project])
        db.session.flush()

        road = RoadSegment(
            name="MC Road",
            road_number="SH 1",
            locality="Chinnakkada",
            pincode="691001",
            authority="Kerala PWD (Roads Division, Kollam)",
            classification="Major District Road / State Highway",
            latitude=8.8932,
            longitude=76.6141,
            project_id=verified_project.id,
        )
        other_road = RoadSegment(
            name="Kollam Beach Road",
            road_number=None,
            locality="Tangasseri",
            pincode="691007",
            authority="Kollam Municipal Corporation",
            classification="Urban arterial",
            latitude=8.8805,
            longitude=76.5796,
            project_id=unknown_project.id,
        )
        db.session.add_all([road, other_road])
        db.session.flush()

        potholes = [
            CanonicalPothole(
                latitude=8.893214,
                longitude=76.614102,
                report_count=5,
                confidence=0.94,
                severity="severe",
                status="open",
                first_detected_at=now - timedelta(days=4),
                last_detected_at=now - timedelta(minutes=3),
                road_id=road.id,
            ),
            CanonicalPothole(
                latitude=8.895,
                longitude=76.618,
                report_count=2,
                confidence=0.91,
                severity="moderate",
                status="open",
                first_detected_at=now - timedelta(days=9),
                last_detected_at=now - timedelta(days=8),
                road_id=road.id,
            ),
            CanonicalPothole(
                latitude=8.8805,
                longitude=76.5796,
                report_count=1,
                confidence=0.88,
                severity="moderate",
                status="open",
                first_detected_at=now - timedelta(days=2),
                last_detected_at=now - timedelta(hours=5),
                road_id=other_road.id,
            ),
            CanonicalPothole(
                latitude=9.5915,
                longitude=76.5222,
                report_count=1,
                confidence=0.8,
                severity="low",
                status="under_repair",
                first_detected_at=now - timedelta(days=20),
                last_detected_at=now - timedelta(days=19),
                road_id=None,
            ),
        ]
        db.session.add_all(potholes)
        db.session.flush()

        for index, canonical in enumerate(potholes):
            for report_index in range(canonical.report_count):
                db.session.add(
                    DetectionReport(
                        report_id="test-report-{0}-{1}".format(index, report_index),
                        canonical_pothole_id=canonical.id,
                        latitude=canonical.latitude,
                        longitude=canonical.longitude,
                        gps_accuracy_m=4.0,
                        confidence=canonical.confidence,
                        observed_at=canonical.first_detected_at
                        + timedelta(hours=report_index),
                    )
                )
        db.session.commit()

        yield {
            "road": road.id,
            "other_road": other_road.id,
            "potholes": [item.id for item in potholes],
            "now": now,
        }
