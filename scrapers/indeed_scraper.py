"""
Indeed.de job scraper. Searches by keywords and location (Elsdorf, Kerpen, Sindorf).
Rate-limit and respectful delays to reduce block risk.
"""
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from log_config import get_scraper_logger
from scrapers.base_scraper import get_session, fetch_url, standard_job_record

logger = get_scraper_logger()

BASE_URL = "https://de.indeed.com"


def _search_url(keyword: str, location: str, start: int = 0) -> str:
    params = {
        "q": keyword,
        "l": location,
        "start": start,
    }
    return f"{BASE_URL}/jobs?{urllib.parse.urlencode(params)}"


def _prepare_indeed_session(session: requests.Session) -> None:
    """Add headers/cookies to better mimic a logged-in browser session.

    If the user creates config/indeed_cookies.txt with a copied Cookie header
    from their own browser session, it will be attached here. This does not
    bypass fundamental blocking but can reduce 403 errors.
    """
    config_dir = PROJECT_ROOT / "config"
    cookies_file = config_dir / "indeed_cookies.txt"
    # Ensure referer and language headers are explicitly set
    session.headers.setdefault("Referer", BASE_URL + "/")
    session.headers.setdefault("Accept-Language", "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7")
    if cookies_file.is_file():
        try:
            cookie_value = cookies_file.read_text(encoding="utf-8").strip()
            if cookie_value:
                session.headers["Cookie"] = cookie_value
                logger.info("Using cookies from %s for Indeed requests.", cookies_file)
        except Exception as exc:
            logger.warning("Could not read Indeed cookies file %s: %s", cookies_file, exc)


def _parse_list_page(html: str, source: str) -> list[dict[str, Any]]:
    """Extract job cards from Indeed search results page. Selectors may need updates if Indeed changes layout."""
    jobs = []
    soup = BeautifulSoup(html, "lxml")
    # Indeed uses job cards with data-jk and sometimes data-jobkey
    cards = soup.select("[data-jk]") or soup.select(".job_seen_beacon") or soup.select(".jobsearch-ResultsList > li")
    for card in cards[:25]:
        try:
            link_el = card.select_one("a[href*='/viewjob']") or card.select_one("a[href*='/rc/clk']") or card.select_one("h2 a")
            title_el = card.select_one("h2") or card.select_one(".jobTitle")
            company_el = card.select_one("[data-testid='company-name']") or card.select_one(".companyName")
            location_el = card.select_one("[data-testid='text-location']") or card.select_one(".companyLocation")
            if not link_el or not title_el:
                continue
            href = link_el.get("href") or ""
            if href.startswith("/"):
                href = BASE_URL + href
            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else ""
            location_str = location_el.get_text(strip=True) if location_el else ""
            jobs.append({
                "title": title,
                "company": company,
                "location": location_str,
                "url": href,
                "description": "",
                "source": source,
                "posted_date": "",
            })
        except Exception as e:
            logger.debug("Skip card: %s", e)
    return jobs


def _fetch_job_description(url: str, session: requests.Session) -> str:
    """Fetch full job description from detail page."""
    r = fetch_url(url, session=session, delay_before=1.0)
    if not r:
        return ""
    soup = BeautifulSoup(r.text, "lxml")
    div = soup.select_one("#jobDescriptionText") or soup.select_one(".jobsearch-JobComponent-description")
    if div:
        return div.get_text(separator=" ", strip=True)[:8000]
    return ""


def scrape_indeed(
    keywords: list[str],
    locations: list[str],
    max_jobs_per_keyword: int = 20,
) -> list[dict[str, Any]]:
    """
    Run Indeed search for each keyword x location. Returns list of job dicts.

    Hinweis: Indeed setzt aggressive Bot-Protection ein. Dieser Scraper versucht,
    sich wie ein Browser zu verhalten und erlaubt optional eigene Cookies
    über config/indeed_cookies.txt. Wenn weiterhin 403-Fehler auftreten,
    kannst du Indeed in config/job_preferences.json aus den job_boards entfernen.
    """
    session = get_session()
    _prepare_indeed_session(session)
    seen_urls = set()
    all_jobs = []
    for keyword in keywords:
        for location in locations:
            url = _search_url(keyword, location)
            logger.info("Indeed search: %s @ %s", keyword, location)
            r = fetch_url(url, session=session, delay_before=1.0)
            if not r:
                continue
            jobs = _parse_list_page(r.text, "indeed")
            for j in jobs:
                if j["url"] in seen_urls:
                    continue
                seen_urls.add(j["url"])
                if j["url"] and not j.get("description"):
                    j["description"] = _fetch_job_description(j["url"], session)
                    time.sleep(1.2)
                all_jobs.append(j)
                if len(all_jobs) >= max_jobs_per_keyword * len(keywords) * len(locations):
                    break
            time.sleep(2.0)
        if len(all_jobs) >= max_jobs_per_keyword * len(keywords) * len(locations):
            break
    logger.info("Indeed scraped %d jobs", len(all_jobs))
    return all_jobs
