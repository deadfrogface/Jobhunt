"""
Central logging configuration for AI Job Hunter.
Logs are written to logs/scraper.log, logs/filter.log, logs/applications.log, logs/errors.log.
"""
import logging
from pathlib import Path

# Project root (directory containing main.py)
PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def _make_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fh = logging.FileHandler(LOGS_DIR / log_file, encoding="utf-8")
    fh.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def get_scraper_logger() -> logging.Logger:
    return _make_logger("scraper", "scraper.log")


def get_filter_logger() -> logging.Logger:
    return _make_logger("filter", "filter.log")


def get_applications_logger() -> logging.Logger:
    return _make_logger("applications", "applications.log")


def get_error_logger() -> logging.Logger:
    return _make_logger("errors", "errors.log", level=logging.WARNING)
