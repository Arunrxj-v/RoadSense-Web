"""Authenticated ingestion endpoint for the Android sensing fleet.

The public website cannot call these routes. They exist so the existing
Phase 1 Android observations can be deduplicated server-side into canonical
potholes without changing the on-device detection pipeline.
"""
import hmac
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from db import db
from models import CanonicalPothole, DetectionReport
from services.location_enrichment import (
    enqueue_pothole_enrichment,
    ensure_metadata,
)
from services.serializers import iso_utc
from services.spatial import find_canonical_near, match_road

internal_api = Blueprint("internal_api", __name__)


def error(message, status=400):
    return jsonify({"error": {"message": message, "status": status}}), status


def _authorized():
    configured = current_app.config.get("INGEST_API_KEY")
    if not configured:
        return False
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    return bool(token) and hmac.compare_digest(token, configured)


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_time(value):
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("observed_at must be an ISO-8601 timestamp.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@internal_api.post("/internal/reports")
def ingest_report():
    if not current_app.config.get("INGEST_API_KEY"):
        return error("Report ingestion is not configured.", 503)
    if not _authorized():
        return error("Not authorised.", 401)

    payload = request.get_json(silent=True) or {}
    required = ("report_id", "latitude", "longitude")
    missing = [field for field in required if payload.get(field) is None]
    if missing:
        return error("Missing required fields: {0}.".format(", ".join(missing)))

    report_id = str(payload["report_id"]).strip()
    if not report_id or len(report_id) > 64:
        return error("report_id must be 1-64 characters.")
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (TypeError, ValueError):
        return error("latitude and longitude must be numbers.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return error("latitude or longitude is out of range.")

    try:
        observed_at = _parse_time(payload.get("observed_at"))
    except ValueError as exc:
        return error(str(exc))
    if observed_at > datetime.now(timezone.utc) + timedelta(minutes=10):
        return error("observed_at cannot be in the future.")

    confidence = payload.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return error("confidence must be a number between 0 and 1.")
        if not 0 <= confidence <= 1:
            return error("confidence must be between 0 and 1.")

    accuracy = payload.get("gps_accuracy_m")
    if accuracy is not None:
        try:
            accuracy = float(accuracy)
        except (TypeError, ValueError):
            return error("gps_accuracy_m must be a number.")

    existing_report = DetectionReport.query.filter_by(report_id=report_id).first()
    if existing_report:
        return (
            jsonify(
                {
                    "created": False,
                    "duplicate_report": True,
                    "pothole_id": existing_report.canonical_pothole.public_id,
                }
            ),
            200,
        )

    cutoff = observed_at - timedelta(days=current_app.config["DEDUPE_WINDOW_DAYS"])
    canonical = find_canonical_near(
        latitude,
        longitude,
        current_app.config["DEDUPE_RADIUS_M"],
        cutoff,
    )
    created = False

    if canonical is None:
        severity = None
        if confidence is not None:
            severity = (
                "severe" if confidence >= 0.85 else "moderate" if confidence >= 0.7 else "low"
            )
        road = match_road(latitude, longitude)
        canonical = CanonicalPothole(
            latitude=latitude,
            longitude=longitude,
            report_count=1,
            confidence=confidence,
            severity=severity,
            status="open",
            first_detected_at=observed_at,
            last_detected_at=observed_at,
            road_id=road.id if road else None,
        )
        db.session.add(canonical)
        db.session.flush()
        created = True
    else:
        canonical.report_count = (canonical.report_count or 0) + 1
        canonical.first_detected_at = min(_as_utc(canonical.first_detected_at), observed_at)
        canonical.last_detected_at = max(_as_utc(canonical.last_detected_at), observed_at)
        if confidence is not None and (
            canonical.confidence is None or confidence > canonical.confidence
        ):
            canonical.confidence = confidence
            canonical.severity = (
                "severe"
                if confidence >= 0.85
                else "moderate"
                if confidence >= 0.7
                else "low"
            )
        if canonical.road_id is None:
            road = match_road(latitude, longitude)
            if road:
                canonical.road_id = road.id

    report = DetectionReport(
        report_id=report_id,
        canonical_pothole_id=canonical.id,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_m=accuracy,
        confidence=confidence,
        observed_at=observed_at,
    )
    ensure_metadata(canonical)
    db.session.add(report)
    db.session.commit()
    try:
        enqueue_pothole_enrichment(canonical.id)
    except Exception:
        current_app.logger.exception(
            "Could not enqueue location enrichment for pothole %s",
            canonical.public_id,
        )

    return (
        jsonify(
            {
                "created": created,
                "duplicate_report": False,
                "pothole_id": canonical.public_id,
                "report_count": canonical.report_count,
                "first_detected_at": iso_utc(canonical.first_detected_at),
                "last_detected_at": iso_utc(canonical.last_detected_at),
            }
        ),
        201 if created else 200,
    )
