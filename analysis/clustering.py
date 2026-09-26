"""CrimeNet Network Clustering Module."""

from __future__ import annotations

from analyzer.community_detection import (
    hierarchical_communities,
    louvain_communities_method,
    greedy_modularity_communities,
    label_propagation_communities,
)

# Clean alias
run_hierarchical_clustering = hierarchical_communities

__all__ = [
    "hierarchical_communities",
    "run_hierarchical_clustering",
    "louvain_communities_method",
    "greedy_modularity_communities",
    "label_propagation_communities",
]
