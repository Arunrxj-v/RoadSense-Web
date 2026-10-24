"""Public JSON serializers.

Only fields needed by the public map and information pages are exposed.
Internal ids, database credentials, raw sensor data and detection imagery are
deliberately never serialized.
"""
from datetime import datetime, timezone


def iso_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def road_summary(road):
    if road is None:
        return None
    return {
        "id": road.id,
        "name": road.name,
        "number": road.road_number,
        "locality": road.locality,
        "pincode": road.pincode,
        "authority": road.authority,
        "classification": road.classification,
    }


def road_detail(road):
    if road is None:
        return None
    data = road_summary(road)
    data["latitude"] = road.latitude
    data["longitude"] = road.longitude
    data["geometry_available"] = bool(road.geometry_geojson)
    return data


def _location_attribution(provider):
    if provider == "maptiler":
        return "MapTiler / OpenStreetMap contributors"
    if provider == "nominatim":
        return "OpenStreetMap contributors"
    return None


def location_summary(metadata):
    """Public reverse-geocoded metadata, including lookup lifecycle state."""
    if metadata is None:
        return {
            "status": "pending",
            "road_name": None,
            "road_number": None,
            "classification": None,
            "locality": None,
            "pincode": None,
            "district": None,
            "state": None,
            "country": None,
            "authority": None,
            "administrative_area": None,
            "suburb": None,
            "municipality": None,
            "operator": None,
            "provider": None,
            "attribution": None,
            "geocoded_at": None,
        }
    return {
        "status": metadata.status or "pending",
        "road_name": metadata.road_name,
        "road_number": metadata.road_number,
        "classification": metadata.classification,
        "locality": metadata.locality,
        "pincode": metadata.pincode,
        "district": metadata.district,
        "state": metadata.state,
        "country": metadata.country,
        "authority": metadata.authority,
        "administrative_area": metadata.administrative_area,
        "suburb": metadata.suburb,
        "municipality": metadata.municipality,
        "operator": metadata.operator,
        "provider": metadata.provider,
        "attribution": _location_attribution(metadata.provider),
        "geocoded_at": iso_utc(metadata.geocoded_at),
    }


def project_public(project):
    """Expose contract provenance exactly as stored, never inferred.

    The UI is responsible for labelling ``verification_status``. A contractor
    name is only emitted when a source-backed record contains one.
    """
    if project is None:
        return None
    status = project.verification_status or "unknown"
    has_source = bool(
        (project.source_name and project.source_name.strip())
        or (project.source_url and project.source_url.strip())
    )
    # A record cannot be presented as verified without provenance.
    if status == "verified" and not has_source:
        status = "unknown"
    contractor_present = bool(project.contractor_name and project.contractor_name.strip())
    contractor_visible = contractor_present and status in {"verified", "unverified"}
    return {
        "name": project.project_name,
        "tender_id": project.tender_id,
        "work_order_ref": project.work_order_ref,
        "authority": project.authority,
        "contractor": project.contractor_name if contractor_visible else None,
        "work_year": project.work_year,
        "awarded_at": project.awarded_at.isoformat() if project.awarded_at else None,
        "source_name": project.source_name,
        "source_url": project.source_url,
        "verification_status": status,
    }


def pothole_summary(pothole):
    return {
        "id": pothole.public_id,
        "latitude": round(pothole.latitude, 7),
        "longitude": round(pothole.longitude, 7),
        "report_count": pothole.report_count,
        "confidence": round(pothole.confidence, 3) if pothole.confidence is not None else None,
        "severity": pothole.severity,
        "status": pothole.status,
        "first_detected_at": iso_utc(pothole.first_detected_at),
        "last_detected_at": iso_utc(pothole.last_detected_at),
        "road": road_summary(pothole.road),
        "location": location_summary(pothole.location_metadata),
    }


def research_public(run):
    if run is None:
        return {
            "status": "none",
            "match": None,
            "confidence": "none",
            "contractor": None,
            "work_title": None,
            "authority": None,
            "tender_number": None,
            "work_reference": None,
            "source_url": None,
            "source_title": None,
            "evidence": None,
            "reason": None,
            "researched_at": None,
        }
    if run.status in {"pending", "running"}:
        return {
            "status": run.status,
            "match": None,
            "confidence": "none",
            "contractor": None,
            "work_title": None,
            "authority": None,
            "tender_number": None,
            "work_reference": None,
            "source_url": None,
            "source_title": None,
            "evidence": None,
            "reason": None,
            "researched_at": None,
        }
    if run.status == "failed":
        return {
            "status": "failed",
            "match": False,
            "confidence": "none",
            "contractor": None,
            "work_title": None,
            "authority": None,
            "tender_number": None,
            "work_reference": None,
            "source_url": None,
            "source_title": None,
            "evidence": None,
            "reason": "Research could not be completed. Cached road metadata remains available.",
            "researched_at": iso_utc(run.completed_at),
        }
    confidence = run.confidence if run.confidence in {"high", "medium"} else "none"
    matched = bool(run.match and confidence != "none")
    return {
        "status": "completed",
        "match": matched,
        "confidence": confidence if matched else "none",
        "contractor": run.contractor if matched else None,
        "work_title": run.work_title if matched else None,
        "authority": run.authority if matched else None,
        "tender_number": run.tender_number if matched else None,
        "work_reference": run.work_reference if matched else None,
        "source_url": run.source_url if matched else None,
        "source_title": run.source_title if matched else None,
        "evidence": run.evidence if matched else None,
        "reason": run.reason,
        "researched_at": iso_utc(run.completed_at),
    }


def research_debug_payload(run):
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "research_key": run.research_key,
        "match": run.match,
        "confidence": run.confidence,
        "contractor": run.contractor,
        "work_title": run.work_title,
        "authority": run.authority,
        "tender_number": run.tender_number,
        "work_reference": run.work_reference,
        "source_url": run.source_url,
        "source_title": run.source_title,
        "evidence": run.evidence,
        "reason": run.reason,
        "error": run.error,
        "model": run.model,
        "queries": run.queries_json or [],
        "query_count": run.query_count,
        "result_count": run.result_count,
        "fetched_source_count": run.fetched_source_count,
        "selected_source_count": run.selected_source_count,
        "search_ms": run.search_ms,
        "fetch_ms": run.fetch_ms,
        "ollama_ms": run.ollama_ms,
        "total_ms": run.total_ms,
        "started_at": iso_utc(run.started_at),
        "completed_at": iso_utc(run.completed_at),
        "sources": [
            {
                "query": source.search_query,
                "rank": source.rank,
                "title": source.title,
                "url": source.url,
                "domain": source.domain,
                "tier": source.tier,
                "snippet": source.snippet,
                "fetch_status": source.fetch_status,
                "fetched": source.fetched,
                "selected": source.selected,
                "text_chars": source.text_chars,
                "error": source.error,
            }
            for source in (run.sources or [])
        ],
    }


def pothole_detail(pothole, related=None, research=None):
    data = pothole_summary(pothole)
    data["road"] = road_detail(pothole.road)
    project = pothole.road.project if pothole.road else None
    data["project"] = project_public(project)
    data["research"] = research_public(research)
    data["related"] = [pothole_summary(item) for item in (related or [])]
    return data


def meta_payload(count, latest, generated_at):
    return {
        "pothole_count": count,
        "latest_detection_at": iso_utc(latest),
        "generated_at": iso_utc(generated_at or datetime.now(timezone.utc)),
    }
