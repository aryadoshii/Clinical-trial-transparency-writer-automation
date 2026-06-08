#!/usr/bin/env python3
"""Parse clean trial XML, inject synthetic errors, and persist everything to SQLite.

Run from the project root:
  python scripts/inject_errors.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from config import settings
from src.ingestion.db import init_db, insert_injected_error, insert_trial
from src.ingestion.error_injector import inject_errors
from src.ingestion.schema_normalizer import normalize
from src.ingestion.xml_parser import parse_directory

console = Console()


def main() -> None:
    init_db(settings.DB_PATH)

    console.print(f"[bold]Parsing XML from[/bold] {settings.DATA_DIR}")
    raw_records = parse_directory(settings.DATA_DIR)
    records = [normalize(r) for r in raw_records]
    console.print(f"Parsed and normalised [cyan]{len(records)}[/cyan] records")

    corrupted, labels = inject_errors(records)
    console.print(
        f"Injected [red]{len(labels)}[/red] errors across {len(corrupted)} records"
    )

    for record in corrupted:
        insert_trial(settings.DB_PATH, record)
    for label in labels:
        insert_injected_error(settings.DB_PATH, label)

    console.print(f"[green]Persisted to {settings.DB_PATH}[/green]")


if __name__ == "__main__":
    main()
