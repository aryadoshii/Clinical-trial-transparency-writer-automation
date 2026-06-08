"""Level-1 validation: mandatory field presence checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.ingestion.xml_parser import ClinicalTrialRecord

_MANDATORY = ["start_date", "primary_outcomes"]
_CONDITIONAL = ["enrollment", "phase"]  # only required for interventional trials
_CRITICAL_FIELDS = {"nct_id", "overall_status", "primary_outcomes"}
_STATUS_REQUIRING_START_DATE = {
    "completed", "terminated", "recruiting", "active, not recruiting",
    "enrolling by invitation", "suspended",
}


@dataclass
class FieldFinding:
    nct_id: str
    field: str
    severity: str = "HIGH"
    error_type: str = "MISSING_FIELD"


def _is_empty(val: object) -> bool:
    return val is None or val == [] or val == ""


def check(record: ClinicalTrialRecord) -> List[FieldFinding]:
    """Return findings for missing mandatory fields.

    phase and enrollment are only required for interventional trials.
    """
    findings: List[FieldFinding] = []

    for field in _MANDATORY:
        if _is_empty(getattr(record, field)):
            if field == "start_date":
                status = (record.overall_status or "").lower().strip()
                if status not in _STATUS_REQUIRING_START_DATE:
                    continue
            severity = "CRITICAL" if field in _CRITICAL_FIELDS else "HIGH"
            findings.append(FieldFinding(nct_id=record.nct_id, field=field, severity=severity))

    if record.study_type and "interventional" in record.study_type.lower():
        for field in _CONDITIONAL:
            if _is_empty(getattr(record, field)):
                findings.append(FieldFinding(nct_id=record.nct_id, field=field, severity="HIGH"))

    return findings
