"""Orchestrate multi-level validation over a batch of ClinicalTrialRecord objects."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.ingestion.db import insert_validation_result
from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation.router import ValidationResult, validate

logger = logging.getLogger(__name__)


def run(records: List[ClinicalTrialRecord], db_path: Path) -> List[ValidationResult]:
    """Validate every record, persist findings to the DB, and return all results."""
    results: List[ValidationResult] = []
    for record in records:
        result = validate(record)
        for finding in result.findings:
            insert_validation_result(
                db_path=db_path,
                nct_id=finding.nct_id,
                error_type=finding.error_type,
                field=finding.field,
                severity=finding.severity,
            )
        results.append(result)

    flagged = sum(1 for r in results if r.has_errors)
    logger.info("Validated %d records; %d had findings", len(results), flagged)
    return results
