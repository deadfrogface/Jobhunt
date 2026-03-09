"""
Generate truthful Anschreiben (cover letters) using only information from Lebenslauf and Arbeitszeugnisse.
Output: outputs/anschreiben/<company>_<role>.txt
"""
import re
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_config import get_applications_logger
from processing.pdf_extractor import get_profile_text
from ai_modules.llm_client import get_client

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "anschreiben"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger = get_applications_logger()


def _sanitize_filename(name: str) -> str:
    """Alphanumeric and underscores only for safe file names."""
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")[:80]


def generate_anschreiben(
    job: dict[str, Any],
    profile_text: Optional[str] = None,
) -> str:
    """
    Generate a truthful cover letter for the job. Returns the text.
    Only uses skills/experience/achievements from profile_text.
    """
    if profile_text is None:
        profile_text = get_profile_text()

    company = job.get("company") or "Unternehmen"
    role = job.get("title") or job.get("role") or "Stelle"
    desc = (job.get("description") or "")[:5000]

    system_prompt = """Du schreibst ein deutsches Anschreiben (Cover Letter) für eine Bewerbung.
WICHTIG: Erfinde NICHTS. Nutze nur Fakten aus dem Bewerberprofil (Lebenslauf und Arbeitszeugnisse).
Wenn die Stelle eine Anforderung nennt, die im Profil nicht vorkommt, formuliere ehrlich z.B.:
"Ich bin motiviert, mich in [Bereich] weiterzuentwickeln" oder "Ich freue mich darauf, meine Kenntnisse in [X] auszubauen."
Struktur: 1) Anrede, 2) Interesse am Unternehmen, 3) Relevante Erfahrung aus dem Profil, 4) Bezug zu den Anforderungen, 5) Schluss mit Bitte um Einladung."""

    user_prompt = f"""Stelle: {role}
Unternehmen: {company}

Ausschreibung (Auszug):
{desc}

Bewerberprofil (nur diese Fakten verwenden):
{profile_text[:7000]}

Schreibe das Anschreiben auf Deutsch, professionell und wahrheitsgemäß."""

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text
    except Exception as e:
        logger.exception("Anschreiben generation failed: %s", e)
        raise


def save_anschreiben(job: dict[str, Any], text: str) -> Path:
    """Save Anschreiben to outputs/anschreiben/<company>_<role>.txt. Returns the file path."""
    company = _sanitize_filename(job.get("company") or "company")
    role = _sanitize_filename(job.get("title") or job.get("role") or "role")
    filename = f"{company}_{role}.txt"
    path = OUTPUT_DIR / filename
    path.write_text(text, encoding="utf-8")
    logger.info("Saved Anschreiben: %s", path)
    return path


def generate_and_save_anschreiben(job: dict[str, Any], profile_text: Optional[str] = None) -> Path:
    """Generate and save; return path to file."""
    text = generate_anschreiben(job, profile_text)
    return save_anschreiben(job, text)
