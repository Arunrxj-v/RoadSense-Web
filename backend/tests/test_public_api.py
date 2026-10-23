from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

from db import db
from models import (
    CanonicalPothole,
    DetectionReport,
    PotholeLocationMetadata,
    parse_public_id,
)
from services.location_enrichment import enrich_pothole
from services.reverse_geocoding import (
    ReverseGeocodeResult,
    _parse_maptiler,
    valid_coordinate,
)


def public_id(numeric):
    return "PH-{0:06d}".format(numeric)


def test_health_and_meta(client, seeded):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}

    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.get_json()
    assert body["pothole_count"] == 4
    assert body["latest_detection_at"].endswith("Z")


def test_bbox_queries_only_return_viewport_potholes(client, seeded):
    response = client.get(
        "/api/v1/potholes?bbox=76.60,8.88,76.63,8.90&limit=100"
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["meta"]["total"] == 2
    assert {item["id"] for item in body["potholes"]} == {
        public_id(seeded["potholes"][0]),
        public_id(seeded["potholes"][1]),
    }
    assert all("latitude" in item and "longitude" in item for item in body["potholes"])

    named_bounds = client.get(
        "/api/v1/potholes?min_lat=8.87&max_lat=8.89&min_lng=76.57&max_lng=76.59&limit=100"
    )
    assert named_bounds.status_code == 200
    assert named_bounds.get_json()["meta"]["total"] == 1


def test_bbox_validation(client):
    assert client.get("/api/v1/potholes").status_code == 400
    assert client.get("/api/v1/potholes?bbox=1,2,3").status_code == 400
    assert client.get("/api/v1/potholes?bbox=76.6,8.9,76.5,8.8").status_code == 400
    assert (
        client.get("/api/v1/potholes?bbox=-180,-90,180,90").status_code == 400
    )
    assert client.get("/api/v1/potholes?bbox=a,b,c,d").status_code == 400


def test_pothole_detail_road_and_verified_contract(client, seeded):
    target = public_id(seeded["potholes"][0])
    response = client.get("/api/v1/potholes/{0}".format(target))
    assert response.status_code == 200
    body = response.get_json()

    assert body["id"] == target
    assert body["report_count"] == 5
    assert body["road"]["name"] == "MC Road"
    assert body["road"]["number"] == "SH 1"
    assert body["road"]["pincode"] == "691001"
    assert body["road"]["authority"].startswith("Kerala PWD")
    assert body["project"]["contractor"] == "Example Infrastructure Ltd"
    assert body["project"]["verification_status"] == "verified"
    assert body["project"]["source_name"] == "Kerala eTendering"
    assert body["project"]["source_url"].startswith("https://")
    assert len(body["related"]) == 1

    numeric = client.get("/api/v1/potholes/{0}".format(seeded["potholes"][0]))
    assert numeric.status_code == 200
    assert numeric.get_json()["id"] == target


def test_unverified_contract_is_flagged_and_unknown_contractor_hidden(client, seeded):
    response = client.get("/api/v1/potholes/{0}".format(public_id(seeded["potholes"][2])))
    assert response.status_code == 200
    body = response.get_json()
    assert body["project"]["verification_status"] == "unknown"
    assert body["project"]["contractor"] is None
    assert body["road"]["name"] == "Kollam Beach Road"


def test_missing_road_and_invalid_ids(client, seeded):
    body = client.get("/api/v1/potholes/{0}".format(public_id(seeded["potholes"][3]))).get_json()
    assert body["road"] is None
    assert body["project"] is None

    assert client.get("/api/v1/potholes/not-an-id").status_code == 404
    assert client.get("/api/v1/potholes/PH-999999").status_code == 404
    assert client.get("/api/v1/roads/999999").status_code == 404


def test_nearby_radius_and_ordering(client, seeded):
    response = client.get("/api/v1/potholes/nearby?lat=8.8932&lng=76.6141&radius_km=1&limit=50")
    assert response.status_code == 200
    body = response.get_json()
    assert body["meta"]["count"] == 2
    assert body["potholes"][0]["distance_m"] <= body["potholes"][1]["distance_m"]
    assert body["potholes"][0]["id"] == public_id(seeded["potholes"][0])

    invalid = client.get("/api/v1/potholes/nearby?lat=200&lng=76&radius_km=1")
    assert invalid.status_code == 400


def test_recent_ledger_search_since_and_pagination(client, seeded):
    response = client.get("/api/v1/potholes/recent?limit=2&offset=0")
    assert response.status_code == 200
    body = response.get_json()
    assert body["meta"]["total"] == 4
    assert len(body["potholes"]) == 2

    search = client.get("/api/v1/potholes/recent?q=691001").get_json()
    assert search["meta"]["total"] == 2

    search_road = client.get("/api/v1/potholes/recent?q=Beach").get_json()
    assert search_road["meta"]["total"] == 1

    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    today = client.get("/api/v1/potholes/recent?since={0}".format(quote(since))).get_json()
    assert today["meta"]["total"] == 2

    public_search = client.get("/api/v1/potholes/recent?q={0}".format(public_id(seeded["potholes"][2])))
    assert public_search.get_json()["meta"]["total"] == 1

    bad_since = client.get("/api/v1/potholes/recent?since=not-a-date")
    assert bad_since.status_code == 400


def test_road_endpoint(client, seeded):
    response = client.get("/api/v1/roads/{0}".format(seeded["road"]))
    assert response.status_code == 200
    body = response.get_json()
    assert body["road"]["name"] == "MC Road"
    assert body["project"]["contractor"] == "Example Infrastructure Ltd"
    assert body["meta"]["pothole_count"] == 2


def test_public_api_is_read_only(client):
    assert client.post("/api/v1/potholes").status_code == 405
    assert client.put("/api/v1/potholes").status_code == 405
    assert client.delete("/api/v1/potholes/PH-000001").status_code == 405
    assert client.post("/api/v1/internal/reports", json={}).status_code == 401


def test_invalid_geocode_input(client):
    for value in ("", "12345", "012345", "abcdef", "6910011"):
        response = client.get("/api/v1/geocode?pincode={0}".format(value))
        assert response.status_code == 400


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or []

    def json(self):
        return self._payload


def test_geocode_success_and_cache(client, monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(params)
        return FakeResponse(
            200,
            [
                {
                    "lat": "8.8932",
                    "lon": "76.6141",
                    "display_name": "Kollam, Kerala, India",
                }
            ],
        )

    monkeypatch.setattr("services.geocoding.requests.get", fake_get)
    response = client.get("/api/v1/geocode?pincode=691001")
    assert response.status_code == 200
    body = response.get_json()
    assert body["pincode"] == "691001"
    assert body["latitude"] == 8.8932
    assert body["source"]
    assert len(calls) == 1

    cached = client.get("/api/v1/geocode/pincode/691001")
    assert cached.status_code == 200
    assert len(calls) == 1


def test_geocode_not_found_and_upstream_failure(client, monkeypatch):
    monkeypatch.setattr(
        "services.geocoding.requests.get",
        lambda *args, **kwargs: FakeResponse(200, []),
    )
    assert client.get("/api/v1/geocode?pincode=690518").status_code == 404

    monkeypatch.setattr(
        "services.geocoding.requests.get",
        lambda *args, **kwargs: FakeResponse(503, []),
    )
    assert client.get("/api/v1/geocode?pincode=690519").status_code == 502

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("services.geocoding.requests.get", timeout)
    assert client.get("/api/v1/geocode?pincode=690520").status_code == 504


def test_ingest_requires_key_and_valid_payload(client):
    assert client.post("/api/v1/internal/reports", json={}).status_code == 401
    assert (
        client.post(
            "/api/v1/internal/reports",
            json={"report_id": "x"},
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )
    response = client.post(
        "/api/v1/internal/reports",
        json={"report_id": "x"},
        headers={"Authorization": "Bearer test-ingest-key"},
    )
    assert response.status_code == 400


def test_ingest_creates_and_deduplicates_canonical_pothole(client, app, seeded):
    headers = {"Authorization": "Bearer test-ingest-key"}
    first = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-report-1",
            "latitude": 8.8933,
            "longitude": 76.6142,
            "confidence": 0.9,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert first.status_code == 200
    body = first.get_json()
    assert body["created"] is False
    canonical_id = body["pothole_id"]

    second = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-report-2",
            "latitude": 8.89331,
            "longitude": 76.61421,
            "confidence": 0.97,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert second.status_code == 200
    assert second.get_json()["pothole_id"] == canonical_id

    with app.app_context():
        pothole = db.session.get(CanonicalPothole, parse_public_id(canonical_id))
        assert pothole.location_metadata is not None
        assert pothole.location_metadata.status == "pending"

    detail = client.get("/api/v1/potholes/{0}".format(canonical_id)).get_json()
    assert detail["report_count"] == 7
    assert detail["id"] == canonical_id

    duplicate = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-report-1",
            "latitude": 8.8933,
            "longitude": 76.6142,
        },
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json()["duplicate_report"] is True

    with app.app_context():
        assert CanonicalPothole.query.count() == 4
        assert DetectionReport.query.filter_by(report_id="android-report-2").count() == 1


def test_ingest_new_pothole_and_validation(client, seeded):
    headers = {"Authorization": "Bearer test-ingest-key"}
    response = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-new-1",
            "latitude": 8.95,
            "longitude": 76.70,
            "confidence": 0.72,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.get_json()["created"] is True

    bad_confidence = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-bad-1",
            "latitude": 8.95,
            "longitude": 76.70,
            "confidence": 1.5,
        },
        headers=headers,
    )
    assert bad_confidence.status_code == 400

    future = client.post(
        "/api/v1/internal/reports",
        json={
            "report_id": "android-future",
            "latitude": 8.95,
            "longitude": 76.70,
            "observed_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert future.status_code == 400


def test_maptiler_parser_extracts_only_provider_fields():
    payload = {
        "features": [
            {
                "id": "address.123",
                "text": "Engineering College Road",
                "place_type": ["address"],
                "properties": {"kind": "street"},
                "feature_tags": {"highway": "residential"},
                "context": [
                    {"id": "postal_code.689121", "text": "689 121"},
                    {"id": "place.1", "text": "Chengannur"},
                    {"id": "county.2", "text": "Chengannur"},
                    {"id": "subregion.3", "text": "Alappuzha"},
                    {"id": "region.4", "text": "Kerala"},
                    {"id": "country.5", "text": "India"},
                ],
            }
        ]
    }

    result = _parse_maptiler(payload)

    assert result.road_name == "Engineering College Road"
    assert result.road_number is None
    assert result.classification == "residential"
    assert result.locality == "Chengannur"
    assert result.pincode == "689121"
    assert result.district == "Alappuzha"
    assert result.administrative_area == "Chengannur"
    assert result.state == "Kerala"
    assert result.country == "India"
    assert result.authority is None
    assert result.provider_place_id == "address.123"
    assert _parse_maptiler({"features": []}) is None


def test_reverse_geocoding_coordinate_validation():
    assert valid_coordinate(9.3177129, 76.6166554)
    assert not valid_coordinate(None, 76.6)
    assert not valid_coordinate(91, 76.6)
    assert not valid_coordinate(9.3, 181)


def test_public_api_exposes_pending_location_state(client, seeded):
    response = client.get("/api/v1/potholes/recent?limit=10")
    assert response.status_code == 200
    body = response.get_json()
    assert all(item["location"]["status"] == "pending" for item in body["potholes"])

    detail = client.get(
        "/api/v1/potholes/{0}".format(public_id(seeded["potholes"][0]))
    ).get_json()
    assert detail["location"]["status"] == "pending"
    assert detail["location"]["road_name"] is None
    assert detail["road"]["name"] == "MC Road"


def test_public_api_exposes_cached_location_metadata(client, app, seeded):
    pothole = db.session.get(CanonicalPothole, seeded["potholes"][0])
    db.session.add(
        PotholeLocationMetadata(
            canonical_pothole_id=pothole.id,
            status="resolved",
            road_name="Engineering College Road",
            classification="residential",
            locality="Chengannur",
            pincode="689121",
            district="Alappuzha",
            state="Kerala",
            country="India",
            administrative_area="Chengannur",
            provider="maptiler",
            geocoded_at=datetime.now(timezone.utc),
        )
    )
    db.session.commit()
    db.session.expire_all()

    detail = client.get(
        "/api/v1/potholes/{0}".format(public_id(seeded["potholes"][0]))
    ).get_json()
    location = detail["location"]
    assert location["status"] == "resolved"
    assert location["road_name"] == "Engineering College Road"
    assert location["pincode"] == "689121"
    assert location["district"] == "Alappuzha"
    assert location["administrative_area"] == "Chengannur"
    assert location["attribution"] == "MapTiler / OpenStreetMap contributors"

    search = client.get("/api/v1/potholes/recent?q=Engineering").get_json()
    assert search["meta"]["total"] == 1
    assert search["potholes"][0]["id"] == public_id(seeded["potholes"][0])

    locality = client.get("/api/v1/potholes/recent?q=Chengannur").get_json()
    assert locality["meta"]["total"] == 1
    assert locality["potholes"][0]["id"] == public_id(seeded["potholes"][0])


def test_enrich_pothole_caches_result_and_is_idempotent(app, seeded, monkeypatch):
    calls = []

    def fake_reverse_geocode(latitude, longitude):
        calls.append((latitude, longitude))
        return ReverseGeocodeResult(
            road_name="Engineering College Road",
            classification="residential",
            locality="Chengannur",
            pincode="689121",
            district="Alappuzha",
            state="Kerala",
            country="India",
            administrative_area="Chengannur",
            provider_place_id="address.123",
        )

    monkeypatch.setattr(
        "services.reverse_geocoding.reverse_geocode", fake_reverse_geocode
    )

    with app.app_context():
        pothole = db.session.get(CanonicalPothole, seeded["potholes"][0])
        metadata = enrich_pothole(pothole)
        assert metadata.status == "resolved"
        assert metadata.road_name == "Engineering College Road"
        assert metadata.district == "Alappuzha"
        assert metadata.attempt_count == 1
        assert metadata.geocoded_at is not None

        again = enrich_pothole(pothole)
        assert again.id == metadata.id
        assert len(calls) == 1


def test_no_result_uses_long_retry_window(app, seeded, monkeypatch):
    monkeypatch.setattr(
        "services.reverse_geocoding.reverse_geocode", lambda *args: None
    )

    with app.app_context():
        pothole = db.session.get(CanonicalPothole, seeded["potholes"][0])
        before = datetime.now(timezone.utc)
        metadata = enrich_pothole(pothole)

        assert metadata.status == "failed"
        assert metadata.last_error == "no_result"
        retry_at = metadata.next_retry_at
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        delay = (retry_at - before).total_seconds()
        assert 604700 <= delay <= 604900
