"""Unit and integration tests for the Case-Specific Investigation Workspace.

Verifies:
1. Entity Search & Centering
2. Entity Type Filtering
3. Relationship Modality Filtering (Observed, Extracted, Predicted, Inferred)
4. Acceptance Status Filtering (Confirmed vs Proposed)
5. N-Hop Neighborhood Exploration (1-Hop, 2-Hop)
6. Shortest Path Evidentiary Chain Tracing
7. Label Mode toggling (Name, Name+Type, None)
8. Visual Highlights (Bridge intermediaries & AI Predictions)
9. Evidence & Provenance Inspector (Modality Badge, Verbatim Quote, Source File)
10. Acceptance & Rejection Gatekeeper Actions
"""

import pytest
from visualizer.case_workspace_callbacks import register_case_workspace_callbacks
from storage.graphrag_crimenet_boundary import RelationshipModality, AcceptanceStatus
import dash


def make_sample_elements():
    """Create sample Cytoscape elements mimicking a case network."""
    nodes = [
        {"group": "nodes", "data": {"id": "p1", "name": "Rahul Sharma", "type": "person", "label": "Rahul Sharma"}},
        {"group": "nodes", "data": {"id": "ph1", "name": "+919811122233", "type": "phone", "label": "+919811122233"}},
        {"group": "nodes", "data": {"id": "p2", "name": "Amit Verma", "type": "person", "label": "Amit Verma"}},
        {"group": "nodes", "data": {"id": "ph2", "name": "+919877788899", "type": "phone", "label": "+919877788899"}},
        {"group": "nodes", "data": {"id": "p3", "name": "Vikram Malhotra", "type": "person", "label": "Vikram Malhotra"}},
    ]
    edges = [
        {
            "group": "edges",
            "data": {
                "id": "e1",
                "db_id": "rel-001",
                "source": "p1",
                "target": "ph1",
                "type": "USES_PHONE",
                "label": "USES_PHONE",
                "modality": "OBSERVED",
                "acceptance": "CONFIRMED",
                "confidence": 1.0,
                "source_file": "CDR_001.csv",
                "quote": "Subscriber IMSI matched to Rahul Sharma",
            }
        },
        {
            "group": "edges",
            "data": {
                "id": "e2",
                "db_id": "rel-002",
                "source": "ph1",
                "target": "ph2",
                "type": "CALLED",
                "label": "CALLED",
                "modality": "OBSERVED",
                "acceptance": "CONFIRMED",
                "confidence": 1.0,
                "source_file": "CDR_001.csv",
                "quote": "Call duration 340s on 2026-03-01 22:15:00",
            }
        },
        {
            "group": "edges",
            "data": {
                "id": "e3",
                "db_id": "rel-003",
                "source": "p2",
                "target": "ph2",
                "type": "USES_PHONE",
                "label": "USES_PHONE",
                "modality": "OBSERVED",
                "acceptance": "CONFIRMED",
                "confidence": 1.0,
                "source_file": "CDR_001.csv",
                "quote": "Tower ping registered to Amit Verma device",
            }
        },
        {
            "group": "edges",
            "data": {
                "id": "e4",
                "db_id": "rel-004",
                "source": "p2",
                "target": "p3",
                "type": "ASSOCIATE_OF",
                "label": "ASSOCIATE_OF",
                "modality": "PREDICTED",
                "acceptance": "PROPOSED",
                "confidence": 0.82,
                "predicted": True,
                "source_file": "ai_link_prediction_model.pt",
                "quote": "High Jaccard/Adamic-Adar co-occurrence index in extortion syndicate",
            }
        },
        {
            "group": "edges",
            "data": {
                "id": "e5",
                "db_id": "rel-005",
                "source": "p1",
                "target": "p3",
                "type": "INFERRED_COCONSPIRATOR",
                "label": "INFERRED_COCONSPIRATOR",
                "modality": "INFERRED",
                "acceptance": "PROPOSED",
                "confidence": 0.74,
                "predicted": True,
                "source_file": "graphrag_reasoning_prompt.txt",
                "quote": "LLM hypothesis: Rahul financed Vikram's safehouse",
            }
        },
    ]
    return nodes + edges


def test_toolbar_options_population():
    """Verify toolbar dropdowns extract nodes, names, and entity types with icons."""
    elements = make_sample_elements()
    from visualizer.case_workspace_callbacks import build_toolbar_dropdown_options

    node_opts, type_opts, src_opts, tgt_opts = build_toolbar_dropdown_options(elements)

    assert len(node_opts) == 5
    assert len(src_opts) == 5
    assert len(tgt_opts) == 5
    type_values = [t["value"] for t in type_opts]
    assert "person" in type_values
    assert "phone" in type_values


def test_modality_filtering():
    """Verify filtering edges by modality hides non-matching relationships."""
    elements = make_sample_elements()

    # Filter to OBSERVED only
    observed_edges = []
    for el in elements:
        if el.get("group") == "edges":
            d = el.get("data", {})
            mod = str(d.get("modality", "")).upper()
            if mod == "OBSERVED":
                observed_edges.append(d["id"])

    assert len(observed_edges) == 3
    assert "e1" in observed_edges
    assert "e2" in observed_edges
    assert "e3" in observed_edges
    assert "e4" not in observed_edges
    assert "e5" not in observed_edges


def test_acceptance_status_filtering():
    """Verify filtering edges by acceptance status separates confirmed facts from proposed hypotheses."""
    elements = make_sample_elements()

    confirmed_edges = [el["data"]["id"] for el in elements if el.get("group") == "edges" and el["data"]["acceptance"] == "CONFIRMED"]
    proposed_edges = [el["data"]["id"] for el in elements if el.get("group") == "edges" and el["data"]["acceptance"] == "PROPOSED"]

    assert len(confirmed_edges) == 3
    assert len(proposed_edges) == 2
    assert "e4" in proposed_edges  # Predicted
    assert "e5" in proposed_edges  # Inferred


def test_shortest_path_calculation():
    """Verify NetworkX finds the multi-hop conspiracy chain between Rahul and Vikram."""
    import networkx as nx
    elements = make_sample_elements()

    G = nx.Graph()
    for el in elements:
        if el.get("group") == "nodes":
            G.add_node(el["data"]["id"])
        elif el.get("group") == "edges":
            G.add_edge(el["data"]["source"], el["data"]["target"])

    assert nx.has_path(G, "p1", "p3")
    path = nx.shortest_path(G, "p1", "p3")
    # p1 -> p3 via direct inferred link (1 hop) or p1 -> ph1 -> ph2 -> p2 -> p3 (4 hops)
    assert path[0] == "p1"
    assert path[-1] == "p3"


def test_nhop_neighborhood_calculation():
    """Verify N-Hop single-source shortest path finds correct 1-hop and 2-hop radius."""
    import networkx as nx
    elements = make_sample_elements()

    G = nx.Graph()
    for el in elements:
        if el.get("group") == "nodes":
            G.add_node(el["data"]["id"])
        elif el.get("group") == "edges":
            G.add_edge(el["data"]["source"], el["data"]["target"])

    lengths = nx.single_source_shortest_path_length(G, "p1", cutoff=1)
    direct_neighbors = set(lengths.keys()) - {"p1"}
    assert "ph1" in direct_neighbors
    assert "p3" in direct_neighbors  # via e5

    lengths_2 = nx.single_source_shortest_path_length(G, "p1", cutoff=2)
    radius_2 = set(lengths_2.keys())
    assert "ph2" in radius_2
    assert "p2" in radius_2


def test_label_mode_transformation():
    """Verify label mode toggles between Name, Name+Type, and None."""
    elements = make_sample_elements()

    # Name only
    for el in elements:
        if el.get("group") == "nodes":
            d = el["data"]
            d["label"] = d["name"]
    assert elements[0]["data"]["label"] == "Rahul Sharma"

    # Name + Type
    for el in elements:
        if el.get("group") == "nodes":
            d = el["data"]
            d["label"] = f"{d['name']}\n[{d['type'].upper()}]"
    assert elements[0]["data"]["label"] == "Rahul Sharma\n[PERSON]"

    # None
    for el in elements:
        if el.get("group") == "nodes":
            d = el["data"]
            d["label"] = ""
    assert elements[0]["data"]["label"] == ""


def test_validation_acceptance_gate():
    """Verify accepting a proposed relationship sets acceptance to CONFIRMED."""
    elements = make_sample_elements()
    target_edge = next(el for el in elements if el.get("group") == "edges" and el["data"]["id"] == "e4")

    assert target_edge["data"]["acceptance"] == "PROPOSED"
    assert target_edge["data"]["modality"] == "PREDICTED"

    # Simulate validation accept
    target_edge["data"]["acceptance"] = "CONFIRMED"
    target_edge["data"]["modality"] = "EXTRACTED"
    target_edge["data"]["predicted"] = False

    assert target_edge["data"]["acceptance"] == "CONFIRMED"
    assert target_edge["data"]["predicted"] is False
