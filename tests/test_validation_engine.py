"""Tests for the four validation levels and the router."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation import l1_field, l2_format, l3_logic, l4_cross_field, router


def test_l1_recruiting_missing_start_date():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        overall_status="Recruiting",
        study_type="Interventional",
        start_date=None,
        primary_outcomes=["OS"],
    )
    assert any(f.field == "start_date" for f in l1_field.check(record))


def test_l1_interventional_missing_phase():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        study_type="Interventional",
        phase=None,
        start_date="2020-01-01",
        primary_outcomes=["OS"],
        overall_status="Recruiting",
    )
    assert any(f.field == "phase" for f in l1_field.check(record))


def test_l1_observational_phase_not_flagged():
    record = ClinicalTrialRecord(
        nct_id="NCT00000002",
        study_type="Observational",
        phase=None,
        enrollment=None,
        primary_outcomes=["Quality of life"],  # satisfy mandatory check; isolate phase/enrollment
        overall_status="Recruiting",
        start_date="2020-01-01",
    )
    findings = l1_field.check(record)
    flagged_fields = {f.field for f in findings}
    assert "phase" not in flagged_fields
    assert "enrollment" not in flagged_fields


def test_l2_bad_date_flagged():
    record = ClinicalTrialRecord(nct_id="NCT00000001", start_date="31-13-2020")
    assert len(l2_format.check(record)) > 0


def test_l2_partial_date_valid():
    record = ClinicalTrialRecord(nct_id="NCT00000001", start_date="2023-06")
    assert l2_format.check(record) == []


def test_l3_inverted_dates():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        start_date="2023-01-01",
        completion_date="2020-01-01",
    )
    assert len(l3_logic.check(record)) > 0


def test_l3_completed_missing_completion_date():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        overall_status="Completed",
        start_date="2020-01-01",
        completion_date=None,
    )
    assert len(l3_logic.check(record)) > 0


def test_l4_gender_pregnancy():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        gender="Male",
        conditions=["pregnancy complication"],
    )
    assert len(l4_cross_field.check(record)) > 0


def test_l4_phase3_low_enrollment():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        phase="Phase 3",
        enrollment=45,
    )
    assert len(l4_cross_field.check(record)) > 0


def test_clean_record():
    record = ClinicalTrialRecord(
        nct_id="NCT00000001",
        study_type="Interventional",
        start_date="2020-01-01",
        completion_date="2023-01-01",
        phase="Phase 2",
        enrollment=200,
        primary_outcomes=["Overall survival"],
        overall_status="Recruiting",
        conditions=["Cancer"],
        gender="All",
    )
    result = router.validate(record)
    assert result.has_errors is False
