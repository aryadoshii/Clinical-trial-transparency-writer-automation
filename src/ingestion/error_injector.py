"""Inject synthetic, labeled errors into ClinicalTrialRecord objects.

Produces a corrupted copy of the input records alongside a ground-truth list
of InjectedError labels for downstream evaluation.
"""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from src.ingestion.xml_parser import ClinicalTrialRecord

_MANDATORY_FIELDS = ["enrollment", "phase", "start_date", "primary_outcomes"]
_DATE_FIELDS = ["start_date", "completion_date"]


@dataclass
class InjectedError:
    """Ground-truth label for a single synthetic data quality error."""

    nct_id: str
    error_type: str
    field_affected: str
    original_value: object
    injected_value: object


# ---------------------------------------------------------------------------
# Injector functions — each mutates *record* in-place and returns an error label.
# ---------------------------------------------------------------------------

def _inject_missing_field(
    record: ClinicalTrialRecord, rng: random.Random
) -> InjectedError:
    field = rng.choice(_MANDATORY_FIELDS)
    original = getattr(record, field)
    setattr(record, field, None)
    return InjectedError(
        nct_id=record.nct_id,
        error_type="MISSING_FIELD",
        field_affected=field,
        original_value=original,
        injected_value=None,
    )


def _inject_format_error(
    record: ClinicalTrialRecord, rng: random.Random
) -> InjectedError:
    field = rng.choice(_DATE_FIELDS)
    original = getattr(record, field)
    bad_value = "31-13-2020"
    setattr(record, field, bad_value)
    return InjectedError(
        nct_id=record.nct_id,
        error_type="FORMAT_ERROR",
        field_affected=field,
        original_value=original,
        injected_value=bad_value,
    )


def _inject_logical_contradiction(
    record: ClinicalTrialRecord, rng: random.Random
) -> InjectedError:
    original = record.completion_date
    # Force completion before any plausible start date.
    record.completion_date = "1990-01-01"
    if not record.start_date:
        record.start_date = "2000-01-01"
    return InjectedError(
        nct_id=record.nct_id,
        error_type="LOGICAL_CONTRADICTION",
        field_affected="completion_date",
        original_value=original,
        injected_value="1990-01-01",
    )


def _inject_cross_field_inconsistency(
    record: ClinicalTrialRecord, rng: random.Random
) -> InjectedError:
    original_gender = record.gender
    record.gender = "Male"
    record.minimum_age = "0 Years"
    record.conditions = list(record.conditions) + ["pregnancy"]
    return InjectedError(
        nct_id=record.nct_id,
        error_type="CROSS_FIELD_INCONSISTENCY",
        field_affected="gender",
        original_value=original_gender,
        injected_value="Male",
    )


# (error_type, probability, injector_fn)
_INJECTORS: List[Tuple[str, float, Callable]] = [
    ("MISSING_FIELD", 0.08, _inject_missing_field),
    ("FORMAT_ERROR", 0.12, _inject_format_error),
    ("LOGICAL_CONTRADICTION", 0.05, _inject_logical_contradiction),
    ("CROSS_FIELD_INCONSISTENCY", 0.04, _inject_cross_field_inconsistency),
]


def inject_errors(
    records: List[ClinicalTrialRecord],
    seed: int = 42,
) -> Tuple[List[ClinicalTrialRecord], List[InjectedError]]:
    """Return (corrupted_records, ground_truth_labels).

    Each record receives at most one injected error. Approximate injection rates:
      - MISSING_FIELD              ~8 %
      - FORMAT_ERROR               ~12 %
      - LOGICAL_CONTRADICTION      ~5 %
      - CROSS_FIELD_INCONSISTENCY  ~4 %
    """
    rng = random.Random(seed)
    corrupted: List[ClinicalTrialRecord] = []
    labels: List[InjectedError] = []

    for record in records:
        rec = copy.deepcopy(record)
        injected_this_record = False
        for _name, prob, fn in _INJECTORS:
            if not injected_this_record and rng.random() < prob:
                labels.append(fn(rec, rng))
                injected_this_record = True
        corrupted.append(rec)

    return corrupted, labels
