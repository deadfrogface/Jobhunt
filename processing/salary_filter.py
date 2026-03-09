"""
Filter jobs by minimum gross yearly salary (default 37_000 EUR).
Uses: 1) direct extraction from text, 2) monthly-to-yearly conversion, 3) OpenAI estimation if missing.
"""
import re
import json
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
JOB_PREFS_PATH = CONFIG_DIR / "job_preferences.json"

MIN_SALARY_DEFAULT = 37_000


def _load_min_salary() -> float:
    with open(JOB_PREFS_PATH, encoding="utf-8") as f:
        return float(json.load(f).get("min_salary_gross_year", MIN_SALARY_DEFAULT))


def extract_salary_from_text(text: str) -> Optional[float]:
    """
    Extract yearly gross salary from job description text.
    Handles: "45.000 €", "37k", "37000 Euro", "3.500 €/Monat" (converts to yearly).
    Returns yearly gross in EUR or None if not found.
    """
    if not text:
        return None
    text = text.replace("\u00a0", " ")
    yearly_patterns = [
        r"(?:bis zu\s+)?(\d{1,3}(?:[.,]\d{3})*)\s*[kK]?\s*(?:€|Euro|EUR)\s*(?:brutto)?\s*(?:pro\s+)?(?:Jahr|jährig)",
        r"(?:Gehalt|Vergütung|Salary)[:\s]*(\d{1,3}(?:[.,]\d{3})*)\s*(?:€|Euro|EUR)",
        r"(\d{1,3}(?:[.,]\d{3})*)\s*(?:€|Euro|EUR)\s*(?:brutto\s+)?(?:pro\s+)?Jahr",
        r"(\d{1,3}(?:[.,]\d{3})*)\s*[kK]\s*(?:€|Euro|EUR)?",
    ]
    for pat in yearly_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            num_str = m.group(1).replace(".", "").replace(",", ".")
            try:
                return float(num_str) if "k" not in m.group(0).lower() else float(num_str) * 1000
            except ValueError:
                continue

    monthly_patterns = [
        r"(\d{1,2}(?:[.,]\d{3})*)\s*(?:€|Euro|EUR)\s*(?:/|\s*pro\s+)(?:Monat|month)",
        r"(\d{1,2}(?:[.,]\d{3})*)\s*(?:€|Euro)\s*/?\s*Monat",
    ]
    for pat in monthly_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            num_str = m.group(1).replace(".", "").replace(",", ".")
            try:
                return float(num_str) * 12
            except ValueError:
                continue
    return None


def estimate_salary_with_openai(job: dict[str, Any], min_salary: float) -> Optional[float]:
    """Use OpenAI to estimate yearly gross salary from job title, location, and description snippet."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from ai_modules.llm_client import get_client
        client = get_client()
    except Exception:
        return None
    title = job.get("title") or job.get("role") or ""
    location = job.get("location") or ""
    desc = (job.get("description") or "")[:2000]
    prompt = f"""Schätze das typische Brutto-Jahresgehalt in EUR für diese Stelle in Deutschland.
Titel: {title}
Ort: {location}
Beschreibung (Auszug): {desc}

Antworte NUR mit einer Zahl (Jahresbrutto in EUR), z.B. 42000. Kein anderer Text."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
        )
        content = (resp.choices[0].message.content or "").strip()
        num = re.sub(r"[^\d.,]", "", content).replace(",", ".")
        if num:
            return float(num)
    except Exception:
        pass
    return None


def get_job_salary_estimate(job: dict[str, Any], min_salary: float) -> tuple[Optional[float], str]:
    """
    Return (estimated_yearly_salary, source) for the job.
    source is one of: 'extracted', 'monthly_converted', 'openai_estimate'.
    """
    text = (job.get("description") or "") + " " + (job.get("salary_text") or "")
    extracted = extract_salary_from_text(text)
    if extracted is not None:
        return (extracted, "extracted")
    estimated = estimate_salary_with_openai(job, min_salary)
    if estimated is not None:
        return (estimated, "openai_estimate")
    return (None, "unknown")


def passes_salary_filter(
    job: dict[str, Any],
    min_salary: Optional[float] = None,
) -> bool:
    """Return True if job's (extracted or estimated) yearly salary >= min_salary."""
    if min_salary is None:
        min_salary = _load_min_salary()
    salary, _ = get_job_salary_estimate(job, min_salary)
    if salary is None:
        return True
    return salary >= min_salary


def filter_jobs_by_salary(
    jobs: list[dict[str, Any]],
    min_salary: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Return only jobs that pass the salary filter. Attach salary_estimate to each job."""
    if min_salary is None:
        min_salary = _load_min_salary()
    result = []
    for j in jobs:
        salary, source = get_job_salary_estimate(j, min_salary)
        if salary is not None and salary < min_salary:
            continue
        j = dict(j)
        if salary is not None:
            j["salary_estimate"] = salary
        result.append(j)
    return result
