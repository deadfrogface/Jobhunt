"""
Normalize raw job data from scrapers into a unified structure.
Extracts plain text from HTML descriptions and standardizes field names.
"""
import re
from html import unescape
from typing import Any
from bs4 import BeautifulSoup


# Standard keys used across the pipeline
STANDARD_KEYS = [
    "title", "role", "company", "location", "url", "description",
    "source", "posted_date", "salary_estimate", "latitude", "longitude",
]


def html_to_text(html: str) -> str:
    """Convert HTML snippet to plain text."""
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_job(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Map raw scraper output to a standard job structure.
    Input may have: title, company, location, url, description, source, posted_date, etc.
    """
    out = {}
    # Title / role
    out["title"] = (raw.get("title") or raw.get("role") or "").strip()
    out["role"] = out["title"]
    out["company"] = (raw.get("company") or raw.get("employer") or "").strip()
    out["location"] = (raw.get("location") or raw.get("city") or raw.get("place") or "").strip()
    out["url"] = (raw.get("url") or raw.get("link") or "").strip()
    desc = raw.get("description") or raw.get("body") or ""
    if desc and ("<" in desc and ">" in desc):
        desc = html_to_text(desc)
    out["description"] = desc.strip() if isinstance(desc, str) else ""
    out["source"] = (raw.get("source") or "unknown").strip()
    out["posted_date"] = raw.get("posted_date") or raw.get("date") or ""
    out["salary_estimate"] = raw.get("salary_estimate")
    out["latitude"] = raw.get("latitude")
    out["longitude"] = raw.get("longitude")
    return out


def parse_jobs(raw_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a list of raw job dicts."""
    return [normalize_job(r) for r in raw_jobs]
