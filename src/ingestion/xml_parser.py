"""Parse ClinicalTrials.gov trial files into ClinicalTrialRecord Pydantic models.

Supports both:
  - Legacy XML format (*.xml) from the old v1 API
  - Current JSON format (*.json) from the v2 API (clinicaltrials.gov/api/v2/studies)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Map v2 API phase enum values → human-readable labels used by schema_normalizer
_V2_PHASE_MAP: Dict[str, str] = {
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
    "NA": "N/A",
    "EARLY_PHASE1": "Phase 1",
}


class ClinicalTrialRecord(BaseModel):
    """Structured representation of a single clinical trial from ClinicalTrials.gov."""

    nct_id: str
    official_title: Optional[str] = None
    overall_status: Optional[str] = None
    study_type: Optional[str] = None
    phase: Optional[str] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    enrollment: Optional[int] = None
    interventions: List[str] = []
    primary_outcomes: List[str] = []
    conditions: List[str] = []
    sponsors: Optional[str] = None
    gender: Optional[str] = None
    minimum_age: Optional[str] = None
    maximum_age: Optional[str] = None


# ---------------------------------------------------------------------------
# XML parser (legacy v1 format)
# ---------------------------------------------------------------------------

def _text(root: etree._Element, xpath: str) -> Optional[str]:
    """Return stripped text of the first element matching *xpath*, or None."""
    elements = root.xpath(xpath)
    if elements:
        text = elements[0].text
        return text.strip() if text else None
    return None


def _text_list(root: etree._Element, xpath: str) -> List[str]:
    """Return stripped text of all elements matching *xpath*, excluding blanks."""
    return [el.text.strip() for el in root.xpath(xpath) if el.text and el.text.strip()]


def parse_trial_xml(xml_path: Path) -> Optional[ClinicalTrialRecord]:
    """Parse a single ClinicalTrials.gov XML file (v1 format).

    Returns None when the file is malformed or lacks an nct_id.
    """
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
    except etree.XMLSyntaxError as exc:
        logger.warning("Malformed XML in %s: %s", xml_path, exc)
        return None

    nct_id = _text(root, ".//id_info/nct_id")
    if not nct_id:
        logger.warning("No nct_id found in %s — skipping", xml_path)
        return None

    enrollment_raw = _text(root, ".//enrollment")
    enrollment: Optional[int] = None
    if enrollment_raw:
        try:
            enrollment = int(enrollment_raw)
        except ValueError:
            logger.debug("Non-integer enrollment %r in %s", enrollment_raw, xml_path)

    return ClinicalTrialRecord(
        nct_id=nct_id,
        official_title=_text(root, ".//official_title"),
        overall_status=_text(root, ".//overall_status"),
        study_type=_text(root, ".//study_type"),
        phase=_text(root, ".//phase"),
        start_date=_text(root, ".//start_date"),
        completion_date=_text(root, ".//primary_completion_date"),
        enrollment=enrollment,
        interventions=_text_list(root, ".//intervention/intervention_name"),
        primary_outcomes=_text_list(root, ".//primary_outcome/measure"),
        conditions=_text_list(root, ".//condition"),
        sponsors=_text(root, ".//lead_sponsor/agency"),
        gender=_text(root, ".//eligibility/gender"),
        minimum_age=_text(root, ".//eligibility/minimum_age"),
        maximum_age=_text(root, ".//eligibility/maximum_age"),
    )


# ---------------------------------------------------------------------------
# JSON parser (current v2 API format)
# ---------------------------------------------------------------------------

def _jget(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safe nested dict access: _jget(d, 'a', 'b', 'c') == d.get('a',{}).get('b',{}).get('c')."""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key, default)
        if obj is None:
            return default
    return obj


def parse_trial_json(json_path: Path) -> Optional[ClinicalTrialRecord]:
    """Parse a single study JSON file from the ClinicalTrials.gov v2 API.

    Returns None when the file is malformed or lacks an nct_id.
    """
    try:
        data: Dict[str, Any] = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cannot read JSON %s: %s", json_path, exc)
        return None

    proto = data.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    arms = proto.get("armsInterventionsModule", {})
    outcomes = proto.get("outcomesModule", {})
    conditions_mod = proto.get("conditionsModule", {})
    sponsors_mod = proto.get("sponsorCollaboratorsModule", {})
    eligibility = proto.get("eligibilityModule", {})

    nct_id = ident.get("nctId", "").strip()
    if not nct_id:
        logger.warning("No nctId in %s — skipping", json_path)
        return None

    # Phases: v2 returns a list like ["PHASE2"]; take the first entry
    phases_raw: List[str] = design.get("phases", [])
    phase: Optional[str] = None
    if phases_raw:
        phase = _V2_PHASE_MAP.get(phases_raw[0], phases_raw[0])

    enrollment_count = _jget(design, "enrollmentInfo", "count")
    enrollment: Optional[int] = int(enrollment_count) if enrollment_count is not None else None

    interventions = [
        i["name"] for i in arms.get("interventions", []) if i.get("name")
    ]
    primary_outcomes = [
        o["measure"] for o in outcomes.get("primaryOutcomes", []) if o.get("measure")
    ]
    conditions = [c for c in conditions_mod.get("conditions", []) if c]

    return ClinicalTrialRecord(
        nct_id=nct_id,
        official_title=ident.get("officialTitle") or ident.get("briefTitle"),
        overall_status=status.get("overallStatus"),
        study_type=design.get("studyType"),
        phase=phase,
        start_date=_jget(status, "startDateStruct", "date"),
        completion_date=_jget(status, "primaryCompletionDateStruct", "date"),
        enrollment=enrollment,
        interventions=interventions,
        primary_outcomes=primary_outcomes,
        conditions=conditions,
        sponsors=_jget(sponsors_mod, "leadSponsor", "name"),
        gender=eligibility.get("sex"),
        minimum_age=eligibility.get("minimumAge"),
        maximum_age=eligibility.get("maximumAge"),
    )


# ---------------------------------------------------------------------------
# Directory scanner — handles both formats
# ---------------------------------------------------------------------------

def parse_directory(data_dir: Path) -> List[ClinicalTrialRecord]:
    """Parse all *.json and *.xml files under *data_dir*, preferring JSON when both exist."""
    json_files = list(data_dir.glob("*.json"))
    xml_files = list(data_dir.glob("*.xml"))
    total = len(json_files) + len(xml_files)
    logger.info(
        "Found %d JSON + %d XML files in %s", len(json_files), len(xml_files), data_dir
    )

    records: List[ClinicalTrialRecord] = []
    for path in json_files:
        record = parse_trial_json(path)
        if record is not None:
            records.append(record)
    for path in xml_files:
        record = parse_trial_xml(path)
        if record is not None:
            records.append(record)

    logger.info("Successfully parsed %d / %d records", len(records), total)
    return records
