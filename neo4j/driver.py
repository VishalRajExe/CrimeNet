"""Neo4j Driver and Operational Graph Synchronization for CrimeNet.

Ensures only verified, human-confirmed relationships are synchronized to the Neo4j operational graph.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger("CrimeNet.Neo4j")


def get_neo4j_driver():
    """Retrieve an authenticated Neo4j Bolt driver or return None if offline."""
    try:
        import neo4j
        return neo4j.GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
    except Exception as e:
        logger.debug("Neo4j driver connection deferred: %s", e)
        return None


def sync_confirmed_to_neo4j(case_id: str, relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Synchronize confirmed relationships into Neo4j with audit provenance."""
    from storage.graphrag_crimenet_boundary import GraphRAGCrimeNetBoundary
    boundary = GraphRAGCrimeNetBoundary(case_id=case_id)
    return boundary.sync_to_neo4j(case_id=case_id, entities=[], relationships=relationships)
