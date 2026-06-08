"""TrialTransparency CLI entry point.

Commands:
  ingest    — parse XML files, normalise, and load into SQLite
  validate  — run validation engine over all trials in the DB
  evaluate  — run evaluation and print precision/recall/F1
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config import settings


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_ingest(args: argparse.Namespace) -> None:
    """Parse XML files, normalise, and upsert into the database."""
    from src.ingestion.db import init_db, insert_trial
    from src.ingestion.schema_normalizer import normalize
    from src.ingestion.xml_parser import parse_directory

    init_db(settings.DB_PATH)
    data_dir = Path(args.data_dir) if args.data_dir else settings.DATA_DIR
    records = parse_directory(data_dir)
    normalized = [normalize(r) for r in records]
    for record in normalized:
        insert_trial(settings.DB_PATH, record)
    print(f"Ingested {len(normalized)} records into {settings.DB_PATH}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Run the validation engine over all trials stored in the database."""
    print("validate: run scripts/run_eval.py for full validation + evaluation")


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Compute and display evaluation metrics against injected ground truth."""
    print("evaluate: run scripts/run_eval.py for full evaluation report")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trial-transparency",
        description="Clinical trial data validation system",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Parse XML files and load into DB")
    ingest_p.add_argument(
        "--data-dir",
        default=None,
        metavar="PATH",
        help="Directory containing ClinicalTrials.gov XML files (overrides DATA_DIR)",
    )
    ingest_p.set_defaults(func=cmd_ingest)

    validate_p = sub.add_parser("validate", help="Run validation engine")
    validate_p.set_defaults(func=cmd_validate)

    evaluate_p = sub.add_parser("evaluate", help="Run evaluation and print metrics")
    evaluate_p.set_defaults(func=cmd_evaluate)

    return parser


def main() -> None:
    _setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
