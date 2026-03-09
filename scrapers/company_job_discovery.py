"""
Discover jobs from local company career pages. Reads company list from data/companies/companies.csv
Format: company_name,career_page_url (or name,url,location).
"""
import csv
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from log_config import get_scraper_logger
from scrapers.base_scraper import get_session, fetch_url

logger = get_scraper_logger()
COMPANIES_DIR = PROJECT_ROOT / "data" / "companies"
COMPANIES_CSV = COMPANIES_DIR / "companies.csv"


def _load_company_list() -> list[dict[str, str]]:
    """Load companies from CSV: name, url (and optional location)."""
    rows = []
    if not COMPANIES_CSV.is_file():
        logger.info("No %s found; create it with columns: company_name,career_page_url[,location]", COMPANIES_CSV)
        return rows
    with open(COMPANIES_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("company_name") or row.get("name") or "").strip()
            url = (row.get("career_page_url") or row.get("url") or "").strip()
            if name and url:
                rows.append({
                    "company": name,
                    "url": url,
                    "location": (row.get("location") or "").strip(),
                })
    return rows


def _extract_job_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
    """Heuristic: find links that look like job postings (e.g. /job, /stellenangebot, /careers/..., /position)."""
    job_keywords = ["/job", "/stellen", "/career", "/position", "/vacancy", "/angebot", "/karriere"]
    links = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        if any(kw in full.lower() for kw in job_keywords) or "stellenangebot" in full.lower():
            title = a.get_text(strip=True) or "Job"
            links.append((full, title))
    return links[:30]


def _scrape_career_page(company: str, url: str, session) -> list[dict[str, Any]]:
    """Fetch career page and extract job links; optionally fetch each for description."""
    r = fetch_url(url, session=session, delay_before=1.0)
    if not r:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    job_links = _extract_job_links(soup, url)
    jobs = []
    for job_url, title in job_links:
        jobs.append({
            "title": title,
            "company": company,
            "location": "",
            "url": job_url,
            "description": "",
            "source": "company_career",
            "posted_date": "",
        })
    return jobs


def scrape_company_career_pages(max_companies: int = 50) -> list[dict[str, Any]]:
    """Scrape jobs from configured company career pages."""
    companies = _load_company_list()[:max_companies]
    if not companies:
        return []
    session = get_session()
    seen = set()
    all_jobs = []
    for c in companies:
        logger.info("Company career: %s", c["company"])
        jobs = _scrape_career_page(c["company"], c["url"], session)
        for j in jobs:
            if j["url"] in seen:
                continue
            seen.add(j["url"])
            if c.get("location"):
                j["location"] = c["location"]
            all_jobs.append(j)
        time.sleep(2.0)
    logger.info("Company career pages: %d jobs", len(all_jobs))
    return all_jobs
