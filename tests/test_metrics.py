"""Tests for the evaluation metrics module."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.metrics import compute_metrics


def test_perfect():
    pairs = [(f"NCT{i:08d}", "MISSING_FIELD") for i in range(10)]
    m = compute_metrics(pairs, pairs)
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0


def test_zero():
    gt = [(f"NCT{i:08d}", "FORMAT_ERROR") for i in range(5)]
    m = compute_metrics([], gt)
    assert m.precision == 0.0
    assert m.recall == 0.0
    assert m.f1 == 0.0


def test_partial():
    gt = [(f"NCT{i:08d}", "LOGICAL_CONTRADICTION") for i in range(10)]
    matching = gt[:7]
    extra = [("NCT99999998", "LOGICAL_CONTRADICTION"), ("NCT99999999", "LOGICAL_CONTRADICTION")]
    detected = matching + extra
    m = compute_metrics(detected, gt)
    assert m.true_positives == 7
    assert m.false_positives == 2
    assert m.false_negatives == 3
