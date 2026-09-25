"""CrimeNet Investigation Actions & Human-in-the-Loop (HITL) Workflow System.

Provides interactive operational action workflows inspired by target LEA systems:
  - Create Lookout Request (LOC / Border & Airport Intercept)
  - Request Account Freeze (Section 102 CrPC / PMLA / FIU Banking Injunction)
  - Mark for Review (Internal Supervisory Priority Flag)
  - Escalate Case (Senior Command / Central Agency ED/CBI Transfer)
  - Technical Surveillance Request (Section 5(2) Telegraph Act CDR / Intercept)
  - Subpoena / Production Notice (Section 91 CrPC Bank / Telco Notice)

LEGAL & SAFETY GUARDRAIL:
-------------------------
These are INTERNAL PROTOTYPE WORKFLOWS and do NOT dispatch real external enforcement
or banking commands. Human oversight, legal context, and judicial warrants are mandatory.
Actions are stored in the database with court-admissible append-oriented audit trails.

Stored Attributes:
  - action_type         (LOOKOUT_REQUEST, ACCOUNT_FREEZE_REQUEST, ...)
  - case_id             (foreign key to cases)
  - target_entity       (name, identifier, account, phone)
  - target_entity_type  (PERSON, BANK_ACCOUNT, ORGANIZATION, ...)
  - reason              (strictly required factual & legal grounds)
  - created_at          (timestamp)
  - status              (PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED)
  - related_evidence    (exhibit or document reference)
  - audit_id            (link to court-admissible audit_logs table)

Public API:
-----------
build_actions_workflow_modal() -> html.Div
build_actions_workflow_panel(case_id: str) -> html.Div
render_actions_list(actions: List[Dict[str, Any]], case_id: str = "") -> html.Div
register_actions_workflow_callbacks(dash_app) -> None
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from storage.case_data_service import CaseDataService

logger = logging.getLogger("CrimeNet.ActionWorkflows")

# ---------------------------------------------------------------------------
# Constants & Styling Config
# ---------------------------------------------------------------------------

_ACTION_META: Dict[str, Dict[str, str]] = {
    "LOOKOUT_REQUEST": {
        "label": "Lookout Request (LOC)",
        "icon": "🚨",
        "color": "#e53e3e",
        "description": "Border & immigration checkpost alert for flight-risk intercept.",
    },
    "ACCOUNT_FREEZE_REQUEST": {
        "label": "Request Account Freeze",
        "icon": "💳",
        "color": "#38a169",
        "description": "Section 102 CrPC / FIU debit injunction against suspected mule accounts.",
    },
    "MARK_FOR_REVIEW": {
        "label": "Mark for Priority Review",
        "icon": "🔍",
        "color": "#d69e2e",
        "description": "Internal supervisory flag for anomalous entities or transactions.",
    },
    "ESCALATE_CASE": {
        "label": "Escalate Case to Command",
        "icon": "⬆️",
        "color": "#805ad5",
        "description": "Inter-agency or senior command escalation (ED, CBI, Special Cell).",
    },
    "SURVEILLANCE_REQUEST": {
        "label": "Technical Surveillance Request",
        "icon": "📡",
        "color": "#3182ce",
        "description": "Section 5(2) Indian Telegraph Act CDR and communication authorization.",
    },
    "SUBPOENA_REQUEST": {
        "label": "Section 91 CrPC Notice",
        "icon": "📄",
        "color": "#2c7a7b",
        "description": "Formal production summons for banking ledgers or subscriber records.",
    },
}

_STATUS_CONFIG: Dict[str, Dict[str, str]] = {
    "PENDING_APPROVAL": {"badge": "warning",   "label": "⏳ PENDING APPROVAL", "color": "#d69e2e"},
    "APPROVED":         {"badge": "success",   "label": "✅ APPROVED",         "color": "#38a169"},
    "COMPLETED":        {"badge": "info",      "label": "🏁 COMPLETED",        "color": "#3182ce"},
    "REJECTED":         {"badge": "danger",    "label": "❌ REJECTED",         "color": "#e53e3e"},
    "DISMISSED":        {"badge": "secondary", "label": "🗑️ DISMISSED",        "color": "#718096"},
}

_PRESETS = {
    "loc": {
        "type": "LOOKOUT_REQUEST",
        "target": "Vikram Malhotra",
        "target_type": "PERSON",
        "evidence": "EX-2026-004 CDR Call Records & Intercept Log",
        "reason": "Suspect holds active international passport; intercepted communications indicate imminent flight to Dubai/Singapore ahead of impending charges under PMLA/IPC. Immediate port/airport intercept requested.",
    },
    "freeze": {
        "type": "ACCOUNT_FREEZE_REQUEST",
        "target": "Mule Account 33190 (HDFC Bank)",
        "target_type": "BANK_ACCOUNT",
        "evidence": "Bank_Ledger_2026.csv & FIU Suspicious Transaction Report (STR)",
        "reason": "Rapid structural dispersal of 45,00,000 INR within 180 seconds across 6 offshore shell entities; designated as primary layering conduit in hawala chain. Section 102 CrPC debit freeze requested.",
    },
    "review": {
        "type": "MARK_FOR_REVIEW",
        "target": "Falcon Global Trading LLC (Shell Corp)",
        "target_type": "ORGANIZATION",
        "evidence": "ROC Registrar Filings & Physical Site Verification Report",
        "reason": "Registered to shared residential address in Bandra West; zero commercial operations detected despite 22 Crore INR transaction throughput. Priority supervisory review flagged.",
    },
    "escalate": {
        "type": "ESCALATE_CASE",
        "target": "Black Falcon Multi-Jurisdictional Hawala Network",
        "target_type": "CASE_MODULE",
        "evidence": "Comprehensive Forensic FIR & Multi-Hop Ledger Analysis",
        "reason": "Fund flow tracing demonstrates cross-border layering exceeding 50 Crore INR involving shell entities in UAE and Mauritius. Escalating to Central Financial Intelligence Bureau & Enforcement Directorate.",
    },
}


# ---------------------------------------------------------------------------
# UI Builders
# ---------------------------------------------------------------------------

def _build_safeguard_alert() -> dbc.Alert:
    """Prominent legal disclaimer regarding internal prototype workflows."""
    return dbc.Alert(
        [
            html.Div(
                style={"display": "flex", "alignItems": "flex-start", "gap": "10px"},
                children=[
                    html.Span("⚖️", style={"fontSize": "22px"}),
                    html.Div([
                        html.B("INTERNAL PROTOTYPE WORKFLOW — STRICT HUMAN-IN-THE-LOOP CONTROL: ", style={"fontSize": "11px", "color": "#fbd38d"}),
                        html.Span(
                            "Actions created here are internal investigative decision-support records. "
                            "No automated API calls or external enforcement commands are dispatched to immigration, "
                            "police, or banking gateways. Operational execution requires formal judicial warrants, "
                            "statutory compliance, and senior supervisory sign-off.",
                            style={"fontSize": "11px", "color": "#cbd5e0"}
                        ),
                    ])
                ]
            )
        ],
        color="warning",
        style={"backgroundColor": "#74421020", "borderColor": "#d69e2e", "padding": "10px 14px", "marginBottom": "14px"}
    )


def _build_action_form() -> html.Div:
    """Build the interactive action creation form with quick presets."""
    return html.Div([
        # One-Click Presets Strip
        html.Div(
            style={
                "backgroundColor": "#141923", "border": "1px solid #2d3748",
                "borderRadius": "6px", "padding": "10px 12px", "marginBottom": "14px"
            },
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "6px"},
                    children=[
                        html.Span("⚡ ONE-CLICK ACTION PRESETS:", style={"fontSize": "10px", "fontWeight": "800", "color": "#63b3ed", "letterSpacing": "0.5px"}),
                        html.Span("(Auto-fill standard LEA grounds & evidentiary context)", style={"fontSize": "10px", "color": "#718096", "fontStyle": "italic"}),
                    ]
                ),
                html.Div(
                    style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                    children=[
                        dbc.Button("🚨 Lookout Request (LOC)", id="btn-preset-loc", size="sm", color="danger", outline=True, style={"fontSize": "11px", "padding": "3px 10px", "fontWeight": "600"}),
                        dbc.Button("💳 Request Account Freeze", id="btn-preset-freeze", size="sm", color="success", outline=True, style={"fontSize": "11px", "padding": "3px 10px", "fontWeight": "600"}),
                        dbc.Button("🔍 Mark for Priority Review", id="btn-preset-review", size="sm", color="warning", outline=True, style={"fontSize": "11px", "padding": "3px 10px", "fontWeight": "600"}),
                        dbc.Button("⬆️ Escalate Case to Command", id="btn-preset-escalate", size="sm", color="primary", outline=True, style={"fontSize": "11px", "padding": "3px 10px", "fontWeight": "600"}),
                    ]
                )
            ]
        ),

        # Form Fields Grid
        dbc.Row([
            dbc.Col([
                dbc.Label("Action Type *", style={"fontSize": "11px", "fontWeight": "700", "color": "#cbd5e0"}),
                dcc.Dropdown(
                    id="action-type-select",
                    options=[
                        {"label": f"{v['icon']} {v['label']}", "value": k}
                        for k, v in _ACTION_META.items()
                    ],
                    value="LOOKOUT_REQUEST",
                    clearable=False,
                    className="dashboard-dropdown",
                    style={"fontSize": "11px"}
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Target Entity / Subject *", style={"fontSize": "11px", "fontWeight": "700", "color": "#cbd5e0"}),
                dbc.Input(
                    id="action-target-input",
                    placeholder="e.g. Vikram Malhotra, Mule Account 33190, Falcon Global Trading LLC",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Target Entity Type", style={"fontSize": "11px", "fontWeight": "700", "color": "#cbd5e0"}),
                dcc.Dropdown(
                    id="action-target-type-select",
                    options=[
                        {"label": "👤 Person (Suspect / Mule)", "value": "PERSON"},
                        {"label": "💳 Bank Account (Financial Conduit)", "value": "BANK_ACCOUNT"},
                        {"label": "🏢 Organization (Shell Company)", "value": "ORGANIZATION"},
                        {"label": "📱 Phone (Communication Node)", "value": "PHONE"},
                        {"label": "🚗 Vehicle (Logistics Asset)", "value": "VEHICLE"},
                        {"label": "💼 Case Module / Syndicate", "value": "CASE_MODULE"},
                    ],
                    value="PERSON",
                    clearable=False,
                    className="dashboard-dropdown",
                    style={"fontSize": "11px"}
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Related Evidence / Source Exhibit", style={"fontSize": "11px", "fontWeight": "700", "color": "#cbd5e0"}),
                dbc.Input(
                    id="action-evidence-ref-input",
                    placeholder="e.g. Bank_Ledger_2026.csv, EX-2026-004 CDR, STR-44/2024",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Investigator Badge / Identity", style={"fontSize": "11px", "fontWeight": "700", "color": "#cbd5e0"}),
                dbc.Input(
                    id="action-investigator-input",
                    value="Inspector Sandeep Verma (Cyber Crime Cell)",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=4),
        ], className="mb-3"),

        # Evidentiary Grounds & Reason (Strictly Required)
        dbc.Row([
            dbc.Col([
                dbc.Label("Evidentiary Grounds & Legal Context * (Strictly Required)", style={"fontSize": "11px", "fontWeight": "700", "color": "#fc8181"}),
                dbc.Textarea(
                    id="action-reason-input",
                    placeholder="Document factual grounds, transaction velocity, call patterns, or flight indicators justifying this operational action. Submissions without substantive legal justification cannot be submitted.",
                    rows=3,
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=12)
        ], className="mb-3"),

        # Submit Button
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "12px"},
            children=[
                dbc.Button("⚡ Submit Investigation Action Request", id="btn-submit-action", color="danger", style={"fontSize": "12px", "fontWeight": "700"}),
                html.Span("Recorded directly into immutable audit trail.", style={"color": "#718096", "fontSize": "11px", "fontStyle": "italic"}),
            ]
        ),
        html.Div(id="action-submit-feedback", style={"marginTop": "10px", "fontSize": "12px"})
    ])


def _build_hitl_tab() -> html.Div:
    """Build Human-in-the-Loop verified correction submission tab."""
    return html.Div([
        dbc.Alert(
            "🛡️ HUMAN-IN-THE-LOOP CONTROL: Verified human corrections NEVER overwrite the original AI prediction. "
            "Both the original AI model claim and the investigator's corroborated correction are preserved in the knowledge graph with full audit provenance.",
            color="info",
            style={"backgroundColor": "#2b6cb020", "borderColor": "#3182ce", "fontSize": "11px", "marginBottom": "14px"}
        ),
        dbc.Row([
            dbc.Col([
                dbc.Label("Target Entity / Relationship ID *", style={"fontSize": "11px", "fontWeight": "700"}),
                dbc.Input(
                    id="hitl-target-input",
                    placeholder="e.g. Vikram Malhotra, phone_9820199887, or Rahul-Amit link",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Supporting Source / Document *", style={"fontSize": "11px", "fontWeight": "700"}),
                dbc.Input(
                    id="hitl-source-input",
                    placeholder="e.g. FIR_102, KYC_Audit_2026.pdf, CAF_REG_99",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Original AI Statement / Inferred Claim", style={"fontSize": "11px", "fontWeight": "700"}),
                dbc.Textarea(
                    id="hitl-original-ai-input",
                    placeholder="e.g. AI claimed Rahul is subscriber to Phone 98201.",
                    rows=2,
                    style={"backgroundColor": "#0d1117", "color": "#feb2b2", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=12)
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Human-Verified Correct Value *", style={"fontSize": "11px", "fontWeight": "700"}),
                dbc.Textarea(
                    id="hitl-corrected-input",
                    placeholder="e.g. Phone subscriber is verified as Amit Verma via Customer Acquisition Form and biometric KYC.",
                    rows=2,
                    style={"backgroundColor": "#0d1117", "color": "#9ae6b4", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=12)
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Reason / Corroboration Grounds *", style={"fontSize": "11px", "fontWeight": "700"}),
                dbc.Input(
                    id="hitl-reason-input",
                    placeholder="e.g. Physical KYC verification conducted at Telco nodal office by Sub-Inspector.",
                    style={"backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "11px"}
                )
            ], width=12)
        ], className="mb-3"),

        dbc.Button("Submit Verified Correction (HITL)", id="btn-submit-hitl-correction", color="success", style={"fontSize": "12px", "fontWeight": "700"}),
        html.Div(id="hitl-submit-feedback", style={"marginTop": "10px", "fontSize": "12px"})
    ])


def render_actions_list(actions: List[Dict[str, Any]], case_id: str = "") -> html.Div:
    """Render interactive registry of investigation action workflows with supervisory lifecycle controls."""
    if not actions:
        return html.Div(
            style={"padding": "32px", "textAlign": "center", "color": "#718096"},
            children=[
                html.Div("⚡", style={"fontSize": "36px", "marginBottom": "8px"}),
                html.Div("No investigation action workflows registered for this case yet.", style={"fontSize": "13px", "fontWeight": "600", "color": "#a0aec0"}),
                html.Div("Use the 'Create Action Request' tab or one-click presets to generate internal Lookout Requests, Account Freezes, or Case Escalations.", style={"fontSize": "11px", "marginTop": "4px"}),
            ]
        )

    # Top KPI Strip
    cnt_total   = len(actions)
    cnt_pending = sum(1 for a in actions if a.get("status") == "PENDING_APPROVAL")
    cnt_apprv   = sum(1 for a in actions if a.get("status") == "APPROVED")
    cnt_comp    = sum(1 for a in actions if a.get("status") == "COMPLETED")
    cnt_rej     = sum(1 for a in actions if a.get("status") in ("REJECTED", "DISMISSED"))

    kpi_bar = html.Div(
        style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "14px"},
        children=[
            html.Div(style={"backgroundColor": "#1a202c", "border": "1px solid #4a5568", "borderRadius": "4px", "padding": "4px 10px"},
                     children=[html.Span("Total Actions: ", style={"color": "#a0aec0", "fontSize": "11px"}), html.B(str(cnt_total), style={"color": "#f7fafc", "fontSize": "12px"})]),
            html.Div(style={"backgroundColor": "#74421025", "border": "1px solid #d69e2e", "borderRadius": "4px", "padding": "4px 10px"},
                     children=[html.Span("Pending Approval: ", style={"color": "#fbd38d", "fontSize": "11px"}), html.B(str(cnt_pending), style={"color": "#ecc94b", "fontSize": "12px"})]),
            html.Div(style={"backgroundColor": "#22543d25", "border": "1px solid #38a169", "borderRadius": "4px", "padding": "4px 10px"},
                     children=[html.Span("Approved: ", style={"color": "#9ae6b4", "fontSize": "11px"}), html.B(str(cnt_apprv), style={"color": "#48bb78", "fontSize": "12px"})]),
            html.Div(style={"backgroundColor": "#2b6cb025", "border": "1px solid #3182ce", "borderRadius": "4px", "padding": "4px 10px"},
                     children=[html.Span("Completed: ", style={"color": "#90cdf4", "fontSize": "11px"}), html.B(str(cnt_comp), style={"color": "#63b3ed", "fontSize": "12px"})]),
            html.Div(style={"backgroundColor": "#742a2a25", "border": "1px solid #e53e3e", "borderRadius": "4px", "padding": "4px 10px"},
                     children=[html.Span("Rejected: ", style={"color": "#feb2b2", "fontSize": "11px"}), html.B(str(cnt_rej), style={"color": "#fc8181", "fontSize": "12px"})]),
        ]
    )

    cards = []
    for act in actions:
        act_id  = act.get("id") or ""
        atype   = act.get("action_type") or "LOOKOUT_REQUEST"
        meta    = _ACTION_META.get(atype, {"label": atype, "icon": "⚡", "color": "#805ad5"})
        st      = act.get("status") or "PENDING_APPROVAL"
        scfg    = _STATUS_CONFIG.get(st, {"badge": "secondary", "label": st, "color": "#718096"})
        target  = act.get("target_entity") or "Unknown Target"
        ttype   = act.get("target_entity_type") or "ENTITY"
        reason  = act.get("reason") or "No reason provided."
        ev_ref  = act.get("related_evidence") or "Direct Case Review"
        inv_id  = act.get("investigator_id") or "investigator"
        audit_id= act.get("audit_id") or "—"
        ts_str  = str(act.get("created_at") or "")[:16]
        notes   = act.get("notes")

        # Supervisory Decision Controls
        action_controls = None
        if st == "PENDING_APPROVAL":
            action_controls = html.Div(
                style={"marginTop": "10px", "paddingTop": "8px", "borderTop": "1px solid #2d3748", "display": "flex", "alignItems": "center", "gap": "8px", "flexWrap": "wrap"},
                children=[
                    html.Span("Supervisory Decision:", style={"fontSize": "10px", "fontWeight": "700", "color": "#a0aec0"}),
                    dbc.Input(
                        id={"type": "action-review-notes", "index": act_id},
                        placeholder="Optional supervisory remarks / warrant ref...",
                        style={"flex": "1", "minWidth": "160px", "backgroundColor": "#0d1117", "color": "#f7fafc", "borderColor": "#4a5568", "fontSize": "10px", "padding": "3px 8px"}
                    ),
                    dbc.Button(
                        "✅ Approve Request",
                        id={"type": "btn-action-approve", "index": act_id},
                        color="success", size="sm",
                        style={"fontSize": "10px", "fontWeight": "700", "padding": "3px 8px"}
                    ),
                    dbc.Button(
                        "❌ Reject",
                        id={"type": "btn-action-reject", "index": act_id},
                        color="danger", size="sm", outline=True,
                        style={"fontSize": "10px", "fontWeight": "700", "padding": "3px 8px"}
                    ),
                ]
            )
        elif st == "APPROVED":
            action_controls = html.Div(
                style={"marginTop": "8px", "paddingTop": "6px", "borderTop": "1px solid #2d3748", "display": "flex", "alignItems": "center", "gap": "8px"},
                children=[
                    html.Span("Execution Status: Warrants active.", style={"fontSize": "10px", "color": "#68d391", "fontStyle": "italic"}),
                    dbc.Button(
                        "🏁 Mark Completed (Served / Executed)",
                        id={"type": "btn-action-complete", "index": act_id},
                        color="info", size="sm", outline=True,
                        style={"fontSize": "10px", "padding": "2px 8px", "marginLeft": "auto"}
                    ),
                ]
            )

        cards.append(html.Div(
            style={
                "backgroundColor": "#141923",
                "border": f"1px solid {meta['color']}55",
                "borderRadius": "6px",
                "padding": "12px 14px",
                "marginBottom": "10px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.2)"
            },
            children=[
                # Top Header Row
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "6px"},
                    children=[
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "6px"},
                            children=[
                                html.Span(meta["icon"], style={"fontSize": "14px"}),
                                html.B(meta["label"].upper(), style={"color": meta["color"], "fontSize": "12px", "letterSpacing": "0.4px"}),
                            ]
                        ),
                        dbc.Badge(scfg["label"], color=scfg["badge"], style={"fontSize": "9px", "fontWeight": "700"})
                    ]
                ),
                # Target & Evidence Row
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px", "fontSize": "11px", "flexWrap": "wrap"},
                    children=[
                        html.Span([
                            html.Span("Target: ", style={"color": "#718096"}),
                            html.B(target, style={"color": "#f7fafc"}),
                            dbc.Badge(ttype, color="secondary", style={"fontSize": "9px", "marginLeft": "4px"}),
                        ]),
                        html.Span([
                            html.Span("Evidence: ", style={"color": "#718096"}),
                            html.Span(ev_ref, style={"color": "#90cdf4", "fontFamily": "Consolas, monospace"}),
                        ]),
                    ]
                ),
                # Evidentiary Grounds Box
                html.Div(
                    reason,
                    style={
                        "backgroundColor": "#0d1117", "borderLeft": f"3px solid {meta['color']}",
                        "borderRadius": "4px", "padding": "8px 10px", "fontSize": "11px",
                        "color": "#e2e8f0", "lineHeight": "1.4", "marginBottom": "6px"
                    }
                ),
                # Reviewer Notes (if present)
                html.Div(
                    f"Supervisory Note: {notes}",
                    style={"fontSize": "10px", "color": "#f6e05e", "fontStyle": "italic", "marginBottom": "4px"}
                ) if notes else None,
                # Footer Audit Trail Info
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "fontSize": "10px", "color": "#718096"},
                    children=[
                        html.Span(f"Filed by {inv_id} · {ts_str}"),
                        html.Span(f"Audit Ref: {audit_id[:8]}", style={"fontFamily": "Consolas, monospace", "color": "#a0aec0"}),
                    ]
                ),
                # Action Buttons
                action_controls,
            ]
        ))

    return html.Div([kpi_bar, html.Div(cards)])


def build_actions_workflow_panel(case_id: str) -> html.Div:
    """Build the standalone panel for Investigation Actions & HITL (embeddable in dashboard or modal)."""
    svc = CaseDataService()
    try:
        actions = svc.list_investigation_actions(case_id=case_id)
    except Exception as exc:
        logger.warning("Failed to list actions for case %s: %s", case_id, exc)
        actions = []

    return html.Div(
        id="investigation-actions-panel",
        children=[
            _build_safeguard_alert(),
            dbc.Tabs([
                dbc.Tab(
                    label="⚡ Create Action Request",
                    tab_id="tab-act-create",
                    style={"fontSize": "12px"},
                    children=[html.Div(style={"paddingTop": "14px"}, children=[_build_action_form()])]
                ),
                dbc.Tab(
                    label=f"📋 Action Registry ({len(actions)})",
                    tab_id="tab-act-registry",
                    style={"fontSize": "12px"},
                    children=[
                        html.Div(
                            id="active-case-actions-list",
                            style={"paddingTop": "14px"},
                            children=render_actions_list(actions, case_id)
                        )
                    ]
                ),
                dbc.Tab(
                    label="✏️ Human-in-the-Loop Corrections",
                    tab_id="tab-act-hitl",
                    style={"fontSize": "12px"},
                    children=[html.Div(style={"paddingTop": "14px"}, children=[_build_hitl_tab()])]
                ),
            ])
        ]
    )


def build_actions_workflow_modal() -> html.Div:
    """Build the modal dialog for Investigation Actions accessible from the secondary navigation bar."""
    return html.Div([
        dbc.Modal(
            id="modal-investigation-actions",
            is_open=False,
            size="xl",
            scrollable=True,
            style={"maxWidth": "90vw"},
            children=[
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span("⚡", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5("Investigation Action Workflows & Human Verification", style={"margin": "0", "fontWeight": "800", "color": "#f7fafc"}),
                                html.Span("Internal decision-support prototype workflows for law enforcement agencies.", style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    close_button=True,
                    style={"backgroundColor": "#161b26", "borderBottom": "1px solid #2d3748"}
                ),
                dbc.ModalBody(
                    id="modal-investigation-actions-body",
                    style={"backgroundColor": "#0d1117", "color": "#cbd5e0", "padding": "20px"},
                    children=[build_actions_workflow_panel("case-synthetic-black-falcon-001")]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close Action Workflows", id="btn-close-investigation-actions", color="secondary", size="sm"),
                    style={"backgroundColor": "#161b26", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def register_actions_workflow_callbacks(dash_app):
    """Register all interactive action submission, preset populating, and supervisory review callbacks."""

    # 1. Toggle Actions Modal
    @dash_app.callback(
        [
            Output("modal-investigation-actions", "is_open"),
            Output("modal-investigation-actions-body", "children"),
        ],
        [
            Input("ws-sec-nav-actions", "n_clicks"),
            Input("btn-close-investigation-actions", "n_clicks"),
        ],
        [
            State("modal-investigation-actions", "is_open"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def toggle_actions_modal(n_open, n_close, is_open, active_case):
        if not ctx.triggered:
            return no_update, no_update
        tid = ctx.triggered[0]["prop_id"].split(".")[0]

        if tid == "ws-sec-nav-actions" and not is_open:
            case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"
            panel = build_actions_workflow_panel(case_id)
            return True, panel
        elif tid == "btn-close-investigation-actions":
            return False, no_update

        return not is_open, no_update

    # 2. Quick Action Presets (Auto-fill form)
    @dash_app.callback(
        [
            Output("action-type-select", "value"),
            Output("action-target-input", "value"),
            Output("action-target-type-select", "value"),
            Output("action-evidence-ref-input", "value"),
            Output("action-reason-input", "value"),
        ],
        [
            Input("btn-preset-loc", "n_clicks"),
            Input("btn-preset-freeze", "n_clicks"),
            Input("btn-preset-review", "n_clicks"),
            Input("btn-preset-escalate", "n_clicks"),
        ],
        prevent_initial_call=True
    )
    def populate_action_presets(n_loc, n_freeze, n_review, n_escalate):
        if not ctx.triggered:
            raise PreventUpdate
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]

        preset_key = {
            "btn-preset-loc": "loc",
            "btn-preset-freeze": "freeze",
            "btn-preset-review": "review",
            "btn-preset-escalate": "escalate",
        }.get(btn_id)

        if not preset_key or preset_key not in _PRESETS:
            raise PreventUpdate

        p = _PRESETS[preset_key]
        return p["type"], p["target"], p["target_type"], p["evidence"], p["reason"]

    # 3. Submit Action Request
    @dash_app.callback(
        [
            Output("action-submit-feedback", "children"),
            Output("active-case-actions-list", "children"),
        ],
        Input("btn-submit-action", "n_clicks"),
        [
            State("action-type-select", "value"),
            State("action-target-input", "value"),
            State("action-target-type-select", "value"),
            State("action-reason-input", "value"),
            State("action-evidence-ref-input", "value"),
            State("action-investigator-input", "value"),
            State("active-case-store", "data"),
            State("dossier-active-case-id-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_submit_action(n_clicks, act_type, target, target_type, reason, evidence_ref, investigator, active_case, dossier_case):
        if not n_clicks:
            raise PreventUpdate
        if not target or not target.strip():
            return dbc.Alert("Target entity / subject is strictly required.", color="danger", style={"fontSize": "11px"}), no_update
        if not reason or len(reason.strip()) < 10:
            return dbc.Alert("A substantive factual reason / evidentiary grounds is strictly required (minimum 10 characters).", color="danger", style={"fontSize": "11px"}), no_update

        service = CaseDataService()
        case_id = (active_case or {}).get("case_id") or dossier_case or "case-synthetic-black-falcon-001"

        try:
            act_id = service.create_investigation_action(
                case_id=case_id,
                action_type=act_type,
                target_entity=target.strip(),
                target_entity_type=target_type or "PERSON",
                reason=reason.strip(),
                related_evidence=evidence_ref.strip() if evidence_ref else None,
                investigator_id=investigator.strip() if investigator else "investigator"
            )
            actions = service.list_investigation_actions(case_id=case_id)
            fb = dbc.Alert(
                f"✅ Created {act_type} request for '{target}'. Registered with court-admissible audit log (Ref: {act_id[:8]}).",
                color="success",
                style={"fontSize": "11px"}
            )
            return fb, render_actions_list(actions, case_id)
        except Exception as exc:
            logger.error("Failed to submit action: %s", exc)
            return dbc.Alert(f"Error submitting action: {exc}", color="danger", style={"fontSize": "11px"}), no_update

    # 4. Supervisory Decision Lifecycle (Approve, Reject, Complete)
    @dash_app.callback(
        Output("active-case-actions-list", "children", allow_duplicate=True),
        [
            Input({"type": "btn-action-approve", "index": ALL}, "n_clicks"),
            Input({"type": "btn-action-reject", "index": ALL}, "n_clicks"),
            Input({"type": "btn-action-complete", "index": ALL}, "n_clicks"),
        ],
        [
            State({"type": "action-review-notes", "index": ALL}, "value"),
            State("active-case-store", "data"),
            State("dossier-active-case-id-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_supervisory_decision(n_apprv_list, n_rej_list, n_comp_list, notes_list, active_case, dossier_case):
        if not ctx.triggered:
            raise PreventUpdate

        triggered_prop = ctx.triggered[0]["prop_id"]
        try:
            prop_data = json.loads(triggered_prop.split(".")[0])
            act_id = prop_data.get("index")
            btn_type = prop_data.get("type")
        except Exception:
            raise PreventUpdate

        target_status = {
            "btn-action-approve": "APPROVED",
            "btn-action-reject": "REJECTED",
            "btn-action-complete": "COMPLETED",
        }.get(btn_type)

        if not target_status or not act_id:
            raise PreventUpdate

        service = CaseDataService()
        case_id = (active_case or {}).get("case_id") or dossier_case or "case-synthetic-black-falcon-001"

        notes = "Supervisory decision registered via CrimeNet DSS."
        service.update_investigation_action_status(
            action_id=act_id,
            status=target_status,
            notes=notes,
            investigator_id="supervisor-001"
        )
        actions = service.list_investigation_actions(case_id=case_id)
        return render_actions_list(actions, case_id)

    # 5. Submit HITL Correction
    @dash_app.callback(
        Output("hitl-submit-feedback", "children"),
        Input("btn-submit-hitl-correction", "n_clicks"),
        [
            State("hitl-target-input", "value"),
            State("hitl-original-ai-input", "value"),
            State("hitl-corrected-input", "value"),
            State("hitl-reason-input", "value"),
            State("hitl-source-input", "value"),
            State("active-case-store", "data"),
            State("dossier-active-case-id-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_submit_hitl_correction(n_clicks, target, original_ai, corrected, reason, source_ref, active_case, dossier_case):
        if not n_clicks:
            raise PreventUpdate
        if not target or not target.strip():
            return dbc.Alert("Target ID / Claim is required.", color="danger", style={"fontSize": "11px"})
        if not corrected or not corrected.strip():
            return dbc.Alert("Human corrected value is required.", color="danger", style={"fontSize": "11px"})
        if not reason or not reason.strip():
            return dbc.Alert("Reason / corroboration grounds are required.", color="danger", style={"fontSize": "11px"})

        service = CaseDataService()
        case_id = (active_case or {}).get("case_id") or dossier_case or "case-synthetic-black-falcon-001"

        try:
            fb_id = service.record_human_correction(
                case_id=case_id,
                target_id=target.strip(),
                original_ai_result=original_ai.strip() if original_ai else "AI claim",
                corrected_value=corrected.strip(),
                reason=reason.strip(),
                source_ref=source_ref.strip() if source_ref else None,
                investigator_id="lead_investigator"
            )
            return dbc.Alert(
                f"✅ Verified correction recorded (Ref: {fb_id[:8]}). Both original AI result and verified correction are preserved with court-admissible audit tracking.",
                color="success",
                style={"fontSize": "11px"}
            )
        except Exception as exc:
            return dbc.Alert(f"Error recording correction: {exc}", color="danger", style={"fontSize": "11px"})
