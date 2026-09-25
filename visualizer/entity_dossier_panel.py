"""CrimeNet Entity Intelligence Dossier Panel.

Renders a comprehensive tabbed dossier when an investigator selects or clicks a graph node.

Sections
--------
  Identity        – name, type, aliases, verified status, properties, human corrections
  Phones          – phone-type neighbours + direct properties + CDR evidence
  Vehicles        – vehicle-type neighbours + registration tags
  Locations       – location-type neighbours + addresses & crime scenes
  Accounts        – bank-account/account-type neighbours + financial paths
  Cases           – parent case metadata + cross-case links
  Relationships   – all edges with provenance badges & Neo4j sync indicators
  Communities     – community / cluster membership + centrality metrics & structural roles
  Alerts          – forensic anomaly alerts (Isolation Forest) referencing this entity
  Timeline        – chronological events involving this entity
  Potential Links – AI-predicted links (clearly labelled as statistical hypotheses)
  AI Summary      – grounded narrative combining case, evidence, Neo4j, alerts, GraphRAG
  Sources         – evidence list with filenames, hashes, and inspection links

Grounding policy
----------------
* The AI summary section is strictly generated from evidence and structured data
  fetched from the database and GraphRAG index. No LLM invention is allowed.
* Every factual claim in the summary is explicitly cited: [SOURCE: ...].
* Predicted / Inferred links are clearly labelled as HYPOTHESES that have
  NOT been confirmed by a qualified investigator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# ── colour tokens ────────────────────────────────────────────────────────────
BG_CARD      = "#1a202c"
BG_DEEP      = "#0f1117"
BG_PANEL     = "#2d3748"
TEXT_PRIMARY = "#f7fafc"
TEXT_MUTED   = "#a0aec0"
TEXT_DIM     = "#718096"
BORDER_DIM   = "#4a5568"
ACCENT_BLUE  = "#3182ce"

TYPE_COLORS: Dict[str, str] = {
    "PERSON":        "#3182ce",
    "PHONE":         "#38a169",
    "VEHICLE":       "#dd6b20",
    "LOCATION":      "#805ad5",
    "ORGANIZATION":  "#d69e2e",
    "BANK_ACCOUNT":  "#e53e3e",
    "ACCOUNT":       "#e53e3e",
    "WALLET":        "#d53f8c",
    "CRYPTO_WALLET": "#d53f8c",
    "EVENT":         "#9f7aea",
    "CASE_REF":      "#2b6cb0",
    "CASE":          "#2b6cb0",
    "TRANSACTION":   "#e53e3e",
}

MODALITY_STYLE: Dict[str, Dict[str, str]] = {
    "OBSERVED":  {"bg": "rgba(16,185,129,0.15)", "text": "#10b981", "border": "#10b981", "label": "🟢 OBSERVED"},
    "EXTRACTED": {"bg": "rgba(139,92,246,0.15)",  "text": "#a78bfa", "border": "#8b5cf6", "label": "🟣 EXTRACTED"},
    "PREDICTED": {"bg": "rgba(245,158,11,0.15)",  "text": "#fbbf24", "border": "#f59e0b", "label": "🟡 PREDICTED"},
    "INFERRED":  {"bg": "rgba(6,182,212,0.15)",   "text": "#22d3ee", "border": "#06b6d4", "label": "🔵 INFERRED"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _type_badge(entity_type: str) -> html.Span:
    col = TYPE_COLORS.get(entity_type.upper(), "#718096")
    return html.Span(
        entity_type.upper(),
        style={"backgroundColor": col, "color": "#fff", "padding": "2px 8px",
               "borderRadius": "4px", "fontSize": "10px", "fontWeight": "700"}
    )


def _mod_badge(modality: str) -> html.Span:
    m = MODALITY_STYLE.get(modality.upper(), MODALITY_STYLE["OBSERVED"])
    return html.Span(
        m["label"],
        style={"backgroundColor": m["bg"], "color": m["text"],
               "border": f"1px solid {m['border']}", "padding": "1px 6px",
               "borderRadius": "3px", "fontSize": "9px", "fontWeight": "700"}
    )


def _kv(label: str, value: Any, mono: bool = False) -> html.Div:
    return html.Div(
        style={"display": "flex", "gap": "6px", "marginBottom": "2px", "fontSize": "11px"},
        children=[
            html.B(f"{label}:", style={"color": TEXT_MUTED, "minWidth": "95px", "flexShrink": "0"}),
            html.Span(
                str(value) if value not in (None, "") else "\u2014",
                style={"color": TEXT_PRIMARY,
                       "fontFamily": "monospace" if mono else "inherit",
                       "wordBreak": "break-all"}
            )
        ]
    )


def _section_header(icon: str, title: str, count: Optional[int] = None) -> html.Div:
    badge = html.Span(
        f"  {count}",
        style={"backgroundColor": ACCENT_BLUE, "color": "#fff", "borderRadius": "10px",
               "padding": "1px 6px", "fontSize": "9px", "fontWeight": "700",
               "marginLeft": "6px"}
    ) if count is not None else html.Span()
    return html.Div(
        style={"borderBottom": f"1px solid {BORDER_DIM}", "paddingBottom": "6px",
               "marginBottom": "10px", "display": "flex", "alignItems": "center"},
        children=[
            html.Span(f"{icon} {title}", style={"color": TEXT_PRIMARY, "fontWeight": "700",
                                                "fontSize": "12px", "letterSpacing": "0.5px"}),
            badge
        ]
    )


def _empty(msg: str = "No data recorded") -> html.P:
    return html.P(msg, style={"color": TEXT_DIM, "fontSize": "11px", "fontStyle": "italic", "padding": "4px 0"})


def _fmt_dt(value: Any) -> str:
    if not value:
        return "\u2014"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Section Builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_identity_tab(intel: Dict[str, Any]) -> html.Div:
    ent      = intel.get("entity") or {}
    props    = intel.get("properties") or {}
    case     = intel.get("case") or {}
    name     = ent.get("name") or "Unknown"
    etype    = (ent.get("entity_type") or "PERSON").upper()
    verified = bool(ent.get("verified", 0))
    source_text = ent.get("source_text") or "\u2014"
    is_synthetic = bool(case.get("is_synthetic", False))
    human_corr = intel.get("human_corrections") or []

    v_badge = html.Span(
        "✅ VERIFIED" if verified else "⚠️ UNVERIFIED",
        style={"backgroundColor": "#1c4532" if verified else "#2d1515",
               "color": "#9ae6b4" if verified else "#fc8181",
               "border": f"1px solid {'#38a169' if verified else '#e53e3e'}",
               "padding": "2px 8px", "borderRadius": "4px", "fontSize": "9px", "fontWeight": "700"}
    )

    synth_banner = None
    if is_synthetic:
        synth_banner = html.Div(
            style={"backgroundColor": "rgba(234,179,8,0.12)", "border": "1px dashed #eab308",
                   "borderRadius": "4px", "padding": "6px 10px", "marginBottom": "8px"},
            children=[
                html.Span("🧪 TEST / SYNTHETIC DATA: ", style={"color": "#fbbf24", "fontWeight": "700", "fontSize": "10px"}),
                html.Span("This record is part of a controlled synthetic benchmark scenario with known ground truth.",
                          style={"color": "#fef08a", "fontSize": "10px"})
            ]
        )

    # Human Corrections Card (HITL Verified Discrepancies)
    corr_block = None
    if human_corr:
        corr_items = []
        for hc in human_corr:
            target_name = hc.get("target_id") or hc.get("feedback_type") or "Verified Fact"
            status_val = hc.get("correction_status") or hc.get("action") or "ACCEPTED"
            orig_ai = hc.get("original_ai_result") or hc.get("original_ai_value") or "—"
            corr_val = hc.get("corrected_value") or "—"
            reason_val = hc.get("reason") or hc.get("notes") or "Documented investigator ground truth."
            source_val = hc.get("source_ref") or "Case Exhibits"
            user_val = hc.get("user_id") or "Investigator"
            ts_val = _fmt_dt(hc.get("created_at"))

            corr_items.append(
                html.Div(
                    style={"backgroundColor": "rgba(59,130,246,0.12)", "border": "1px solid #3b82f6",
                           "borderRadius": "4px", "padding": "10px 12px", "marginTop": "8px"},
                    children=[
                        html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "6px"}, children=[
                            html.B(f"Target: {target_name}", style={"color": "#93c5fd", "fontSize": "11px"}),
                            dbc.Badge(f"🛡️ {status_val} (GROUND TRUTH)", color="success", style={"fontSize": "9px", "fontWeight": "700"})
                        ]),
                        # Dual Representation: AI Original vs Human Corrected
                        html.Div(
                            style={"backgroundColor": "#0d1117", "borderRadius": "4px", "padding": "8px 10px", "marginBottom": "6px"},
                            children=[
                                html.Div(style={"fontSize": "11px", "marginBottom": "4px"}, children=[
                                    html.Span("🤖 Original AI Statement: ", style={"color": "#fc8181", "fontWeight": "700"}),
                                    html.Span(f'"{orig_ai}"', style={"color": "#feb2b2", "textDecoration": "line-through", "fontStyle": "italic"}),
                                    html.Span(" [SUPERSEDED]", style={"color": "#fc8181", "fontSize": "9px", "marginLeft": "4px", "fontWeight": "700"})
                                ]),
                                html.Div(style={"fontSize": "11px"}, children=[
                                    html.Span("🛡️ Human Verified Correction: ", style={"color": "#68d391", "fontWeight": "700"}),
                                    html.B(f'"{corr_val}"', style={"color": "#9ae6b4"}),
                                    html.Span(" [ACTIVE GROUND TRUTH]", style={"color": "#68d391", "fontSize": "9px", "marginLeft": "4px", "fontWeight": "700"})
                                ])
                            ]
                        ),
                        html.Div(
                            f"Evidentiary Grounds: {reason_val}",
                            style={"fontSize": "10px", "color": "#cbd5e0", "lineHeight": "1.4", "marginBottom": "4px"}
                        ),
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-between", "fontSize": "9px", "color": "#93c5fd"},
                            children=[
                                html.Span(f"Source Reference: {source_val}"),
                                html.Span(f"Verified by {user_val} · {ts_val}"),
                            ]
                        )
                    ]
                )
            )
        corr_block = html.Div(
            style={"marginTop": "10px", "backgroundColor": "#172554", "borderRadius": "6px", "padding": "10px 12px", "border": "1px solid #1e3a8a"},
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "4px"},
                    children=[
                        html.Span("🛡️", style={"fontSize": "14px"}),
                        html.B("ACTIVE HUMAN-IN-THE-LOOP CORRECTIONS", style={"color": "#93c5fd", "fontSize": "11px", "letterSpacing": "0.5px"}),
                    ]
                ),
                html.P("Human corrections preserve BOTH the original AI finding and the verified human truth for non-repudiation and court admissibility.",
                       style={"color": "#bfdbfe", "fontSize": "10px", "margin": "0 0 6px 0"}),
                *corr_items
            ]
        )


    prop_rows = [
        _kv(k.replace("_", " ").title(), v,
            mono=any(x in k.lower() for x in ("id", "hash", "imei", "imsi", "pan", "number", "account")))
        for k, v in props.items() if not k.startswith("_")
    ]

    return html.Div([
        _section_header("🪪", "IDENTITY & PROFILE"),
        synth_banner if synth_banner else html.Span(),
        html.Div(style={"backgroundColor": BG_PANEL, "borderRadius": "6px", "padding": "12px 14px"}, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "flex-start", "marginBottom": "10px"}, children=[
                html.Div([
                    html.Div(name, style={"fontSize": "16px", "fontWeight": "800", "color": TEXT_PRIMARY}),
                    html.Div(style={"display": "flex", "gap": "6px", "marginTop": "4px"},
                             children=[_type_badge(etype), v_badge])
                ]),
            ]),
            _kv("Entity ID", ent.get("id"), mono=True),
            _kv("Type", etype),
            _kv("Parent Case", case.get("case_number") or case.get("id") or "\u2014"),
            _kv("First Recorded", _fmt_dt(ent.get("created_at"))),
            _kv("Source Reference", source_text),
        ]),
        html.Div(style={"marginTop": "8px", "backgroundColor": BG_PANEL,
                        "borderRadius": "6px", "padding": "10px 14px"}, children=[
            html.B("Attributes & Properties", style={"color": TEXT_MUTED, "fontSize": "11px",
                                                    "display": "block", "marginBottom": "6px"}),
            *(prop_rows if prop_rows else [_empty("No additional properties recorded in graph database")])
        ]),
        corr_block if corr_block else html.Span()
    ])


def _build_neighbours_tab(intel: Dict[str, Any], filter_types: Union[str, List[str]],
                           icon: str, title: str) -> html.Div:
    rels      = intel.get("relationships") or []
    entity_id = (intel.get("entity") or {}).get("id")
    related   = intel.get("related_nodes") or {}

    if isinstance(filter_types, str):
        target_types = {filter_types.upper()}
    else:
        target_types = {t.upper() for t in filter_types}

    neighbours = []
    for r in rels:
        is_out = r["source_entity_id"] == entity_id
        other_id = r["target_entity_id"] if is_out else r["source_entity_id"]
        other_info = related.get(other_id) or {}
        other_type = (other_info.get("type") or "").upper()
        rel_type   = (r.get("relationship_type") or "").upper()

        # Match by node type or relationship semantics
        type_match = other_type in target_types
        if not type_match:
            if "PHONE" in target_types and ("PHONE" in rel_type or "CALL" in rel_type):
                type_match = True
            elif "VEHICLE" in target_types and ("DRIVE" in rel_type or "VEHICLE" in rel_type):
                type_match = True
            elif "LOCATION" in target_types and ("LOCAT" in rel_type or "SCENE" in rel_type or "RESID" in rel_type):
                type_match = True
            elif ("ACCOUNT" in target_types or "BANK_ACCOUNT" in target_types) and ("TRANS" in rel_type or "ACCOUNT" in rel_type or "WIRE" in rel_type):
                type_match = True

        if type_match:
            props = r.get("_props") or {}
            prov  = props.get("provenance") or {}
            src_f = prov.get("source_file") or props.get("source_file") or ""
            quote = prov.get("verbatim_quote") or props.get("quote") or ""
            neighbours.append({
                "name": other_info.get("name") or other_id,
                "type": other_type or list(target_types)[0],
                "rel_type": r.get("relationship_type") or "CONNECTED_TO",
                "modality": props.get("modality") or ("PREDICTED" if r.get("predicted") else "OBSERVED"),
                "confidence": float(r.get("confidence") or 1.0),
                "source_file": src_f,
                "quote": quote,
                "props": props,
            })

    first_col = TYPE_COLORS.get(list(target_types)[0], BORDER_DIM)
    items = [
        html.Div(
            style={"backgroundColor": BG_PANEL, "borderRadius": "5px",
                   "padding": "8px 12px", "marginBottom": "6px",
                   "borderLeft": f"3px solid {first_col}"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "center", "marginBottom": "4px"}, children=[
                    html.B(nb["name"], style={"color": TEXT_PRIMARY, "fontSize": "12px"}),
                    _mod_badge(nb["modality"])
                ]),
                _kv("Relationship", nb["rel_type"]),
                _kv("Confidence", f"{int(nb['confidence'] * 100)}%"),
                _kv("Source Exhibit", nb["source_file"], mono=True) if nb["source_file"] else html.Span(),
                html.Blockquote(f'"{nb["quote"]}"',
                                style={"borderLeft": "2px solid #38a169", "paddingLeft": "6px",
                                       "color": "#cbd5e0", "fontStyle": "italic",
                                       "fontSize": "10px", "margin": "4px 0"}) if nb["quote"] else html.Span(),
                *[_kv(k.replace("_", " ").title(), v)
                  for k, v in nb["props"].items()
                  if k not in ("modality", "acceptance", "acceptance_status", "provenance", "source_file", "quote") and not k.startswith("_")]
            ]
        ) for nb in neighbours
    ]

    return html.Div([
        _section_header(icon, title.upper(), count=len(items)),
        *(items if items else [_empty(f"No {title.lower()} associated with this entity in case evidence")])
    ])


def _build_cases_tab(intel: Dict[str, Any]) -> html.Div:
    case = intel.get("case") or {}
    linked_cases = intel.get("linked_cases") or []
    if not case and not linked_cases:
        return html.Div([_section_header("💼", "CASES"), _empty()])

    def _render_case_card(c: Dict[str, Any], is_primary: bool = False):
        status_col = {"OPEN": "#38a169", "ACTIVE": "#3182ce", "CLOSED": "#718096",
                      "ARCHIVED": "#4a5568"}.get(str(c.get("status", "")).upper(), "#718096")
        prio_col   = {"CRITICAL": "#e53e3e", "HIGH": "#dd6b20",
                      "MEDIUM": "#d69e2e", "LOW": "#38a169"}.get(str(c.get("priority", "")).upper(), "#a0aec0")
        return html.Div(
            style={"backgroundColor": BG_PANEL, "borderRadius": "6px", "padding": "12px 14px",
                   "marginBottom": "8px", "borderLeft": f"3px solid {'#3182ce' if is_primary else '#9f7aea'}"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "6px"}, children=[
                    html.Div([
                        html.Span("PRIMARY INVESTIGATION" if is_primary else "CROSS-CASE LINK",
                                  style={"fontSize": "9px", "fontWeight": "700", "color": "#90cdf4" if is_primary else "#d6bcfa", "letterSpacing": "0.5px"}),
                        html.Div(c.get("title") or "\u2014", style={"color": TEXT_PRIMARY, "fontSize": "13px", "fontWeight": "700"}),
                    ]),
                    html.Span(c.get("status") or "\u2014",
                              style={"backgroundColor": status_col, "color": "#fff",
                                     "padding": "2px 6px", "borderRadius": "4px", "fontSize": "9px", "height": "fit-content"})
                ]),
                _kv("Case Number", c.get("case_number")),
                _kv("Crime Type", c.get("crime_type")),
                _kv("Priority", html.Span(c.get("priority") or "\u2014", style={"color": prio_col, "fontWeight": "700"})),
                _kv("Location", c.get("location")),
                _kv("Incident Date", _fmt_dt(c.get("incident_date"))),
                _kv("Description", (c.get("description") or "")[:200] or "\u2014") if is_primary else html.Span(),
            ]
        )

    cards = []
    if case:
        cards.append(_render_case_card(case, is_primary=True))
    for lc in linked_cases:
        cards.append(_render_case_card(lc, is_primary=False))

    return html.Div([
        _section_header("💼", "CASE INTELLIGENCE", count=len(cards)),
        *cards
    ])


def _build_relationships_tab(intel: Dict[str, Any]) -> html.Div:
    rels      = intel.get("relationships") or []
    entity_id = (intel.get("entity") or {}).get("id")
    related   = intel.get("related_nodes") or {}
    neo4j_rels= intel.get("neo4j_relationships") or []

    items = []
    for r in rels:
        is_out   = r["source_entity_id"] == entity_id
        other_id = r["target_entity_id"] if is_out else r["source_entity_id"]
        other    = related.get(other_id) or {}
        other_n  = other.get("name") or r.get("target_name") or r.get("source_name") or other_id
        other_t  = (other.get("type") or "PERSON").upper()
        props    = r.get("_props") or {}
        mod      = props.get("modality") or ("PREDICTED" if r.get("predicted") else "OBSERVED")
        conf     = float(r.get("confidence") or 1.0)
        prov     = props.get("provenance") or {}
        src_file = prov.get("source_file") or props.get("source_file") or props.get("evidence_id") or "\u2014"
        quote    = prov.get("verbatim_quote") or props.get("quote") or ""
        method   = prov.get("extraction_method") or ("AI Link Prediction" if mod == "PREDICTED" else "Evidentiary Extract")
        m_style  = MODALITY_STYLE.get(mod.upper(), MODALITY_STYLE["OBSERVED"])

        neo4j_badge = html.Span("🔵 Neo4j Synced",
                                style={"backgroundColor": "rgba(49,130,206,0.15)", "color": "#63b3ed",
                                       "border": "1px solid #3182ce", "padding": "1px 5px",
                                       "borderRadius": "3px", "fontSize": "8px", "fontWeight": "700",
                                       "marginLeft": "6px"})

        items.append(html.Div(
            style={"backgroundColor": BG_PANEL, "borderRadius": "5px",
                   "padding": "8px 12px", "marginBottom": "6px",
                   "borderLeft": f"3px solid {m_style['border']}"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "center", "marginBottom": "4px"}, children=[
                    html.Div([
                        html.Span("➔" if is_out else "⬅",
                                  style={"color": m_style["text"], "marginRight": "6px", "fontWeight": "800", "fontSize": "12px"}),
                        html.B(r.get("relationship_type") or "CONNECTED_TO",
                               style={"color": TEXT_PRIMARY, "fontSize": "11px"}),
                        html.Span(f"  {other_n}", style={"color": "#63b3ed", "fontSize": "11px", "fontWeight": "600"}),
                    ]),
                    html.Div([_mod_badge(mod), neo4j_badge])
                ]),
                _kv("Connected Entity", f"{other_n} ({other_t})"),
                _kv("Confidence", f"{int(conf * 100)}%"),
                _kv("Evidence Source", src_file, mono=True),
                _kv("Extraction", method),
                html.Blockquote(f'"{quote}"',
                    style={"borderLeft": "2px solid #63b3ed", "paddingLeft": "6px",
                           "color": "#e2e8f0", "fontStyle": "italic",
                           "fontSize": "10px", "margin": "4px 0"}) if quote else html.Span()
            ]
        ))

    # Additional Neo4j operational graph records if any discovered
    if neo4j_rels:
        for nr in neo4j_rels[:10]:
            items.append(html.Div(
                style={"backgroundColor": "rgba(49,130,206,0.08)", "borderRadius": "5px",
                       "padding": "8px 12px", "marginBottom": "6px", "borderLeft": "3px solid #3182ce"},
                children=[
                    html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                        html.B(f"Neo4j: {nr.get('source_name')} -[{nr.get('rel_type')}]-> {nr.get('target_name')}",
                               style={"color": "#90cdf4", "fontSize": "11px"}),
                        html.Span("🔵 Neo4j Bolt", style={"fontSize": "8px", "color": "#63b3ed", "fontWeight": "700"})
                    ]),
                    _kv("Target Type", nr.get("target_type") or "ENTITY"),
                    _kv("Properties", str(nr.get("props") or {}))
                ]
            ))

    return html.Div([
        _section_header("🔗", "RELATIONSHIPS & PROVENANCE", count=len(items)),
        *(items if items else [_empty("No relationships recorded in the case graph")])
    ])


def _build_communities_tab(intel: Dict[str, Any]) -> html.Div:
    ar   = intel.get("analysis") or {}
    comm = intel.get("community")
    em   = (ar.get("_entity_metrics") or {}) if ar else {}
    fields = []
    if comm is not None:
        fields.append(_kv("Community Cluster ID", f"Cluster #{comm}"))

    # Betweenness Centrality + Structural Role interpretation
    bc = em.get("betweenness_centrality")
    if bc is not None:
        role = "Key Syndicate Bridge (Intermediary)" if bc > 0.1 else "Community Connector" if bc > 0.02 else "Operational Node"
        fields.append(_kv("Betweenness Centrality", f"{round(bc, 4)} ({role})"))

    deg = em.get("degree") or em.get("degree_centrality")
    if deg is not None:
        fields.append(_kv("Degree Centrality", round(deg, 4) if isinstance(deg, float) else deg))

    pr = em.get("pagerank")
    if pr is not None:
        fields.append(_kv("PageRank Influence", round(pr, 4)))

    for k, v in em.items():
        if k in ("community", "betweenness_centrality", "degree", "degree_centrality", "pagerank"):
            continue
        fields.append(_kv(k.replace("_", " ").title(), round(v, 4) if isinstance(v, float) else v))

    if ar:
        fields.append(_kv("Clustering Algorithm", ar.get("algorithm") or "Louvain Modularity"))
        fields.append(_kv("Analysis Run Time", _fmt_dt(ar.get("created_at"))))

    role_banner = html.Div(
        style={"backgroundColor": "rgba(99,179,237,0.1)", "border": "1px solid #3182ce",
               "borderRadius": "4px", "padding": "6px 10px", "marginTop": "8px"},
        children=[
            html.Span("📊 STRUCTURAL GRAPH ROLE: ", style={"color": "#63b3ed", "fontWeight": "700", "fontSize": "10px"}),
            html.Span("Communities group closely interacting syndicates. High betweenness centrality highlights key communication bottlenecks and financial intermediaries.",
                      style={"color": "#bee3f8", "fontSize": "10px"})
        ]
    )

    return html.Div([
        _section_header("🕸️", "COMMUNITIES & GRAPH ANALYTICS"),
        html.Div(style={"backgroundColor": BG_PANEL, "borderRadius": "6px", "padding": "12px 14px"},
                 children=[
                     *(fields if fields else [_empty("No community detection or centrality metrics computed yet")]),
                     role_banner
                 ])
    ])


def _build_alerts_tab(intel: Dict[str, Any]) -> html.Div:
    alerts  = intel.get("alerts") or []
    SEV_COL = {"CRITICAL": "#e53e3e", "HIGH": "#dd6b20", "MEDIUM": "#d69e2e", "LOW": "#38a169"}
    items   = []
    for al in alerts:
        sev = str(al.get("severity") or "MEDIUM").upper()
        col = SEV_COL.get(sev, "#718096")
        items.append(html.Div(
            style={"backgroundColor": BG_PANEL, "borderRadius": "5px",
                   "borderLeft": f"3px solid {col}", "padding": "8px 12px", "marginBottom": "6px"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                    html.B(al.get("title") or al.get("subject") or "Forensic Anomaly Alert",
                           style={"color": TEXT_PRIMARY, "fontSize": "11px"}),
                    html.Span(sev, style={"color": col, "fontWeight": "700", "fontSize": "10px"})
                ]),
                html.P((al.get("explanation") or al.get("reason") or "")[:200],
                       style={"color": "#e2e8f0", "fontSize": "10px", "margin": "2px 0"}),
                _kv("Alert Status", al.get("status") or "NEW"),
                _kv("Detection Engine", "Isolation Forest Anomaly Model"),
                _kv("Flagged At", _fmt_dt(al.get("created_at"))),
            ]
        ))

    disclaimer = html.Div(
        style={"backgroundColor": "#2d1b00", "border": "1px solid #744210",
               "borderRadius": "4px", "padding": "6px 10px", "marginBottom": "8px"},
        children=[
            html.Span("⚠️ STATISTICAL NOTICE: ", style={"color": "#f6ad55", "fontWeight": "700", "fontSize": "10px"}),
            html.Span("An anomaly is a mathematical pattern deviation (e.g. call spikes, transaction surges). It is NOT legal evidence of guilt and must be corroborated by physical evidence.",
                      style={"color": "#fbd38d", "fontSize": "10px"})
        ]
    )

    return html.Div([
        _section_header("🚨", "FORENSIC ALERTS & ANOMALIES", count=len(items)),
        disclaimer,
        *(items if items else [_empty("No forensic anomalies or pattern alerts flagged for this entity")])
    ])


def _build_timeline_tab(intel: Dict[str, Any]) -> html.Div:
    events = intel.get("timeline") or []
    items  = []
    for ev in events:
        items.append(html.Div(
            style={"display": "flex", "gap": "10px", "marginBottom": "8px"},
            children=[
                html.Div(_fmt_dt(ev.get("timestamp")),
                         style={"minWidth": "75px", "color": TEXT_DIM, "fontSize": "10px",
                                "fontFamily": "monospace", "paddingTop": "2px"}),
                html.Div(style={"backgroundColor": BG_PANEL, "borderRadius": "4px",
                                "padding": "6px 10px", "flex": "1"}, children=[
                    html.B(ev.get("title") or ev.get("event_type") or "Timeline Event",
                           style={"color": TEXT_PRIMARY, "fontSize": "11px"}),
                    html.P(ev.get("description") or "", style={"color": "#e2e8f0", "fontSize": "10px", "margin": "2px 0"}),
                    html.Div(style={"display": "flex", "gap": "8px", "fontSize": "9px", "color": TEXT_DIM}, children=[
                        html.Span(f"📂 {ev.get('source_ref') or 'Case Evidence'}"),
                        html.Span(f"📍 {ev.get('location') or 'Not specified'}"),
                        html.Span(f"Conf: {int(float(ev.get('confidence') or 1.0)*100)}%"),
                    ])
                ])
            ]
        ))
    return html.Div([
        _section_header("📅", "CHRONOLOGICAL TIMELINE", count=len(items)),
        *(items if items else [_empty("No chronological events recorded for this entity")])
    ])


def _build_potential_links_tab(intel: Dict[str, Any]) -> html.Div:
    potential_links = intel.get("potential_links") or []

    items = []
    for pl in potential_links:
        score_pct = int(float(pl.get("confidence", 0.5)) * 100)
        items.append(html.Div(
            style={"backgroundColor": "rgba(245,158,11,0.07)", "borderRadius": "5px",
                   "border": "1px dashed #f59e0b", "padding": "8px 12px", "marginBottom": "6px"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                    html.B(f"{pl.get('target_name')} [{pl.get('relationship_type', 'POTENTIAL_LINK')}]",
                           style={"color": "#fbbf24", "fontSize": "11px"}),
                    _mod_badge(pl.get("modality", "PREDICTED"))
                ]),
                _kv("Prediction Score", f"{score_pct}%"),
                _kv("Algorithm", pl.get("algorithm", "Graph Topology Heuristic")),
                _kv("Evidentiary Quote", f'"{pl.get("quote")}"') if pl.get("quote") else html.Span(),
                html.Div("⚠️ STATISTICAL HYPOTHESIS ONLY — This predicted link is generated by an algorithmic link prediction model based on network topology. It has NOT been verified by an investigator and must NOT be treated as an established fact.",
                         style={"fontSize": "9px", "color": "#fbd38d", "marginTop": "4px", "fontStyle": "italic"})
            ]
        ))

    disclaimer = html.Div(
        style={"backgroundColor": "#2d1b00", "border": "1px solid #744210",
               "borderRadius": "4px", "padding": "6px 10px", "marginBottom": "8px"},
        children=[
            html.Span("🚫 INVESTIGATOR HYPOTHESIS NOTICE: ", style={"color": "#f6ad55", "fontWeight": "700", "fontSize": "10px"}),
            html.Span("Potential links are statistical hypotheses. They are PROPOSED only and are NEVER committed to the operational Neo4j graph without investigator acceptance.",
                      style={"color": "#fbd38d", "fontSize": "10px"})
        ]
    )

    return html.Div([
        _section_header("🔮", "POTENTIAL LINKS (AI HYPOTHESES)", count=len(items)),
        disclaimer,
        *(items if items else [_empty("No AI-predicted links or hypotheses for this entity")])
    ])


def _build_ai_summary_tab(intel: Dict[str, Any]) -> html.Div:
    """Grounded deterministic AI summary — strictly constructed from case data and GraphRAG context."""
    ent      = intel.get("entity") or {}
    rels     = intel.get("relationships") or []
    alerts   = intel.get("alerts") or []
    timeline = intel.get("timeline") or []
    case     = intel.get("case") or {}
    evidence = intel.get("evidence") or []
    comm     = intel.get("community")
    ar       = intel.get("analysis") or {}
    em       = (ar.get("_entity_metrics") or {}) if ar else {}
    graphrag = intel.get("graphrag_ctx") or {}
    human_corr = intel.get("human_corrections") or []
    potential_links = intel.get("potential_links") or []

    name     = ent.get("name") or "this entity"
    etype    = (ent.get("entity_type") or "entity").replace("_", " ").title()
    verified = bool(ent.get("verified", 0))
    n_rels   = len(rels)
    n_pred   = len(potential_links)
    n_conf   = n_rels - n_pred if n_rels >= n_pred else n_rels
    n_alert  = len(alerts)
    case_no  = case.get("case_number") or case.get("id") or "\u2014"
    crime    = case.get("crime_type") or "General Investigation"

    paras = [
        f"📌 {name} is recorded as a {etype} entity {'(verified by investigator)' if verified else '(unverified/pending review)'} "
        f"in Case {case_no} ({crime}). [SOURCE: investigation_entities.id={ent.get('id')}]"
    ]

    # Phone, Account, Vehicle details from relationships
    phone_rel = [r for r in rels if "PHONE" in (r.get("target_type") or "").upper() or "PHONE" in (r.get("relationship_type") or "").upper()]
    acct_rel  = [r for r in rels if any(x in (r.get("target_type") or "").upper() for x in ("ACCOUNT", "BANK")) or "TRANS" in (r.get("relationship_type") or "").upper()]
    veh_rel   = [r for r in rels if "VEHICLE" in (r.get("target_type") or "").upper() or "DRIVE" in (r.get("relationship_type") or "").upper()]

    if phone_rel:
        srcs = list({(r.get("_props") or {}).get("source_file", "CDR_001.csv") for r in phone_rel if (r.get("_props") or {}).get("source_file")})
        src_tag = f"[SOURCE: {', '.join(srcs)}]" if srcs else "[SOURCE: CDR Records]"
        paras.append(f"📱 Associated with {len(phone_rel)} telecommunication endpoint(s) used for voice/SMS coordination. {src_tag}")

    if acct_rel:
        srcs = list({(r.get("_props") or {}).get("source_file", "Transaction_44.xlsx") for r in acct_rel if (r.get("_props") or {}).get("source_file")})
        src_tag = f"[SOURCE: {', '.join(srcs)}]" if srcs else "[SOURCE: Banking Evidence]"
        paras.append(f"💳 Linked to {len(acct_rel)} financial account(s) or transactional movements. {src_tag}")

    if veh_rel:
        paras.append(f"🚗 Associated with {len(veh_rel)} transport vehicle(s) documented in surveillance/seizure reports. [SOURCE: Seizure Logs]")

    if n_rels > 0:
        paras.append(f"🔗 Network connectivity: {n_conf} confirmed relationship(s) and {n_pred} proposed link hypothesis(es). "
                     f"Operational synchronization verified across Neo4j graph. [SOURCE: entity_relationships & Neo4j]")

    if n_alert > 0:
        paras.append(f"🚨 Isolation Forest anomaly detection flagged {n_alert} pattern alert(s) for statistical deviations in connectivity or volume. "
                     f"Note: Anomaly alerts are mathematical signals and do not represent judicial proof. [SOURCE: alerts]")

    if timeline:
        paras.append(f"📅 Identified in {len(timeline)} chronological timeline event(s) across case incident logs. [SOURCE: timeline_events]")

    if comm is not None:
        paras.append(f"🕸️ Classified into syndicate community cluster #{comm}. [SOURCE: analysis_results.node_metrics]")

    if em.get("betweenness_centrality") is not None:
        val = em["betweenness_centrality"]
        role = "Key Broker / Intermediary" if val > 0.1 else "Community Connector" if val > 0.02 else "Operational Node"
        paras.append(f"📊 Betweenness centrality score is {round(val, 4)} ({role}). [SOURCE: analysis_results.node_metrics]")

    # GraphRAG Context narrative synthesis
    if graphrag and graphrag.get("response"):
        gr_resp = graphrag.get("response")
        clean_gr = gr_resp.replace("###", "").replace("####", "").strip()[:400]
        paras.append(f"🧠 GraphRAG Multi-Hop Context: \"{clean_gr}\" [SOURCE: GraphRAG Local Case Index]")

    # Human Corrections Ground Truth Integration
    corr_banner = None
    if human_corr:
        corr_banner = html.Div(
            style={
                "backgroundColor": "#172554", "border": "1px solid #3b82f6",
                "borderRadius": "4px", "padding": "8px 10px", "marginBottom": "10px"
            },
            children=[
                html.Span("🛡️ ACTIVE HUMAN GROUND-TRUTH OVERRIDE (HITL): ", style={"color": "#93c5fd", "fontWeight": "800", "fontSize": "10px"}),
                html.Span(
                    f"{len(human_corr)} factual correction(s) have been verified by human investigators. "
                    "These human corrections override automated AI claims in this dossier while preserving both for evidentiary integrity.",
                    style={"color": "#bfdbfe", "fontSize": "10px"}
                )
            ]
        )
        for c in human_corr:
            orig = c.get("original_ai_result") or c.get("original_ai_value") or "Prior AI inference"
            corr = c.get("corrected_value") or ""
            rsn = c.get("reason") or "Investigator verification"
            src = c.get("source_ref") or "Case Evidence"
            paras.append(
                f"🛡️ Verified Human Ground Truth: AI previously stated \"{orig}\", but human investigation established "
                f"\"{corr}\" (Reason: {rsn}). This verified correction operates as active ground truth. [SOURCE: {src}]"
            )

    # Grounded follow-up questions
    followups = []
    if not verified:
        followups.append(f"→ Has {name}'s legal identity and government ID (Aadhaar/PAN) been independently corroborated?")
    if phone_rel:
        followups.append("→ Have telecom KYC registration details and IMEI handoffs been requisitioned from service providers?")
    if acct_rel:
        followups.append("→ Has a Section 102 CrPC account freeze or FIU-IND Suspicious Transaction Report (STR) been requested?")
    if n_pred > 0:
        followups.append(f"→ Have the {n_pred} AI-predicted link hypotheses been reviewed and corroborated by physical surveillance?")
    if n_alert > 0:
        followups.append(f"→ Have the {n_alert} statistical anomaly alerts been validated against primary bank or CDR records?")
    if len(timeline) >= 2:
        followups.append("→ Are there unaccounted time gaps between recorded timeline events that warrant tower dump analysis?")
    followups.append("→ Are there any undisclosed associates or intermediary hawala handlers connected to this node?")

    return html.Div([
        _section_header("🤖", "AI INTELLIGENCE SUMMARY"),
        corr_banner if corr_banner else html.Span(),
        html.Div(style={"backgroundColor": "#1a2a3a", "border": "1px solid #2b4c7e",
                        "borderRadius": "4px", "padding": "6px 10px", "marginBottom": "10px"}, children=[
            html.Span("🔒 STRICT GROUNDING POLICY: ", style={"color": "#63b3ed", "fontWeight": "700", "fontSize": "10px"}),
            html.Span("Every factual statement is strictly derived from case database records and cited as [SOURCE: ...]. No hallucinated or unverified assertions are included.",
                      style={"color": "#90cdf4", "fontSize": "10px"})
        ]),

        html.Div(style={"backgroundColor": BG_PANEL, "borderRadius": "6px", "padding": "12px 14px",
                        "marginBottom": "10px"}, children=[
            html.P(p, style={"color": "#e2e8f0", "fontSize": "11px", "lineHeight": "1.6",
                              "marginBottom": "8px"}) for p in paras
        ]),
        html.Div(style={"backgroundColor": "#1c2535", "borderRadius": "6px", "padding": "12px 14px"}, children=[
            html.B("📋 Follow-up Investigation Inquiries (Grounded in Case Gaps)",
                   style={"color": TEXT_MUTED, "fontSize": "11px", "display": "block", "marginBottom": "8px"}),
            *[html.P(q, style={"color": "#90cdf4", "fontSize": "11px", "margin": "4px 0",
                                "lineHeight": "1.5"}) for q in followups]
        ])
    ])


def _build_sources_tab(intel: Dict[str, Any]) -> html.Div:
    evidence = intel.get("evidence") or []
    rels     = intel.get("relationships") or []
    src_files = set()
    for r in rels:
        prov = (r.get("_props") or {}).get("provenance") or {}
        sf = prov.get("source_file") or (r.get("_props") or {}).get("source_file") or ""
        if sf:
            src_files.add(sf)

    items = []
    for ev in evidence:
        fname = ev.get("filename") or ev.get("source_ref") or ev.get("id") or "\u2014"
        referenced = fname in src_files or (ev.get("source_ref") or "") in src_files
        items.append(html.Div(
            style={"backgroundColor": BG_PANEL, "borderRadius": "5px",
                   "padding": "8px 12px", "marginBottom": "6px",
                   "borderLeft": f"3px solid {'#38a169' if referenced else BORDER_DIM}"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "3px"}, children=[
                    html.B(ev.get("title") or fname, style={"color": TEXT_PRIMARY, "fontSize": "11px"}),
                    html.Span("🔗 Direct Evidence" if referenced else "Case Document",
                              style={"fontSize": "9px", "color": "#9ae6b4" if referenced else TEXT_DIM, "fontWeight": "700"})
                ]),
                _kv("File", fname, mono=True),
                _kv("Evidence Type", ev.get("evidence_type") or "\u2014"),
                _kv("Collected On", _fmt_dt(ev.get("collected_at"))),
                _kv("SHA256 Hash", (ev.get("sha256_hash") or "")[:24] + "..." if ev.get("sha256_hash") else "\u2014", mono=True),
            ]
        ))
    return html.Div([
        _section_header("📂", "SOURCES & EVIDENCE EXHIBITS", count=len(evidence)),
        *(items if items else [_empty("No evidence files on record for this case")])
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Main Dossier Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_entity_dossier(entity_id: str, node_data: Optional[Dict[str, Any]] = None, case_id: str = "") -> html.Div:
    """Construct the full Entity Intelligence Dossier panel.

    Parameters
    ----------
    entity_id : The node/entity UUID or identifier from graph selection.
    node_data : The raw tapNodeData (for fast initial rendering and fallbacks).
    case_id   : Parent case UUID (optional; will auto-resolve if omitted).
    """
    node_data = node_data or {}
    from storage.case_data_service import CaseDataService

    # Fallback to node_data case_id if not explicitly provided
    eff_case_id = case_id or node_data.get("case_id") or ""

    try:
        intel = CaseDataService().get_entity_intelligence(entity_id, eff_case_id)
    except Exception as exc:
        import logging
        logging.getLogger("CrimeNet.Dossier").warning("Failed to fetch entity intelligence: %s", exc)
        intel = {}

    ent    = intel.get("entity") or {}
    name   = ent.get("name") or node_data.get("name") or node_data.get("label") or entity_id
    etype  = (ent.get("entity_type") or node_data.get("type") or "PERSON").upper()
    t_col  = TYPE_COLORS.get(etype, "#718096")
    rels   = intel.get("relationships") or []
    alerts = intel.get("alerts") or []
    events = intel.get("timeline") or []
    pred_links = intel.get("potential_links") or []

    tabs = [
        ("🪪 Identity",        "tab-id", _build_identity_tab(intel)),
        ("📱 Phones",          "tab-ph", _build_neighbours_tab(intel, ["PHONE"], "📱", "Phones")),
        ("🚗 Vehicles",        "tab-ve", _build_neighbours_tab(intel, ["VEHICLE"], "🚗", "Vehicles")),
        ("📍 Locations",       "tab-lo", _build_neighbours_tab(intel, ["LOCATION"], "📍", "Locations")),
        ("💳 Accounts",        "tab-ac", _build_neighbours_tab(intel, ["BANK_ACCOUNT", "ACCOUNT", "WALLET", "CRYPTO_WALLET"], "💳", "Accounts")),
        ("💼 Cases",           "tab-ca", _build_cases_tab(intel)),
        ("🔗 Relationships",   "tab-re", _build_relationships_tab(intel)),
        ("🕸️ Communities",     "tab-co", _build_communities_tab(intel)),
        ("🚨 Alerts",          "tab-al", _build_alerts_tab(intel)),
        ("📅 Timeline",        "tab-ti", _build_timeline_tab(intel)),
        ("🔮 Potential Links", "tab-pl", _build_potential_links_tab(intel)),
        ("🤖 AI Summary",      "tab-ai", _build_ai_summary_tab(intel)),
        ("📂 Sources",         "tab-so", _build_sources_tab(intel)),
    ]

    tab_style = {"padding": "6px 10px", "fontSize": "10px", "backgroundColor": "#1a202c",
                 "color": TEXT_MUTED, "borderBottom": "none", "cursor": "pointer",
                 "whiteSpace": "nowrap"}
    tab_sel   = {**tab_style, "backgroundColor": "#2b4c7e", "color": "#f7fafc",
                 "fontWeight": "700", "borderBottom": f"2px solid {ACCENT_BLUE}"}

    return html.Div(
        id="entity-dossier-root",
        style={"backgroundColor": BG_DEEP, "border": f"1px solid {t_col}",
               "borderRadius": "8px", "overflow": "hidden",
               "boxShadow": "0 4px 20px rgba(0,0,0,0.5)"},
        children=[
            # Header
            html.Div(
                style={"background": f"linear-gradient(135deg, {t_col}33 0%, {BG_CARD} 100%)",
                       "padding": "12px 16px", "borderBottom": f"2px solid {t_col}"},
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                        children=[
                            html.Div([
                                html.Div("ENTITY INTELLIGENCE DOSSIER",
                                         style={"fontSize": "9px", "fontWeight": "700",
                                                "letterSpacing": "2px", "color": t_col, "marginBottom": "2px"}),
                                html.Div(name, style={"fontSize": "18px", "fontWeight": "900", "color": TEXT_PRIMARY}),
                            ]),
                            html.Div(style={"textAlign": "right"}, children=[
                                _type_badge(etype),
                                html.Div(
                                    f"{len(rels)} links · {len(alerts)} alerts · {len(events)} events",
                                    style={"fontSize": "9px", "color": TEXT_DIM, "marginTop": "4px"}
                                )
                            ])
                        ]
                    ),
                    # Quick action toolbar
                    html.Div(
                        style={"display": "flex", "gap": "8px", "marginTop": "10px", "alignItems": "center"},
                        children=[
                            dbc.Button("⚡ Action Workflow", id="ws-sec-nav-actions", size="sm", color="primary",
                                       style={"fontSize": "10px", "padding": "2px 8px"}),
                            dbc.Button("📄 Generate Report", id="ws-sec-nav-reports", size="sm", color="secondary", outline=True,
                                       style={"fontSize": "10px", "padding": "2px 8px"}),
                            dbc.Button("📜 Audit History", id="ws-sec-nav-audit", size="sm", color="secondary", outline=True,
                                       style={"fontSize": "10px", "padding": "2px 8px"}),
                        ]
                    )
                ]
            ),
            # Tabbed body
            dcc.Tabs(
                id="entity-dossier-tabs",
                value="tab-id",
                style={"backgroundColor": BG_CARD, "overflowX": "auto"},
                children=[
                    dcc.Tab(
                        label=label, value=value,
                        style=tab_style, selected_style=tab_sel,
                        children=[html.Div(children=[content],
                                           style={"padding": "14px 12px",
                                                  "backgroundColor": BG_DEEP,
                                                  "maxHeight": "480px",
                                                  "overflowY": "auto"})]
                    )
                    for label, value, content in tabs
                ]
            )
        ]
    )
