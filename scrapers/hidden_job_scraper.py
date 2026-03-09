"""
Hidden job market: Google Custom Search for site-restricted queries.
E.g. site:jobs.personio.de "IT Support" Kerpen, site:boards.greenhouse.io ...
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from log_config import get_scraper_logger
from scrapers.base_scraper import fetch_url

logger = get_scraper_logger()
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_queries() -> list:
    prefs_path = CONFIG_DIR / "job_preferences.json"
    if not prefs_path.is_file():
        return []
    with open(prefs_path, encoding="utf-8") as f:
        return json.load(f).get("hidden_job_queries", [])


def _google_cse_search(query: str, api_key: str, cse_id: str, start: int = 1) -> list:
    """Call Google Custom Search JSON API. Returns list of result items."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "start": start, "num": 10}
    r = fetch_url(f"{url}?{urlencode(params)}", delay_before=0.5)
    if not r:
        return []
    try:
        data = r.json()
        return data.get("items") or []
    except Exception as e:
        logger.warning("Google CSE parse error: %s", e)
        return []


def _item_to_job(item: dict) -> dict:
    title = item.get("title") or ""
    link = item.get("link") or ""
    snippet = item.get("snippet") or ""
    return {
        "title": title,
        "company": "",
        "location": "",
        "url": link,
        "description": snippet,
        "source": "hidden_job",
        "posted_date": "",
    }


def scrape_hidden_jobs(max_results_per_query: int = 10) -> list:
    """
    Run configured hidden job queries via Google Custom Search API.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID in config/.env. Without them, returns [].
    """
    from dotenv import load_dotenv
    load_dotenv(CONFIG_DIR / ".env")
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        logger.info("Hidden job scraper: GOOGLE_API_KEY or GOOGLE_CSE_ID not set; skipping.")
        return []

    queries = _load_queries()
    if not queries:
        return []

    seen_urls = set()
    all_jobs = []
    for q in queries:
        logger.info("Hidden job query: %s", q[:60])
        items = _google_cse_search(q, api_key, cse_id)
        for item in items:
            j = _item_to_job(item)
            if j["url"] in seen_urls:
                continue
            seen_urls.add(j["url"])
            all_jobs.append(j)
        time.sleep(1.5)

    logger.info("Hidden job scraper found %d jobs", len(all_jobs))
    return all_jobs
