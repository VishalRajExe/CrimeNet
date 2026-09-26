"""CrimeNet Case Dashboard Module.

Implements the case-oriented investigation management portal:
- View all active/closed cases from MySQL
- Search and multi-criteria filtering (priority, status, jurisdiction)
- Quick KPI metrics (Critical alerts, entity volume, active syndicates)
- Case Dossier drawer covering the 10 domain models (Evidence, Entities, Relations, Alerts, Timeline, etc.)
- Create Case modal
- One-click launch into the isolated Investigation Workspace for that specific case
"""

from __future__ import annotations

import os
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
from storage.case_data_service import CaseDataService
from storage.evidence_processor import EvidenceProcessor
from visualizer.case_timeline_panel import build_case_timeline, register_timeline_callbacks
from visualizer.actions_workflow_modal import build_actions_workflow_panel


def get_priority_badge(priority: str) -> html.Span:
    p = (priority or "MEDIUM").upper()
    colors = {
        "CRITICAL": {"bg": "rgba(229, 62, 62, 0.15)", "text": "#fc8181", "border": "#e53e3e"},
        "HIGH": {"bg": "rgba(221, 107, 32, 0.15)", "text": "#fbd38d", "border": "#dd6b20"},
        "MEDIUM": {"bg": "rgba(49, 130, 206, 0.15)", "text": "#90cdf4", "border": "#3182ce"},
        "LOW": {"bg": "rgba(113, 128, 150, 0.15)", "text": "#cbd5e0", "border": "#718096"},
    }
    cfg = colors.get(p, colors["MEDIUM"])
    return html.Span(
        p,
        className="case-badge case-badge-priority",
        style={
            "backgroundColor": cfg["bg"],
            "color": cfg["text"],
            "border": f"1px solid {cfg['border']}",
            "padding": "2px 8px",
            "borderRadius": "4px",
            "fontSize": "10px",
            "fontWeight": "700",
            "letterSpacing": "0.5px"
        }
    )


def get_status_badge(status: str) -> html.Span:
    s = (status or "OPEN").upper()
    colors = {
        "ACTIVE": {"bg": "rgba(56, 161, 105, 0.15)", "text": "#9ae6b4", "border": "#38a169"},
        "UNDER_REVIEW": {"bg": "rgba(128, 90, 213, 0.15)", "text": "#d6bcfa", "border": "#805ad5"},
        "OPEN": {"bg": "rgba(49, 151, 149, 0.15)", "text": "#81e6d9", "border": "#319795"},
        "CLOSED": {"bg": "rgba(74, 85, 104, 0.15)", "text": "#a0aec0", "border": "#4a5568"},
        "ARCHIVED": {"bg": "rgba(45, 55, 72, 0.2)", "text": "#718096", "border": "#2d3748"},
    }
    cfg = colors.get(s, colors["OPEN"])
    return html.Span(
        s.replace("_", " "),
        className="case-badge case-badge-status",
        style={
            "backgroundColor": cfg["bg"],
            "color": cfg["text"],
            "border": f"1px solid {cfg['border']}",
            "padding": "2px 8px",
            "borderRadius": "4px",
            "fontSize": "10px",
            "fontWeight": "600"
        }
    )


def build_kpi_card(title: str, value: str | int, subtitle: str, color_hex: str = "#3182ce") -> html.Div:
    return html.Div(
        className="dashboard-kpi-card",
        style={
            "backgroundColor": "#1a202c",
            "border": "1px solid #2d3748",
            "borderRadius": "8px",
            "padding": "16px 20px",
            "flex": "1",
            "minWidth": "160px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.2)"
        },
        children=[
            html.Div(title, style={"fontSize": "11px", "color": "#a0aec0", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
            html.Div(str(value), style={"fontSize": "26px", "fontWeight": "800", "color": color_hex, "margin": "4px 0"}),
            html.Div(subtitle, style={"fontSize": "11px", "color": "#718096"})
        ]
    )


def build_case_card(c: Dict[str, Any]) -> html.Div:
    case_id = c["id"]
    c_num = c.get("case_number") or case_id[:12]
    title = c.get("title") or "Untitled Investigation"
    desc = c.get("description") or "No case narrative entered."
    if len(desc) > 140:
        desc = desc[:137] + "..."

    ent_count = c.get("entity_count", 0)
    rel_count = c.get("relationship_count", 0)
    alert_count = c.get("alert_count", 0)
    crime_type = (c.get("crime_type") or "ORGANIZED CRIME").replace("_", " ")
    location = c.get("location") or "Multi-Jurisdiction"
    updated_date = str(c.get("updated_at") or "")[:10]

    return html.Div(
        className="case-card",
        id=f"case-card-container-{case_id}",
        style={
            "backgroundColor": "#1a202c",
            "border": "1px solid #2d3748",
            "borderRadius": "8px",
            "padding": "18px 20px",
            "marginBottom": "16px",
            "transition": "all 0.2s ease-in-out",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)"
        },
        children=[
            # Top header line: Case Number, Priority, Status
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "10px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span(c_num, style={"color": "#63b3ed", "fontWeight": "700", "fontSize": "13px", "fontFamily": "monospace"}),
                            get_priority_badge(c.get("priority", "MEDIUM")),
                            get_status_badge(c.get("status", "OPEN")),
                        ]
                    ),
                    html.Span(f"Updated: {updated_date}", style={"color": "#718096", "fontSize": "11px"})
                ]
            ),
            # Title
            html.H4(
                title,
                style={"color": "#f7fafc", "fontSize": "16px", "fontWeight": "700", "margin": "0 0 8px 0"}
            ),
            # Narrative Description
            html.P(
                desc,
                style={"color": "#a0aec0", "fontSize": "12px", "lineHeight": "1.5", "margin": "0 0 14px 0"}
            ),
            # Metadata Tags
            html.Div(
                style={"display": "flex", "gap": "12px", "fontSize": "11px", "color": "#718096", "marginBottom": "14px"},
                children=[
                    html.Span(f"📁 {crime_type}", style={"backgroundColor": "#2d3748", "padding": "2px 8px", "borderRadius": "4px"}),
                    html.Span(f"📍 {location}", style={"backgroundColor": "#2d3748", "padding": "2px 8px", "borderRadius": "4px"}),
                ]
            ),
            # Bottom row: Metrics & Actions
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "borderTop": "1px solid #2d3748", "paddingTop": "12px"},
                children=[
                    # Metrics
                    html.Div(
                        style={"display": "flex", "gap": "16px", "fontSize": "12px"},
                        children=[
                            html.Span([html.B(str(ent_count), style={"color": "#e2e8f0"}), " Entities"], style={"color": "#a0aec0"}),
                            html.Span([html.B(str(rel_count), style={"color": "#e2e8f0"}), " Connections"], style={"color": "#a0aec0"}),
                            html.Span([html.B(str(alert_count), style={"color": "#fc8181" if alert_count > 0 else "#a0aec0"}), " Alerts"], style={"color": "#a0aec0"}),
                        ]
                    ),
                    # Action buttons
                    html.Div(
                        style={"display": "flex", "gap": "8px"},
                        children=[
                            dbc.Button(
                                "Dossier",
                                id={"type": "btn-dossier-case", "index": case_id},
                                size="sm",
                                color="secondary",
                                outline=True,
                                style={"fontSize": "11px", "padding": "4px 10px"}
                            ),
                            dbc.Button(
                                "Open Workspace →",
                                id={"type": "btn-open-case", "index": case_id},
                                size="sm",
                                color="primary",
                                style={"fontSize": "11px", "padding": "4px 12px", "fontWeight": "600"}
                            ),
                        ]
                    )
                ]
            )
        ]
    )


def build_dashboard_view() -> html.Div:
    """Build the complete Case Management Dashboard view."""
    svc = CaseDataService()
    cases = svc.list_cases()

    # Aggregate stats
    total_cases = len(cases)
    critical_cases = sum(1 for c in cases if (c.get("priority") or "").upper() == "CRITICAL")
    total_entities = sum(c.get("entity_count", 0) for c in cases)
    total_relations = sum(c.get("relationship_count", 0) for c in cases)
    total_alerts = sum(c.get("alert_count", 0) for c in cases)

    case_cards = [build_case_card(c) for c in cases]

    return html.Div(
        id="case-dashboard-container",
        style={"padding": "24px 32px", "maxWidth": "1400px", "margin": "0 auto", "color": "#f7fafc"},
        children=[
            # Top Banner & Actions
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start", "marginBottom": "24px"},
                children=[
                    html.Div([
                        html.H2("CrimeNet Case Intelligence Platform", style={"fontWeight": "800", "fontSize": "22px", "color": "#f7fafc", "margin": "0 0 4px 0"}),
                        html.P("Active Operational Cases, Syndicate Networks & Forensic Dossiers", style={"color": "#a0aec0", "fontSize": "13px", "margin": 0})
                    ]),
                    html.Div(
                        style={"display": "flex", "gap": "10px"},
                        children=[
                            dbc.Button(
                                "+ New Investigation Case",
                                id="btn-open-create-case-modal",
                                color="success",
                                size="sm",
                                style={"fontWeight": "600", "padding": "6px 14px", "fontSize": "12px"}
                            ),
                            dbc.Button(
                                "Switch to Cytoscape Workspace",
                                id="btn-switch-to-workspace-direct",
                                color="primary",
                                outline=True,
                                size="sm",
                                style={"fontWeight": "600", "padding": "6px 14px", "fontSize": "12px"}
                            )
                        ]
                    )
                ]
            ),

            # KPI Summary Statistics Cards
            html.Div(
                style={"display": "flex", "gap": "16px", "marginBottom": "24px", "flexWrap": "wrap"},
                children=[
                    build_kpi_card("Total Active Cases", total_cases, "Tracked investigations", "#63b3ed"),
                    build_kpi_card("Critical Priority", critical_cases, "Urgent syndicates", "#fc8181"),
                    build_kpi_card("Identified Entities", total_entities, "Suspects, phones, vehicles", "#9ae6b4"),
                    build_kpi_card("Investigated Links", total_relations, "Calls, hawala, sightings", "#fbd38d"),
                    build_kpi_card("Forensic Anomalies", total_alerts, "Smurfing, odd-hour, cross-case", "#d6bcfa"),
                ]
            ),

            # Filter & Search Toolbar
            html.Div(
                style={
                    "backgroundColor": "#1a202c",
                    "border": "1px solid #2d3748",
                    "borderRadius": "8px",
                    "padding": "14px 18px",
                    "marginBottom": "20px",
                    "display": "flex",
                    "gap": "14px",
                    "alignItems": "center",
                    "flexWrap": "wrap"
                },
                children=[
                    # Search Input
                    html.Div(
                        style={"flex": "2", "minWidth": "250px"},
                        children=[
                            dbc.Input(
                                id="dashboard-search-input",
                                placeholder="Search by case number, title, crime type, or jurisdiction...",
                                type="text",
                                style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}
                            )
                        ]
                    ),
                    # Priority Filter
                    html.Div(
                        style={"flex": "1", "minWidth": "140px"},
                        children=[
                            dcc.Dropdown(
                                id="dashboard-priority-filter",
                                options=[
                                    {"label": "Priority: All", "value": "ALL"},
                                    {"label": "Critical", "value": "CRITICAL"},
                                    {"label": "High", "value": "HIGH"},
                                    {"label": "Medium", "value": "MEDIUM"},
                                    {"label": "Low", "value": "LOW"},
                                ],
                                value="ALL",
                                clearable=False,
                                className="dashboard-dropdown",
                                style={"fontSize": "12px"}
                            )
                        ]
                    ),
                    # Status Filter
                    html.Div(
                        style={"flex": "1", "minWidth": "140px"},
                        children=[
                            dcc.Dropdown(
                                id="dashboard-status-filter",
                                options=[
                                    {"label": "Status: All", "value": "ALL"},
                                    {"label": "Active", "value": "ACTIVE"},
                                    {"label": "Under Review", "value": "UNDER_REVIEW"},
                                    {"label": "Open", "value": "OPEN"},
                                    {"label": "Closed", "value": "CLOSED"},
                                ],
                                value="ALL",
                                clearable=False,
                                className="dashboard-dropdown",
                                style={"fontSize": "12px"}
                            )
                        ]
                    ),
                    # Refresh Button
                    dbc.Button(
                        "↻ Refresh",
                        id="btn-refresh-dashboard",
                        color="secondary",
                        outline=True,
                        size="sm",
                        style={"fontSize": "12px", "padding": "6px 12px"}
                    )
                ]
            ),

            # Case Cards Grid
            html.Div(
                id="dashboard-cases-grid",
                children=case_cards if case_cards else [
                    html.Div(
                        "No matching investigation cases found.",
                        style={"textAlign": "center", "padding": "40px", "color": "#718096", "fontSize": "14px"}
                    )
                ]
            ),

            # Create Case Modal
            build_create_case_modal(),

            # Case Dossier Modal (10-Domain Breakdown)
            build_case_dossier_modal(),

            # Internal refresh trigger store
            dcc.Store(id="case-refresh-trigger", storage_type="memory", data=0),
        ]
    )


def build_create_case_modal() -> dbc.Modal:
    """Modal dialog for creating a new investigation case in MySQL."""
    return dbc.Modal(
        id="modal-create-case",
        is_open=False,
        centered=True,
        size="lg",
        children=[
            dbc.ModalHeader(
                dbc.ModalTitle("Create New Investigation Case", style={"color": "#f7fafc", "fontWeight": "700"}),
                close_button=True,
                style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748"}
            ),
            dbc.ModalBody(
                style={"backgroundColor": "#171923", "color": "#e2e8f0", "padding": "20px"},
                children=[
                    html.Div(id="create-case-alert-div"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Case Title *", style={"fontSize": "12px", "fontWeight": "600"}),
                            dbc.Input(id="new-case-title", placeholder="e.g. Operation Hawk: Cross-Border Syndicate", style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}),
                        ], width=8),
                        dbc.Col([
                            dbc.Label("Case Number (FIR)", style={"fontSize": "12px", "fontWeight": "600"}),
                            dbc.Input(id="new-case-number", placeholder="Auto-generated if empty", style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}),
                        ], width=4),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Crime Type", style={"fontSize": "12px", "fontWeight": "600"}),
                            dcc.Dropdown(
                                id="new-case-crime-type",
                                options=[
                                    {"label": "Narcotics Transit & Distribution", "value": "NARCOTICS"},
                                    {"label": "Hawala & Money Laundering", "value": "HAWALA"},
                                    {"label": "Cyber Extortion & Loan Fraud", "value": "CYBER_EXTORTION"},
                                    {"label": "Organized Contraband & Arms", "value": "ORGANIZED_CRIME"},
                                    {"label": "Terror Finance & Recruitment", "value": "TERROR_FINANCE"},
                                    {"label": "Financial Fraud & Ponzi", "value": "FINANCIAL_FRAUD"},
                                ],
                                value="ORGANIZED_CRIME",
                                clearable=False,
                                className="dashboard-dropdown",
                                style={"fontSize": "12px"}
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Priority", style={"fontSize": "12px", "fontWeight": "600"}),
                            dcc.Dropdown(
                                id="new-case-priority",
                                options=[
                                    {"label": "Critical", "value": "CRITICAL"},
                                    {"label": "High", "value": "HIGH"},
                                    {"label": "Medium", "value": "MEDIUM"},
                                    {"label": "Low", "value": "LOW"},
                                ],
                                value="HIGH",
                                clearable=False,
                                className="dashboard-dropdown",
                                style={"fontSize": "12px"}
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Initial Status", style={"fontSize": "12px", "fontWeight": "600"}),
                            dcc.Dropdown(
                                id="new-case-status",
                                options=[
                                    {"label": "Open", "value": "OPEN"},
                                    {"label": "Active", "value": "ACTIVE"},
                                    {"label": "Under Review", "value": "UNDER_REVIEW"},
                                ],
                                value="ACTIVE",
                                clearable=False,
                                className="dashboard-dropdown",
                                style={"fontSize": "12px"}
                            )
                        ], width=4),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Jurisdiction / Location", style={"fontSize": "12px", "fontWeight": "600"}),
                            dbc.Input(id="new-case-location", placeholder="e.g. Mumbai Coastal Zone, Delhi NCR", style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Lead Investigating Officer (IO)", style={"fontSize": "12px", "fontWeight": "600"}),
                            dbc.Input(id="new-case-officer", placeholder="e.g. Inspector R. Sharma (Badge #4892)", style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}),
                        ], width=6),
                    ], className="mb-3"),

                    html.Div([
                        dbc.Label("Case Narrative & Initial FIR Statement", style={"fontSize": "12px", "fontWeight": "600"}),
                        dbc.Textarea(
                            id="new-case-description",
                            placeholder="Enter the initial report text, informant tips, or seized device details...",
                            rows=4,
                            style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}
                        )
                    ], className="mb-2")
                ]
            ),
            dbc.ModalFooter(
                style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"},
                children=[
                    dbc.Button("Cancel", id="btn-cancel-create-case", color="secondary", outline=True, size="sm"),
                    dbc.Button("Create Case", id="btn-submit-create-case", color="success", size="sm", style={"fontWeight": "600"}),
                ]
            )
        ]
    )


def get_evidence_processing_badge(status: str) -> html.Span:
    status_upper = (status or "UPLOADED").upper()
    color_map = {
        "UPLOADED": {"bg": "#2b6cb0", "border": "#3182ce", "text": "#ebf8ff", "icon": "📤"},
        "PROCESSING": {"bg": "#744210", "border": "#d69e2e", "text": "#fefcbf", "icon": "⏳"},
        "PROCESSED": {"bg": "#22543d", "border": "#38a169", "text": "#c6f6d5", "icon": "✅"},
        "FAILED": {"bg": "#742a2a", "border": "#e53e3e", "text": "#fed7d7", "icon": "❌"},
    }
    c = color_map.get(status_upper, color_map["UPLOADED"])
    return html.Span(
        f"{c['icon']} {status_upper}",
        style={
            "backgroundColor": c["bg"],
            "borderColor": c["border"],
            "color": c["text"],
            "fontSize": "10px",
            "fontWeight": "700",
            "padding": "2px 7px",
            "borderRadius": "4px",
            "border": f"1px solid {c['border']}",
            "letterSpacing": "0.3px",
            "display": "inline-flex",
            "alignItems": "center",
            "gap": "4px"
        }
    )


def get_evidence_extraction_badge(status: str) -> html.Span:
    status_upper = (status or "PENDING").upper()
    color_map = {
        "EXTRACTED": {"bg": "#234e52", "border": "#319795", "text": "#b2f5ea", "icon": "🧠"},
        "PENDING": {"bg": "#2d3748", "border": "#4a5568", "text": "#cbd5e0", "icon": "🕒"},
        "NO ENTITIES FOUND": {"bg": "#1a202c", "border": "#4a5568", "text": "#a0aec0", "icon": "🔍"},
        "FAILED": {"bg": "#742a2a", "border": "#e53e3e", "text": "#fed7d7", "icon": "⚠️"},
    }
    c = color_map.get(status_upper, color_map["PENDING"])
    return html.Span(
        f"{c['icon']} {status_upper}",
        style={
            "backgroundColor": c["bg"],
            "borderColor": c["border"],
            "color": c["text"],
            "fontSize": "10px",
            "fontWeight": "600",
            "padding": "2px 7px",
            "borderRadius": "4px",
            "border": f"1px solid {c['border']}",
            "display": "inline-flex",
            "alignItems": "center",
            "gap": "4px"
        }
    )


def get_evidence_type_badge(etype: str) -> html.Span:
    etype_upper = (etype or "UNKNOWN").upper()
    color_map = {
        "PDF": {"bg": "#742a2a", "border": "#e53e3e", "color": "#fed7d7", "icon": "📄"},
        "TXT": {"bg": "#2a4365", "border": "#3182ce", "color": "#bee3f8", "icon": "📝"},
        "CSV": {"bg": "#1c4532", "border": "#38a169", "color": "#c6f6d5", "icon": "📊"},
        "JSON": {"bg": "#744210", "border": "#d69e2e", "color": "#fefcbf", "icon": "🕸️"},
    }
    c = color_map.get(etype_upper, {"bg": "#2d3748", "border": "#4a5568", "color": "#e2e8f0", "icon": "📁"})
    return html.Span(
        f"{c['icon']} {etype_upper}",
        style={
            "backgroundColor": c["bg"],
            "borderColor": c["border"],
            "color": c["color"],
            "fontSize": "10px",
            "fontWeight": "700",
            "padding": "2px 8px",
            "borderRadius": "4px",
            "border": f"1px solid {c['border']}",
            "fontFamily": "monospace"
        }
    )


def build_evidence_card(ev: Dict[str, Any]) -> html.Div:
    """Build a comprehensive, forensic-grade card for an evidence exhibit."""
    ev_id = ev.get("id", "")
    title = ev.get("title") or ev.get("filename") or f"Exhibit #{ev_id[:8]}"
    filename = ev.get("filename") or "unnamed_exhibit"
    etype = ev.get("evidence_type") or "UNKNOWN"
    proc_status = ev.get("processing_status") or "Uploaded"
    ext_status = ev.get("extraction_status") or "Pending"
    source = ev.get("source_ref") or "N/A"
    created = str(ev.get("created_at") or ev.get("collected_at") or "")
    sha256 = ev.get("sha256_hash") or "N/A"
    desc = ev.get("description") or ""
    err_msg = ev.get("error_message") or ""
    ent_cnt = ev.get("entity_count", 0)
    rel_cnt = ev.get("relation_count", 0)

    border_accent = "#38a169" if proc_status == "Processed" else ("#e53e3e" if proc_status == "Failed" else "#3182ce")

    return html.Div(
        style={
            "backgroundColor": "#1e2433",
            "border": "1px solid #2d3748",
            "borderLeft": f"4px solid {border_accent}",
            "borderRadius": "6px",
            "padding": "12px 16px",
            "marginBottom": "10px"
        },
        children=[
            # Header row: Title + Type badge + Status badges
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start", "marginBottom": "6px", "gap": "10px"},
                children=[
                    html.Div(
                        children=[
                            html.Div(
                                style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "2px", "flexWrap": "wrap"},
                                children=[
                                    get_evidence_type_badge(etype),
                                    html.B(title, style={"color": "#f7fafc", "fontSize": "13px"}),
                                    html.Span(f"({filename})", style={"color": "#a0aec0", "fontSize": "11px", "fontFamily": "monospace"}),
                                ]
                            ),
                            html.Div(
                                style={"fontSize": "11px", "color": "#718096"},
                                children=f"Exhibit ID: {ev_id} | Uploaded: {created[:19]} | Source: {source}"
                            )
                        ]
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "6px", "flexShrink": 0},
                        children=[
                            get_evidence_processing_badge(proc_status),
                            get_evidence_extraction_badge(ext_status)
                        ]
                    )
                ]
            ),

            # Description if present
            html.P(desc, style={"color": "#cbd5e0", "fontSize": "12px", "margin": "4px 0", "lineHeight": "1.4"}) if desc else None,

            # Real error alert box if failed
            html.Div(
                style={
                    "backgroundColor": "#2d1515",
                    "border": "1px solid #742a2a",
                    "borderRadius": "4px",
                    "padding": "8px 12px",
                    "margin": "8px 0",
                    "color": "#feb2b2",
                    "fontSize": "11px",
                    "fontFamily": "monospace",
                    "wordBreak": "break-all"
                },
                children=[
                    html.B("⚠️ Extraction / Ingestion Error: "),
                    html.Span(err_msg)
                ]
            ) if (proc_status == "Failed" or err_msg) else None,

            # Footer row: Counts and SHA-256
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginTop": "8px", "borderTop": "1px solid #2d3748", "paddingTop": "6px", "flexWrap": "wrap", "gap": "8px"},
                children=[
                    html.Div(
                        style={"display": "flex", "gap": "10px", "alignItems": "center"},
                        children=[
                            html.Span(f"👥 {ent_cnt} Entities Linked", style={"color": "#9ae6b4" if ent_cnt > 0 else "#a0aec0", "fontSize": "11px", "fontWeight": "600"}),
                            html.Span(f"🔗 {rel_cnt} Relationships Formed", style={"color": "#63b3ed" if rel_cnt > 0 else "#a0aec0", "fontSize": "11px", "fontWeight": "600"}),
                        ]
                    ),
                    html.Div(
                        style={"fontSize": "10px", "fontFamily": "monospace", "color": "#68d391"},
                        children=f"SHA-256: {sha256[:16]}...{sha256[-8:]}" if len(sha256) > 24 else f"SHA-256: {sha256}"
                    )
                ]
            )
        ]
    )


def build_evidence_registry_view(evidence_list: List[Dict[str, Any]]) -> html.Div:
    """Render the list of evidence exhibits or the Empty State card."""
    if not evidence_list:
        # Empty State
        return html.Div(
            style={
                "textAlign": "center",
                "padding": "36px 20px",
                "backgroundColor": "#1a202c",
                "borderRadius": "8px",
                "border": "1px dashed #4a5568",
                "marginTop": "12px"
            },
            children=[
                html.Div("📂", style={"fontSize": "42px", "marginBottom": "10px"}),
                html.H5("No Evidence Exhibits Registered Yet", style={"color": "#f7fafc", "fontWeight": "700", "fontSize": "14px"}),
                html.P(
                    "Upload and ingest case exhibits (PDF reports, witness TXT statements, CDR CSVs, or JSON intelligence) above to automatically populate this case's graph.",
                    style={"color": "#a0aec0", "fontSize": "12px", "maxWidth": "500px", "margin": "0 auto"}
                )
            ]
        )

    return html.Div(
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "10px"},
                children=[
                    html.H5(f"Registered Forensic Exhibits ({len(evidence_list)})", style={"fontSize": "13px", "fontWeight": "700", "color": "#e2e8f0", "margin": 0}),
                    html.Span("Chain of Custody & Audit Verified", style={"fontSize": "10px", "color": "#68d391", "fontWeight": "600"})
                ]
            ),
            html.Div(
                style={"maxHeight": "360px", "overflowY": "auto", "paddingRight": "4px"},
                children=[build_evidence_card(ev) for ev in evidence_list]
            )
        ]
    )


def build_dedicated_evidence_section(case_id: str, evidence_list: List[Dict[str, Any]]) -> html.Div:
    """Build the complete, dedicated Evidence Section with Upload, Processing, Success, Error, and Empty states."""
    return html.Div(
        children=[
            # Top Explanatory Header
            html.Div(
                style={"backgroundColor": "#1a202c", "border": "1px solid #2d3748", "borderRadius": "8px", "padding": "14px 18px", "marginBottom": "14px"},
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "4px"},
                        children=[
                            html.H4("📁 Case Evidence Ingestion & NLP Intelligence Pipeline", style={"fontSize": "14px", "fontWeight": "700", "color": "#f7fafc", "margin": 0}),
                            html.Span("Multi-Source Pipeline: PDF • TXT • CSV • JSON", style={"fontSize": "11px", "color": "#63b3ed", "fontWeight": "600"})
                        ]
                    ),
                    html.P(
                        "Upload and validate evidentiary files. The forensic pipeline computes cryptographic SHA-256 hashes, extracts entities (persons, phones, accounts, vehicles, locations, organizations) and operational links, and binds them directly into the case investigation graph.",
                        style={"fontSize": "11px", "color": "#a0aec0", "margin": 0, "lineHeight": "1.4"}
                    )
                ]
            ),

            # Upload & Metadata Form Card
            html.Div(
                id="card-evidence-upload",
                style={"backgroundColor": "#1e2433", "border": "1px solid #2d3748", "borderRadius": "8px", "padding": "16px", "marginBottom": "16px"},
                children=[
                    # Drag-and-drop zone
                    dcc.Upload(
                        id="evidence-file-upload",
                        multiple=False,
                        style={
                            "border": "2px dashed #4299e1",
                            "borderRadius": "8px",
                            "backgroundColor": "#171923",
                            "padding": "20px 14px",
                            "textAlign": "center",
                            "cursor": "pointer",
                            "marginBottom": "12px",
                            "transition": "all 0.2s ease"
                        },
                        children=html.Div([
                            html.Div("📄 📝 📊 🕸️", style={"fontSize": "26px", "marginBottom": "6px"}),
                            html.B("Click to Browse or Drag & Drop Forensic File Here", style={"color": "#63b3ed", "fontSize": "13px"}),
                            html.Div("Supported: PDF (Reports/Panchnama) • TXT (Statements) • CSV (CDR/Banking) • JSON (Intel)", style={"color": "#a0aec0", "fontSize": "11px", "marginTop": "4px"}),
                        ])
                    ),

                    # Dynamic banner showing chosen filename
                    html.Div(id="evidence-selected-file-banner", style={"marginBottom": "12px"}),

                    # Metadata inputs row
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Exhibit Title / Name", style={"fontSize": "11px", "fontWeight": "600", "color": "#cbd5e0"}),
                            dbc.Input(
                                id="evidence-title-input",
                                placeholder="e.g. Seized Mobile CDR or Interrogation Statement",
                                style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Format Type", style={"fontSize": "11px", "fontWeight": "600", "color": "#cbd5e0"}),
                            dcc.Dropdown(
                                id="evidence-type-select",
                                options=[
                                    {"label": "🔍 Auto-Detect Format", "value": "AUTO"},
                                    {"label": "📄 PDF Document (pypdf text stream)", "value": "PDF"},
                                    {"label": "📝 TXT Text (Statement / Transcript)", "value": "TXT"},
                                    {"label": "📊 CSV Dataset (CDR / Hawala / Tower)", "value": "CSV"},
                                    {"label": "🕸️ JSON Feed (Graph / Cyber Intelligence)", "value": "JSON"},
                                ],
                                value="AUTO",
                                clearable=False,
                                className="dash-dropdown-dark",
                                style={"fontSize": "12px"}
                            )
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Source Reference", style={"fontSize": "11px", "fontWeight": "600", "color": "#cbd5e0"}),
                            dbc.Input(
                                id="evidence-source-input",
                                placeholder="e.g. Panchnama Memo #4 / Cyber Cell",
                                style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px"}
                            )
                        ], width=3),
                    ], className="mb-2"),

                    # Description / Custody notes
                    html.Div([
                        dbc.Label("Description & Chain of Custody Notes", style={"fontSize": "11px", "fontWeight": "600", "color": "#cbd5e0"}),
                        dbc.Textarea(
                            id="evidence-desc-input",
                            placeholder="Enter notes on evidence seizure, handling officer, device IMEI, or statement context...",
                            rows=2,
                            style={"backgroundColor": "#2d3748", "color": "#f7fafc", "border": "1px solid #4a5568", "fontSize": "12px", "marginBottom": "10px"}
                        )
                    ]),

                    # Action buttons
                    html.Div(
                        style={"display": "flex", "justifyContent": "flex-end", "gap": "10px"},
                        children=[
                            dbc.Button(
                                "⚡ Ingest, Extract & Link to Graph",
                                id="btn-process-evidence",
                                color="success",
                                size="sm",
                                style={"fontWeight": "700", "padding": "6px 16px", "backgroundColor": "#38a169", "borderColor": "#38a169"}
                            )
                        ]
                    )
                ]
            ),

            # Dynamic Pipeline Status Container (Loading, Success, or Error states)
            dcc.Loading(
                id="loading-evidence-process",
                type="circle",
                color="#3182ce",
                children=html.Div(id="evidence-pipeline-status-div", style={"marginBottom": "14px"})
            ),

            # Forensic Registry Container (displays empty state or exhibit cards)
            html.Div(
                id="dossier-evidence-registry-container",
                children=build_evidence_registry_view(evidence_list)
            )
        ]
    )


def build_case_dossier_modal() -> dbc.Modal:
    """Modal displaying the 10-layer Case Dossier breakdown for an opened case."""
    return dbc.Modal(
        id="modal-case-dossier",
        is_open=False,
        centered=True,
        size="xl",
        children=[
            dbc.ModalHeader(
                id="modal-dossier-header",
                children=[dbc.ModalTitle("Case Dossier & Evidence Management")],
                close_button=True,
                style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748", "color": "#f7fafc"}
            ),
            dbc.ModalBody(
                id="modal-dossier-body",
                style={"backgroundColor": "#171923", "color": "#e2e8f0", "padding": "20px", "maxHeight": "75vh", "overflowY": "auto"},
                children=[html.Div("Loading dossier...")]
            ),
            dbc.ModalFooter(
                style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"},
                children=[
                    dbc.Button("Close", id="btn-close-dossier", color="secondary", outline=True, size="sm"),
                    dbc.Button("Launch Workspace for this Case →", id="btn-dossier-launch-workspace", color="primary", size="sm", style={"fontWeight": "600"})
                ]
            )
        ]
    )


def build_dossier_content(case_id: str) -> html.Div:
    """Render full case details covering all 10 conceptual domain models."""
    svc = CaseDataService()
    c = svc.get_case(case_id)
    if not c:
        return html.Div("Case not found.", style={"color": "#fc8181"})

    evidence = svc.list_evidence(case_id)
    alerts = svc.list_alerts(case_id)
    timeline = svc.list_timeline_events(case_id)
    reports = svc.list_reports(case_id)
    audit = svc.list_audit_logs(case_id)
    feedback = svc.list_feedback(case_id)
    analysis = svc.list_analysis_results(case_id)

    with svc._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM investigation_entities WHERE case_id = %s;", (case_id,))
            entities = cur.fetchall()
            cur.execute("SELECT * FROM entity_relationships WHERE case_id = %s;", (case_id,))
            relationships = cur.fetchall()

    return html.Div(
        children=[
            # Top Case Summary Header
            html.Div(
                style={"borderBottom": "1px solid #2d3748", "paddingBottom": "14px", "marginBottom": "16px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px"},
                        children=[
                            html.Span(c.get("case_number", ""), style={"color": "#63b3ed", "fontFamily": "monospace", "fontWeight": "700", "fontSize": "14px"}),
                            get_priority_badge(c.get("priority", "MEDIUM")),
                            get_status_badge(c.get("status", "OPEN")),
                            html.Span(f"Crime Type: {c.get('crime_type', 'N/A')}", style={"color": "#a0aec0", "fontSize": "11px", "backgroundColor": "#2d3748", "padding": "2px 8px", "borderRadius": "4px"}),
                            html.Span(f"Location: {c.get('location', 'N/A')}", style={"color": "#a0aec0", "fontSize": "11px", "backgroundColor": "#2d3748", "padding": "2px 8px", "borderRadius": "4px"}),
                        ]
                    ),
                    html.H3(c.get("title", "Untitled Case"), style={"color": "#f7fafc", "fontWeight": "700", "fontSize": "18px", "margin": "0 0 6px 0"}),
                    html.P(c.get("description", "No case narrative entered."), style={"color": "#cbd5e0", "fontSize": "12px", "lineHeight": "1.5", "margin": 0})
                ]
            ),

            # Tabs across the 10 domain models
            dcc.Tabs(
                id="dossier-tabs",
                value="tab-entities-rel",
                className="dossier-tabs-bar",
                children=[
                    # 1. Entities & Relations
                    dcc.Tab(
                        label=f"👥 Entities ({len(entities)}) & 🔗 Relations ({len(relationships)})",
                        value="tab-entities-rel",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                html.H5("Identified Entities", style={"fontSize": "13px", "fontWeight": "700", "color": "#e2e8f0"}),
                                html.Div(
                                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px", "marginBottom": "16px"},
                                    children=[
                                        html.Div(
                                            style={"backgroundColor": "#2d3748", "border": "1px solid #4a5568", "padding": "6px 10px", "borderRadius": "6px", "fontSize": "11px"},
                                            children=[
                                                html.B(ent.get("name", "Unknown"), style={"color": "#f7fafc"}),
                                                html.Span(f" ({ent.get('entity_type', 'PERSON')})", style={"color": "#a0aec0", "fontSize": "10px"})
                                            ]
                                        ) for ent in entities[:40]
                                    ]
                                ),
                                html.H5("Operational Relationships", style={"fontSize": "13px", "fontWeight": "700", "color": "#e2e8f0"}),
                                html.Div(
                                    style={"maxHeight": "200px", "overflowY": "auto"},
                                    children=[
                                        html.Div(
                                            style={"padding": "4px 8px", "borderBottom": "1px solid #2d3748", "fontSize": "11px", "color": "#cbd5e0"},
                                            children=f"• Link #{rel.get('id', '')[:8]} — Type: {rel.get('relationship_type')} | Confidence: {rel.get('confidence', 1.0)} | AI Predicted: {bool(rel.get('predicted', 0))}"
                                        ) for rel in relationships[:30]
                                    ]
                                )
                            ])
                        ]
                    ),

                    # 2. Evidence (Dedicated Pipeline Section)
                    dcc.Tab(
                        label=f"📁 Evidence ({len(evidence)})",
                        value="tab-evidence",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                build_dedicated_evidence_section(case_id, evidence)
                            ])
                        ]
                    ),

                    # 3. Forensic Alerts
                    dcc.Tab(
                        label=f"🚨 Alerts ({len(alerts)})",
                        value="tab-alerts",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                # Summary ribbon
                                html.Div(
                                    style={"backgroundColor": "#2d3748", "borderRadius": "6px", "padding": "10px 14px", "marginBottom": "14px",
                                           "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                                    children=[
                                        html.Div([
                                            html.Span(f"🚨 {len(alerts)} alert{'s' if len(alerts) != 1 else ''} detected",
                                                      style={"color": "#f7fafc", "fontWeight": "700", "fontSize": "13px"}),
                                            html.Div(
                                                " · ".join([
                                                    f"🔴 {sum(1 for a in alerts if (a.get('severity') or '').upper() == 'CRITICAL')} Critical",
                                                    f"🟠 {sum(1 for a in alerts if (a.get('severity') or '').upper() == 'HIGH')} High",
                                                    f"🟡 {sum(1 for a in alerts if (a.get('severity') or '').upper() == 'MEDIUM')} Medium",
                                                ]),
                                                style={"color": "#a0aec0", "fontSize": "11px", "marginTop": "3px"}
                                            ),
                                        ]),
                                        dbc.Button("Open Full Alerts Panel →",
                                                   id="btn-dossier-open-alerts-panel",
                                                   size="sm", color="warning", outline=True,
                                                   style={"fontSize": "11px"}),
                                    ]
                                ),
                                # Quick preview: top 5 most critical alerts
                                html.Div(
                                    children=[
                                        html.Div(
                                            style={
                                                "backgroundColor": "#2d3748",
                                                "borderLeft": "4px solid " + (
                                                    "#e53e3e" if (al.get("severity") or "").upper() == "CRITICAL" else
                                                    "#dd6b20" if (al.get("severity") or "").upper() == "HIGH" else
                                                    "#d69e2e" if (al.get("severity") or "").upper() == "MEDIUM" else "#718096"
                                                ),
                                                "padding": "8px 12px",
                                                "borderRadius": "4px",
                                                "marginBottom": "6px"
                                            },
                                            children=[
                                                html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}, children=[
                                                    html.B(al.get("title", "Anomaly Alert"), style={"color": "#f7fafc", "fontSize": "12px"}),
                                                    get_priority_badge(al.get("severity", "MEDIUM"))
                                                ]),
                                                html.P((al.get("explanation") or "")[:120] + ("…" if len(al.get("explanation") or "") > 120 else ""),
                                                       style={"color": "#e2e8f0", "fontSize": "11px", "margin": "3px 0"}),
                                                html.Div(f"Subject: {al.get('subject', 'N/A')} · Status: {al.get('status', 'OPEN')}",
                                                         style={"fontSize": "10px", "color": "#a0aec0"})
                                            ]
                                        ) for al in sorted(alerts, key=lambda x: {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}.get((x.get("severity") or "").upper(), 4))[:5]
                                    ] if alerts else [html.P("No forensic anomalies currently flagged for this case.", style={"color": "#718096", "fontSize": "12px"})]
                                ),
                                html.Div(
                                    style={"marginTop": "10px", "backgroundColor": "#2d1b00", "border": "1px solid #744210",
                                           "borderRadius": "4px", "padding": "8px 12px"},
                                    children=[
                                        html.Span("⚠️ FORENSIC DISCLAIMER: ", style={"color": "#f6ad55", "fontWeight": "700", "fontSize": "10px"}),
                                        html.Span("An anomaly is a statistical signal only — NOT evidence of criminal activity. "
                                                  "Every flagged entity must be independently verified by a qualified investigator.",
                                                  style={"color": "#fbd38d", "fontSize": "10px"})
                                    ]
                                )
                            ])
                        ]
                    ),


                    # 4. Timeline
                    dcc.Tab(
                        label=f"⏱️ Timeline ({len(timeline)})",
                        value="tab-timeline",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            style={"padding": "8px 12px", "borderLeft": "2px solid #3182ce", "marginLeft": "10px", "marginBottom": "10px"},
                                            children=[
                                                html.Span(str(ev.get("timestamp", ""))[:19], style={"color": "#63b3ed", "fontSize": "11px", "fontFamily": "monospace"}),
                                                html.B(f" — {ev.get('title', '')}", style={"color": "#f7fafc", "fontSize": "12px"}),
                                                html.P(ev.get("description", ""), style={"color": "#cbd5e0", "fontSize": "11px", "margin": "2px 0 0 0"}),
                                                html.Span(f"📍 {ev.get('location', 'N/A')}", style={"color": "#718096", "fontSize": "10px"})
                                            ]
                                        ) for ev in timeline
                                    ] if timeline else [html.P("No chronological timeline events recorded yet.", style={"color": "#718096", "fontSize": "12px"})]
                                )
                            ])
                        ]
                    ),

                    # 5. Reports
                    dcc.Tab(
                        label=f"📄 Reports ({len(reports)})",
                        value="tab-reports",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            style={"backgroundColor": "#2d3748", "padding": "10px 14px", "borderRadius": "6px", "marginBottom": "8px"},
                                            children=[
                                                html.B(rep.get("title", ""), style={"color": "#f7fafc"}),
                                                html.Span(f" ({rep.get('report_type', 'SUMMARY')})", style={"color": "#9ae6b4", "fontSize": "11px"}),
                                                html.P(rep.get("content", ""), style={"color": "#cbd5e0", "fontSize": "12px", "margin": "6px 0", "whiteSpace": "pre-wrap"}),
                                                html.Div(f"Author: {rep.get('generated_by', 'IO')} | Created: {str(rep.get('created_at', ''))[:10]}", style={"color": "#718096", "fontSize": "10px"})
                                            ]
                                        ) for rep in reports
                                    ] if reports else [html.P("No dossier reports generated yet for this case.", style={"color": "#718096", "fontSize": "12px"})]
                                )
                            ])
                        ]
                    ),

                    # 6. Audit Trail
                    dcc.Tab(
                        label=f"🛡️ Audit Trail ({len(audit)})",
                        value="tab-audit",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                html.Div(
                                    style={"maxHeight": "240px", "overflowY": "auto"},
                                    children=[
                                        html.Div(
                                            style={"fontSize": "11px", "padding": "4px 8px", "borderBottom": "1px solid #2d3748", "color": "#a0aec0"},
                                            children=[
                                                html.Span(str(log.get("timestamp", ""))[:19], style={"color": "#63b3ed", "fontFamily": "monospace"}),
                                                html.B(f" | Officer: {log.get('username') or log.get('user_id')} | Action: {log.get('action')}", style={"color": "#e2e8f0"}),
                                                html.Span(f" — {log.get('details', '')}", style={"color": "#718096"})
                                            ]
                                        ) for log in audit
                                    ] if audit else [html.P("No audit logs recorded for this case.", style={"color": "#718096", "fontSize": "12px"})]
                                )
                            ])
                        ]
                    ),

                    # 7. Human Feedback
                    dcc.Tab(
                        label=f"💬 Feedback ({len(feedback)})",
                        value="tab-feedback",
                        style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                        selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                        children=[
                            html.Div(style={"padding": "14px 0"}, children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            style={"backgroundColor": "#2d3748", "padding": "8px 12px", "borderRadius": "4px", "marginBottom": "6px"},
                                            children=[
                                                html.B(f"{fb.get('feedback_type')} → {fb.get('action')}", style={"color": "#68d391" if fb.get("action") == "ACCEPTED" else "#fc8181"}),
                                                html.Span(f" on target '{fb.get('target_id')}'", style={"color": "#cbd5e0", "fontSize": "11px"}),
                                                html.P(f"Notes: {fb.get('notes', 'None')}", style={"color": "#a0aec0", "fontSize": "11px", "margin": "2px 0 0 0"})
                                            ]
                                        ) for fb in feedback
                                    ] if feedback else [html.P("No human feedback recorded yet for this case.", style={"color": "#718096", "fontSize": "12px"})]
                                )
                            ])
                        ]
                    ),

                     # 8. Case Timeline
                     dcc.Tab(
                         label="📅 Timeline",
                         value="tab-timeline",
                         style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                         selected_style={"backgroundColor": "#2b6cb0", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                         children=[
                             html.Div(
                                 style={"padding": "14px 0"},
                                 children=[build_case_timeline(case_id)]
                             )
                         ]
                     ),

                     # 9. Investigation Actions & HITL
                     dcc.Tab(
                         label="⚡ Actions (HITL)",
                         value="tab-actions",
                         style={"backgroundColor": "#1a202c", "color": "#a0aec0", "padding": "8px", "fontSize": "12px"},
                         selected_style={"backgroundColor": "#b7791f", "color": "#ffffff", "padding": "8px", "fontSize": "12px", "fontWeight": "700"},
                         children=[
                             html.Div(
                                 style={"padding": "14px 0"},
                                 children=[build_actions_workflow_panel(case_id)]
                             )
                         ]
                     ),
                ]
            )
        ]
    )



def build_global_nav_bar() -> html.Div:
    """Build persistent top navigation bar featuring the CASE selector, badges, and quick actions."""
    svc = CaseDataService()
    cases = svc.list_cases()
    case_options = [
        {
            "label": f"{c.get('case_number') or c.get('id')} — {c.get('title') or c.get('id')} ({(c.get('priority') or 'MED').upper()})",
            "value": c.get("id")
        }
        for c in cases
    ]
    default_case = "case-synthetic-black-falcon-001" if any(c.get("id") == "case-synthetic-black-falcon-001" for c in cases) else (cases[0].get("id") if cases else "")

    return html.Div(
        id="crimenet-global-nav",
        style={
            "backgroundColor": "#10141d",
            "borderBottom": "1px solid #2a3447",
            "padding": "0 20px",
            "height": "56px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.4)"
        },
        children=[
            # Left: Brand & Case Selector
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "14px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "6px", "cursor": "pointer"},
                        children=[
                            html.Span("🛡️", style={"fontSize": "20px"}),
                            html.Span("CrimeNet", style={"fontWeight": "900", "fontSize": "17px", "color": "#f7fafc", "letterSpacing": "1px"}),
                            html.Span("CASE OS", style={"fontSize": "9px", "fontWeight": "800", "backgroundColor": "rgba(99, 179, 237, 0.2)", "color": "#63b3ed", "padding": "2px 6px", "borderRadius": "3px", "letterSpacing": "1px"})
                        ]
                    ),
                    html.Span("|", style={"color": "#2d3748"}),
                    # Prominent CASE Selector
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span("CASE:", style={"fontWeight": "900", "fontSize": "12px", "color": "#38bdf8", "letterSpacing": "1px"}),
                            dcc.Dropdown(
                                id="global-case-selector",
                                options=case_options,
                                value=default_case,
                                clearable=False,
                                searchable=True,
                                style={
                                    "width": "350px",
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "color": "#1a202c",
                                }
                            )
                        ]
                    )
                ]
            ),

            # Center: Active Case Context Banner Pill
            html.Div(
                id="active-case-header-display",
                style={"display": "flex", "alignItems": "center", "gap": "8px"},
                children=[
                    html.Span("CASE-BF-2026-001", style={"fontSize": "11px", "fontFamily": "monospace", "fontWeight": "700", "color": "#cbd5e0", "backgroundColor": "#1e293b", "padding": "3px 8px", "borderRadius": "4px"}),
                    html.Span("CRITICAL", style={"fontSize": "10px", "fontWeight": "800", "backgroundColor": "rgba(239, 68, 68, 0.2)", "color": "#fca5a5", "padding": "2px 7px", "borderRadius": "4px"}),
                    html.Span("ACTIVE", style={"fontSize": "10px", "fontWeight": "800", "backgroundColor": "rgba(16, 185, 129, 0.2)", "color": "#86efac", "padding": "2px 7px", "borderRadius": "4px"}),
                    html.Span("25 Entities • 26 Links • 4 Alerts", style={"fontSize": "11px", "color": "#94a3b8", "marginLeft": "4px"})
                ]
            ),

            # Right: Operator / Officer Info & Actions
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    dbc.Button(
                        "📁 Case Directory",
                        id="nav-btn-case-directory",
                        color="secondary",
                        size="sm",
                        outline=True,
                        style={"fontSize": "11px", "fontWeight": "600", "padding": "4px 10px"}
                    ),
                    dbc.Button(
                        "+ New Case",
                        id="nav-btn-new-case",
                        color="success",
                        size="sm",
                        outline=True,
                        style={"fontSize": "11px", "fontWeight": "600", "padding": "4px 10px"}
                    ),
                    html.Span("|", style={"color": "#2d3748"}),
                    html.Span("🟢 MySQL Connected", style={"fontSize": "11px", "color": "#68d391", "fontWeight": "600"}),
                    html.Div(
                        style={"display": "none"},
                        children=[
                            dbc.Button("Dashboard", id="nav-btn-dashboard"),
                            dbc.Button("Workspace", id="nav-btn-workspace"),
                        ]
                    )
                ]
            )
        ]
    )


def build_top_ask_crimenet_bar() -> html.Div:
    """Build the prominent top Ask CrimeNet query bar spanning the workspace."""
    return html.Div(
        id="top-ask-crimenet-container",
        style={
            "backgroundColor": "#121620",
            "borderBottom": "1px solid #2a3447",
            "padding": "7px 20px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "gap": "14px",
            "flexWrap": "wrap",
        },
        children=[
            # Query bar input
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "8px", "flex": "1", "minWidth": "340px"},
                children=[
                    html.Span("🤖", style={"fontSize": "18px"}),
                    dbc.Input(
                        id="top-ask-crimenet-input",
                        type="text",
                        placeholder="Ask CrimeNet... (e.g. 'Why is Rahul connected to Amit?', 'Trace Hawala money flow', 'Show unverified AI links')",
                        style={
                            "backgroundColor": "#0c0f17",
                            "color": "#f7fafc",
                            "border": "1px solid #2d3748",
                            "borderRadius": "6px",
                            "padding": "5px 12px",
                            "fontSize": "12px",
                        }
                    ),
                    dbc.Button(
                        [html.Span("⚡ "), "Ask Agent"],
                        id="top-ask-crimenet-submit-btn",
                        color="primary",
                        size="sm",
                        style={"fontWeight": "700", "fontSize": "11.5px", "padding": "5px 14px", "whiteSpace": "nowrap"}
                    )
                ]
            ),
            # Suggestion Chips
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "6px", "flexWrap": "wrap"},
                children=[
                    html.Span("Quick Prompts:", style={"color": "#718096", "fontSize": "10.5px", "fontWeight": "700"}),
                    dbc.Button("Why is Rahul connected to Amit?", id="top-ask-chip-1", size="sm", color="secondary", outline=True, style={"fontSize": "10.5px", "padding": "2px 8px", "borderRadius": "10px", "borderColor": "#3182ce", "color": "#90cdf4"}),
                    dbc.Button("Hawala Money Flow", id="top-ask-chip-2", size="sm", color="secondary", outline=True, style={"fontSize": "10.5px", "padding": "2px 8px", "borderRadius": "10px", "borderColor": "#2f855a", "color": "#9ae6b4"}),
                    dbc.Button("Uncorroborated Claims", id="top-ask-chip-3", size="sm", color="secondary", outline=True, style={"fontSize": "10.5px", "padding": "2px 8px", "borderRadius": "10px", "borderColor": "#dd6b20", "color": "#fbd38d"}),
                    dbc.Button("High Risk Suspects", id="top-ask-chip-4", size="sm", color="secondary", outline=True, style={"fontSize": "10.5px", "padding": "2px 8px", "borderRadius": "10px", "borderColor": "#e53e3e", "color": "#feb2b2"}),
                ]
            )
        ]
    )


def build_case_directory_modal() -> html.Div:
    """Build modal displaying the case directory cards so investigators can browse cases without leaving the workspace."""
    svc = CaseDataService()
    cases = svc.list_cases()
    return html.Div([
        dbc.Modal(
            id="modal-case-directory",
            is_open=False,
            size="xl",
            scrollable=True,
            children=[
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span("📁", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5("Investigation Cases Directory", style={"margin": "0", "fontWeight": "800", "color": "#f7fafc"}),
                                html.Span("Select an investigation case to focus the central graph and intelligence workspace.", style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748"}
                ),
                dbc.ModalBody(
                    style={"backgroundColor": "#0f1117", "color": "#cbd5e0", "padding": "18px"},
                    children=[
                        html.Div(
                            id="case-directory-grid",
                            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fill, minmax(320px, 1fr))", "gap": "14px"},
                            children=[build_case_card(c) for c in cases]
                        )
                    ]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="btn-close-case-directory", color="secondary", size="sm"),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


def register_dashboard_callbacks(dash_app) -> None:
    """Register all interactive callbacks for the CrimeNet Case Dashboard."""

    # 1. Filter Cases (Search text, priority dropdown, status dropdown, refresh, create trigger)
    @dash_app.callback(
        Output("dashboard-cases-grid", "children"),
        [
            Input("dashboard-search-input", "value"),
            Input("dashboard-priority-filter", "value"),
            Input("dashboard-status-filter", "value"),
            Input("btn-refresh-dashboard", "n_clicks"),
            Input("case-refresh-trigger", "data"),
        ],
        prevent_initial_call=False
    )
    def filter_cases_callback(search_val, priority_val, status_val, _refresh, _trigger):
        svc = CaseDataService()
        cases = svc.list_cases()
        filtered = []
        for c in cases:
            if priority_val and priority_val != "ALL":
                if (c.get("priority") or "").upper() != priority_val.upper():
                    continue
            if status_val and status_val != "ALL":
                if (c.get("status") or "").upper() != status_val.upper():
                    continue
            if search_val and search_val.strip():
                s = search_val.strip().lower()
                num = (c.get("case_number") or "").lower()
                tit = (c.get("title") or "").lower()
                desc = (c.get("description") or "").lower()
                ctype = (c.get("crime_type") or "").lower()
                loc = (c.get("location") or "").lower()
                if not (s in num or s in tit or s in desc or s in ctype or s in loc):
                    continue
            filtered.append(c)

        if not filtered:
            return [
                html.Div(
                    "No matching investigation cases found. Try adjusting your search query or filters.",
                    style={"textAlign": "center", "padding": "40px", "color": "#718096", "fontSize": "14px"}
                )
            ]
        return [build_case_card(c) for c in filtered]

    # 2. Create Case Modal toggle & form submission
    @dash_app.callback(
        [
            Output("modal-create-case", "is_open"),
            Output("create-case-alert-div", "children"),
            Output("case-refresh-trigger", "data"),
        ],
        [
            Input("btn-open-create-case-modal", "n_clicks"),
            Input("nav-btn-new-case", "n_clicks"),
            Input("btn-cancel-create-case", "n_clicks"),
            Input("btn-submit-create-case", "n_clicks"),
        ],
        [
            State("new-case-title", "value"),
            State("new-case-number", "value"),
            State("new-case-crime-type", "value"),
            State("new-case-priority", "value"),
            State("new-case-status", "value"),
            State("new-case-location", "value"),
            State("new-case-officer", "value"),
            State("new-case-description", "value"),
            State("case-refresh-trigger", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_create_case(open_clicks, nav_clicks, cancel_clicks, submit_clicks,
                           title, case_number, crime_type, priority, status,
                           location, officer, description, current_trigger):
        triggered_id = ctx.triggered_id
        if triggered_id in ("btn-open-create-case-modal", "nav-btn-new-case"):
            return True, "", no_update
        if triggered_id == "btn-cancel-create-case":
            return False, "", no_update
        if triggered_id == "btn-submit-create-case":
            if not title or not title.strip():
                alert = dbc.Alert("Case Title is required to register an investigation.", color="danger", dismissable=True)
                return True, alert, no_update
            
            try:
                svc = CaseDataService()
                new_id = svc.create_case(
                    title=title.strip(),
                    case_number=case_number.strip() if case_number else None,
                    description=description.strip() if description else "",
                    crime_type=crime_type or "ORGANIZED_CRIME",
                    priority=priority or "HIGH",
                    status=status or "ACTIVE",
                    location=location.strip() if location else "",
                    lead_investigator_id=officer.strip() if officer else None,
                    metadata={"lead_officer": officer} if officer else None
                )
                svc.log_audit(new_id, "CASE_CREATED", officer or "investigator", f"Created investigation case: {title.strip()}")
                return False, "", (current_trigger or 0) + 1
            except Exception as ex:
                alert = dbc.Alert(f"Failed to create case: {str(ex)}", color="danger", dismissable=True)
                return True, alert, no_update
        return no_update, no_update, no_update

    # 3. Open Case Dossier Modal (10-Domain Breakdown)
    @dash_app.callback(
        [
            Output("modal-case-dossier", "is_open"),
            Output("modal-dossier-header", "children"),
            Output("modal-dossier-body", "children"),
            Output("dossier-active-case-id-store", "data"),
        ],
        [
            Input({"type": "btn-dossier-case", "index": ALL}, "n_clicks"),
            Input("btn-close-dossier", "n_clicks"),
            Input("btn-dossier-launch-workspace", "n_clicks"),
        ],
        prevent_initial_call=True
    )
    def handle_case_dossier(dossier_clicks, close_clicks, launch_clicks):
        triggered = ctx.triggered_id
        if triggered in ("btn-close-dossier", "btn-dossier-launch-workspace"):
            return False, no_update, no_update, no_update
        if isinstance(triggered, dict) and triggered.get("type") == "btn-dossier-case":
            case_id = triggered.get("index")
            has_clicks = any(dossier_clicks) if isinstance(dossier_clicks, (list, tuple)) else bool(dossier_clicks)
            if not has_clicks:
                return no_update, no_update, no_update, no_update
            svc = CaseDataService()
            c = svc.get_case(case_id)
            if not c:
                return True, [dbc.ModalTitle("Case Not Found")], html.Div("Case record not found in MySQL.", style={"color": "#fc8181"}), None
            title = c.get("title") or case_id
            c_num = c.get("case_number") or ""
            header = [
                dbc.ModalTitle(f"Forensic Dossier: {c_num} — {title}", style={"color": "#f7fafc", "fontWeight": "700", "fontSize": "16px"})
            ]
            content = build_dossier_content(case_id)
            return True, header, content, case_id
        return no_update, no_update, no_update, no_update

    # 4. Enter Investigation Workspace & View Navigation
    @dash_app.callback(
        [
            Output("case-dashboard-view", "style"),
            Output("workspace-view", "style"),
            Output("active-case-store", "data"),
            Output("active-case-header-display", "children"),
            Output("cytoscape", "elements", allow_duplicate=True),
            Output("network-info", "children", allow_duplicate=True),
            Output("node-interaction-table", "children", allow_duplicate=True),
            Output("edge-interaction-table", "children", allow_duplicate=True),
            Output("label-interaction-table", "children", allow_duplicate=True),
            Output("nav-btn-dashboard", "style"),
            Output("nav-btn-workspace", "style"),
        ],
        [
            Input({"type": "btn-open-case", "index": ALL}, "n_clicks"),
            Input("btn-dossier-launch-workspace", "n_clicks"),
            Input("nav-btn-dashboard", "n_clicks"),
            Input("nav-btn-workspace", "n_clicks"),
            Input("btn-switch-to-workspace-direct", "n_clicks"),
            Input("global-case-selector", "value"),
        ],
        [
            State("dossier-active-case-id-store", "data"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=False
    )
    def handle_workspace_navigation(open_case_clicks, dossier_launch_clicks,
                                    nav_dash_clicks, nav_ws_clicks, switch_direct_clicks,
                                    global_case_val,
                                    dossier_case_id, active_case_data):
        from visualizer import app as vapp
        from visualizer import dash_formatter

        triggered = ctx.triggered_id
        dash_active_style = {"fontSize": "12px", "fontWeight": "600", "padding": "5px 12px", "backgroundColor": "#2b6cb0", "borderColor": "#2b6cb0", "color": "#ffffff"}
        dash_inactive_style = {"fontSize": "12px", "fontWeight": "600", "padding": "5px 12px", "borderColor": "#4a5568", "color": "#cbd5e0", "backgroundColor": "transparent"}
        ws_active_style = {"fontSize": "12px", "fontWeight": "600", "padding": "5px 12px", "backgroundColor": "#2b6cb0", "borderColor": "#2b6cb0", "color": "#ffffff"}
        ws_inactive_style = {"fontSize": "12px", "fontWeight": "600", "padding": "5px 12px", "borderColor": "#4a5568", "color": "#cbd5e0", "backgroundColor": "transparent"}

        # Return to Dashboard
        if triggered == "nav-btn-dashboard":
            return (
                {"display": "block"}, {"display": "none"},
                no_update, no_update,
                no_update, no_update, no_update, no_update, no_update,
                dash_active_style, ws_inactive_style
            )

        # Switch to Workspace directly
        if triggered in ("nav-btn-workspace", "btn-switch-to-workspace-direct"):
            return (
                {"display": "none"}, {"display": "block"},
                no_update, no_update,
                no_update, no_update, no_update, no_update, no_update,
                dash_inactive_style, ws_active_style
            )

        # A specific case was chosen to enter workspace
        target_case_id = None
        if triggered == "global-case-selector" and global_case_val:
            target_case_id = global_case_val
        elif triggered == "btn-dossier-launch-workspace" and dossier_case_id:
            target_case_id = dossier_case_id
        elif isinstance(triggered, dict) and triggered.get("type") == "btn-open-case":
            has_clicks = any(open_case_clicks) if isinstance(open_case_clicks, (list, tuple)) else bool(open_case_clicks)
            if has_clicks:
                target_case_id = triggered.get("index")
        elif not triggered and global_case_val:
            # Initial page load: seed workspace with default case
            target_case_id = global_case_val

        if not target_case_id:
            return (
                no_update, no_update,
                no_update, no_update,
                no_update, no_update, no_update, no_update, no_update,
                no_update, no_update
            )

        svc = CaseDataService()
        c = svc.get_case(target_case_id)
        if not c:
            return (
                no_update, no_update,
                no_update, no_update,
                no_update, no_update, no_update, no_update, no_update,
                no_update, no_update
            )

        net = svc.build_active_network_for_case(target_case_id)
        if not net:
            return (
                no_update, no_update,
                no_update, no_update,
                no_update, no_update, no_update, no_update, no_update,
                no_update, no_update
            )

        vapp.active_network = net
        vapp.style.reset()
        vapp.style.set_type_styles(net.get_active_node_types())

        node_table, edge_table, label_table = vapp.get_interaction_tables(net)
        net_info = dash_formatter.dash_network_info(net.get_active_network_info())

        c_num = c.get("case_number") or target_case_id
        c_title = c.get("title") or "Investigation"
        c_priority = c.get("priority") or "MEDIUM"

        header_banner = html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "10px", "backgroundColor": "#1a202c", "padding": "4px 12px", "borderRadius": "6px", "border": "1px solid #2d3748"},
            children=[
                html.Span("ACTIVE CASE:", style={"color": "#a0aec0", "fontWeight": "700", "fontSize": "11px", "letterSpacing": "0.5px"}),
                html.Span(c_num, style={"color": "#63b3ed", "fontFamily": "monospace", "fontWeight": "700", "fontSize": "12px"}),
                get_priority_badge(c_priority),
                html.Span(f"• {c_title}", style={"color": "#f7fafc", "fontWeight": "600", "fontSize": "12px"}),
                html.Span(f"({len(net.nodes)} entities, {len(net.edges)} links)", style={"color": "#9ae6b4", "fontSize": "11px", "fontWeight": "600"}),
            ]
        )

        case_store_data = {
            "case_id": c["id"],
            "case_number": c_num,
            "title": c_title,
            "priority": c_priority,
            "status": c.get("status", "OPEN"),
            "node_count": len(net.nodes),
            "edge_count": len(net.edges)
        }

        svc.log_audit(c["id"], "WORKSPACE_ACCESSED", "Lead Investigator", f"Entered investigation workspace for case {c_num}")

        return (
            {"display": "none"}, {"display": "block"},
            case_store_data, header_banner,
            net.elements, net_info, node_table, edge_table, label_table,
            dash_inactive_style, ws_active_style
        )

    # 4b. Case Directory modal toggle
    @dash_app.callback(
        Output("modal-case-directory", "is_open"),
        [
            Input("nav-btn-case-directory", "n_clicks"),
            Input("btn-close-case-directory", "n_clicks"),
            Input({"type": "btn-open-case", "index": ALL}, "n_clicks"),
        ],
        [State("modal-case-directory", "is_open")],
        prevent_initial_call=True
    )
    def toggle_case_directory_modal(open_clicks, close_clicks, select_clicks, is_open):
        triggered = ctx.triggered_id
        if triggered == "nav-btn-case-directory":
            return not is_open
        elif triggered == "btn-close-case-directory":
            return False
        elif isinstance(triggered, dict) and triggered.get("type") == "btn-open-case":
            if any(select_clicks) if isinstance(select_clicks, (list, tuple)) else bool(select_clicks):
                return False
        return is_open

    # 5. Selected Evidence File Banner indicator
    @dash_app.callback(
        Output("evidence-selected-file-banner", "children"),
        Input("evidence-file-upload", "filename"),
        prevent_initial_call=True
    )
    def update_selected_evidence_filename(filename):
        if not filename:
            return ""
        ext = os.path.splitext(filename)[1].lower()
        badge_color = "#38a169" if ext in (".pdf", ".txt", ".csv", ".json") else "#e53e3e"
        return html.Div(
            style={"backgroundColor": "#171923", "border": f"1px solid {badge_color}", "borderRadius": "4px", "padding": "6px 10px", "display": "flex", "alignItems": "center", "gap": "8px"},
            children=[
                html.Span("SELECTED EXHIBIT:", style={"color": "#a0aec0", "fontWeight": "700", "fontSize": "11px"}),
                html.Span(filename, style={"color": "#f7fafc", "fontWeight": "700", "fontSize": "12px", "fontFamily": "monospace"}),
                html.Span("• Ready for validation & graph ingestion", style={"color": "#68d391", "fontSize": "11px", "fontWeight": "600"})
            ]
        )

    # 6. End-to-End Evidence Ingestion Pipeline (Upload -> Validate -> Store -> Process -> Extract -> Analyze -> Link)
    @dash_app.callback(
        [
            Output("evidence-pipeline-status-div", "children"),
            Output("dossier-evidence-registry-container", "children"),
            Output("case-refresh-trigger", "data", allow_duplicate=True),
            Output("cytoscape", "elements", allow_duplicate=True),
            Output("network-info", "children", allow_duplicate=True),
            Output("node-interaction-table", "children", allow_duplicate=True),
            Output("edge-interaction-table", "children", allow_duplicate=True),
            Output("label-interaction-table", "children", allow_duplicate=True),
            Output("evidence-file-upload", "contents"),
        ],
        Input("btn-process-evidence", "n_clicks"),
        [
            State("evidence-file-upload", "contents"),
            State("evidence-file-upload", "filename"),
            State("evidence-type-select", "value"),
            State("evidence-title-input", "value"),
            State("evidence-source-input", "value"),
            State("evidence-desc-input", "value"),
            State("dossier-active-case-id-store", "data"),
            State("case-refresh-trigger", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_evidence_ingestion_pipeline(
        process_clicks,
        file_contents,
        filename,
        declared_type,
        title,
        source_ref,
        description,
        case_id,
        current_trigger
    ):
        from visualizer import app as vapp
        from visualizer import dash_formatter

        if not process_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        if not case_id:
            err_alert = dbc.Alert("Error: No active investigation case context found.", color="danger", dismissable=True)
            return err_alert, no_update, no_update, no_update, no_update, no_update, no_update, no_update, None

        if not file_contents or not filename:
            err_alert = dbc.Alert("Please select or drop a forensic file (PDF, TXT, CSV, or JSON) before clicking Ingest.", color="warning", dismissable=True)
            return err_alert, no_update, no_update, no_update, no_update, no_update, no_update, no_update, None

        # Decode base64 file contents
        try:
            if "," in file_contents:
                _, b64_data = file_contents.split(",", 1)
            else:
                b64_data = file_contents
            file_bytes = base64.b64decode(b64_data)
        except Exception as dec_err:
            err_alert = dbc.Alert(f"File decoding error: {str(dec_err)}", color="danger", dismissable=True)
            return err_alert, no_update, no_update, no_update, no_update, no_update, no_update, no_update, None

        # Execute Pipeline
        processor = EvidenceProcessor()
        file_type_arg = None if declared_type == "AUTO" else declared_type
        
        result = processor.process_evidence_pipeline(
            case_id=case_id,
            filename=filename,
            file_bytes=file_bytes,
            declared_type=file_type_arg,
            title=title,
            source_ref=source_ref,
            description=description,
            user_id="u-002"
        )

        svc = CaseDataService()
        updated_evidence_list = svc.list_evidence(case_id)
        registry_view = build_evidence_registry_view(updated_evidence_list)
        new_trigger = (current_trigger or 0) + 1

        if not result["success"]:
            # Error State: display real error message clearly without fake success
            error_banner = html.Div(
                style={
                    "backgroundColor": "#2d1515",
                    "border": "1px solid #e53e3e",
                    "borderRadius": "6px",
                    "padding": "12px 16px",
                    "marginBottom": "12px"
                },
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "6px"},
                        children=[
                            html.Span("❌", style={"fontSize": "16px"}),
                            html.B(f"Evidence Processing Failed ({result.get('stage', 'Pipeline')} Stage)", style={"color": "#feb2b2", "fontSize": "13px"})
                        ]
                    ),
                    html.P(f"Filename: {filename}", style={"color": "#cbd5e0", "fontSize": "11px", "fontFamily": "monospace", "margin": "0 0 4px 0"}),
                    html.Div(
                        style={
                            "backgroundColor": "#1a202c",
                            "border": "1px solid #4a5568",
                            "borderRadius": "4px",
                            "padding": "8px 12px",
                            "color": "#fc8181",
                            "fontSize": "11px",
                            "fontFamily": "monospace"
                        },
                        children=result.get("error", "Unknown error occurred.")
                    )
                ]
            )
            return error_banner, registry_view, new_trigger, no_update, no_update, no_update, no_update, no_update, None

        # Success State
        ent_cnt = result.get("entities_count", 0)
        rel_cnt = result.get("relations_count", 0)
        sha_hash = result.get("sha256", "")
        sample_entities = result.get("entities_sample", [])
        entity_chips = [
            html.Span(
                f"{e.get('text')} ({e.get('type')})",
                style={"backgroundColor": "#2d3748", "color": "#f7fafc", "padding": "2px 8px", "borderRadius": "4px", "fontSize": "10px", "border": "1px solid #4a5568"}
            ) for e in sample_entities[:8]
        ]

        success_banner = html.Div(
            style={
                "backgroundColor": "#1c4532",
                "border": "1px solid #38a169",
                "borderRadius": "6px",
                "padding": "12px 16px",
                "marginBottom": "12px"
            },
            children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "6px"},
                    children=[
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "8px"},
                            children=[
                                html.Span("✅", style={"fontSize": "16px"}),
                                html.B("Evidence Successfully Processed & Linked to Investigation Graph!", style={"color": "#c6f6d5", "fontSize": "13px"})
                            ]
                        ),
                        html.Span("STATUS: PROCESSED", style={"backgroundColor": "#22543d", "color": "#9ae6b4", "fontWeight": "700", "fontSize": "10px", "padding": "2px 8px", "borderRadius": "4px"})
                    ]
                ),
                html.Div(
                    style={"display": "flex", "gap": "14px", "fontSize": "11px", "color": "#e2e8f0", "marginBottom": "6px", "flexWrap": "wrap"},
                    children=[
                        html.Span(f"📁 {filename}", style={"fontFamily": "monospace"}),
                        html.Span(f"👥 {ent_cnt} Entities Linked", style={"color": "#9ae6b4", "fontWeight": "700"}),
                        html.Span(f"🔗 {rel_cnt} Relationships Formed", style={"color": "#63b3ed", "fontWeight": "700"}),
                        html.Span(f"🔒 SHA-256: {sha_hash[:12]}...", style={"color": "#cbd5e0", "fontFamily": "monospace"}),
                    ]
                ),
                html.Div(
                    style={"display": "flex", "flexWrap": "wrap", "gap": "6px", "marginTop": "6px"},
                    children=entity_chips
                ) if entity_chips else None
            ]
        )

        # Update Cytoscape elements for this case if active
        net = svc.build_active_network_for_case(case_id)
        if net:
            vapp.active_network = net
            vapp.style.reset()
            vapp.style.set_type_styles(net.get_active_node_types())
            node_table, edge_table, label_table = vapp.get_interaction_tables(net)
            net_info = dash_formatter.dash_network_info(net.get_active_network_info())
            return (
                success_banner, registry_view, new_trigger,
                net.elements, net_info, node_table, edge_table, label_table, None
            )

        return (
            success_banner, registry_view, new_trigger,
            no_update, no_update, no_update, no_update, no_update, None
        )


    # ── Open Full Alerts Panel from dossier shortcut button ─────────────────
    @dash_app.callback(
        Output("alerts-panel-outer", "style"),
        Input("btn-dossier-open-alerts-panel", "n_clicks"),
        State("alerts-panel-outer", "style"),
        prevent_initial_call=True,
    )
    def toggle_alerts_panel_from_dossier(n_clicks, current_style):
        """Show the dedicated Forensic Alerts Panel when triggered from dossier."""
        from dash.exceptions import PreventUpdate
        if not n_clicks:
            raise PreventUpdate
        is_hidden = (current_style or {}).get("display") == "none"
        return {
            "display": "block" if is_hidden else "none",
            "position": "fixed",
            "top": "60px",
            "left": "0",
            "right": "0",
            "bottom": "0",
            "zIndex": "8000",
            "backgroundColor": "#0f1117",
            "overflowY": "auto",
            "boxShadow": "0 -4px 20px rgba(0,0,0,0.5)",
        }

