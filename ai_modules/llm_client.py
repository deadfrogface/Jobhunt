"""
OpenAI client wrapper for AI Job Hunter. Loads API key from config/.env.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


def get_client(model: str = "gpt-4o"):
    """Return OpenAI client instance. Requires OPENAI_API_KEY in environment or .env."""
    from openai import OpenAI
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set. Add it to config/.env or environment.")
    return OpenAI(api_key=key)


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o")
