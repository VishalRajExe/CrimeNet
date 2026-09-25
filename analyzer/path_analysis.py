"""Path Analysis Module for CrimeNet.

Implements NetworkX & Neo4j graph path analytics:
- Shortest Path (Dijkstra / Bidirectional evidentiary chain tracing)
- N-Hop Neighborhood (Single-source shortest path radial exploration)
- All Connecting Paths (Alternative conspiracy pathways within cutoff)

Simple Meaning:
Show how entities are connected across the evidentiary graph.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

# Ensure internal package imports
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

import analyzer.common.helpers as helpers
from storage.graphrag_crimenet_boundary import GraphRAGCrimeNetBoundary


def _build_nx_graph_with_string_ids(network: Any, params: Optional[Dict[str, Any]] = None) -> nx.Graph:
    """Construct an undirected NetworkX Graph preserving original node IDs and edge attributes."""
    G = nx.Graph()

    # Network can be a dictionary with 'edges' or a list of edge objects
    edges = network.get("edges") if isinstance(network, dict) else network
    if not edges:
        return G

    for e in edges:
        if not isinstance(e, dict):
            continue
        src = str(e.get("source"))
        tgt = str(e.get("target"))
        props = e.get("properties") or {}
        edge_type = props.get("type") or e.get("type") or "CONNECTED"
        conf = float(props.get("confidence") or e.get("confidence") or 1.0)
        weight = float(props.get("weight") or 1.0)
        modality = str(props.get("modality") or e.get("modality") or "OBSERVED")
        acceptance = str(props.get("acceptance") or props.get("acceptance_status") or "CONFIRMED")

        G.add_edge(src, tgt, type=edge_type, confidence=conf, weight=weight, modality=modality, acceptance=acceptance)

    return G


def _try_neo4j_shortest_path(source: str, target: str) -> Optional[Dict[str, Any]]:
    """Execute live Cypher shortestPath query against Neo4j if driver is available."""
    try:
        driver = GraphRAGCrimeNetBoundary.get_neo4j_driver()
        if not driver:
            return None

        query = """
        MATCH (a {id: $source}), (b {id: $target}),
              p = shortestPath((a)-[*]-(b))
        RETURN [n IN nodes(p) | n.id] AS node_ids,
               [r IN relationships(p) | type(r)] AS rel_types,
               length(p) AS hops
        """
        with driver.session() as session:
            record = session.run(query, source=source, target=target).single()
            if record and record.get("node_ids"):
                nodes = record["node_ids"]
                hops = record["hops"]
                rel_types = record["rel_types"]
                return {
                    "source": source,
                    "target": target,
                    "path": nodes,
                    "hops": hops,
                    "rel_types": rel_types,
                    "engine": "Neo4j",
                }
    except Exception:
        pass
    return None


def shortest_path(network: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Find the shortest connecting evidentiary chain between two entities.

    :param network: Case network (edge list or ActiveNetwork dict)
    :param params: Dict containing 'source' and 'target' entity IDs
    :return: Dict containing status, hops, path sequence, and explanation
    """
    if not params:
        return {
            "success": 0,
            "message": "Parameters 'source' and 'target' are required for shortest path analysis.",
            "path": None,
            "hops": 0,
        }

    source = str(params.get("source") or "")
    target = str(params.get("target") or "")

    if not source or not target:
        return {
            "success": 0,
            "message": "Both 'source' and 'target' entity IDs must be specified.",
            "path": None,
            "hops": 0,
        }

    if source == target:
        return {
            "success": 0,
            "message": "Source and target must be distinct entities.",
            "path": None,
            "hops": 0,
        }

    # 1. Try Neo4j if enabled/available
    neo_res = _try_neo4j_shortest_path(source, target)
    if neo_res:
        path = neo_res["path"]
        hops = neo_res["hops"]
        explanation = f"Shortest path identified via Neo4j: {hops} hop(s) connecting {source} to {target}."
        return {
            "success": 1,
            "message": explanation,
            "path": path,
            "hops": hops,
            "engine": "Neo4j",
            "scores": {node: 1.0 if node in (source, target) else 0.5 for node in path},
        }

    # 2. NetworkX graph analysis
    G = _build_nx_graph_with_string_ids(network, params)
    if source not in G:
        return {
            "success": 0,
            "message": f"Source entity '{source}' does not exist in the active graph.",
            "path": None,
            "hops": 0,
        }
    if target not in G:
        return {
            "success": 0,
            "message": f"Target entity '{target}' does not exist in the active graph.",
            "path": None,
            "hops": 0,
        }

    if not nx.has_path(G, source, target):
        return {
            "success": 0,
            "message": f"No connecting evidentiary path found between '{source}' and '{target}'.",
            "path": None,
            "hops": 0,
        }

    path = nx.shortest_path(G, source, target)
    hops = len(path) - 1
    intermediaries = path[1:-1]
    inter_desc = f" through {len(intermediaries)} intermediary entity(s)" if intermediaries else " (direct link)"

    explanation = f"Shortest path: {hops} hop(s){inter_desc}."
    return {
        "success": 1,
        "message": explanation,
        "path": path,
        "hops": hops,
        "intermediaries": intermediaries,
        "engine": "NetworkX",
        "scores": {node: 1.0 if node in (source, target) else 0.5 for node in path},
    }


def n_hop(network: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Isolate the radial conspiracy neighborhood around an entity up to N hops.

    :param network: Case network (edge list or ActiveNetwork dict)
    :param params: Dict containing 'root'/'source' and 'cutoff'/'K' (default 1)
    :return: Dict containing hop distances, neighborhood nodes, and counts
    """
    if not params:
        return {
            "success": 0,
            "message": "Parameter 'root' (or 'source') is required for N-Hop exploration.",
            "neighborhood": None,
        }

    root = str(params.get("root") or params.get("source") or "")
    cutoff = int(params.get("cutoff") or params.get("K") or params.get("hops") or 1)
    cutoff = max(1, min(cutoff, 5))

    G = _build_nx_graph_with_string_ids(network, params)
    if not root or root not in G:
        return {
            "success": 0,
            "message": f"Root entity '{root}' does not exist in the active graph.",
            "neighborhood": None,
        }

    lengths = nx.single_source_shortest_path_length(G, root, cutoff=cutoff)
    nodes_by_hop: Dict[int, List[str]] = {h: [] for h in range(cutoff + 1)}
    for nid, dist in lengths.items():
        nodes_by_hop[dist].append(nid)

    neighborhood_nodes = list(lengths.keys())
    total_neighbors = len(neighborhood_nodes) - 1

    explanation = (
        f"N-Hop Analysis: Surfaced {total_neighbors} entities within {cutoff}-hop "
        f"radius of '{root}'."
    )

    # Score nodes inversely proportional to distance (root = 1.0, 1-hop = 0.8, 2-hop = 0.6)
    scores = {nid: round(1.0 - (dist * 0.2), 2) for nid, dist in lengths.items()}

    return {
        "success": 1,
        "message": explanation,
        "root": root,
        "cutoff": cutoff,
        "total_entities": len(neighborhood_nodes),
        "neighborhood": neighborhood_nodes,
        "hop_distances": lengths,
        "nodes_by_hop": nodes_by_hop,
        "scores": scores,
        "engine": "NetworkX",
    }


def all_paths(network: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Find all alternative connecting paths between two entities within cutoff.

    :param network: Case network
    :param params: 'source', 'target', and optional 'cutoff'
    """
    if not params:
        return {"success": 0, "message": "Missing parameters.", "paths": []}

    source = str(params.get("source") or "")
    target = str(params.get("target") or "")
    cutoff = int(params.get("cutoff") or params.get("K") or 3)

    G = _build_nx_graph_with_string_ids(network, params)
    if source not in G or target not in G or not nx.has_path(G, source, target):
        return {"success": 0, "message": "No path exists.", "paths": []}

    paths = list(nx.all_simple_paths(G, source, target, cutoff=cutoff))
    return {
        "success": 1,
        "message": f"Found {len(paths)} simple path(s) within {cutoff} hops.",
        "paths": paths,
        "count": len(paths),
    }


def get_info() -> Dict[str, Any]:
    """Metadata dictionary for analyzer discovery."""
    return {
        "name": "Path Analysis",
        "methods": {
            "shortest_path": {
                "name": "Shortest Evidentiary Path",
                "parameter": {
                    "source": {"description": "Source entity ID"},
                    "target": {"description": "Target entity ID"},
                },
            },
            "n_hop": {
                "name": "N-Hop Neighborhood",
                "parameter": {
                    "K": {
                        "description": "Exploration radius (hops)",
                        "options": {"Integer": [1, 2, 3]},
                    }
                },
            },
            "all_paths": {
                "name": "All Connecting Paths",
                "parameter": {
                    "K": {
                        "description": "Maximum path length",
                        "options": {"Integer": [2, 3, 4]},
                    }
                },
            },
        },
    }


class PathAnalyzer:
    """Class for executing path and connectivity graph analytics."""

    def __init__(self, algorithm: str):
        self.algorithm = algorithm
        self.methods = {
            "shortest_path": shortest_path,
            "path": shortest_path,
            "n_hop": n_hop,
            "nhop": n_hop,
            "all_paths": all_paths,
        }

    def perform(self, network: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        algo = self.algorithm.lower()
        if algo not in self.methods:
            return {
                "success": 0,
                "message": f"Algorithm '{self.algorithm}' not recognized in PathAnalyzer.",
            }
        return self.methods[algo](network, params)
