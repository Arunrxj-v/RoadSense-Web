-- Reference schema for PostgreSQL + PostGIS.
-- The authoritative, idempotent migration is backend/schema.py (run via
-- `flask --app wsgi:app init-db`). This file is provided for DBA review.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS road_projects (
  id SERIAL PRIMARY KEY,
  project_name VARCHAR(255),
  tender_id VARCHAR(128),
  work_order_ref VARCHAR(128),
  authority VARCHAR(255),
  contractor_name VARCHAR(255),
  work_year INTEGER,
  awarded_at DATE,
  source_name VARCHAR(255),
  source_url VARCHAR(1024),
  verification_status VARCHAR(32) NOT NULL DEFAULT 'unknown',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS road_segments (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  road_number VARCHAR(64),
  locality VARCHAR(255),
  pincode VARCHAR(6),
  authority VARCHAR(255),
  classification VARCHAR(128),
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  geometry_geojson TEXT,
  geom geometry(LineString, 4326),
  project_id INTEGER REFERENCES road_projects(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS canonical_potholes (
  id SERIAL PRIMARY KEY,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  geom geometry(Point, 4326),
  geog geography(Point, 4326),
  report_count INTEGER NOT NULL DEFAULT 1,
  confidence DOUBLE PRECISION,
  severity VARCHAR(16),
  status VARCHAR(24) NOT NULL DEFAULT 'open',
  first_detected_at TIMESTAMPTZ NOT NULL,
  last_detected_at TIMESTAMPTZ NOT NULL,
  road_id INTEGER REFERENCES road_segments(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS detection_reports (
  id SERIAL PRIMARY KEY,
  report_id VARCHAR(64) NOT NULL UNIQUE,
  canonical_pothole_id INTEGER NOT NULL REFERENCES canonical_potholes(id),
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  gps_accuracy_m DOUBLE PRECISION,
  confidence DOUBLE PRECISION,
  observed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_road_segments_geom ON road_segments USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geom ON canonical_potholes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geog ON canonical_potholes USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_last_detected ON canonical_potholes (last_detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_road ON canonical_potholes (road_id);
CREATE INDEX IF NOT EXISTS idx_detection_reports_canonical ON detection_reports (canonical_pothole_id, observed_at DESC);
