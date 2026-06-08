"""Normalize raw field values in ClinicalTrialRecord instances."""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional

from src.ingestion.xml_parser import ClinicalTrialRecord

logger = logging.getLogger(__name__)

_PHASE_MAP: dict[str, str] = {
    "phase 1": "Phase 1",
    "phase i": "Phase 1",
    "phase 1/phase 2": "Phase 1",
    "phase 2": "Phase 2",
    "phase ii": "Phase 2",
    "phase 2/phase 3": "Phase 2",
    "phase 3": "Phase 3",
    "phase iii": "Phase 3",
    "phase 4": "Phase 4",
    "phase iv": "Phase 4",
    "n/a": "N/A",
    "not applicable": "N/A",
    "": "N/A",
}

_MONTH_MAP: dict[str, str] = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

_RE_MDY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_RE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RE_MONTH_YEAR = re.compile(r"^([A-Za-z]+)\s+(\d{4})$")


def _parse_date(raw: Optional[str]) -> Optional[str]:
    """Return ISO 8601 date string for *raw*, or None when unparseable."""
    if not raw:
        return None
    raw = raw.strip()

    m = _RE_MDY.fullmatch(raw)
    if m:
        month, day, year = m.groups()
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return None

    m = _RE_ISO.fullmatch(raw)
    if m:
        year, month, day = m.groups()
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return None

    m = _RE_MONTH_YEAR.fullmatch(raw)
    if m:
        month_name, year = m.groups()
        month_num = _MONTH_MAP.get(month_name.lower())
        if month_num:
            return f"{year}-{month_num}-01"

    logger.debug("Unparseable date: %r", raw)
    return None


def _normalize_phase(raw: Optional[str]) -> Optional[str]:
    """Map raw phase text to a canonical label, or return raw if unrecognised."""
    if raw is None:
        return None
    return _PHASE_MAP.get(raw.strip().lower(), raw.strip())


def normalize(record: ClinicalTrialRecord) -> ClinicalTrialRecord:
    """Return a copy of *record* with normalised date, phase, and status fields."""
    return record.model_copy(
        update={
            "start_date": _parse_date(record.start_date),
            "completion_date": _parse_date(record.completion_date),
            "phase": _normalize_phase(record.phase),
            "overall_status": (
                record.overall_status.strip().title() if record.overall_status else None
            ),
        }
    )
