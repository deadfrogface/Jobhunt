"""
Generate a 1-page interview brief per job: company overview, role, key skills, salary, talking points, questions to ask.
Output: outputs/interview_briefs/<company>_<role>.txt
"""
import re
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_config import get_applications_logger
from ai_modules.llm_client import get_client

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "interview_briefs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger = get_applications_logger()


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")[:80]


def generate_interview_brief(job: dict[str, Any], company_info: Optional[str] = None) -> str:
    """
    Generate a concise 1-page interview briefing in German.
    """
    company = job.get("company") or "Unternehmen"
    role = job.get("title") or job.get("role") or "Stelle"
    location = job.get("location") or ""
    desc = (job.get("description") or "")[:4500]
    salary = job.get("salary_estimate")

    user_prompt = f"""Erstelle ein kurzes, einseitiges Interview-Briefing auf Deutsch für folgende Stelle.

Unternehmen: {company}
Rolle: {role}
Ort: {location}
{f'Geschätztes Gehalt: {salary} € brutto/Jahr' if salary else ''}

Stellenbeschreibung (Auszug):
{desc}
"""
    if company_info:
        user_prompt += f"\nZusätzliche Firmeninfos:\n{company_info[:1500]}\n"

    user_prompt += """
Struktur (knapp, Stichpunkte ok):
1. Firmenüberblick (Branche, Größe, Standort)
2. Produkte/Dienstleistungen
3. Rolle und Verantwortung
4. Wichtige Anforderungen/Skills
5. Warum sucht das Unternehmen (Vermutung)
6. Talking Points für das Gespräch
7. Sinnvolle Fragen an den Arbeitgeber
8. Evtl. aktuelle Unternehmensmeldungen (wenn aus Kontext erkennbar)

Halte das Briefing auf etwa eine Seite (max. 800 Wörter)."""

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Du erstellst prägnante Interview-Vorbereitungen auf Deutsch. Nur Fakten und klare Stichpunkte."},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.exception("Interview brief generation failed: %s", e)
        raise


def save_interview_brief(job: dict[str, Any], text: str) -> Path:
    """Save brief to outputs/interview_briefs/<company>_<role>.txt."""
    company = _sanitize_filename(job.get("company") or "company")
    role = _sanitize_filename(job.get("title") or job.get("role") or "role")
    path = OUTPUT_DIR / f"{company}_{role}.txt"
    path.write_text(text, encoding="utf-8")
    logger.info("Saved interview brief: %s", path)
    return path


def generate_and_save_interview_brief(
    job: dict[str, Any],
    company_info: Optional[str] = None,
) -> Path:
    """Generate and save; return path to file."""
    text = generate_interview_brief(job, company_info)
    return save_interview_brief(job, text)
