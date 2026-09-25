"""
CrimeNet Reports Panel & Generator Modal.

Allows generating all 4 court-admissible forensic PDF report formats locally:
- Investigation Brief
- Entity Dossier
- Supervisor Summary
- Interagency Brief

Integrates directly with reports/report_generator.py and CaseDataService.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dash import dcc, html
import dash_bootstrap_components as dbc

from reports.report_generator import InvestigationReportCompiler, ReportFormat
from storage.case_data_service import CaseDataService


def build_reports_modal() -> html.Div:
    """Build the modal for generating and viewing local case PDF reports."""
    return html.Div([
        dbc.Modal(
            id="modal-case-reports",
            is_open=False,
            size="lg",
            scrollable=True,
            children=[
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span("📋", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5("Forensic & Intelligence Report Generator", style={"margin": "0", "fontWeight": "800", "color": "#f7fafc"}),
                                html.Span("Compile strictly grounded, court-admissible PDF reports locally from active case data.", style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748"}
                ),
                dbc.ModalBody(
                    style={"backgroundColor": "#0f1117", "color": "#cbd5e0", "padding": "20px"},
                    children=[
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Report Format *", style={"fontSize": "12px", "fontWeight": "700"}),
                                dcc.Dropdown(
                                    id="report-format-select",
                                    options=[
                                        {"label": "📑 Investigation Operational Brief (Comprehensive)", "value": ReportFormat.INVESTIGATION_BRIEF},
                                        {"label": "👤 Entity Intelligence Dossier (Deep-Dive)", "value": ReportFormat.ENTITY_DOSSIER},
                                        {"label": "🎖️ Command Supervisor Summary (Executive)", "value": ReportFormat.SUPERVISOR_SUMMARY},
                                        {"label": "🏛️ Interagency Evidentiary Brief (ED / FIU / LEA)", "value": ReportFormat.INTERAGENCY_BRIEF},
                                    ],
                                    value=ReportFormat.INVESTIGATION_BRIEF,
                                    clearable=False,
                                    style={"color": "#1a202c", "fontSize": "12px"}
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Target Entity (Required for Entity Dossier)", style={"fontSize": "12px", "fontWeight": "700"}),
                                dcc.Dropdown(
                                    id="report-target-entity-select",
                                    placeholder="Select subject entity...",
                                    options=[],
                                    clearable=True,
                                    style={"color": "#1a202c", "fontSize": "12px"}
                                )
                            ], width=6),
                        ], className="mb-3"),

                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Investigator Name / Badge", style={"fontSize": "12px", "fontWeight": "700"}),
                                dbc.Input(
                                    id="report-investigator-input",
                                    value="Inspector Sandeep Verma",
                                    style={"backgroundColor": "#1a202c", "color": "#f7fafc", "borderColor": "#2d3748", "fontSize": "12px"}
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Investigator Observations & Field Notes", style={"fontSize": "12px", "fontWeight": "700"}),
                                dbc.Textarea(
                                    id="report-notes-input",
                                    placeholder="Optional notes or operational guidance to include in Section 8 of the generated report.",
                                    rows=2,
                                    style={"backgroundColor": "#1a202c", "color": "#f7fafc", "borderColor": "#2d3748", "fontSize": "12px"}
                                )
                            ], width=6),
                        ], className="mb-3"),

                        dbc.Button("📄 Generate Local PDF Report", id="btn-generate-report", color="primary", style={"fontSize": "12px", "fontWeight": "700"}),
                        html.Div(id="report-generation-feedback", style={"marginTop": "14px"}),

                        html.Hr(style={"borderColor": "#2d3748", "margin": "20px 0"}),

                        html.H6("📂 Historical Case Reports", style={"fontWeight": "700", "color": "#f7fafc"}),
                        html.Div(id="case-reports-history-list", style={"marginTop": "10px"})
                    ]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="btn-close-case-reports", color="secondary", size="sm"),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


def render_reports_history(reports: List[Dict[str, Any]]) -> html.Div:
    """Render list of generated reports for the case."""
    if not reports:
        return html.Div("No reports generated for this case yet.", style={"color": "#a0aec0", "fontSize": "12px"})

    items = []
    for r in reports:
        meta = {}
        if r.get("metadata"):
            try:
                meta = json.loads(r["metadata"]) if isinstance(r["metadata"], str) else r["metadata"]
            except Exception:
                pass

        fp = r.get("file_path") or ""
        fn = meta.get("filename") or os.path.basename(fp) or "report.pdf"
        exists = os.path.exists(fp) if fp else False

        items.append(html.Div(
            style={
                "backgroundColor": "#1a202c",
                "border": "1px solid #2d3748",
                "borderRadius": "6px",
                "padding": "10px 14px",
                "marginBottom": "8px",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center"
            },
            children=[
                html.Div([
                    html.B(r.get("title", "Investigation Report"), style={"color": "#f7fafc", "fontSize": "12px"}),
                    html.Div([
                        html.Span(f"Format: {r.get('report_type')} | ", style={"color": "#a0aec0", "fontSize": "11px"}),
                        html.Span(f"Generated at: {str(r.get('created_at', ''))[:16]}", style={"color": "#718096", "fontSize": "11px"}),
                    ]),
                    html.Div(f"📁 Local File: {fp}", style={"color": "#63b3ed", "fontSize": "10px", "fontFamily": "monospace"}) if fp else None
                ]),
                dbc.Badge("PDF Ready", color="success" if exists else "secondary", style={"fontSize": "11px"})
            ]
        ))

    return html.Div(items)


def register_reports_callbacks(dash_app):
    """Register callbacks for generating reports."""
    from dash import Input, Output, State, ctx, no_update
    from dash.exceptions import PreventUpdate

    # Toggle Reports Modal
    @dash_app.callback(
        Output("modal-case-reports", "is_open"),
        [
            Input("ws-sec-nav-reports", "n_clicks"),
            Input("btn-close-case-reports", "n_clicks"),
        ],
        [State("modal-case-reports", "is_open")],
        prevent_initial_call=True
    )
    def toggle_reports_modal(n_open, n_close, is_open):
        if n_open or n_close:
            return not is_open
        return is_open

    # Populate entity dropdown
    @dash_app.callback(
        Output("report-target-entity-select", "options"),
        Input("dossier-active-case-id-store", "data"),
        prevent_initial_call=False
    )
    def populate_report_entities(case_id):
        if not case_id:
            return []
        try:
            service = CaseDataService()
            graph = service.get_case_graph(case_id)
            nodes = graph.get("nodes", [])
            return [{"label": f"{n.get('name') or n.get('id')} ({n.get('type')})", "value": n.get("id")} for n in nodes]
        except Exception:
            return []

    # Generate Report
    @dash_app.callback(
        [
            Output("report-generation-feedback", "children"),
            Output("case-reports-history-list", "children"),
        ],
        Input("btn-generate-report", "n_clicks"),
        [
            State("report-format-select", "value"),
            State("report-target-entity-select", "value"),
            State("report-investigator-input", "value"),
            State("report-notes-input", "value"),
            State("dossier-active-case-id-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_report_generation(n_clicks, fmt, target_ent, investigator, notes, case_id):
        if not n_clicks:
            raise PreventUpdate

        service = CaseDataService()
        if not case_id:
            cases = service.list_cases()
            case_id = cases[0]["id"] if cases else "case-synthetic-black-falcon-001"

        try:
            compiler = InvestigationReportCompiler(service=service)
            res = compiler.generate_pdf_report(
                case_id=case_id,
                report_format=fmt or ReportFormat.INVESTIGATION_BRIEF,
                target_entity_id=target_ent,
                investigator=investigator or "Inspector Sandeep Verma",
                notes=notes or ""
            )

            feedback = dbc.Alert([
                html.B(f"✅ Generated {res['title']} successfully!"),
                html.Div(f"Saved locally to: {res['file_path']}", style={"fontSize": "11px", "fontFamily": "monospace", "marginTop": "4px"}),
                html.Small("Court-admissible PDF generated with complete evidentiary citations and audit log entry.", style={"display": "block", "marginTop": "4px"})
            ], color="success", style={"fontSize": "12px"})

            reports = service.list_reports(case_id)
            return feedback, render_reports_history(reports)
        except Exception as exc:
            return dbc.Alert(f"Error generating PDF report: {exc}", color="danger", style={"fontSize": "12px"}), no_update
