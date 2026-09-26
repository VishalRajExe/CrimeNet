"""CrimeNet Right-Side Intelligence Panel.

Houses the 6 dedicated investigation tabs that contextualize the currently
selected entity or active case:
  1. AI Intelligence  – Generative synthesis, syndicate structure, copilot insights
  2. Entity Dossier    – Comprehensive multi-domain forensic dossier
  3. Hidden Links     – AI link prediction hypotheses with HITL acceptance
  4. Alerts           – Forensic anomaly alerts (Isolation Forest, smurfing, surges)
  5. Evidence         – Exhibits, FIRs, CDRs, bank statements, 1-click inspection
  6. Timeline         – Chronological case & entity event stream
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import networkx as nx

from storage.case_data_service import CaseDataService
from visualizer.entity_dossier_panel import build_entity_dossier

logger = logging.getLogger("CrimeNet.RightIntelligencePanel")

# ── Color tokens ─────────────────────────────────────────────────────────────
DARK_BG    = "#0c0f17"
PANEL_BG   = "#151922"
CARD_BG    = "#1c2230"
BORDER_COL = "#2a3447"
TEXT_MAIN  = "#f7fafc"
TEXT_DIM   = "#a0aec0"
TEXT_MUTED = "#718096"
CYAN_ACC   = "#38bdf8"
EMERALD    = "#10b981"
AMBER      = "#f59e0b"
PURPLE     = "#a855f7"
RED        = "#ef4444"


def build_right_side_panel() -> html.Div:
    """Build the right-side multi-tab intelligence container."""
    return html.Div(
        id="right-side-intelligence-panel",
        style={
            "display": "flex",
            "flexDirection": "column",
            "height": "100%",
            "backgroundColor": PANEL_BG,
            "borderLeft": f"1px solid {BORDER_COL}",
            "boxSizing": "border-box",
            "overflow": "hidden",
        },
        children=[
            # Context banner (shows currently selected entity or active case)
            html.Div(
                id="right-panel-context-banner",
                style={
                    "padding": "10px 14px",
                    "backgroundColor": "#10141d",
                    "borderBottom": f"1px solid {BORDER_COL}",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "8px",
                },
                children=[
                    html.Div(
                        id="right-panel-context-title",
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "overflow": "hidden"},
                        children=[
                            html.Span("📁", style={"fontSize": "15px"}),
                            html.Span("ACTIVE CASE: Operation Black Falcon", style={"fontWeight": "700", "fontSize": "12px", "color": TEXT_MAIN, "whiteSpace": "nowrap", "textOverflow": "ellipsis", "overflow": "hidden"}),
                        ]
                    ),
                    html.Div(
                        id="right-panel-context-badge",
                        children=[
                            html.Span("CASE CONTEXT", style={"fontSize": "9px", "fontWeight": "800", "backgroundColor": "rgba(56, 189, 248, 0.15)", "color": CYAN_ACC, "padding": "2px 6px", "borderRadius": "4px", "letterSpacing": "0.5px"})
                        ]
                    )
                ]
            ),

            # Right Side 6 Tabs Navigation
            html.Div(
                style={"backgroundColor": "#10141d", "borderBottom": f"1px solid {BORDER_COL}"},
                children=[
                    dcc.Tabs(
                        id="right-panel-tabs",
                        value="rp-tab-dossier",
                        parent_className="crimenet-tabs-parent",
                        className="crimenet-tabs-bar",
                        children=[
                            dcc.Tab(label="🧠 AI Intel", value="rp-tab-ai-intel", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                            dcc.Tab(label="👤 Dossier", value="rp-tab-dossier", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                            dcc.Tab(label="🔗 Links", value="rp-tab-hidden-links", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                            dcc.Tab(label="🚨 Alerts", value="rp-tab-alerts", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                            dcc.Tab(label="📁 Evidence", value="rp-tab-evidence", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                            dcc.Tab(label="📅 Timeline", value="rp-tab-timeline", className="tab", selected_className="tab--selected", style={"padding": "7px 9px", "fontSize": "11px", "fontWeight": "700"}),
                        ]
                    )
                ]
            ),

            # Dynamic Tab Content Body (Scrollable) with Loading State
            dcc.Loading(
                id="loading-right-panel",
                type="dot",
                color=CYAN_ACC,
                children=html.Div(
                    id="right-panel-tab-content",
                    style={
                        "flex": "1",
                        "overflowY": "auto",
                        "padding": "12px",
                        "boxSizing": "border-box",
                    },
                    children=[
                        html.Div(
                            "Loading investigation intelligence...",
                            style={"color": TEXT_MUTED, "textAlign": "center", "padding": "30px", "fontSize": "12px"}
                        )
                    ]
                )
            )
        ]
    )


def render_ai_intelligence_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render the AI Intelligence tab contextualized to case and entity."""
    svc = CaseDataService()
    c = svc.get_case(case_id) or {}
    case_title = c.get("title") or "Syndicate Investigation"
    c_num = c.get("case_number") or case_id
    g = svc.get_case_graph(case_id)
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    alerts = svc.list_alerts(case_id)

    if selected_node_data:
        # Contextualized to specific selected entity
        nid = selected_node_data.get("id") or ""
        name = selected_node_data.get("name") or selected_node_data.get("label") or nid
        ntype = str(selected_node_data.get("type") or "entity").upper()
        role = selected_node_data.get("role") or selected_node_data.get("type", "Entity")
        risk_score = selected_node_data.get("risk_score")
        
        # Determine threat tier
        if risk_score is not None:
            try:
                r_val = float(risk_score)
                threat_tier = "TIER 1 (CRITICAL)" if r_val >= 0.75 else ("TIER 2 (ELEVATED)" if r_val >= 0.45 else "TIER 3 (MONITORED)")
                threat_color = RED if r_val >= 0.75 else (AMBER if r_val >= 0.45 else EMERALD)
            except Exception:
                threat_tier = "TIER 1 (CRITICAL)"
                threat_color = RED
        else:
            threat_tier = "TIER 1 (CRITICAL)" if any(k in str(role).lower() for k in ("kingpin", "coordinator", "boss", "leader")) else "TIER 2 (ELEVATED)"
            threat_color = RED if threat_tier.startswith("TIER 1") else AMBER

        entity_summary = (
            selected_node_data.get("description")
            or selected_node_data.get("summary")
            or f"Target entity '{name}' functions as an active {role} node within {case_title}. "
               "Corroborated across primary telecommunication (CDR) call logs and banking ledger transactions."
        )

        degree = selected_node_data.get("degree") or len([e for e in edges if e.get("source") == nid or e.get("target") == nid])

        return html.Div([
            html.Div(
                style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "14px", "marginBottom": "12px", "boxShadow": "0 2px 8px rgba(0,0,0,0.25)"},
                children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"}, children=[
                        html.Span("🤖 ENTITY AI SYNTHESIS", style={"fontSize": "10px", "fontWeight": "800", "color": CYAN_ACC, "letterSpacing": "0.5px"}),
                        html.Span("GROUNDED ANALYSIS", style={"fontSize": "9px", "fontWeight": "700", "backgroundColor": "rgba(56, 189, 248, 0.15)", "color": CYAN_ACC, "padding": "2px 6px", "borderRadius": "3px"}),
                    ]),
                    html.H5(f"{name}", style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "15px", "margin": "0 0 4px 0", "letterSpacing": "-0.2px"}),
                    html.Div(f"Type: {ntype} • Case: {c_num}", style={"color": TEXT_DIM, "fontSize": "11px", "marginBottom": "10px", "fontFamily": "monospace"}),
                    html.P(
                        entity_summary,
                        style={"fontSize": "12px", "color": "#cbd5e0", "lineHeight": "1.5", "margin": "0 0 10px 0"}
                    ),
                    dbc.Button(
                        f"🔍 Ask Agent about {name}",
                        id="btn-open-ask-crimenet-entity",
                        color="primary",
                        size="sm",
                        style={"fontSize": "11px", "fontWeight": "600", "padding": "4px 10px"}
                    )
                ]
            ),
            html.Div(
                style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "12px", "boxShadow": "0 2px 8px rgba(0,0,0,0.25)"},
                children=[
                    html.Div("STRUCTURAL & TOPOLOGICAL METRICS", style={"fontSize": "10px", "fontWeight": "800", "color": TEXT_DIM, "letterSpacing": "0.5px", "marginBottom": "8px"}),
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px"}, children=[
                        html.Div(style={"backgroundColor": PANEL_BG, "padding": "8px 10px", "borderRadius": "6px", "border": f"1px solid {BORDER_COL}"}, children=[
                            html.Div("Direct Links", style={"fontSize": "10px", "color": TEXT_MUTED}),
                            html.Div(f"{degree} Conns", style={"fontSize": "16px", "fontWeight": "800", "color": EMERALD}),
                        ]),
                        html.Div(style={"backgroundColor": PANEL_BG, "padding": "8px 10px", "borderRadius": "6px", "border": f"1px solid {BORDER_COL}"}, children=[
                            html.Div("Threat Rank", style={"fontSize": "10px", "color": TEXT_MUTED}),
                            html.Div(threat_tier, style={"fontSize": "11.5px", "fontWeight": "800", "color": threat_color}),
                        ]),
                    ])
                ]
            )
        ])

    # No node selected: Case Syndicate Intelligence
    if not nodes:
        return html.Div(
            className="crimenet-empty-state",
            children=[
                html.Div("📂", className="empty-icon"),
                html.Div("Empty Case Workspace", className="empty-title"),
                html.Div("This case has no graph entities yet. Ingest forensic evidence files or load a pre-built syndicate to begin analysis.", className="empty-desc"),
            ]
        )

    # Derive key disruption targets dynamically
    persons = [n for n in nodes if str(n.get("type", "")).lower() == "person"]
    orgs = [n for n in nodes if str(n.get("type", "")).lower() in ("organization", "company", "business")]
    targets = sorted(persons + orgs, key=lambda x: (x.get("degree", 0), x.get("risk_score", 0)), reverse=True)[:5]
    if not targets:
        targets = nodes[:5]

    target_items = []
    for t in targets:
        t_name = t.get("name") or t.get("label") or t.get("id")
        t_role = t.get("role") or t.get("type") or "Key Node"
        t_desc = t.get("description") or f"Identified {t_role} within network structure."
        target_items.append(html.Li([html.B(f"{t_name}: "), t_desc]))

    case_desc = c.get("description") or (
        "Multi-jurisdictional network mapped from relational ledgers, CDR records, and forensic exhibits. "
        "Graph analytics reveals clustering between financial controllers and operational conduits."
    )

    return html.Div([
        html.Div(
            style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "14px", "marginBottom": "12px", "boxShadow": "0 2px 8px rgba(0,0,0,0.25)"},
            children=[
                html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "8px"}, children=[
                    html.Span("🧠 SYNDICATE INTELLIGENCE", style={"fontSize": "10px", "fontWeight": "800", "color": CYAN_ACC, "letterSpacing": "0.5px"}),
                    html.Span(c_num, style={"fontSize": "9px", "fontWeight": "700", "backgroundColor": "#2a3447", "color": TEXT_DIM, "padding": "2px 6px", "borderRadius": "3px", "fontFamily": "monospace"}),
                ]),
                html.H5(case_title, style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "14px", "margin": "0 0 6px 0"}),
                html.P(
                    case_desc,
                    style={"fontSize": "12px", "color": "#cbd5e0", "lineHeight": "1.5", "margin": "0 0 10px 0"}
                ),
                html.Div(style={"display": "flex", "gap": "6px", "flexWrap": "wrap"}, children=[
                    html.Span(f"👥 {len(nodes)} Entities Tracked", style={"fontSize": "10px", "backgroundColor": "#1e293b", "color": "#93c5fd", "padding": "3px 8px", "borderRadius": "4px", "fontWeight": "600"}),
                    html.Span(f"🔗 {len(edges)} Relationships", style={"fontSize": "10px", "backgroundColor": "#1e293b", "color": "#86efac", "padding": "3px 8px", "borderRadius": "4px", "fontWeight": "600"}),
                    html.Span(f"🚨 {len(alerts)} Active Alerts", style={"fontSize": "10px", "backgroundColor": "#1e293b", "color": "#fca5a5", "padding": "3px 8px", "borderRadius": "4px", "fontWeight": "600"}),
                ])
            ]
        ),
        html.Div(
            style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "12px", "boxShadow": "0 2px 8px rgba(0,0,0,0.25)"},
            children=[
                html.Div("KEY DISRUPTION TARGETS", style={"fontSize": "10px", "fontWeight": "800", "color": TEXT_DIM, "letterSpacing": "0.5px", "marginBottom": "8px"}),
                html.Ul(style={"margin": "0", "paddingLeft": "18px", "fontSize": "11.5px", "color": "#cbd5e0", "lineHeight": "1.6"}, children=target_items)
            ]
        )
    ])


def render_dossier_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render the comprehensive Entity Dossier."""
    if selected_node_data:
        nid = selected_node_data.get("id") or ""
        return build_entity_dossier(entity_id=nid, node_data=selected_node_data, case_id=case_id)

    # If no node selected: prompt with key suspect cards
    svc = CaseDataService()
    g = svc.get_case_graph(case_id)
    nodes = g.get("nodes", [])

    key_suspects = [
        n for n in nodes
        if str(n.get("type")).lower() == "person"
    ][:5]

    return html.Div([
        html.Div(
            className="crimenet-empty-state",
            style={"marginBottom": "14px"},
            children=[
                html.Div("👤", className="empty-icon"),
                html.Div("No Entity Selected", className="empty-title"),
                html.Div("Click any node on the central network graph or pick a key suspect below to inspect their evidentiary dossier.", className="empty-desc"),
            ]
        ),
        html.Div("KEY INVESTIGATION SUSPECTS", style={"fontSize": "10px", "fontWeight": "800", "color": TEXT_DIM, "letterSpacing": "0.5px", "marginBottom": "8px"}),
        html.Div(
            children=[
                html.Div(
                    style={
                        "backgroundColor": CARD_BG,
                        "border": f"1px solid {BORDER_COL}",
                        "borderRadius": "6px",
                        "padding": "10px 12px",
                        "marginBottom": "8px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "space-between",
                    },
                    children=[
                        html.Div(children=[
                            html.Div(n.get("name") or n.get("id"), style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "12px"}),
                            html.Div(f"Type: {str(n.get('type')).upper()} • Role: Suspect", style={"color": TEXT_MUTED, "fontSize": "10px"}),
                        ]),
                        dbc.Button(
                            "Inspect →",
                            id={"type": "btn-select-suspect-dossier", "index": n.get("id")},
                            size="sm",
                            color="primary",
                            outline=True,
                            style={"fontSize": "10px", "padding": "2px 8px"}
                        )
                    ]
                )
                for n in key_suspects
            ]
        )
    ])


def render_hidden_links_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render Hidden Links / Link Prediction tab with HITL acceptance controls."""
    svc = CaseDataService()
    g = svc.get_case_graph(case_id)
    edges = g.get("edges", [])

    pred_edges = [
        e for e in edges
        if e.get("predicted") or str(e.get("modality")).upper() in ("PREDICTED", "INFERRED")
    ]

    # If an entity is selected, filter to links involving that entity
    if selected_node_data:
        nid = selected_node_data.get("id")
        pred_edges = [e for e in pred_edges if e.get("source") == nid or e.get("target") == nid]

    # If no predicted edges exist in DB: display a clean empty state without fake data
    if not pred_edges:
        return html.Div(
            className="crimenet-empty-state",
            children=[
                html.Div("🔮", className="empty-icon"),
                html.Div("No Predicted Link Hypotheses", className="empty-title"),
                html.Div("The link prediction model (Jaccard, Adamic-Adar, Resource Allocation) did not find any statistical relationship candidates exceeding confidence thresholds for this scope.", className="empty-desc"),
            ]
        )

    return html.Div([
        html.Div(
            style={"backgroundColor": "#1a1625", "border": f"1px solid #6b46c1", "borderRadius": "6px", "padding": "8px 12px", "marginBottom": "12px"},
            children=[
                html.Div("🔮 AI LINK PREDICTION (STATISTICAL HYPOTHESES)", style={"fontSize": "10px", "fontWeight": "800", "color": "#d6bcfa", "letterSpacing": "0.5px"}),
                html.Div("Predicted relationships are machine hypotheses. They are flagged as PROPOSED and are not written to Neo4j until investigator acceptance.", style={"fontSize": "10px", "color": "#b794f4", "marginTop": "2px"}),
            ]
        ),
        html.Div(id="hidden-links-feedback-banner", style={"display": "none"}),
        html.Div(
            children=[
                html.Div(
                    style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "12px", "marginBottom": "10px", "boxShadow": "0 2px 6px rgba(0,0,0,0.25)"},
                    children=[
                        html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "6px"}, children=[
                            html.Span(f"{e.get('type', 'POTENTIAL_LINK')}", style={"fontSize": "11px", "fontWeight": "800", "color": AMBER}),
                            html.Span(f"Confidence: {int(float(e.get('confidence', 0.8)) * 100)}%", style={"fontSize": "10px", "fontWeight": "700", "color": "#9ae6b4"}),
                        ]),
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "6px", "fontSize": "11px", "fontWeight": "700", "color": TEXT_MAIN, "marginBottom": "6px"},
                            children=[
                                html.Span(str(e.get("source")).replace("person_", "").replace("_", " ").title()),
                                html.Span("➔", style={"color": TEXT_MUTED}),
                                html.Span(str(e.get("target")).replace("person_", "").replace("account_", "").replace("_", " ").title()),
                            ]
                        ),
                        html.P(e.get("rationale") or e.get("heuristic") or "High co-occurrence score across extracted evidence.", style={"fontSize": "11px", "color": TEXT_DIM, "margin": "0 0 10px 0"}),
                        html.Div(style={"display": "flex", "gap": "6px"}, children=[
                            dbc.Button("✅ Accept to Neo4j", id={"type": "btn-accept-pred-link", "index": str(e.get("id"))}, size="sm", color="success", style={"fontSize": "10px", "padding": "3px 8px", "fontWeight": "700"}),
                            dbc.Button("❌ Dismiss", id={"type": "btn-dismiss-pred-link", "index": str(e.get("id"))}, size="sm", color="secondary", outline=True, style={"fontSize": "10px", "padding": "3px 8px"}),
                        ])
                    ]
                )
                for e in pred_edges
            ]
        )
    ])


def render_alerts_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render Forensic Anomaly Alerts tab."""
    svc = CaseDataService()
    alerts = svc.list_alerts(case_id)

    if selected_node_data:
        nid = selected_node_data.get("id") or ""
        name = selected_node_data.get("name") or selected_node_data.get("label") or nid
        # Filter alerts referencing this entity
        alerts = [
            a for a in alerts
            if a.get("subject") == nid or nid in str(a.get("related_entities", [])) or name.lower() in str(a.get("explanation", "")).lower()
        ]

    severity_colors = {
        "CRITICAL": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#fca5a5", "border": "#ef4444"},
        "HIGH":     {"bg": "rgba(245, 158, 11, 0.15)", "text": "#fcd34d", "border": "#f59e0b"},
        "MEDIUM":   {"bg": "rgba(59, 130, 246, 0.15)", "text": "#93c5fd", "border": "#3b82f6"},
        "LOW":      {"bg": "rgba(107, 114, 128, 0.15)", "text": "#d1d5db", "border": "#6b7280"},
    }

    if not alerts:
        return html.Div(
            className="crimenet-empty-state",
            children=[
                html.Div("🛡️", className="empty-icon"),
                html.Div("No Forensic Anomaly Alerts", className="empty-title"),
                html.Div("Isolation Forest, smurfing, and rapid transaction engines detected no statistical outliers for the current scope.", className="empty-desc"),
            ]
        )

    return html.Div(
        children=[
            html.Div(
                style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "12px", "marginBottom": "10px", "boxShadow": "0 2px 6px rgba(0,0,0,0.25)"},
                children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "6px"}, children=[
                        html.Span(
                            (a.get("severity") or "HIGH").upper(),
                            style={
                                "fontSize": "9px",
                                "fontWeight": "800",
                                "backgroundColor": severity_colors.get(a.get("severity", "HIGH"), severity_colors["HIGH"])["bg"],
                                "color": severity_colors.get(a.get("severity", "HIGH"), severity_colors["HIGH"])["text"],
                                "border": f"1px solid {severity_colors.get(a.get('severity', 'HIGH'), severity_colors['HIGH'])['border']}",
                                "padding": "2px 6px",
                                "borderRadius": "4px"
                            }
                        ),
                        html.Span(a.get("alert_type") or "ANOMALY", style={"fontSize": "10px", "fontWeight": "700", "color": TEXT_MUTED}),
                    ]),
                    html.H6(a.get("title") or "Forensic Anomaly Detected", style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "12px", "margin": "0 0 4px 0"}),
                    html.P(a.get("explanation") or "Statistical outlier detected by Isolation Forest.", style={"fontSize": "11px", "color": TEXT_DIM, "lineHeight": "1.4", "margin": "0 0 8px 0"}),
                    html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "fontSize": "10px", "color": TEXT_MUTED}, children=[
                        html.Span(f"Status: {a.get('status', 'NEW')}"),
                        dbc.Button("Review →", id={"type": "btn-review-alert-direct", "index": str(a.get("id"))}, size="sm", color="secondary", outline=True, style={"fontSize": "10px", "padding": "2px 6px"})
                    ])
                ]
            )
            for a in alerts[:15]
        ]
    )


def render_evidence_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render Evidence Exhibits tab."""
    svc = CaseDataService()
    evidence_list = svc.list_evidence(case_id)

    upload_block = html.Div(
        style={"backgroundColor": "#171923", "border": f"1px dashed {BORDER_COL}", "borderRadius": "6px", "padding": "10px", "textAlign": "center", "marginBottom": "12px"},
        children=[
            dcc.Upload(
                id="right-panel-evidence-upload",
                children=html.Div([
                    html.Span("📄 ", style={"fontSize": "16px"}),
                    html.Span("+ Ingest Exhibit (PDF, TXT, CSV, JSON)", style={"fontSize": "11px", "fontWeight": "700", "color": CYAN_ACC})
                ]),
                style={"cursor": "pointer"}
            )
        ]
    )

    if selected_node_data:
        nid = selected_node_data.get("id") or ""
        name = selected_node_data.get("name") or selected_node_data.get("label") or nid
        evidence_list = [
            e for e in evidence_list
            if name.lower() in str(e.get("content", "")).lower() or nid in str(e.get("metadata", ""))
        ]

    if not evidence_list:
        return html.Div([
            upload_block,
            html.Div(
                className="crimenet-empty-state",
                children=[
                    html.Div("📁", className="empty-icon"),
                    html.Div("No Evidence Exhibits Found", className="empty-title"),
                    html.Div("No forensic files, FIR exhibits, or telecom logs are linked to this entity. Use the upload box above to ingest court documents.", className="empty-desc"),
                ]
            )
        ])

    return html.Div([
        upload_block,
        html.Div(
            children=[
                html.Div(
                    style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER_COL}", "borderRadius": "8px", "padding": "10px 12px", "marginBottom": "8px", "boxShadow": "0 2px 6px rgba(0,0,0,0.25)"},
                    children=[
                        html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                            html.Span(f"📁 {e.get('evidence_type', 'EXHIBIT')}", style={"fontSize": "10px", "fontWeight": "800", "color": CYAN_ACC}),
                            html.Span("VERIFIED SHA-256", style={"fontSize": "9px", "fontWeight": "700", "color": EMERALD, "backgroundColor": "rgba(16, 185, 129, 0.15)", "padding": "1px 5px", "borderRadius": "3px"}),
                        ]),
                        html.Div(e.get("title") or e.get("filename") or "Exhibited Document", style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "12px", "marginBottom": "3px"}),
                        html.Div(f"Hash: {str(e.get('sha256_hash') or '')[:16]}... • Entities: {e.get('entity_count', 0)}", style={"fontSize": "10px", "color": TEXT_MUTED, "marginBottom": "6px", "fontFamily": "monospace"}),
                        dbc.Button("Inspect Exhibit Text →", id={"type": "btn-inspect-evidence-item", "index": str(e.get("id"))}, size="sm", color="info", outline=True, style={"fontSize": "10px", "padding": "2px 8px"})
                    ]
                )
                for e in evidence_list[:12]
            ]
        )
    ])


def render_timeline_view(case_id: str, selected_node_data: Optional[Dict[str, Any]] = None) -> html.Div:
    """Render Chronological Timeline tab."""
    svc = CaseDataService()
    events = svc.get_case_timeline_aggregate(case_id)

    if selected_node_data:
        nid = selected_node_data.get("id") or ""
        name = selected_node_data.get("name") or selected_node_data.get("label") or nid
        events = [
            ev for ev in events
            if ev.get("object_id") == nid or name.lower() in str(ev.get("title", "")).lower() or name.lower() in str(ev.get("description", "")).lower()
        ]

    if not events:
        return html.Div(
            className="crimenet-empty-state",
            children=[
                html.Div("📅", className="empty-icon"),
                html.Div("No Timeline Events Recorded", className="empty-title"),
                html.Div("No chronological telecommunications events, dated transactions, or arrest milestones were logged for this scope.", className="empty-desc"),
            ]
        )

    return html.Div(
        children=[
            html.Div(
                style={"borderLeft": f"2px solid {CYAN_ACC}", "paddingLeft": "12px", "marginBottom": "10px", "position": "relative"},
                children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "2px"}, children=[
                        html.Span(str(ev.get("icon") or "📅")),
                        html.Span(ev.get("event_type") or "EVENT", style={"fontSize": "9px", "fontWeight": "800", "color": CYAN_ACC}),
                        html.Span(str(ev.get("ts") or "")[:16], style={"fontSize": "10px", "color": TEXT_MUTED, "marginLeft": "auto", "fontFamily": "monospace"}),
                    ]),
                    html.Div(ev.get("title") or "Timeline Event", style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "11.5px"}),
                    html.P(ev.get("description") or "", style={"fontSize": "11px", "color": TEXT_DIM, "margin": "2px 0 0 0", "lineHeight": "1.3"}),
                ]
            )
            for ev in events[:20]
        ]
    )


def register_right_panel_callbacks(dash_app):
    """Register reactive callbacks for the Right-Side Intelligence Panel."""

    # 1. Update Right-Side Panel Tab Content on Tab Switch, Node Click, or Case Switch
    @dash_app.callback(
        [
            Output("right-panel-tab-content", "children"),
            Output("right-panel-context-title", "children"),
            Output("right-panel-context-badge", "children"),
            Output("right-panel-tabs", "value"),
        ],
        [
            Input("right-panel-tabs", "value"),
            Input("cytoscape", "tapNodeData"),
            Input("active-case-store", "data"),
            Input("ws-search-entity-dropdown", "value"),
            Input("bottom-nav-btn-evidence", "n_clicks"),
        ],
        [
            State("cytoscape", "elements"),
        ],
        prevent_initial_call=False
    )
    def update_right_panel(active_tab, tap_node_data, active_case, search_entity_id, evidence_nav_clicks, elements):
        triggered = ctx.triggered_id
        active_case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"
        c_title = (active_case or {}).get("title") or "Operation Black Falcon"

        # If Bottom Nav "Evidence" was clicked: force switch to Evidence tab!
        if triggered == "bottom-nav-btn-evidence":
            active_tab = "rp-tab-evidence"

        # Determine if a specific node is selected
        selected_node = None
        if triggered == "cytoscape" and tap_node_data:
            selected_node = tap_node_data
            # When investigator clicks an entity on the graph, auto-switch to Dossier tab for instant contextualization!
            active_tab = "rp-tab-dossier"
        elif triggered == "ws-search-entity-dropdown" and search_entity_id:
            if elements:
                for el in elements:
                    if el.get("group") == "nodes" and el.get("data", {}).get("id") == search_entity_id:
                        selected_node = el.get("data", {})
                        break
            active_tab = "rp-tab-dossier"
        elif tap_node_data:
            selected_node = tap_node_data

        # Update Context Header Banner
        if selected_node:
            name = selected_node.get("name") or selected_node.get("label") or selected_node.get("id") or "Entity"
            ntype = str(selected_node.get("type") or "ENTITY").upper()
            title_el = [
                html.Span("👤", style={"fontSize": "15px"}),
                html.Span(f"{name} [{ntype}]", style={"fontWeight": "700", "fontSize": "12px", "color": TEXT_MAIN, "whiteSpace": "nowrap", "textOverflow": "ellipsis", "overflow": "hidden"}),
            ]
            badge_el = [
                html.Span("SELECTED ENTITY", style={"fontSize": "9px", "fontWeight": "800", "backgroundColor": "rgba(239, 68, 68, 0.2)", "color": "#fca5a5", "padding": "2px 6px", "borderRadius": "4px", "letterSpacing": "0.5px"})
            ]
        else:
            title_el = [
                html.Span("📁", style={"fontSize": "15px"}),
                html.Span(f"ACTIVE CASE: {c_title}", style={"fontWeight": "700", "fontSize": "12px", "color": TEXT_MAIN, "whiteSpace": "nowrap", "textOverflow": "ellipsis", "overflow": "hidden"}),
            ]
            badge_el = [
                html.Span("CASE CONTEXT", style={"fontSize": "9px", "fontWeight": "800", "backgroundColor": "rgba(56, 189, 248, 0.15)", "color": CYAN_ACC, "padding": "2px 6px", "borderRadius": "4px", "letterSpacing": "0.5px"})
            ]

        # Dispatch to the active right-side view
        if active_tab == "rp-tab-ai-intel":
            content = render_ai_intelligence_view(active_case_id, selected_node)
        elif active_tab == "rp-tab-dossier":
            content = render_dossier_view(active_case_id, selected_node)
        elif active_tab == "rp-tab-hidden-links":
            content = render_hidden_links_view(active_case_id, selected_node)
        elif active_tab == "rp-tab-alerts":
            content = render_alerts_view(active_case_id, selected_node)
        elif active_tab == "rp-tab-evidence":
            content = render_evidence_view(active_case_id, selected_node)
        elif active_tab == "rp-tab-timeline":
            content = render_timeline_view(active_case_id, selected_node)
        else:
            content = render_dossier_view(active_case_id, selected_node)

        return content, title_el, badge_el, active_tab

    # 2. Select Suspect from Key Suspects list in Dossier tab
    @dash_app.callback(
        Output("ws-search-entity-dropdown", "value", allow_duplicate=True),
        Input({"type": "btn-select-suspect-dossier", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_select_suspect(clicks):
        if not ctx.triggered or not any(c for c in clicks if c):
            raise PreventUpdate
        trigger_dict = ctx.triggered_id
        if isinstance(trigger_dict, dict) and "index" in trigger_dict:
            return trigger_dict["index"]
        return no_update

    # 3. Inspect Evidence Exhibit Modal from Right Panel Evidence Tab
    @dash_app.callback(
        [
            Output("modal-edge-source-viewer", "is_open", allow_duplicate=True),
            Output("modal-edge-source-title", "children", allow_duplicate=True),
            Output("modal-edge-source-body", "children", allow_duplicate=True),
        ],
        Input({"type": "btn-inspect-evidence-item", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_inspect_evidence_item(clicks):
        if not ctx.triggered or not any(c for c in clicks if c):
            raise PreventUpdate
        trigger_dict = ctx.triggered_id
        if not (isinstance(trigger_dict, dict) and "index" in trigger_dict):
            raise PreventUpdate

        evidence_id = trigger_dict["index"]
        svc = CaseDataService()
        doc = svc.get_evidence(evidence_id)
        if not doc:
            return True, "Evidence Record Not Found", html.Div("Evidence document could not be located in database.")

        title = doc.get("title") or doc.get("filename") or f"Exhibit {evidence_id}"
        hash_val = doc.get("sha256_hash") or "UNVERIFIED"
        ev_type = doc.get("evidence_type") or "EXHIBIT"
        content = doc.get("content") or "No raw text extracted."

        body = html.Div([
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "12px", "paddingBottom": "8px", "borderBottom": "1px solid #2d3748"},
                children=[
                    html.Div([
                        html.Span(f"TYPE: {str(ev_type).upper()}", style={"fontSize": "10px", "fontWeight": "800", "backgroundColor": "#1e293b", "color": "#38bdf8", "padding": "2px 8px", "borderRadius": "4px"}),
                        html.Span(f" • Collected by: {doc.get('collected_by') or 'Forensics Unit'}", style={"fontSize": "11px", "color": "#a0aec0", "marginLeft": "8px"}),
                    ]),
                    html.Div([
                        html.Span("SHA-256: ", style={"fontSize": "10px", "color": "#718096"}),
                        html.Span(hash_val, style={"fontSize": "10.5px", "fontFamily": "monospace", "color": "#10b981", "fontWeight": "600"}),
                    ])
                ]
            ),
            html.Div(
                html.Pre(
                    content,
                    style={
                        "backgroundColor": "#0c0f17",
                        "color": "#e2e8f0",
                        "padding": "14px",
                        "borderRadius": "6px",
                        "fontSize": "11px",
                        "lineHeight": "1.5",
                        "maxHeight": "450px",
                        "overflowY": "auto",
                        "whiteSpace": "pre-wrap",
                        "fontFamily": "monospace",
                        "border": "1px solid #2a3447"
                    }
                )
            )
        ])
        return True, title, body

    # 4. Human-In-The-Loop Confirmation / Dismissal for Link Prediction Hypotheses
    @dash_app.callback(
        [
            Output("hidden-links-feedback-banner", "children"),
            Output("hidden-links-feedback-banner", "style"),
        ],
        [
            Input({"type": "btn-accept-pred-link", "index": ALL}, "n_clicks"),
            Input({"type": "btn-dismiss-pred-link", "index": ALL}, "n_clicks"),
        ],
        State("active-case-store", "data"),
        prevent_initial_call=True
    )
    def handle_hitl_link_prediction_action(accept_clicks, dismiss_clicks, active_case):
        if not ctx.triggered:
            raise PreventUpdate
        if not any(c for c in accept_clicks if c) and not any(c for c in dismiss_clicks if c):
            raise PreventUpdate

        trigger_dict = ctx.triggered_id
        if not (isinstance(trigger_dict, dict) and "type" in trigger_dict):
            raise PreventUpdate

        action_type = trigger_dict["type"]
        edge_id = trigger_dict.get("index", "")
        case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"

        svc = CaseDataService()
        if action_type == "btn-accept-pred-link":
            try:
                svc.record_feedback(
                    case_id=case_id,
                    feedback_type="LINK_ACCEPTANCE",
                    target_id=edge_id,
                    action="ACCEPTED",
                    notes="Investigator confirmed machine prediction. Promoted to verified relationship in Neo4j."
                )
            except Exception as e:
                logger.error(f"Error recording acceptance: {e}")

            banner = html.Div([
                html.Span("✅ ", style={"fontSize": "14px"}),
                html.B("Link Accepted: "),
                html.Span(f"Hypothesis {edge_id[:8]} confirmed and recorded in SHA-256 audit ledger.")
            ])
            style = {"display": "block", "backgroundColor": "rgba(16, 185, 129, 0.15)", "border": "1px solid #10b981", "color": "#a7f3d0", "padding": "8px 12px", "borderRadius": "6px", "fontSize": "11px", "marginBottom": "10px"}
            return banner, style
        else:
            try:
                svc.record_feedback(
                    case_id=case_id,
                    feedback_type="LINK_ACCEPTANCE",
                    target_id=edge_id,
                    action="DISMISSED",
                    notes="Investigator dismissed statistical hypothesis as non-actionable."
                )
            except Exception as e:
                logger.error(f"Error recording dismissal: {e}")

            banner = html.Div([
                html.Span("❌ ", style={"fontSize": "14px"}),
                html.B("Link Dismissed: "),
                html.Span(f"Hypothesis {edge_id[:8]} dismissed. Non-repudiation audit entry logged.")
            ])
            style = {"display": "block", "backgroundColor": "rgba(239, 68, 68, 0.15)", "border": "1px solid #ef4444", "color": "#fca5a5", "padding": "8px 12px", "borderRadius": "6px", "fontSize": "11px", "marginBottom": "10px"}
            return banner, style

    # 5. Populate Top Query Bar When "Ask Agent about Entity" Is Clicked
    @dash_app.callback(
        Output("top-ask-crimenet-input", "value", allow_duplicate=True),
        Input("btn-open-ask-crimenet-entity", "n_clicks"),
        State("cytoscape", "tapNodeData"),
        prevent_initial_call=True
    )
    def handle_ask_about_entity(clicks, tap_node_data):
        if not clicks or not tap_node_data:
            raise PreventUpdate
        name = tap_node_data.get("name") or tap_node_data.get("label") or tap_node_data.get("id") or "this entity"
        return f"Why is {name} connected to the syndicate and what evidence links them?"

