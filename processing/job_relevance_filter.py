"""
Filter jobs by relevance to the user's qualifications (Lebenslauf + Arbeitszeugnisse).
Uses OpenAI to classify: relevant, relevant_with_review, not_relevant.
"""
import json
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_config import get_filter_logger
from processing.pdf_extractor import get_profile_text
from ai_modules.llm_client import get_client

logger = get_filter_logger()


def classify_relevance(job: dict[str, Any], profile_text: str) -> str:
    """
    Return one of: 'relevant', 'relevant_with_review', 'not_relevant'.
    relevant_with_review: job fits but has some requirements the user doesn't have (growth potential).
    """
    if not profile_text.strip():
        logger.warning("No profile text (Lebenslauf/Arbeitszeugnisse); marking job as relevant_with_review")
        return "relevant_with_review"

    title = job.get("title") or job.get("role") or ""
    company = job.get("company") or ""
    desc = (job.get("description") or "")[:4000]

    prompt = f"""Du bist ein Karriere-Berater. Bewerte, ob die folgende Stelle zum Bewerberprofil passt.

STELLE:
Titel: {title}
Unternehmen: {company}
Beschreibung (Auszug):
{desc}

BEWERBERPROFIL (aus Lebenslauf und Arbeitszeugnissen):
{profile_text[:6000]}

Antworte mit genau einem der drei Werte:
- relevant: Der Bewerber erfüllt die Anforderungen (Skills, Erfahrung, Ausbildung) gut.
- relevant_with_review: Der Bewerber passt grundsätzlich, es fehlen aber einige Anforderungen mit sinnvollem Lernpotenzial; zur manuellen Prüfung.
- not_relevant: Der Bewerber passt nicht (z.B. völlig andere Branche, fehlende Grundqualifikation)."""

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Antworte nur mit einem der drei Wörter: relevant, relevant_with_review, not_relevant. Kein anderer Text."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=20,
        )
        content = (resp.choices[0].message.content or "").strip().lower()
        if "relevant_with_review" in content:
            return "relevant_with_review"
        if "not_relevant" in content:
            return "not_relevant"
        return "relevant"
    except Exception as e:
        logger.exception("OpenAI relevance check failed: %s", e)
        return "relevant_with_review"


def filter_jobs_by_relevance(jobs: list[dict[str, Any]], profile_text: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Keep only jobs that are 'relevant' or 'relevant_with_review'.
    Attach 'relevance' and 'relevance_flag' (for review) to each job.
    """
    if profile_text is None:
        profile_text = get_profile_text()
    result = []
    for j in jobs:
        relevance = classify_relevance(j, profile_text)
        if relevance == "not_relevant":
            logger.info("Filtered out (not_relevant): %s at %s", j.get("role"), j.get("company"))
            continue
        j = dict(j)
        j["relevance"] = relevance
        j["relevance_flag"] = "review" if relevance == "relevant_with_review" else None
        result.append(j)
    return result
