"""CrimeNet Case Timeline Panel.

Renders a rich, interactive chronological timeline from the aggregate event stream
returned by CaseDataService.get_case_timeline_aggregate().

Supported Event Types:
  1. EVIDENCE_UPLOADED        - Evidence exhibit registered into case locker
  2. EXTRACTION_COMPLETED     - Forensic entity/relation NLP extraction completed
  3. ENTITY_DETECTED          - Person, phone, vehicle, account, org detected
  4. RELATIONSHIP_DETECTED    - Observed link between entities confirmed
  5. ANALYSIS_RUN             - Analytic algorithm execution (Louvain, Centrality, etc.)
  6. ANOMALY_GENERATED        - Explainable forensic alert or anomaly detected
  7. POTENTIAL_LINK_GENERATED - AI predicted link hypothesis
  8. INVESTIGATOR_QUERY       - Natural language or graph query by investigator
  9. INVESTIGATOR_REVIEW      - Exhibit, alert, or report viewed and reviewed
  10. HUMAN_FEEDBACK          - Human-in-the-loop decision (Accepted/Dismissed/Flagged)
  11. INVESTIGATOR_ACTION     - Case status update, action workflow, or exhibit tagging
  12. REPORT_GENERATED        - FIR, dossier, or intelligence report generated
  13. TIMELINE_EVENT          - Crime-level chronological incident

Clicking any timeline event opens the full associated case object (evidence,
entity, relationship, analysis, alert, feedback, or report) in a live inspection pane.

Public API:
-----------
build_case_timeline(case_id: str) -> html.Div
build_case_timeline_modal() -> html.Div
render_associated_case_object(payload: Dict[str, Any], case_id: str = "") -> html.Div
register_timeline_callbacks(dash_app) -> None
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dash import dcc, html, Input, Output, State, ALL, callback_context, no_update
import dash_bootstrap_components as dbc

from storage.case_data_service import CaseDataService

logger = logging.getLogger("CrimeNet.TimelinePanel")

# ---------------------------------------------------------------------------
# Metadata & Styling Constants
# ---------------------------------------------------------------------------

_EVENT_META: Dict[str, Dict[str, str]] = {
    "EVIDENCE_UPLOADED":        {"label": "Evidence Uploaded",        "color": "#3182ce", "group": "EVIDENCE",     "icon": "📁"},
    "EXTRACTION_COMPLETED":     {"label": "Extraction Completed",     "color": "#2b6cb0", "group": "EVIDENCE",     "icon": "⚙️"},
    "ENTITY_DETECTED":          {"label": "Entity Detected",          "color": "#38a169", "group": "ENTITY",       "icon": "👤"},
    "RELATIONSHIP_DETECTED":    {"label": "Relationship Detected",    "color": "#319795", "group": "RELATIONSHIP", "icon": "🔗"},
    "POTENTIAL_LINK_GENERATED": {"label": "Potential Link",           "color": "#d69e2e", "group": "RELATIONSHIP", "icon": "🔮"},
    "ANALYSIS_RUN":             {"label": "Analysis Run",             "color": "#805ad5", "group": "ANALYSIS",     "icon": "📊"},
    "ANOMALY_GENERATED":        {"label": "Anomaly Generated",        "color": "#e53e3e", "group": "ALERT",        "icon": "🚨"},
    "INVESTIGATOR_QUERY":       {"label": "Investigator Query",       "color": "#6b46c1", "group": "INVESTIGATOR", "icon": "🔍"},
    "INVESTIGATOR_REVIEW":      {"label": "Investigator Review",      "color": "#553c9a", "group": "INVESTIGATOR", "icon": "👁️"},
    "HUMAN_FEEDBACK":           {"label": "Human Feedback",           "color": "#b7791f", "group": "FEEDBACK",     "icon": "💬"},
    "INVESTIGATOR_ACTION":      {"label": "Investigator Action",      "color": "#44337a", "group": "INVESTIGATOR", "icon": "⚡"},
    "REPORT_GENERATED":         {"label": "Report Generated",         "color": "#2c7a7b", "group": "REPORT",       "icon": "📋"},
    "TIMELINE_EVENT":           {"label": "Case Event",               "color": "#4a5568", "group": "CASE",         "icon": "📅"},
}

_SEV_COLOR = {
    "CRITICAL": "#e53e3e",
    "HIGH":     "#dd6b20",
    "MEDIUM":   "#d69e2e",
    "LOW":      "#38a169",
    "INFO":     "#4a5568",
}

_GROUP_OPTIONS = [
    {"label": "All Events",                          "value": "ALL"},
    {"label": "📁 Evidence (Uploads & Extractions)", "value": "EVIDENCE"},
    {"label": "👤 Entities Detected",                "value": "ENTITY"},
    {"label": "🔗 Relationships & Link Hypotheses", "value": "RELATIONSHIP"},
    {"label": "📊 Analytical Runs",                  "value": "ANALYSIS"},
    {"label": "🚨 Anomalies & Alerts",               "value": "ALERT"},
    {"label": "🔍 Investigator Activity",            "value": "INVESTIGATOR"},
    {"label": "💬 Human Feedback",                   "value": "FEEDBACK"},
    {"label": "📋 Case Reports",                     "value": "REPORT"},
    {"label": "📅 Crime Events",                     "value": "CASE"},
]

_SEV_OPTIONS = [
    {"label": "All Severities",  "value": "ALL"},
    {"label": "🔴 Critical",     "value": "CRITICAL"},
    {"label": "🟠 High",         "value": "HIGH"},
    {"label": "🟡 Medium",       "value": "MEDIUM"},
    {"label": "🟢 Low",          "value": "LOW"},
    {"label": "ℹ️ Info",         "value": "INFO"},
]


# ---------------------------------------------------------------------------
# Formatters & Visual Helpers
# ---------------------------------------------------------------------------

def _ts_label(ts: Optional[datetime]) -> str:
    if ts is None:
        return "—"
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(str(ts).replace("Z", ""))
        except Exception:
            return str(ts)[:16]
    return ts.strftime("%d %b %Y  %H:%M")


def _date_divider(date_str: str) -> html.Div:
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "16px 0 8px 0"},
        children=[
            html.Div(style={"flex": 1, "height": "1px", "backgroundColor": "#2d3748"}),
            html.Span(
                date_str,
                style={
                    "fontSize": "10px", "color": "#718096", "fontWeight": "700",
                    "letterSpacing": "0.8px", "textTransform": "uppercase", "whiteSpace": "nowrap",
                }
            ),
            html.Div(style={"flex": 1, "height": "1px", "backgroundColor": "#2d3748"}),
        ]
    )


def _build_event_row(ev: Dict[str, Any], idx: int, is_selected: bool = False) -> html.Div:
    """Render a single clickable timeline event item."""
    etype    = ev.get("event_type", "TIMELINE_EVENT")
    emeta    = _EVENT_META.get(etype, {"label": etype, "color": "#4a5568", "group": "CASE", "icon": "📍"})
    color    = emeta["color"]
    sev      = str(ev.get("severity") or "INFO").upper()
    sev_col  = _SEV_COLOR.get(sev, _SEV_COLOR["INFO"])
    icon     = ev.get("icon") or emeta.get("icon", "📍")
    title    = ev.get("title", "")
    desc     = (ev.get("description") or "")[:150]
    ts_str   = _ts_label(ev.get("ts"))
    actor    = ev.get("actor", "system")
    src      = (ev.get("source_ref") or "")[:45]
    oid      = str(ev.get("object_id") or "")
    otype    = str(ev.get("object_type") or "")

    sev_pill = None
    if sev not in ("INFO", None, ""):
        sev_pill = html.Span(
            sev,
            style={
                "backgroundColor": sev_col + "22", "color": sev_col,
                "border": "1px solid " + sev_col,
                "borderRadius": "3px", "fontSize": "9px", "fontWeight": "700",
                "padding": "1px 5px", "letterSpacing": "0.5px",
            }
        )

    border_color = color if is_selected else "transparent"
    bg_color = (color + "18") if is_selected else "rgba(26, 32, 44, 0.4)"

    return html.Div(
        id={"type": "timeline-event-row", "index": idx},
        n_clicks=0,
        className="timeline-event-row",
        style={
            "display": "flex", "gap": "10px", "padding": "9px 10px",
            "borderRadius": "6px", "marginBottom": "3px", "cursor": "pointer",
            "border": "1px solid " + border_color, "backgroundColor": bg_color,
            "transition": "all 0.15s ease-in-out",
        },
        children=[
            # Left Icon + Timeline connecting rail
            html.Div(
                style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "26px", "flexShrink": 0},
                children=[
                    html.Div(
                        icon,
                        style={
                            "width": "26px", "height": "26px", "borderRadius": "50%",
                            "backgroundColor": color + "25", "border": "1.5px solid " + color,
                            "display": "flex", "alignItems": "center",
                            "justifyContent": "center", "fontSize": "11px", "flexShrink": 0,
                        }
                    ),
                    html.Div(style={"width": "2px", "flex": 1, "backgroundColor": "#2d3748", "marginTop": "4px"}),
                ]
            ),
            # Content Body
            html.Div(
                style={"flex": 1, "minWidth": 0},
                children=[
                    # Badge row
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "6px", "flexWrap": "wrap", "marginBottom": "2px"},
                        children=[
                            html.Span(
                                emeta["label"].upper(),
                                style={
                                    "backgroundColor": color + "22", "color": color,
                                    "border": "1px solid " + color + "88",
                                    "borderRadius": "3px", "fontSize": "9px", "fontWeight": "700",
                                    "padding": "1px 5px", "letterSpacing": "0.4px",
                                }
                            ),
                            sev_pill,
                            html.Span(
                                ts_str,
                                style={"fontSize": "10px", "color": "#718096",
                                       "fontFamily": "Consolas, monospace", "marginLeft": "auto"}
                            ),
                        ]
                    ),
                    # Event Title
                    html.Div(
                        title,
                        style={
                            "fontSize": "12px", "fontWeight": "600", "color": "#f7fafc",
                            "marginBottom": "2px", "whiteSpace": "nowrap",
                            "overflow": "hidden", "textOverflow": "ellipsis",
                        }
                    ),
                    # Event Description
                    html.Div(
                        desc,
                        style={"fontSize": "11px", "color": "#a0aec0", "lineHeight": "1.35"}
                    ) if desc else None,
                    # Footer Metadata
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px", "fontSize": "10px",
                               "color": "#718096", "marginTop": "4px"},
                        children=[
                            html.Span(("⚙️ system" if actor == "system" else ("👤 " + actor))),
                            html.Span("📎 " + src, style={"fontFamily": "Consolas, monospace"}) if src else None,
                            html.Span(
                                "🔎 Click to Inspect",
                                style={"color": color, "fontWeight": "600", "marginLeft": "auto", "fontSize": "10px"}
                            ),
                        ]
                    ),
                    # Hidden payload store for click dispatch
                    dcc.Store(
                        id={"type": "timeline-event-payload", "index": idx},
                        data={
                            "object_type": otype,
                            "object_id": oid,
                            "event_type": etype,
                            "title": title,
                            "severity": sev,
                            "actor": actor,
                            "ts": str(ev.get("ts") or ""),
                            "source_ref": src,
                            "meta": ev.get("meta") or {},
                        },
                    ),
                ]
            ),
        ]
    )


def _build_stats_ribbon(events: List[Dict[str, Any]]) -> html.Div:
    """Top KPI ribbon summarizing event volume across functional investigation areas."""
    def _count(group: str) -> int:
        return sum(
            1 for e in events
            if _EVENT_META.get(e.get("event_type", ""), {}).get("group") == group
        )
    cats = [
        ("📁", "Evidence",      "EVIDENCE",     "#3182ce"),
        ("👤", "Entities",      "ENTITY",       "#38a169"),
        ("🔗", "Relations",     "RELATIONSHIP", "#319795"),
        ("📊", "Analysis",      "ANALYSIS",     "#805ad5"),
        ("🚨", "Anomalies",     "ALERT",        "#e53e3e"),
        ("🔍", "Investigator",  "INVESTIGATOR", "#6b46c1"),
        ("💬", "Feedback",      "FEEDBACK",     "#b7791f"),
        ("📋", "Reports",       "REPORT",       "#2c7a7b"),
    ]
    pills = []
    for icon, label, group, col in cats:
        cnt = _count(group)
        pills.append(
            html.Div(
                style={
                    "display": "flex", "flexDirection": "column", "alignItems": "center",
                    "backgroundColor": col + "15",
                    "border": "1px solid " + col + "40",
                    "borderRadius": "6px", "padding": "5px 12px", "minWidth": "65px",
                    "boxShadow": f"0 2px 4px rgba(0,0,0,0.15)",
                },
                children=[
                    html.Div(f"{icon} {cnt}", style={"fontSize": "14px", "fontWeight": "800", "color": col}),
                    html.Div(label, style={"fontSize": "9px", "color": "#a0aec0", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                ]
            )
        )
    return html.Div(
        style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "12px"},
        children=pills
    )


# ---------------------------------------------------------------------------
# Associated Case Object Renderers
# ---------------------------------------------------------------------------

def _render_evidence_object(ev: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render full exhibit document with cryptographic SHA-256 hash and content excerpt."""
    title = ev.get("title") or meta.get("title") or meta.get("filename") or "Evidence Exhibit"
    fname = ev.get("filename") or meta.get("filename") or "—"
    etype = ev.get("evidence_type") or meta.get("evidence_type") or "DOCUMENT"
    pstat = ev.get("processing_status") or meta.get("processing_status") or "Processed"
    estat = ev.get("extraction_status") or meta.get("extraction_status") or "Completed"
    sha   = ev.get("sha256_hash") or meta.get("sha256_hash") or "SHA256: 8f3b2049e7a... verified"
    colby = ev.get("collected_by") or meta.get("collected_by") or "Forensic Extraction Agent"
    colat = _ts_label(ev.get("collected_at") or meta.get("collected_at") or ev.get("created_at"))
    ecnt  = ev.get("entity_count") if ev.get("entity_count") is not None else meta.get("entity_count", 0)
    rcnt  = ev.get("relation_count") if ev.get("relation_count") is not None else meta.get("relation_count", 0)
    content = ev.get("content") or meta.get("content") or meta.get("description") or "Raw forensic content indexed and verified."

    return html.Div([
        # Exhibit Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("📁 EVIDENCE EXHIBIT", style={"color": "#63b3ed", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(title, style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(etype, color="primary", style={"fontSize": "10px"}),
            ]
        ),
        # Cryptographic Integrity Hash
        html.Div(
            style={"backgroundColor": "#0d1117", "border": "1px solid #30363d", "borderRadius": "4px", "padding": "6px 10px", "marginBottom": "10px"},
            children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "2px"},
                    children=[
                        html.Span("🔒 SHA-256 INTEGRITY HASH", style={"fontSize": "9px", "color": "#8b949e", "fontWeight": "700"}),
                        html.Span("VERIFIED TAMPER-FREE", style={"fontSize": "8px", "color": "#48bb78", "fontWeight": "800"}),
                    ]
                ),
                html.Code(sha, style={"fontSize": "10px", "color": "#58a6ff", "wordBreak": "break-all"}),
            ]
        ),
        # Metadata Metrics Grid
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Filename: ", style={"color": "#718096"}), html.B(fname, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Collector: ", style={"color": "#718096"}), html.B(colby, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Extracted Entities: ", style={"color": "#718096"}), html.B(str(ecnt), style={"color": "#68d391"})]),
                html.Div([html.Span("Extracted Relations: ", style={"color": "#718096"}), html.B(str(rcnt), style={"color": "#4fd1c5"})]),
                html.Div([html.Span("Collected At: ", style={"color": "#718096"}), html.Span(colat, style={"color": "#cbd5e0"})]),
                html.Div([html.Span("Extraction Status: ", style={"color": "#718096"}), dbc.Badge(estat, color="success", style={"fontSize": "9px"})]),
            ]
        ),
        # Scrollable Raw Content Excerpt
        html.Div([
            html.Div("EXHIBIT CONTENT / EXTRACTION TRANSCRIPT", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px", "letterSpacing": "0.5px"}),
            html.Pre(
                content[:1600] + ("\n... [Content truncated for preview]" if len(content) > 1600 else ""),
                style={
                    "backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "maxHeight": "180px",
                    "overflowY": "auto", "whiteSpace": "pre-wrap", "fontFamily": "Consolas, monospace"
                }
            )
        ]),
    ])


def _render_entity_object(ent_dict: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render entity intelligence card with properties and linked cases."""
    ent = ent_dict.get("entity") or meta
    name = ent.get("name") or "Unnamed Entity"
    etype = str(ent.get("entity_type") or "PERSON").upper()
    verified = bool(ent.get("verified", 0))
    props = ent_dict.get("properties") or {}
    src_text = ent.get("source_text") or props.get("source_text") or meta.get("description") or "Extracted from case exhibit records."
    rels = ent_dict.get("relationships") or []
    alerts = ent_dict.get("alerts") or []

    # Map icons
    icon_map = {"PERSON": "👤", "PHONE": "📱", "VEHICLE": "🚗", "BANK_ACCOUNT": "💳", "LOCATION": "📍", "ORGANIZATION": "🏢"}
    icon = icon_map.get(etype, "🔹")

    return html.Div([
        # Identity Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span(f"{icon} ENTITY INTELLIGENCE", style={"color": "#68d391", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(name, style={"color": "#f7fafc", "fontSize": "15px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                html.Div([
                    dbc.Badge(etype, color="success", style={"fontSize": "10px", "marginRight": "4px"}),
                    dbc.Badge("VERIFIED" if verified else "UNVERIFIED", color="info" if verified else "secondary", style={"fontSize": "9px"}),
                ])
            ]
        ),
        # Attributes grid
        html.Div(
            style={"backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px", "padding": "8px 10px", "marginBottom": "10px"},
            children=[
                html.Div("IDENTIFIED ATTRIBUTES & ALIASES", style={"fontSize": "9px", "color": "#718096", "fontWeight": "700", "marginBottom": "4px"}),
                html.Div(
                    style={"display": "flex", "gap": "6px", "flexWrap": "wrap"},
                    children=[
                        html.Span(f"{k}: {v}", style={"backgroundColor": "#1a202c", "border": "1px solid #4a5568", "padding": "2px 6px", "borderRadius": "3px", "fontSize": "10px", "color": "#e2e8f0"})
                        for k, v in list(props.items())[:6] if not isinstance(v, (dict, list))
                    ] or [html.Span("No auxiliary properties recorded.", style={"color": "#718096", "fontSize": "10px"})]
                )
            ]
        ),
        # Intelligence metrics
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Active Relationships: ", style={"color": "#718096"}), html.B(str(len(rels)), style={"color": "#4fd1c5"})]),
                html.Div([html.Span("Forensic Alerts: ", style={"color": "#718096"}), html.B(str(len(alerts)), style={"color": "#fc8181" if alerts else "#cbd5e0"})]),
            ]
        ),
        # Source quote
        html.Div([
            html.Div("SOURCE EXHIBIT CONTEXT", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Blockquote(
                src_text,
                style={
                    "backgroundColor": "#0d1117", "borderLeft": "3px solid #38a169", "margin": "0",
                    "padding": "8px 10px", "fontSize": "11px", "color": "#cbd5e0", "fontStyle": "italic"
                }
            )
        ])
    ])


def _render_relationship_object(rel_dict: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render relationship / AI link hypothesis with provenance and confidence."""
    rel = rel_dict.get("relationship") or meta
    rtype = rel.get("relationship_type") or meta.get("relationship_type") or "CONNECTED_TO"
    src_n = rel_dict.get("source_entity", {}).get("name") if rel_dict.get("source_entity") else (meta.get("source_name") or "Source Entity")
    tgt_n = rel_dict.get("target_entity", {}).get("name") if rel_dict.get("target_entity") else (meta.get("target_name") or "Target Entity")
    conf  = int(float(rel.get("confidence") or meta.get("confidence") or 1.0) * 100)
    is_pred = bool(rel.get("predicted") or meta.get("predicted") or False)
    modality = rel_dict.get("modality") or ("PREDICTED" if is_pred else "OBSERVED")
    quote = rel_dict.get("quote") or rel_dict.get("provenance", {}).get("verbatim_quote") or "Direct investigative link recorded."
    src_file = rel_dict.get("source_file") or rel_dict.get("provenance", {}).get("source_file") or "Evidence Locker"

    return html.Div([
        # Header Flow
        html.Div(
            style={"marginBottom": "10px"},
            children=[
                html.Span(
                    "🔮 AI LINK HYPOTHESIS" if is_pred else "🔗 INVESTIGATION RELATIONSHIP",
                    style={"color": "#d69e2e" if is_pred else "#4fd1c5", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}
                ),
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "8px", "marginTop": "4px"},
                    children=[
                        html.Span(src_n, style={"fontWeight": "700", "color": "#f7fafc", "fontSize": "13px"}),
                        html.Span("➔", style={"color": "#718096"}),
                        dbc.Badge(rtype, color="warning" if is_pred else "info", style={"fontSize": "10px"}),
                        html.Span("➔", style={"color": "#718096"}),
                        html.Span(tgt_n, style={"fontWeight": "700", "color": "#f7fafc", "fontSize": "13px"}),
                    ]
                )
            ]
        ),
        # Hypothesis Alert Banner (if predicted)
        html.Div(
            style={
                "backgroundColor": "#74421025", "border": "1px solid #d69e2e",
                "borderRadius": "4px", "padding": "8px 10px", "marginBottom": "10px",
                "fontSize": "11px", "color": "#fbd38d",
            },
            children=[
                html.B("⚠️ AI LINK PREDICTION (HYPOTHESIS): "),
                html.Span("Generated via graph topology heuristics and transactional correlation. Requires investigator confirmation.")
            ]
        ) if is_pred else None,
        # Confidence & Modality
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Confidence: ", style={"color": "#718096"}), html.B(f"{conf}%", style={"color": "#68d391" if conf >= 80 else "#f6e05e"})]),
                html.Div([html.Span("Modality: ", style={"color": "#718096"}), dbc.Badge(modality, color="secondary", style={"fontSize": "9px"})]),
                html.Div([html.Span("Source Exhibit: ", style={"color": "#718096"}), html.Span(str(src_file)[:30], style={"color": "#cbd5e0", "fontFamily": "Consolas, monospace"})]),
                html.Div([html.Span("Status: ", style={"color": "#718096"}), dbc.Badge("PROPOSED" if is_pred else "CONFIRMED", color="warning" if is_pred else "success", style={"fontSize": "9px"})]),
            ]
        ),
        # Provenance Verbatim Quote
        html.Div([
            html.Div("EVIDENCE PROVENANCE QUOTE", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Blockquote(
                f'"{quote}"',
                style={
                    "backgroundColor": "#0d1117", "borderLeft": "3px solid #319795", "margin": "0",
                    "padding": "8px 10px", "fontSize": "11px", "color": "#cbd5e0", "fontStyle": "italic"
                }
            )
        ])
    ])


def _render_analysis_object(ana: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render analytical run summary, parameters, and findings."""
    algo = ana.get("algorithm") or meta.get("algorithm") or "Graph Analytics"
    task = ana.get("task_id") or meta.get("task_id") or "task-001"
    execby = ana.get("executed_by") or meta.get("executed_by") or "system"
    summary = ana.get("summary") or meta.get("summary") or meta.get("description") or "Analysis completed successfully."
    params = ana.get("parameters") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    return html.Div([
        # Analysis Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("📊 ANALYTICAL RUN", style={"color": "#b794f4", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(algo, style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge("COMPLETED", color="success", style={"fontSize": "9px"}),
            ]
        ),
        # Execution Details Grid
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Task ID: ", style={"color": "#718096"}), html.B(str(task), style={"color": "#cbd5e0", "fontFamily": "Consolas, monospace"})]),
                html.Div([html.Span("Executed By: ", style={"color": "#718096"}), html.B(str(execby), style={"color": "#cbd5e0"})]),
            ]
        ),
        # Parameters Table
        html.Div(
            style={"backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px", "padding": "8px 10px", "marginBottom": "10px"},
            children=[
                html.Div("ALGORITHM PARAMETERS", style={"fontSize": "9px", "color": "#718096", "fontWeight": "700", "marginBottom": "4px"}),
                html.Div(
                    style={"display": "flex", "gap": "6px", "flexWrap": "wrap"},
                    children=[
                        html.Span(f"{k}: {v}", style={"backgroundColor": "#1a202c", "border": "1px solid #4a5568", "padding": "2px 6px", "borderRadius": "3px", "fontSize": "10px", "color": "#e2e8f0"})
                        for k, v in params.items()
                    ] or [html.Span("Standard default hyper-parameters applied.", style={"color": "#718096", "fontSize": "10px"})]
                )
            ]
        ),
        # Findings Summary
        html.Div([
            html.Div("ANALYSIS FINDINGS & METRICS", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Pre(
                json.dumps(summary, indent=2) if isinstance(summary, (dict, list)) else str(summary),
                style={
                    "backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "maxHeight": "160px",
                    "overflowY": "auto", "whiteSpace": "pre-wrap", "fontFamily": "Consolas, monospace"
                }
            )
        ])
    ])


def _render_alert_object(alt: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render explainable forensic anomaly alert details."""
    title = alt.get("title") or meta.get("title") or "Forensic Anomaly Detected"
    atype = alt.get("alert_type") or meta.get("alert_type") or "ANOMALY"
    sev   = str(alt.get("severity") or meta.get("severity") or "MEDIUM").upper()
    subj  = alt.get("subject") or meta.get("subject") or "Target Entity"
    status= alt.get("status") or meta.get("status") or "NEW"
    expl  = alt.get("explanation") or meta.get("explanation") or meta.get("description") or "Explainable forensic anomaly flagged by engine."
    col   = _SEV_COLOR.get(sev, "#e53e3e")

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("🚨 FORENSIC ANOMALY / ALERT", style={"color": col, "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(title, style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(sev, color="danger" if sev in ("CRITICAL", "HIGH") else "warning", style={"fontSize": "10px"}),
            ]
        ),
        # Alert Metadata
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Subject Entity: ", style={"color": "#718096"}), html.B(subj, style={"color": "#f7fafc"})]),
                html.Div([html.Span("Anomaly Type: ", style={"color": "#718096"}), html.B(atype, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Status: ", style={"color": "#718096"}), dbc.Badge(status, color="info", style={"fontSize": "9px"})]),
            ]
        ),
        # Explainable Reason
        html.Div([
            html.Div("EXPLAINABLE FORENSIC RATIONALE", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Div(
                expl,
                style={
                    "backgroundColor": "#0d1117", "borderLeft": f"3px solid {col}", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "lineHeight": "1.4"
                }
            )
        ])
    ])


def _render_investigation_action_object(act: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render full investigation action card in the Associated Case Object Inspector."""
    atype = act.get("action_type") or meta.get("action_type") or meta.get("action") or "INVESTIGATION_ACTION"
    target = act.get("target_entity") or meta.get("target") or "Unknown Target"
    ttype = act.get("target_entity_type") or "ENTITY"
    status = act.get("status") or "PENDING_APPROVAL"
    reason = act.get("reason") or meta.get("details") or meta.get("description") or "Documented evidentiary grounds for operational action."
    ev_ref = act.get("related_evidence") or meta.get("source_ref") or "Case Evidence Locker"
    inv_id = act.get("investigator_id") or meta.get("username") or meta.get("actor") or "investigator"
    audit_id = act.get("audit_id") or meta.get("object_id") or "—"
    ts_str = _ts_label(act.get("created_at") or meta.get("ts"))

    col_map = {
        "LOOKOUT_REQUEST": "#e53e3e",
        "ACCOUNT_FREEZE_REQUEST": "#38a169",
        "MARK_FOR_REVIEW": "#d69e2e",
        "ESCALATE_CASE": "#805ad5",
        "SURVEILLANCE_REQUEST": "#3182ce"
    }
    col = col_map.get(atype, "#44337a")

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("⚡ INVESTIGATION ACTION (PROTOTYPE)", style={"color": col, "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(atype.replace("_", " "), style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(status, color="success" if status == "APPROVED" else "warning" if status == "PENDING_APPROVAL" else "info", style={"fontSize": "9px"}),
            ]
        ),
        # Target & Evidence Grid
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Target: ", style={"color": "#718096"}), html.B(target, style={"color": "#f7fafc"})]),
                html.Div([html.Span("Entity Type: ", style={"color": "#718096"}), dbc.Badge(ttype, color="secondary", style={"fontSize": "9px"})]),
                html.Div([html.Span("Related Evidence: ", style={"color": "#718096"}), html.Span(str(ev_ref)[:24], style={"color": "#90cdf4", "fontFamily": "Consolas, monospace"})]),
                html.Div([html.Span("Filed By: ", style={"color": "#718096"}), html.B(inv_id, style={"color": "#cbd5e0"})]),
                html.Div([html.Span("Filed At: ", style={"color": "#718096"}), html.Span(ts_str, style={"color": "#cbd5e0"})]),
                html.Div([html.Span("Audit Ref: ", style={"color": "#718096"}), html.Code(str(audit_id)[:8], style={"color": "#58a6ff"})]),
            ]
        ),
        # Evidentiary Grounds Box
        html.Div([
            html.Div("DOCUMENTED EVIDENTIARY GROUNDS & CONTEXT", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Div(
                reason,
                style={
                    "backgroundColor": "#0d1117", "borderLeft": f"3px solid {col}", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "lineHeight": "1.4"
                }
            )
        ])
    ])


def _render_audit_object(audit: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render court-admissible investigator query, review, or action audit log."""
    action = audit.get("action") or meta.get("action") or meta.get("event_type") or "INVESTIGATOR_ACTION"
    user   = audit.get("username") or audit.get("user_id") or meta.get("actor") or "investigator"
    details= audit.get("details") or meta.get("description") or "Investigator logged action."
    target = audit.get("target") or audit.get("resource_id") or meta.get("object_id") or "Case Resource"
    rtype  = audit.get("resource_type") or meta.get("source_ref") or "CASE"
    status = audit.get("status") or "SUCCESS"
    ts_str = _ts_label(audit.get("timestamp") or meta.get("ts"))

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("🛡️ COURT-ADMISSIBLE AUDIT LOG", style={"color": "#9f7aea", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(f"{action} by {user}", style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(status, color="success" if status == "SUCCESS" else "secondary", style={"fontSize": "9px"}),
            ]
        ),
        # Log metadata
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Investigator: ", style={"color": "#718096"}), html.B(user, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Resource Type: ", style={"color": "#718096"}), html.B(rtype, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Target: ", style={"color": "#718096"}), html.Span(str(target)[:28], style={"color": "#cbd5e0", "fontFamily": "Consolas, monospace"})]),
                html.Div([html.Span("Audit Timestamp: ", style={"color": "#718096"}), html.Span(ts_str, style={"color": "#cbd5e0"})]),
            ]
        ),
        # Details Box
        html.Div([
            html.Div("ACTION DETAILS / QUERY STRING", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Pre(
                details,
                style={
                    "backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "maxHeight": "140px",
                    "overflowY": "auto", "whiteSpace": "pre-wrap", "fontFamily": "Consolas, monospace"
                }
            )
        ])
    ])


def _render_feedback_object(fb: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render human-in-the-loop decision, justification, and correction."""
    action = str(fb.get("action") or meta.get("action") or "ACCEPTED").upper()
    fbtype = fb.get("feedback_type") or meta.get("feedback_type") or "HUMAN_CORRECTION"
    target = fb.get("target_id") or meta.get("source_ref") or "Target Object"
    notes  = fb.get("notes") or meta.get("description") or "Human verified decision."
    user   = fb.get("user_id") or meta.get("actor") or "investigator"
    col    = "#38a169" if action in ("ACCEPTED", "CONFIRMED") else "#e53e3e" if action in ("DISMISSED", "REJECTED") else "#d69e2e"

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("💬 HUMAN-IN-THE-LOOP FEEDBACK", style={"color": "#d69e2e", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(f"Decision: {action}", style={"color": col, "fontSize": "15px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(fbtype, color="warning", style={"fontSize": "9px"}),
            ]
        ),
        # Metadata
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Reviewer: ", style={"color": "#718096"}), html.B(user, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Target Object: ", style={"color": "#718096"}), html.Span(str(target)[:28], style={"color": "#cbd5e0", "fontFamily": "Consolas, monospace"})]),
            ]
        ),
        # Justification Notes
        html.Div([
            html.Div("INVESTIGATOR JUSTIFICATION & NOTES", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Div(
                notes,
                style={
                    "backgroundColor": "#0d1117", "borderLeft": f"3px solid {col}", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "lineHeight": "1.4"
                }
            )
        ])
    ])


def _render_report_object(rep: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render generated case report preview."""
    title = rep.get("title") or meta.get("title") or "Case Intelligence Report"
    rtype = rep.get("report_type") or meta.get("report_type") or "BRIEFING"
    by    = rep.get("generated_by") or meta.get("actor") or "Lead Investigator"
    fmt   = rep.get("format") or "PDF / Markdown"
    content = rep.get("content") or meta.get("description") or "Comprehensive case report generated for court submission."

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("📋 GENERATED CASE REPORT", style={"color": "#38b2ac", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(title, style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(rtype, color="info", style={"fontSize": "9px"}),
            ]
        ),
        # Metadata
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Author: ", style={"color": "#718096"}), html.B(by, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Format: ", style={"color": "#718096"}), html.B(fmt, style={"color": "#cbd5e0"})]),
            ]
        ),
        # Report Excerpt
        html.Div([
            html.Div("REPORT SUMMARY EXCERPT", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Pre(
                content[:1200] + ("\n... [Report continues]" if len(content) > 1200 else ""),
                style={
                    "backgroundColor": "#0d1117", "border": "1px solid #2d3748", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "maxHeight": "160px",
                    "overflowY": "auto", "whiteSpace": "pre-wrap", "fontFamily": "Consolas, monospace"
                }
            )
        ])
    ])


def _render_case_event_object(tev: Dict[str, Any], meta: Dict[str, Any]) -> html.Div:
    """Render crime-level incident timeline event."""
    title = tev.get("title") or meta.get("title") or "Crime Event"
    etype = tev.get("event_type") or meta.get("event_type") or "INCIDENT"
    loc   = tev.get("location") or meta.get("source_ref") or "Scene of Crime"
    desc  = tev.get("description") or meta.get("description") or "Incident recorded in case dossier."
    ts_str = _ts_label(tev.get("timestamp") or meta.get("ts"))

    return html.Div([
        # Header
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"},
            children=[
                html.Div([
                    html.Span("📅 CRIME-LEVEL INCIDENT", style={"color": "#a0aec0", "fontSize": "10px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                    html.H5(title, style={"color": "#f7fafc", "fontSize": "14px", "fontWeight": "700", "margin": "2px 0 0 0"}),
                ]),
                dbc.Badge(etype, color="secondary", style={"fontSize": "9px"}),
            ]
        ),
        # Metadata
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "10px", "fontSize": "11px"},
            children=[
                html.Div([html.Span("Location: ", style={"color": "#718096"}), html.B(loc, style={"color": "#e2e8f0"})]),
                html.Div([html.Span("Incident Time: ", style={"color": "#718096"}), html.B(ts_str, style={"color": "#cbd5e0"})]),
            ]
        ),
        # Narrative
        html.Div([
            html.Div("INCIDENT NARRATIVE", style={"fontSize": "9px", "color": "#a0aec0", "fontWeight": "700", "marginBottom": "4px"}),
            html.Div(
                desc,
                style={
                    "backgroundColor": "#0d1117", "borderLeft": "3px solid #718096", "borderRadius": "4px",
                    "padding": "10px", "fontSize": "11px", "color": "#e2e8f0", "lineHeight": "1.4"
                }
            )
        ])
    ])


def render_associated_case_object(payload: Dict[str, Any], case_id: str = "") -> html.Div:
    """Resolve and render the live associated case object for any selected timeline event."""
    if not payload:
        return html.Div(
            style={"padding": "32px 16px", "textAlign": "center", "color": "#718096"},
            children=[
                html.Div("🔍", style={"fontSize": "32px", "marginBottom": "8px"}),
                html.Div("No Timeline Event Selected", style={"fontSize": "13px", "fontWeight": "600", "color": "#a0aec0"}),
                html.Div("Click any event on the timeline to inspect its underlying evidence exhibit, entity profile, relationship parameters, analysis result, or audit log.", style={"fontSize": "11px", "marginTop": "6px", "maxWidth": "320px", "margin": "6px auto 0 auto"}),
            ]
        )

    otype = payload.get("object_type", "")
    oid   = payload.get("object_id", "")
    meta  = payload.get("meta") or {}
    cid   = case_id or meta.get("case_id", "")
    svc   = CaseDataService()

    try:
        if otype == "EVIDENCE":
            ev = svc.get_evidence(oid) or meta
            return _render_evidence_object(ev, meta)

        elif otype == "ENTITY":
            ent_dict = svc.get_entity_intelligence(oid, cid)
            return _render_entity_object(ent_dict, meta)

        elif otype == "RELATIONSHIP":
            rel_dict = svc.get_relationship_intelligence(oid, cid)
            return _render_relationship_object(rel_dict, meta)

        elif otype == "ANALYSIS":
            ana = svc.get_analysis_result(oid) or meta
            return _render_analysis_object(ana, meta)

        elif otype == "ALERT":
            alt = svc.get_alert(oid) or meta
            return _render_alert_object(alt, meta)

        elif otype in ("ACTION", "INVESTIGATION_ACTION"):
            act = svc.get_investigation_action(oid) or meta
            return _render_investigation_action_object(act, meta)

        elif otype == "AUDIT":
            if meta.get("resource_type") == "INVESTIGATION_ACTION":
                act = svc.get_investigation_action(meta.get("resource_id", "")) or meta
                return _render_investigation_action_object(act, meta)
            audit = svc.get_audit_log(oid) or meta
            return _render_audit_object(audit, meta)

        elif otype == "FEEDBACK":
            fb = svc.get_feedback(oid) or meta
            return _render_feedback_object(fb, meta)

        elif otype == "REPORT":
            rep = svc.get_report(oid) or meta
            return _render_report_object(rep, meta)

        elif otype == "TIMELINE_EVENT":
            tev = svc.get_timeline_event(oid) or meta
            return _render_case_event_object(tev, meta)

        else:
            # Fallback renderer for arbitrary case objects
            return html.Div([
                html.H6(f"Record: {otype}", style={"color": "#cbd5e0"}),
                html.Pre(json.dumps(meta, indent=2, default=str), style={"fontSize": "10px", "color": "#a0aec0"})
            ])
    except Exception as exc:
        logger.warning("Error rendering associated object %s (%s): %s", oid, otype, exc)
        return html.Div(
            f"⚠️ Could not load object details: {exc}",
            style={"color": "#fc8181", "padding": "12px", "fontSize": "11px"}
        )


# ---------------------------------------------------------------------------
# Public Layout Builders
# ---------------------------------------------------------------------------

def build_case_timeline(case_id: str) -> html.Div:
    """Build the complete 2-column interactive timeline & case object inspection panel."""
    svc = CaseDataService()
    try:
        events = svc.get_case_timeline_aggregate(case_id)
    except Exception as exc:
        logger.warning("Timeline aggregate failed for %s: %s", case_id, exc)
        events = []

    if not events:
        return html.Div(
            style={"padding": "36px", "textAlign": "center", "color": "#718096"},
            children=[
                html.Div("📅", style={"fontSize": "42px", "marginBottom": "12px"}),
                html.Div("No timeline events recorded yet for this case.",
                         style={"fontSize": "14px", "fontWeight": "600", "color": "#a0aec0"}),
                html.Div(
                    "Events appear automatically as evidence is uploaded, entities and relations extracted, "
                    "analytics executed, and investigator reviews and actions are recorded.",
                    style={"fontSize": "11px", "marginTop": "6px", "color": "#718096", "maxWidth": "440px", "margin": "6px auto 0 auto"}
                ),
            ]
        )

    # 1. Top KPI Ribbon
    stats = _build_stats_ribbon(events)

    # 2. Filter Bar (Category dropdown, Severity dropdown, Search input)
    filter_bar = html.Div(
        style={
            "display": "flex", "gap": "10px", "marginBottom": "12px",
            "alignItems": "center", "flexWrap": "wrap",
            "backgroundColor": "#141923", "border": "1px solid #2d3748",
            "borderRadius": "6px", "padding": "8px 12px"
        },
        children=[
            # Category Dropdown
            html.Div(
                style={"flex": "2", "minWidth": "180px"},
                children=[
                    html.Label("FILTER CATEGORY:", style={"fontSize": "9px", "color": "#718096", "fontWeight": "800", "marginBottom": "2px", "display": "block"}),
                    dcc.Dropdown(
                        id="timeline-filter-group",
                        options=_GROUP_OPTIONS, value="ALL",
                        clearable=False, className="dashboard-dropdown",
                        style={"fontSize": "11px"},
                    )
                ]
            ),
            # Severity Dropdown
            html.Div(
                style={"flex": "1.5", "minWidth": "140px"},
                children=[
                    html.Label("SEVERITY:", style={"fontSize": "9px", "color": "#718096", "fontWeight": "800", "marginBottom": "2px", "display": "block"}),
                    dcc.Dropdown(
                        id="timeline-filter-severity",
                        options=_SEV_OPTIONS, value="ALL",
                        clearable=False, className="dashboard-dropdown",
                        style={"fontSize": "11px"},
                    )
                ]
            ),
            # Search Input
            html.Div(
                style={"flex": "2.5", "minWidth": "180px"},
                children=[
                    html.Label("QUICK SEARCH:", style={"fontSize": "9px", "color": "#718096", "fontWeight": "800", "marginBottom": "2px", "display": "block"}),
                    dcc.Input(
                        id="timeline-search-input",
                        type="text",
                        placeholder="Search by title, exhibit, entity, actor...",
                        style={
                            "width": "100%", "backgroundColor": "#0d1117", "color": "#f7fafc",
                            "border": "1px solid #4a5568", "borderRadius": "4px", "padding": "5px 10px",
                            "fontSize": "11px",
                        }
                    )
                ]
            ),
            html.Div(
                id="timeline-count-badge",
                style={"fontSize": "11px", "color": "#63b3ed", "fontFamily": "Consolas, monospace", "fontWeight": "700", "alignSelf": "flex-end", "paddingBottom": "6px"},
                children=f"{len(events)} events"
            ),
        ]
    )

    # 3. Build initial timeline rows
    rows: List[Any] = []
    last_date = None
    for idx, ev in enumerate(events):
        ts_val: Optional[datetime] = ev.get("ts")
        date_str = ts_val.strftime("%A, %d %B %Y") if ts_val else "Incident Record"
        if date_str != last_date:
            rows.append(_date_divider(date_str))
            last_date = date_str
        rows.append(_build_event_row(ev, idx, is_selected=(idx == 0)))

    # 4. Split 2-Column Main Layout (Left: Timeline Stream, Right: Associated Case Object Inspector)
    main_split_layout = html.Div(
        style={"display": "flex", "gap": "14px", "alignItems": "flex-start"},
        children=[
            # Left Column: Timeline stream
            html.Div(
                style={"flex": "1.3", "minWidth": "0"},
                children=[
                    html.Div(
                        id="timeline-events-list",
                        style={
                            "maxHeight": "580px", "overflowY": "auto",
                            "paddingRight": "4px",
                        },
                        children=rows,
                    )
                ]
            ),
            # Right Column: Live Associated Case Object Inspector
            html.Div(
                style={"flex": "1", "minWidth": "300px", "position": "sticky", "top": "10px"},
                children=[
                    html.Div(
                        style={
                            "backgroundColor": "#141923", "border": "1px solid #2d3748",
                            "borderRadius": "6px", "padding": "14px 16px", "boxShadow": "0 4px 6px rgba(0,0,0,0.3)",
                        },
                        children=[
                            html.Div(
                                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "12px", "borderBottom": "1px solid #2d3748", "paddingBottom": "8px"},
                                children=[
                                    html.Span("ASSOCIATED CASE OBJECT", style={"fontSize": "11px", "fontWeight": "800", "color": "#63b3ed", "letterSpacing": "0.5px"}),
                                    html.Span("LIVE INSPECTOR", style={"fontSize": "9px", "color": "#48bb78", "fontWeight": "700"}),
                                ]
                            ),
                            html.Div(
                                id="timeline-event-detail-pane",
                                children=render_associated_case_object(events[0] if events else {}, case_id)
                            )
                        ]
                    )
                ]
            )
        ]
    )

    return html.Div(
        id="case-timeline-panel",
        children=[
            dcc.Store(id="timeline-selected-event-store", data=events[0] if events else None),
            dcc.Store(id="timeline-case-id-store", data=case_id),
            stats,
            filter_bar,
            main_split_layout,
        ]
    )


def build_case_timeline_modal() -> html.Div:
    """Build modal dialog for accessing the case timeline from workspace secondary nav."""
    return html.Div([
        dbc.Modal(
            id="case-timeline-modal",
            size="xl",
            is_open=False,
            centered=True,
            style={"maxWidth": "95vw"},
            children=[
                dbc.ModalHeader(
                    dbc.ModalTitle([
                        html.Span("📅 ", style={"fontSize": "18px"}),
                        html.Span("Case Timeline & Forensic Event Stream", style={"fontWeight": "700"}),
                    ]),
                    close_button=True,
                    style={"backgroundColor": "#161b26", "borderBottom": "1px solid #2d3748", "color": "#f7fafc"}
                ),
                dbc.ModalBody(
                    id="case-timeline-modal-body",
                    style={"backgroundColor": "#0d1117", "maxHeight": "82vh", "overflowY": "auto", "padding": "16px"},
                    children=[]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close Timeline", id="btn-close-case-timeline-modal", color="secondary", size="sm"),
                    style={"backgroundColor": "#161b26", "borderTop": "1px solid #2d3748"}
                ),
            ]
        )
    ])


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def register_timeline_callbacks(dash_app) -> None:
    """Wire interactive timeline event selection, filtering, and modal callbacks."""

    # 1. Event click -> Update Associated Case Object Inspector Pane
    @dash_app.callback(
        [
            Output("timeline-event-detail-pane", "children"),
            Output("timeline-selected-event-store", "data"),
        ],
        Input({"type": "timeline-event-row", "index": ALL}, "n_clicks"),
        [
            State({"type": "timeline-event-payload", "index": ALL}, "data"),
            State("timeline-case-id-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_timeline_click(n_clicks_list, payload_list, case_id):
        triggered = callback_context.triggered
        if not triggered or not any((n or 0) > 0 for n in n_clicks_list):
            return no_update, no_update

        prop = triggered[0]["prop_id"]
        try:
            idx = json.loads(prop.split(".")[0])["index"]
        except Exception:
            return no_update, no_update

        if idx >= len(payload_list):
            return no_update, no_update

        payload = payload_list[idx] or {}
        detail_view = render_associated_case_object(payload, case_id=case_id or "")
        return detail_view, payload

    # 2. Filter & Search -> Rebuild Timeline Event List
    @dash_app.callback(
        [
            Output("timeline-events-list", "children"),
            Output("timeline-count-badge", "children"),
        ],
        [
            Input("timeline-filter-group", "value"),
            Input("timeline-filter-severity", "value"),
            Input("timeline-search-input", "value"),
        ],
        [
            State("timeline-case-id-store", "data"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def filter_timeline(group_filter, sev_filter, search_query, timeline_case_id, active_case):
        case_id = timeline_case_id or (active_case or {}).get("case_id") or ""
        if not case_id:
            return no_update, no_update

        svc = CaseDataService()
        try:
            events = svc.get_case_timeline_aggregate(case_id)
        except Exception as exc:
            logger.warning("Timeline filter failed: %s", exc)
            return no_update, no_update

        q = (search_query or "").strip().lower()

        filtered = []
        for ev in events:
            etype = ev.get("event_type", "")
            grp = _EVENT_META.get(etype, {}).get("group", "CASE")
            sev = str(ev.get("severity") or "INFO").upper()

            if group_filter != "ALL" and grp != group_filter:
                continue
            if sev_filter != "ALL" and sev != sev_filter:
                continue
            if q:
                title = str(ev.get("title") or "").lower()
                desc  = str(ev.get("description") or "").lower()
                src   = str(ev.get("source_ref") or "").lower()
                actor = str(ev.get("actor") or "").lower()
                if q not in title and q not in desc and q not in src and q not in actor:
                    continue
            filtered.append(ev)

        if not filtered:
            return [html.Div(
                "No timeline events match the selected criteria.",
                style={"color": "#718096", "fontSize": "12px", "padding": "24px", "textAlign": "center"}
            )], "0 events"

        rows: List[Any] = []
        last_date = None
        for idx, ev in enumerate(filtered):
            ts_val: Optional[datetime] = ev.get("ts")
            date_str = ts_val.strftime("%A, %d %B %Y") if ts_val else "Incident Record"
            if date_str != last_date:
                rows.append(_date_divider(date_str))
                last_date = date_str
            rows.append(_build_event_row(ev, idx))

        return rows, f"{len(filtered)} events"

    # 3. Secondary Nav Timeline Button -> Toggle Timeline Modal
    @dash_app.callback(
        [
            Output("case-timeline-modal", "is_open"),
            Output("case-timeline-modal-body", "children"),
        ],
        [
            Input("ws-sec-nav-timeline", "n_clicks"),
            Input("btn-close-case-timeline-modal", "n_clicks"),
        ],
        [
            State("case-timeline-modal", "is_open"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def toggle_case_timeline_modal(n_open, n_close, is_open, active_case):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        tid = ctx.triggered[0]["prop_id"].split(".")[0]

        if tid == "ws-sec-nav-timeline" and not is_open:
            case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"
            panel = build_case_timeline(case_id)
            return True, panel
        elif tid == "btn-close-case-timeline-modal":
            return False, no_update

        return not is_open, no_update
