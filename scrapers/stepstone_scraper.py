"""
StepStone.de job scraper. Searches by keywords and location.
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
from scrapers.base_scraper import get_session, fetch_url

logger = get_scraper_logger()

BASE_URL = "https://www.stepstone.de"


def _search_url(keyword: str, location: str) -> str:
    params = {"q": keyword, "li": location}
    return f"{BASE_URL}/5/ergebnisliste.html?{urllib.parse.urlencode(params)}"


def _parse_list_page(html: str, source: str) -> list[dict]:
    jobs = []
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("[data-job-id]") or soup.select("article[data-at='job-item']") or soup.select(".results-list__item")
    for card in cards[:25]:
        try:
            link_el = card.select_one("a[href*='/stellenangebote']") or card.select_one("a[data-at='job-link']") or card.select_one("h2 a, a[href]")
            title_el = card.select_one("h2") or card.select_one("[data-at='job-title']")
            company_el = card.select_one("[data-at='job-company']") or card.select_one(".company-name")
            location_el = card.select_one("[data-at='job-location']") or card.select_one(".job-location")
            if not link_el:
                continue
            href = link_el.get("href") or ""
            if href.startswith("/"):
                href = BASE_URL + href
            title = (title_el or link_el).get_text(strip=True)
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


def _fetch_description(url: str, session: requests.Session) -> str:
    r = fetch_url(url, session=session, delay_before=1.0)
    if not r:
        return ""
    soup = BeautifulSoup(r.text, "lxml")
    div = soup.select_one("[data-at='job-description']") or soup.select_one(".job-description") or soup.select_one("article")
    if div:
        return div.get_text(separator=" ", strip=True)[:8000]
    return ""


def scrape_stepstone(keywords: list, locations: list, max_per_combination: int = 15) -> list[dict]:
    """Run StepStone search; return list of job dicts."""
    session = get_session()
    seen = set()
    all_jobs = []
    for keyword in keywords:
        for location in locations:
            url = _search_url(keyword, location)
            logger.info("StepStone search: %s @ %s", keyword, location)
            r = fetch_url(url, session=session, delay_before=1.0)
            if not r:
                continue
            jobs = _parse_list_page(r.text, "stepstone")
            for j in jobs:
                if j["url"] in seen:
                    continue
                seen.add(j["url"])
                if j["url"] and not j.get("description"):
                    j["description"] = _fetch_description(j["url"], session)
                    time.sleep(1.2)
                all_jobs.append(j)
            time.sleep(2.0)
    logger.info("StepStone scraped %d jobs", len(all_jobs))
    return all_jobs
