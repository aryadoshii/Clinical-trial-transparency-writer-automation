"""Level-4 validation: cross-field consistency checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.ingestion.xml_parser import ClinicalTrialRecord

_LATE_PHASE = {"Phase 3", "Phase 4"}


@dataclass
class CrossFieldFinding:
    nct_id: str
    field: str
    detail: str
    severity: str = "WARNING"
    error_type: str = "CROSS_FIELD_INCONSISTENCY"


def check(record: ClinicalTrialRecord) -> List[CrossFieldFinding]:
    """Return findings for known cross-field contradictions."""
    findings: List[CrossFieldFinding] = []

    # Check 1: Male gender combined with a pregnancy-related condition is contradictory.
    if record.gender and record.gender.strip().lower() == "male":
        if any("pregnan" in c.lower() for c in record.conditions):
            findings.append(
                CrossFieldFinding(
                    nct_id=record.nct_id,
                    field="gender",
                    detail="gender=Male but conditions include a pregnancy-related term",
                )
            )

    # Check 2: Phase 3/4 trials with fewer than 100 enrolled subjects are suspicious.
    if (
        record.phase in _LATE_PHASE
        and record.enrollment is not None
        and record.enrollment < 100
    ):
        findings.append(
            CrossFieldFinding(
                nct_id=record.nct_id,
                field="enrollment",
                detail=(
                    f"Phase 3/4 trial has only {record.enrollment} enrolled subjects"
                ),
                severity="MEDIUM",
            )
        )

    # Check 3: Completed trials should have recorded primary outcomes.
    if (
        record.overall_status
        and "completed" in record.overall_status.lower()
        and not record.primary_outcomes
    ):
        findings.append(
            CrossFieldFinding(
                nct_id=record.nct_id,
                field="primary_outcomes",
                detail="Completed trial has no recorded primary outcomes",
                severity="HIGH",
            )
        )

    return findings
