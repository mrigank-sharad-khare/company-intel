"""
SQLite persistence.

Reports are stored as a parent row plus the full result set serialised to
JSON in a child column. Why JSON rather than a fully normalised answers table?
The question set evolves over time; storing results as JSON keeps historical
reports renderable even after the questionnaire changes, and avoids brittle
migrations. We still index the columns analysts query on (company, date).

The module exposes a tiny, explicit API. No ORM — the surface is small enough
that raw, parameterised SQL is clearer and dependency-free.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config.settings import DATABASE_PATH
from core.models import Report

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name  TEXT    NOT NULL,
    website       TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    pdf_path      TEXT    DEFAULT '',
    avg_confidence INTEGER DEFAULT 0,
    results_json  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_company ON reports(company_name);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);
"""


@contextmanager
def _connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    """Create tables if they do not exist. Safe to call on every startup."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def save_report(report: Report, db_path: Path | None = None) -> int:
    """Insert (or update if it already has an id) and return the report id."""
    payload = json.dumps([r.to_dict() for r in report.results])
    with _connect(db_path) as conn:
        if report.id is None:
            cur = conn.execute(
                """INSERT INTO reports
                   (company_name, website, created_at, pdf_path,
                    avg_confidence, results_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    report.company_name,
                    report.website,
                    report.created_at,
                    report.pdf_path,
                    report.average_confidence,
                    payload,
                ),
            )
            report.id = int(cur.lastrowid)
        else:
            conn.execute(
                """UPDATE reports
                   SET company_name=?, website=?, created_at=?, pdf_path=?,
                       avg_confidence=?, results_json=?
                   WHERE id=?""",
                (
                    report.company_name,
                    report.website,
                    report.created_at,
                    report.pdf_path,
                    report.average_confidence,
                    payload,
                    report.id,
                ),
            )
    return report.id


def list_reports(db_path: Path | None = None) -> list[dict]:
    """Lightweight listing for the 'Previous Reports' sidebar."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT id, company_name, website, created_at,
                      pdf_path, avg_confidence
               FROM reports ORDER BY created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: int, db_path: Path | None = None) -> Report | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id=?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["results"] = json.loads(data.pop("results_json"))
    return Report.from_dict(data)


def delete_report(report_id: int, db_path: Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
