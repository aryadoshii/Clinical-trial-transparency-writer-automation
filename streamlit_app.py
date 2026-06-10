"""TrialTransparency — Streamlit dashboard."""
import sys

sys.path.insert(0, ".")

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# Must be the first Streamlit call.
st.set_page_config(
    page_title="TrialTransparency",
    layout="wide",
    page_icon="🏥",
)

st.markdown(
    """
    <style>
    /* ── Warm palette ────────────────────────────────────────────────────────
       #FAF6F0  warm ivory       (page background)
       #F0E6D6  warm beige       (card / panel surfaces)
       #E8D5BE  sand             (borders / dividers)
       #C05800  burnt orange     (primary accent / CTAs)
       #8B4513  saddle brown     (secondary accent / headings)
       #2C1A0E  espresso         (dark text / sidebar bg)
    ───────────────────────────────────────────────────────────────────────── */

    /* Page background */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #FAF6F0 !important;
    }
    [data-testid="stHeader"] {
        background-color: #FAF6F0 !important;
        border-bottom: 1px solid #E8D5BE;
    }

    /* Base text */
    body, .stMarkdown, .stText, p, li, label, div {
        color: #2C1A0E !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #2C1A0E !important;
    }

    /* Divider */
    hr {
        border-color: #E8D5BE !important;
        opacity: 1;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #2C1A0E !important;
        border-right: 1px solid #8B4513;
    }
    [data-testid="stSidebar"] * {
        color: #FAF6F0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #C05800 !important;
        font-size: 2rem !important;
    }

    /* Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid #E8D5BE !important;
        background-color: transparent !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: #8B4513 !important;
        font-weight: 600;
        background-color: transparent !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: #C05800 !important;
        border-bottom: 3px solid #C05800 !important;
        background-color: transparent !important;
    }

    /* Primary buttons (Run validation) */
    .stButton > button {
        background-color: #C05800 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 8px 20px !important;
        box-shadow: 0 2px 6px rgba(192,88,0,0.35) !important;
    }
    .stButton > button:hover {
        background-color: #8B4513 !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 8px rgba(139,69,19,0.4) !important;
    }

    /* Download buttons — distinct from primary */
    [data-testid="stDownloadButton"] > button {
        background-color: #F0E6D6 !important;
        color: #2C1A0E !important;
        border: 1.5px solid #8B4513 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 8px 20px !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #8B4513 !important;
        color: #FFFFFF !important;
        border-color: #8B4513 !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] > div > div {
        background-color: #FFFFFF !important;
        border: 1.5px solid #E8D5BE !important;
        color: #2C1A0E !important;
        border-radius: 8px !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 1.5px dashed #C05800 !important;
        border-radius: 8px !important;
        background-color: #F0E6D6 !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        border: 1px solid #E8D5BE !important;
        border-radius: 10px !important;
        background-color: #FFFFFF !important;
    }
    [data-testid="stExpander"] summary {
        color: #2C1A0E !important;
        font-weight: 600 !important;
        background-color: #F0E6D6 !important;
        border-radius: 10px !important;
    }

    /* Radio */
    [data-testid="stRadio"] label {
        color: #2C1A0E !important;
    }

    /* st.info — LLM explanation boxes */
    [data-testid="stInfo"] {
        background-color: #F0E6D6 !important;
        border-left: 4px solid #C05800 !important;
        color: #2C1A0E !important;
    }

    /* st.success */
    [data-testid="stSuccess"] {
        background-color: #EAF4E0 !important;
        border-left: 4px solid #5A8A1E !important;
        color: #2C1A0E !important;
    }

    /* st.warning */
    [data-testid="stWarning"] {
        background-color: #F5E8D4 !important;
        border-left: 4px solid #C05800 !important;
        color: #2C1A0E !important;
    }

    /* st.error */
    [data-testid="stError"] {
        border-left: 4px solid #8B4513 !important;
        color: #2C1A0E !important;
    }

    /* Caption */
    [data-testid="stCaptionContainer"] p {
        color: #8B4513 !important;
        font-size: 13px !important;
    }

    /* Metric */
    [data-testid="stMetricValue"] {
        color: #C05800 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #2C1A0E !important;
        font-weight: 600 !important;
    }

    /* Spinner text */
    [data-testid="stSpinner"] p {
        color: #8B4513 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

from config import settings
from src.explainability.llm_client import explain
from src.explainability.prompt_builder import build_explanation_prompt
from src.ingestion.db import get_trial
from src.ingestion.schema_normalizer import _parse_date, normalize
from src.ingestion.xml_parser import ClinicalTrialRecord, parse_trial_json, parse_trial_xml
from src.validation import l1_field, l2_format, l3_logic, l4_cross_field
from src.validation.router import ValidationResult

# ── Constants ─────────────────────────────────────────────────────────────────

_LAYER_CONFIGS = [
    ("L1", "Field Presence",   "mandatory field checks",   l1_field),
    ("L2", "Format Checks",    "date, id, enrollment",     l2_format),
    ("L3", "Temporal Logic",   "dates & age ranges",       l3_logic),
    ("L4", "Cross-Field",      "inter-field consistency",  l4_cross_field),
]

_LAYER_CLASS_MAP: Dict[str, str] = {
    "FieldFinding":       "L1",
    "FormatFinding":      "L2",
    "LogicFinding":       "L3",
    "CrossFieldFinding":  "L4",
}

_STATE_STYLES: Dict[str, Dict[str, str]] = {
    "idle":        {"bg": "#F0E6D6", "border": "#E8D5BE"},
    "running":     {"bg": "#FFF0E0", "border": "#C05800"},
    "done_clean":  {"bg": "#EAF4E0", "border": "#5A8A1E"},
    "done_issues": {"bg": "#FFF0E0", "border": "#C05800"},
}

_ICONS: Dict[str, str] = {
    "idle":        "○",
    "running":     "⏳",
    "done_clean":  "✓",
    "done_issues": "⚠",
}

_SEVERITY_STYLES: Dict[str, Dict[str, str]] = {
    "CRITICAL": {"bg": "#2C1A0E", "color": "#FAF6F0"},
    "HIGH":     {"bg": "#8B4513", "color": "#FFFFFF"},
    "MEDIUM":   {"bg": "#C05800", "color": "#FFFFFF"},
    # Aliases used by some finding classes
    "ERROR":    {"bg": "#8B4513", "color": "#FFFFFF"},
    "WARNING":  {"bg": "#C05800", "color": "#FFFFFF"},
}

_ACTION_MAP: Dict[str, str] = {
    "MISSING_FIELD":             "Add missing data",
    "FORMAT_ERROR":              "Correct format",
    "LOGICAL_CONTRADICTION":     "Resolve conflict",
    "CROSS_FIELD_INCONSISTENCY": "Verify fields",
}

_ROLE_CONTEXT: Dict[str, str] = {
    "data_manager": (
        "Explain this to a clinical data manager responsible for data "
        "cleaning and registry submissions."
    ),
    "clinical_investigator": (
        "Explain this to a clinical investigator running the trial who "
        "needs to understand the impact on study conduct."
    ),
    "sponsor": (
        "Explain this to a sponsor reviewing trial data quality for "
        "regulatory submission purposes."
    ),
}


# ── Helper functions ──────────────────────────────────────────────────────────

def render_layer_card(
    placeholder: Any,
    state: str,
    name: str,
    subtitle: str,
    count: int = 0,
) -> None:
    """Write a styled validation-layer card into *placeholder*."""
    s = _STATE_STYLES[state]
    icon = _ICONS[state]
    if state == "running":
        badge_text = "running…"
    elif state == "done_clean":
        badge_text = "✓ clean"
    elif state == "done_issues":
        badge_text = f"{count} issue{'s' if count != 1 else ''}"
    else:
        badge_text = "waiting"

    html = (
        f'<div style="background:{s["bg"]};border:1px solid {s["border"]};'
        f'border-radius:12px;padding:14px 12px;text-align:center;min-height:134px;">'
        f'  <div style="font-size:26px;margin-bottom:4px;">{icon}</div>'
        f'  <div style="font-size:13px;font-weight:600;margin-bottom:2px;">{name}</div>'
        f'  <div style="font-size:11px;color:#8B4513;margin-bottom:8px;">{subtitle}</div>'
        f'  <span style="display:inline-block;border-radius:99px;font-size:11px;'
        f'padding:2px 10px;background:{s["bg"]};border:1px solid {s["border"]};'
        f'color:{s["border"]};">{badge_text}</span>'
        f'</div>'
    )
    placeholder.markdown(html, unsafe_allow_html=True)


def render_metadata_card(record: ClinicalTrialRecord) -> None:
    """Render a bordered HTML card with key trial fields."""
    fields = [
        ("NCT ID",       record.nct_id),
        ("Status",       record.overall_status or "—"),
        ("Phase",        record.phase or "—"),
        ("Enrollment",   str(record.enrollment) if record.enrollment is not None else "—"),
        ("Start Date",   record.start_date or "—"),
        ("Completion",   record.completion_date or "—"),
        ("Sponsor",      record.sponsors or "—"),
    ]
    rows_html = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:7px 0;'
        f'border-bottom:1px solid #E8D5BE;">'
        f'<span style="color:#8B4513;font-size:12px;font-weight:500;">{k}</span>'
        f'<span style="font-weight:700;font-size:12px;color:#2C1A0E;text-align:right;'
        f'max-width:62%;word-break:break-word;">{v}</span></div>'
        for k, v in fields
    )
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E8D5BE;'
        f'border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(44,26,14,0.08);">'
        f'{rows_html}</div>',
        unsafe_allow_html=True,
    )


def render_findings_table(rows: List[Dict]) -> None:
    """Render a styled HTML table for validation findings."""
    header = (
        '<table style="width:100%;border-collapse:collapse;font-size:12px;'
        'border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(44,26,14,0.1);">'
        '<thead><tr style="background:#2C1A0E;">'
        '<th style="padding:10px 12px;text-align:left;color:#FAF6F0;font-weight:600;letter-spacing:0.03em;">Layer</th>'
        '<th style="padding:10px 12px;text-align:left;color:#FAF6F0;font-weight:600;letter-spacing:0.03em;">Field</th>'
        '<th style="padding:10px 12px;text-align:left;color:#FAF6F0;font-weight:600;letter-spacing:0.03em;">Detail</th>'
        '<th style="padding:10px 12px;text-align:left;color:#FAF6F0;font-weight:600;letter-spacing:0.03em;">Severity</th>'
        '<th style="padding:10px 12px;text-align:left;color:#FAF6F0;font-weight:600;letter-spacing:0.03em;">Action</th>'
        '</tr></thead><tbody>'
    )
    body = ""
    for i, row in enumerate(rows):
        sev = row["severity"]
        ss = _SEVERITY_STYLES.get(sev, _SEVERITY_STYLES["HIGH"])
        badge = (
            f'<span style="display:inline-block;border-radius:99px;font-size:11px;'
            f'padding:3px 10px;background:{ss["bg"]};color:{ss["color"]};'
            f'font-weight:700;letter-spacing:0.02em;">{sev}</span>'
        )
        action = _ACTION_MAP.get(row["error_type"], "Review")
        detail = row["detail"] or "—"
        row_bg = "#FFFFFF" if i % 2 == 0 else "#F7F0E8"
        body += (
            f'<tr style="background:{row_bg};border-bottom:1px solid #E8D5BE;">'
            f'<td style="padding:9px 12px;font-weight:700;color:#8B4513;">{row["layer"]}</td>'
            f'<td style="padding:9px 12px;font-family:monospace;color:#2C1A0E;font-size:12px;">{row["field"]}</td>'
            f'<td style="padding:9px 12px;color:#2C1A0E;">{detail}</td>'
            f'<td style="padding:9px 12px;">{badge}</td>'
            f'<td style="padding:9px 12px;color:#8B4513;font-weight:500;">{action}</td>'
            f'</tr>'
        )
    st.markdown(header + body + "</tbody></table>", unsafe_allow_html=True)


def get_nct_ids() -> List[str]:
    db_path = settings.DB_PATH
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT nct_id FROM trials ORDER BY nct_id").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def parse_uploaded_file(uploaded_file: Any) -> Optional[ClinicalTrialRecord]:
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)
    try:
        record = parse_trial_json(tmp_path) if suffix == ".json" else parse_trial_xml(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return record


def _finding_to_row(finding: Any) -> Dict:
    return {
        "layer":       _LAYER_CLASS_MAP.get(type(finding).__name__, "?"),
        "field":       finding.field,
        "detail":      getattr(finding, "detail", ""),
        "severity":    finding.severity,
        "error_type":  finding.error_type,
        "finding_obj": finding,
    }


def patch_record(record: ClinicalTrialRecord, findings: list) -> dict:
    """Return record.model_dump() with auto-patches and review annotations applied."""
    data = record.model_dump()
    auto_patched: List[str] = []
    requires_manual: List[str] = []
    flagged: List[str] = []

    for finding in findings:
        if finding.error_type == "FORMAT_ERROR" and finding.field in ["start_date", "completion_date"]:
            bad_val = data.get(finding.field)
            fixed = _parse_date(str(bad_val)) if bad_val is not None else None
            data[finding.field] = fixed
            auto_patched.append(finding.field)
        elif finding.error_type == "MISSING_FIELD":
            data.setdefault("__requires_manual_review__", []).append(finding.field)
            requires_manual.append(finding.field)
        elif finding.error_type in ["LOGICAL_CONTRADICTION", "CROSS_FIELD_INCONSISTENCY"]:
            detail = getattr(finding, "detail", "")
            data.setdefault("__flagged_for_review__", []).append(
                {"field": finding.field, "detail": detail}
            )
            flagged.append(f"{finding.field}: {detail}")

    data["__validation_report__"] = {
        "generated_by": "TrialTransparency",
        "total_findings": len(findings),
        "auto_patched": auto_patched,
        "requires_manual_review": requires_manual,
        "flagged_for_review": flagged,
    }
    return data


# ── Session state initialisation ──────────────────────────────────────────────

for _key, _default in [
    ("findings", None),
    ("record", None),
    ("layer_findings", {}),
    ("explanations", {}),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ── Sidebar ───────────────────────────────────────────────────────────────────

_findings: Optional[List] = st.session_state["findings"]
if _findings is not None:
    st.sidebar.title("Run Summary")
    st.sidebar.metric("Total findings", len(_findings))

    _sev_counts: Dict[str, int] = {}
    _layer_counts: Dict[str, int] = {}
    for _f in _findings:
        _sev_counts[_f.severity] = _sev_counts.get(_f.severity, 0) + 1
        _lyr = _LAYER_CLASS_MAP.get(type(_f).__name__, "?")
        _layer_counts[_lyr] = _layer_counts.get(_lyr, 0) + 1

    st.sidebar.markdown("**By severity**")
    for _sev in ["CRITICAL", "HIGH", "MEDIUM", "ERROR", "WARNING"]:
        if _sev in _sev_counts:
            st.sidebar.markdown(f"- {_sev}: **{_sev_counts[_sev]}**")

    st.sidebar.markdown("**By layer**")
    for _lyr in ["L1", "L2", "L3", "L4"]:
        if _lyr in _layer_counts:
            st.sidebar.markdown(f"- {_lyr}: **{_layer_counts[_lyr]}**")


# ── SECTION 1 — INPUT PANEL ───────────────────────────────────────────────────

st.markdown(
    '<h2 style="color:#2C1A0E;font-weight:700;margin-bottom:4px;letter-spacing:-0.01em;">🏥 TrialTransparency</h2>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B4513;margin-top:0;font-size:15px;">Clinical trial data validation · deterministic rules + LLM explainability</p>',
    unsafe_allow_html=True,
)
st.divider()

tab_select, tab_upload = st.tabs(["Select existing trial", "Upload file"])

_pending_record: Optional[ClinicalTrialRecord] = None
_run_clicked = False

with tab_select:
    nct_ids = get_nct_ids()
    if not nct_ids:
        st.warning(
            "No trials in database. Run: `python scripts/inject_errors.py` first."
        )
    else:
        selected_nct = st.selectbox("Select a trial", options=nct_ids)
        if st.button("Run validation", key="btn_select"):
            _rec = get_trial(settings.DB_PATH, selected_nct)
            if _rec is not None:
                _pending_record = _rec
                _run_clicked = True

with tab_upload:
    uploaded = st.file_uploader(
        "Upload a clinical trial file", type=["json", "xml"]
    )
    if uploaded is not None:
        if st.button("Run validation", key="btn_upload"):
            with st.spinner("Parsing file…"):
                _parsed = parse_uploaded_file(uploaded)
            if _parsed is None:
                st.error(
                    "Could not parse file — check that it is a valid "
                    "ClinicalTrials.gov XML or v2 JSON."
                )
            else:
                _pending_record = normalize(_parsed)
                _run_clicked = True

if _run_clicked and _pending_record is not None:
    st.session_state["_pending_record"] = _pending_record
    st.session_state["_run_triggered"] = True
    # Clear stale explanation cache for the new run
    st.session_state["explanations"] = {}


# ── SECTION 2 — PIPELINE ANIMATION ───────────────────────────────────────────

st.divider()
st.markdown("### Validation pipeline")

# Create placeholders via col.empty() — called directly on the column object
# so Streamlit flushes each markdown write immediately to the frontend.
col1, col2, col3, col4 = st.columns(4)
p1 = col1.empty()
p2 = col2.empty()
p3 = col3.empty()
p4 = col4.empty()
_placeholders: List[Any] = [p1, p2, p3, p4]

# Render resting state (idle or previous run results) before any animation.
_lf_map: Dict[str, List] = st.session_state.get("layer_findings", {})
for _i, (_lk, _name, _sub, _) in enumerate(_LAYER_CONFIGS):
    _lf = _lf_map.get(_lk)
    if _lf is None:
        render_layer_card(_placeholders[_i], "idle", _name, _sub)
    elif not _lf:
        render_layer_card(_placeholders[_i], "done_clean", _name, _sub)
    else:
        render_layer_card(_placeholders[_i], "done_issues", _name, _sub, len(_lf))

# Animation — sequential L1 → L2 → L3 → L4, one layer at a time.
# Each placeholder.markdown() call is flushed immediately; sleep lets the
# "running" frame render before we overwrite it with the "done" frame.
if st.session_state.get("_run_triggered"):
    _anim_record: ClinicalTrialRecord = st.session_state["_pending_record"]
    del st.session_state["_pending_record"]
    del st.session_state["_run_triggered"]

    _all_findings: List[Any] = []
    _new_lf: Dict[str, List] = {}

    # p1 → L1
    render_layer_card(p1, "running", _LAYER_CONFIGS[0][1], _LAYER_CONFIGS[0][2])
    time.sleep(0.6)
    _lf0 = l1_field.check(_anim_record)
    _new_lf["L1"] = _lf0
    _all_findings.extend(_lf0)
    render_layer_card(p1, "done_issues" if _lf0 else "done_clean",
                      _LAYER_CONFIGS[0][1], _LAYER_CONFIGS[0][2], len(_lf0))

    # p2 → L2
    render_layer_card(p2, "running", _LAYER_CONFIGS[1][1], _LAYER_CONFIGS[1][2])
    time.sleep(0.6)
    _lf1 = l2_format.check(_anim_record)
    _new_lf["L2"] = _lf1
    _all_findings.extend(_lf1)
    render_layer_card(p2, "done_issues" if _lf1 else "done_clean",
                      _LAYER_CONFIGS[1][1], _LAYER_CONFIGS[1][2], len(_lf1))

    # p3 → L3
    render_layer_card(p3, "running", _LAYER_CONFIGS[2][1], _LAYER_CONFIGS[2][2])
    time.sleep(0.6)
    _lf2 = l3_logic.check(_anim_record)
    _new_lf["L3"] = _lf2
    _all_findings.extend(_lf2)
    render_layer_card(p3, "done_issues" if _lf2 else "done_clean",
                      _LAYER_CONFIGS[2][1], _LAYER_CONFIGS[2][2], len(_lf2))

    # p4 → L4
    render_layer_card(p4, "running", _LAYER_CONFIGS[3][1], _LAYER_CONFIGS[3][2])
    time.sleep(0.6)
    _lf3 = l4_cross_field.check(_anim_record)
    _new_lf["L4"] = _lf3
    _all_findings.extend(_lf3)
    render_layer_card(p4, "done_issues" if _lf3 else "done_clean",
                      _LAYER_CONFIGS[3][1], _LAYER_CONFIGS[3][2], len(_lf3))

    st.session_state["findings"] = _all_findings
    st.session_state["record"] = _anim_record
    st.session_state["layer_findings"] = _new_lf
    st.rerun()


# ── SECTION 3 — RESULTS ───────────────────────────────────────────────────────

if st.session_state.get("findings") is not None:
    st.divider()
    st.markdown("### Results")

    _record: ClinicalTrialRecord = st.session_state["record"]
    _all_findings: List[Any] = st.session_state["findings"]

    _left, _right = st.columns([1, 2])

    with _left:
        st.markdown("**Trial metadata**")
        render_metadata_card(_record)

    with _right:
        if not _all_findings:
            st.success("No issues detected — this record is clean.")
        else:
            _rows = [_finding_to_row(_f) for _f in _all_findings]

            st.markdown(
                f"**{len(_all_findings)} finding"
                f"{'s' if len(_all_findings) != 1 else ''} detected**"
            )
            render_findings_table(_rows)
            st.markdown("")

            for _idx, _row in enumerate(_rows):
                _finding = _row["finding_obj"]
                _label = (
                    f"{_finding.field} — {_finding.error_type} [{_finding.severity}]"
                )
                with st.expander(_label):
                    _role = st.radio(
                        "Explain for:",
                        ["data_manager", "clinical_investigator", "sponsor"],
                        horizontal=True,
                        key=f"role_{_idx}_{_finding.nct_id}_{_finding.field}_{_finding.error_type}",
                    )
                    _explain_btn = st.button(
                        "Explain",
                        key=f"explain_{_idx}_{_finding.nct_id}_{_finding.field}_{_finding.error_type}",
                    )

                    _cache_key = (
                        _record.nct_id,
                        _finding.field,
                        _finding.error_type,
                        _role,
                    )
                    _cached = st.session_state["explanations"].get(_cache_key)

                    if _explain_btn:
                        _mock_result = ValidationResult(
                            nct_id=_record.nct_id, findings=[_finding]
                        )
                        _prompt = build_explanation_prompt(_record, _mock_result)
                        _full_prompt = (
                            _prompt
                            + f"\n\nAudience context: {_ROLE_CONTEXT[_role]}"
                        )
                        with st.spinner("Generating explanation…"):
                            _explanation = explain(
                                _full_prompt,
                                groq_api_key=settings.GROQ_API_KEY,
                                gemini_api_key=settings.GEMINI_API_KEY,
                            )
                        st.session_state["explanations"][_cache_key] = _explanation
                        st.info(_explanation)
                    elif _cached:
                        st.info(_cached)

        st.caption(
            "Download the original trial record or the auto-corrected version "
            "with validation annotations."
        )
        _dl_col1, _dl_col2 = st.columns(2)
        with _dl_col1:
            st.download_button(
                "Download original file",
                data=json.dumps(_record.model_dump(), indent=2, default=str),
                file_name=f"{_record.nct_id}_original.json",
                mime="application/json",
            )
        with _dl_col2:
            _corrected = patch_record(_record, _all_findings)
            st.download_button(
                "Download corrected file",
                data=json.dumps(_corrected, indent=2, default=str),
                file_name=f"{_record.nct_id}_corrected.json",
                mime="application/json",
            )
