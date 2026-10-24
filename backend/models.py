"""RoadSense relational schema.

canonical_potholes  one row per physical pothole (public map source)
pothole_location_metadata  cached reverse-geocoded address/road metadata
detection_reports   individual vehicle observations (never shown as markers)
road_segments       road metadata + optional PostGIS line geometry
road_projects       public work/contract records with provenance

The public web tier only reads the first, second, fourth and fifth tables.
"""
from datetime import datetime, timezone

from db import db


def utcnow():
    return datetime.now(timezone.utc)


class RoadProject(db.Model):
    __tablename__ = "road_projects"

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255))
    tender_id = db.Column(db.String(128))
    work_order_ref = db.Column(db.String(128))
    authority = db.Column(db.String(255))
    contractor_name = db.Column(db.String(255))
    work_year = db.Column(db.Integer)
    awarded_at = db.Column(db.Date)
    source_name = db.Column(db.String(255))
    source_url = db.Column(db.String(1024))
    verification_status = db.Column(db.String(32), nullable=False, default="unknown")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    segments = db.relationship("RoadSegment", back_populates="project", lazy="selectin")


class RoadSegment(db.Model):
    __tablename__ = "road_segments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True)
    road_number = db.Column(db.String(64), index=True)
    locality = db.Column(db.String(255), index=True)
    pincode = db.Column(db.String(6), index=True)
    authority = db.Column(db.String(255))
    classification = db.Column(db.String(128))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    geometry_geojson = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey("road_projects.id"), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    project = db.relationship("RoadProject", back_populates="segments", lazy="joined")
    potholes = db.relationship("CanonicalPothole", back_populates="road", lazy="noload")


class CanonicalPothole(db.Model):
    __tablename__ = "canonical_potholes"

    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)
    report_count = db.Column(db.Integer, nullable=False, default=1)
    confidence = db.Column(db.Float)
    severity = db.Column(db.String(16))
    status = db.Column(db.String(24), nullable=False, default="open", index=True)
    first_detected_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_detected_at = db.Column(
        db.DateTime(timezone=True), nullable=False, index=True
    )
    road_id = db.Column(db.Integer, db.ForeignKey("road_segments.id"), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    road = db.relationship("RoadSegment", back_populates="potholes", lazy="joined")
    reports = db.relationship(
        "DetectionReport", back_populates="canonical_pothole", lazy="noload"
    )
    location_metadata = db.relationship(
        "PotholeLocationMetadata",
        back_populates="pothole",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )
    research_runs = db.relationship(
        "PotholeResearchRun",
        back_populates="pothole",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    @property
    def public_id(self):
        return format_public_id(self.id)


class PotholeLocationMetadata(db.Model):
    """Cached reverse-geocoding result for one canonical pothole.

    Coordinates remain authoritative on ``canonical_potholes``. This table only
    stores provider-returned metadata and the lookup lifecycle state so public
    reads never call the geocoder.
    """

    __tablename__ = "pothole_location_metadata"

    id = db.Column(db.Integer, primary_key=True)
    canonical_pothole_id = db.Column(
        db.Integer,
        db.ForeignKey("canonical_potholes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)

    road_name = db.Column(db.String(255))
    road_number = db.Column(db.String(64))
    classification = db.Column(db.String(128))
    locality = db.Column(db.String(255))
    pincode = db.Column(db.String(16))
    district = db.Column(db.String(255))
    state = db.Column(db.String(255))
    country = db.Column(db.String(255))
    authority = db.Column(db.String(255))
    administrative_area = db.Column(db.String(255))
    suburb = db.Column(db.String(255))
    municipality = db.Column(db.String(255))
    operator = db.Column(db.String(255))

    provider = db.Column(db.String(32))
    provider_place_id = db.Column(db.String(128))
    geocoded_at = db.Column(db.DateTime(timezone=True))
    attempted_at = db.Column(db.DateTime(timezone=True))
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    next_retry_at = db.Column(db.DateTime(timezone=True), index=True)
    last_error = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    pothole = db.relationship("CanonicalPothole", back_populates="location_metadata")


class PotholeResearchRun(db.Model):
    __tablename__ = "pothole_research_runs"

    id = db.Column(db.Integer, primary_key=True)
    canonical_pothole_id = db.Column(
        db.Integer,
        db.ForeignKey("canonical_potholes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_key = db.Column(db.String(512), index=True)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    match = db.Column(db.Boolean)
    confidence = db.Column(db.String(16))
    contractor = db.Column(db.String(255))
    work_title = db.Column(db.String(512))
    authority = db.Column(db.String(255))
    tender_number = db.Column(db.String(128))
    work_reference = db.Column(db.String(128))
    source_url = db.Column(db.String(1024))
    source_title = db.Column(db.String(512))
    evidence = db.Column(db.Text)
    reason = db.Column(db.String(512))
    model = db.Column(db.String(128))
    queries_json = db.Column(db.JSON)
    query_count = db.Column(db.Integer, nullable=False, default=0)
    result_count = db.Column(db.Integer, nullable=False, default=0)
    fetched_source_count = db.Column(db.Integer, nullable=False, default=0)
    selected_source_count = db.Column(db.Integer, nullable=False, default=0)
    search_ms = db.Column(db.Integer)
    fetch_ms = db.Column(db.Integer)
    ollama_ms = db.Column(db.Integer)
    total_ms = db.Column(db.Integer)
    error = db.Column(db.String(64))
    reused_from_run_id = db.Column(db.Integer, db.ForeignKey("pothole_research_runs.id"))
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    pothole = db.relationship("CanonicalPothole", back_populates="research_runs")
    sources = db.relationship(
        "PotholeResearchSource",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PotholeResearchSource(db.Model):
    __tablename__ = "pothole_research_sources"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.Integer,
        db.ForeignKey("pothole_research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    search_query = db.Column(db.String(512))
    rank = db.Column(db.Integer)
    title = db.Column(db.String(512))
    url = db.Column(db.String(1024))
    domain = db.Column(db.String(255))
    tier = db.Column(db.Integer)
    snippet = db.Column(db.Text)
    fetch_status = db.Column(db.String(32))
    fetched = db.Column(db.Boolean, nullable=False, default=False)
    selected = db.Column(db.Boolean, nullable=False, default=False)
    text_chars = db.Column(db.Integer)
    error = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    run = db.relationship("PotholeResearchRun", back_populates="sources")


class DetectionReport(db.Model):
    __tablename__ = "detection_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    canonical_pothole_id = db.Column(
        db.Integer, db.ForeignKey("canonical_potholes.id"), nullable=False, index=True
    )
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    gps_accuracy_m = db.Column(db.Float)
    confidence = db.Column(db.Float)
    observed_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    canonical_pothole = db.relationship("CanonicalPothole", back_populates="reports")


def format_public_id(numeric_id):
    if numeric_id is None:
        return None
    return "PH-{0:06d}".format(int(numeric_id))


def parse_public_id(value):
    """Accept PH-000124, ph-124, or 124. Returns int or None."""
    if value is None:
        return None
    raw = str(value).strip().upper()
    if raw.startswith("PH-"):
        raw = raw[3:]
    elif raw.startswith("PH"):
        raw = raw[2:].lstrip("-")
    if not raw.isdigit():
        return None
    return int(raw)
