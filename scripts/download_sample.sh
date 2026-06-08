#!/usr/bin/env bash
# Fetch SAMPLE_SIZE clinical trial JSON files from the ClinicalTrials.gov v2 API
# and write each as <nct_id>.json under DATA_DIR.
#
# Usage:
#   SAMPLE_SIZE=200 DATA_DIR=./data bash scripts/download_sample.sh
set -euo pipefail

SAMPLE_SIZE="${SAMPLE_SIZE:-500}"
DATA_DIR="${DATA_DIR:-./data}"

mkdir -p "$DATA_DIR"
echo "Fetching ${SAMPLE_SIZE} trials → ${DATA_DIR} (ClinicalTrials.gov v2 API)"

python3 - <<PYEOF
import json
import os
import sys
from pathlib import Path

import requests

data_dir = Path(os.environ.get("DATA_DIR", "./data"))
sample_size = int(os.environ.get("SAMPLE_SIZE", 500))
page_size = 100  # v2 API max is 1000; keep small for reliability
base_url = "https://clinicaltrials.gov/api/v2/studies"

saved = 0
page_token = None

while saved < sample_size:
    want = min(page_size, sample_size - saved)
    params = {
        "format": "json",
        "pageSize": want,
        "fields": ",".join([
            "NCTId",
            "OfficialTitle",
            "BriefTitle",
            "OverallStatus",
            "StudyType",
            "Phase",
            "StartDate",
            "PrimaryCompletionDate",
            "EnrollmentCount",
            "InterventionName",
            "PrimaryOutcomeMeasure",
            "Condition",
            "LeadSponsorName",
            "Sex",
            "MinimumAge",
            "MaximumAge",
        ]),
    }
    if page_token:
        params["pageToken"] = page_token

    resp = requests.get(base_url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()

    studies = payload.get("studies", [])
    if not studies:
        print("No more studies returned — stopping early.")
        break

    for study in studies:
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        nct_id = ident.get("nctId", "").strip()
        if not nct_id:
            continue
        out_path = data_dir / f"{nct_id}.json"
        out_path.write_text(json.dumps(study, indent=2))
        saved += 1

    page_token = payload.get("nextPageToken")
    print(f"  saved {saved} / {sample_size} trials ...", flush=True)

    if not page_token:
        print("Reached last page of results.")
        break

print(f"Done — {saved} trials written to {data_dir}")
PYEOF
