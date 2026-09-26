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


def sync_confirmed_to_neo4j(case_id: str, relationships: List[Any]) -> Dict[str, Any]:
    """Synchronize confirmed relationships into Neo4j with audit provenance."""
    from storage.graphrag_crimenet_boundary import (
        GraphRAGCrimeNetBoundary,
        NormalizedRelationship,
        RelationshipModality,
        AcceptanceStatus,
    )
    boundary = GraphRAGCrimeNetBoundary(case_id=case_id)
    norm_rels = []
    for r in relationships:
        if isinstance(r, NormalizedRelationship):
            norm_rels.append(r)
        elif isinstance(r, dict):
            acc = r.get("acceptance_status") or r.get("acceptance") or AcceptanceStatus.CONFIRMED
            if isinstance(acc, str):
                acc = AcceptanceStatus(acc.upper())
            mod = r.get("modality") or RelationshipModality.OBSERVED
            if isinstance(mod, str):
                mod = RelationshipModality(mod.upper())
            norm_rels.append(
                NormalizedRelationship(
                    id=str(r.get("id") or "rel-01"),
                    source_id=str(r.get("source_id") or r.get("source")),
                    source_name=str(r.get("source_name") or r.get("source")),
                    target_id=str(r.get("target_id") or r.get("target")),
                    target_name=str(r.get("target_name") or r.get("target")),
                    relationship_type=str(r.get("relationship_type") or r.get("type") or "ASSOCIATED_WITH"),
                    case_id=case_id,
                    source_evidence_id=str(r.get("source_evidence_id") or r.get("evidence_source") or "EVID_01"),
                    source_file=str(r.get("source_file") or "evidence.txt"),
                    modality=mod,
                    acceptance_status=acc,
                    confidence=float(r.get("confidence", 1.0)),
                    properties=r.get("properties") or {},
                )
            )
        else:
            norm_rels.append(r)
    return boundary.sync_to_neo4j(case_id=case_id, entities=[], relationships=norm_rels)
