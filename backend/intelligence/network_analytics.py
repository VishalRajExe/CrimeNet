"""
network_analytics.py - NetworkX Graph Analytics Engine
Powers real-time topology metrics, community detection, centrality scores,
and link prediction on the operational crime network.
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple
import networkx as nx

logger = logging.getLogger("crimenet.intelligence.networkx")


class NetworkAnalytics:
    def _build_nx_graph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], directed: bool = False) -> nx.Graph:
        g = nx.DiGraph() if directed else nx.Graph()
        for n in nodes:
            nid = str(n.get("id"))
            g.add_node(nid, **n)
        for e in edges:
            u = str(e.get("source"))
            v = str(e.get("target"))
            if u and v:
                g.add_edge(u, v, **e)
        return g

    # -------------------------------------------------------------------------
    # 1. Social Influence & Centrality Analytics
    # -------------------------------------------------------------------------
    def compute_centrality(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], metric: str = "pagerank") -> Dict[str, Any]:
        """
        Computes PageRank, Betweenness, Closeness, or Degree centrality using NetworkX.
        Returns mapped scores per node and sorted rankings.
        """
        if not nodes:
            return {"scores": {}, "rankings": []}

        g = self._build_nx_graph(nodes, edges, directed=False)
        scores = {}

        try:
            if metric == "pagerank":
                scores = nx.pagerank(g, alpha=0.85, max_iter=200)
            elif metric == "betweenness":
                scores = nx.betweenness_centrality(g, normalized=True)
            elif metric == "closeness":
                scores = nx.closeness_centrality(g)
            elif metric == "degree":
                scores = nx.degree_centrality(g)
            else:
                scores = nx.degree_centrality(g)
        except Exception as e:
            logger.warning("NetworkX centrality computation fallback for %s: %s", metric, e)
            # Fallback to degree centrality
            scores = {n: g.degree(n) / max(1, len(g.nodes()) - 1) for n in g.nodes()}

        node_map = {str(n.get("id")): n for n in nodes}
        rankings = []
        for nid, val in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            n_data = node_map.get(nid, {})
            rankings.append({
                "id": nid,
                "label": n_data.get("label", nid),
                "type": n_data.get("type", "UNKNOWN"),
                "score": round(float(val), 4)
            })

        return {
            "metric": metric,
            "scores": {k: round(float(v), 4) for k, v in scores.items()},
            "rankings": rankings[:30]
        }

    # -------------------------------------------------------------------------
    # 2. Community Detection
    # -------------------------------------------------------------------------
    def detect_communities(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], algorithm: str = "louvain") -> Dict[str, Any]:
        """
        Detects syndicate sub-clusters using Louvain, Greedy Modularity, or Label Propagation.
        """
        if not nodes:
            return {"groups": 0, "communityOf": {}, "clusters": []}

        g = self._build_nx_graph(nodes, edges, directed=False)
        clusters = []

        try:
            if algorithm in ("louvain", "modularity_maximization"):
                try:
                    # Louvain partition
                    communities = nx.community.louvain_communities(g, seed=42)
                    clusters = [list(c) for c in communities]
                except Exception:
                    communities = nx.community.greedy_modularity_communities(g)
                    clusters = [list(c) for c in communities]
            elif algorithm in ("label_prop", "async_label_prop"):
                communities = nx.community.asyn_lpa_communities(g, seed=42)
                clusters = [list(c) for c in communities]
            elif algorithm == "k_clique":
                communities = nx.community.k_clique_communities(g, k=3)
                clusters = [list(c) for c in communities]
            else:
                communities = nx.community.greedy_modularity_communities(g)
                clusters = [list(c) for c in communities]
        except Exception as e:
            logger.warning("Community detection fallback: %s", e)
            # Fallback: connected components
            clusters = [list(c) for c in nx.connected_components(g)]

        # Map each node to its community index
        community_of = {}
        for idx, cluster in enumerate(clusters):
            for nid in cluster:
                community_of[nid] = idx

        # Assign any isolated nodes not captured
        for n in nodes:
            nid = str(n.get("id"))
            if nid not in community_of:
                idx = len(clusters)
                clusters.append([nid])
                community_of[nid] = idx

        node_map = {str(n.get("id")): n for n in nodes}
        cluster_details = []
        for idx, members in enumerate(clusters):
            member_names = [node_map.get(m, {}).get("label", m) for m in members]
            cluster_details.append({
                "id": idx,
                "size": len(members),
                "members": members,
                "sample_labels": member_names[:5]
            })

        return {
            "algorithm": algorithm,
            "groups": len(clusters),
            "communityOf": community_of,
            "clusters": cluster_details
        }

    # -------------------------------------------------------------------------
    # 3. Link Prediction
    # -------------------------------------------------------------------------
    def predict_links(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], method: str = "jaccard") -> List[Dict[str, Any]]:
        """
        Predicts unseen conspirator relationships (triadic closure, money mules).
        Uses Jaccard coefficient, Adamic-Adar, or Resource Allocation.
        """
        if len(nodes) < 2:
            return []

        g = self._build_nx_graph(nodes, edges, directed=False)
        # Find non-edges
        non_edges = list(nx.non_edges(g))
        if not non_edges:
            return []

        # Limit candidate pairs if graph is massive
        if len(non_edges) > 500:
            import random
            non_edges = random.sample(non_edges, 500)

        predictions = []
        try:
            if method == "adamic_adar":
                preds = nx.adamic_adar_index(g, non_edges)
            elif method == "resource_allocation":
                preds = nx.resource_allocation_index(g, non_edges)
            else:
                preds = nx.jaccard_coefficient(g, non_edges)

            node_map = {str(n.get("id")): n for n in nodes}
            for u, v, p in preds:
                if p > 0:
                    u_node = node_map.get(u, {})
                    v_node = node_map.get(v, {})
                    predictions.append({
                        "source": u,
                        "target": v,
                        "source_label": u_node.get("label", u),
                        "target_label": v_node.get("label", v),
                        "source_type": u_node.get("type", "UNKNOWN"),
                        "target_type": v_node.get("type", "UNKNOWN"),
                        "score": round(float(p), 4),
                        "rationale": f"High triadic overlap under {method.replace('_', ' ').title()}"
                    })
        except Exception as e:
            logger.error("Link prediction error: %s", e)

        predictions.sort(key=lambda x: x["score"], reverse=True)
        return predictions[:25]

    # -------------------------------------------------------------------------
    # 4. Critical Bottlenecks & Articulation Points
    # -------------------------------------------------------------------------
    def find_network_bottlenecks(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Finds articulation points (cut vertices) whose removal fractures the syndicate.
        """
        if not nodes or not edges:
            return {"cut_vertices": [], "bridges": []}

        g = self._build_nx_graph(nodes, edges, directed=False)
        cut_vertices = []
        bridges = []

        try:
            cut_nodes = list(nx.articulation_points(g))
            node_map = {str(n.get("id")): n for n in nodes}
            for nid in cut_nodes:
                n_data = node_map.get(nid, {})
                cut_vertices.append({
                    "id": nid,
                    "label": n_data.get("label", nid),
                    "type": n_data.get("type", "UNKNOWN"),
                    "threat": n_data.get("threat_level", "HIGH"),
                    "explanation": "Critical communication bridge. Arresting this operative disconnects network components."
                })
        except Exception as e:
            logger.warning("Cut vertices error: %s", e)

        try:
            edge_bridges = list(nx.bridges(g))
            for u, v in edge_bridges:
                bridges.append({"source": u, "target": v})
        except Exception as e:
            logger.warning("Bridges error: %s", e)

        return {
            "cut_vertices": cut_vertices,
            "bridges": bridges[:10]
        }


default_network_analytics = NetworkAnalytics()
