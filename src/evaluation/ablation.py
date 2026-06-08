"""Ablation study: measure performance impact of disabling one validation level at a time."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from src.ingestion.error_injector import InjectedError
from src.ingestion.xml_parser import ClinicalTrialRecord
from src.evaluation.metrics import EvalMetrics, compute_metrics


@dataclass
class AblationResult:
    disabled_level: str
    metrics: EvalMetrics


def run_ablation(
    records: List[ClinicalTrialRecord],
    ground_truth: List[InjectedError],
    levels: Optional[List[str]] = None,
) -> List[AblationResult]:
    """Return metrics for each configuration where one validation level is disabled.

    Leaving *levels* as None ablates all four levels in turn.
    """
    from src.validation import l1_field, l2_format, l3_logic, l4_cross_field

    level_modules = {
        "l1_field": l1_field,
        "l2_format": l2_format,
        "l3_logic": l3_logic,
        "l4_cross_field": l4_cross_field,
    }
    targets = levels if levels is not None else list(level_modules.keys())
    gt_pairs = [(e.nct_id, e.error_type) for e in ground_truth]
    results: List[AblationResult] = []

    for disabled in targets:
        detected = []
        for record in records:
            for name, module in level_modules.items():
                if name == disabled:
                    continue
                for finding in module.check(record):
                    detected.append((finding.nct_id, finding.error_type))

        metrics = compute_metrics(detected, gt_pairs)
        results.append(AblationResult(disabled_level=disabled, metrics=metrics))

    return results
