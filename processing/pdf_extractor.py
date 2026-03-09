"""
Extract text from Lebenslauf and Arbeitszeugnisse PDFs for use in relevance filter and Anschreiben generator.
"""
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LEBENSLAUF_PATH = CONFIG_DIR / "lebenslauf.pdf"
ARBEITSZEUGNISSE_PATH = CONFIG_DIR / "arbeitszeugnisse.pdf"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from a single PDF file."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n\n".join(text_parts).strip() if text_parts else ""


def get_lebenslauf_text() -> str:
    """Return full text of config/lebenslauf.pdf. Returns empty string if file missing."""
    if not LEBENSLAUF_PATH.is_file():
        return ""
    return extract_text_from_pdf(LEBENSLAUF_PATH)


def get_arbeitszeugnisse_text() -> str:
    """Return full text of config/arbeitszeugnisse.pdf. Returns empty string if file missing."""
    if not ARBEITSZEUGNISSE_PATH.is_file():
        return ""
    return extract_text_from_pdf(ARBEITSZEUGNISSE_PATH)


def get_profile_text() -> str:
    """Return combined text from Lebenslauf and Arbeitszeugnisse for AI modules."""
    lebenslauf = get_lebenslauf_text()
    arbeitszeugnisse = get_arbeitszeugnisse_text()
    parts = []
    if lebenslauf:
        parts.append("=== LEBENSLAUF ===\n" + lebenslauf)
    if arbeitszeugnisse:
        parts.append("=== ARBEITSZEUGNISSE ===\n" + arbeitszeugnisse)
    return "\n\n".join(parts) if parts else ""
