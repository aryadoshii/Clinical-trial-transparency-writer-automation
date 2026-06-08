"""Precision, recall, and F1 computation for validation output vs. ground truth."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass
class EvalMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def compute_metrics(
    detected: List[Tuple[str, str]],
    ground_truth: List[Tuple[str, str]],
) -> EvalMetrics:
    """Compute TP/FP/FN from (nct_id, error_type) pair lists."""
    det: Set[Tuple[str, str]] = set(detected)
    gt: Set[Tuple[str, str]] = set(ground_truth)
    return EvalMetrics(
        true_positives=len(det & gt),
        false_positives=len(det - gt),
        false_negatives=len(gt - det),
    )
