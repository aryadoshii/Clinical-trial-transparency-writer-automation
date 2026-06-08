"""Level-2 validation: date, numeric, and identifier format checks."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from src.ingestion.xml_parser import ClinicalTrialRecord

_ISO_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
_NCT_RE = re.compile(r"^NCT\d{8}$")
_DATE_FIELDS = ["start_date", "completion_date"]


@dataclass
class FormatFinding:
    nct_id: str
    field: str
    bad_value: str
    severity: str = "ERROR"
    error_type: str = "FORMAT_ERROR"


def check(record: ClinicalTrialRecord) -> List[FormatFinding]:
    """Return a finding for each field whose value fails its expected format."""
    findings: List[FormatFinding] = []

    # Date fields must be ISO 8601
    for field in _DATE_FIELDS:
        val = getattr(record, field)
        if val is not None and not _ISO_DATE.match(str(val)):
            findings.append(
                FormatFinding(nct_id=record.nct_id, field=field, bad_value=str(val))
            )

    # Enrollment must be a positive integer
    if record.enrollment is not None and record.enrollment <= 0:
        findings.append(
            FormatFinding(
                nct_id=record.nct_id,
                field="enrollment",
                bad_value=str(record.enrollment),
            )
        )

    # nct_id must match NCT + 8 digits
    if not _NCT_RE.match(record.nct_id):
        findings.append(
            FormatFinding(
                nct_id=record.nct_id,
                field="nct_id",
                bad_value=record.nct_id,
            )
        )

    return findings
