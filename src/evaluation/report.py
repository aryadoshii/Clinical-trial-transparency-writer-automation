"""Generate evaluation reports as Rich tables and JSON summaries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from src.evaluation.ablation import AblationResult
from src.evaluation.metrics import EvalMetrics

console = Console()


def print_metrics(label: str, metrics: EvalMetrics) -> None:
    """Render a Rich table for *metrics* to stdout."""
    table = Table(title=label, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Precision", f"{metrics.precision:.3f}")
    table.add_row("Recall", f"{metrics.recall:.3f}")
    table.add_row("F1", f"{metrics.f1:.3f}")
    table.add_row("True Positives", str(metrics.true_positives))
    table.add_row("False Positives", str(metrics.false_positives))
    table.add_row("False Negatives", str(metrics.false_negatives))
    console.print(table)


def print_ablation(results: List[AblationResult]) -> None:
    """Render a Rich table comparing metrics across ablated configurations."""
    table = Table(title="Ablation Study", header_style="bold magenta")
    table.add_column("Disabled Level", style="bold")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")
    for r in results:
        table.add_row(
            r.disabled_level,
            f"{r.metrics.precision:.3f}",
            f"{r.metrics.recall:.3f}",
            f"{r.metrics.f1:.3f}",
        )
    console.print(table)


def save_json(output_path: Path, data: dict) -> None:
    """Write *data* as indented JSON to *output_path*, creating parent dirs as needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Report saved → {output_path}[/green]")
