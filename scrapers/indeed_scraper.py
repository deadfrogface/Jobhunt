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
    Run Indeed search for each keyword x location. Returns list of standard job dicts.
    """
    session = get_session()
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
