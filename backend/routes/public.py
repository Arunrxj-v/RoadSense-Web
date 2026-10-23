"""Read-only public API consumed by the RoadSense Vision website."""
import math
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import cast, func, or_, String
from sqlalchemy.orm import joinedload

from db import db
from models import (
    CanonicalPothole,
    PotholeLocationMetadata,
    RoadSegment,
    format_public_id,
    parse_public_id,
)
from services import geocoding
from services.serializers import (
    iso_utc,
    meta_payload,
    pothole_detail,
    pothole_summary,
    project_public,
    road_detail,
)
from services.spatial import (
    haversine_m,
    is_postgres,
    nearby_filter_and_order,
    pothole_bbox_filter,
)

public_api = Blueprint("public_api", __name__)


def error(message, status=400):
    return jsonify({"error": {"message": message, "status": status}}), status


def _parse_float(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("{0} must be a number.".format(name))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("{0} must be a finite number.".format(name))
    return number


def _validate_lat_lng(lat, lng):
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180 <= lng <= 180):
        raise ValueError("Longitude must be between -180 and 180.")


def _bbox_from_request():
    bbox = request.args.get("bbox")
    if bbox:
        parts = bbox.split(",")
        if len(parts) != 4:
            raise ValueError(
                "bbox must be min_longitude,min_latitude,max_longitude,max_latitude."
            )
        min_lng, min_lat, max_lng, max_lat = [_parse_float(p, "bbox") for p in parts]
    elif any(
        request.args.get(name) is not None
        for name in ("min_lat", "max_lat", "min_lng", "max_lng")
    ):
        try:
            min_lat = _parse_float(request.args["min_lat"], "min_lat")
            max_lat = _parse_float(request.args["max_lat"], "max_lat")
            min_lng = _parse_float(request.args["min_lng"], "min_lng")
            max_lng = _parse_float(request.args["max_lng"], "max_lng")
        except KeyError:
            raise ValueError("All four bounds are required.")
    else:
        raise ValueError("A bbox query parameter is required.")

    _validate_lat_lng(min_lat, min_lng)
    _validate_lat_lng(max_lat, max_lng)
    if min_lat >= max_lat or min_lng >= max_lng:
        raise ValueError("The bounding box minimums must be less than maximums.")
    if (max_lat - min_lat) * (max_lng - min_lng) > 400:
        raise ValueError("The requested bounding box is too large.")
    return min_lat, min_lng, max_lat, max_lng


def _apply_filters(query):
    since_days = request.args.get("since_days")
    if since_days:
        try:
            days = int(since_days)
        except ValueError:
            raise ValueError("since_days must be an integer.")
        if days < 0 or days > 3650:
            raise ValueError("since_days must be between 0 and 3650.")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(CanonicalPothole.last_detected_at >= cutoff)

    since = request.args.get("since")
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("since must be an ISO-8601 timestamp.")
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
        query = query.filter(CanonicalPothole.last_detected_at >= since_dt.astimezone(timezone.utc))

    status = request.args.get("status")
    if status:
        if status not in {"open", "under_repair", "repaired", "unknown"}:
            raise ValueError("Unknown status filter.")
        query = query.filter(CanonicalPothole.status == status)

    search = (request.args.get("q") or "").strip()
    if search:
        if len(search) > 120:
            raise ValueError("Search text is too long.")
        like = "%{0}%".format(search)
        numeric = parse_public_id(search)
        clauses = [
            RoadSegment.name.ilike(like),
            RoadSegment.road_number.ilike(like),
            RoadSegment.locality.ilike(like),
            RoadSegment.pincode.ilike(like),
            RoadSegment.authority.ilike(like),
            PotholeLocationMetadata.road_name.ilike(like),
            PotholeLocationMetadata.road_number.ilike(like),
            PotholeLocationMetadata.locality.ilike(like),
            PotholeLocationMetadata.pincode.ilike(like),
            PotholeLocationMetadata.district.ilike(like),
            PotholeLocationMetadata.state.ilike(like),
            PotholeLocationMetadata.authority.ilike(like),
            cast(CanonicalPothole.id, String).ilike(like),
        ]
        if numeric is not None:
            clauses.append(CanonicalPothole.id == numeric)
        query = (
            query.outerjoin(RoadSegment)
            .outerjoin(
                PotholeLocationMetadata,
                PotholeLocationMetadata.canonical_pothole_id == CanonicalPothole.id,
            )
            .filter(or_(*clauses))
        )
    return query


@public_api.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok"})
    except Exception:
        return error("The road condition service is unavailable.", 503)


@public_api.get("/meta")
def meta():
    count = CanonicalPothole.query.count()
    latest = db.session.query(func.max(CanonicalPothole.last_detected_at)).scalar()
    return jsonify(meta_payload(count, latest, datetime.now(timezone.utc)))


@public_api.get("/potholes")
def list_potholes():
    try:
        bbox = _bbox_from_request()
        query = CanonicalPothole.query.options(joinedload(CanonicalPothole.road))
        query = pothole_bbox_filter(query, *bbox)
        query = _apply_filters(query)
        total = query.order_by(None).count()

        default_limit = current_app.config["PUBLIC_DEFAULT_LIMIT"]
        max_limit = current_app.config["PUBLIC_MAX_LIMIT"]
        try:
            limit = max(1, min(max_limit, int(request.args.get("limit", default_limit))))
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            raise ValueError("limit and offset must be integers.")

        query = query.order_by(
            CanonicalPothole.last_detected_at.desc(), CanonicalPothole.id.desc()
        )
        rows = query.offset(offset).limit(limit).all()
        return jsonify(
            {
                "potholes": [pothole_summary(row) for row in rows],
                "meta": {
                    "count": len(rows),
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "bbox": {
                        "min_lat": bbox[0],
                        "min_lng": bbox[1],
                        "max_lat": bbox[2],
                        "max_lng": bbox[3],
                    },
                    "generated_at": iso_utc(datetime.now(timezone.utc)),
                },
            }
        )
    except ValueError as exc:
        return error(str(exc), 400)


@public_api.get("/potholes/recent")
def recent_potholes():
    """Paginated canonical-pothole ledger used by the Detections page."""
    try:
        query = CanonicalPothole.query.options(joinedload(CanonicalPothole.road))
        query = _apply_filters(query)
        total = query.order_by(None).count()

        try:
            limit = max(
                1,
                min(
                    current_app.config["PUBLIC_MAX_LIMIT"],
                    int(request.args.get("limit", 25)),
                ),
            )
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            raise ValueError("limit and offset must be integers.")

        rows = (
            query.order_by(
                CanonicalPothole.last_detected_at.desc(), CanonicalPothole.id.desc()
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        return jsonify(
            {
                "potholes": [pothole_summary(row) for row in rows],
                "meta": {
                    "count": len(rows),
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "generated_at": iso_utc(datetime.now(timezone.utc)),
                },
            }
        )
    except ValueError as exc:
        return error(str(exc), 400)


@public_api.get("/potholes/nearby")
def nearby_potholes():
    try:
        lat = _parse_float(request.args.get("lat"), "lat")
        lng = _parse_float(request.args.get("lng"), "lng")
        _validate_lat_lng(lat, lng)
        try:
            radius_km = float(request.args.get("radius_km", 2))
            limit = int(request.args.get("limit", 100))
        except (TypeError, ValueError):
            raise ValueError("radius_km and limit must be numbers.")
        if not (0.05 <= radius_km <= 50):
            raise ValueError("radius_km must be between 0.05 and 50.")
        limit = max(1, min(limit, 500))
    except ValueError as exc:
        return error(str(exc), 400)

    radius_m = radius_km * 1000.0
    query = CanonicalPothole.query.options(joinedload(CanonicalPothole.road))
    query, distance_order = nearby_filter_and_order(query, lat, lng, radius_m)
    if is_postgres():
        rows = query.order_by(distance_order).limit(limit).all()
    else:
        candidates = query.all()
        for row in candidates:
            row._near_distance = haversine_m(lat, lng, row.latitude, row.longitude)
        candidates = [r for r in candidates if r._near_distance <= radius_m]
        candidates.sort(key=lambda r: r._near_distance)
        rows = candidates[:limit]

    payload = []
    for row in rows:
        item = pothole_summary(row)
        item["distance_m"] = round(
            getattr(row, "_near_distance", None)
            or haversine_m(lat, lng, row.latitude, row.longitude),
            1,
        )
        payload.append(item)

    return jsonify(
        {
            "potholes": payload,
            "meta": {
                "count": len(payload),
                "center": {"latitude": lat, "longitude": lng},
                "radius_km": radius_km,
                "generated_at": iso_utc(datetime.now(timezone.utc)),
            },
        }
    )


@public_api.get("/potholes/<pothole_id>")
def get_pothole(pothole_id):
    numeric_id = parse_public_id(pothole_id)
    if numeric_id is None:
        return error("That pothole identifier is not valid.", 404)
    pothole = CanonicalPothole.query.options(
        joinedload(CanonicalPothole.road)
    ).filter(CanonicalPothole.id == numeric_id).first()
    if not pothole:
        return error("That pothole could not be found.", 404)

    related = []
    if pothole.road_id:
        related = (
            CanonicalPothole.query.filter(
                CanonicalPothole.road_id == pothole.road_id,
                CanonicalPothole.id != pothole.id,
            )
            .order_by(CanonicalPothole.last_detected_at.desc())
            .limit(4)
            .all()
        )
    return jsonify(pothole_detail(pothole, related))


@public_api.get("/roads/<int:road_id>")
def get_road(road_id):
    road = db.session.get(RoadSegment, road_id)
    if not road:
        return error("That road record could not be found.", 404)
    potholes = (
        CanonicalPothole.query.filter_by(road_id=road.id)
        .order_by(CanonicalPothole.last_detected_at.desc())
        .limit(current_app.config["PUBLIC_DETAIL_LIMIT"])
        .all()
    )
    return jsonify(
        {
            "road": road_detail(road),
            "project": project_public(road.project),
            "potholes": [pothole_summary(item) for item in potholes],
            "meta": {
                "pothole_count": CanonicalPothole.query.filter_by(
                    road_id=road.id
                ).count(),
                "generated_at": iso_utc(datetime.now(timezone.utc)),
            },
        }
    )


@public_api.get("/geocode")
def geocode():
    pincode = (request.args.get("pincode") or "").strip()
    return _geocode_response(pincode)


@public_api.get("/geocode/pincode/<pincode>")
def geocode_path(pincode):
    return _geocode_response(pincode.strip())


def _geocode_response(pincode):
    if not geocoding.valid_pincode(pincode):
        return error("Enter a valid 6-digit Indian PIN code.", 400)
    try:
        return jsonify(geocoding.resolve_pincode(pincode))
    except geocoding.GeocodeError as exc:
        return error(exc.message, exc.status)
