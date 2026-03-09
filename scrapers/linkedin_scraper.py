"""
LinkedIn job scraper. Public job search pages only; no login.
Scraping LinkedIn is fragile and may violate ToS; use sparingly and with rate limits.
"""
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from log_config import get_scraper_logger
from scrapers.base_scraper import get_session, fetch_url

logger = get_scraper_logger()

# Public job search URL (may redirect or require JS in practice)
BASE = "https://www.linkedin.com/jobs/search"


def _search_url(keyword: str, location: str) -> str:
    params = {"keywords": keyword, "location": location}
    return f"{BASE}?{urllib.parse.urlencode(params)}"


def scrape_linkedin(
    keywords: list[str],
    locations: list[str],
    max_jobs: int = 15,
) -> list[dict[str, Any]]:
    """
    Attempt to fetch LinkedIn job listings. LinkedIn often requires JS/login;
    this stub returns minimal results from public page if parseable, else empty list.
    """
    session = get_session()
    all_jobs = []
    try:
        for keyword in keywords:
            for location in locations:
                url = _search_url(keyword, location)
                logger.info("LinkedIn search: %s @ %s (public)", keyword, location)
                r = fetch_url(url, session=session, delay_before=2.0)
                if not r:
                    continue
                # LinkedIn renders many job cards via JS; HTML may have minimal content
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select(".base-card") or soup.select("[data-job-id]") or soup.select("li.job-result-card")
                for card in cards[:10]:
                    link = card.select_one("a[href*='/jobs/view']") or card.select_one("a.base-card__full-link")
                    title_el = card.select_one("h3") or card.select_one(".base-search-card__title")
                    company_el = card.select_one("h4") or card.select_one(".base-search-card__subtitle")
                    location_el = card.select_one(".job-search-card__location")
                    if link:
                        href = link.get("href") or ""
                        title = (title_el or link).get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else ""
                        loc = location_el.get_text(strip=True) if location_el else ""
                        all_jobs.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": href,
                            "description": "",
                            "source": "linkedin",
                            "posted_date": "",
                        })
                time.sleep(3.0)
                if len(all_jobs) >= max_jobs:
                    break
            if len(all_jobs) >= max_jobs:
                break
    except Exception as e:
        logger.warning("LinkedIn scraper error: %s", e)
    logger.info("LinkedIn scraped %d jobs", len(all_jobs))
    return all_jobs
