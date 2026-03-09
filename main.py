#!/usr/bin/env python3
"""
AI Job Hunter - Entry point.
Usage:
  python main.py --daily       Run full daily workflow (scrape, filter, generate, save).
  python main.py --scrape-only  Only run scrapers and print job count (no DB/Anschreiben).
  python main.py --filter-only  Load jobs from data/jobs/latest.json (if present), run filters only.
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="AI Job Hunter - automated job discovery and application prep")
    parser.add_argument("--daily", action="store_true", help="Run full daily workflow")
    parser.add_argument("--scrape-only", action="store_true", help="Only run scrapers, no filters or AI")
    parser.add_argument("--filter-only", action="store_true", help="Run filters on data/jobs/latest.json if present")
    args = parser.parse_args()

    if args.scrape_only:
        from automation.application_assistant import _run_scrapers
        from processing.job_parser import parse_jobs
        raw = _run_scrapers()
        jobs = parse_jobs(raw)
        out_path = PROJECT_ROOT / "data" / "jobs" / "latest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"Scraped and parsed {len(jobs)} jobs; saved to {out_path}")
        return

    if args.filter_only:
        in_path = PROJECT_ROOT / "data" / "jobs" / "latest.json"
        if not in_path.is_file():
            print("No data/jobs/latest.json. Run --scrape-only first.")
            return
        with open(in_path, encoding="utf-8") as f:
            jobs = json.load(f)
        from processing.location_filter import filter_jobs_by_location
        from processing.salary_filter import filter_jobs_by_salary
        from processing.job_relevance_filter import filter_jobs_by_relevance
        jobs = filter_jobs_by_location(jobs)
        jobs = filter_jobs_by_salary(jobs)
        jobs = filter_jobs_by_relevance(jobs)
        print(f"After filters: {len(jobs)} jobs")
        return

    if args.daily:
        from automation.application_assistant import run_daily
        run_daily(skip_scrape=False)
        print("Daily run completed. Check outputs/anschreiben and outputs/interview_briefs. Confirm manually before submitting.")
        return

    parser.print_help()
    print("\nExample: python main.py --daily")


if __name__ == "__main__":
    main()
