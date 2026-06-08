#!/usr/bin/env python3
"""Generate LLM explanations for a sample of high-severity validation findings.

Prerequisites: run scripts/inject_errors.py first so the DB is populated.

Run from the project root:
  python scripts/explain_sample.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from config import settings
from src.explainability.llm_client import explain
from src.explainability.prompt_builder import build_explanation_prompt
from src.ingestion.db import get_trial, init_db
from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation.engine import run as run_validation

console = Console()
_HIGH_SEVERITIES = {"CRITICAL", "HIGH"}
_OUTPUT_PATH = Path("outputs/sample_explanations.txt")


def _load_trials(db_path: Path) -> list[ClinicalTrialRecord]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    nct_ids = [row["nct_id"] for row in conn.execute("SELECT nct_id FROM trials")]
    conn.close()
    return [t for nct_id in nct_ids if (t := get_trial(db_path, nct_id)) is not None]


def main() -> None:
    init_db(settings.DB_PATH)
    trials = _load_trials(settings.DB_PATH)
    console.print(f"Loaded [cyan]{len(trials)}[/cyan] trials")

    results = run_validation(trials, settings.DB_PATH)

    # Collect (nct_id, finding) for CRITICAL/HIGH findings
    high_findings = [
        (result.nct_id, finding)
        for result in results
        for finding in result.findings
        if getattr(finding, "severity", "") in _HIGH_SEVERITIES
    ]

    sample = high_findings[:10]
    console.print(f"Explaining [yellow]{len(sample)}[/yellow] high-severity findings")

    no_keys = not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY
    output_lines: list[str] = []

    for nct_id, finding in sample:
        record = get_trial(settings.DB_PATH, nct_id)
        if record is None:
            continue

        # Build a single-finding ValidationResult for the prompt builder
        from src.validation.router import ValidationResult
        mock_result = ValidationResult(nct_id=nct_id, findings=[finding])
        prompt = build_explanation_prompt(record, mock_result)

        if no_keys:
            explanation_text = "[No API key configured]"
        else:
            explanation_text = explain(
                prompt,
                groq_api_key=settings.GROQ_API_KEY,
                gemini_api_key=settings.GEMINI_API_KEY,
            )

        header = (
            f"NCT ID    : {nct_id}\n"
            f"Field     : {finding.field}\n"
            f"Error Type: {finding.error_type}\n"
            f"Severity  : {finding.severity}\n"
            f"Explanation:\n{explanation_text}"
        )

        console.print(f"\n[bold]{nct_id}[/bold] | {finding.field} | {finding.error_type} | {finding.severity}")
        console.print(explanation_text)
        output_lines.append(header)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text("\n---\n".join(output_lines) + "\n")
    console.print(f"\n[green]Explanations saved → {_OUTPUT_PATH}[/green]")


if __name__ == "__main__":
    main()
