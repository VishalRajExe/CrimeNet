"""
anomaly_detector.py - scikit-learn Isolation Forest Anomaly Detector
Detects anomalous criminal actors, money laundering funnel accounts,
and hub outliers using unsupervised ensemble isolation trees.
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import networkx as nx
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("crimenet.intelligence.anomaly")


class IsolationForestAnomalyDetector:
    def __init__(self, contamination: float = 0.15):
        self.contamination = contamination

    def extract_node_features(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Tuple[List[str], np.ndarray, Dict[str, Dict[str, float]]]:
        """
        Extracts multi-dimensional topological and financial features for every node in the graph:
        - degree (total connections)
        - in_degree (incoming funds/calls)
        - out_degree (outgoing transfers/calls)
        - pagerank (network influence)
        - betweenness (brokerage score)
        - clustering_coefficient (triad cohesion)
        - flow_volume (aggregated monetary/communication weight)
        - threat_prior (base threat score)
        """
        g_di = nx.DiGraph()
        g_un = nx.Graph()

        node_ids = []
        for n in nodes:
            nid = str(n.get("id"))
            node_ids.append(nid)
            g_di.add_node(nid, **n)
            g_un.add_node(nid, **n)

        # Track flow volume per node
        flow_volume = {nid: 0.0 for nid in node_ids}

        for e in edges:
            u = str(e.get("source"))
            v = str(e.get("target"))
            if u in flow_volume and v in flow_volume:
                amt_str = str(e.get("amount", e.get("volume", e.get("weight", "1"))))
                # clean amount string
                digits = "".join(ch for ch in amt_str if ch.isdigit() or ch == ".")
                try:
                    w = float(digits) if digits else 1.0
                except ValueError:
                    w = 1.0

                g_di.add_edge(u, v, weight=w)
                g_un.add_edge(u, v, weight=w)
                flow_volume[u] += w
                flow_volume[v] += w

        # Network metrics
        try:
            pr = nx.pagerank(g_un, alpha=0.85, max_iter=100)
        except Exception:
            pr = {n: 1.0 / max(1, len(node_ids)) for n in node_ids}

        try:
            bet = nx.betweenness_centrality(g_un, normalized=True)
        except Exception:
            bet = {n: 0.0 for n in node_ids}

        try:
            clust = nx.clustering(g_un)
        except Exception:
            clust = {n: 0.0 for n in node_ids}

        node_map = {str(n.get("id")): n for n in nodes}
        feature_matrix = []
        raw_metrics = {}

        for nid in node_ids:
            ndata = node_map.get(nid, {})
            deg = g_un.degree(nid)
            in_deg = g_di.in_degree(nid)
            out_deg = g_di.out_degree(nid)
            vol = flow_volume.get(nid, 0.0)
            threat = float(ndata.get("threat_score", 0.5))

            vec = [
                float(deg),
                float(in_deg),
                float(out_deg),
                float(pr.get(nid, 0.0)),
                float(bet.get(nid, 0.0)),
                float(clust.get(nid, 0.0)),
                math.log1p(vol),
                threat
            ]
            feature_matrix.append(vec)
            raw_metrics[nid] = {
                "degree": deg,
                "in_degree": in_deg,
                "out_degree": out_deg,
                "pagerank": round(float(pr.get(nid, 0.0)), 4),
                "betweenness": round(float(bet.get(nid, 0.0)), 4),
                "clustering": round(float(clust.get(nid, 0.0)), 4),
                "volume": vol,
                "threat": threat
            }

        return node_ids, np.array(feature_matrix, dtype=float), raw_metrics

    def detect_anomalies(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Runs scikit-learn Isolation Forest to detect anomalous nodes and explain their anomaly reasons.
        """
        if len(nodes) < 4:
            # Not enough nodes for statistical ensemble isolation
            return []

        node_ids, X, raw_metrics = self.extract_node_features(nodes, edges)

        # Standardize / fill NaNs
        X = np.nan_to_num(X, nan=0.0)

        # Determine contamination rate dynamically based on graph size
        contam = min(0.25, max(0.05, 2.0 / len(node_ids)))

        iso = IsolationForest(
            n_estimators=100,
            contamination=contam,
            random_state=42,
            n_jobs=-1
        )

        try:
            iso.fit(X)
            preds = iso.predict(X)  # -1 = anomaly, 1 = normal
            scores = iso.decision_function(X)  # lower = more abnormal
        except Exception as e:
            logger.error("IsolationForest fitting error: %s", e)
            return []

        node_map = {str(n.get("id")): n for n in nodes}
        anomalies = []

        # Find median metrics to construct explainable contrasts
        med_deg = float(np.median(X[:, 0])) if len(X) > 0 else 1.0
        med_bet = float(np.median(X[:, 4])) if len(X) > 0 else 0.0

        for idx, nid in enumerate(node_ids):
            pred = preds[idx]
            raw_score = scores[idx]
            ndata = node_map.get(nid, {})
            m = raw_metrics[nid]

            # Consider anomalous if IsolationForest flagged it or anomaly score is deeply negative
            if pred == -1 or raw_score < -0.05:
                # Anomaly confidence score normalized from 0.0 to 1.0
                norm_score = round(float(max(0.0, min(1.0, 0.5 - (raw_score * 1.5)))), 3)

                # Determine explainable forensic tags
                reasons = []
                tags = []
                if m["in_degree"] > m["out_degree"] * 2 and m["in_degree"] >= 3:
                    tags.append("Mule Funnel Account")
                    reasons.append(f"Inflow concentration: {m['in_degree']} incoming channels vs {m['out_degree']} exit transfers.")
                elif m["out_degree"] > m["in_degree"] * 2 and m["out_degree"] >= 3:
                    tags.append("Disbursement Spreader")
                    reasons.append(f"Rapid dispersal: funneling funds to {m['out_degree']} downstream accounts.")

                if m["betweenness"] > med_bet * 3 and m["betweenness"] > 0.1:
                    tags.append("Conduit Key Broker")
                    reasons.append(f"High betweenness centrality ({m['betweenness']}) bridging disconnected syndicates.")

                if m["degree"] > med_deg * 3:
                    tags.append("High-Degree Hub Outlier")
                    reasons.append(f"Topology hub outlier with {m['degree']} direct links (syndicate median is {int(med_deg)}).")

                if not tags:
                    tags.append("Structural Pattern Anomaly")
                    reasons.append(f"Isolation Forest flagged deviation in multidimensional feature vector (anomaly score: {raw_score:.3f}).")

                anomalies.append({
                    "id": nid,
                    "label": ndata.get("label", nid),
                    "type": ndata.get("type", "UNKNOWN"),
                    "threat_level": ndata.get("threat_level", "HIGH"),
                    "anomaly_score": norm_score,
                    "raw_score": round(float(raw_score), 4),
                    "tags": tags,
                    "reason": " ".join(reasons),
                    "metrics": m
                })

        # Sort anomalies by most suspicious first
        anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return anomalies


default_anomaly_detector = IsolationForestAnomalyDetector()
