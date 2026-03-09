"""
Daily workflow: scrape -> parse -> location -> salary -> relevance -> generate Anschreiben + interview brief -> save to DB.
No automatic submission; user confirms before marking as 'applied'.
"""
import json
import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_config import get_applications_logger, get_scraper_logger, get_error_logger
from database.database_manager import init_db, insert_job, get_by_company_role
from processing.job_parser import parse_jobs
from processing.location_filter import filter_jobs_by_location
from processing.salary_filter import filter_jobs_by_salary
from processing.job_relevance_filter import filter_jobs_by_relevance
from processing.pdf_extractor import get_profile_text
from ai_modules.anschreiben_generator import generate_and_save_anschreiben
from ai_modules.interview_brief_generator import generate_and_save_interview_brief

logger = get_applications_logger()
err_log = get_error_logger()
CONFIG_DIR = PROJECT_ROOT / "config"
PREFS_PATH = CONFIG_DIR / "job_preferences.json"


def _load_prefs():
    with open(PREFS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _run_scrapers():
    """Run all scrapers and return combined raw job list."""
    from scrapers.indeed_scraper import scrape_indeed
    from scrapers.stepstone_scraper import scrape_stepstone
    from scrapers.hidden_job_scraper import scrape_hidden_jobs
    from scrapers.company_job_discovery import scrape_company_career_pages
    from scrapers.linkedin_scraper import scrape_linkedin

    prefs = _load_prefs()
    keywords = prefs.get("search_keywords", ["IT Support"])
    locations = prefs.get("locations", ["Kerpen", "Elsdorf", "Sindorf"])
    boards = prefs.get("job_boards", ["indeed", "stepstone"])

    all_raw = []
    if "indeed" in boards:
        try:
            all_raw.extend(scrape_indeed(keywords, locations, max_jobs_per_keyword=15))
        except Exception as e:
            err_log.exception("Indeed scraper failed: %s", e)
    if "stepstone" in boards:
        try:
            all_raw.extend(scrape_stepstone(keywords, locations, max_per_combination=10))
        except Exception as e:
            err_log.exception("StepStone scraper failed: %s", e)
    if "linkedin" in boards:
        try:
            all_raw.extend(scrape_linkedin(keywords, locations, max_jobs=10))
        except Exception as e:
            err_log.exception("LinkedIn scraper failed: %s", e)
    try:
        all_raw.extend(scrape_hidden_jobs(max_results_per_query=5))
    except Exception as e:
        err_log.exception("Hidden job scraper failed: %s", e)
    try:
        all_raw.extend(scrape_company_career_pages(max_companies=30))
    except Exception as e:
        err_log.exception("Company career scraper failed: %s", e)

    return all_raw


def run_daily(skip_scrape: bool = False, raw_jobs: list = None):
    """
    Execute full pipeline. If skip_scrape=True, pass raw_jobs from previous run or empty list.
    """
    init_db()
    if not skip_scrape and raw_jobs is None:
        raw_jobs = _run_scrapers()
    elif raw_jobs is None:
        raw_jobs = []

    jobs = parse_jobs(raw_jobs)
    logger.info("Parsed %d jobs", len(jobs))

    jobs = filter_jobs_by_location(jobs)
    logger.info("After location filter: %d", len(jobs))

    jobs = filter_jobs_by_salary(jobs)
    logger.info("After salary filter: %d", len(jobs))

    profile_text = get_profile_text()
    jobs = filter_jobs_by_relevance(jobs, profile_text=profile_text)
    logger.info("After relevance filter: %d", len(jobs))

    for j in jobs:
        company = j.get("company") or "Unbekannt"
        role = j.get("title") or j.get("role") or "Stelle"
        existing = get_by_company_role(company, role)
        if existing:
            logger.info("Skip duplicate: %s - %s", company, role)
            continue
        try:
            generate_and_save_anschreiben(j, profile_text=profile_text)
            generate_and_save_interview_brief(j)
            insert_job(
                company=company,
                role=role,
                location=j.get("location"),
                source=j.get("source"),
                salary_estimate=j.get("salary_estimate"),
                date_found=date.isoformat(date.today()),
                notes=j.get("relevance_flag"),
            )
        except Exception as e:
            err_log.exception("Failed to process job %s - %s: %s", company, role, e)
    logger.info("Daily run finished. Applications prepared; confirm manually before submitting.")
