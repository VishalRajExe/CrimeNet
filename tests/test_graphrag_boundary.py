"""Unit tests for CrimeNet GraphRAG Integration Boundary Layer.

Verifies:
1. GraphRAG entity mapping to CrimeNet taxonomy (PERSON, PHONE, VEHICLE, LOCATION, ORGANIZATION, ACCOUNT, etc.).
2. GraphRAG relationship mapping to CrimeNet canonical types (CALLED, USES_PHONE, USES_VEHICLE, TRANSFERRED_TO, etc.).
3. Provenance tracking (source_file, evidence_quote, char_offsets, confidence).
4. Relationship distinguishability: OBSERVED, EXTRACTED, PREDICTED, INFERRED.
5. Acceptance gatekeeper: Predicted/Inferred relationships are PROPOSED, not CONFIRMED, and not synced to Neo4j until accepted.
6. Acceptance and rejection transitions.
"""

import pytest
from storage.graphrag_crimenet_boundary import (
    GraphRAGCrimeNetBoundary,
    RelationshipModality,
    AcceptanceStatus,
    NormalizedEntity,
    NormalizedRelationship,
)


def test_taxonomy_entity_mapping():
    """Verify raw GraphRAG entity strings map to canonical CrimeNet types."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    # Direct mappings
    assert b.map_entity_type("individual", "Vikram Singhania") == "PERSON"
    assert b.map_entity_type("suspect", "Rahul") == "PERSON"
    assert b.map_entity_type("mobile", "9876543210") == "PHONE"
    assert b.map_entity_type("car", "DL8CAF5031") == "VEHICLE"
    assert b.map_entity_type("company", "Sunrise Traders Pvt Ltd") == "ORGANIZATION"
    assert b.map_entity_type("bank_account", "912345678901") == "ACCOUNT"
    assert b.map_entity_type("warehouse", "Bhiwandi Spot") == "LOCATION"

    # Heuristic fallback based on value
    assert b.map_entity_type("unknown", "9811223344") == "PHONE"
    assert b.map_entity_type("concept", "MH04AX9999") == "VEHICLE"
    assert b.map_entity_type("concept", "Apex Infotech Ltd") == "ORGANIZATION"


def test_taxonomy_relationship_mapping():
    """Verify raw GraphRAG relationship strings map to canonical CrimeNet types."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    assert b.map_relationship_type("phoned") == "CALLED"
    assert b.map_relationship_type("contacted") == "CALLED"
    assert b.map_relationship_type("wire_transfer") == "TRANSFERRED_TO"
    assert b.map_relationship_type("drove") == "USES_VEHICLE"
    assert b.map_relationship_type("operated_phone") == "USES_PHONE"
    assert b.map_relationship_type("co_conspirator") == "ASSOCIATE_OF"
    assert b.map_relationship_type("employed_by") == "AFFILIATED_WITH"


def test_modality_distinguishability():
    """Verify relationships are strictly distinguished as Observed, Extracted, Predicted, Inferred."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    # Structured CDR -> OBSERVED
    assert b.classify_modality("CDR_001.csv", "TELECOM_CDR") == RelationshipModality.OBSERVED
    assert b.classify_modality("transactions_march.csv", "WIRE_RECORD") == RelationshipModality.OBSERVED

    # Unstructured narrative FIR -> EXTRACTED
    assert b.classify_modality("FIR_2026_0142.txt", "REGEX_EXTRACTION") == RelationshipModality.EXTRACTED
    assert b.classify_modality("witness_memo.txt", "SPACY_NER") == RelationshipModality.EXTRACTED

    # Link prediction algorithms -> PREDICTED
    assert b.classify_modality("case_graph", "jaccard_coefficient") == RelationshipModality.PREDICTED
    assert b.classify_modality("case_graph", "adamic_adar_index") == RelationshipModality.PREDICTED

    # GraphRAG multi-hop / LLM -> INFERRED
    assert b.classify_modality("graphrag_output", "graphrag_drift_search") == RelationshipModality.INFERRED
    assert b.classify_modality("evidence.txt", "llm_inferred_syndicate") == RelationshipModality.INFERRED


def test_acceptance_gatekeeper_predicted_inferred_not_confirmed():
    """Verify predicted/inferred relationships are PROPOSED, not automatically confirmed or pushed to Neo4j."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    raw_ents = [
        {"name": "Rahul", "type": "person", "evidence": "Rahul met with Amit"},
        {"name": "Amit", "type": "person", "evidence": "Rahul met with Amit"},
    ]
    raw_rels = [
        # Inferred by LLM / GraphRAG
        {
            "source": "Rahul",
            "target": "Amit",
            "type": "ASSOCIATE_OF",
            "rule_name": "graphrag_drift_search",
            "confidence": 0.85,
            "evidence": "Inferred co-conspirator via multi-hop corridor",
        }
    ]

    res = b.process_evidence_knowledge(
        raw_entities=raw_ents,
        raw_relationships=raw_rels,
        source_file="FIR_001.txt",
        evidence_id="ev-001",
        evidence_text="Rahul met with Amit in Karol Bagh.",
    )

    assert res["success"] is True
    assert res["relationships_proposed"] == 1
    assert res["relationships_confirmed"] == 0
    assert res["modality_breakdown"]["INFERRED"] == 1

    # Neo4j must NOT sync the unconfirmed inferred relationship
    assert res["neo4j_sync"]["relationships_synced"] == 0


def test_observed_relationship_provenance_and_confirmation():
    """Verify observed relationships from CDR_001.csv carry full provenance and default to CONFIRMED."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    raw_ents = [
        {"name": "9811223344", "type": "phone", "evidence": "Caller 9811223344"},
        {"name": "9876543210", "type": "phone", "evidence": "Callee 9876543210"},
    ]
    raw_rels = [
        {
            "source": "9811223344",
            "target": "9876543210",
            "type": "CALLED",
            "rule_name": "TELECOM_CDR",
            "confidence": 0.99,
            "evidence": "Call duration 120s on 2026-03-15 14:22:00",
        }
    ]

    res = b.process_evidence_knowledge(
        raw_entities=raw_ents,
        raw_relationships=raw_rels,
        source_file="CDR_001.csv",
        evidence_id="ev-cdr-001",
    )

    assert res["success"] is True
    assert res["relationships_confirmed"] == 1
    assert res["relationships_proposed"] == 0
    assert res["modality_breakdown"]["OBSERVED"] == 1
    assert res["neo4j_sync"]["relationships_synced"] == 1


def test_acceptance_and_rejection_actions():
    """Verify investigator can explicitly accept or reject proposed relationships."""
    b = GraphRAGCrimeNetBoundary("case-sih-001")

    # Ingest a proposed inferred link
    raw_ents = [{"name": "Vikram", "type": "person"}, {"name": "Tariq", "type": "person"}]
    raw_rels = [{
        "source": "Vikram",
        "target": "Tariq",
        "type": "ASSOCIATE_OF",
        "rule_name": "graphrag_drift_search",
        "confidence": 0.82,
        "evidence": "DRIFT inference linking Vikram to Tariq via overseas transactions",
    }]

    res = b.process_evidence_knowledge(raw_ents, raw_rels, "FIR_991.txt", "ev-991")
    assert res["relationships_proposed"] >= 1

    # Fetch proposed edge ID from database
    with b.svc._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, properties FROM entity_relationships WHERE case_id = %s ORDER BY created_at DESC LIMIT 1;",
                ("case-sih-001",)
            )
            row = cur.fetchone()
            assert row is not None
            rel_id = row["id"]

    # 1. Accept proposed relationship
    accepted = b.accept_relationship(rel_id, investigator_id="investigator_test")
    assert accepted is True

    # Verify updated state
    with b.svc._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT properties FROM entity_relationships WHERE id = %s;", (rel_id,))
            updated_row = cur.fetchone()
            import json
            props = json.loads(updated_row["properties"])
            assert props["acceptance_status"] == AcceptanceStatus.CONFIRMED.value
            assert props["accepted_by"] == "investigator_test"

    # 2. Reject relationship
    rejected = b.reject_relationship(rel_id, reason="Insufficient corroborating evidence", investigator_id="investigator_test")
    assert rejected is True

    with b.svc._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT properties FROM entity_relationships WHERE id = %s;", (rel_id,))
            updated_row2 = cur.fetchone()
            props2 = json.loads(updated_row2["properties"])
            assert props2["acceptance_status"] == AcceptanceStatus.REJECTED.value
            assert "Insufficient" in props2["rejection_reason"]


def test_neo4j_cypher_provenance_statements():
    """Verify Neo4j cypher sync generates statements containing complete provenance."""
    b = GraphRAGCrimeNetBoundary("test-case-001")

    ent = NormalizedEntity(
        id="ent_test_01",
        name="Rahul Kumar",
        entity_type="PERSON",
        case_id="test-case-001",
        source_evidence_id="ev-01",
        source_file="FIR_001.txt",
        confidence=0.98,
        evidence_quote="Rahul Kumar was present at Karol Bagh",
    )
    rel = NormalizedRelationship(
        id="rel_test_01",
        source_id="ent_test_01",
        source_name="Rahul Kumar",
        target_id="ent_test_02",
        target_name="Amit Sharma",
        relationship_type="CALLED",
        case_id="test-case-001",
        source_evidence_id="ev-01",
        source_file="CDR_001.csv",
        modality=RelationshipModality.OBSERVED,
        acceptance_status=AcceptanceStatus.CONFIRMED,
        confidence=0.95,
        evidence_quote="Call duration 180s on 2026-03-15",
    )

    sync_res = b.sync_to_neo4j(
        case_id="test-case-001",
        entities=[ent],
        relationships=[rel],
        driver=None,  # Offline generation
    )

    assert sync_res["entities_synced"] == 1
    assert sync_res["relationships_synced"] == 1
    assert sync_res["statements_generated"] == 2
    cypher_text = "\n".join(sync_res["cypher_sample"])
    assert "Rahul Kumar" in cypher_text
    assert "CALLED" in cypher_text
    assert "OBSERVED" in cypher_text
    assert "CDR_001.csv" in cypher_text

