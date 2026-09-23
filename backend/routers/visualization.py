import json
import math
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException
from models.workstation import EnvironmentState, GeographyData, ObjectVisual
from propagate import gmst_rad, parse_utc

router = APIRouter()
DATA = Path(__file__).resolve().parents[1] / "data"


@router.get("/environment", response_model=EnvironmentState)
async def environment(utc: str | None = None) -> EnvironmentState:
    try:
        dt = parse_utc(utc)
    except ValueError as exc:
        raise HTTPException(422, "Invalid UTC") from exc
    # Low-precision solar ephemeris for lighting only, never an orbital state.
    days = dt.timestamp() / 86400 + 2440587.5 - 2451545.0
    mean_long = math.radians((280.460 + .9856474 * days) % 360)
    anomaly = math.radians((357.528 + .9856003 * days) % 360)
    longitude = mean_long + math.radians(1.915) * math.sin(anomaly) + math.radians(.020) * math.sin(2 * anomaly)
    obliquity = math.radians(23.439 - .0000004 * days)
    ra = math.atan2(math.cos(obliquity) * math.sin(longitude), math.cos(longitude))
    dec = math.asin(math.sin(obliquity) * math.sin(longitude))
    lon = ra - gmst_rad(dt)
    return EnvironmentState(utc=dt.isoformat().replace("+00:00", "Z"),
        sun_direction=[math.cos(dec)*math.cos(lon), math.sin(dec), math.cos(dec)*math.sin(lon)],
        illumination_model="Approximate solar ephemeris for visualization; static NASA surface/cloud composites")


# Verified object-image registry: both catalog ID AND name must match a known mission.
# Only well-identified, individually trackable spacecraft get a real photo/technical image.
# Large satellite constellations (Starlink, etc.) and debris fragments always fall back
# to the honest representative model — never a guessed or generic photograph.
VERIFIED_VISUALS: dict[str, dict] = {
    "20580": {"match": ("HST", "HUBBLE"), "kind": "photograph", "image_url": "/assets/hubble.jpg",
        "source_url": "https://esahubble.org/images/heic0908c/", "credit": "NASA / ESA · STS-125, 19 May 2009",
        "caption": "Hubble Space Telescope after release from Atlantis. Archival mission photograph, not a live image."},
    "25544": {"match": ("ISS", "ZARYA"), "kind": "photograph",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/STS-134_International_Space_Station_after_undocking.jpg/1280px-STS-134_International_Space_Station_after_undocking.jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:STS-134_International_Space_Station_after_undocking.jpg",
        "credit": "NASA · Photo ID S134-E-010137, 29 May 2011 (public domain)",
        "caption": "The International Space Station photographed from Endeavour (STS-134) during post-undocking separation."},
}


@router.get("/visuals/{object_id}", response_model=ObjectVisual)
async def object_visual(object_id: str, name: str = "") -> ObjectVisual:
    # Both catalog ID and mission name must match; no generic photograph guesses.
    entry = VERIFIED_VISUALS.get(object_id)
    if entry and any(token in name.upper() for token in entry["match"]):
        return ObjectVisual(object_id=object_id, kind=entry["kind"], image_url=entry["image_url"],
            source_url=entry["source_url"], credit=entry["credit"], caption=entry["caption"])
    return ObjectVisual(object_id=object_id, kind="representative", caption="Representative geometry only. Not a photograph, exact spacecraft design, or size estimate.")


@lru_cache(maxsize=3)
def geography_file(level: str) -> GeographyData:
    path = DATA / f"geography-{level}.json"
    if not path.exists():
        raise HTTPException(503, "Geography data unavailable")
    return GeographyData(**json.loads(path.read_text()))


@router.get("/geography/{level}", response_model=GeographyData)
async def geography(level: str) -> GeographyData:
    if level not in {"countries", "regions", "cities"}:
        raise HTTPException(404, "Unknown geography level")
    return geography_file(level)