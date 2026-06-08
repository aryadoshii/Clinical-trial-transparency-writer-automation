"""Route a single record through all validation levels and aggregate findings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation import l1_field, l2_format, l3_logic, l4_cross_field


@dataclass
class ValidationResult:
    """Aggregated validation output for one trial record."""

    nct_id: str
    findings: List[Any] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.findings)


def validate(record: ClinicalTrialRecord) -> ValidationResult:
    """Run all four validation levels against *record* and return the combined result."""
    result = ValidationResult(nct_id=record.nct_id)
    result.findings.extend(l1_field.check(record))
    result.findings.extend(l2_format.check(record))
    result.findings.extend(l3_logic.check(record))
    result.findings.extend(l4_cross_field.check(record))
    return result
