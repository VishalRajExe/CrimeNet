"""CrimeNet Forensic Alerts Panel.

Builds the complete Alerts UI for the Case Investigation Workspace:
  - Isolation Forest anomaly results displayed as a rich, filterable table
  - Entity-type filters: Person / Organisation / Account / Vehicle / Location
  - Status filters: New / Reviewed / Dismissed / Confirmed
  - Severity badges: CRITICAL / HIGH / MEDIUM / LOW
  - Anomaly score bar (0–100 percentile rank)
  - Full-reason expandable drawer
  - One-click status transitions (Mark Reviewed / Dismiss / Confirm)
  - "Run Anomaly Detection" trigger button

FORENSIC DISCLAIMER — rendered prominently on the panel:
    An anomaly is a STATISTICAL SIGNAL only.
    It is NOT evidence of criminal activity.
    Every flagged entity MUST be independently verified
    by a qualified investigator before any action is taken.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

# ── Design tokens (dark theme consistent with CrimeNet) ─────────────────────
DARK_BG    = "#0f1117"
PANEL_BG   = "#1a202c"
BORDER_COL = "#2d3748"
TEXT_MAIN  = "#f7fafc"
TEXT_DIM   = "#a0aec0"
TEXT_MUTED = "#718096"

SEVERITY_COLOURS = {
    "CRITICAL": ("#e53e3e", "#fff5f5"),
    "HIGH":     ("#dd6b20", "#fffaf0"),
    "MEDIUM":   ("#d69e2e", "#fffff0"),
    "LOW":      ("#38a169", "#f0fff4"),
}

STATUS_COLOURS = {
    "NEW":       ("#63b3ed", "#1a202c"),
    "REVIEWED":  ("#9ae6b4", "#1a202c"),
    "DISMISSED": ("#718096", "#1a202c"),
    "CONFIRMED": ("#d6bcfa", "#1a202c"),
}

TYPE_ICONS = {
    "PERSON":       "👤",
    "ORGANIZATION": "🏢",
    "ACCOUNT":      "💳",
    "VEHICLE":      "🚗",
    "LOCATION":     "📍",
    "PHONE":        "📱",
    "EVENT":        "📅",
    "UNKNOWN":      "🔹",
}

ALERT_TYPE_LABELS = {
    "UNUSUAL_COMMUNICATION_ACTIVITY": "📞 Unusual Communication",
    "UNUSUAL_NETWORK_BEHAVIOUR":      "🕸️ Unusual Network Behaviour",
    "UNUSUAL_TRANSACTION_PATTERN":    "💸 Unusual Transaction Pattern",
    "HIGH_BETWEENNESS_ANOMALY":       "🔗 Hidden Intermediary",
    "DEGREE_OUTLIER":                 "📊 Degree Outlier",
}


# ── Helper builders ──────────────────────────────────────────────────────────

def _severity_badge(severity: str) -> html.Span:
    sev = (severity or "MEDIUM").upper()
    fg, bg = SEVERITY_COLOURS.get(sev, ("#a0aec0", "#2d3748"))
    return html.Span(
        sev,
        style={
            "backgroundColor": bg,
            "color": fg,
            "border": f"1px solid {fg}",
            "borderRadius": "4px",
            "padding": "1px 7px",
            "fontSize": "10px",
            "fontWeight": "700",
            "letterSpacing": "0.05em",
            "fontFamily": "monospace",
        }
    )


def _status_badge(status: str) -> html.Span:
    st = (status or "NEW").upper()
    fg, bg = STATUS_COLOURS.get(st, ("#a0aec0", "#2d3748"))
    return html.Span(
        st,
        style={
            "backgroundColor": bg,
            "color": fg,
            "border": f"1px solid {fg}",
            "borderRadius": "4px",
            "padding": "1px 7px",
            "fontSize": "10px",
            "fontWeight": "700",
            "letterSpacing": "0.05em",
        }
    )


def _score_bar(score: Optional[float], rank: Optional[float]) -> html.Div:
    """Mini score bar representing anomaly percentile rank (0–100)."""
    if rank is None and score is None:
        return html.Span("—", style={"color": TEXT_MUTED, "fontSize": "11px"})
    pct = float(rank or 0.0)
    colour = "#e53e3e" if pct >= 90 else "#dd6b20" if pct >= 70 else "#d69e2e" if pct >= 50 else "#63b3ed"
    label  = f"{pct:.0f}th pct"
    sc_str = f"  (raw: {score:.4f})" if score is not None else ""
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "6px", "minWidth": "130px"},
        children=[
            html.Div(
                style={"flex": "1", "height": "5px", "backgroundColor": "#2d3748", "borderRadius": "3px", "position": "relative"},
                children=[
                    html.Div(style={
                        "width": f"{min(pct, 100):.0f}%",
                        "height": "100%",
                        "backgroundColor": colour,
                        "borderRadius": "3px",
                    })
                ]
            ),
            html.Span(label + sc_str, style={"fontSize": "10px", "color": TEXT_DIM, "whiteSpace": "nowrap"}),
        ]
    )


def build_alert_row(alert: Dict[str, Any], idx: int) -> html.Div:
    """Build a single alert card row."""
    alert_id   = alert.get("alert_id", "")
    entity     = alert.get("entity") or "Unknown"
    e_type     = (alert.get("entity_type") or "UNKNOWN").upper()
    a_type     = alert.get("type") or "UNKNOWN"
    severity   = (alert.get("severity") or "MEDIUM").upper()
    status     = (alert.get("status") or "NEW").upper()
    reason     = alert.get("reason") or ""
    score      = alert.get("score")
    rank       = alert.get("anomaly_rank")
    source     = alert.get("source") or "IsolationForest"
    created    = str(alert.get("created_time") or "")[:16]
    review_t   = str(alert.get("review_time") or "")[:16]

    icon        = TYPE_ICONS.get(e_type, "🔹")
    a_label     = ALERT_TYPE_LABELS.get(a_type, a_type.replace("_", " ").title())

    # Trim reason for the collapsed view
    reason_preview = (reason or "")[:180] + ("…" if len(reason or "") > 180 else "")
    # Full reason in collapse
    reason_full = reason or ""

    collapse_id = f"alert-reason-collapse-{idx}"
    toggle_id   = f"alert-reason-toggle-{idx}"

    return html.Div(
        id=f"alert-row-{alert_id[:8] if alert_id else idx}",
        style={
            "backgroundColor": PANEL_BG,
            "border": f"1px solid {BORDER_COL}",
            "borderRadius": "6px",
            "padding": "12px 16px",
            "marginBottom": "10px",
            "transition": "box-shadow 0.2s ease",
        },
        children=[
            # ── Top row: Entity, Type badge, Severity, Status ─────────────
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "6px", "gap": "8px", "flexWrap": "wrap"},
                children=[
                    # Left: entity + icon + alert label
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span(icon, style={"fontSize": "15px"}),
                            html.Span(entity, style={"fontWeight": "700", "color": TEXT_MAIN, "fontSize": "13px"}),
                            html.Span(e_type, style={"color": TEXT_MUTED, "fontSize": "11px", "fontFamily": "monospace"}),
                            html.Span("·", style={"color": BORDER_COL}),
                            html.Span(a_label, style={"color": "#9ae6b4", "fontSize": "11px"}),
                        ]
                    ),
                    # Right: severity + status
                    html.Div(
                        style={"display": "flex", "gap": "6px", "alignItems": "center"},
                        children=[_severity_badge(severity), _status_badge(status)]
                    ),
                ]
            ),
            # ── Middle: score bar + source + times ───────────────────────
            html.Div(
                style={"display": "flex", "gap": "18px", "alignItems": "center", "marginBottom": "8px", "flexWrap": "wrap"},
                children=[
                    html.Div([html.Span("Score ", style={"color": TEXT_MUTED, "fontSize": "11px"}), _score_bar(score, rank)],
                             style={"display": "flex", "alignItems": "center", "gap": "4px"}),
                    html.Span(f"Source: {source}", style={"color": TEXT_MUTED, "fontSize": "11px"}),
                    html.Span(f"Detected: {created}", style={"color": TEXT_MUTED, "fontSize": "11px"}),
                    *([html.Span(f"Reviewed: {review_t}", style={"color": "#9ae6b4", "fontSize": "11px"})] if review_t else []),
                ]
            ),
            # ── Reason preview + toggle ───────────────────────────────────
            html.Div(
                style={"marginBottom": "8px"},
                children=[
                    html.P(reason_preview, style={"color": TEXT_DIM, "fontSize": "12px", "margin": "0 0 4px 0", "lineHeight": "1.5"}),
                    dbc.Button(
                        "Show full reason ▾",
                        id=toggle_id,
                        size="sm",
                        color="link",
                        style={"fontSize": "11px", "color": "#63b3ed", "padding": "0", "textDecoration": "none"},
                        n_clicks=0,
                    ),
                    dbc.Collapse(
                        html.Pre(
                            reason_full,
                            style={
                                "backgroundColor": "#0f1117",
                                "border": f"1px solid {BORDER_COL}",
                                "borderRadius": "4px",
                                "padding": "10px 12px",
                                "fontSize": "11px",
                                "color": "#e2e8f0",
                                "whiteSpace": "pre-wrap",
                                "marginTop": "6px",
                                "maxHeight": "180px",
                                "overflowY": "auto",
                            }
                        ),
                        id=collapse_id,
                        is_open=False,
                    ),
                ]
            ),
            # ── Action buttons ────────────────────────────────────────────
            html.Div(
                style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                children=[
                    dbc.Button("✅ Confirm",
                               id={"type": "btn-alert-confirm", "index": alert_id},
                               size="sm", color="success", outline=True,
                               style={"fontSize": "11px", "padding": "3px 10px"}),
                    dbc.Button("👁️ Mark Reviewed",
                               id={"type": "btn-alert-review", "index": alert_id},
                               size="sm", color="info", outline=True,
                               style={"fontSize": "11px", "padding": "3px 10px"}),
                    dbc.Button("🚫 Dismiss",
                               id={"type": "btn-alert-dismiss", "index": alert_id},
                               size="sm", color="secondary", outline=True,
                               style={"fontSize": "11px", "padding": "3px 10px"}),
                ]
            ),
        ]
    )


def build_alerts_panel(case_id: Optional[str] = None) -> html.Div:
    """
    Build the complete Forensic Alerts Panel for the Case Workspace.

    :param case_id: Active case ID (None = no case loaded yet).
    :returns: A Dash html.Div containing the full alerts UI.
    """
    return html.Div(
        id="alerts-panel-container",
        style={"padding": "18px", "backgroundColor": DARK_BG, "minHeight": "400px"},
        children=[

            # ── Disclaimer ────────────────────────────────────────────────
            html.Div(
                style={
                    "backgroundColor": "#2d1b00",
                    "border": "1px solid #744210",
                    "borderRadius": "6px",
                    "padding": "10px 14px",
                    "marginBottom": "18px",
                    "display": "flex",
                    "gap": "10px",
                    "alignItems": "flex-start",
                },
                children=[
                    html.Span("⚠️", style={"fontSize": "18px", "flexShrink": "0"}),
                    html.Div([
                        html.B("FORENSIC DISCLAIMER", style={"color": "#f6ad55", "fontSize": "12px", "display": "block", "marginBottom": "3px"}),
                        html.Span(
                            "An anomaly is a STATISTICAL SIGNAL only — it is NOT evidence of criminal activity. "
                            "Every flagged entity MUST be independently verified by a qualified investigator "
                            "before any operational or legal action is taken.",
                            style={"color": "#fbd38d", "fontSize": "11px", "lineHeight": "1.5"}
                        )
                    ])
                ]
            ),

            # ── Header + Run Detection button ─────────────────────────────
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
                children=[
                    html.Div([
                        html.H4("Forensic Anomaly Alerts", style={"color": TEXT_MAIN, "margin": "0 0 2px 0", "fontSize": "16px", "fontWeight": "700"}),
                        html.Span("Isolation Forest — Graph-structural & behavioural anomalies", style={"color": TEXT_MUTED, "fontSize": "11px"}),
                    ]),
                    html.Div(
                        style={"display": "flex", "gap": "8px"},
                        children=[
                            dbc.Button(
                                "🔍 Run Anomaly Detection",
                                id="btn-run-anomaly-detection",
                                color="warning",
                                size="sm",
                                style={"fontWeight": "600", "fontSize": "12px"},
                                n_clicks=0,
                            ),
                            dcc.Loading(
                                id="anomaly-detection-loading",
                                type="circle",
                                children=html.Div(id="anomaly-detection-status", style={"fontSize": "11px", "color": "#9ae6b4"}),
                                style={"display": "inline"},
                            ),
                        ]
                    ),
                ]
            ),

            # ── Filter Toolbar ────────────────────────────────────────────
            html.Div(
                style={
                    "backgroundColor": PANEL_BG,
                    "border": f"1px solid {BORDER_COL}",
                    "borderRadius": "6px",
                    "padding": "12px 16px",
                    "marginBottom": "16px",
                    "display": "flex",
                    "gap": "12px",
                    "alignItems": "center",
                    "flexWrap": "wrap",
                },
                children=[
                    # Entity type filter chips
                    html.Span("Entity:", style={"color": TEXT_MUTED, "fontSize": "12px", "fontWeight": "600"}),
                    dcc.Checklist(
                        id="alert-filter-entity-type",
                        options=[
                            {"label": "👤 Person",       "value": "PERSON"},
                            {"label": "🏢 Organisation", "value": "ORGANIZATION"},
                            {"label": "💳 Account",      "value": "ACCOUNT"},
                            {"label": "🚗 Vehicle",      "value": "VEHICLE"},
                            {"label": "📍 Location",     "value": "LOCATION"},
                        ],
                        value=[],
                        inline=True,
                        labelStyle={"fontSize": "12px", "color": TEXT_DIM, "marginRight": "12px", "cursor": "pointer"},
                        style={"display": "inline"},
                    ),
                    html.Span("|", style={"color": BORDER_COL}),
                    # Status filter
                    html.Span("Status:", style={"color": TEXT_MUTED, "fontSize": "12px", "fontWeight": "600"}),
                    dcc.Checklist(
                        id="alert-filter-status",
                        options=[
                            {"label": "🔵 New",       "value": "NEW"},
                            {"label": "🟢 Reviewed",  "value": "REVIEWED"},
                            {"label": "⚫ Dismissed", "value": "DISMISSED"},
                            {"label": "🟣 Confirmed", "value": "CONFIRMED"},
                        ],
                        value=["NEW", "REVIEWED"],
                        inline=True,
                        labelStyle={"fontSize": "12px", "color": TEXT_DIM, "marginRight": "12px", "cursor": "pointer"},
                        style={"display": "inline"},
                    ),
                    html.Span("|", style={"color": BORDER_COL}),
                    # Severity filter
                    dcc.Dropdown(
                        id="alert-filter-severity",
                        options=[
                            {"label": "All Severities", "value": "ALL"},
                            {"label": "🔴 Critical",    "value": "CRITICAL"},
                            {"label": "🟠 High",        "value": "HIGH"},
                            {"label": "🟡 Medium",      "value": "MEDIUM"},
                            {"label": "🟢 Low",         "value": "LOW"},
                        ],
                        value="ALL",
                        clearable=False,
                        style={"width": "160px", "fontSize": "12px", "backgroundColor": PANEL_BG},
                    ),
                ]
            ),

            # ── Alert notification store ──────────────────────────────────
            dcc.Store(id="alerts-status-update-store"),

            # ── Alert List (populated by callback) ───────────────────────
            dcc.Loading(
                id="alerts-list-loading",
                type="dot",
                children=html.Div(id="alerts-list-container",
                                  style={"minHeight": "100px"},
                                  children=[
                                      html.Div(
                                          style={"textAlign": "center", "color": TEXT_MUTED, "padding": "40px", "fontSize": "13px"},
                                          children=[
                                              html.Div("🔍", style={"fontSize": "32px", "marginBottom": "10px"}),
                                              html.Div("Open a case and run Anomaly Detection to see alerts.")
                                          ]
                                      )
                                  ])
            ),
        ]
    )


def render_alerts_list(
    alerts: List[Dict[str, Any]],
    entity_type_filter: Optional[List[str]] = None,
    status_filter: Optional[List[str]] = None,
    severity_filter: Optional[str] = None,
) -> html.Div:
    """
    Render the alerts list based on filter selections.

    Called from a Dash callback whenever filters change or after detection runs.

    :param alerts: Raw alert dicts (from list_alerts_filtered).
    :param entity_type_filter: Selected entity types (empty list = show all).
    :param status_filter: Selected statuses (empty list = show all).
    :param severity_filter: Selected severity or 'ALL'.
    :returns: html.Div containing alert rows.
    """
    if not alerts:
        return html.Div(
            style={"textAlign": "center", "color": TEXT_MUTED, "padding": "40px"},
            children=[
                html.Div("✅", style={"fontSize": "32px", "marginBottom": "10px"}),
                html.Div("No alerts match the current filters.", style={"fontSize": "13px"}),
            ]
        )

    # Apply filters client-side (server already filters, but keep UI-consistent)
    filtered = alerts
    if entity_type_filter:
        filtered = [a for a in filtered if (a.get("entity_type") or "UNKNOWN").upper() in entity_type_filter]
    if status_filter:
        filtered = [a for a in filtered if (a.get("status") or "NEW").upper() in status_filter]
    if severity_filter and severity_filter != "ALL":
        filtered = [a for a in filtered if (a.get("severity") or "MEDIUM").upper() == severity_filter.upper()]

    if not filtered:
        return html.Div(
            style={"textAlign": "center", "color": TEXT_MUTED, "padding": "40px"},
            children=[
                html.Div("🔍", style={"fontSize": "32px", "marginBottom": "10px"}),
                html.Div(f"No alerts match the current filters ({len(alerts)} total).", style={"fontSize": "13px"}),
            ]
        )

    count_str = f"{len(filtered)} alert{'s' if len(filtered) != 1 else ''}"
    if len(filtered) < len(alerts):
        count_str += f" (filtered from {len(alerts)})"

    return html.Div([
        html.Div(count_str, style={"color": TEXT_MUTED, "fontSize": "11px", "marginBottom": "10px"}),
        *[build_alert_row(a, i) for i, a in enumerate(filtered)]
    ])


def register_alerts_callbacks(dash_app):
    """Register all alerts panel Dash callbacks."""
    from dash import Input, Output, State, ctx, no_update
    from dash.exceptions import PreventUpdate

    # ── Toggle reason collapse ────────────────────────────────────────────
    # This is a pattern callback — one for each rendered row.
    # Because the number of rows is dynamic, we use a dcc.Store to signal
    # re-renders and register collapses through clientside callbacks.

    # ── Run anomaly detection ─────────────────────────────────────────────
    @dash_app.callback(
        Output("anomaly-detection-status", "children"),
        Output("alerts-list-container", "children", allow_duplicate=True),
        Input("btn-run-anomaly-detection", "n_clicks"),
        State("dossier-active-case-id-store", "data"),
        prevent_initial_call=True,
    )
    def run_anomaly_detection_callback(n_clicks, case_id):
        if not n_clicks or not case_id:
            raise PreventUpdate

        try:
            from storage.case_data_service import CaseDataService
            svc     = CaseDataService()
            results = svc.run_anomaly_detection(case_id, contamination=0.05, persist=True)
            if not results:
                return "⚠️ No anomalies detected (graph too small or no anomalies).", no_update

            alerts_all = svc.list_alerts_filtered(case_id)
            rendered   = render_alerts_list(alerts_all)
            return f"✅ {len(results)} anomal{'y' if len(results)==1 else 'ies'} detected.", rendered
        except Exception as exc:
            return f"❌ Error: {str(exc)[:100]}", no_update

    # ── Refresh alert list on filter change ──────────────────────────────
    @dash_app.callback(
        Output("alerts-list-container", "children"),
        Input("alert-filter-entity-type", "value"),
        Input("alert-filter-status",      "value"),
        Input("alert-filter-severity",    "value"),
        State("dossier-active-case-id-store",     "data"),
        prevent_initial_call=False,
    )
    def refresh_alerts_list(entity_types, statuses, severity, case_id):
        if not case_id:
            return html.Div(
                "Open a case workspace to view anomaly alerts.",
                style={"textAlign": "center", "color": TEXT_MUTED, "padding": "30px", "fontSize": "13px"}
            )
        try:
            from storage.case_data_service import CaseDataService
            svc    = CaseDataService()
            alerts = svc.list_alerts_filtered(
                case_id,
                entity_types=entity_types or None,
                statuses=statuses or None,
                severity=severity if severity != "ALL" else None,
            )
            return render_alerts_list(alerts)
        except Exception as exc:
            return html.Div(f"⚠️ Error loading alerts: {exc}", style={"color": "#fc8181", "padding": "20px", "fontSize": "12px"})

    # ── Status update: Confirm / Review / Dismiss ───────────────────────
    @dash_app.callback(
        Output("alerts-status-update-store", "data"),
        Input({"type": "btn-alert-confirm",  "index": dash.ALL}, "n_clicks"),
        Input({"type": "btn-alert-review",   "index": dash.ALL}, "n_clicks"),
        Input({"type": "btn-alert-dismiss",  "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_alert_status_update(confirm_clicks, review_clicks, dismiss_clicks):
        from dash import ctx as _ctx
        if not _ctx.triggered_id:
            raise PreventUpdate
        triggered = _ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        alert_id   = triggered.get("index", "")
        btn_type   = triggered.get("type", "")
        new_status = {"btn-alert-confirm": "CONFIRMED", "btn-alert-review": "REVIEWED", "btn-alert-dismiss": "DISMISSED"}.get(btn_type)
        if not new_status or not alert_id:
            raise PreventUpdate
        try:
            from storage.case_data_service import CaseDataService
            CaseDataService().update_alert_status(alert_id, new_status)
            return {"updated": alert_id, "status": new_status}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Re-render list after status update ───────────────────────────────
    @dash_app.callback(
        Output("alerts-list-container", "children", allow_duplicate=True),
        Input("alerts-status-update-store", "data"),
        State("dossier-active-case-id-store",       "data"),
        State("alert-filter-entity-type",   "value"),
        State("alert-filter-status",        "value"),
        State("alert-filter-severity",      "value"),
        prevent_initial_call=True,
    )
    def rerender_after_status_update(update_data, case_id, entity_types, statuses, severity):
        if not update_data or "error" in update_data or not case_id:
            raise PreventUpdate
        try:
            from storage.case_data_service import CaseDataService
            svc    = CaseDataService()
            alerts = svc.list_alerts_filtered(
                case_id,
                entity_types=entity_types or None,
                statuses=statuses or None,
                severity=severity if severity != "ALL" else None,
            )
            return render_alerts_list(alerts)
        except Exception as exc:
            raise PreventUpdate

