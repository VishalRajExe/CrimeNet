"""CrimeNet Anomaly Detection Engine — Isolation Forest.

Applies sklearn's IsolationForest to graph-structural and entity-level features
extracted from CrimeNet investigation networks to surface statistically unusual
entities for investigator review.

IMPORTANT DISCLAIMER:
═══════════════════════════════════════════════════════════════════════
An anomaly detected by this system is a STATISTICAL SIGNAL only.
It is NOT evidence of criminal activity and must NEVER be treated
as such without independent investigator verification.
Every flagged entity must be reviewed by a qualified investigator
before any operational or legal action is taken.
═══════════════════════════════════════════════════════════════════════

Anomaly types detected:
- UNUSUAL_COMMUNICATION_ACTIVITY  : Unusually high/low contact frequency
- UNUSUAL_NETWORK_BEHAVIOUR       : Bridge nodes, isolated clusters, structural gaps
- UNUSUAL_TRANSACTION_PATTERN     : Atypical financial connectivity (structuring, smurfing)
- HIGH_BETWEENNESS_ANOMALY        : Entity acting as critical hidden intermediary
- DEGREE_OUTLIER                  : Degree far outside the network distribution
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

logger = logging.getLogger("CrimeNet.AnomalyDetection")

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

ANOMALY_DISCLAIMER = (
    "⚠️ This is a STATISTICAL ANOMALY — not evidence of criminal activity. "
    "It requires independent investigator verification before any action."
)

ALERT_STATUSES = {"NEW", "REVIEWED", "DISMISSED", "CONFIRMED"}

ALERT_TYPE_LABELS = {
    "UNUSUAL_COMMUNICATION_ACTIVITY": "Unusual Communication Activity",
    "UNUSUAL_NETWORK_BEHAVIOUR":      "Unusual Network Behaviour",
    "UNUSUAL_TRANSACTION_PATTERN":    "Unusual Transaction Pattern",
    "HIGH_BETWEENNESS_ANOMALY":       "High Betweenness Anomaly",
    "DEGREE_OUTLIER":                 "Degree Outlier",
}


@dataclass
class AnomalyAlert:
    """A structured anomaly alert produced by the detection engine."""
    entity_id: str
    entity_name: str
    entity_type: str
    alert_type: str                          # e.g. UNUSUAL_COMMUNICATION_ACTIVITY
    severity: str                            # CRITICAL / HIGH / MEDIUM / LOW
    score: float                             # Raw Isolation Forest score (higher = more anomalous)
    anomaly_rank: float                      # Percentile rank 0–100 within this run
    reason: str                              # Human-readable explanation
    supporting_signals: Dict[str, Any]       # Raw feature values that triggered the flag
    source: str = "IsolationForest"
    status: str = "NEW"
    case_id: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------

def _extract_node_features(
    g: nx.Graph,
    nodes: Optional[List[str]] = None,
) -> Tuple[List[str], np.ndarray, Dict[str, Dict[str, float]]]:
    """
    Extract a rich feature vector for every node in the graph.

    Features computed:
      0  degree             – raw edge count
      1  weighted_degree    – sum of edge weights (1.0 if unweighted)
      2  in_degree          – for directed; falls back to degree
      3  out_degree         – for directed; falls back to degree
      4  clustering_coeff   – local clustering coefficient
      5  betweenness        – betweenness centrality
      6  closeness          – closeness centrality
      7  pagerank           – PageRank score
      8  is_bridge          – 1 if node is incident to at least one bridge edge

    :param g: NetworkX graph (directed or undirected)
    :param nodes: Optional list of node IDs to restrict to
    :returns: (ordered_node_ids, feature_matrix [N×9], raw_feature_dict)
    """
    ug = g.to_undirected() if g.is_directed() else g

    node_list = nodes if nodes is not None else list(g.nodes())
    node_list = [n for n in node_list if n in g.nodes()]

    # Degree
    degree = dict(g.degree())

    # Weighted degree
    w_degree: Dict[str, float] = {}
    for n in g.nodes():
        if g.is_directed():
            w_degree[n] = sum(
                g[n][nb].get("weight", 1.0) for nb in g.successors(n)
            ) + sum(
                g[nb][n].get("weight", 1.0) for nb in g.predecessors(n)
            )
        else:
            w_degree[n] = sum(g[n][nb].get("weight", 1.0) for nb in g.neighbors(n))

    # In/Out degree
    if g.is_directed():
        in_deg  = dict(g.in_degree())
        out_deg = dict(g.out_degree())
    else:
        in_deg  = degree
        out_deg = degree

    # Clustering (on undirected projection)
    try:
        clustering = nx.clustering(ug)
    except Exception:
        clustering = {n: 0.0 for n in ug.nodes()}

    # Betweenness centrality
    try:
        if len(g.nodes()) > 500:
            btwn = nx.betweenness_centrality(g, k=min(100, len(g.nodes())), normalized=True)
        else:
            btwn = nx.betweenness_centrality(g, normalized=True)
    except Exception:
        btwn = {n: 0.0 for n in g.nodes()}

    # Closeness centrality
    try:
        close = nx.closeness_centrality(ug)
    except Exception:
        close = {n: 0.0 for n in g.nodes()}

    # PageRank
    try:
        pr = nx.pagerank(ug, alpha=0.85, max_iter=200)
    except Exception:
        pr = {n: 1.0 / max(len(g.nodes()), 1) for n in g.nodes()}

    # Bridge membership – nodes incident to bridge edges
    bridge_nodes: set = set()
    try:
        for u, v in nx.bridges(ug):
            bridge_nodes.add(u)
            bridge_nodes.add(v)
    except Exception:
        pass

    # Build feature dict for reference
    raw: Dict[str, Dict[str, float]] = {}
    matrix_rows: List[List[float]] = []

    for n in node_list:
        feats = {
            "degree":          float(degree.get(n, 0)),
            "weighted_degree": float(w_degree.get(n, 0)),
            "in_degree":       float(in_deg.get(n, 0)),
            "out_degree":      float(out_deg.get(n, 0)),
            "clustering_coeff": float(clustering.get(n, 0.0)),
            "betweenness":     float(btwn.get(n, 0.0)),
            "closeness":       float(close.get(n, 0.0)),
            "pagerank":        float(pr.get(n, 0.0)),
            "is_bridge":       1.0 if n in bridge_nodes else 0.0,
        }
        raw[n] = feats
        matrix_rows.append([
            feats["degree"],
            feats["weighted_degree"],
            feats["in_degree"],
            feats["out_degree"],
            feats["clustering_coeff"],
            feats["betweenness"],
            feats["closeness"],
            feats["pagerank"],
            feats["is_bridge"],
        ])

    X = np.array(matrix_rows, dtype=np.float32)
    return node_list, X, raw


# ---------------------------------------------------------------------------
# Anomaly Typing
# ---------------------------------------------------------------------------

def _classify_anomaly_type(
    feats: Dict[str, float],
    network_stats: Dict[str, float],
    entity_type: str,
) -> Tuple[str, str, str]:
    """
    Given the raw features of an anomalous node, decide the most appropriate
    alert type, severity, and a concise reason string.

    Returns: (alert_type, severity, reason)
    """
    deg  = feats.get("degree", 0)
    btwn = feats.get("betweenness", 0.0)
    clst = feats.get("clustering_coeff", 0.0)
    is_b = feats.get("is_bridge", 0.0)

    mean_deg  = network_stats.get("mean_degree", 1.0)
    std_deg   = network_stats.get("std_degree", 1.0)
    mean_btwn = network_stats.get("mean_betweenness", 0.0)

    etype_lower = (entity_type or "").lower()
    is_financial = etype_lower in {"account", "bank_account", "transaction"}
    is_comm      = etype_lower in {"phone", "person"}

    z_deg  = (deg  - mean_deg)  / max(std_deg,  1e-9)
    z_btwn = (btwn - mean_btwn) / max(mean_btwn * 2, 1e-9)

    # Decide type
    if is_financial and deg > mean_deg + 2 * std_deg:
        alert_type = "UNUSUAL_TRANSACTION_PATTERN"
        reason = (
            f"Entity has {int(deg)} financial connections, "
            f"{z_deg:.1f}× standard deviations above network mean ({mean_deg:.1f}). "
            "May indicate structuring, layering, or smurfing behaviour."
        )
    elif is_b > 0 and btwn > mean_btwn * 3:
        alert_type = "UNUSUAL_NETWORK_BEHAVIOUR"
        reason = (
            f"Entity is a BRIDGE NODE with betweenness centrality {btwn:.4f}, "
            f"{z_btwn:.1f}× above average. "
            "Removing this entity would disconnect network components."
        )
    elif is_comm and deg > mean_deg + 2 * std_deg:
        alert_type = "UNUSUAL_COMMUNICATION_ACTIVITY"
        reason = (
            f"Entity has {int(deg)} communication links, "
            f"{z_deg:.1f} std-devs above mean ({mean_deg:.1f}). "
            "Unusual volume may warrant further review."
        )
    elif btwn > mean_btwn * 4 and deg <= mean_deg:
        alert_type = "HIGH_BETWEENNESS_ANOMALY"
        reason = (
            f"Entity has low degree ({int(deg)}) but very high betweenness "
            f"centrality ({btwn:.4f}). Potential hidden intermediary or broker."
        )
    elif abs(z_deg) > 2.5:
        alert_type = "DEGREE_OUTLIER"
        reason = (
            f"Entity's connectivity ({int(deg)} links) is a statistical outlier "
            f"({z_deg:+.1f} std-devs from mean). "
            "Degree is unusually {'high' if z_deg > 0 else 'low'} for this network."
        )
    else:
        alert_type = "UNUSUAL_NETWORK_BEHAVIOUR"
        reason = (
            f"Entity exhibits an unusual combination of structural features: "
            f"degree={int(deg)}, betweenness={btwn:.4f}, "
            f"clustering={clst:.3f}. Statistical profile is atypical."
        )

    # Severity based on z-score magnitude
    max_z = max(abs(z_deg), abs(z_btwn))
    if max_z > 4.0 or is_b:
        severity = "HIGH"
    elif max_z > 2.5:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return alert_type, severity, reason


# ---------------------------------------------------------------------------
# Core Detection Engine
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """
    Isolation Forest anomaly detector for CrimeNet investigation networks.

    Usage:
        detector = AnomalyDetector(contamination=0.05)
        alerts = detector.detect(networkx_graph, entity_metadata)
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 200,
        random_state: int = 42,
    ):
        """
        :param contamination: Expected fraction of anomalous nodes (0.01–0.20).
        :param n_estimators: Number of base estimators in the Isolation Forest.
        :param random_state: RNG seed for reproducibility.
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._model: Optional[IsolationForest] = None
        self._scaler: Optional[StandardScaler] = None

    def detect(
        self,
        graph: nx.Graph,
        entity_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        case_id: Optional[str] = None,
        min_nodes: int = 5,
    ) -> List[AnomalyAlert]:
        """
        Run anomaly detection on the provided graph.

        :param graph: NetworkX graph. Nodes must be identifiable by string ID.
        :param entity_metadata: Optional dict {node_id: {name, type, ...}}.
        :param case_id: Case ID for traceability.
        :param min_nodes: Minimum node count to run detection.
        :returns: List of AnomalyAlert objects for statistically anomalous nodes.
        """
        if entity_metadata is None:
            entity_metadata = {}

        n_nodes = graph.number_of_nodes()
        if n_nodes < min_nodes:
            logger.warning(
                "Graph has only %d nodes (min %d). Skipping anomaly detection.",
                n_nodes, min_nodes,
            )
            return []

        logger.info(
            "Running Isolation Forest on %d nodes, %d edges...",
            n_nodes, graph.number_of_edges(),
        )

        # Extract features
        node_ids, X, raw_feats = _extract_node_features(graph)
        if X.shape[0] == 0:
            return []

        # Fit scaler + Isolation Forest
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        eff_contamination = min(self.contamination, (n_nodes - 1) / n_nodes)
        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=eff_contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(X_scaled)

        # Predictions: -1 = anomaly, +1 = normal
        preds   = self._model.predict(X_scaled)
        # decision_function: lower = more anomalous
        scores  = -self._model.decision_function(X_scaled)  # negate so higher = more anomalous

        # Compute network-level statistics for anomaly classification
        degrees = [d for _, d in graph.degree()]
        btwns   = list(nx.betweenness_centrality(graph, normalized=True).values()) if n_nodes <= 500 else [0]
        network_stats = {
            "mean_degree":       float(np.mean(degrees)),
            "std_degree":        float(np.std(degrees)),
            "mean_betweenness":  float(np.mean(btwns)),
        }

        # Rank all scores into percentile 0-100
        score_arr = np.array(scores)
        rank_pcts = (score_arr.argsort().argsort() / max(len(score_arr) - 1, 1)) * 100

        alerts: List[AnomalyAlert] = []
        for idx, node_id in enumerate(node_ids):
            if preds[idx] != -1:
                continue  # Not anomalous

            meta   = entity_metadata.get(str(node_id), {})
            e_name = meta.get("name") or meta.get("label") or str(node_id)
            e_type = meta.get("type") or "UNKNOWN"
            feats  = raw_feats[node_id]

            alert_type, severity, reason = _classify_anomaly_type(
                feats, network_stats, e_type
            )

            reason = f"{reason}\n\n{ANOMALY_DISCLAIMER}"

            alert = AnomalyAlert(
                entity_id=str(node_id),
                entity_name=e_name,
                entity_type=e_type,
                alert_type=alert_type,
                severity=severity,
                score=round(float(scores[idx]), 6),
                anomaly_rank=round(float(rank_pcts[idx]), 1),
                reason=reason,
                supporting_signals={
                    k: round(float(v), 6) for k, v in feats.items()
                },
                source="IsolationForest/NetworkFeatures",
                status="NEW",
                case_id=case_id,
            )
            alerts.append(alert)

        # Sort by score descending (most anomalous first)
        alerts.sort(key=lambda a: a.score, reverse=True)

        logger.info(
            "Anomaly detection complete: %d anomalies detected from %d nodes.",
            len(alerts), n_nodes,
        )
        return alerts

    def detect_from_network(
        self,
        network: Dict[str, Any],
        case_id: Optional[str] = None,
    ) -> List[AnomalyAlert]:
        """
        Detect anomalies from a CrimeNet network dict (edge-list format).

        :param network: Network dict with 'nodes' and 'edges' lists (CrimeNet standard).
        :param case_id: Optional case identifier.
        """
        import analyzer.common.helpers as helpers

        try:
            g, node_ids_list = helpers.convert_to_nx_undirected_graph(network)
        except Exception as exc:
            logger.error("Failed to convert network to NetworkX: %s", exc)
            return []

        # Build entity_metadata from node_ids_list (list of original names)
        entity_metadata = {}
        nodes_data = network.get("nodes", [])
        for i, orig_id in enumerate(node_ids_list):
            # node_ids_list[i] = original node name; the networkx node index = i
            if isinstance(nodes_data, list) and i < len(nodes_data):
                nd = nodes_data[i] if isinstance(nodes_data[i], dict) else {}
                entity_metadata[i] = {
                    "name": nd.get("name") or nd.get("label") or orig_id,
                    "type": nd.get("type") or nd.get("entity_type") or "UNKNOWN",
                }
            else:
                entity_metadata[i] = {"name": orig_id, "type": "UNKNOWN"}

        return self.detect(g, entity_metadata=entity_metadata, case_id=case_id)


# ---------------------------------------------------------------------------
# Convenience: Detect from CaseDataService graph
# ---------------------------------------------------------------------------

def detect_from_case(
    case_id: str,
    contamination: float = 0.05,
    persist_alerts: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run the full anomaly detection pipeline for a CrimeNet case and optionally
    persist the detected alerts to the database.

    :param case_id: Case ID to analyse.
    :param contamination: Fraction of nodes expected to be anomalous (0.01–0.20).
    :param persist_alerts: If True, save alerts to the database via CaseDataService.
    :returns: List of anomaly alert dicts.
    """
    from storage.case_data_service import CaseDataService

    svc = CaseDataService()
    graph_data = svc.get_case_graph(case_id)
    if not graph_data or not graph_data.get("elements"):
        logger.warning("No graph data for case %s", case_id)
        return []

    # Build NetworkX graph from elements
    g = nx.DiGraph()
    entity_metadata: Dict[str, Dict[str, Any]] = {}

    for el in graph_data["elements"]:
        d = el.get("data", {})
        if el.get("group") == "nodes":
            nid = d["id"]
            g.add_node(nid)
            entity_metadata[nid] = {
                "name": d.get("name") or d.get("label") or nid,
                "type": d.get("type") or "UNKNOWN",
            }
        elif el.get("group") == "edges":
            g.add_edge(
                d["source"],
                d["target"],
                weight=float(d.get("confidence", 1.0)),
            )

    if g.number_of_nodes() < 5:
        logger.warning("Graph for case %s has fewer than 5 nodes. Skipping.", case_id)
        return []

    detector = AnomalyDetector(contamination=contamination)
    alerts = detector.detect(g, entity_metadata=entity_metadata, case_id=case_id)

    if persist_alerts:
        for alert in alerts:
            try:
                alert_id = svc.create_alert(
                    case_id=case_id,
                    alert_type=alert.alert_type,
                    title=ALERT_TYPE_LABELS.get(alert.alert_type, alert.alert_type),
                    explanation=alert.reason,
                    severity=alert.severity,
                    subject=alert.entity_name,
                    related_entities=json.dumps({
                        "entity_id": alert.entity_id,
                        "entity_type": alert.entity_type,
                        "score": alert.score,
                        "anomaly_rank": alert.anomaly_rank,
                        "source": alert.source,
                        "status": "NEW",
                        "review_time": None,
                        "supporting_signals": alert.supporting_signals,
                    }),
                )
                alert.case_id = case_id
                logger.info("Persisted alert %s for entity '%s'", alert_id, alert.entity_name)
            except Exception as exc:
                logger.warning("Failed to persist alert for %s: %s", alert.entity_name, exc)

    return [a.to_dict() for a in alerts]


# ---------------------------------------------------------------------------
# Module-level info
# ---------------------------------------------------------------------------

def get_info() -> Dict[str, Any]:
    """Return metadata about the anomaly detection module."""
    return {
        "name": "Anomaly Detection",
        "engine": "Isolation Forest (sklearn)",
        "disclaimer": ANOMALY_DISCLAIMER,
        "alert_types": ALERT_TYPE_LABELS,
        "severity_levels": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "statuses": list(ALERT_STATUSES),
        "features_used": [
            "degree", "weighted_degree", "in_degree", "out_degree",
            "clustering_coefficient", "betweenness_centrality",
            "closeness_centrality", "pagerank", "is_bridge_node",
        ],
    }
