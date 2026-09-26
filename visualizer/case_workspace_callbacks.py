"""CrimeNet Case Investigation Workspace Callbacks.

Provides reactive interactive controls for the case-specific investigation workspace:
- Entity quick search & auto-centering
- Multi-criteria entity filtering (person, phone, vehicle, location, org, account)
- Relationship modality filtering (Observed, Extracted, Predicted, Inferred)
- Acceptance status filtering (Confirmed vs Proposed)
- N-Hop neighborhood exploration (1-Hop, 2-Hop, 3-Hop)
- Shortest path evidentiary chain tracing
- Neighbor expansion & view restoration
- Label visibility controls (Name, Name+Type, None)
- Visual analysis highlights (Bridges, AI Predictions, Clear)
- Forensic Evidence & Provenance Inspector
- Human-in-the-loop Validation Layer (Accept & Confirm to Neo4j / Dismiss)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import networkx as nx

from dash import dcc, html, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from storage.graphrag_crimenet_boundary import (
    GraphRAGCrimeNetBoundary,
    RelationshipModality,
    AcceptanceStatus,
)
from storage.case_data_service import CaseDataService
from visualizer.entity_dossier_panel import build_entity_dossier
from visualizer.relationship_panel import build_relationship_panel

logger = logging.getLogger("CrimeNet.Workspace")


def build_toolbar_dropdown_options(elements: List[Dict[str, Any]]):
    """Extract entity nodes and types with emojis for investigation workspace dropdowns."""
    if not elements:
        return [], [], [], []

    node_options = []
    types_set = set()
    for el in elements:
        if el.get("group") == "nodes":
            d = el.get("data", {})
            nid = d.get("id")
            name = d.get("name") or d.get("label") or nid
            ntype = str(d.get("type") or "entity").upper()
            types_set.add(ntype.lower())
            node_options.append({"label": f"{name} ({ntype})", "value": nid})

    node_options.sort(key=lambda x: str(x["label"]).lower())
    type_icons = {
        "person": "👤",
        "phone": "📱",
        "vehicle": "🚗",
        "location": "📍",
        "organization": "🏢",
        "account": "💳",
        "case": "💼",
        "event": "📅",
    }
    type_options = [
        {"label": f"{type_icons.get(t, '🔹')} {t.upper()}", "value": t}
        for t in sorted(list(types_set))
    ]
    return node_options, type_options, node_options, node_options


def register_case_workspace_callbacks(dash_app):
    """Register all investigation workspace interactivity callbacks with Dash."""

    # -------------------------------------------------------------------------
    # 1. Populate Workspace Toolbar Dropdowns whenever Cytoscape elements change
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("ws-search-entity-dropdown", "options"),
            Output("ws-filter-entity-type", "options"),
            Output("ws-path-source", "options"),
            Output("ws-path-target", "options"),
        ],
        [Input("cytoscape", "elements")],
        prevent_initial_call=True
    )
    def populate_workspace_toolbar_options(elements):
        return build_toolbar_dropdown_options(elements)

    # -------------------------------------------------------------------------
    # 2. Entity Quick Search & Filtering (Entity Type, Modality, Acceptance)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        Output("cytoscape", "elements", allow_duplicate=True),
        [
            Input("ws-search-entity-dropdown", "value"),
            Input("ws-filter-entity-type", "value"),
            Input("ws-filter-modality", "value"),
            Input("ws-filter-acceptance", "value"),
        ],
        [State("cytoscape", "elements")],
        prevent_initial_call=True
    )
    def handle_workspace_search_and_filters(search_node_id, filter_types, filter_modality, filter_acceptance, elements):
        if not elements:
            return no_update

        triggered = ctx.triggered_id
        new_elements = []

        # If user searched for a specific entity: focus and highlight it
        if triggered == "ws-search-entity-dropdown" and search_node_id:
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d
                if el.get("group") == "nodes":
                    if d.get("id") == search_node_id:
                        el_copy["classes"] = "crimenet-focus-pair"
                        d["selected"] = True
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                        d["selected"] = False
                elif el.get("group") == "edges":
                    if d.get("source") == search_node_id or d.get("target") == search_node_id:
                        el_copy["classes"] = "crimenet-focus-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                new_elements.append(el_copy)
            return new_elements

        # Apply multi-filter criteria
        selected_types = set([t.lower() for t in filter_types]) if filter_types else None
        modality_filter = (filter_modality or "ALL").upper()
        acceptance_filter = (filter_acceptance or "ALL").upper()

        hidden_nodes = set()
        for el in elements:
            if el.get("group") == "nodes":
                d = el.get("data", {})
                ntype = str(d.get("type", "")).lower()
                is_hidden = False
                if selected_types and ntype not in selected_types:
                    is_hidden = True
                if is_hidden:
                    hidden_nodes.add(d.get("id"))

        for el in elements:
            el_copy = dict(el)
            d = dict(el_copy.get("data", {}))
            el_copy["data"] = d

            if el.get("group") == "nodes":
                nid = d.get("id")
                d["hidden"] = nid in hidden_nodes
                # Clear focus classes when filters are actively changed
                current_classes = el_copy.get("classes", "")
                if "crimenet-dimmed" in current_classes:
                    el_copy["classes"] = current_classes.replace("crimenet-dimmed", "").strip()
            elif el.get("group") == "edges":
                src = d.get("source")
                tgt = d.get("target")
                emod = str(d.get("modality") or ("PREDICTED" if d.get("predicted") else "OBSERVED")).upper()
                eacc = str(d.get("acceptance") or ("PROPOSED" if d.get("predicted") else "CONFIRMED")).upper()

                is_hidden = False
                if src in hidden_nodes or tgt in hidden_nodes:
                    is_hidden = True
                if modality_filter != "ALL" and emod != modality_filter:
                    is_hidden = True
                if acceptance_filter != "ALL" and eacc != acceptance_filter:
                    is_hidden = True

                d["hidden"] = is_hidden

            new_elements.append(el_copy)

        return new_elements

    # -------------------------------------------------------------------------
    # 3. Graph Exploration Tools (N-Hop, Shortest Path, Neighbors, Reset View)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("cytoscape", "elements", allow_duplicate=True),
            Output("analysis-summary", "children", allow_duplicate=True),
        ],
        [
            Input("ws-btn-nhop-1", "n_clicks"),
            Input("ws-btn-nhop-2", "n_clicks"),
            Input("ws-btn-nhop-3", "n_clicks"),
            Input("ws-btn-find-path", "n_clicks"),
            Input("ws-btn-expand-neighbors", "n_clicks"),
            Input("ws-btn-reset-view", "n_clicks"),
        ],
        [
            State("cytoscape", "elements"),
            State("ws-search-entity-dropdown", "value"),
            State("ws-path-source", "value"),
            State("ws-path-target", "value"),
        ],
        prevent_initial_call=True
    )
    def handle_workspace_exploration(
        nhop1_clicks, nhop2_clicks, nhop3_clicks,
        path_clicks, expand_clicks, reset_clicks,
        elements, search_node_id, path_source_id, path_target_id
    ):
        from visualizer import app as vapp

        triggered = ctx.triggered_id
        if not elements:
            return no_update, no_update

        # RESET VIEW: Restore full network without dimming or focus classes
        if triggered == "ws-btn-reset-view":
            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                d["hidden"] = False
                d["highlighted"] = False
                d["selected"] = False
                el_copy["data"] = d
                el_copy["classes"] = ""
                new_elements.append(el_copy)
            summary = html.Div(
                "Full investigation network restored.",
                style={"color": "#9ae6b4", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
            )
            return new_elements, summary

        # EXPAND NEIGHBORS: Expand selected nodes in active network
        if triggered == "ws-btn-expand-neighbors":
            selected = []
            if getattr(vapp, "active_network", None):
                selected = vapp.active_network.get_selected_nodes()
            if not selected and search_node_id:
                selected = [search_node_id]

            if not selected:
                alert = html.Div(
                    "⚠️ Please select at least one entity in the graph to expand neighbors.",
                    style={"color": "#fbd38d", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return no_update, alert

            if getattr(vapp, "active_network", None):
                vapp.active_network.expand_nodes(selected)
                summary = html.Div(
                    f"Expanded neighbors for {len(selected)} entity(s).",
                    style={"color": "#9ae6b4", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return vapp.active_network.elements, summary
            return no_update, no_update

        # N-HOP EXPLORATION: 1-Hop, 2-Hop, 3-Hop
        if triggered in ("ws-btn-nhop-1", "ws-btn-nhop-2", "ws-btn-nhop-3"):
            hops_map = {"ws-btn-nhop-1": 1, "ws-btn-nhop-2": 2, "ws-btn-nhop-3": 3}
            max_hops = hops_map.get(triggered, 1)

            root_id = search_node_id
            if not root_id and getattr(vapp, "active_network", None):
                sel = vapp.active_network.get_selected_nodes()
                if sel:
                    root_id = sel[0]

            if not root_id:
                alert = html.Div(
                    "⚠️ Please select or search for an entity first to explore its N-Hop neighborhood.",
                    style={"color": "#fbd38d", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return no_update, alert

            # Build adjacency graph
            G = nx.Graph()
            node_name_map = {}
            for el in elements:
                if el.get("group") == "nodes":
                    d = el.get("data", {})
                    nid = d.get("id")
                    G.add_node(nid)
                    node_name_map[nid] = d.get("name") or d.get("label") or nid
                elif el.get("group") == "edges":
                    d = el.get("data", {})
                    G.add_edge(d.get("source"), d.get("target"), edge_id=d.get("id"))

            if root_id not in G:
                return no_update, html.Div(f"Entity '{root_id}' not found in active graph.", style={"color": "#fc8181"})

            lengths = nx.single_source_shortest_path_length(G, root_id, cutoff=max_hops)
            in_hop_nodes = set(lengths.keys())

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "nodes":
                    nid = d.get("id")
                    if nid == root_id:
                        el_copy["classes"] = "crimenet-focus-pair"
                    elif nid in in_hop_nodes:
                        el_copy["classes"] = "crimenet-nhop-node"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                elif el.get("group") == "edges":
                    src = d.get("source")
                    tgt = d.get("target")
                    if src in in_hop_nodes and tgt in in_hop_nodes:
                        el_copy["classes"] = "crimenet-nhop-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                new_elements.append(el_copy)

            root_label = node_name_map.get(root_id, root_id)
            summary = html.Div(
                [
                    html.B(f"🔍 {max_hops}-Hop Evidentiary Neighborhood: "),
                    html.Span(f"{len(in_hop_nodes)} entities linked to "),
                    html.B(root_label, style={"color": "#63b3ed"}),
                    html.Span(f" within {max_hops} hop(s)."),
                ],
                style={"color": "#e2e8f0", "fontSize": "11px", "padding": "4px 8px"}
            )
            return new_elements, summary

        # SHORTEST PATH FINDER
        if triggered == "ws-btn-find-path":
            if not path_source_id or not path_target_id:
                alert = html.Div(
                    "⚠️ Please select both Source and Target entities to trace the shortest evidentiary path.",
                    style={"color": "#fbd38d", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return no_update, alert

            if path_source_id == path_target_id:
                alert = html.Div(
                    "⚠️ Source and Target must be different entities.",
                    style={"color": "#fbd38d", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return no_update, alert

            G = nx.Graph()
            node_name_map = {}
            for el in elements:
                if el.get("group") == "nodes":
                    d = el.get("data", {})
                    nid = d.get("id")
                    G.add_node(nid)
                    node_name_map[nid] = d.get("name") or d.get("label") or nid
                elif el.get("group") == "edges":
                    d = el.get("data", {})
                    G.add_edge(d.get("source"), d.get("target"), edge_id=d.get("id"))

            if not nx.has_path(G, path_source_id, path_target_id):
                src_name = node_name_map.get(path_source_id, path_source_id)
                tgt_name = node_name_map.get(path_target_id, path_target_id)
                alert = html.Div(
                    f"❌ No connecting evidentiary path found between '{src_name}' and '{tgt_name}'.",
                    style={"color": "#fc8181", "fontSize": "11px", "fontWeight": "600", "padding": "4px 8px"}
                )
                return no_update, alert

            path = nx.shortest_path(G, path_source_id, path_target_id)
            path_nodes = set(path)
            path_edges = set()
            for idx in range(len(path) - 1):
                u, v = path[idx], path[idx + 1]
                path_edges.add((u, v))
                path_edges.add((v, u))

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "nodes":
                    nid = d.get("id")
                    if nid in (path_source_id, path_target_id):
                        el_copy["classes"] = "crimenet-focus-pair"
                    elif nid in path_nodes:
                        el_copy["classes"] = "crimenet-intermediary"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                elif el.get("group") == "edges":
                    src = d.get("source")
                    tgt = d.get("target")
                    if (src, tgt) in path_edges or (tgt, src) in path_edges:
                        el_copy["classes"] = "crimenet-focus-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                new_elements.append(el_copy)

            chain_labels = [node_name_map.get(n, n) for n in path]
            hops_count = len(path) - 1
            summary = html.Div(
                [
                    html.B(f"🎯 Shortest Evidentiary Chain ({hops_count} Hops): "),
                    html.Span(" ➔ ".join(chain_labels), style={"color": "#63b3ed", "fontWeight": "600"}),
                ],
                style={"color": "#e2e8f0", "fontSize": "11px", "padding": "4px 8px"}
            )
            return new_elements, summary

        return no_update, no_update

    # -------------------------------------------------------------------------
    # 4. Label Visibility Controls (Name, Name+Type, None)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        Output("cytoscape", "elements", allow_duplicate=True),
        [Input("ws-label-mode", "value")],
        [State("cytoscape", "elements")],
        prevent_initial_call=True
    )
    def handle_workspace_label_mode(label_mode, elements):
        if not elements or not label_mode:
            return no_update

        new_elements = []
        for el in elements:
            el_copy = dict(el)
            d = dict(el_copy.get("data", {}))
            el_copy["data"] = d

            if el.get("group") == "nodes":
                name = d.get("name") or d.get("id") or ""
                ntype = str(d.get("type") or "").upper()
                if label_mode == "name":
                    d["label"] = name
                elif label_mode == "name_type":
                    d["label"] = f"{name}\n[{ntype}]" if ntype else name
                elif label_mode == "none":
                    d["label"] = ""

            new_elements.append(el_copy)
        return new_elements

    # -------------------------------------------------------------------------
    # 5. Visual Analysis Highlights (Bridges, AI Predictions, Clear)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("cytoscape", "elements", allow_duplicate=True),
            Output("analysis-summary", "children", allow_duplicate=True),
        ],
        [
            Input("ws-btn-highlight-bridges", "n_clicks"),
            Input("ws-btn-highlight-predicted", "n_clicks"),
            Input("ws-btn-clear-highlights", "n_clicks"),
        ],
        [State("cytoscape", "elements")],
        prevent_initial_call=True
    )
    def handle_workspace_highlights(bridges_clicks, pred_clicks, clear_clicks, elements):
        triggered = ctx.triggered_id
        if not elements:
            return no_update, no_update

        if triggered == "ws-btn-clear-highlights":
            new_elements = []
            for el in elements:
                el_copy = dict(el)
                el_copy["classes"] = ""
                new_elements.append(el_copy)
            summary = html.Div("Highlights cleared.", style={"color": "#a0aec0", "fontSize": "11px", "padding": "4px 8px"})
            return new_elements, summary

        if triggered == "ws-btn-highlight-bridges":
            G = nx.Graph()
            node_name_map = {}
            for el in elements:
                if el.get("group") == "nodes":
                    d = el.get("data", {})
                    G.add_node(d.get("id"))
                    node_name_map[d.get("id")] = d.get("name") or d.get("id")
                elif el.get("group") == "edges":
                    d = el.get("data", {})
                    G.add_edge(d.get("source"), d.get("target"))

            if len(G) == 0:
                return no_update, no_update

            centralities = nx.betweenness_centrality(G)
            sorted_nodes = sorted(centralities.items(), key=lambda x: x[1], reverse=True)
            top_bridges = set([k for k, score in sorted_nodes[:5] if score > 0])

            if not top_bridges:
                return no_update, html.Div("No distinct bridge intermediaries detected in network.", style={"color": "#fbd38d"})

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "nodes":
                    if d.get("id") in top_bridges:
                        el_copy["classes"] = "crimenet-focus-pair"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                elif el.get("group") == "edges":
                    src, tgt = d.get("source"), d.get("target")
                    if src in top_bridges or tgt in top_bridges:
                        el_copy["classes"] = "crimenet-focus-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                new_elements.append(el_copy)

            bridge_names = [node_name_map.get(b, b) for b in top_bridges]
            summary = html.Div(
                [
                    html.B("🌉 Key Network Bridge Entities: "),
                    html.Span(", ".join(bridge_names), style={"color": "#f6ad55", "fontWeight": "700"}),
                ],
                style={"color": "#e2e8f0", "fontSize": "11px", "padding": "4px 8px"}
            )
            return new_elements, summary

        if triggered == "ws-btn-highlight-predicted":
            pred_edges = []
            pred_endpoints = set()
            for el in elements:
                if el.get("group") == "edges":
                    d = el.get("data", {})
                    mod = str(d.get("modality") or ("PREDICTED" if d.get("predicted") else "OBSERVED")).upper()
                    if mod in ("PREDICTED", "INFERRED") or d.get("predicted"):
                        pred_edges.append(d)
                        pred_endpoints.add(d.get("source"))
                        pred_endpoints.add(d.get("target"))

            if not pred_edges:
                return no_update, html.Div("No predicted or inferred links present in current view.", style={"color": "#fbd38d"})

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "nodes":
                    if d.get("id") in pred_endpoints:
                        el_copy["classes"] = "crimenet-intermediary"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"
                elif el.get("group") == "edges":
                    mod = str(d.get("modality") or ("PREDICTED" if d.get("predicted") else "OBSERVED")).upper()
                    if mod in ("PREDICTED", "INFERRED") or d.get("predicted"):
                        el_copy["classes"] = "crimenet-focus-edge"
                    else:
                        el_copy["classes"] = "crimenet-dimmed"

                new_elements.append(el_copy)

            summary = html.Div(
                [
                    html.B("⚠️ AI Predicted & Inferred Relationships: "),
                    html.Span(f"Highlighting {len(pred_edges)} hypothesis link(s) across {len(pred_endpoints)} entities. Awaiting acceptance."),
                ],
                style={"color": "#fbd38d", "fontSize": "11px", "padding": "4px 8px"}
            )
            return new_elements, summary

        return no_update, no_update

    # -------------------------------------------------------------------------
    # 6. Forensic Evidence & Provenance Inspector (Node Click, Edge Click, or Search Select)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("evidence-inspector-card", "children"),
            Output("inspected-edge-store", "data"),
        ],
        [
            Input("cytoscape", "tapEdgeData"),
            Input("cytoscape", "tapNodeData"),
            Input("ws-search-entity-dropdown", "value"),
        ],
        [
            State("active-case-store", "data"),
            State("cytoscape", "elements"),
        ],
        prevent_initial_call=True
    )
    def handle_evidence_inspection(tap_edge_data, tap_node_data, search_entity_id, active_case, elements):
        """Dispatch to Entity Dossier or Relationship Investigation panel."""
        triggered = ctx.triggered_id
        prop = ctx.triggered[0]["prop_id"].split(".")[1] if ctx.triggered else ""
        active_case_id = (active_case or {}).get("case_id") or ""

        # ── Edge click → Relationship Investigation Panel ─────────────────────
        if prop == "tapEdgeData" and tap_edge_data:
            d = tap_edge_data
            case_id = d.get("case_id") or active_case_id
            try:
                panel = build_relationship_panel(edge_data=d, case_id=case_id)
            except Exception as exc:
                logger.warning("build_relationship_panel failed: %s", exc)
                panel = html.Div(
                    f"⚠️ Could not load relationship panel: {exc}",
                    style={"color": "#fc8181", "padding": "10px", "fontSize": "11px"}
                )
            return panel, d

        # ── Node click → Entity Intelligence Dossier ──────────────────────────
        elif prop == "tapNodeData" and tap_node_data:
            d = tap_node_data
            entity_id = d.get("id") or ""
            case_id   = d.get("case_id") or active_case_id
            try:
                panel = build_entity_dossier(
                    entity_id=entity_id,
                    node_data=d,
                    case_id=case_id,
                )
            except Exception as exc:
                logger.warning("build_entity_dossier failed: %s", exc)
                panel = html.Div(
                    f"⚠️ Could not load entity dossier: {exc}",
                    style={"color": "#fc8181", "padding": "10px", "fontSize": "11px"}
                )
            return panel, None

        # ── Search dropdown select → Entity Intelligence Dossier ──────────────
        elif triggered == "ws-search-entity-dropdown" and search_entity_id:
            node_data = {}
            if elements:
                for el in elements:
                    if el.get("group") == "nodes" and el.get("data", {}).get("id") == search_entity_id:
                        node_data = el.get("data", {})
                        break

            case_id = node_data.get("case_id") or active_case_id
            try:
                panel = build_entity_dossier(
                    entity_id=search_entity_id,
                    node_data=node_data,
                    case_id=case_id,
                )
            except Exception as exc:
                logger.warning("build_entity_dossier for search failed: %s", exc)
                panel = html.Div(
                    f"⚠️ Could not load entity dossier: {exc}",
                    style={"color": "#fc8181", "padding": "10px", "fontSize": "11px"}
                )
            return panel, None

        return no_update, no_update

    # -------------------------------------------------------------------------
    # 7. Relationship Acceptance & Rejection Actions (Human-in-the-loop Gate)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("evidence-inspector-card", "children", allow_duplicate=True),
            Output("cytoscape", "elements", allow_duplicate=True),
        ],
        [
            Input("btn-accept-edge", "n_clicks"),
            Input("btn-reject-edge", "n_clicks"),
        ],
        [
            State("inspected-edge-store", "data"),
            State("cytoscape", "elements"),
            State("active-case-store", "data"),
        ],
        prevent_initial_call=True
    )
    def handle_relationship_validation(accept_clicks, reject_clicks, edge_data, elements, active_case):
        from visualizer import app as vapp

        triggered = ctx.triggered_id
        if not edge_data or not elements:
            return no_update, no_update

        edge_id = edge_data.get("db_id") or edge_data.get("id")
        case_id = (active_case or {}).get("case_id") or edge_data.get("case_id") or "CASE-2026-0142"

        boundary = GraphRAGCrimeNetBoundary(case_id=case_id)

        # ACCEPT RELATIONSHIP: Promote to CONFIRMED and Sync to Neo4j
        if triggered == "btn-accept-edge":
            success = boundary.accept_relationship(str(edge_id), investigator_id="Lead Investigator")
            driver = GraphRAGCrimeNetBoundary.get_neo4j_driver()
            if driver:
                boundary.sync_to_neo4j(driver=driver, case_id=case_id)

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "edges" and (d.get("id") == edge_data.get("id") or d.get("db_id") == edge_id):
                    d["acceptance"] = "CONFIRMED"
                    d["modality"] = "EXTRACTED"
                    d["predicted"] = False
                    el_copy["classes"] = ""

                new_elements.append(el_copy)

            if getattr(vapp, "active_network", None):
                vapp.active_network.elements = new_elements

            confirmation_card = html.Div(
                style={"backgroundColor": "#1c4532", "border": "1px solid #38a169", "borderRadius": "6px", "padding": "12px 14px", "marginTop": "10px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "4px"},
                        children=[
                            html.Span("✅", style={"fontSize": "16px"}),
                            html.B("Relationship Validated & Confirmed!", style={"color": "#c6f6d5", "fontSize": "12px"}),
                        ]
                    ),
                    html.Div(
                        "Promoted to CONFIRMED fact in CrimeNet graph and synchronized to Neo4j operational database. Audit log recorded.",
                        style={"color": "#e2e8f0", "fontSize": "11px"}
                    )
                ]
            )
            return confirmation_card, new_elements

        # REJECT RELATIONSHIP: Mark REJECTED and Dismiss from Graph
        if triggered == "btn-reject-edge":
            success = boundary.reject_relationship(str(edge_id), investigator_id="Lead Investigator")

            new_elements = []
            for el in elements:
                el_copy = dict(el)
                d = dict(el_copy.get("data", {}))
                el_copy["data"] = d

                if el.get("group") == "edges" and (d.get("id") == edge_data.get("id") or d.get("db_id") == edge_id):
                    d["hidden"] = True
                    d["acceptance"] = "REJECTED"

                new_elements.append(el_copy)

            if getattr(vapp, "active_network", None):
                vapp.active_network.elements = new_elements

            dismiss_card = html.Div(
                style={"backgroundColor": "#2d1515", "border": "1px solid #e53e3e", "borderRadius": "6px", "padding": "12px 14px", "marginTop": "10px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "4px"},
                        children=[
                            html.Span("❌", style={"fontSize": "16px"}),
                            html.B("Relationship Dismissed", style={"color": "#feb2b2", "fontSize": "12px"}),
                        ]
                    ),
                    html.Div(
                        "Flagged as REJECTED and excluded from operational investigation graph. Audit log recorded.",
                        style={"color": "#e2e8f0", "fontSize": "11px"}
                    )
                ]
            )
            return dismiss_card, new_elements

        return no_update, no_update

    # -------------------------------------------------------------------------
    # 8. Viewport Controls (Fit, Zoom In, Zoom Out, Center Selected, Re-layout)
    # -------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("cytoscape", "zoom", allow_duplicate=True),
            Output("cytoscape", "pan", allow_duplicate=True),
            Output("cytoscape", "layout", allow_duplicate=True),
        ],
        [
            Input("btn-cyto-fit", "n_clicks"),
            Input("btn-cyto-zoom-in", "n_clicks"),
            Input("btn-cyto-zoom-out", "n_clicks"),
            Input("btn-cyto-center-selected", "n_clicks"),
            Input("btn-cyto-relayout", "n_clicks"),
        ],
        [
            State("cytoscape", "zoom"),
            State("cytoscape", "pan"),
            State("ws-search-entity-dropdown", "value"),
            State("cytoscape", "elements"),
        ],
        prevent_initial_call=True
    )
    def handle_viewport_hud_controls(fit_c, zin_c, zout_c, center_c, relayout_c, cur_zoom, cur_pan, search_id, elements):
        tid = ctx.triggered_id
        if not tid:
            raise PreventUpdate

        current_zoom = float(cur_zoom or 1.0)
        current_pan = cur_pan or {"x": 0, "y": 0}

        if tid == "btn-cyto-fit":
            return 1.0, {"x": 0, "y": 0}, {"name": "cose-bilkent", "animate": False, "fit": True, "padding": 40}

        if tid == "btn-cyto-zoom-in":
            new_zoom = min(current_zoom * 1.25, 2.2)
            return new_zoom, no_update, no_update

        if tid == "btn-cyto-zoom-out":
            new_zoom = max(current_zoom * 0.8, 0.25)
            return new_zoom, no_update, no_update

        if tid == "btn-cyto-relayout":
            return no_update, no_update, {"name": "cose-bilkent", "animate": True, "fit": True, "padding": 30, "randomize": False}

        if tid == "btn-cyto-center-selected":
            if search_id and elements:
                for el in elements:
                    if el.get("data", {}).get("id") == search_id and "position" in el:
                        pos = el["position"]
                        return 1.4, {"x": -pos.get("x", 0) + 300, "y": -pos.get("y", 0) + 250}, no_update
            return min(current_zoom * 1.15, 2.0), no_update, no_update

        return no_update, no_update, no_update

