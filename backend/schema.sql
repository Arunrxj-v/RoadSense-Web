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

CREATE TABLE IF NOT EXISTS pothole_location_metadata (
  id SERIAL PRIMARY KEY,
  canonical_pothole_id INTEGER NOT NULL UNIQUE REFERENCES canonical_potholes(id) ON DELETE CASCADE,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  road_name VARCHAR(255),
  road_number VARCHAR(64),
  classification VARCHAR(128),
  locality VARCHAR(255),
  pincode VARCHAR(16),
  district VARCHAR(255),
  state VARCHAR(255),
  country VARCHAR(255),
  authority VARCHAR(255),
  administrative_area VARCHAR(255),
  suburb VARCHAR(255),
  municipality VARCHAR(255),
  operator VARCHAR(255),
  provider VARCHAR(32),
  provider_place_id VARCHAR(128),
  geocoded_at TIMESTAMPTZ,
  attempted_at TIMESTAMPTZ,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_retry_at TIMESTAMPTZ,
  last_error VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pothole_location_metadata_status ON pothole_location_metadata (status);
CREATE INDEX IF NOT EXISTS idx_pothole_location_metadata_next_retry ON pothole_location_metadata (next_retry_at);

CREATE TABLE IF NOT EXISTS pothole_research_runs (
  id SERIAL PRIMARY KEY,
  canonical_pothole_id INTEGER NOT NULL REFERENCES canonical_potholes(id) ON DELETE CASCADE,
  research_key VARCHAR(512),
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  match BOOLEAN,
  confidence VARCHAR(16),
  contractor VARCHAR(255),
  work_title VARCHAR(512),
  authority VARCHAR(255),
  tender_number VARCHAR(128),
  work_reference VARCHAR(128),
  source_url VARCHAR(1024),
  source_title VARCHAR(512),
  evidence TEXT,
  reason VARCHAR(512),
  model VARCHAR(128),
  queries_json JSONB,
  query_count INTEGER NOT NULL DEFAULT 0,
  result_count INTEGER NOT NULL DEFAULT 0,
  fetched_source_count INTEGER NOT NULL DEFAULT 0,
  selected_source_count INTEGER NOT NULL DEFAULT 0,
  search_ms INTEGER,
  fetch_ms INTEGER,
  ollama_ms INTEGER,
  total_ms INTEGER,
  error VARCHAR(64),
  reused_from_run_id INTEGER REFERENCES pothole_research_runs(id),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pothole_research_sources (
  id SERIAL PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES pothole_research_runs(id) ON DELETE CASCADE,
  search_query VARCHAR(512),
  rank INTEGER,
  title VARCHAR(512),
  url VARCHAR(1024),
  domain VARCHAR(255),
  tier INTEGER,
  snippet TEXT,
  fetch_status VARCHAR(32),
  fetched BOOLEAN NOT NULL DEFAULT false,
  selected BOOLEAN NOT NULL DEFAULT false,
  text_chars INTEGER,
  error VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pothole_research_runs_pothole ON pothole_research_runs (canonical_pothole_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pothole_research_runs_key ON pothole_research_runs (research_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pothole_research_runs_status ON pothole_research_runs (status);
CREATE INDEX IF NOT EXISTS idx_pothole_research_sources_run ON pothole_research_sources (run_id);

CREATE INDEX IF NOT EXISTS idx_road_segments_geom ON road_segments USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geom ON canonical_potholes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_geog ON canonical_potholes USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_last_detected ON canonical_potholes (last_detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_potholes_road ON canonical_potholes (road_id);
CREATE INDEX IF NOT EXISTS idx_detection_reports_canonical ON detection_reports (canonical_pothole_id, observed_at DESC);
