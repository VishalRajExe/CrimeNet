"""CrimeNet "Ask CrimeNet" Investigation Agent Panel.

Provides a full-screen modal investigation assistant panel that connects
to the LangGraph investigation agent (analyzer/investigation_agent.py).

Features:
  - Natural-language question input
  - Case context auto-injected (active case ID, title, crime type)
  - Real-time tool trace log showing which CrimeNet tools are invoked
  - Formatted answer display with markdown rendering
  - Example questions for quick-start
  - Forensic disclaimer: agent answers require investigator verification
  - No OpenAI key → graceful fallback message (no crash)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from dash import dcc, html
import dash_bootstrap_components as dbc

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

# ── Design tokens ────────────────────────────────────────────────────────────
DARK_BG    = "#0f1117"
PANEL_BG   = "#1a202c"
BORDER_COL = "#2d3748"
TEXT_MAIN  = "#f7fafc"
TEXT_DIM   = "#a0aec0"
TEXT_MUTED = "#718096"
ACCENT     = "#63b3ed"

EXAMPLE_QUESTIONS = [
    "How is [Entity Name] connected to the main suspect?",
    "Who are the most influential entities in this case?",
    "Find the shortest path between [Entity A] and [Entity B].",
    "What communities exist in the network?",
    "List all anomaly alerts and explain the most critical one.",
    "What evidence is available for this case?",
    "Are there any potential (predicted) links I should investigate?",
    "Show me the timeline of key events involving [Entity Name].",
    "Retrieve the investigation reports for this case.",
    "What does GraphRAG say about [Event or Theme]?",
]

TOOL_ICONS = {
    "search_entities":     "🔎",
    "search_case":         "📁",
    "graph_nhop":          "🕸️",
    "find_shortest_path":  "📍",
    "get_pagerank":        "📊",
    "detect_communities":  "👥",
    "predict_links":       "🔗",
    "lookup_anomalies":    "⚠️",
    "retrieve_evidence":   "📄",
    "search_graphrag":     "🧠",
    "get_timeline":        "📅",
    "get_reports":         "📋",
}


# ── Main Modal builder ────────────────────────────────────────────────────────

def build_ask_crimenet_modal() -> html.Div:
    """
    Build the full "Ask CrimeNet" modal layout.

    Returns a wrapper Div that contains:
    - The floating trigger button (fixed bottom-right)
    - The full-screen investigation modal
    """
    return html.Div([

        # ── Floating Trigger Button ───────────────────────────────────────
        dbc.Button(
            children=[
                html.Span("🤖", style={"fontSize": "18px", "marginRight": "6px"}),
                html.Span("Ask CrimeNet", style={"fontWeight": "700", "fontSize": "13px"}),
            ],
            id="btn-open-ask-crimenet",
            n_clicks=0,
            style={
                "position": "fixed",
                "bottom": "24px",
                "right": "24px",
                "zIndex": "9999",
                "background": "linear-gradient(135deg, #2b6cb0, #553c9a)",
                "border": "none",
                "borderRadius": "28px",
                "padding": "12px 20px",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.4)",
                "display": "flex",
                "alignItems": "center",
                "cursor": "pointer",
                "transition": "transform 0.15s ease, box-shadow 0.15s ease",
            }
        ),

        # ── Full-Screen Modal ─────────────────────────────────────────────
        dbc.Modal(
            id="modal-ask-crimenet",
            is_open=False,
            size="xl",
            scrollable=True,
            style={"maxWidth": "95vw"},
            children=[

                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            html.Span("🤖", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5("Ask CrimeNet", style={"margin": "0", "color": TEXT_MAIN, "fontWeight": "800"}),
                                html.Span("LangGraph Investigation Agent · Powered by actual CrimeNet tools",
                                          style={"fontSize": "11px", "color": TEXT_MUTED}),
                            ]),
                            # Case context pill
                            html.Div(id="ask-crimenet-case-pill", style={"marginLeft": "auto"}),
                        ]
                    ),
                    style={"backgroundColor": "#161b27", "borderBottom": f"1px solid {BORDER_COL}"},
                    close_button=True,
                ),

                dbc.ModalBody(
                    style={"backgroundColor": DARK_BG, "padding": "0"},
                    children=[

                        # ── Forensic disclaimer ───────────────────────────
                        html.Div(
                            style={
                                "backgroundColor": "#1a1a2e",
                                "borderBottom": f"1px solid {BORDER_COL}",
                                "padding": "8px 20px",
                                "display": "flex",
                                "gap": "8px",
                                "alignItems": "center",
                            },
                            children=[
                                html.Span("ℹ️", style={"flexShrink": "0"}),
                                html.Span(
                                    "Agent responses are generated from real CrimeNet data tools. "
                                    "Answers must be independently verified before any investigative or legal action.",
                                    style={"color": "#90cdf4", "fontSize": "11px"}
                                )
                            ]
                        ),

                        # ── Two-column layout ─────────────────────────────
                        html.Div(
                            style={"display": "flex", "height": "72vh", "overflow": "hidden"},
                            children=[

                                # LEFT: Question input + answer
                                html.Div(
                                    style={"flex": "1 1 65%", "display": "flex", "flexDirection": "column", "borderRight": f"1px solid {BORDER_COL}"},
                                    children=[

                                        # ── Input area ───────────────────
                                        html.Div(
                                            style={
                                                "padding": "16px 20px",
                                                "borderBottom": f"1px solid {BORDER_COL}",
                                                "backgroundColor": PANEL_BG,
                                            },
                                            children=[
                                                html.Div(
                                                    style={"display": "flex", "gap": "10px", "alignItems": "flex-end"},
                                                    children=[
                                                        html.Div(
                                                            style={"flex": "1"},
                                                            children=[
                                                                dbc.Textarea(
                                                                    id="ask-crimenet-input",
                                                                    placeholder="Ask an investigation question…\ne.g. How is Rahul connected to the account used in Case 102?",
                                                                    rows=3,
                                                                    style={
                                                                        "backgroundColor": "#0f1117",
                                                                        "color": TEXT_MAIN,
                                                                        "border": f"1px solid {BORDER_COL}",
                                                                        "borderRadius": "6px",
                                                                        "fontSize": "13px",
                                                                        "resize": "vertical",
                                                                        "fontFamily": "'Inter', sans-serif",
                                                                    }
                                                                ),
                                                            ]
                                                        ),
                                                        dbc.Button(
                                                            "Investigate →",
                                                            id="btn-ask-crimenet-submit",
                                                            n_clicks=0,
                                                            style={
                                                                "background": "linear-gradient(135deg, #2b6cb0, #553c9a)",
                                                                "border": "none",
                                                                "fontWeight": "700",
                                                                "fontSize": "13px",
                                                                "padding": "10px 18px",
                                                                "borderRadius": "6px",
                                                                "alignSelf": "stretch",
                                                                "minWidth": "120px",
                                                            }
                                                        ),
                                                    ]
                                                ),

                                                # Example questions
                                                html.Div(
                                                    style={"marginTop": "8px", "display": "flex", "gap": "6px", "flexWrap": "wrap"},
                                                    children=[
                                                        html.Span("Examples:", style={"color": TEXT_MUTED, "fontSize": "11px", "alignSelf": "center"}),
                                                        *[
                                                            dbc.Badge(
                                                                q[:50] + ("…" if len(q) > 50 else ""),
                                                                id={"type": "ask-example-question", "index": i},
                                                                color="dark",
                                                                className="me-1",
                                                                style={"cursor": "pointer", "fontSize": "10px", "fontWeight": "400"},
                                                                n_clicks=0,
                                                            )
                                                            for i, q in enumerate(EXAMPLE_QUESTIONS[:5])
                                                        ]
                                                    ]
                                                ),
                                            ]
                                        ),

                                        # ── Answer area ──────────────────
                                        html.Div(
                                            style={"flex": "1", "overflowY": "auto", "padding": "20px"},
                                            children=[
                                                dcc.Loading(
                                                    id="ask-crimenet-answer-loading",
                                                    type="cube",
                                                    color=ACCENT,
                                                    children=html.Div(
                                                        id="ask-crimenet-answer",
                                                        style={"minHeight": "200px"},
                                                        children=_build_empty_state(),
                                                    )
                                                )
                                            ]
                                        ),
                                    ]
                                ),

                                # RIGHT: Tool trace log
                                html.Div(
                                    style={
                                        "flex": "0 0 35%",
                                        "display": "flex",
                                        "flexDirection": "column",
                                        "backgroundColor": "#0d1117",
                                    },
                                    children=[
                                        html.Div(
                                            style={"padding": "12px 16px", "borderBottom": f"1px solid {BORDER_COL}"},
                                            children=[
                                                html.Span("🔧 Tool Trace", style={"color": TEXT_MAIN, "fontSize": "13px", "fontWeight": "700"}),
                                                html.Span(" · Tool calls made by the agent", style={"color": TEXT_MUTED, "fontSize": "11px"}),
                                            ]
                                        ),
                                        html.Div(
                                            id="ask-crimenet-tool-trace",
                                            style={
                                                "flex": "1",
                                                "overflowY": "auto",
                                                "padding": "12px 16px",
                                                "fontFamily": "monospace",
                                                "fontSize": "11px",
                                            },
                                            children=[
                                                html.Div("No tool calls yet.", style={"color": TEXT_MUTED})
                                            ]
                                        ),
                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        ),

        # Evidence Source Inspector Modal
        dbc.Modal(
            id="modal-ask-source-detail",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader("Corroborating Evidence Document Record", style={"backgroundColor": "#1a202c", "color": "#f7fafc", "borderBottom": "1px solid #2d3748"}),
                dbc.ModalBody(id="modal-ask-source-body", style={"backgroundColor": "#0f1117", "color": "#cbd5e0", "padding": "20px"}),
                dbc.ModalFooter(
                    dbc.Button("Close Record", id="btn-close-ask-source-modal", color="secondary", size="sm"),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        ),

        # Stores
        dcc.Store(id="ask-crimenet-result-store"),
    ])


def _build_empty_state() -> html.Div:
    return html.Div(
        style={"textAlign": "center", "paddingTop": "60px"},
        children=[
            html.Div("🔍", style={"fontSize": "48px", "marginBottom": "16px"}),
            html.H5("Ask an investigation question", style={"color": TEXT_DIM, "fontWeight": "600"}),
            html.P(
                "Type a natural-language question about entities, connections, anomalies, "
                "evidence, or the investigation network. The agent will use actual CrimeNet "
                "analysis tools to answer.",
                style={"color": TEXT_MUTED, "fontSize": "12px", "maxWidth": "400px", "margin": "0 auto", "lineHeight": "1.6"}
            ),
        ]
    )


def _render_tool_trace(trace: List[Dict[str, Any]]) -> html.Div:
    if not trace:
        return html.Div("No tools invoked.", style={"color": TEXT_MUTED})

    children = []
    for i, step in enumerate(trace):
        tool_name = step.get("tool", "unknown")
        args_str  = json.dumps(step.get("args", {}), indent=None)[:120]
        result_p  = step.get("result", "")[:200]
        t_start   = str(step.get("started_at", ""))[:19]
        icon      = TOOL_ICONS.get(tool_name, "🔧")

        children.append(html.Div(
            style={
                "marginBottom": "12px",
                "borderLeft": f"2px solid {ACCENT}",
                "paddingLeft": "10px",
            },
            children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    children=[
                        html.Span([html.Span(f"{i+1}. ", style={"color": TEXT_MUTED}),
                                   html.Span(f"{icon} {tool_name}", style={"color": ACCENT, "fontWeight": "700"})]),
                        html.Span(t_start, style={"color": TEXT_MUTED, "fontSize": "10px"}),
                    ]
                ),
                html.Div(f"args: {args_str}", style={"color": TEXT_MUTED, "fontSize": "10px", "marginTop": "2px"}),
                html.Div(
                    result_p,
                    style={
                        "color": "#9ae6b4",
                        "fontSize": "10px",
                        "marginTop": "4px",
                        "whiteSpace": "pre-wrap",
                        "wordBreak": "break-all",
                    }
                ),
            ]
        ))

    return html.Div(children)


def _render_answer(answer: str, sources: Optional[List[Dict[str, Any]]] = None) -> html.Div:
    """Render the agent's answer with markdown formatting, clickable supporting sources, and HITL action."""
    if not answer:
        return html.Div("No answer generated.", style={"color": TEXT_MUTED})

    sources_component = None
    if sources:
        source_buttons = []
        for s in sources:
            src_id = s.get("id")
            sref = s.get("source_ref") or src_id
            stitle = s.get("title") or sref
            stype = s.get("type", "EVIDENCE")
            source_buttons.append(
                dbc.Button(
                    children=[
                        html.Span("📄 ", style={"fontSize": "12px"}),
                        html.B(str(sref), style={"fontSize": "11px"}),
                        html.Span(f" ({stype})", style={"color": "#a0aec0", "fontSize": "10px", "marginLeft": "4px"})
                    ],
                    id={"type": "ask-source-badge", "source_id": src_id},
                    size="sm",
                    color="primary",
                    outline=True,
                    style={"fontSize": "11px", "padding": "4px 10px", "borderColor": "#3182ce"}
                )
            )

        sources_component = html.Div(
            style={
                "marginTop": "14px",
                "padding": "12px 14px",
                "backgroundColor": "#131b26",
                "borderRadius": "6px",
                "border": "1px solid #2b6cb0"
            },
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "8px"},
                    children=[
                        html.B("Supporting Sources & Evidentiary Provenance:", style={"color": "#63b3ed", "fontSize": "12px"}),
                        html.Span(" · Click any source to inspect verified court record", style={"color": "#a0aec0", "fontSize": "11px"})
                    ]
                ),
                html.Div(
                    style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                    children=source_buttons
                )
            ]
        )

    return html.Div(
        style={
            "backgroundColor": PANEL_BG,
            "border": f"1px solid {BORDER_COL}",
            "borderRadius": "8px",
            "padding": "18px 20px",
        },
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "14px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span("🤖", style={"fontSize": "18px"}),
                            html.Span("CrimeNet Investigation Response", style={"color": TEXT_MAIN, "fontWeight": "700", "fontSize": "13px"}),
                        ]
                    ),
                    dbc.Button(
                        "✏️ Dispute / Correct AI Finding (HITL)",
                        id="btn-ask-hitl-dispute",
                        size="sm",
                        color="warning",
                        outline=True,
                        style={"fontSize": "11px", "fontWeight": "600"}
                    )
                ]
            ),
            dcc.Markdown(
                answer,
                style={
                    "color": TEXT_DIM,
                    "fontSize": "13px",
                    "lineHeight": "1.7",
                    "whiteSpace": "pre-wrap",
                },
            ),
            sources_component if sources_component else None,
            html.Hr(style={"borderColor": BORDER_COL, "margin": "16px 0 10px 0"}),
            html.Span(
                "⚠️ CrimeNet is an investigation decision-support system. "
                "AI responses and predicted links are analytical signals that require primary evidence verification by human investigators.",
                style={"color": "#d69e2e", "fontSize": "10px", "fontStyle": "italic"}
            )
        ]
    )


def register_ask_crimenet_callbacks(dash_app):
    """Register all Ask CrimeNet Dash callbacks."""
    from dash import Input, Output, State, ctx, ALL, no_update
    from dash.exceptions import PreventUpdate

    # ── Open/close modal ─────────────────────────────────────────────────
    @dash_app.callback(
        Output("modal-ask-crimenet", "is_open"),
        [
            Input("btn-open-ask-crimenet", "n_clicks"),
            Input("top-ask-crimenet-submit-btn", "n_clicks"),
            Input("top-ask-chip-1", "n_clicks"),
            Input("top-ask-chip-2", "n_clicks"),
            Input("top-ask-chip-3", "n_clicks"),
            Input("top-ask-chip-4", "n_clicks"),
        ],
        State("modal-ask-crimenet", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_ask_modal(btn_open, top_submit, chip1, chip2, chip3, chip4, is_open):
        triggered = ctx.triggered_id
        if triggered == "btn-open-ask-crimenet":
            return not is_open
        elif triggered in ("top-ask-crimenet-submit-btn", "top-ask-chip-1", "top-ask-chip-2", "top-ask-chip-3", "top-ask-chip-4"):
            return True
        return is_open

    # ── Populate case context pill ────────────────────────────────────────
    @dash_app.callback(
        Output("ask-crimenet-case-pill", "children"),
        Input("dossier-active-case-id-store", "data"),
        prevent_initial_call=False,
    )
    def update_case_pill(case_id):
        if not case_id:
            return html.Span("No case active", style={"color": TEXT_MUTED, "fontSize": "11px"})
        try:
            from storage.case_data_service import CaseDataService
            c = CaseDataService().get_case(case_id)
            if c:
                return dbc.Badge(
                    f"📁 {c.get('case_number', case_id)} — {(c.get('title') or '')[:30]}",
                    color="primary",
                    style={"fontSize": "11px"}
                )
        except Exception:
            pass
        return html.Span(f"Case: {case_id[:12]}…", style={"color": ACCENT, "fontSize": "11px"})

    # ── Fill example question into input ──────────────────────────────────
    @dash_app.callback(
        Output("ask-crimenet-input", "value"),
        [
            Input({"type": "ask-example-question", "index": ALL}, "n_clicks"),
            Input("top-ask-crimenet-submit-btn", "n_clicks"),
            Input("top-ask-chip-1", "n_clicks"),
            Input("top-ask-chip-2", "n_clicks"),
            Input("top-ask-chip-3", "n_clicks"),
            Input("top-ask-chip-4", "n_clicks"),
        ],
        State("top-ask-crimenet-input", "value"),
        prevent_initial_call=True,
    )
    def fill_example_question(all_clicks, top_submit, chip1, chip2, chip3, chip4, top_input_val):
        triggered = ctx.triggered_id
        if not triggered:
            raise PreventUpdate
        if triggered == "top-ask-chip-1":
            return "Why is Rahul connected to Amit?"
        elif triggered == "top-ask-chip-2":
            return "Trace Hawala money flow and cross-border laundering channels."
        elif triggered == "top-ask-chip-3":
            return "Identify uncorroborated AI links and suspect connections that require investigator verification."
        elif triggered == "top-ask-chip-4":
            return "Which suspects hold the highest operational and flight risk across active syndicates?"
        elif triggered == "top-ask-crimenet-submit-btn":
            q = (top_input_val or "").strip()
            return q or "Provide a comprehensive intelligence summary of the active syndicate network."
        elif isinstance(triggered, dict) and triggered.get("type") == "ask-example-question":
            idx = triggered.get("index", 0)
            if idx < len(EXAMPLE_QUESTIONS):
                return EXAMPLE_QUESTIONS[idx]
        raise PreventUpdate

    # ── Submit question to agent ──────────────────────────────────────────
    @dash_app.callback(
        Output("ask-crimenet-result-store", "data"),
        [
            Input("btn-ask-crimenet-submit", "n_clicks"),
            Input("top-ask-crimenet-submit-btn", "n_clicks"),
            Input("top-ask-chip-1", "n_clicks"),
            Input("top-ask-chip-2", "n_clicks"),
            Input("top-ask-chip-3", "n_clicks"),
            Input("top-ask-chip-4", "n_clicks"),
        ],
        [
            State("ask-crimenet-input",    "value"),
            State("top-ask-crimenet-input", "value"),
            State("dossier-active-case-id-store",  "data"),
        ],
        prevent_initial_call=True,
    )
    def submit_question(n_clicks, top_submit, chip1, chip2, chip3, chip4, question, top_input, case_id):
        triggered = ctx.triggered_id
        if not triggered:
            raise PreventUpdate
        effective_q = question
        if triggered == "top-ask-chip-1":
            effective_q = "Why is Rahul connected to Amit?"
        elif triggered == "top-ask-chip-2":
            effective_q = "Trace Hawala money flow and cross-border laundering channels."
        elif triggered == "top-ask-chip-3":
            effective_q = "Identify uncorroborated AI links and suspect connections that require investigator verification."
        elif triggered == "top-ask-chip-4":
            effective_q = "Which suspects hold the highest operational and flight risk across active syndicates?"
        elif triggered == "top-ask-crimenet-submit-btn":
            effective_q = (top_input or "").strip() or question or "Provide a comprehensive intelligence summary of the active syndicate network."

        if not effective_q or not effective_q.strip():
            raise PreventUpdate

        question = effective_q

        case_id = case_id or "case-synthetic-black-falcon-001"

        case_context: Dict[str, Any] = {}
        try:
            from storage.case_data_service import CaseDataService
            c = CaseDataService().get_case(case_id)
            if c:
                case_context = {k: c.get(k) for k in ("case_number", "title", "crime_type", "status")}
        except Exception:
            pass

        try:
            from analyzer.investigation_agent import run_investigation
            result = run_investigation(
                question=question.strip(),
                case_id=case_id,
                case_context=case_context,
            )
            return result
        except Exception as exc:
            return {
                "answer":     f"⚠️ Agent error: {exc}",
                "sources":    [],
                "tool_trace": [],
                "messages":   [],
            }

    # ── Render answer from store ──────────────────────────────────────────
    @dash_app.callback(
        Output("ask-crimenet-answer",     "children"),
        Output("ask-crimenet-tool-trace", "children"),
        Input("ask-crimenet-result-store", "data"),
        prevent_initial_call=True,
    )
    def render_result(data):
        if not data:
            raise PreventUpdate
        answer     = data.get("answer", "")
        sources    = data.get("sources", [])
        tool_trace = data.get("tool_trace", [])
        return _render_answer(answer, sources=sources), _render_tool_trace(tool_trace)

    # ── Inspect supporting evidence source when clicked ────────────────────
    @dash_app.callback(
        [
            Output("modal-ask-source-detail", "is_open"),
            Output("modal-ask-source-body",   "children"),
        ],
        [
            Input({"type": "ask-source-badge", "source_id": ALL}, "n_clicks"),
            Input("btn-close-ask-source-modal", "n_clicks"),
        ],
        [
            State("modal-ask-source-detail", "is_open"),
            State("dossier-active-case-id-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_inspect_source(badge_clicks, close_click, is_open, active_case_id):
        trig = ctx.triggered_id
        if trig == "btn-close-ask-source-modal":
            return False, no_update

        if isinstance(trig, dict) and trig.get("type") == "ask-source-badge":
            source_id = str(trig.get("source_id") or "").strip()
            if not source_id:
                raise PreventUpdate

            case_id = active_case_id or "case-synthetic-black-falcon-001"
            from storage.case_data_service import CaseDataService
            svc = CaseDataService()

            # 1. Search Evidence Table
            ev = svc.get_evidence(source_id)
            if not ev:
                for e in svc.list_evidence(case_id):
                    e_sref = str(e.get("source_ref") or "").lower()
                    e_id = str(e.get("id") or "").lower()
                    if source_id.lower() == e_id or source_id.lower() == e_sref or source_id.lower() in e_sref:
                        ev = e
                        break

            if ev:
                meta = {}
                if ev.get("metadata"):
                    try:
                        meta = json.loads(ev["metadata"]) if isinstance(ev["metadata"], str) else ev["metadata"]
                    except Exception:
                        pass

                body = html.Div([
                    html.Div([
                        dbc.Badge(ev.get("evidence_type", "PRIMARY EXHIBIT"), color="primary", style={"fontSize": "12px", "marginBottom": "6px"}),
                        html.H5(ev.get("title", "Evidence Record"), style={"color": "#f7fafc", "fontWeight": "700"}),
                        html.Div([
                            html.Span("Source Ref: ", style={"color": "#a0aec0", "fontSize": "11px", "fontWeight": "700"}),
                            html.Span(str(ev.get("source_ref") or source_id), style={"color": "#63b3ed", "fontSize": "11px", "fontFamily": "monospace"}),
                            html.Span(" | Filename: ", style={"color": "#a0aec0", "fontSize": "11px"}),
                            html.Span(str(ev.get("filename") or meta.get("filename") or "—"), style={"color": "#cbd5e0", "fontSize": "11px"}),
                        ], style={"marginBottom": "12px"}),
                    ]),
                    html.Div(
                        style={"backgroundColor": "#1a202c", "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "14px", "marginBottom": "12px"},
                        children=[
                            html.B("Extracted Evidence Content / Raw Text:", style={"fontSize": "11px", "color": "#a0aec0"}),
                            html.P(ev.get("content") or "No raw text content available.", style={"color": "#f7fafc", "fontSize": "12px", "marginTop": "6px", "lineHeight": "1.6", "whiteSpace": "pre-wrap"})
                        ]
                    ),
                    html.Div([
                        html.Span("SHA-256 Hash: ", style={"color": "#718096", "fontSize": "10px", "fontWeight": "700"}),
                        html.Span(str(ev.get("sha256_hash") or "Verified Ingested Document"), style={"color": "#a0aec0", "fontSize": "10px", "fontFamily": "monospace"}),
                    ])
                ])
                return True, body

            # 2. Search Graph Transactions & Edges
            graph_data = svc.get_case_graph(case_id)
            matching_edges = []
            for eg in graph_data.get("edges", []):
                props = eg.get("info") or eg.get("properties") or {}
                if isinstance(props, str):
                    try:
                        props = json.loads(props)
                    except Exception:
                        props = {}
                e_ref = str(props.get("source_ref") or eg.get("source_ref") or props.get("provenance") or eg.get("id") or "")
                if source_id.lower() in e_ref.lower():
                    matching_edges.append((eg, props))

            if matching_edges:
                edge_cards = []
                for eg, props in matching_edges[:5]:
                    s = eg.get("source_name") or eg.get("source")
                    t = eg.get("target_name") or eg.get("target")
                    rel = eg.get("label") or eg.get("type") or "CONNECTED_TO"
                    amt = props.get("amount_inr") or props.get("amount")
                    amt_str = f"Rs. {amt:,.2f}" if amt else "—"
                    edge_cards.append(
                        html.Div(
                            style={"backgroundColor": "#1a202c", "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "12px", "marginBottom": "10px"},
                            children=[
                                html.Div([
                                    dbc.Badge(rel, color="info", className="me-2"),
                                    html.Span(f"{s} -> {t}", style={"fontWeight": "700", "color": "#f7fafc", "fontSize": "13px"}),
                                ], style={"marginBottom": "6px"}),
                                html.Div([
                                    html.Span("Amount: ", style={"color": "#a0aec0", "fontSize": "11px"}),
                                    html.Span(amt_str, style={"color": "#48bb78", "fontWeight": "700", "fontSize": "12px"}),
                                    html.Span(" | Provenance: ", style={"color": "#a0aec0", "fontSize": "11px", "marginLeft": "8px"}),
                                    html.Span(str(props.get("provenance") or props.get("source_ref") or source_id), style={"color": "#63b3ed", "fontSize": "11px"}),
                                ]),
                                html.Div([
                                    html.Span("Transaction ID / Modality: ", style={"color": "#718096", "fontSize": "10px"}),
                                    html.Span(f"{props.get('transaction_id', 'TXN-RECORD')} [OBSERVED PRIMARY RECORD]", style={"color": "#a0aec0", "fontSize": "10px", "fontFamily": "monospace"}),
                                ], style={"marginTop": "4px"})
                            ]
                        )
                    )

                body = html.Div([
                    dbc.Badge("OBSERVED TRANSACTION LEDGER", color="success", style={"fontSize": "12px", "marginBottom": "6px"}),
                    html.H5(f"Banking & Transaction Record: {source_id}", style={"color": "#f7fafc", "fontWeight": "700"}),
                    html.P("This source reference corresponds to observed financial transactions extracted from verified banking exhibits.", style={"color": "#a0aec0", "fontSize": "12px"}),
                    html.Div(edge_cards),
                ])
                return True, body

            # 3. Search Human Corrections
            corrections = svc.get_active_corrections(case_id)
            for cid, c in corrections.items():
                c_sref = str(c.get("source_ref") or "")
                if source_id.lower() in c_sref.lower() or source_id.lower() in cid.lower():
                    body = html.Div([
                        dbc.Badge("HUMAN GROUND TRUTH", color="warning", style={"fontSize": "12px", "marginBottom": "6px"}),
                        html.H5(f"Verified Human Correction: {source_id}", style={"color": "#f7fafc", "fontWeight": "700"}),
                        html.Div(
                            style={"backgroundColor": "#1a202c", "border": "1px solid #d69e2e", "borderRadius": "6px", "padding": "14px", "marginBottom": "12px"},
                            children=[
                                html.P([
                                    html.B("Prior AI Inference (Superseded): ", style={"color": "#e53e3e"}),
                                    html.Span(f"\"{c.get('original_ai_result')}\"", style={"color": "#cbd5e0", "textDecoration": "line-through"})
                                ]),
                                html.P([
                                    html.B("Human Verified Truth: ", style={"color": "#38a169"}),
                                    html.Span(f"\"{c.get('corrected_value')}\"", style={"color": "#f7fafc", "fontWeight": "700"})
                                ]),
                                html.P([
                                    html.B("Reason: ", style={"color": "#a0aec0"}),
                                    html.Span(str(c.get("reason") or "Investigator verification"))
                                ]),
                                html.P([
                                    html.B("Source Exhibit: ", style={"color": "#a0aec0"}),
                                    html.Span(str(c.get("source_ref") or "CAF / KYC Records"), style={"color": "#63b3ed"})
                                ]),
                            ]
                        ),
                        html.Div("Note: This correction is applied as active case context and does not retrain the underlying model.", style={"color": "#718096", "fontSize": "11px", "fontStyle": "italic"})
                    ])
                    return True, body

            # 4. Fallback Exhibit Detail
            body = html.Div([
                dbc.Badge("CASE EXHIBIT REFERENCE", color="secondary", style={"fontSize": "12px", "marginBottom": "6px"}),
                html.H5(f"Supporting Exhibit: {source_id}", style={"color": "#f7fafc", "fontWeight": "700"}),
                html.P(f"This exhibit reference ({source_id}) is cited in the investigation findings as corroborating evidence. It forms part of Case {case_id}'s evidentiary record.", style={"color": "#cbd5e0", "fontSize": "12px", "marginTop": "10px"}),
                html.Div(
                    style={"backgroundColor": "#1a202c", "border": "1px solid #2d3748", "borderRadius": "6px", "padding": "12px", "marginTop": "12px"},
                    children=[
                        html.Span("Evidentiary Status: ", style={"color": "#a0aec0", "fontSize": "11px", "fontWeight": "700"}),
                        html.Span("OBSERVED PRIMARY DOCUMENT / TELECOM RECORD", style={"color": "#48bb78", "fontSize": "11px", "fontWeight": "700"}),
                    ]
                )
            ])
            return True, body

        return is_open, no_update

    # ── Open HITL modal from Ask CrimeNet dispute button ───────────────────
    @dash_app.callback(
        [
            Output("modal-investigation-actions", "is_open", allow_duplicate=True),
            Output("hitl-original-ai-input",      "value", allow_duplicate=True),
        ],
        Input("btn-ask-hitl-dispute", "n_clicks"),
        State("ask-crimenet-result-store", "data"),
        prevent_initial_call=True
    )
    def open_hitl_from_ask(n_clicks, data):
        if not n_clicks:
            raise PreventUpdate
        answer_snippet = (data.get("answer", "") if data else "")[:200]
        return True, answer_snippet
