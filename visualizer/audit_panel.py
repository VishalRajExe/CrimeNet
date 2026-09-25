"""
CrimeNet Visible Investigation Audit Trail Panel.

Provides a court-admissible, append-oriented investigation audit history viewer:
- Queries submitted
- Graph searches & N-hop traversals
- Analysis executions (Centrality, Communities, Paths)
- Potential links generated
- Alerts reviewed & triaged
- Human corrections submitted (HITL)
- Investigation actions created (Lookout, Freeze, Review, Escalate)
- Reports generated (PDF briefs)

Stores and displays:
- timestamp
- case
- investigator / user identity
- action
- target
- old value ➔ new value (diff)
- source ref
- result ID
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dash import dcc, html
import dash_bootstrap_components as dbc

from storage.case_data_service import CaseDataService

ACTION_COLORS: Dict[str, str] = {
    "QUERY_SUBMITTED":           "#3182ce",  # Blue
    "SEARCH_EXECUTED":          "#3182ce",
    "GRAPH_SEARCH":             "#2b6cb0",
    "ANALYSIS_EXECUTED":        "#805ad5",  # Purple
    "POTENTIAL_LINK_GENERATED": "#d69e2e",  # Yellow/Gold
    "ALERT_REVIEWED":           "#dd6b20",  # Orange
    "CORRECTION_SUBMITTED":     "#38a169",  # Green (HITL)
    "FEEDBACK_RECORDED":        "#319795",  # Teal
    "ACTION_CREATED":           "#e53e3e",  # Red
    "ACTION_STATUS_UPDATED":    "#c53030",
    "REPORT_GENERATED":         "#00b4d8",  # Cyan
    "EVIDENCE_INGESTED":        "#4a5568",  # Slate
    "CASE_CREATED":             "#2f855a",
}


def _get_action_badge(action: str) -> html.Span:
    col = ACTION_COLORS.get(action.upper(), "#718096")
    return html.Span(
        action.replace("_", " "),
        style={
            "backgroundColor": col,
            "color": "#ffffff",
            "fontSize": "10px",
            "fontWeight": "700",
            "padding": "3px 8px",
            "borderRadius": "4px",
            "display": "inline-block",
            "textTransform": "uppercase",
            "letterSpacing": "0.4px"
        }
    )


def build_audit_panel() -> html.Div:
    """Build the root layout for the visible Investigation Audit Trail."""
    return html.Div(
        id="investigation-audit-container",
        style={
            "backgroundColor": "#0f1117",
            "color": "#f7fafc",
            "padding": "16px 20px",
            "minHeight": "450px"
        },
        children=[
            # Top Header & Filter Controls
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "borderBottom": "1px solid #2d3748",
                    "paddingBottom": "12px",
                    "marginBottom": "14px",
                    "flexWrap": "wrap",
                    "gap": "10px"
                },
                children=[
                    html.Div([
                        html.H5("🛡️ Investigation Audit History", style={"margin": "0", "fontWeight": "800", "color": "#f7fafc", "display": "flex", "alignItems": "center", "gap": "8px"}),
                        html.Span("Append-oriented, court-admissible log of all investigative queries, analyses, actions, and human corrections.", style={"fontSize": "11px", "color": "#a0aec0"})
                    ]),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            dcc.Dropdown(
                                id="audit-filter-action",
                                placeholder="Filter Action...",
                                options=[
                                    {"label": "All Investigative Actions", "value": "ALL"},
                                    {"label": "🔎 Queries Submitted", "value": "QUERY_SUBMITTED"},
                                    {"label": "👥 Analysis Executions", "value": "ANALYSIS_EXECUTED"},
                                    {"label": "⚠️ Alert Reviews", "value": "ALERT_REVIEWED"},
                                    {"label": "✏️ Human Corrections (HITL)", "value": "CORRECTION_SUBMITTED"},
                                    {"label": "⚡ Workflow Actions Created", "value": "ACTION_CREATED"},
                                    {"label": "📋 Reports Generated", "value": "REPORT_GENERATED"},
                                ],
                                value="ALL",
                                clearable=False,
                                style={"width": "220px", "color": "#1a202c", "fontSize": "12px"}
                            ),
                            dbc.Button("🔄 Refresh Audit", id="btn-refresh-audit-logs", size="sm", color="primary", outline=True, style={"fontSize": "11px"}),
                        ]
                    )
                ]
            ),

            # Main Audit Table Display
            html.Div(id="audit-history-table-wrapper", children=[
                html.Div("Loading investigation audit history...", style={"color": "#a0aec0", "padding": "20px", "textAlign": "center"})
            ])
        ]
    )


def render_audit_table(logs: List[Dict[str, Any]]) -> html.Div:
    """Render structured table of audit entries."""
    if not logs:
        return html.Div(
            style={"textAlign": "center", "padding": "40px", "color": "#718096"},
            children=[
                html.Div("📜", style={"fontSize": "36px", "marginBottom": "10px"}),
                html.B("No audit events recorded for this case yet.", style={"fontSize": "13px"}),
                html.P("Investigation activities will automatically generate an immutable append-only record here.", style={"fontSize": "11px"})
            ]
        )

    rows = []
    for l in logs:
        ts = str(l.get("timestamp", ""))[:19]
        act = str(l.get("action", "UNKNOWN"))
        user = str(l.get("username") or l.get("user_id") or "investigator")
        target = str(l.get("target") or l.get("resource_id") or "—")
        old_val = l.get("old_value")
        new_val = l.get("new_value")
        src_ref = l.get("source_ref") or "—"
        details = str(l.get("details") or "")

        # Format diff if old and new values exist
        diff_cell = []
        if old_val or new_val:
            diff_cell = [
                html.Div([
                    html.Span("Old: ", style={"color": "#e53e3e", "fontWeight": "700"}),
                    html.Span(str(old_val)[:40] if old_val else "None", style={"color": "#feb2b2"})
                ]),
                html.Div([
                    html.Span("New: ", style={"color": "#38a169", "fontWeight": "700"}),
                    html.Span(str(new_val)[:40] if new_val else "None", style={"color": "#9ae6b4"})
                ])
            ]
        else:
            diff_cell = [html.Span(details[:60] or "—", style={"color": "#cbd5e0"})]

        rows.append(html.Tr(
            style={"borderBottom": "1px solid #2d3748", "fontSize": "11px"},
            children=[
                html.Td(ts, style={"padding": "8px 10px", "whiteSpace": "nowrap", "color": "#a0aec0", "fontFamily": "monospace"}),
                html.Td(_get_action_badge(act), style={"padding": "8px 10px"}),
                html.Td(user, style={"padding": "8px 10px", "color": "#e2e8f0", "fontWeight": "600"}),
                html.Td(target[:35], style={"padding": "8px 10px", "color": "#63b3ed", "fontWeight": "600"}),
                html.Td(diff_cell, style={"padding": "8px 10px", "maxWidth": "250px"}),
                html.Td(
                    dbc.Badge(src_ref, color="secondary", style={"fontSize": "10px"}) if src_ref != "—" else "—",
                    style={"padding": "8px 10px"}
                ),
            ]
        ))

    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse", "backgroundColor": "#1a202c", "borderRadius": "6px", "overflow": "hidden"},
        children=[
            html.Thead(
                html.Tr(
                    style={"backgroundColor": "#2d3748", "color": "#cbd5e0", "fontSize": "11px", "textAlign": "left"},
                    children=[
                        html.Th("TIMESTAMP", style={"padding": "10px"}),
                        html.Th("ACTION", style={"padding": "10px"}),
                        html.Th("INVESTIGATOR", style={"padding": "10px"}),
                        html.Th("TARGET ENTITY / REF", style={"padding": "10px"}),
                        html.Th("DETAILS / VALUE DIFF", style={"padding": "10px"}),
                        html.Th("SOURCE REF", style={"padding": "10px"}),
                    ]
                )
            ),
            html.Tbody(rows)
        ]
    )


def build_audit_modal() -> html.Div:
    """Build the modal for viewing the visible investigation audit history."""
    return html.Div([
        dbc.Modal(
            id="modal-case-audit",
            is_open=False,
            size="xl",
            scrollable=True,
            children=[
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span("🛡️", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5("Investigation Audit History & Chain of Custody", style={"margin": "0", "fontWeight": "800", "color": "#f7fafc"}),
                                html.Span("Append-oriented, court-admissible log of all investigative queries, analyses, actions, and human corrections.", style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748"}
                ),
                dbc.ModalBody(
                    style={"backgroundColor": "#0f1117", "color": "#cbd5e0", "padding": "16px"},
                    children=[build_audit_panel()]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="btn-close-case-audit", className="ms-auto", color="secondary", style={"fontSize": "11px"}),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


def register_audit_panel_callbacks(dash_app):
    """Register callbacks for the visible audit history panel."""
    from dash import Input, Output, State, ctx, no_update
    from dash.exceptions import PreventUpdate

    # Toggle Audit Modal
    @dash_app.callback(
        Output("modal-case-audit", "is_open"),
        [
            Input("ws-sec-nav-audit", "n_clicks"),
            Input("btn-close-case-audit", "n_clicks"),
        ],
        [State("modal-case-audit", "is_open")],
        prevent_initial_call=True
    )
    def toggle_audit_modal(n_open, n_close, is_open):
        if n_open or n_close:
            return not is_open
        return is_open

    @dash_app.callback(
        Output("audit-history-table-wrapper", "children"),
        [
            Input("dossier-active-case-id-store", "data"),
            Input("audit-filter-action", "value"),
            Input("btn-refresh-audit-logs", "n_clicks"),
        ],
        prevent_initial_call=False
    )
    def update_audit_table(case_id, action_filter, n_refresh):
        if not case_id:
            # Fallback to first available case
            try:
                cases = CaseDataService().list_cases()
                if cases:
                    case_id = cases[0]["id"]
            except Exception:
                pass

        if not case_id:
            return html.Div("Please select or open an investigation case.", style={"color": "#a0aec0", "padding": "20px"})

        service = CaseDataService()
        selected_act = None if action_filter in (None, "ALL") else action_filter
        logs = service.list_audit_logs(case_id=case_id, action=selected_act, limit=100)
        return render_audit_table(logs)

