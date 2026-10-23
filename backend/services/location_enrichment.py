"""Cached reverse-geocoding lifecycle for canonical potholes.

The canonical coordinate is never changed. A lookup runs only when metadata is
missing or due for retry, and the result is cached in
``pothole_location_metadata`` so public page views do not call the provider.
"""
import threading
from datetime import datetime, timedelta, timezone

import click
from flask import current_app
from sqlalchemy import and_, or_

from db import db
from models import CanonicalPothole, PotholeLocationMetadata, parse_public_id, utcnow
from services import reverse_geocoding

_INFLIGHT = set()
_INFLIGHT_LOCK = threading.Lock()
_FIELDS = (
    "road_name",
    "road_number",
    "classification",
    "locality",
    "pincode",
    "district",
    "state",
    "country",
    "authority",
    "administrative_area",
    "suburb",
    "municipality",
    "operator",
)


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_metadata(pothole):
    if pothole.id is None:
        db.session.flush()
    metadata = pothole.location_metadata
    if metadata is None:
        metadata = PotholeLocationMetadata(
            canonical_pothole_id=pothole.id,
            status="pending",
        )
        db.session.add(metadata)
        pothole.location_metadata = metadata
    return metadata


def _retry_delay(attempt_count, error=None):
    if error is not None and error.retry_after_seconds is not None:
        return max(0, error.retry_after_seconds)
    base = current_app.config["REVERSE_GEOCODING_RETRY_BASE_SECONDS"]
    maximum = current_app.config["REVERSE_GEOCODING_RETRY_MAX_SECONDS"]
    exponent = min(max(attempt_count - 1, 0), 10)
    return min(base * (2 ** exponent), maximum)


def _finish_failure(metadata, error_code, next_retry_at):
    metadata.status = "failed"
    metadata.last_error = error_code
    metadata.next_retry_at = next_retry_at
    db.session.commit()
    current_app.logger.warning(
        "Reverse geocoding failed for pothole %s: %s",
        metadata.canonical_pothole_id,
        error_code,
    )


def enrich_pothole(pothole, force=False):
    metadata = ensure_metadata(pothole)
    now = utcnow()

    if not force:
        if metadata.status in {"resolved", "skipped"}:
            return metadata
        max_attempts = current_app.config["REVERSE_GEOCODING_MAX_ATTEMPTS"]
        if (metadata.attempt_count or 0) >= max_attempts:
            _finish_failure(metadata, "max_attempts", None)
            return metadata
        next_retry_at = _as_utc(metadata.next_retry_at)
        if next_retry_at and next_retry_at > now:
            return metadata

    if not reverse_geocoding.valid_coordinate(pothole.latitude, pothole.longitude):
        metadata.status = "skipped"
        metadata.last_error = "invalid_coordinates"
        metadata.next_retry_at = None
        db.session.commit()
        return metadata

    metadata.status = "pending"
    metadata.attempted_at = now
    metadata.attempt_count = (metadata.attempt_count or 0) + 1
    metadata.last_error = None
    metadata.next_retry_at = now + timedelta(
        seconds=_retry_delay(metadata.attempt_count)
    )
    db.session.commit()

    try:
        result = reverse_geocoding.reverse_geocode(
            pothole.latitude, pothole.longitude
        )
    except reverse_geocoding.ReverseGeocodeError as error:
        retry_at = None
        if error.retryable:
            retry_at = utcnow() + timedelta(
                seconds=_retry_delay(metadata.attempt_count, error)
            )
        _finish_failure(metadata, error.code, retry_at)
        return metadata
    except Exception:
        current_app.logger.exception(
            "Unexpected reverse geocoding error for pothole %s",
            metadata.canonical_pothole_id,
        )
        _finish_failure(
            metadata,
            "unexpected_error",
            utcnow() + timedelta(seconds=_retry_delay(metadata.attempt_count)),
        )
        return metadata

    if result is None:
        _finish_failure(
            metadata,
            "no_result",
            utcnow()
            + timedelta(
                seconds=current_app.config[
                    "REVERSE_GEOCODING_NO_RESULT_RETRY_SECONDS"
                ]
            ),
        )
        return metadata

    for field in _FIELDS:
        setattr(metadata, field, getattr(result, field, None))
    metadata.status = "resolved"
    metadata.provider = result.provider
    metadata.provider_place_id = result.provider_place_id
    metadata.geocoded_at = utcnow()
    metadata.next_retry_at = None
    metadata.last_error = None
    db.session.commit()
    return metadata


def enrich_pothole_by_id(pothole_id, force=False):
    pothole = db.session.get(CanonicalPothole, pothole_id)
    if pothole is None:
        return None
    return enrich_pothole(pothole, force=force)


def enqueue_pothole_enrichment(pothole_id):
    app = current_app._get_current_object()
    if app.config.get("TESTING") or not app.config.get("REVERSE_GEOCODING_ASYNC"):
        return
    with _INFLIGHT_LOCK:
        if pothole_id in _INFLIGHT:
            return
        _INFLIGHT.add(pothole_id)

    def run():
        try:
            with app.app_context():
                enrich_pothole_by_id(pothole_id)
        except Exception:
            app.logger.exception(
                "Background location enrichment failed for pothole %s", pothole_id
            )
        finally:
            with _INFLIGHT_LOCK:
                _INFLIGHT.discard(pothole_id)

    threading.Thread(
        target=run,
        daemon=True,
        name="roadsense-geocode-{0}".format(pothole_id),
    ).start()


def _candidate_ids(limit, retry_failed, force):
    now = utcnow()
    query = db.session.query(CanonicalPothole.id).outerjoin(
        PotholeLocationMetadata,
        PotholeLocationMetadata.canonical_pothole_id == CanonicalPothole.id,
    )
    if force:
        condition = or_(
            PotholeLocationMetadata.id.is_(None),
            PotholeLocationMetadata.status.in_(["pending", "resolved", "failed"]),
        )
    elif retry_failed:
        condition = or_(
            PotholeLocationMetadata.id.is_(None),
            PotholeLocationMetadata.status == "pending",
            and_(
                PotholeLocationMetadata.status == "failed",
                or_(
                    PotholeLocationMetadata.next_retry_at.is_(None),
                    PotholeLocationMetadata.next_retry_at <= now,
                ),
            ),
        )
    else:
        condition = or_(
            PotholeLocationMetadata.id.is_(None),
            PotholeLocationMetadata.status == "pending",
        )
    return [
        row[0]
        for row in query.filter(condition)
        .order_by(CanonicalPothole.last_detected_at.desc())
        .limit(limit)
        .all()
    ]


def register_cli(app):
    @app.cli.command("enrich-locations")
    @click.option("--limit", default=100, show_default=True)
    @click.option("--retry-failed", is_flag=True, help="Retry failed rows that are due.")
    @click.option("--force", is_flag=True, help="Re-geocode resolved rows too.")
    @click.option("--pothole", default=None, help="Only enrich one public pothole ID.")
    def enrich_locations(limit, retry_failed, force, pothole):
        """Populate cached reverse-geocoded metadata for existing potholes."""
        if pothole:
            numeric_id = parse_public_id(pothole)
            if numeric_id is None:
                raise click.ClickException("Invalid pothole identifier.")
            row = db.session.get(CanonicalPothole, numeric_id)
            if row is None:
                raise click.ClickException("Pothole not found.")
            metadata = enrich_pothole(row, force=force)
            click.echo(
                "{0}: {1}".format(
                    pothole, metadata.status if metadata else "not found"
                )
            )
            return

        ids = _candidate_ids(max(1, limit), retry_failed, force)
        if not ids:
            click.echo("No locations need enrichment.")
            return

        counts = {"resolved": 0, "failed": 0, "skipped": 0, "pending": 0}
        for pothole_id in ids:
            metadata = enrich_pothole_by_id(pothole_id, force=force)
            if metadata is not None:
                counts[metadata.status] = counts.get(metadata.status, 0) + 1

        click.echo(
            "Enriched {0} location(s): {1} resolved, {2} failed, {3} skipped, "
            "{4} pending.".format(
                len(ids),
                counts.get("resolved", 0),
                counts.get("failed", 0),
                counts.get("skipped", 0),
                counts.get("pending", 0),
            )
        )
