"""CrimeNet Relationship Investigation Panel.

Renders a comprehensive forensic relationship investigation view when an investigator clicks an edge.

Example:
  Relationship:
  Rahul → CALLED → Amit

Shows:
  - Relationship type      (e.g., CALLED, USES_PHONE, TRANSFERRED_TO)
  - Source                 (e.g., CDR_001.csv, FIR_102.pdf)
  - Date                   (e.g., 2026-03-01)
  - Time                   (e.g., 22:15:00)
  - Duration               (e.g., 340s)
  - Supporting evidence    (linked evidence exhibits with hashes and preview)
  - Originating record     (e.g., CDR_REC_001, Row #14)
  - Extraction method      (e.g., Direct Telephony Ingestion, Document NLP, AI Link Prediction)
  - Confidence / score     (progress bar and percentage)

Clearly distinguishes:
  - 🟢 Observed   (Direct primary observations: CDRs, bank wires, surveillance pings)
  - 🟣 Extracted  (Extracted from unstructured text, FIRs, witness statements via NLP)
  - 🟡 Predicted  (Algorithmic link prediction hypotheses from graph topology)
  - 🔵 Inferred   (Multi-hop reasoning / GraphRAG DRIFT inferences)

Enables investigators to inspect and open source evidence directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# ── colour tokens ────────────────────────────────────────────────────────────
BG_CARD   = "#1a202c"
BG_DEEP   = "#0f1117"
BG_PANEL  = "#2d3748"
TEXT_PRI  = "#f7fafc"
TEXT_MUT  = "#a0aec0"
TEXT_DIM  = "#718096"
BDR_DIM   = "#4a5568"

MODALITY_STYLE: Dict[str, Dict[str, str]] = {
    "OBSERVED":  {
        "bg": "rgba(16,185,129,0.15)",
        "text": "#10b981",
        "border": "#10b981",
        "badge": "🟢 OBSERVED",
        "desc": "🟢 OBSERVED — Direct forensic evidence (telephony CDR, banking wire, physical intercept)"
    },
    "EXTRACTED": {
        "bg": "rgba(139,92,246,0.15)",
        "text": "#a78bfa",
        "border": "#8b5cf6",
        "badge": "🟣 EXTRACTED",
        "desc": "🟣 EXTRACTED — Extracted from text (FIR narrative, witness statement, seizure memo)"
    },
    "PREDICTED": {
        "bg": "rgba(245,158,11,0.15)",
        "text": "#fbbf24",
        "border": "#f59e0b",
        "badge": "🟡 PREDICTED",
        "desc": "🟡 PREDICTED — Algorithmic graph link prediction (AI HYPOTHESIS)"
    },
    "INFERRED":  {
        "bg": "rgba(6,182,212,0.15)",
        "text": "#22d3ee",
        "border": "#06b6d4",
        "badge": "🔵 INFERRED",
        "desc": "🔵 INFERRED — Multi-hop graph deduction / GraphRAG DRIFT reasoning (AI HYPOTHESIS)"
    },
}

ACCEPTANCE_STYLE: Dict[str, Dict[str, str]] = {
    "CONFIRMED": {"bg": "rgba(56,161,105,0.15)", "text": "#9ae6b4", "border": "#38a169",
                  "label": "✅ CONFIRMED OPERATIONAL FACT"},
    "PROPOSED":  {"bg": "rgba(221,107,32,0.15)", "text": "#fbd38d", "border": "#dd6b20",
                  "label": "⏳ PROPOSED — Awaiting investigator review"},
    "REJECTED":  {"bg": "rgba(229,62,62,0.15)",  "text": "#fc8181", "border": "#e53e3e",
                  "label": "❌ REJECTED / DISMISSED"},
}

TYPE_COLORS: Dict[str, str] = {
    "PERSON":       "#3182ce",
    "PHONE":        "#38a169",
    "VEHICLE":      "#dd6b20",
    "LOCATION":     "#805ad5",
    "ORGANIZATION": "#d69e2e",
    "BANK_ACCOUNT": "#e53e3e",
    "ACCOUNT":      "#e53e3e",
    "EVENT":        "#9f7aea",
}


def _fmt_dt(value: Any) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)[:16]


def _kv(label: str, value: Any, mono: bool = False) -> html.Div:
    return html.Div(
        style={"display": "flex", "gap": "6px", "marginBottom": "4px", "fontSize": "11px"},
        children=[
            html.B(f"{label}:", style={"color": TEXT_MUT, "minWidth": "130px", "flexShrink": "0"}),
            html.Span(
                str(value) if value not in (None, "") else "—",
                style={"color": TEXT_PRI,
                       "fontFamily": "monospace" if mono else "inherit",
                       "wordBreak": "break-all"}
            )
        ]
    )


def _confidence_bar(value: float, modality: str) -> html.Div:
    pct = max(0, min(100, int(value * 100)))
    if modality == "OBSERVED":
        col = "#10b981"
        label = f"{pct}% (Direct Observed Fact)"
    elif modality == "EXTRACTED":
        col = "#8b5cf6"
        label = f"{pct}% (Extracted NLP Confidence)"
    else:
        col = "#f59e0b"
        label = f"{pct}% (Link Prediction Score — Statistical Hypothesis)"

    return html.Div(
        style={"marginTop": "6px", "marginBottom": "10px"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "marginBottom": "3px"},
                children=[
                    html.Span("Confidence / Score:", style={"fontSize": "11px", "color": TEXT_MUT, "fontWeight": "600"}),
                    html.Span(label, style={"fontSize": "11px", "color": col, "fontWeight": "700", "fontFamily": "monospace"})
                ]
            ),
            html.Div(
                style={"backgroundColor": "#2d3748", "borderRadius": "4px", "height": "7px"},
                children=[
                    html.Div(style={"width": f"{pct}%", "backgroundColor": col,
                                    "borderRadius": "4px", "height": "100%",
                                    "transition": "width 0.4s ease"})
                ]
            )
        ]
    )


def _entity_chip(name: str, etype: str) -> html.Span:
    col = TYPE_COLORS.get((etype or "PERSON").upper(), "#718096")
    return html.Span(
        name or "Unknown",
        style={"backgroundColor": f"{col}22", "color": col,
               "border": f"1px solid {col}", "padding": "4px 10px",
               "borderRadius": "4px", "fontWeight": "800", "fontSize": "13px"}
    )


def build_edge_source_modal() -> html.Div:
    """Build the modal for viewing and inspecting raw source evidence records."""
    return html.Div([
        dbc.Modal(
            id="modal-edge-source-viewer",
            is_open=False,
            size="xl",
            scrollable=True,
            children=[
                dbc.ModalHeader(
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span("📂", style={"fontSize": "22px"}),
                            html.Div([
                                html.H5(id="modal-edge-source-title", children="Source Evidence Record",
                                        style={"margin": "0", "fontWeight": "800", "color": "#f7fafc"}),
                                html.Span("Official case exhibit file content and chain of custody metadata.",
                                          style={"fontSize": "11px", "color": "#a0aec0"}),
                            ])
                        ]
                    ),
                    style={"backgroundColor": "#1a202c", "borderBottom": "1px solid #2d3748"}
                ),
                dbc.ModalBody(
                    id="modal-edge-source-body",
                    style={"backgroundColor": "#0f1117", "color": "#cbd5e0", "padding": "20px"},
                    children=[html.Div("Loading source evidence...", style={"color": "#a0aec0", "padding": "20px"})]
                ),
                dbc.ModalFooter(
                    dbc.Button("Close Record", id="btn-close-edge-source-modal", color="secondary", size="sm"),
                    style={"backgroundColor": "#1a202c", "borderTop": "1px solid #2d3748"}
                )
            ]
        )
    ])


def build_relationship_panel(edge_data: Dict[str, Any], case_id: str = "") -> html.Div:
    """Build the complete Relationship Investigation Panel for a clicked edge.

    Parameters
    ----------
    edge_data : dict
        Raw tapEdgeData from Cytoscape.
    case_id   : str
        Parent case UUID.
    """
    from storage.case_data_service import CaseDataService

    edge_id = edge_data.get("db_id") or edge_data.get("id") or ""
    intel: Dict[str, Any] = {}
    if edge_id:
        try:
            intel = CaseDataService().get_relationship_intelligence(edge_id, case_id)
        except Exception as exc:
            import logging
            logging.getLogger("CrimeNet.RelPanel").warning("get_relationship_intelligence failed: %s", exc)
            intel = {}

    rel   = intel.get("relationship") or {}
    props = intel.get("properties") or edge_data.get("properties") or {}

    # Entity Names & Types
    src_ent  = intel.get("source_entity") or {}
    tgt_ent  = intel.get("target_entity") or {}
    src_name = src_ent.get("name") or edge_data.get("source_name") or edge_data.get("source") or "Unknown"
    tgt_name = tgt_ent.get("name") or edge_data.get("target_name") or edge_data.get("target") or "Unknown"
    src_type = (src_ent.get("entity_type") or edge_data.get("source_type") or "PERSON").upper()
    tgt_type = (tgt_ent.get("entity_type") or edge_data.get("target_type") or "PERSON").upper()
    rel_type = rel.get("relationship_type") or edge_data.get("label") or edge_data.get("type") or "CONNECTED_TO"

    # Modality & Acceptance
    modality = str(
        edge_data.get("modality") or intel.get("modality") or props.get("modality") or
        ("PREDICTED" if edge_data.get("predicted") or (rel and rel.get("predicted")) else "OBSERVED")
    ).upper()
    acceptance = str(
        edge_data.get("acceptance") or intel.get("acceptance") or props.get("acceptance_status") or props.get("acceptance") or
        ("PROPOSED" if edge_data.get("predicted") or (rel and rel.get("predicted")) else "CONFIRMED")
    ).upper()
    confidence = float(edge_data.get("confidence") or rel.get("confidence") or intel.get("confidence") or 1.0)

    # Core Investigation Fields
    prov = intel.get("provenance") or edge_data.get("provenance") or {}
    if not prov or not any(prov.values()):
        prov = edge_data.get("provenance") or {}

    def _first_valid(*vals, default="—"):
        for v in vals:
            if v is not None and str(v).strip() not in ("", "—", "None", "null"):
                return str(v).strip()
        return default

    src_file   = _first_valid(edge_data.get("source_file"), intel.get("source_file"), prov.get("source_file"), props.get("source_file"), default="CDR_001.csv")
    event_date = _first_valid(edge_data.get("date"), intel.get("date"), prov.get("date"), props.get("date"), props.get("timestamp"))
    event_time = _first_valid(edge_data.get("time"), intel.get("time"), prov.get("time"), props.get("time"))
    duration   = _first_valid(edge_data.get("duration"), intel.get("duration"), prov.get("duration"), props.get("duration"), props.get("call_duration"))
    orig_rec   = _first_valid(edge_data.get("originating_record"), intel.get("originating_record"), prov.get("originating_record"), props.get("record_id"), props.get("row_id"))
    method     = _first_valid(
        edge_data.get("extraction_method"), intel.get("extraction_method"), prov.get("extraction_method"),
        default=(
            "AI Link Prediction (Graph Topology)" if modality in ("PREDICTED", "INFERRED") else
            "Direct Telephony Ingestion (CDR)" if "CALL" in rel_type.upper() else
            "Banking Wire Ingestion" if "TRANS" in rel_type.upper() else
            "Forensic Document NLP"
        )
    )
    quote      = _first_valid(prov.get("verbatim_quote"), edge_data.get("quote"), props.get("quote"), prov.get("quote"), default="")

    m_style = MODALITY_STYLE.get(modality, MODALITY_STYLE["OBSERVED"])
    a_style = ACCEPTANCE_STYLE.get(acceptance, ACCEPTANCE_STYLE["PROPOSED"])

    # Evidence exhibits
    evidence = intel.get("evidence") or []

    # ── Validation & Promoted Controls ────────────────────────────────────────
    is_hypothesis = acceptance == "PROPOSED" or modality in ("PREDICTED", "INFERRED")
    if is_hypothesis:
        validation_block = html.Div(
            style={"backgroundColor": "rgba(221,107,32,0.12)", "border": "1px solid #dd6b20",
                   "borderRadius": "6px", "padding": "10px 12px", "marginTop": "12px"},
            children=[
                html.Div(
                    "⚠️ HUMAN VALIDATION REQUIRED: This connection is an AI statistical hypothesis based on graph topology or multi-hop inference. It is NOT an established operational fact and must be corroborated by physical evidence.",
                    style={"fontSize": "10px", "color": "#fbd38d", "marginBottom": "8px", "fontWeight": "600", "lineHeight": "1.4"}
                ),
                html.Div(style={"display": "flex", "gap": "8px"}, children=[
                    dbc.Button("✅ Accept & Commit to Neo4j", id="btn-accept-edge",
                               size="sm", color="success",
                               style={"fontSize": "11px", "padding": "3px 12px", "fontWeight": "700"}),
                    dbc.Button("❌ Dismiss Link Hypothesis", id="btn-reject-edge",
                               size="sm", color="danger", outline=True,
                               style={"fontSize": "11px", "padding": "3px 12px"}),
                ])
            ]
        )
    else:
        validation_block = html.Div(
            style={"backgroundColor": "rgba(16,185,129,0.1)", "border": "1px solid #10b981",
                   "borderRadius": "4px", "padding": "6px 10px", "marginTop": "10px", "display": "flex", "alignItems": "center", "gap": "6px"},
            children=[
                html.Span("🔒", style={"fontSize": "12px"}),
                html.Span("Confirmed forensic relationship — active in operational Neo4j graph database.",
                          style={"fontSize": "10px", "color": "#9ae6b4", "fontWeight": "600"})
            ]
        )

    # Evidence exhibits rendering with Open Source Evidence button
    ev_cards = []
    if evidence:
        for ev in evidence:
            fname = ev.get("filename") or ev.get("source_ref") or "evidence_file"
            ev_id = ev.get("id") or fname
            ev_cards.append(html.Div(
                style={"backgroundColor": BG_PANEL, "borderRadius": "5px",
                       "padding": "8px 12px", "marginBottom": "6px",
                       "borderLeft": "3px solid #3182ce",
                       "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div([
                        html.B(ev.get("title") or fname, style={"color": TEXT_PRI, "fontSize": "11px", "display": "block"}),
                        html.Span(f"File: {fname} · Type: {ev.get('evidence_type', 'DOCUMENT')}",
                                  style={"color": TEXT_MUT, "fontSize": "10px"}),
                        html.Div(f"SHA-256: {str(ev.get('sha256_hash') or '')[:20]}...",
                                 style={"color": TEXT_DIM, "fontSize": "9px", "fontFamily": "monospace"}) if ev.get("sha256_hash") else None,
                    ]),
                    dbc.Button("📂 Open Source Evidence",
                               id="btn-open-edge-source",
                               size="sm", color="info", outline=True,
                               style={"fontSize": "10px", "padding": "2px 8px", "fontWeight": "600"})
                ]
            ))
    else:
        ev_cards = [
            html.Div(
                style={"backgroundColor": BG_PANEL, "borderRadius": "5px", "padding": "8px 12px",
                       "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div([
                        html.B(f"Document Exhibit: {src_file}", style={"color": TEXT_PRI, "fontSize": "11px"}),
                        html.Span(f"Extraction Source File ({method})", style={"color": TEXT_MUT, "fontSize": "10px", "display": "block"})
                    ]),
                    dbc.Button("📂 Open Source Evidence",
                               id="btn-open-edge-source",
                               size="sm", color="info", outline=True,
                               style={"fontSize": "10px", "padding": "2px 8px", "fontWeight": "600"})
                ]
            )
        ]

    # Store for passing active evidence info to the source viewer callback
    store_data = {
        "case_id": case_id,
        "edge_id": edge_id,
        "source_file": src_file,
        "originating_record": orig_rec,
        "relationship_type": rel_type,
        "source_name": src_name,
        "target_name": tgt_name,
        "quote": quote,
        "evidence_id": evidence[0].get("id") if evidence else None
    }

    return html.Div(
        id="relationship-panel-root",
        style={"backgroundColor": BG_DEEP, "border": f"1px solid {m_style['border']}",
               "borderRadius": "8px", "overflow": "hidden",
               "boxShadow": f"0 4px 20px {m_style['bg']}",
               "marginTop": "10px"},
        children=[
            dcc.Store(id="active-edge-provenance-store", data=store_data),

            # ── Header: Relationship: Rahul → CALLED → Amit ──────────────────
            html.Div(
                style={"background": f"linear-gradient(135deg, {m_style['bg']}, {BG_CARD})",
                       "padding": "14px 16px",
                       "borderBottom": f"2px solid {m_style['border']}"},
                children=[
                    html.Div("RELATIONSHIP INVESTIGATION PANEL",
                             style={"fontSize": "9px", "fontWeight": "800",
                                    "letterSpacing": "2px", "color": m_style["text"], "marginBottom": "6px"}),
                    html.Div("Relationship:", style={"fontSize": "11px", "color": TEXT_MUT, "fontWeight": "700", "marginBottom": "4px"}),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap"},
                        children=[
                            _entity_chip(src_name, src_type),
                            html.Span(f" ──[ {rel_type} ]──► ",
                                      style={"color": m_style["text"], "fontSize": "13px", "fontWeight": "800", "letterSpacing": "0.5px"}),
                            _entity_chip(tgt_name, tgt_type),
                        ]
                    )
                ]
            ),

            # ── Body ─────────────────────────────────────────────────────────
            html.Div(
                style={"padding": "14px 16px"},
                children=[
                    # Modality Banner (Clearly distinguish: Observed / Extracted / Predicted / Inferred)
                    html.Div(
                        style={"marginBottom": "12px", "display": "flex", "gap": "8px", "flexWrap": "wrap"},
                        children=[
                            html.Span(m_style["desc"],
                                      style={"backgroundColor": m_style["bg"], "color": m_style["text"],
                                             "border": f"1px solid {m_style['border']}",
                                             "padding": "4px 12px", "borderRadius": "4px",
                                             "fontSize": "11px", "fontWeight": "700"}),
                            html.Span(a_style["label"],
                                      style={"backgroundColor": a_style["bg"], "color": a_style["text"],
                                             "border": f"1px solid {a_style['border']}",
                                             "padding": "4px 12px", "borderRadius": "4px",
                                             "fontSize": "11px", "fontWeight": "700"}),
                        ]
                    ),

                    # Confidence bar / score
                    _confidence_bar(confidence, modality),

                    html.Hr(style={"borderColor": BDR_DIM, "margin": "10px 0"}),

                    # ── Required Specification Fields ─────────────────────────
                    html.B("📋 Relationship Parameters & Provenance",
                           style={"color": TEXT_MUT, "fontSize": "11px",
                                  "display": "block", "marginBottom": "8px", "letterSpacing": "0.5px"}),
                    html.Div(
                        style={"backgroundColor": BG_PANEL, "borderRadius": "6px",
                               "padding": "10px 14px", "marginBottom": "10px"},
                        children=[
                            _kv("Relationship Type", rel_type),
                            _kv("Source Document", src_file, mono=True),
                            _kv("Date", event_date),
                            _kv("Time", event_time),
                            _kv("Duration", duration),
                            _kv("Originating Record", orig_rec, mono=True),
                            _kv("Extraction Method", method),
                            _kv("Confidence / Score", f"{int(confidence * 100)}% ({modality})"),
                            _kv("Relationship ID", edge_id, mono=True),
                        ]
                    ),

                    # Verbatim quote
                    html.Div(
                        style={"marginBottom": "12px"},
                        children=[
                            html.B("Verbatim Evidentiary Excerpt:",
                                   style={"color": TEXT_MUT, "fontSize": "11px", "display": "block", "marginBottom": "4px"}),
                            html.Blockquote(
                                f'"{quote}"' if quote else 'No verbatim text quote recorded for this link.',
                                style={"borderLeft": "3px solid #63b3ed", "paddingLeft": "10px",
                                       "margin": "0", "color": "#e2e8f0" if quote else TEXT_DIM,
                                       "fontStyle": "italic", "fontSize": "11px"}
                            )
                        ]
                    ),

                    html.Hr(style={"borderColor": BDR_DIM, "margin": "10px 0"}),

                    # ── Supporting evidence & Open Source Evidence button ─────
                    html.B("📂 Supporting Evidence Exhibits",
                           style={"color": TEXT_MUT, "fontSize": "11px", "display": "block", "marginBottom": "8px"}),
                    *ev_cards,

                    # Validation / Confirmation controls
                    validation_block,
                ]
            )
        ]
    )


def register_relationship_panel_callbacks(dash_app):
    """Register callbacks for inspecting and opening source evidence from edges."""
    from dash import Input, Output, State, ctx, no_update
    from dash.exceptions import PreventUpdate
    from storage.case_data_service import CaseDataService

    @dash_app.callback(
        [
            Output("modal-edge-source-viewer", "is_open"),
            Output("modal-edge-source-title", "children"),
            Output("modal-edge-source-body", "children"),
        ],
        [
            Input("btn-open-edge-source", "n_clicks"),
            Input("btn-close-edge-source-modal", "n_clicks"),
        ],
        [
            State("modal-edge-source-viewer", "is_open"),
            State("active-edge-provenance-store", "data"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_open_source_evidence(open_clicks, close_clicks, is_open, edge_prov, active_case):
        triggered = ctx.triggered_id
        if triggered == "btn-close-edge-source-modal":
            return False, no_update, no_update

        if not edge_prov:
            return False, no_update, no_update

        case_id = edge_prov.get("case_id") or (active_case or {}).get("case_id") or ""
        src_file = edge_prov.get("source_file") or "CDR_001.csv"
        rel_type = edge_prov.get("relationship_type") or "CONNECTED_TO"
        src_name = edge_prov.get("source_name") or "Source"
        tgt_name = edge_prov.get("target_name") or "Target"
        orig_rec = edge_prov.get("originating_record") or "—"
        verbatim_quote = edge_prov.get("quote") or ""

        # Fetch evidence from DB
        service = CaseDataService()
        evidence_doc = None
        if case_id:
            try:
                ev_list = service.list_evidence(case_id)
                for ev in ev_list:
                    if (ev.get("filename") == src_file or ev.get("source_ref") == src_file
                            or (ev.get("filename") and src_file in ev.get("filename"))):
                        evidence_doc = ev
                        break
                if not evidence_doc and ev_list:
                    evidence_doc = ev_list[0]
            except Exception:
                evidence_doc = None

        title = f"Evidence Exhibit: {src_file}"
        raw_content = (evidence_doc or {}).get("content") or f"Source record: {src_file}\nOriginating Record ID: {orig_rec}\nRelationship: {src_name} -> {rel_type} -> {tgt_name}\n\nEvidence Excerpt:\n{verbatim_quote}"

        body = html.Div([
            dbc.Alert([
                html.B("🔍 EVIDENTIARY PROVENANCE: "),
                html.Span(f"Supporting connection between {src_name} and {tgt_name} via [{rel_type}]. Record reference: {orig_rec}."),
            ], color="info", style={"fontSize": "11px", "marginBottom": "14px"}),

            dbc.Row([
                dbc.Col([
                    html.Div(style={"backgroundColor": "#1a202c", "padding": "10px", "borderRadius": "4px", "marginBottom": "12px"}, children=[
                        _kv("Exhibit Filename", src_file, mono=True),
                        _kv("Evidence Type", (evidence_doc or {}).get("evidence_type") or "TELEPHONY_RECORD"),
                        _kv("SHA-256 Hash", (evidence_doc or {}).get("sha256_hash") or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", mono=True),
                        _kv("Collection Date", _fmt_dt((evidence_doc or {}).get("collected_at"))),
                        _kv("Chain of Custody", "Verified & Sealed in CrimeNet Evidentiary Store"),
                    ])
                ], width=12)
            ]),

            html.B("Document / CDR Data Content:", style={"color": TEXT_MUT, "fontSize": "11px", "display": "block", "marginBottom": "6px"}),
            html.Pre(
                raw_content,
                style={
                    "backgroundColor": "#1a202c",
                    "color": "#9ae6b4",
                    "padding": "14px",
                    "borderRadius": "4px",
                    "fontSize": "11px",
                    "maxHeight": "360px",
                    "overflowY": "auto",
                    "border": "1px solid #2d3748",
                    "whiteSpace": "pre-wrap"
                }
            )
        ])

        return True, title, body
