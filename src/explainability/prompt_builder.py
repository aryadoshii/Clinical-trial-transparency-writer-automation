"""Build LLM prompts that explain validation findings for a given trial record."""
from __future__ import annotations

from src.ingestion.xml_parser import ClinicalTrialRecord
from src.validation.router import ValidationResult


def build_explanation_prompt(
    record: ClinicalTrialRecord, result: ValidationResult
) -> str:
    """Return a prompt asking the LLM to explain each validation finding in plain language."""
    finding_lines = "\n".join(
        f"  - [{f.error_type}] field={f.field}" for f in result.findings
    )
    return (
        f"You are a clinical trial data quality expert.\n\n"
        f"Trial: {record.nct_id} — {record.official_title or 'untitled'}\n\n"
        f"The following data quality issues were detected:\n{finding_lines}\n\n"
        f"For each issue:\n"
        f"  1. Explain why it is a problem.\n"
        f"  2. Suggest the most likely corrective action.\n"
        f"  3. Note any regulatory implications (e.g. ICH E6, FDA 21 CFR Part 11).\n\n"
        f"Be concise and use non-technical language where possible."
    )
