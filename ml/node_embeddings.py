from __future__ import annotations

from backend.intelligence.node_embeddings import GraphEmbeddingEngine, default_embedding_engine

# Canonical aliases
NodeEmbeddingEngine = GraphEmbeddingEngine

__all__ = ["GraphEmbeddingEngine", "NodeEmbeddingEngine", "default_embedding_engine"]
