import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchTarget:
    pothole_id: int
    public_id: str
    road_name: str
    locality: str
    district: str
    state: str
    country: str
    pincode: str
    latitude: float
    longitude: float


def normalize_text(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", text).strip()


def normalize_key(value):
    text = normalize_text(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_target(pothole):
    metadata = pothole.location_metadata
    road_name = normalize_text(metadata.road_name if metadata else None)
    if not road_name:
        road_name = normalize_text(pothole.road.name if pothole.road else None)
    if not road_name:
        return None
    locality = normalize_text(metadata.locality if metadata else None)
    district = normalize_text(metadata.district if metadata else None)
    state = normalize_text(metadata.state if metadata else None)
    country = normalize_text(metadata.country if metadata else None)
    pincode = normalize_text(metadata.pincode if metadata else None)
    return ResearchTarget(
        pothole_id=pothole.id,
        public_id=pothole.public_id,
        road_name=road_name,
        locality=locality,
        district=district,
        state=state,
        country=country,
        pincode=pincode,
        latitude=pothole.latitude,
        longitude=pothole.longitude,
    )


def road_aliases(target):
    if target is None:
        return []
    road = normalize_text(target.road_name)
    key = normalize_key(road)
    if not key:
        return []
    aliases = [road]
    base = re.sub(r"\s+(road|rd|street|st)$", "", road, flags=re.IGNORECASE).strip()
    if base and normalize_key(base) != key:
        aliases.append(base)
    if "engineering college" in key:
        aliases.extend(
            [
                "Engineering College Back Road",
                "Road behind IHRD Engineering College",
                "IHRD Engineering College Road",
            ]
        )
    seen = set()
    result = []
    for alias in aliases:
        alias_key = normalize_key(alias)
        if alias_key and alias_key not in seen:
            seen.add(alias_key)
            result.append(normalize_text(alias))
    return result


def road_match_aliases(target):
    if target is None:
        return []
    base = re.sub(
        r"\s+(road|rd|street|st)$", "", normalize_text(target.road_name), flags=re.IGNORECASE
    ).strip()
    base_key = normalize_key(base)
    seen = set()
    aliases = []
    for alias in road_aliases(target):
        alias_key = normalize_key(alias)
        if not alias_key or alias_key == base_key or alias_key in seen:
            continue
        seen.add(alias_key)
        aliases.append(alias)
    return aliases


def build_research_key(target):
    if target is None:
        return None
    parts = [
        normalize_key(target.road_name),
        normalize_key(target.locality),
        normalize_key(target.district),
        normalize_key(target.state),
    ]
    return "|".join(part for part in parts if part)
