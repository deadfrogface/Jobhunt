"""
SQLite database manager for application tracking.
Schema: applications (id, company, role, location, source, salary_estimate, date_found, date_applied, status, notes).
"""
import sqlite3
from pathlib import Path
from datetime import date
from typing import Optional

# Resolve project root (parent of ai-job-hunter/database/)
_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "applications.db"

VALID_STATUSES = ("saved", "applied", "interview", "rejected", "offer")


def _get_logger():
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from log_config import get_applications_logger
    return get_applications_logger()


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database. Creates data dir and DB if needed."""
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the applications table if it does not exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT,
                source TEXT,
                salary_estimate REAL,
                date_found TEXT,
                date_applied TEXT,
                status TEXT CHECK(status IN ('saved','applied','interview','rejected','offer')),
                notes TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def insert_job(
    company: str,
    role: str,
    location: Optional[str] = None,
    source: Optional[str] = None,
    salary_estimate: Optional[float] = None,
    date_found: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Insert a new job application with status 'saved'. Returns the new row id."""
    if date_found is None:
        date_found = date.isoformat(date.today())
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO applications (company, role, location, source, salary_estimate, date_found, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'saved', ?)
            """,
            (company, role, location, source, salary_estimate, date_found, notes),
        )
        conn.commit()
        row_id = cur.lastrowid
        _get_logger().info("insert_job company=%s role=%s id=%s", company, role, row_id)
        return row_id
    finally:
        conn.close()


def update_application_status(application_id: int, status: str, notes: Optional[str] = None) -> None:
    """Update status of an application. Optionally set date_applied when status is 'applied'."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
    conn = get_connection()
    try:
        if status == "applied":
            conn.execute(
                "UPDATE applications SET status = ?, date_applied = ?, notes = COALESCE(?, notes) WHERE id = ?",
                (status, date.isoformat(date.today()), notes, application_id),
            )
        else:
            conn.execute(
                "UPDATE applications SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
                (status, notes, application_id),
            )
        conn.commit()
        _get_logger().info("update_application_status id=%s status=%s", application_id, status)
    finally:
        conn.close()


def get_pending_for_review() -> list[dict]:
    """Return all applications with status 'saved' (pending user confirmation before applying)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, company, role, location, source, salary_estimate, date_found, status, notes FROM applications WHERE status = 'saved' ORDER BY date_found DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_by_status(status: str) -> list[dict]:
    """Return all applications with the given status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, company, role, location, source, salary_estimate, date_found, date_applied, status, notes FROM applications WHERE status = ? ORDER BY date_found DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_by_company_role(company: str, role: str) -> Optional[dict]:
    """Return the most recent application for this company and role, if any."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, company, role, location, source, salary_estimate, date_found, date_applied, status, notes FROM applications WHERE company = ? AND role = ? ORDER BY id DESC LIMIT 1",
            (company, role),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
