"""Idempotent database initialization.

PostgreSQL deployments receive real PostGIS point/line geometry, GiST spatial
indexes and sync triggers. SQLite development databases keep the same logical
schema with numeric coordinate columns.
"""
from sqlalchemy import text

from db import db

POSTGIS_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "ALTER TABLE canonical_potholes ADD COLUMN IF NOT EXISTS geom geometry(Point,4326)",
    "ALTER TABLE canonical_potholes ADD COLUMN IF NOT EXISTS geog geography(Point,4326)",
    "ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS geom geometry(LineString,4326)",
    """
    CREATE OR REPLACE FUNCTION roadsense_sync_pothole_point() RETURNS trigger AS $$
    BEGIN
      NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
      NEW.geog := NEW.geom::geography;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE OR REPLACE FUNCTION roadsense_sync_road_line() RETURNS trigger AS $$
    BEGIN
      IF NEW.geometry_geojson IS NOT NULL AND length(NEW.geometry_geojson) > 0 THEN
        NEW.geom := ST_SetSRID(ST_GeomFromGeoJSON(NEW.geometry_geojson), 4326);
      ELSE
        NEW.geom := NULL;
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_roadsense_pothole_point ON canonical_potholes",
    """
    CREATE TRIGGER trg_roadsense_pothole_point
    BEFORE INSERT OR UPDATE OF latitude, longitude ON canonical_potholes
    FOR EACH ROW EXECUTE FUNCTION roadsense_sync_pothole_point()
    """,
    "DROP TRIGGER IF EXISTS trg_roadsense_road_line ON road_segments",
    """
    CREATE TRIGGER trg_roadsense_road_line
    BEFORE INSERT OR UPDATE OF geometry_geojson ON road_segments
    FOR EACH ROW EXECUTE FUNCTION roadsense_sync_road_line()
    """,
    "UPDATE canonical_potholes SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), geog = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography WHERE geom IS NULL",
    "UPDATE road_segments SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geometry_geojson), 4326) WHERE geometry_geojson IS NOT NULL AND geom IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geom ON canonical_potholes USING GIST (geom)",
    "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geog ON canonical_potholes USING GIST (geog)",
    "CREATE INDEX IF NOT EXISTS idx_road_segments_geom ON road_segments USING GIST (geom)",
    "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_last_detected ON canonical_potholes (last_detected_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_road ON canonical_potholes (road_id)",
    "CREATE INDEX IF NOT EXISTS idx_detection_reports_canonical ON detection_reports (canonical_pothole_id, observed_at DESC)",
]


def init_database(app):
    from models import (  # noqa: F401
        DetectionReport,
        PotholeLocationMetadata,
        RoadProject,
        RoadSegment,
    )

    with app.app_context():
        is_postgres = db.engine.dialect.name == "postgresql"
        if is_postgres:
            with db.engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        db.create_all()
        if is_postgres:
            with db.engine.begin() as connection:
                for statement in POSTGIS_STATEMENTS[1:]:
                    connection.execute(text(statement))
        else:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_bbox "
                        "ON canonical_potholes (latitude, longitude)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_canonical_potholes_recent "
                        "ON canonical_potholes (last_detected_at DESC)"
                    )
                )
