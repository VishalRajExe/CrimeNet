"""Analytics Service for CrimeNet.

Single entry point for graph theory algorithms, community detection,
centrality metrics, link predictions, and anomaly detection.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import networkx as nx

from backend.intelligence.network_analytics import default_network_analytics
from backend.intelligence.anomaly_detector import default_anomaly_detector
from analyzer.path_analysis import shortest_path

logger = logging.getLogger("CrimeNet.AnalyticsService")


class AnalyticsService:
    def __init__(self):
        self.net_analytics = default_network_analytics
        self.anomaly_detector = default_anomaly_detector

    def compute_centrality(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], metric: str = "pagerank"
    ) -> Dict[str, Any]:
        """Compute PageRank, Betweenness, Closeness, or Degree centrality."""
        return self.net_analytics.compute_centrality(nodes, edges, metric=metric)

    def detect_communities(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], algorithm: str = "louvain"
    ) -> Dict[str, Any]:
        """Detect criminal subgroups and clusters."""
        return self.net_analytics.detect_communities(nodes, edges, algorithm=algorithm)

    def predict_links(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], method: str = "jaccard"
    ) -> List[Dict[str, Any]]:
        """Predict unobserved relationships between entities."""
        return self.net_analytics.predict_links(nodes, edges, method=method)

    def find_path(
        self, elements: List[Dict[str, Any]], source_id: str, target_id: str
    ) -> Dict[str, Any]:
        """Find shortest forensic evidentiary path between two entities."""
        return shortest_path(elements, {"source": source_id, "target": target_id})

    def detect_anomalies(
        self, case_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect transaction smurfing, odd-hour communications, and topological outliers."""
        return self.anomaly_detector.detect_anomalies(case_id, nodes, edges)


default_analytics_service = AnalyticsService()
