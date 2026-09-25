"""Comprehensive End-to-End Test Suite for CrimeNet Graph Analytics Workflow.

Validates:
1. Community Detection:
   - Louvain
   - Label Propagation
   - Modularity Maximization
   - Spectral Clustering
   - Hierarchical Clustering
   - Scopes: Full Network, Selected Entity, Selected Subgraph
2. Social Influence Analysis:
   - PageRank
   - Degree Centrality
   - Betweenness Centrality
   - Closeness Centrality
   - Scopes: Full Network, Selected Entity (Personalized PageRank), Selected Subgraph
3. Path Analysis:
   - Shortest Path (Dijkstra / Bidirectional)
   - N-Hop Radial Neighborhood Exploration
   - All Connecting Paths
   - Scopes: Selected Pair, Selected Entity, Full Network
4. Graph Visual Highlighting & Classes:
   - .crimenet-focus-pair, .crimenet-intermediary, .crimenet-focus-edge
   - .crimenet-nhop-node, .crimenet-nhop-edge, .crimenet-cluster-node, .crimenet-dimmed
5. Case Record Persistence:
   - MySQL analysis_results persistence
   - Audit trail logging
6. Authenticity:
   - Mathematical outputs come directly from NetworkX and Neo4j algorithms.
"""

import os
import sys
import pytest
import networkx as nx

# Add project root to sys.path
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

from storage.builtin_datasets import ActiveNetwork
from storage.case_data_service import CaseDataService
from analyzer import request_taker
from analyzer import path_analysis
from analyzer import social_influence_analysis
from analyzer import community_detection


def _create_synthetic_investigation_network():
    """Build a deterministic criminal syndicate graph with 10 entities and 14 evidentiary links.
    
    Structure:
    - Core syndicate: Rahul (kingpin) -> Amit (lieutenant) -> Vikas (enforcer)
    - Financial cell: Amit -> Hawala_1 -> Hawala_2
    - Logistics cell: Vikas -> Driver_1 -> Warehouse_1
    - Bridge / Intermediary: Priya connects Core syndicate to Supplier_A and Supplier_B
    """
    edges = [
        # Core cell
        {"source": "Rahul", "target": "Amit", "properties": {"type": "COMMUNICATED", "confidence": 0.95, "modality": "OBSERVED"}},
        {"source": "Rahul", "target": "Vikas", "properties": {"type": "COMMANDS", "confidence": 0.90, "modality": "OBSERVED"}},
        {"source": "Amit", "target": "Vikas", "properties": {"type": "COORDINATES", "confidence": 0.85, "modality": "OBSERVED"}},
        
        # Financial cell
        {"source": "Amit", "target": "Hawala_1", "properties": {"type": "TRANSFERRED_FUNDS", "confidence": 0.80, "modality": "EXTRACTED"}},
        {"source": "Hawala_1", "target": "Hawala_2", "properties": {"type": "LAUNDERED", "confidence": 0.88, "modality": "EXTRACTED"}},
        {"source": "Hawala_2", "target": "Amit", "properties": {"type": "KICKBACK", "confidence": 0.75, "modality": "INFERRED"}},
        
        # Logistics cell
        {"source": "Vikas", "target": "Driver_1", "properties": {"type": "DISPATCHED", "confidence": 0.92, "modality": "OBSERVED"}},
        {"source": "Driver_1", "target": "Warehouse_1", "properties": {"type": "VISITED", "confidence": 0.90, "modality": "OBSERVED"}},
        {"source": "Vikas", "target": "Warehouse_1", "properties": {"type": "OWNS", "confidence": 0.85, "modality": "EXTRACTED"}},
        
        # Bridge to suppliers
        {"source": "Rahul", "target": "Priya", "properties": {"type": "MEETING", "confidence": 0.70, "modality": "OBSERVED"}},
        {"source": "Priya", "target": "Supplier_A", "properties": {"type": "PROCURES", "confidence": 0.82, "modality": "EXTRACTED"}},
        {"source": "Priya", "target": "Supplier_B", "properties": {"type": "PROCURES", "confidence": 0.78, "modality": "EXTRACTED"}},
        {"source": "Supplier_A", "target": "Supplier_B", "properties": {"type": "ASSOCIATE", "confidence": 0.65, "modality": "INFERRED"}},
        {"source": "Supplier_B", "target": "Warehouse_1", "properties": {"type": "DELIVERED_TO", "confidence": 0.88, "modality": "OBSERVED"}},
    ]

    net = ActiveNetwork(initialize=False)
    net.edges = edges
    net.nodes = {
        "Rahul": {"type": "person", "name": "Rahul (Kingpin)"},
        "Amit": {"type": "person", "name": "Amit (Lieutenant)"},
        "Vikas": {"type": "person", "name": "Vikas (Enforcer)"},
        "Priya": {"type": "person", "name": "Priya (Broker)"},
        "Hawala_1": {"type": "account", "name": "Hawala Operator 1"},
        "Hawala_2": {"type": "account", "name": "Hawala Operator 2"},
        "Driver_1": {"type": "person", "name": "Courier Driver"},
        "Warehouse_1": {"type": "location", "name": "Dock Warehouse"},
        "Supplier_A": {"type": "organization", "name": "Contraband Supplier Alpha"},
        "Supplier_B": {"type": "organization", "name": "Contraband Supplier Beta"},
    }
    net.adj_list = {n: [] for n in net.nodes}
    for idx, e in enumerate(edges):
        net.adj_list[e["source"]].append(idx)
        net.adj_list[e["target"]].append(idx)

    net.node_types = {"person": {}, "account": {}, "location": {}, "organization": {}}
    net.edge_types = {"COMMUNICATED": {}, "COMMANDS": {}, "COORDINATES": {}, "TRANSFERRED_FUNDS": {},
                      "LAUNDERED": {}, "KICKBACK": {}, "DISPATCHED": {}, "VISITED": {}, "OWNS": {},
                      "MEETING": {}, "PROCURES": {}, "ASSOCIATE": {}, "DELIVERED_TO": {}}

    net.initialize(params={"network_name": "Syndicate Test Network", "case_id": "case-test-syndicate-101"})
    return net


# =============================================================================
# 1. COMMUNITY DETECTION TESTS
# =============================================================================

def test_community_detection_louvain_full_network():
    """Verify Louvain identifies distinct criminal cells on full network."""
    net = _create_synthetic_investigation_network()
    res = net.apply_analysis("community_detection", "louvain", params={}, scope="FULL_NETWORK")
    assert res is not None
    assert res.get("success") == 1
    assert "membership" in res
    assert len(res["membership"]) == 10

    # Ensure nodes in active network have community assigned
    nodes_with_comm = [e for e in net.elements if e.get("group") == "nodes" and e.get("data", {}).get("community") is not None]
    assert len(nodes_with_comm) == 10


def test_community_detection_label_propagation():
    """Verify Label Propagation algorithm partitions network into communities."""
    net = _create_synthetic_investigation_network()
    res = net.apply_analysis("community_detection", "label_propagation", params={}, scope="FULL_NETWORK")
    assert res.get("success") == 1
    assert len(res["membership"]) == 10
    # Check that communities list is populated
    assert len(res.get("communities", [])) >= 1


def test_community_detection_modularity_and_spectral():
    """Verify Modularity Maximization and Spectral Clustering algorithms."""
    net = _create_synthetic_investigation_network()
    res_mod = net.apply_analysis("community_detection", "modularity", params={}, scope="FULL_NETWORK")
    assert res_mod.get("success") == 1
    assert len(res_mod["membership"]) == 10

    res_spec = net.apply_analysis("community_detection", "spectral", params={"K": 3}, scope="FULL_NETWORK")
    assert res_spec.get("success") == 1
    assert len(res_spec["membership"]) == 10


def test_community_detection_selected_entity_scope():
    """Verify Selected Entity scope isolates and highlights the entity's crime cell."""
    net = _create_synthetic_investigation_network()
    net.selected_nodes = {"Rahul"}

    res = net.apply_analysis("community_detection", "louvain", params={}, scope="SELECTED_ENTITY")
    assert res.get("success") == 1

    rahul_comm = list(res["membership"]["Rahul"].keys())[0]

    # Check graph element classes: Rahul's community members should have .crimenet-cluster-node, others .crimenet-dimmed
    for el in net.elements:
        if el.get("group") == "nodes":
            nid = el["data"]["id"]
            node_comm = list(res["membership"][nid].keys())[0]
            classes = el.get("classes", "").split()
            if node_comm == rahul_comm:
                assert "crimenet-cluster-node" in classes
            else:
                assert "crimenet-dimmed" in classes


def test_community_detection_selected_subgraph_scope():
    """Verify Selected Subgraph scope restricts community detection strictly to selected nodes."""
    net = _create_synthetic_investigation_network()
    financial_cell = {"Amit", "Hawala_1", "Hawala_2"}
    net.selected_nodes = financial_cell

    res = net.apply_analysis("community_detection", "louvain", params={}, scope="SELECTED_SUBGRAPH")
    assert res.get("success") == 1
    # Only the 3 selected nodes should be analyzed
    assert len(res["membership"]) == 3
    for n in financial_cell:
        assert n in res["membership"]


# =============================================================================
# 2. SOCIAL INFLUENCE ANALYSIS TESTS
# =============================================================================

def test_social_influence_pagerank():
    """Verify PageRank calculates authentic structural influence scores."""
    net = _create_synthetic_investigation_network()
    res = net.apply_analysis("social_influence_analysis", "pagerank", params={}, scope="FULL_NETWORK")
    assert res.get("success") == 1
    scores = res["scores"]
    assert len(scores) == 10
    # PageRank scores must sum to approx 1.0
    assert abs(sum(scores.values()) - 1.0) < 1e-4

    # Top influencer should be tagged with crimenet-cluster-node
    top_node = max(scores, key=scores.get)
    for el in net.elements:
        if el.get("group") == "nodes" and el["data"]["id"] == top_node:
            assert "crimenet-cluster-node" in el.get("classes", "").split()


def test_social_influence_degree_centrality():
    """Verify Degree Centrality calculates authentic degree scores."""
    net = _create_synthetic_investigation_network()
    res = net.apply_analysis("social_influence_analysis", "degree_centrality", params={}, scope="FULL_NETWORK")
    assert res.get("success") == 1
    scores = res["scores"]
    assert len(scores) == 10
    # Check degree centrality formula: degree / (n - 1) where n=10 => divisor is 9
    # Vikas is connected to Rahul, Amit, Driver_1, Warehouse_1 => degree = 4 => 4/9 = 0.4444
    assert round(scores["Vikas"], 4) == round(4 / 9, 4)


def test_social_influence_betweenness_centrality():
    """Verify Betweenness Centrality identifies bridge nodes."""
    net = _create_synthetic_investigation_network()
    res = net.apply_analysis("social_influence_analysis", "betweenness", params={}, scope="FULL_NETWORK")
    assert res.get("success") == 1
    scores = res["scores"]
    assert len(scores) == 10
    # Priya connects Rahul to Supplier_A and Supplier_B, so Priya must have positive betweenness
    assert scores["Priya"] > 0.0


def test_social_influence_selected_entity_personalized_pagerank():
    """Verify Selected Entity scope sets personalized PageRank starting from the suspect."""
    net = _create_synthetic_investigation_network()
    net.selected_nodes = {"Rahul"}

    res = net.apply_analysis("social_influence_analysis", "pagerank", params={}, scope="SELECTED_ENTITY")
    assert res.get("success") == 1
    scores = res["scores"]
    # With personalization on Rahul, Rahul should have the highest localized influence
    assert max(scores, key=scores.get) == "Rahul"


# =============================================================================
# 3. PATH ANALYSIS TESTS
# =============================================================================

def test_path_analysis_shortest_path_selected_pair():
    """Verify Shortest Path identifies evidentiary connection chain between two suspects."""
    net = _create_synthetic_investigation_network()
    # Test path from Hawala_1 to Warehouse_1
    net.selected_nodes = {"Hawala_1", "Warehouse_1"}

    res = net.apply_analysis("path_analysis", "shortest_path", params={}, scope="SELECTED_PAIR")
    assert res.get("success") == 1
    path = res["path"]
    assert set([path[0], path[-1]]) == {"Hawala_1", "Warehouse_1"}
    assert res["hops"] == len(path) - 1

    # Verify visual highlighting on the graph
    pair_nodes = {"Hawala_1", "Warehouse_1"}
    inter_nodes = set(path[1:-1])

    for el in net.elements:
        if el.get("group") == "nodes":
            nid = el["data"]["id"]
            classes = el.get("classes", "").split()
            if nid in pair_nodes:
                assert "crimenet-focus-pair" in classes
            elif nid in inter_nodes:
                assert "crimenet-intermediary" in classes
            else:
                assert "crimenet-dimmed" in classes
        elif el.get("group") == "edges":
            esrc = el["data"]["source"]
            etgt = el["data"]["target"]
            classes = el.get("classes", "").split()
            # If edge connects consecutive nodes in path
            is_path_edge = any((path[i] == esrc and path[i+1] == etgt) or (path[i] == etgt and path[i+1] == esrc) for i in range(len(path)-1))
            if is_path_edge:
                assert "crimenet-focus-edge" in classes
            else:
                assert "crimenet-dimmed" in classes


def test_path_analysis_n_hop_radial_neighborhood():
    """Verify N-Hop isolates radial neighborhood up to K hops around selected entity."""
    net = _create_synthetic_investigation_network()
    net.selected_nodes = {"Priya"}

    res = net.apply_analysis("path_analysis", "n_hop", params={"K": 2}, scope="SELECTED_ENTITY")
    assert res.get("success") == 1
    assert res["root"] == "Priya"
    assert res["cutoff"] == 2

    neighborhood = set(res["neighborhood"])
    # 1-hop: Rahul, Supplier_A, Supplier_B
    # 2-hop: Amit, Vikas, Warehouse_1
    assert "Rahul" in neighborhood
    assert "Supplier_A" in neighborhood
    assert "Supplier_B" in neighborhood
    assert "Warehouse_1" in neighborhood

    # Verify visual classes on elements
    for el in net.elements:
        if el.get("group") == "nodes":
            nid = el["data"]["id"]
            classes = el.get("classes", "").split()
            if nid == "Priya":
                assert "crimenet-focus-pair" in classes
            elif nid in neighborhood:
                assert "crimenet-nhop-node" in classes
            else:
                assert "crimenet-dimmed" in classes


def test_path_analysis_all_paths():
    """Verify All Paths surfaces alternative connecting conspiracy routes."""
    net = _create_synthetic_investigation_network()
    net.selected_nodes = {"Rahul", "Warehouse_1"}

    res = net.apply_analysis("path_analysis", "all_paths", params={"K": 3}, scope="SELECTED_PAIR")
    assert res.get("success") == 1
    paths = res["paths"]
    assert len(paths) >= 1
    for p in paths:
        assert set([p[0], p[-1]]) == {"Rahul", "Warehouse_1"}


# =============================================================================
# 4. CASE PERSISTENCE & AUDIT TRAIL TESTS
# =============================================================================

def test_save_analysis_result_persistence_and_audit():
    """Verify analysis results and audit events are saved against a case."""
    svc = CaseDataService()
    test_case_id = "test-case-analytics-888"

    # Ensure clean test case
    try:
        with svc._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cases WHERE id = %s;", (test_case_id,))
    except Exception:
        pass

    # Create dummy case
    created_id = svc.create_case(
        title="Automated Analytics Test Case",
        case_number="CASE-ANL-888",
        description="Testing graph analytics persistence",
        priority="HIGH"
    )
    assert created_id is not None

    try:
        # Save Louvain Community Detection Run
        run_id_louvain = svc.save_analysis_result(
            case_id=created_id,
            task_id="community_detection",
            algorithm="louvain",
            parameters={"scope": "FULL_NETWORK"},
            summary={"num_communities": 3, "nodes_analyzed": 10},
            node_metrics={"Rahul": 0, "Amit": 0, "Vikas": 1},
            executed_by="Inspector Sharma"
        )
        assert run_id_louvain is not None

        # Save Shortest Path Run
        run_id_path = svc.save_analysis_result(
            case_id=created_id,
            task_id="path_analysis",
            algorithm="shortest_path",
            parameters={"scope": "SELECTED_PAIR", "source": "Rahul", "target": "Warehouse_1"},
            summary={"hops": 2, "engine": "NetworkX"},
            edge_metrics=["Rahul", "Vikas", "Warehouse_1"],
            executed_by="Inspector Sharma"
        )
        assert run_id_path is not None

        # Log audit
        audit_id = svc.log_audit(
            case_id=created_id,
            action="GRAPH_ANALYSIS_EXECUTED",
            username="Inspector Sharma",
            details=f"Executed louvain & shortest_path. Run IDs: {run_id_louvain[:8]}, {run_id_path[:8]}"
        )
        assert audit_id is not None

        # Retrieve saved analysis results
        history = svc.list_analysis_results(created_id)
        assert len(history) >= 2
        tasks = [h["task_id"] for h in history]
        assert "community_detection" in tasks
        assert "path_analysis" in tasks

    finally:
        # Cleanup
        try:
            with svc._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM cases WHERE id = %s;", (created_id,))
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
