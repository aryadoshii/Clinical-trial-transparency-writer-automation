"""SQLite persistence layer for TrialTransparency.

Tables:
  trials              — one row per ClinicalTrialRecord
  validation_results  — findings produced by the validation engine
  injected_errors     — ground-truth labels from the error injector
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ingestion.xml_parser import ClinicalTrialRecord
from src.ingestion.error_injector import InjectedError

_DDL = """
CREATE TABLE IF NOT EXISTS trials (
    nct_id            TEXT PRIMARY KEY,
    official_title    TEXT,
    overall_status    TEXT,
    study_type        TEXT,
    phase             TEXT,
    start_date        TEXT,
    completion_date   TEXT,
    enrollment        INTEGER,
    interventions     TEXT,
    primary_outcomes  TEXT,
    conditions        TEXT,
    sponsors          TEXT,
    gender            TEXT,
    minimum_age       TEXT,
    maximum_age       TEXT
);

CREATE TABLE IF NOT EXISTS validation_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id      TEXT NOT NULL,
    error_type  TEXT,
    field       TEXT,
    severity    TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS injected_errors (
    nct_id          TEXT,
    error_type      TEXT,
    field           TEXT,
    original_value  TEXT,
    injected_value  TEXT
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Create all tables if they do not already exist."""
    with _connect(db_path) as conn:
        conn.executescript(_DDL)


def insert_trial(db_path: Path, record: ClinicalTrialRecord) -> None:
    """Upsert a ClinicalTrialRecord into the trials table."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO trials VALUES (
                :nct_id, :official_title, :overall_status, :study_type,
                :phase, :start_date, :completion_date, :enrollment,
                :interventions, :primary_outcomes, :conditions,
                :sponsors, :gender, :minimum_age, :maximum_age
            )
            """,
            {
                "nct_id": record.nct_id,
                "official_title": record.official_title,
                "overall_status": record.overall_status,
                "study_type": record.study_type,
                "phase": record.phase,
                "start_date": record.start_date,
                "completion_date": record.completion_date,
                "enrollment": record.enrollment,
                "interventions": json.dumps(record.interventions or []),
                "primary_outcomes": json.dumps(record.primary_outcomes or []),
                "conditions": json.dumps(record.conditions or []),
                "sponsors": record.sponsors,
                "gender": record.gender,
                "minimum_age": record.minimum_age,
                "maximum_age": record.maximum_age,
            },
        )


def insert_validation_result(
    db_path: Path,
    nct_id: str,
    error_type: str,
    field: str,
    severity: str,
    detected_at: Optional[datetime] = None,
) -> None:
    """Insert one validation finding row."""
    ts = (detected_at or datetime.utcnow()).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO validation_results (nct_id, error_type, field, severity, detected_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nct_id, error_type, field, severity, ts),
        )


def insert_injected_error(db_path: Path, error: InjectedError) -> None:
    """Persist one InjectedError label."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO injected_errors (nct_id, error_type, field, original_value, injected_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                error.nct_id,
                error.error_type,
                error.field_affected,
                str(error.original_value),
                str(error.injected_value),
            ),
        )


def get_trial(db_path: Path, nct_id: str) -> Optional[ClinicalTrialRecord]:
    """Return the trial with *nct_id*, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM trials WHERE nct_id = ?", (nct_id,)
        ).fetchone()
    if row is None:
        return None
    return ClinicalTrialRecord(
        nct_id=row["nct_id"],
        official_title=row["official_title"],
        overall_status=row["overall_status"],
        study_type=row["study_type"],
        phase=row["phase"],
        start_date=row["start_date"],
        completion_date=row["completion_date"],
        enrollment=row["enrollment"],
        interventions=json.loads(row["interventions"] or "[]") or [],
        primary_outcomes=json.loads(row["primary_outcomes"] or "[]") or [],
        conditions=json.loads(row["conditions"] or "[]") or [],
        sponsors=row["sponsors"],
        gender=row["gender"],
        minimum_age=row["minimum_age"],
        maximum_age=row["maximum_age"],
    )
