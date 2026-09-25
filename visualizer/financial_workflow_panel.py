"""CrimeNet Financial Investigation Workflow Panel.

Provides a dedicated forensic money-flow investigation modal and workspace:
- Account nodes inspection (Bank Accounts, UPI VPAs, Corporate, Mule, Offshore)
- Transaction relationships with exact amounts, currencies, timestamps, transaction IDs
- Multi-hop fund flow tracing (Forward dispersal, Backward funding sources)
- Canonical Person ➔ UPI ➔ Mule ➔ Company ➔ Offshore flow stepper
- Automated anomaly detection badges (Rapid Layering, Mule Intake, Offshore Freezone Flight)
- Live Cytoscape graph canvas money-flow highlighting
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import dash
from dash import dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from analyzer.financial_investigation import (
    FinancialInvestigationService,
    FinancialPath,
    FinancialTransaction,
    FinancialAccountSummary,
)

logger = logging.getLogger("CrimeNet.FinancialWorkflowPanel")

# ── Color Tokens ─────────────────────────────────────────────────────────────
BG_DEEP   = "#0f1117"
BG_CARD   = "#1a202c"
BG_PANEL  = "#2d3748"
TEXT_PRI  = "#f7fafc"
TEXT_MUT  = "#a0aec0"
TEXT_DIM  = "#718096"
BDR_DIM   = "#4a5568"
ACCENT_GREEN = "#10b981"
ACCENT_RED   = "#ef4444"
ACCENT_GOLD  = "#f59e0b"
ACCENT_BLUE  = "#3182ce"


def _account_role_badge(node_id: str, node_name: str, node_type: str) -> html.Span:
    """Return a styled chip depending on the entity's financial role."""
    nid = node_id.lower()
    nname = node_name.lower()

    if "mule" in nid or "sbi" in nid or "mule" in nname:
        return html.Span("🚨 MULE ACCOUNT", style={
            "backgroundColor": "rgba(239,68,68,0.2)", "color": "#f87171",
            "border": "1px solid #ef4444", "padding": "2px 8px", "borderRadius": "4px",
            "fontSize": "10px", "fontWeight": "800"
        })
    elif "freezone" in nname or "fze" in nname or "shell" in nid or "offshore" in nid:
        return html.Span("🌐 OFFSHORE ENTITY", style={
            "backgroundColor": "rgba(245,158,11,0.2)", "color": "#fbbf24",
            "border": "1px solid #f59e0b", "padding": "2px 8px", "borderRadius": "4px",
            "fontSize": "10px", "fontWeight": "800"
        })
    elif "upi" in nid or "okhdfc" in nname or "vpa" in nname:
        return html.Span("⚡ UPI VPA", style={
            "backgroundColor": "rgba(16,185,129,0.2)", "color": "#34d399",
            "border": "1px solid #10b981", "padding": "2px 8px", "borderRadius": "4px",
            "fontSize": "10px", "fontWeight": "800"
        })
    elif "org" in nid or "company" in nname or "exports" in nname or node_type == "ORGANIZATION":
        return html.Span("🏢 COMPANY / FRONT", style={
            "backgroundColor": "rgba(49,130,206,0.2)", "color": "#63b3ed",
            "border": "1px solid #3182ce", "padding": "2px 8px", "borderRadius": "4px",
            "fontSize": "10px", "fontWeight": "800"
        })
    elif node_type == "PERSON":
        return html.Span("👤 PERSON", style={
            "backgroundColor": "rgba(159,122,234,0.2)", "color": "#b794f4",
            "border": "1px solid #9f7aea", "padding": "2px 8px", "borderRadius": "4px",
            "fontSize": "10px", "fontWeight": "800"
        })
    return html.Span("💳 BANK ACCOUNT", style={
        "backgroundColor": "rgba(74,85,104,0.3)", "color": "#cbd5e0",
        "border": "1px solid #4a5568", "padding": "2px 8px", "borderRadius": "4px",
        "fontSize": "10px", "fontWeight": "700"
    })


def render_transaction_hop_card(step_num: int, txn: FinancialTransaction) -> html.Div:
    """Render a detailed forensic card for a single hop in the money flow."""
    anom_badges = [
        html.Span(
            f"🚨 {a}",
            style={
                "backgroundColor": "rgba(239,68,68,0.15)", "color": "#fca5a5",
                "border": "1px solid #ef4444", "padding": "2px 6px",
                "borderRadius": "3px", "fontSize": "9px", "fontWeight": "700"
            }
        )
        for a in txn.anomaly_indicators
    ]

    return html.Div(
        style={
            "backgroundColor": BG_CARD,
            "border": "1px solid #2d3748",
            "borderLeft": "4px solid #10b981" if not txn.anomaly_indicators else "4px solid #ef4444",
            "borderRadius": "6px",
            "padding": "12px 14px",
            "marginBottom": "10px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.3)"
        },
        children=[
            # Top row: Step number, Transaction Type, Amount, Currency
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "8px"}, children=[
                        html.Span(f"HOP {step_num}", style={
                            "backgroundColor": "#2d3748", "color": TEXT_PRI, "padding": "2px 8px",
                            "borderRadius": "4px", "fontWeight": "800", "fontSize": "11px"
                        }),
                        html.B(txn.relationship_type, style={"color": "#63b3ed", "fontSize": "12px", "letterSpacing": "0.5px"}),
                    ]),
                    html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "6px"}, children=[
                        html.Span(txn.formatted_amount(), style={
                            "color": "#10b981" if txn.currency == "INR" else "#f59e0b",
                            "fontSize": "16px", "fontWeight": "900", "fontFamily": "monospace"
                        }),
                        html.Span(f"({txn.currency})", style={"color": TEXT_MUT, "fontSize": "10px", "fontWeight": "700"})
                    ])
                ]
            ),

            # Middle row: Flow directional path (Source -> Target)
            html.Div(
                style={
                    "backgroundColor": BG_PANEL, "borderRadius": "5px", "padding": "8px 10px",
                    "display": "flex", "alignItems": "center", "justifyContent": "space-between",
                    "marginBottom": "8px", "flexWrap": "wrap", "gap": "6px"
                },
                children=[
                    # Source
                    html.Div([
                        _account_role_badge(txn.source_id, txn.source_name, txn.source_type),
                        html.B(txn.source_name, style={"color": TEXT_PRI, "fontSize": "12px", "display": "block", "marginTop": "2px"}),
                        html.Span(f"Account: {txn.source_account}", style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": "monospace"})
                    ]),
                    # Arrow
                    html.Div([
                        html.Span("➔ ➔ ➔", style={"color": "#10b981", "fontSize": "14px", "fontWeight": "900"}),
                    ]),
                    # Target
                    html.Div([
                        _account_role_badge(txn.target_id, txn.target_name, txn.target_type),
                        html.B(txn.target_name, style={"color": TEXT_PRI, "fontSize": "12px", "display": "block", "marginTop": "2px"}),
                        html.Span(f"Account: {txn.destination_account}", style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": "monospace"})
                    ])
                ]
            ),

            # Parameters row: TxID, Timestamp, Evidence Source
            html.Div(
                style={"display": "flex", "gap": "14px", "fontSize": "11px", "color": TEXT_MUT, "flexWrap": "wrap"},
                children=[
                    html.Div([html.B("TxID: ", style={"color": TEXT_DIM}), html.Span(txn.transaction_id, style={"color": TEXT_PRI, "fontFamily": "monospace"})]),
                    html.Div([html.B("Timestamp: ", style={"color": TEXT_DIM}), html.Span(txn.timestamp or f"{txn.date} {txn.time}", style={"color": TEXT_PRI})]),
                    html.Div([html.B("Exhibit Source: ", style={"color": TEXT_DIM}), html.Span(txn.evidence_source, style={"color": "#90cdf4"})]),
                    html.Div([html.B("Modality: ", style={"color": TEXT_DIM}), html.Span(f"🟢 {txn.modality}", style={"color": "#68d391", "fontWeight": "700"})]),
                ]
            ),

            # Anomaly badges
            html.Div(
                style={"marginTop": "8px", "display": "flex", "gap": "6px", "flexWrap": "wrap"} if anom_badges else {"display": "none"},
                children=anom_badges
            )
        ]
    )


def build_financial_workflow_modal() -> html.Div:
    """Build the complete Financial Investigation Workflow Modal."""
    return html.Div([
        dcc.Store(id="active-financial-path-store", data=None),
        dcc.Store(id="financial-paths-cache-store", data=None),

        dbc.Modal(
            id="modal-financial-workflow",
            is_open=False,
            size="xl",
            scrollable=True,
            children=[
                # ── Header ──────────────────────────────────────────────────
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            html.Span("💰", style={"fontSize": "26px"}),
                            html.Div([
                                html.H4("DEDICATED FINANCIAL INVESTIGATION WORKFLOW",
                                        style={"margin": "0", "fontWeight": "900", "color": "#f7fafc", "letterSpacing": "0.5px"}),
                                html.Span("Multi-Hop Fund Flow Tracing · Account Provenance · Automated Anomaly Detection · Graph Highlighting",
                                          style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderBottom": "2px solid #10b981"}
                ),

                # ── Body ────────────────────────────────────────────────────
                dbc.ModalBody(
                    style={"backgroundColor": BG_DEEP, "color": "#cbd5e0", "padding": "20px"},
                    children=[
                        # 1. Top Metrics Strip
                        html.Div(
                            id="fin-metrics-strip",
                            style={"display": "flex", "gap": "10px", "marginBottom": "16px", "flexWrap": "wrap"},
                            children=[
                                html.Div(
                                    style={"flex": "1", "minWidth": "160px", "backgroundColor": BG_CARD, "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "10px"},
                                    children=[
                                        html.Div("TOTAL FLOW VOLUME", style={"fontSize": "9px", "color": TEXT_MUT, "fontWeight": "800"}),
                                        html.Div(id="fin-metric-volume", children="₹52.5 Lakh / $30K", style={"fontSize": "17px", "fontWeight": "900", "color": "#10b981", "marginTop": "4px"}),
                                    ]
                                ),
                                html.Div(
                                    style={"flex": "1", "minWidth": "160px", "backgroundColor": BG_CARD, "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "10px"},
                                    children=[
                                        html.Div("ACCOUNT NODES", style={"fontSize": "9px", "color": TEXT_MUT, "fontWeight": "800"}),
                                        html.Div(id="fin-metric-accounts", children="4 Accounts · 1 UPI VPA", style={"fontSize": "15px", "fontWeight": "800", "color": "#63b3ed", "marginTop": "4px"}),
                                    ]
                                ),
                                html.Div(
                                    style={"flex": "1", "minWidth": "160px", "backgroundColor": BG_CARD, "border": "1px solid #ef4444", "borderRadius": "6px", "padding": "10px"},
                                    children=[
                                        html.Div("FLAGGED MULE ACCOUNTS", style={"fontSize": "9px", "color": "#f87171", "fontWeight": "800"}),
                                        html.Div(id="fin-metric-mules", children="1 Mule (SBI-ACC-8812)", style={"fontSize": "15px", "fontWeight": "800", "color": "#ef4444", "marginTop": "4px"}),
                                    ]
                                ),
                                html.Div(
                                    style={"flex": "1", "minWidth": "160px", "backgroundColor": BG_CARD, "border": "1px solid #f59e0b", "borderRadius": "6px", "padding": "10px"},
                                    children=[
                                        html.Div("OFFSHORE FLIGHT", style={"fontSize": "9px", "color": "#fbbf24", "fontWeight": "800"}),
                                        html.Div(id="fin-metric-offshore", children="1 UAE Freezone Wire", style={"fontSize": "15px", "fontWeight": "800", "color": "#f59e0b", "marginTop": "4px"}),
                                    ]
                                ),
                            ]
                        ),

                        # 2. One-Click Investigation Presets
                        html.Div(
                            style={"backgroundColor": BG_CARD, "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "12px 14px", "marginBottom": "16px"},
                            children=[
                                html.Div("⭐ CANONICAL INVESTIGATION SCENARIOS (ONE-CLICK TRACING):",
                                         style={"fontSize": "10px", "color": TEXT_MUT, "fontWeight": "800", "marginBottom": "8px"}),
                                html.Div(
                                    style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                                    children=[
                                        dbc.Button(
                                            "⭐ Canonical 5-Tier Flow: Person ➔ UPI ➔ Mule ➔ Company ➔ Offshore",
                                            id="btn-fin-preset-canonical",
                                            size="sm",
                                            color="success",
                                            style={"fontSize": "11px", "fontWeight": "700", "padding": "4px 12px"}
                                        ),
                                        dbc.Button(
                                            "🚨 Mule Layering: SBI-ACC-8812 Tracing",
                                            id="btn-fin-preset-mule",
                                            size="sm",
                                            color="danger",
                                            outline=True,
                                            style={"fontSize": "11px", "padding": "4px 12px"}
                                        ),
                                        dbc.Button(
                                            "🌐 Offshore Wire: Omega Exports ➔ Shell Corp Global",
                                            id="btn-fin-preset-offshore",
                                            size="sm",
                                            color="warning",
                                            outline=True,
                                            style={"fontSize": "11px", "padding": "4px 12px"}
                                        ),
                                    ]
                                )
                            ]
                        ),

                        # 3. Interactive Multi-Hop Tracing Controls
                        html.Div(
                            style={"backgroundColor": BG_CARD, "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "14px", "marginBottom": "16px"},
                            children=[
                                html.Div("🔍 MULTI-HOP MONEY FLOW TRACER CONTROLS:",
                                         style={"fontSize": "10px", "color": TEXT_MUT, "fontWeight": "800", "marginBottom": "10px"}),
                                html.Div(
                                    style={"display": "flex", "gap": "10px", "alignItems": "flex-end", "flexWrap": "wrap"},
                                    children=[
                                        html.Div(
                                            style={"flex": "1.3", "minWidth": "200px"},
                                            children=[
                                                html.Label("Origin Entity / Account:", style={"fontSize": "10px", "color": TEXT_MUT, "display": "block", "marginBottom": "3px"}),
                                                dcc.Dropdown(
                                                    id="fin-trace-source-dropdown",
                                                    placeholder="Select starting entity/account...",
                                                    options=[],
                                                    value="person_rahul_sharma",
                                                    clearable=False,
                                                    style={"color": "#1a202c", "fontSize": "12px"}
                                                )
                                            ]
                                        ),
                                        html.Div(
                                            style={"flex": "1.3", "minWidth": "200px"},
                                            children=[
                                                html.Label("Target Destination (Optional):", style={"fontSize": "10px", "color": TEXT_MUT, "display": "block", "marginBottom": "3px"}),
                                                dcc.Dropdown(
                                                    id="fin-trace-target-dropdown",
                                                    placeholder="All downstream endpoints...",
                                                    options=[],
                                                    value="org_shell_corp_global",
                                                    clearable=True,
                                                    style={"color": "#1a202c", "fontSize": "12px"}
                                                )
                                            ]
                                        ),
                                        html.Div(
                                            style={"flex": "1", "minWidth": "140px"},
                                            children=[
                                                html.Label("Flow Direction:", style={"fontSize": "10px", "color": TEXT_MUT, "display": "block", "marginBottom": "3px"}),
                                                dcc.Dropdown(
                                                    id="fin-trace-direction-dropdown",
                                                    options=[
                                                        {"label": "➔ Forward (Dispersal)", "value": "forward"},
                                                        {"label": "⬅ Backward (Funding Source)", "value": "backward"},
                                                    ],
                                                    value="forward",
                                                    clearable=False,
                                                    style={"color": "#1a202c", "fontSize": "12px"}
                                                )
                                            ]
                                        ),
                                        html.Div(
                                            style={"flex": "0.8", "minWidth": "110px"},
                                            children=[
                                                html.Label("Max Hops:", style={"fontSize": "10px", "color": TEXT_MUT, "display": "block", "marginBottom": "3px"}),
                                                dcc.Dropdown(
                                                    id="fin-trace-hops-dropdown",
                                                    options=[{"label": f"{i} Hops", "value": i} for i in range(1, 7)],
                                                    value=5,
                                                    clearable=False,
                                                    style={"color": "#1a202c", "fontSize": "12px"}
                                                )
                                            ]
                                        ),
                                        dbc.Button(
                                            "⚡ Trace Flow",
                                            id="btn-fin-execute-trace",
                                            color="info",
                                            size="sm",
                                            style={"fontSize": "12px", "fontWeight": "800", "padding": "7px 16px"}
                                        )
                                    ]
                                )
                            ]
                        ),

                        # 4. Active Money Flow Path Banner & Action Controls
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px", "flexWrap": "wrap", "gap": "10px"},
                            children=[
                                html.Div([
                                    html.H5("Active Money-Flow Ledger & Path Stepper",
                                            style={"margin": "0", "fontWeight": "800", "color": TEXT_PRI, "fontSize": "15px"}),
                                    html.Span(id="fin-active-path-summary",
                                              children="Canonical Laundering Pipeline: Person ➔ UPI ➔ Mule ➔ Company ➔ Offshore",
                                              style={"fontSize": "11px", "color": "#10b981", "fontWeight": "600"})
                                ]),
                                html.Div(
                                    style={"display": "flex", "gap": "8px"},
                                    children=[
                                        dbc.Button(
                                            "⚡ Highlight Money Flow on Graph",
                                            id="btn-fin-highlight-graph",
                                            color="success",
                                            size="sm",
                                            style={"fontSize": "11px", "fontWeight": "800", "padding": "5px 14px", "boxShadow": "0 0 10px rgba(16,185,129,0.3)"}
                                        ),
                                        dbc.Button(
                                            "❌ Clear Graph Highlight",
                                            id="btn-fin-clear-graph",
                                            color="secondary",
                                            outline=True,
                                            size="sm",
                                            style={"fontSize": "11px", "padding": "5px 12px"}
                                        )
                                    ]
                                )
                            ]
                        ),

                        # 5. Sequential Transaction Stepper Cards
                        html.Div(
                            id="fin-flow-stepper-container",
                            style={"marginBottom": "20px"},
                            children=[
                                html.Div("Loading money-flow path...", style={"color": TEXT_MUT, "padding": "20px", "textAlign": "center"})
                            ]
                        ),

                        # 6. Forensic Anomaly & FIU Red Flags Card
                        html.Div(
                            id="fin-anomalies-card",
                            style={"backgroundColor": BG_CARD, "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "14px"},
                            children=[
                                html.Div("🚨 DETECTED FINANCIAL FORENSIC RED FLAGS:",
                                         style={"fontSize": "10px", "color": "#f87171", "fontWeight": "800", "marginBottom": "8px"}),
                                html.Div(id="fin-anomalies-container", children=[
                                    html.Div("• Rapid Velocity Layering: Funds routed from UPI to Mule to Commercial entity in under 24 hours.", style={"fontSize": "11px", "color": "#fca5a5"}),
                                    html.Div("• Nominal Mule Account: SBI-ACC-8812 held by Priya Patel acting as pass-through conduit for enterprise wire.", style={"fontSize": "11px", "color": "#fca5a5"}),
                                    html.Div("• Offshore Freezone Diversion: USD 30,000 transferred to Shell Corp Global FZE (UAE) without bill of entry.", style={"fontSize": "11px", "color": "#fca5a5"}),
                                ])
                            ]
                        )
                    ]
                ),

                # ── Footer ──────────────────────────────────────────────────
                dbc.ModalFooter(
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "width": "100%", "alignItems": "center"},
                        children=[
                            html.Span("Official Financial Exhibit Reference: FIU-IND STR-44/2024 (Primary Evidence)",
                                      style={"fontSize": "11px", "color": TEXT_MUT, "fontStyle": "italic"}),
                            dbc.Button("Close Financial Workflow", id="btn-close-financial-modal", color="secondary", size="sm")
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


def register_financial_workflow_callbacks(dash_app: dash.Dash) -> None:
    """Register callbacks for financial investigation workflow and graph highlighting."""

    # 1. Open/Close Modal
    @dash_app.callback(
        Output("modal-financial-workflow", "is_open"),
        [
            Input("ws-sec-nav-financial", "n_clicks"),
            Input("ws-btn-money-flow-toolbar", "n_clicks"),
            Input("btn-close-financial-modal", "n_clicks"),
        ],
        [State("modal-financial-workflow", "is_open")],
        prevent_initial_call=True
    )
    def toggle_financial_modal(n_sec, n_tool, n_close, is_open):
        triggered = ctx.triggered_id
        if triggered in ("ws-sec-nav-financial", "ws-btn-money-flow-toolbar"):
            return True
        if triggered == "btn-close-financial-modal":
            return False
        return is_open

    # 2. Populate Dropdown Options on Modal Open / Case Change
    @dash_app.callback(
        [
            Output("fin-trace-source-dropdown", "options"),
            Output("fin-trace-target-dropdown", "options"),
            Output("fin-metric-volume", "children"),
            Output("fin-metric-accounts", "children"),
            Output("fin-metric-mules", "children"),
            Output("fin-metric-offshore", "children"),
        ],
        [
            Input("modal-financial-workflow", "is_open"),
            Input("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def populate_financial_controls(is_open, active_case):
        if not is_open:
            return no_update, no_update, no_update, no_update, no_update, no_update

        case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"
        svc = FinancialInvestigationService()
        txns = svc.get_financial_transactions(case_id)
        accounts = svc.get_account_nodes(case_id)

        # Entity options
        options_set: Dict[str, str] = {}
        for t in txns:
            options_set[t.source_id] = f"{t.source_name} ({t.source_type})"
            options_set[t.target_id] = f"{t.target_name} ({t.target_type})"

        opts = [{"label": label, "value": val} for val, label in sorted(options_set.items(), key=lambda x: x[1])]

        # Metrics calculation
        total_inr = sum(t.amount_inr for t in txns)
        usd_txns = [t for t in txns if t.currency == "USD"]
        total_usd = sum(t.amount for t in usd_txns)
        vol_str = f"₹{total_inr / 100000:.1f} Lakh"
        if total_usd > 0:
            vol_str += f" / ${total_usd:,.0f} USD"

        acc_count = len(accounts)
        mule_count = len([a for a in accounts if a.is_mule])
        offshore_count = len([a for a in accounts if a.is_offshore])

        acc_str = f"{acc_count} Accounts · Tracked"
        mule_str = f"{mule_count} Mule (SBI-ACC-8812)" if mule_count else "0 Flagged"
        offshore_str = f"{offshore_count} Offshore Flight" if offshore_count else "0 Detected"

        return opts, opts, vol_str, acc_str, mule_str, offshore_str

    # 3. Handle Tracing and Presets Loading
    @dash_app.callback(
        [
            Output("active-financial-path-store", "data"),
            Output("fin-active-path-summary", "children"),
            Output("fin-flow-stepper-container", "children"),
            Output("fin-anomalies-container", "children"),
        ],
        [
            Input("modal-financial-workflow", "is_open"),
            Input("btn-fin-preset-canonical", "n_clicks"),
            Input("btn-fin-preset-mule", "n_clicks"),
            Input("btn-fin-preset-offshore", "n_clicks"),
            Input("btn-fin-execute-trace", "n_clicks"),
        ],
        [
            State("fin-trace-source-dropdown", "value"),
            State("fin-trace-target-dropdown", "value"),
            State("fin-trace-direction-dropdown", "value"),
            State("fin-trace-hops-dropdown", "value"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_financial_path_selection(
        is_open, n_canon, n_mule, n_off, n_exec,
        src_val, tgt_val, dir_val, hops_val, active_case
    ):
        triggered = ctx.triggered_id
        case_id = (active_case or {}).get("case_id") or "case-synthetic-black-falcon-001"
        svc = FinancialInvestigationService()

        # Handle Presets
        if triggered == "btn-fin-preset-canonical" or is_open:
            paths = svc.get_canonical_investigation_paths(case_id)
        elif triggered == "btn-fin-preset-mule":
            paths = svc.trace_money_flow(case_id, start_entity_id="account_sbi_8812", direction="forward", max_hops=4)
        elif triggered == "btn-fin-preset-offshore":
            paths = svc.trace_money_flow(case_id, start_entity_id="org_omega_exports", end_entity_id="org_shell_corp_global", max_hops=4)
        elif triggered == "btn-fin-execute-trace":
            start_id = src_val or "person_rahul_sharma"
            paths = svc.trace_money_flow(
                case_id=case_id,
                start_entity_id=start_id,
                end_entity_id=tgt_val if tgt_val else None,
                direction=dir_val or "forward",
                max_hops=int(hops_val or 5)
            )
        else:
            paths = svc.get_canonical_investigation_paths(case_id)

        if not paths:
            return None, "No connecting money-flow paths found for selected criteria.", html.Div("No transactions in selected corridor.", style={"padding": "20px", "color": TEXT_MUT}), html.Div("No anomalies detected.")

        active_path = paths[0]

        # Build cards
        cards = []
        for idx, t in enumerate(active_path.transactions, 1):
            cards.append(render_transaction_hop_card(idx, t))

        # Build anomalies list
        anom_divs = []
        if active_path.anomaly_indicators:
            for a in active_path.anomaly_indicators:
                anom_divs.append(html.Div(f"• {a}", style={"fontSize": "11px", "color": "#fca5a5", "marginBottom": "4px"}))
        else:
            anom_divs = [html.Div("No statutory anomalies flagged along this path.", style={"fontSize": "11px", "color": TEXT_MUT})]

        # Store serializable path dict
        path_dict = {
            "path_id": active_path.path_id,
            "node_ids": active_path.node_ids,
            "node_names": active_path.node_names,
            "node_types": active_path.node_types,
            "total_amount_inr": active_path.total_amount_inr,
            "formatted_amount": active_path.formatted_total_inr(),
            "hops": active_path.hops,
            "anomalies": active_path.anomaly_indicators,
            "summary": active_path.flow_summary,
            "transactions": [
                {
                    "source_id": t.source_id,
                    "target_id": t.target_id,
                    "amount": t.amount,
                    "currency": t.currency,
                    "formatted_amount": t.formatted_amount(),
                    "transaction_id": t.transaction_id,
                    "relationship_type": t.relationship_type,
                    "timestamp": t.timestamp
                }
                for t in active_path.transactions
            ]
        }

        return path_dict, active_path.flow_summary, html.Div(cards), html.Div(anom_divs)

    # 4. Highlight Money Flow on Graph Canvas
    @dash_app.callback(
        [
            Output("cytoscape", "elements", allow_duplicate=True),
            Output("workspace-analytics-summary", "children", allow_duplicate=True),
        ],
        [
            Input("btn-fin-highlight-graph", "n_clicks"),
            Input("btn-fin-clear-graph", "n_clicks"),
        ],
        [
            State("active-financial-path-store", "data"),
            State("cytoscape", "elements"),
        ],
        prevent_initial_call=True
    )
    def highlight_money_flow_on_graph(n_highlight, n_clear, path_data, current_elements):
        triggered = ctx.triggered_id
        if not current_elements:
            return no_update, no_update

        if triggered == "btn-fin-clear-graph":
            # Restore view
            clean_elements = []
            for el in current_elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d
                el_copy["classes"] = ""
                d.pop("money_label", None)
                clean_elements.append(el_copy)
            summary = html.Div("Money flow highlighting cleared. Graph restored to normal view.", style={"color": "#a0aec0", "padding": "4px 8px"})
            return clean_elements, summary

        if triggered == "btn-fin-highlight-graph" and path_data:
            path_nodes = set(path_data.get("node_ids", []))
            txns = path_data.get("transactions", [])
            edge_map: Dict[Tuple[str, str], str] = {
                (t["source_id"], t["target_id"]): t["formatted_amount"]
                for t in txns
            }

            highlighted_elements = []
            for el in current_elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "nodes":
                    nid = d.get("id")
                    if nid in path_nodes:
                        nname = str(d.get("name", "")).lower()
                        if "mule" in nid.lower() or "sbi" in nid.lower():
                            el_copy["classes"] = "crimenet-mule-node"
                        elif "freezone" in nname or "fze" in nname or "shell" in nid.lower():
                            el_copy["classes"] = "crimenet-offshore-node"
                        else:
                            el_copy["classes"] = "crimenet-money-node"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                elif el.get("group") == "edges":
                    src = d.get("source")
                    tgt = d.get("target")
                    if (src, tgt) in edge_map:
                        d["money_label"] = edge_map[(src, tgt)]
                        el_copy["classes"] = "crimenet-money-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                highlighted_elements.append(el_copy)

            path_summary = path_data.get("summary", "Money Flow Path")
            fmt_amt = path_data.get("formatted_amount", "")
            banner = html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "padding": "6px 10px",
                       "backgroundColor": "rgba(16,185,129,0.15)", "border": "1px solid #10b981", "borderRadius": "4px"},
                children=[
                    html.Span("💰 ACTIVE MONEY FLOW HIGHLIGHT:", style={"fontWeight": "800", "color": "#10b981", "fontSize": "11px"}),
                    html.Span(f"{path_summary} · Total Volume: {fmt_amt}", style={"color": TEXT_PRI, "fontSize": "11px"}),
                    dbc.Button("Clear Highlight", id="btn-fin-clear-graph-banner", size="sm", color="light", outline=True,
                               style={"fontSize": "10px", "padding": "1px 8px", "marginLeft": "auto"})
                ]
            )
            return highlighted_elements, banner

        return no_update, no_update
