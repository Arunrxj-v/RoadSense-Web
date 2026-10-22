"""PostGIS-first spatial helpers with a portable SQLite fallback.

Production queries use geometry/geography columns and GiST indexes created by
``schema.py``. The fallback exists so the API can be developed and tested on a
laptop without a GIS server; it is not intended for production scale.
"""
import math

from flask import current_app
from sqlalchemy import text

from db import db
from models import CanonicalPothole, RoadSegment

EARTH_RADIUS_M = 6371008.8


def is_postgres():
    try:
        return db.engine.dialect.name == "postgresql"
    except Exception:
        return False


def haversine_m(lat1, lng1, lat2, lng2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))


def pothole_bbox_filter(query, min_lat, min_lng, max_lat, max_lng):
    if is_postgres():
        return query.filter(
            text(
                "canonical_potholes.geom && "
                "ST_MakeEnvelope(:bbox_min_lng, :bbox_min_lat, "
                ":bbox_max_lng, :bbox_max_lat, 4326)"
            )
        ).params(
            bbox_min_lng=min_lng,
            bbox_min_lat=min_lat,
            bbox_max_lng=max_lng,
            bbox_max_lat=max_lat,
        )
    return query.filter(
        CanonicalPothole.latitude >= min_lat,
        CanonicalPothole.latitude <= max_lat,
        CanonicalPothole.longitude >= min_lng,
        CanonicalPothole.longitude <= max_lng,
    )


def nearby_filter_and_order(query, lat, lng, radius_m):
    if is_postgres():
        point_sql = "ST_SetSRID(ST_MakePoint(:near_lng, :near_lat), 4326)::geography"
        distance_sql = "ST_Distance(canonical_potholes.geog, {point})".format(
            point=point_sql
        )
        query = query.filter(
            text(
                "ST_DWithin(canonical_potholes.geog, {point}, :near_radius)".format(
                    point=point_sql
                )
            )
        ).params(near_lat=lat, near_lng=lng, near_radius=radius_m)
        return query, text(distance_sql).bindparams(near_lat=lat, near_lng=lng)

    # SQLite: coarse degree box, then exact filter in Python by the caller.
    lat_delta = radius_m / 111320.0
    lng_delta = radius_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    query = query.filter(
        CanonicalPothole.latitude >= lat - lat_delta,
        CanonicalPothole.latitude <= lat + lat_delta,
        CanonicalPothole.longitude >= lng - lng_delta,
        CanonicalPothole.longitude <= lng + lng_delta,
    )
    return query, None


def find_canonical_near(lat, lng, radius_m, cutoff):
    query = CanonicalPothole.query.filter(CanonicalPothole.last_detected_at >= cutoff)
    if is_postgres():
        point_sql = "ST_SetSRID(ST_MakePoint(:match_lng, :match_lat), 4326)::geography"
        query = query.filter(
            text(
                "ST_DWithin(canonical_potholes.geog, {point}, :match_radius)".format(
                    point=point_sql
                )
            )
        ).params(match_lat=lat, match_lng=lng, match_radius=radius_m)
        query = query.order_by(
            text(
                "ST_Distance(canonical_potholes.geog, {point})".format(point=point_sql)
            ).bindparams(match_lat=lat, match_lng=lng)
        )
        return query.first()

    lat_delta = radius_m / 111320.0
    lng_delta = radius_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    candidates = query.filter(
        CanonicalPothole.latitude >= lat - lat_delta,
        CanonicalPothole.latitude <= lat + lat_delta,
        CanonicalPothole.longitude >= lng - lng_delta,
        CanonicalPothole.longitude <= lng + lng_delta,
    ).all()
    best = None
    best_distance = None
    for candidate in candidates:
        distance = haversine_m(lat, lng, candidate.latitude, candidate.longitude)
        if distance <= radius_m and (best_distance is None or distance < best_distance):
            best = candidate
            best_distance = distance
    return best


def match_road(lat, lng, radius_m=None):
    """Return the nearest road segment within the configured tolerance."""
    radius_m = radius_m or current_app.config["ROAD_MATCH_RADIUS_M"]
    if is_postgres():
        query = RoadSegment.query.filter(
            RoadSegment.geometry_geojson.isnot(None),
            text(
                "road_segments.geom IS NOT NULL AND ST_DWithin("
                "road_segments.geom::geography, "
                "ST_SetSRID(ST_MakePoint(:road_lng, :road_lat), 4326)::geography, "
                ":road_radius)"
            ),
        ).params(road_lat=lat, road_lng=lng, road_radius=radius_m)
        query = query.order_by(
            text(
                "ST_Distance(road_segments.geom::geography, "
                "ST_SetSRID(ST_MakePoint(:road_lng, :road_lat), 4326)::geography)"
            ).bindparams(road_lat=lat, road_lng=lng)
        )
        return query.first()

    roads = RoadSegment.query.filter(
        RoadSegment.latitude.isnot(None), RoadSegment.longitude.isnot(None)
    ).all()
    best = None
    best_distance = None
    for road in roads:
        distance = haversine_m(lat, lng, road.latitude, road.longitude)
        if distance <= radius_m and (best_distance is None or distance < best_distance):
            best = road
            best_distance = distance
    return best
