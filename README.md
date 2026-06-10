# 🏥 TrialTransparency

> Clinical trial data validation — deterministic rules meet LLM explainability.

Built against the ClinicalTrials.gov v2 API. On 500 trials with seeded synthetic error injection: 
**Recall = 0.961**, **F1 = 0.555**, **FORMAT_ERROR F1 = 0.926**.

---

## What it does

Clinical trial records are messy. Dates in wrong formats, missing outcome fields, completion dates that predate the study start, male patients enrolled in pregnancy trials. These aren't hypothetical — they show up in the public registry.

TrialTransparency runs every record through a four-layer rule engine, flags what's wrong, and uses an LLM to explain each finding in plain language — tailored to whoever's reading it (data manager, clinical investigator, or sponsor).

---

## Dashboard

Select a trial from the database or upload your own file. Watch the validation layers run one by one. Inspect findings. Get an LLM explanation. Download the original or the auto-corrected record.

**Input panel + live pipeline**
![Validation pipeline and input panel](frontend/assets/pipeline.png)

**Findings table + LLM explanation + download**
![Results panel with findings table and download buttons](frontend/assets/results.png)

```bash
streamlit run streamlit_app.py
```

---

## How it works

```
ClinicalTrials.gov v2 API
        │
        ▼
┌─────────────────────┐
│  Tier 1 — Ingestion │  Parse → Normalise → Inject errors (eval only)
└─────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  Tier 2 — Validation engine                              │
│                                                          │
│  L1 Field presence   →  Is the field even there?        │
│  L2 Format checks    →  Is the date actually a date?    │
│  L3 Temporal logic   →  Does the timeline make sense?   │
│  L4 Cross-field      →  Do the fields agree with each   │
│                         other?                          │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Tier 3 — Explainability │  Groq Llama 3.3 70B → role-aware explanation
│                          │  Gemini 2.0 Flash fallback · disk cache
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Tier 4 — Evaluation     │  Per-category P/R/F1 · ablation · FP attribution
└──────────────────────────┘
```

### Tier 1 — Ingestion

Trials come in as JSON from the ClinicalTrials.gov v2 API, each parsed into a `ClinicalTrialRecord` Pydantic model (15 fields: identifiers, dates, enrollment, phase, conditions, outcomes, eligibility, sponsor). A normalisation pass irons out date formats, canonicalises phase labels, and title-cases status strings.

For evaluation, a seeded error injector corrupts a copy of the clean records at known rates and stores ground-truth labels in SQLite — so every eval run is exactly reproducible.

### Tier 2 — Validation engine

Four independent layers, each returning typed findings:

| Layer | What it catches | Example |
|---|---|---|
| **L1 — field presence** | Mandatory fields missing or empty | `primary_outcomes = []` on a completed trial |
| **L2 — format checks** | Malformed values | `start_date = "31-13-2020"` |
| **L3 — temporal logic** | Impossible sequences | `completion_date < start_date` |
| **L4 — cross-field** | Fields that contradict each other | `gender = "Male"`, `conditions = ["pregnancy"]` |

L1 is context-aware: `phase` and `enrollment` are only required for interventional trials. `start_date` is only flagged when the trial's status implies it has already started.

Each layer is fully independent — any single one can be removed for ablation without touching the others.

### Tier 3 — LLM explainability

CRITICAL and HIGH findings get a role-aware explanation via Groq (Llama 3.3 70B). The prompt changes depending on who's asking:

- **Data manager** — specific field, rule violated, exact corrective step
- **Clinical investigator** — plain language, patient safety angle
- **Sponsor** — regulatory risk, ICH E6 / FDA 21 CFR Part 11 traceability, timeline impact

Gemini 2.0 Flash is the fallback if Groq fails. Explanations are cached on disk by SHA-256 key `(error_type + field + severity + role)` — same error pattern across different trials reuses the cached explanation.

### Tier 4 — Evaluation harness

Error injection uses `seed=42` — run the eval twice, get identical numbers. Metrics are standard precision/recall/F1 over `(nct_id, error_type)` pairs. The harness also runs an ablation study (disable one layer at a time, measure F1 delta) and attributes every false positive back to the layer that produced it.

---

## Evaluation results

500 trials · 127 injected errors · seed=42

**Overall: Precision=0.390 | Recall=0.961 | F1=0.555**

### Per-category

| Category | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| MISSING_FIELD | 25 | 130 | 5 | 0.161 | 0.833 | 0.270 |
| FORMAT_ERROR | 63 | 10 | 0 | 0.863 | 1.000 | **0.926** |
| LOGICAL_CONTRADICTION | 17 | 18 | 0 | 0.486 | 1.000 | 0.654 |
| CROSS_FIELD_INCONSISTENCY | 17 | 33 | 0 | 0.340 | 1.000 | 0.507 |

### Ablation — what happens when you remove a layer

| Layer disabled | F1 | vs baseline |
|---|---:|---:|
| L1 — field presence | 0.681 | +0.126 ↑ |
| L2 — format | 0.322 | −0.233 ↓ |
| L3 — temporal logic | 0.519 | −0.036 ↓ |
| L4 — cross-field | 0.538 | −0.017 ↓ |

Removing L2 causes the sharpest drop — format checks are the most precise layer. Removing L1 actually *improves* F1, because L1 generates 70% of all false positives (fields that are legitimately absent in real-world records).

### Where the false positives come from

| Layer | FP count | % of total |
|---|---:|---:|
| L1 — field presence | 145 | 70.0% |
| L2 — format | 10 | 4.8% |
| L3 — temporal logic | 18 | 8.7% |
| L4 — cross-field | 34 | 16.4% |

### Three things worth knowing about these numbers

**FORMAT_ERROR is the strongest layer (F1=0.926).** The single biggest precision improvement came from relaxing the date regex from `^\d{4}-\d{2}-\d{2}$` to `^\d{4}(-\d{2}(-\d{2})?)?$` — the v2 API legitimately returns partial dates like `2023-06` or `2019` for trials where only month or year precision is recorded. That one change cut L2 false positives by ~80%.

**L1 produces 70% of all false positives — and that's a fundamental problem, not a fixable bug.** Whether a field is "missing" depends on the trial protocol, not just the study type. A missing `phase` field is valid for an observational study and an error for a Phase 3 intervention. The current study_type conditional handles the obvious case; getting further requires per-protocol rule sets the v2 API doesn't expose.

**Precision (0.390) is lower than recall (0.961) by design.** In clinical data validation, a missed error is worse than a spurious flag. The system errs toward over-detection — a reviewer clearing a false positive costs minutes; a missed integrity issue can invalidate a study.

---

## Limitations

- **Synthetic errors, not organic ones.** Injected errors follow known patterns at fixed rates. Real data quality issues from complex collection workflows — partial submissions, protocol amendments, transcription errors — may look different and be harder to catch.

- **500 trials from a single API page.** The sample isn't stratified by therapeutic area or trial type. Performance on oncology, rare disease, device trials, or expanded access records is untested.

- **L1 precision ceiling.** Mandatory-field checks without protocol context have a hard precision limit. Closing the gap requires richer metadata than the v2 API provides.

- **LLM explanations are unverified.** The explainability layer produces coherent, role-appropriate text — but hallucination risk is unquantified. Don't surface these to a clinical audience without review.

---

## Setup

```bash
uv sync
cp .env.example .env   # add GROQ_API_KEY and GEMINI_API_KEY
```

```bash
# 1. Fetch 500 trials
bash scripts/download_sample.sh

# 2. Inject synthetic errors + store ground truth
python scripts/inject_errors.py

# 3. Full eval: metrics + ablation + FP breakdown
python scripts/run_eval.py

# 4. LLM explanations for 10 high-severity findings
python scripts/explain_sample.py

# 5. Run tests
uv run pytest tests/ -v    # 13 tests

# 6. Launch dashboard
streamlit run streamlit_app.py
```

If both API keys are empty, `explain_sample.py` writes `[No API key configured]` and skips API calls.

---

## Stack

`Python 3.11+` · `uv` · `lxml` · `Pydantic v2` · `SQLite` · `Rich` · `Groq Llama 3.3 70B` · `Gemini 2.0 Flash` · `Streamlit` · `pytest`
