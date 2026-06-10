"""Level-3 validation: logical consistency checks within a single record."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from src.ingestion.xml_parser import ClinicalTrialRecord

_AGE_SUFFIX = re.compile(r"\s*(years?|months?)\s*$", re.IGNORECASE)


@dataclass
class LogicFinding:
    nct_id: str
    field: str
    detail: str
    severity: str = "HIGH"
    error_type: str = "LOGICAL_CONTRADICTION"


def _parse_age_int(age_str: Optional[str]) -> Optional[int]:
    """Strip unit suffixes and return integer age value, or None if unparseable."""
    if not age_str:
        return None
    cleaned = _AGE_SUFFIX.sub("", age_str.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def check(record: ClinicalTrialRecord) -> List[LogicFinding]:
    """Return findings for logical contradictions within a single record."""
    findings: List[LogicFinding] = []

    # Check 1: completion_date must not precede start_date
    if record.start_date and record.completion_date:
        if record.completion_date < record.start_date:
            findings.append(
                LogicFinding(
                    nct_id=record.nct_id,
                    field="completion_date",
                    detail=(
                        f"completion_date {record.completion_date!r} "
                        f"precedes start_date {record.start_date!r}"
                    ),
                )
            )

    # Check 2: Completed trials must have a completion_date (only "completed", not "terminated")
    if (
        record.overall_status
        and record.overall_status.lower().strip() == "completed"
        and record.start_date  # skip pre-start trials
        and not record.completion_date
    ):
        findings.append(
            LogicFinding(
                nct_id=record.nct_id,
                field="completion_date",
                detail="overall_status='Completed' but completion_date is absent",
            )
        )

    # Check 3: minimum_age must not equal or exceed maximum_age
    try:
        min_age = _parse_age_int(record.minimum_age)
        max_age = _parse_age_int(record.maximum_age)
        if min_age is not None and max_age is not None and min_age >= max_age:
            findings.append(
                LogicFinding(
                    nct_id=record.nct_id,
                    field="minimum_age",
                    detail=(
                        f"minimum_age ({record.minimum_age}) >= "
                        f"maximum_age ({record.maximum_age})"
                    ),
                    severity="HIGH",
                    error_type="LOGICAL_CONTRADICTION",
                )
            )
    except Exception:
        pass

    return findings
