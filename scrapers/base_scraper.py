"""
Base scraper: shared HTTP session, retry logic, User-Agent rotation, logging to logs/scraper.log.
"""
import time
import random
import sys
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from log_config import get_scraper_logger

logger = get_scraper_logger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_session(
    retries: int = 3,
    backoff: float = 1.0,
    timeout: float = 15.0,
) -> requests.Session:
    """Return a requests Session with retries and a random User-Agent."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


def fetch_url(
    url: str,
    session: Optional[requests.Session] = None,
    delay_before: float = 0.5,
) -> Optional[requests.Response]:
    """GET url with optional delay. Returns Response or None on failure."""
    if session is None:
        session = get_session()
    if delay_before > 0:
        time.sleep(delay_before)
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None


def standard_job_record(
    title: str,
    company: str,
    location: str,
    url: str,
    description: str,
    source: str,
    posted_date: str = "",
) -> dict:
    """Build a standard job dict for pipeline compatibility."""
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "source": source,
        "posted_date": posted_date,
    }
