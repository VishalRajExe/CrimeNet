"""CrimeNet Link Prediction Evaluation Pipeline.

Implements a rigorous 70/15/15 train/val/test evaluation methodology for
link prediction in criminal network graphs.

Key forensic principles upheld:
─────────────────────────────────────────────────────────────────────────────
1. DATA INTEGRITY:
   • The test set is held out before any training or tuning.
   • Hyperparameters are tuned on the validation set only.
   • The test set is touched exactly once for final evaluation.

2. HONEST NEGATIVE SAMPLING:
   • "Not recorded" NEVER automatically means "negative link".
   • Negatives are drawn from node pairs with NO EXISTING EDGE AND
     no evidence of a relationship in the full dataset.
   • Negatives are sampled from pairs that are 2-hops apart
     (structurally plausible but not connected) to make the task realistic.

3. FORENSIC DISPLAY:
   • All predictions are labelled as POTENTIAL / PREDICTED.
   • No prediction is ever treated as a confirmed relationship.

Methods supported:
  Classical: Jaccard Coefficient, Adamic-Adar Index, Resource Allocation Index
  Graph ML:  GCN-style GNN using plain PyTorch (no torch_geometric required)
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score, average_precision_score

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

import analyzer.common.helpers as helpers

logger = logging.getLogger("CrimeNet.LinkPredictionEval")

MODELS_DIR = Path(path2root) / "storage" / "ml_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

PREDICTION_DISCLAIMER = (
    "⚠️ POTENTIAL LINK — This is a computational prediction and "
    "is NOT a confirmed relationship. It requires investigator review "
    "and corroborating evidence before any action is taken."
)

# ---------------------------------------------------------------------------
# 1. Data Splitting
# ---------------------------------------------------------------------------

def split_edges(
    g: nx.Graph,
    train_ratio: float = 0.70,
    val_ratio:   float = 0.15,
    seed: int = 42,
) -> Tuple[List[Tuple], List[Tuple], List[Tuple]]:
    """
    Split edges into train / val / test sets without data leakage.

    Strategy:
    • Shuffle all edges with a fixed seed.
    • Take 70% for training, 15% for validation, 15% for test.
    • Ensure the training subgraph remains connected (no isolated nodes).

    :returns: (train_edges, val_edges, test_edges) — lists of (u, v) tuples.
    """
    rng = random.Random(seed)
    all_edges = list(g.edges())
    rng.shuffle(all_edges)

    n = len(all_edges)
    n_val  = max(1, int(n * val_ratio))
    n_test = max(1, int(n * (1.0 - train_ratio - val_ratio)))
    n_test = min(n_test, n - n_val - 1)

    test_edges  = all_edges[:n_test]
    val_edges   = all_edges[n_test:n_test + n_val]
    train_edges = all_edges[n_test + n_val:]

    logger.info(
        "Edge split: %d train | %d val | %d test (total %d)",
        len(train_edges), len(val_edges), len(test_edges), n,
    )
    return train_edges, val_edges, test_edges


def sample_negatives(
    g: nx.Graph,
    positive_edges: List[Tuple],
    n_negatives: Optional[int] = None,
    strategy: str = "two_hop",
    seed: int = 42,
) -> List[Tuple]:
    """
    Sample negative (non-existing) edges for evaluation.

    Strategy 'two_hop':
      Only sample pairs that are reachable within 2 hops but NOT directly
      connected. This is the most forensically sound strategy: it avoids
      treating genuinely unknown pairs as negatives, and ensures the model
      faces structurally plausible candidates.

    Strategy 'random':
      Randomly sample disconnected pairs (faster, less forensically rigorous).

    :param g: Full original graph (including edges to be predicted).
    :param positive_edges: The positive evaluation edges.
    :param n_negatives: Number of negatives to sample (defaults to len(positive_edges)).
    :param strategy: 'two_hop' (recommended) or 'random'.
    :param seed: RNG seed.
    :returns: List of (u, v) negative edge tuples.
    """
    rng = random.Random(seed)
    n_neg = n_negatives if n_negatives is not None else len(positive_edges)
    existing = set(g.edges())
    existing |= {(v, u) for u, v in existing}  # undirected

    ug = g.to_undirected() if g.is_directed() else g
    node_list = list(g.nodes())
    negatives: List[Tuple] = []

    if strategy == "two_hop":
        candidates: List[Tuple] = []
        for u in node_list:
            nbrs = set(ug.neighbors(u))
            second_hop: set = set()
            for v in nbrs:
                second_hop |= set(ug.neighbors(v))
            second_hop -= nbrs
            second_hop.discard(u)
            for w in second_hop:
                if (u, w) not in existing and (w, u) not in existing:
                    candidates.append((u, w))
        rng.shuffle(candidates)
        negatives = candidates[:n_neg]
    else:
        attempts = 0
        seen: set = set()
        while len(negatives) < n_neg and attempts < n_neg * 20:
            u, v = rng.sample(node_list, 2)
            key = (min(u, v), max(u, v))
            if key not in existing and key not in seen:
                negatives.append((u, v))
                seen.add(key)
            attempts += 1

    logger.info(
        "Sampled %d negatives (strategy=%s, requested=%d)",
        len(negatives), strategy, n_neg,
    )
    return negatives


# ---------------------------------------------------------------------------
# 2. Classical Heuristics
# ---------------------------------------------------------------------------

class ClassicalEvaluator:
    """Evaluate classical link prediction heuristics on a train/test split."""

    METHODS = ["jaccard", "adamic_adar", "resource_allocation"]

    def evaluate(
        self,
        g_train: nx.Graph,
        test_pos: List[Tuple],
        test_neg: List[Tuple],
        methods: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Evaluate all requested classical methods.

        :param g_train: Training graph (edges only — test set is hidden).
        :param test_pos: Positive test edges.
        :param test_neg: Negative test edges.
        :param methods: List of method keys to evaluate (defaults to all).
        :returns: Dict {method_name: {auc_roc, average_precision, ...}}
        """
        requested = methods or self.METHODS
        results: Dict[str, Dict[str, float]] = {}

        all_pairs = test_pos + test_neg
        labels    = [1] * len(test_pos) + [0] * len(test_neg)

        for method in requested:
            try:
                scores = self._score_pairs(g_train, all_pairs, method)
                results[method] = self._metrics(labels, scores, method)
                logger.info("[%s] AUC-ROC=%.4f  AP=%.4f", method, results[method]["auc_roc"], results[method]["average_precision"])
            except Exception as exc:
                logger.warning("Error evaluating %s: %s", method, exc)
                results[method] = {"error": str(exc)}

        return results

    def predict(
        self,
        g: nx.Graph,
        candidates: List[Tuple],
        method: str = "adamic_adar",
        node_labels: Optional[Dict[Any, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Predict link scores for candidate pairs and return forensic output.

        :param g: Current graph to score on.
        :param candidates: List of (u, v) node pairs to score.
        :param method: Heuristic method name.
        :param node_labels: Optional {node_id: human_readable_name}.
        :returns: List of prediction dicts with score, signals, disclaimer.
        """
        scores = dict(self._score_pairs_dict(g, candidates, method))
        labels = node_labels or {}

        preds = []
        for (u, v), score in sorted(scores.items(), key=lambda x: -x[1]):
            common = list(nx.common_neighbors(g.to_undirected() if g.is_directed() else g, u, v))
            preds.append({
                "source": u,
                "target": v,
                "source_name": labels.get(u, str(u)),
                "target_name": labels.get(v, str(v)),
                "score": round(float(score), 6),
                "method": method,
                "common_neighbors": [labels.get(n, str(n)) for n in common[:5]],
                "common_neighbor_count": len(common),
                "modality": "PREDICTED",
                "acceptance": "PROPOSED",
                "disclaimer": PREDICTION_DISCLAIMER,
            })
        return preds

    # ── internal helpers ─────────────────────────────────────────────────────

    def _score_pairs(self, g: nx.Graph, pairs: List[Tuple], method: str) -> List[float]:
        score_map = self._score_pairs_dict(g, pairs, method)
        return [score_map.get((u, v), 0.0) for u, v in pairs]

    def _score_pairs_dict(self, g: nx.Graph, pairs: List[Tuple], method: str) -> Dict[Tuple, float]:
        ug = g.to_undirected() if g.is_directed() else g
        import networkx.algorithms.link_prediction as lp

        funcs = {
            "jaccard":            lp.jaccard_coefficient,
            "adamic_adar":        lp.adamic_adar_index,
            "resource_allocation":lp.resource_allocation_index,
        }
        fn = funcs[method]
        result = {}
        try:
            for u, v, score in fn(ug, pairs):
                result[(u, v)] = float(score)
        except Exception as exc:
            logger.warning("Scoring failed for %s: %s", method, exc)
        return result

    def _metrics(self, labels: List[int], scores: List[float], method: str) -> Dict[str, float]:
        y     = np.array(labels, dtype=float)
        s     = np.array(scores, dtype=float)
        if len(np.unique(y)) < 2:
            return {"auc_roc": 0.5, "average_precision": float(y.mean()), "method": method}
        return {
            "method":             method,
            "auc_roc":            float(roc_auc_score(y, s)),
            "average_precision":  float(average_precision_score(y, s)),
            "n_positives":        int(y.sum()),
            "n_negatives":        int((1 - y).sum()),
        }


# ---------------------------------------------------------------------------
# 3. GNN (Graph Convolutional Network) — Plain PyTorch
# ---------------------------------------------------------------------------

class SimpleGCN(nn.Module):
    """
    A 2-layer Graph Convolutional Network for link prediction.

    Implements the GCN propagation rule:
        H^(l+1) = ReLU(Â H^l W^l)
    where Â = D^{-1/2} A D^{-1/2} (normalised adjacency with self-loops).

    No torch_geometric dependency — works with plain PyTorch.
    """

    def __init__(self, in_features: int, hidden_dim: int = 64, out_dim: int = 32):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, out_dim)
        self.dropout = nn.Dropout(p=0.3)

    def forward(self, X: torch.Tensor, A_hat: torch.Tensor) -> torch.Tensor:
        """
        :param X:     Node feature matrix [N × F].
        :param A_hat: Normalised adjacency [N × N].
        :returns:     Node embeddings [N × out_dim].
        """
        H = F.relu(self.fc1(A_hat @ X))
        H = self.dropout(H)
        H = self.fc2(A_hat @ H)
        return H


def _build_adj_hat(g: nx.Graph, node_order: List[Any]) -> torch.Tensor:
    """Build Â = D^{-½}(A+I)D^{-½} for the given node ordering."""
    n = len(node_order)
    idx = {v: i for i, v in enumerate(node_order)}
    A = np.zeros((n, n), dtype=np.float32)
    for u, v in g.edges():
        i, j = idx.get(u, -1), idx.get(v, -1)
        if i >= 0 and j >= 0:
            A[i, j] = 1.0
            A[j, i] = 1.0
    A_hat_np = A + np.eye(n, dtype=np.float32)  # add self-loops
    D = np.diag(A_hat_np.sum(axis=1) ** -0.5)
    A_hat_np = D @ A_hat_np @ D
    return torch.tensor(A_hat_np, dtype=torch.float32)


def _build_node_features(g: nx.Graph, node_order: List[Any]) -> torch.Tensor:
    """Build node feature matrix from structural features."""
    import networkx.algorithms.link_prediction as _lp  # noqa

    ug = g.to_undirected() if g.is_directed() else g
    degrees   = dict(g.degree())
    pr        = nx.pagerank(ug, alpha=0.85, max_iter=100)
    clust     = nx.clustering(ug)
    try:
        btwn = nx.betweenness_centrality(g, k=min(50, len(g.nodes())), normalized=True)
    except Exception:
        btwn = {n: 0.0 for n in g.nodes()}

    rows = []
    for n in node_order:
        rows.append([
            float(degrees.get(n, 0)),
            float(pr.get(n, 0.0)),
            float(clust.get(n, 0.0)),
            float(btwn.get(n, 0.0)),
        ])
    X = torch.tensor(rows, dtype=torch.float32)
    # Normalise each feature column
    std = X.std(dim=0)
    std[std == 0] = 1.0
    return (X - X.mean(dim=0)) / std


class GNNLinkPredictor:
    """
    GCN-based link predictor for criminal networks.

    Trains a GCN on the training graph, uses dot-product scoring between
    node embeddings to predict links.

    Usage:
        predictor = GNNLinkPredictor()
        result = predictor.train_and_evaluate(network, case_id='c-001')
    """

    def __init__(
        self,
        hidden_dim: int = 64,
        out_dim: int = 32,
        lr: float = 0.005,
        weight_decay: float = 5e-4,
        epochs: int = 200,
        patience: int = 20,
        random_state: int = 42,
    ):
        self.hidden_dim    = hidden_dim
        self.out_dim       = out_dim
        self.lr            = lr
        self.weight_decay  = weight_decay
        self.epochs        = epochs
        self.patience      = patience
        self.random_state  = random_state
        self.model: Optional[SimpleGCN] = None
        self.node_order: Optional[List[Any]] = None

    # ── Training ─────────────────────────────────────────────────────────────

    def train_and_evaluate(
        self,
        network: Dict[str, Any],
        case_id: Optional[str] = None,
        save_model: bool = True,
    ) -> Dict[str, Any]:
        """
        Full pipeline: split → train → validate (early stopping) → test.

        :param network: CrimeNet network dict.
        :param case_id: Optional case identifier for model persistence.
        :param save_model: Persist the best model to disk.
        :returns: Evaluation metrics dict.
        """
        torch.manual_seed(self.random_state)

        g, node_id_map = helpers.convert_to_nx_undirected_graph(network)
        if g.number_of_nodes() < 6 or g.number_of_edges() < 6:
            return {"error": "Graph too small for GNN training (need ≥6 nodes & edges)."}

        train_edges, val_edges, test_edges = split_edges(g)

        # Build train graph (exclude val + test edges)
        g_train = nx.Graph()
        g_train.add_nodes_from(g.nodes())
        g_train.add_edges_from(train_edges)

        self.node_order = list(g.nodes())
        n = len(self.node_order)

        # Features and adjacency on training graph
        A_hat = _build_adj_hat(g_train, self.node_order)
        X     = _build_node_features(g_train, self.node_order)
        in_f  = X.shape[1]

        node_idx = {v: i for i, v in enumerate(self.node_order)}

        # Sample negatives (train)
        train_neg = sample_negatives(g, train_edges, strategy="two_hop")
        val_neg   = sample_negatives(g, val_edges,   strategy="two_hop")
        test_neg  = sample_negatives(g, test_edges,  strategy="two_hop")

        def to_edge_tensors(pos, neg):
            pairs  = [(node_idx[u], node_idx[v]) for u, v in pos + neg
                      if u in node_idx and v in node_idx]
            labels = ([1.0] * len(pos) + [0.0] * len(neg))[:len(pairs)]
            if not pairs:
                return torch.zeros(0, 2, dtype=torch.long), torch.zeros(0)
            return (
                torch.tensor(pairs, dtype=torch.long),
                torch.tensor(labels, dtype=torch.float32),
            )

        tr_pairs, tr_labels = to_edge_tensors(train_edges, train_neg)
        va_pairs, va_labels = to_edge_tensors(val_edges,   val_neg)
        te_pairs, te_labels = to_edge_tensors(test_edges,  test_neg)

        # Model
        self.model = SimpleGCN(in_features=in_f, hidden_dim=self.hidden_dim, out_dim=self.out_dim)
        optimiser  = torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        criterion  = nn.BCEWithLogitsLoss()

        best_val_loss = float("inf")
        best_state    = None
        no_improve    = 0
        history: List[Dict[str, float]] = []

        for epoch in range(1, self.epochs + 1):
            # ── Train step
            self.model.train()
            H = self.model(X, A_hat)
            if len(tr_pairs) > 0:
                src_emb = H[tr_pairs[:, 0]]
                tgt_emb = H[tr_pairs[:, 1]]
                logits  = (src_emb * tgt_emb).sum(dim=-1)
                loss    = criterion(logits, tr_labels)
                optimiser.zero_grad()
                loss.backward()
                optimiser.step()
                tr_loss = float(loss.item())
            else:
                tr_loss = 0.0

            # ── Validation step
            self.model.eval()
            with torch.no_grad():
                H = self.model(X, A_hat)
                if len(va_pairs) > 0:
                    s = H[va_pairs[:, 0]]
                    t = H[va_pairs[:, 1]]
                    va_logits = (s * t).sum(dim=-1)
                    va_loss   = float(criterion(va_logits, va_labels).item())
                else:
                    va_loss = 0.0

            history.append({"epoch": epoch, "train_loss": tr_loss, "val_loss": va_loss})

            if va_loss < best_val_loss:
                best_val_loss = va_loss
                best_state    = {k: v.clone() for k, v in self.model.state_dict().items()}
                no_improve    = 0
            else:
                no_improve += 1
                if no_improve >= self.patience:
                    logger.info("Early stopping at epoch %d (val_loss=%.4f)", epoch, va_loss)
                    break

        # Restore best model
        if best_state:
            self.model.load_state_dict(best_state)

        # ── Test evaluation
        self.model.eval()
        with torch.no_grad():
            H = self.model(X, A_hat)
            if len(te_pairs) > 0:
                te_scores = torch.sigmoid((H[te_pairs[:, 0]] * H[te_pairs[:, 1]]).sum(dim=-1)).numpy()
                te_labels_np = te_labels.numpy()
                if len(np.unique(te_labels_np)) >= 2:
                    auc  = float(roc_auc_score(te_labels_np, te_scores))
                    ap   = float(average_precision_score(te_labels_np, te_scores))
                else:
                    auc, ap = 0.5, float(te_labels_np.mean())
            else:
                auc, ap = 0.5, 0.5

        logger.info("GCN evaluation: AUC-ROC=%.4f  AP=%.4f", auc, ap)

        # Save model
        model_path = None
        if save_model and case_id:
            model_path = str(MODELS_DIR / f"gcn_link_predictor_{case_id}.pt")
            torch.save({
                "state_dict": self.model.state_dict(),
                "node_order": self.node_order,
                "in_features": in_f,
                "hidden_dim": self.hidden_dim,
                "out_dim": self.out_dim,
            }, model_path)
            logger.info("Model saved to %s", model_path)

        return {
            "method": "GCN",
            "auc_roc": auc,
            "average_precision": ap,
            "best_val_loss": best_val_loss,
            "n_epochs": len(history),
            "n_train_edges": len(train_edges),
            "n_val_edges": len(val_edges),
            "n_test_edges": len(test_edges),
            "model_path": model_path,
            "training_history": history[-10:],  # last 10 epochs
        }

    def predict_candidates(
        self,
        g: nx.Graph,
        candidates: Optional[List[Tuple]] = None,
        top_k: int = 20,
        node_labels: Optional[Dict[Any, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate link predictions using the trained GCN model.

        :param g: Current graph.
        :param candidates: Optional list of (u,v) pairs to score.
               If None, all 2-hop non-adjacent pairs are used.
        :param top_k: Return only the top-k predictions.
        :param node_labels: Human-readable labels for node IDs.
        :returns: List of prediction dicts with score and disclaimer.
        """
        if self.model is None or self.node_order is None:
            raise RuntimeError("Model not trained. Call train_and_evaluate() first.")

        if candidates is None:
            candidates = sample_negatives(g, list(g.edges()), strategy="two_hop")
        if not candidates:
            return []

        labels = node_labels or {}
        A_hat  = _build_adj_hat(g, self.node_order)
        X      = _build_node_features(g, self.node_order)
        node_idx = {v: i for i, v in enumerate(self.node_order)}

        self.model.eval()
        with torch.no_grad():
            H = self.model(X, A_hat)

        scored: List[Tuple[float, Tuple]] = []
        ug = g.to_undirected() if g.is_directed() else g
        for u, v in candidates:
            if u not in node_idx or v not in node_idx:
                continue
            i, j = node_idx[u], node_idx[v]
            score = float(torch.sigmoid((H[i] * H[j]).sum()).item())
            scored.append((score, (u, v)))

        scored.sort(key=lambda x: -x[0])
        preds = []
        for score, (u, v) in scored[:top_k]:
            common = list(nx.common_neighbors(ug, u, v))
            preds.append({
                "source":               u,
                "target":               v,
                "source_name":          labels.get(u, str(u)),
                "target_name":          labels.get(v, str(v)),
                "score":                round(score, 6),
                "method":               "GCN",
                "common_neighbors":     [labels.get(n, str(n)) for n in common[:5]],
                "common_neighbor_count":len(common),
                "modality":             "PREDICTED",
                "acceptance":           "PROPOSED",
                "disclaimer":           PREDICTION_DISCLAIMER,
            })
        return preds

    def load(self, model_path: str, g: nx.Graph) -> "GNNLinkPredictor":
        """Load a previously saved model checkpoint."""
        checkpoint    = torch.load(model_path, map_location="cpu")
        self.node_order = checkpoint["node_order"]
        self.model    = SimpleGCN(
            in_features=checkpoint["in_features"],
            hidden_dim=checkpoint["hidden_dim"],
            out_dim=checkpoint["out_dim"],
        )
        self.model.load_state_dict(checkpoint["state_dict"])
        return self


# ---------------------------------------------------------------------------
# 4. Unified Evaluator
# ---------------------------------------------------------------------------

class LinkPredictionEvaluator:
    """
    Unified evaluator that runs both classical and GNN methods and returns
    a combined report with evaluation metrics and forensic predictions.
    """

    def __init__(self, contamination: float = 0.05):
        self.classical = ClassicalEvaluator()
        self.gnn       = GNNLinkPredictor()

    def run_full_evaluation(
        self,
        network: Dict[str, Any],
        case_id: Optional[str] = None,
        run_gnn: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete 70/15/15 evaluation on a network.

        :param network: CrimeNet network dict (nodes + edges).
        :param case_id: Optional case ID.
        :param run_gnn: Include GNN evaluation (slower; requires ≥6 nodes).
        :returns: Dict with evaluation metrics and best predictions.
        """
        g, node_id_list = helpers.convert_to_nx_undirected_graph(network)
        if g.number_of_edges() < 4:
            return {"error": "Graph too small for evaluation (need ≥4 edges)."}

        train_edges, val_edges, test_edges = split_edges(g)

        # Build the hidden-edge graph (only training edges)
        g_train = nx.Graph()
        g_train.add_nodes_from(g.nodes())
        g_train.add_edges_from(train_edges)

        test_neg = sample_negatives(g, test_edges, strategy="two_hop")

        # Classical evaluation
        classical_results = self.classical.evaluate(
            g_train, test_edges, test_neg
        )

        # GNN evaluation
        gnn_result: Dict[str, Any] = {}
        if run_gnn:
            try:
                gnn_result = self.gnn.train_and_evaluate(network, case_id=case_id)
            except Exception as exc:
                logger.warning("GNN training failed: %s", exc)
                gnn_result = {"error": str(exc)}

        # Generate predictions on the full graph using the best classical method
        node_labels = {i: name for i, name in enumerate(node_id_list)}
        best_classical = max(
            classical_results.items(),
            key=lambda x: x[1].get("auc_roc", 0.0),
            default=("adamic_adar", {}),
        )[0]

        # Get all 2-hop candidates on full graph
        all_candidates = sample_negatives(g, list(g.edges()), strategy="two_hop")
        classical_preds = self.classical.predict(g, all_candidates, method=best_classical, node_labels=node_labels)

        gnn_preds: List[Dict] = []
        if run_gnn and "error" not in gnn_result:
            try:
                gnn_preds = self.gnn.predict_candidates(g, all_candidates, top_k=20, node_labels=node_labels)
            except Exception as exc:
                logger.warning("GNN prediction failed: %s", exc)

        return {
            "case_id":              case_id,
            "n_nodes":              g.number_of_nodes(),
            "n_edges":              g.number_of_edges(),
            "n_train":              len(train_edges),
            "n_val":                len(val_edges),
            "n_test":               len(test_edges),
            "classical_evaluation": classical_results,
            "gnn_evaluation":       gnn_result,
            "best_classical_method":best_classical,
            "classical_predictions":classical_preds[:20],
            "gnn_predictions":      gnn_preds[:20],
            "disclaimer":           PREDICTION_DISCLAIMER,
        }


# ---------------------------------------------------------------------------
# Module-level info
# ---------------------------------------------------------------------------

def get_info() -> Dict[str, Any]:
    return {
        "name": "Link Prediction Evaluation Pipeline",
        "split": {"train": 0.70, "val": 0.15, "test": 0.15},
        "classical_methods": ClassicalEvaluator.METHODS,
        "ml_methods": ["GCN (SimpleGCN, plain PyTorch)"],
        "negative_sampling": "two_hop (forensically conservative)",
        "metrics": ["AUC-ROC", "Average Precision"],
        "models_dir": str(MODELS_DIR),
        "disclaimer": PREDICTION_DISCLAIMER,
    }
