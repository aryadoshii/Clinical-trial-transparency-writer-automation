#!/usr/bin/env python3
"""Run the full validation + evaluation pipeline and emit a report.

Prerequisites: run scripts/inject_errors.py first so the DB is populated.

Run from the project root:
  python scripts/run_eval.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from config import settings
from src.evaluation.ablation import run_ablation
from src.evaluation.metrics import compute_metrics
from src.evaluation.report import print_ablation, print_metrics, save_json
from src.ingestion.db import get_trial, init_db
from src.ingestion.error_injector import InjectedError
from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation.engine import run as run_validation

console = Console()

_ERROR_TYPES = [
    "MISSING_FIELD",
    "FORMAT_ERROR",
    "LOGICAL_CONTRADICTION",
    "CROSS_FIELD_INCONSISTENCY",
]

_FINDING_LAYER = {
    "FieldFinding": "L1",
    "FormatFinding": "L2",
    "LogicFinding": "L3",
    "CrossFieldFinding": "L4",
}


def _load_trials(db_path: Path) -> List[ClinicalTrialRecord]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    nct_ids = [row["nct_id"] for row in conn.execute("SELECT nct_id FROM trials")]
    conn.close()
    return [t for nct_id in nct_ids if (t := get_trial(db_path, nct_id)) is not None]


def _load_ground_truth(db_path: Path) -> List[InjectedError]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM injected_errors").fetchall()
    conn.close()
    return [
        InjectedError(
            nct_id=r["nct_id"],
            error_type=r["error_type"],
            field_affected=r["field"],
            original_value=r["original_value"],
            injected_value=r["injected_value"],
        )
        for r in rows
    ]


def _print_per_category(
    detected: List[Tuple[str, str]],
    gt_pairs: List[Tuple[str, str]],
) -> None:
    category_detected: defaultdict[str, List[Tuple[str, str]]] = defaultdict(list)
    category_gt: defaultdict[str, List[Tuple[str, str]]] = defaultdict(list)
    for nct_id, error_type in detected:
        category_detected[error_type].append((nct_id, error_type))
    for nct_id, error_type in gt_pairs:
        category_gt[error_type].append((nct_id, error_type))

    table = Table(title="Per-Category Breakdown", header_style="bold cyan")
    table.add_column("Category", style="bold")
    table.add_column("TP", justify="right")
    table.add_column("FP", justify="right")
    table.add_column("FN", justify="right")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")

    for error_type in _ERROR_TYPES:
        m = compute_metrics(category_detected[error_type], category_gt[error_type])
        table.add_row(
            error_type,
            str(m.true_positives),
            str(m.false_positives),
            str(m.false_negatives),
            f"{m.precision:.3f}",
            f"{m.recall:.3f}",
            f"{m.f1:.3f}",
        )
    console.print(table)


def _print_fp_sources(results, gt_set: set) -> None:
    layer_fps: defaultdict[str, int] = defaultdict(int)
    total_fps = 0
    for result in results:
        for finding in result.findings:
            if (finding.nct_id, finding.error_type) not in gt_set:
                layer = _FINDING_LAYER.get(type(finding).__name__, "Unknown")
                layer_fps[layer] += 1
                total_fps += 1

    table = Table(title="False Positive Sources", header_style="bold magenta")
    table.add_column("Layer", style="bold")
    table.add_column("FP Count", justify="right")
    table.add_column("% of Total FPs", justify="right")

    for layer in ["L1", "L2", "L3", "L4"]:
        count = layer_fps[layer]
        pct = (count / total_fps * 100) if total_fps else 0.0
        table.add_row(layer, str(count), f"{pct:.1f}%")
    console.print(table)


def main() -> None:
    init_db(settings.DB_PATH)

    trials = _load_trials(settings.DB_PATH)
    ground_truth = _load_ground_truth(settings.DB_PATH)
    console.print(
        f"Loaded [cyan]{len(trials)}[/cyan] trials, "
        f"[red]{len(ground_truth)}[/red] ground-truth labels"
    )

    results = run_validation(trials, settings.DB_PATH)

    detected = [
        (finding.nct_id, finding.error_type)
        for result in results
        for finding in result.findings
    ]
    gt_pairs = [(e.nct_id, e.error_type) for e in ground_truth]
    gt_set = set(gt_pairs)

    metrics = compute_metrics(detected, gt_pairs)
    print_metrics("Overall Validation Metrics", metrics)

    ablation_results = run_ablation(trials, ground_truth)
    print_ablation(ablation_results)

    _print_per_category(detected, gt_pairs)
    _print_fp_sources(results, gt_set)

    save_json(
        Path("outputs/eval_report.json"),
        {
            "overall": {
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1": metrics.f1,
                "tp": metrics.true_positives,
                "fp": metrics.false_positives,
                "fn": metrics.false_negatives,
            },
            "ablation": [
                {
                    "disabled_level": r.disabled_level,
                    "precision": r.metrics.precision,
                    "recall": r.metrics.recall,
                    "f1": r.metrics.f1,
                }
                for r in ablation_results
            ],
        },
    )


if __name__ == "__main__":
    main()
