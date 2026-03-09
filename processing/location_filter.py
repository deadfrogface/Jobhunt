"""
Filter jobs by geographic distance: only keep jobs within radius_km of Elsdorf, Kerpen, Sindorf.
Uses coordinates from config/locations_geo.json and geopy for distance calculation.
"""
import json
from pathlib import Path
from typing import Any, Optional

from geopy.distance import geodesic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
GEO_PATH = CONFIG_DIR / "locations_geo.json"
JOB_PREFS_PATH = CONFIG_DIR / "job_preferences.json"


def _load_geo() -> dict:
    with open(GEO_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_radius() -> float:
    with open(JOB_PREFS_PATH, encoding="utf-8") as f:
        prefs = json.load(f)
    return float(prefs.get("radius_km", 25))


def _get_reference_points() -> list[tuple[float, float]]:
    geo = _load_geo()
    return [(v["lat"], v["lon"]) for v in geo.values()]


def _coords_for_location(location_str: str) -> Optional[tuple[float, float]]:
    """Resolve location string (e.g. 'Kerpen', '50170 Kerpen', 'Köln') to (lat, lon)."""
    if not location_str or not location_str.strip():
        return None
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    except ImportError:
        return None
    geocoder = Nominatim(user_agent="ai-job-hunter")
    try:
        loc = geocoder.geocode(location_str, country_codes="de", timeout=5)
        if loc:
            return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None


def _extract_plz_or_city(text: str) -> Optional[str]:
    """Try to get a place name or PLZ from job location string for geocoding."""
    if not text:
        return None
    # German PLZ: 5 digits at start or standalone
    import re
    m = re.search(r"\b(5\d{4})\b", text)
    if m:
        return m.group(1) + " Germany"
    # Use first significant token as city name
    parts = [p.strip(".,") for p in text.split() if len(p) > 2]
    if parts:
        return parts[0] + " Germany" if "Germany" not in text else parts[0]
    return text.strip() + " Germany"


def passes_location_filter(
    job: dict[str, Any],
    radius_km: Optional[float] = None,
    include_without_location: Optional[bool] = None,
) -> bool:
    """
    Return True if job is within radius_km of any reference location (Elsdorf, Kerpen, Sindorf).
    job may have 'location' (str) or 'latitude'/'longitude' keys.
    """
    if radius_km is None:
        radius_km = _load_radius()
    if include_without_location is None:
        with open(JOB_PREFS_PATH, encoding="utf-8") as f:
            include_without_location = json.load(f).get("include_jobs_without_location", False)

    refs = _get_reference_points()

    # Prefer explicit coordinates
    lat = job.get("latitude")
    lon = job.get("longitude")
    if lat is not None and lon is not None:
        try:
            point = (float(lat), float(lon))
        except (TypeError, ValueError):
            point = None
    else:
        point = None

    if point is None:
        loc_str = job.get("location") or job.get("city") or ""
        loc_str = _extract_plz_or_city(loc_str) if loc_str else None
        if not loc_str:
            return include_without_location
        point = _coords_for_location(loc_str)
        if point is None:
            return include_without_location

    for ref in refs:
        if geodesic(point, ref).kilometers <= radius_km:
            return True
    return False


def filter_jobs_by_location(
    jobs: list[dict[str, Any]],
    radius_km: Optional[float] = None,
    include_without_location: Optional[bool] = None,
) -> list[dict[str, Any]]:
    """Return only jobs that pass the location filter."""
    return [j for j in jobs if passes_location_filter(j, radius_km, include_without_location)]
