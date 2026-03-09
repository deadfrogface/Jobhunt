#!/usr/bin/env python3
"""
AI Job Hunter - Entry point.
Usage:
  python main.py --daily        Run full daily workflow (scrape, filter, generate, save).
  python main.py --scrape-only  Only run scrapers, no filters or AI.
  python main.py --filter-only  Load jobs from data/jobs/latest.json (if present), run filters only.

Beim ersten Start mit --daily oder --filter-only wird geprüft, ob
- ein gültiger OPENAI_API_KEY in config/.env gesetzt ist und
- config/lebenslauf.pdf und config/arbeitszeugnisse.pdf vorhanden sind.

Falls nicht, fragt ein Setup-Dialog nach diesen Angaben, bevor der Lauf startet.
"""
import argparse
import json
import os
import sys
from getpass import getpass
from pathlib import Path
from shutil import copyfile

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_basic_setup() -> None:
    """Interactive setup for OPENAI_API_KEY and required PDFs.

    - If OPENAI_API_KEY is missing or placeholder, ask once and write to config/.env.
    - If config/lebenslauf.pdf or config/arbeitszeugnisse.pdf are missing, offer to copy from a user-provided path.
    """
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    env_path = config_dir / ".env"

    # Load existing .env content
    env_lines: list[str] = []
    if env_path.is_file():
        env_lines = env_path.read_text(encoding="utf-8").splitlines()

    def _get_env_value(name: str) -> str:
        # Prefer process env, then .env content
        val = os.environ.get(name)
        if val:
            return val
        for line in env_lines:
            if line.strip().startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
        return ""

    current_key = _get_env_value("OPENAI_API_KEY")
    if not current_key or current_key == "your-openai-api-key-here":
        print("OPENAI_API_KEY ist noch nicht gesetzt oder ist nur ein Platzhalter.")
        choice = input("Möchtest du jetzt deinen OpenAI-API-Key eintragen? [J/n]: ").strip().lower() or "j"
        if choice.startswith("j"):
            new_key = getpass("Bitte deinen OpenAI-API-Key eingeben (Eingabe wird nicht angezeigt): ").strip()
            if new_key:
                # Update or append in env_lines
                updated = False
                for i, line in enumerate(env_lines):
                    if line.strip().startswith("OPENAI_API_KEY="):
                        env_lines[i] = f"OPENAI_API_KEY={new_key}"
                        updated = True
                        break
                if not updated:
                    env_lines.append(f"OPENAI_API_KEY={new_key}")
                env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
                print("OPENAI_API_KEY in config/.env gespeichert.")
            else:
                print("Kein Key eingegeben, versuche weiter mit vorhandener Konfiguration.")

    # Ensure Lebenslauf and Arbeitszeugnisse PDFs
    lebenslauf_path = config_dir / "lebenslauf.pdf"
    arbeitszeugnisse_path = config_dir / "arbeitszeugnisse.pdf"

    if not lebenslauf_path.is_file():
        print("Es wurde noch kein 'lebenslauf.pdf' in config/ gefunden.")
        src = input("Pfad zu deinem Lebenslauf-PDF (leer lassen zum Überspringen): ").strip()
        if src:
            try:
                copyfile(src, lebenslauf_path)
                print(f"Lebenslauf nach {lebenslauf_path} kopiert.")
            except Exception as exc:
                print(f"Konnte Lebenslauf nicht kopieren: {exc}")

    if not arbeitszeugnisse_path.is_file():
        print("Es wurde noch kein 'arbeitszeugnisse.pdf' in config/ gefunden.")
        src = input("Pfad zu deinen Arbeitszeugnissen-PDF (leer lassen zum Überspringen): ").strip()
        if src:
            try:
                copyfile(src, arbeitszeugnisse_path)
                print(f"Arbeitszeugnisse nach {arbeitszeugnisse_path} kopiert.")
            except Exception as exc:
                print(f"Konnte Arbeitszeugnisse nicht kopieren: {exc}")


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

    # For AI-powered runs, ensure that key and PDFs are configured
    if args.filter_only or args.daily:
        _ensure_basic_setup()

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
