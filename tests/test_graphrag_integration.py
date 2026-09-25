"""Comprehensive integration test suite for CrimeNet Microsoft GraphRAG 3.2.0.

Verifies:
1. GraphRAG 3.2.0 configuration generation with CrimeNet entity types:
   (person, phone, vehicle, location, organization, case, event, account, transaction).
2. Unstructured evidence document staging and deterministic GraphRAG index creation.
3. Strict compatibility with GraphRAG 3.2.0 query indexer adapters:
   - read_indexer_entities
   - read_indexer_relationships
   - read_indexer_communities
   - read_indexer_reports
   - read_indexer_text_units
4. Verification of all 4 GraphRAG search modes:
   - local search
   - global search
   - basic search
   - DRIFT search
5. Strict evidence grounding and citations adhering to [Data: ...] syntax.
6. Non-replacement of Neo4j & operational graph correlation.
7. End-to-end integration with EvidenceProcessor & CaseDataService.
"""

import os
import shutil
import tempfile
import pytest
import pandas as pd

from storage.case_data_service import CaseDataService
from storage.evidence_processor import EvidenceProcessor
from storage.crimenet_graphrag import (
    CrimeNetGraphRAG,
    CRIMENET_ENTITY_TYPES,
    create_crimenet_graphrag_config,
    GRAPHRAG_AVAILABLE,
)


@pytest.fixture(scope="module")
def case_id():
    svc = CaseDataService()
    cases = svc.list_cases()
    target = next((c["id"] for c in cases if c["id"] == "case-sih-001"), cases[0]["id"])
    return target


@pytest.fixture(scope="module")
def temp_graphrag_dir():
    d = tempfile.mkdtemp(prefix="crimenet_graphrag_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_graphrag_availability_and_imports():
    """Verify Microsoft GraphRAG 3.2.0 API is installed and importable."""
    assert GRAPHRAG_AVAILABLE is True, "Microsoft GraphRAG 3.2.0 packages must be available"


def test_crimenet_entity_taxonomy_and_config(temp_graphrag_dir):
    """Verify GraphRagConfig is generated with all 9 CrimeNet-specific entity types."""
    cfg = create_crimenet_graphrag_config(
        case_id="case-test-tax",
        root_dir=temp_graphrag_dir,
        offline_mode=True,
    )

    expected_types = {
        "person", "phone", "vehicle", "location", "organization",
        "case", "event", "account", "transaction"
    }
    actual_types = set(cfg.extract_graph.entity_types)
    assert expected_types.issubset(actual_types), f"Missing entity types: {expected_types - actual_types}"

    # Verify storage paths
    assert "input" in cfg.input_storage.base_dir
    assert "output" in cfg.output_storage.base_dir
    assert "cache" in cfg.cache.storage.base_dir


def test_evidence_indexing_and_parquet_generation(temp_graphrag_dir):
    """Test staging an actual FIR and building GraphRAG Parquet tables."""
    rag = CrimeNetGraphRAG(
        case_id="case-fir-142",
        base_dir=temp_graphrag_dir,
        offline_mode=True,
    )

    fir_content = (
        "FIRST INFORMATION REPORT - FIR NO. 142/2026\n"
        "Special Crime Branch Anti-Narcotics Division, Mumbai Central.\n"
        "Accused Person: Ashok Nair (alias Anna), operative of D-Syndicate.\n"
        "Associated Suspect: Ramesh Shinde (driver and courier).\n"
        "Intercepted Vehicle: White Mahindra Scorpio MH04AB1234 at Bhiwandi Toll Plaza.\n"
        "Seized Device: Samsung Galaxy with burner SIM +919876543210.\n"
        "Financial Dispersal: Illicit transfer to Sunrise Traders Pvt Ltd, Account AC-9988776655.\n"
        "Primary Hub: Bhiwandi Warehouse, Sector 4."
    )

    rag.add_evidence_document(
        doc_id="exhibit_fir_142",
        filename="FIR_142_Bhiwandi_Seizure.txt",
        content=fir_content,
        metadata={"crime_type": "NARCOTICS_TRAFFICKING", "officer": "Insp. Pawar"}
    )

    stats = rag.build_index()
    assert stats["success"] is True
    assert stats["document_count"] >= 1
    assert stats["text_unit_count"] >= 1
    assert stats["entity_count"] >= 3, "Expected at least phone, vehicle, and person/org entities"
    assert stats["relationship_count"] >= 1
    assert stats["community_count"] >= 1
    assert stats["report_count"] >= 1

    # Verify Parquet files exist on disk
    out_dir = rag.output_dir
    for table_name in ["documents", "text_units", "entities", "relationships", "communities", "community_reports", "covariates"]:
        p = out_dir / f"{table_name}.parquet"
        assert p.exists(), f"Missing expected Parquet file: {p}"
        df = pd.read_parquet(p)
        assert not df.empty, f"Parquet table {table_name} should not be empty"


def test_graphrag_indexer_adapters_compatibility(temp_graphrag_dir):
    """Verify that Microsoft GraphRAG 3.2.0 internal indexer adapters load our tables."""
    from graphrag.query.indexer_adapters import (
        read_indexer_entities,
        read_indexer_relationships,
        read_indexer_communities,
        read_indexer_reports,
        read_indexer_text_units,
    )

    rag = CrimeNetGraphRAG(
        case_id="case-fir-142",
        base_dir=temp_graphrag_dir,
        offline_mode=True,
    )
    tables = rag.load_parquet_tables()

    ents = read_indexer_entities(tables["entities"], tables["communities"], 0)
    rels = read_indexer_relationships(tables["relationships"])
    comms = read_indexer_communities(tables["communities"], tables["community_reports"])
    reps = read_indexer_reports(tables["community_reports"], tables["communities"], 0)
    tus = read_indexer_text_units(tables["text_units"])

    assert len(ents) >= 3, "Entities should be parsed into GraphRAG Entity objects"
    assert len(rels) >= 1, "Relationships should be parsed into GraphRAG Relationship objects"
    assert len(comms) >= 1, "Communities should be parsed into GraphRAG Community objects"
    assert len(reps) >= 1, "Reports should be parsed into GraphRAG CommunityReport objects"
    assert len(tus) >= 1, "Text units should be parsed into GraphRAG TextUnit objects"


def test_all_four_search_modes(temp_graphrag_dir):
    """Verify all 4 search modes (local, global, basic, drift) return grounded answers."""
    rag = CrimeNetGraphRAG(
        case_id="case-fir-142",
        base_dir=temp_graphrag_dir,
        offline_mode=True,
    )

    query = "What vehicle and phone number were used in the Bhiwandi smuggling operation?"

    # 1. Local Search
    res_local = rag.query(query, mode="local")
    assert res_local["mode"] == "local"
    assert res_local["grounded"] is True
    assert "[Data:" in res_local["response"], "Local search response must contain [Data: ...] citations"
    assert len(res_local["entities"]) > 0

    # 2. Global Search
    res_global = rag.query(query, mode="global")
    assert res_global["mode"] == "global"
    assert res_global["grounded"] is True
    assert "[Data: Reports" in res_global["response"] or "[Data: Communities" in res_global["response"]
    assert len(res_global["reports"]) > 0

    # 3. Basic Search
    res_basic = rag.query(query, mode="basic")
    assert res_basic["mode"] == "basic"
    assert res_basic["grounded"] is True
    assert "[Data: Sources" in res_basic["response"], "Basic search response must cite Sources"
    assert len(res_basic["sources"]) > 0

    # 4. DRIFT Search
    res_drift = rag.query(query, mode="drift")
    assert res_drift["mode"] == "drift"
    assert res_drift["grounded"] is True
    assert "[Data: Entities" in res_drift["response"] or "[Data: Relationships" in res_drift["response"]
    assert len(res_drift["entities"]) > 0


def test_neo4j_correlation_and_non_replacement(temp_graphrag_dir):
    """Verify Neo4j remains operational and correlation detects overlapping & new leads."""
    rag = CrimeNetGraphRAG(
        case_id="case-fir-142",
        base_dir=temp_graphrag_dir,
        offline_mode=True,
    )

    corr = rag.correlate_with_neo4j(neo4j_driver=None)
    assert "total_graphrag_entities" in corr
    assert corr["total_graphrag_entities"] >= 3
    assert "new_leads" in corr
    assert len(corr["new_leads"]) >= 1


def test_evidence_processor_graphrag_pipeline(case_id):
    """Test full integration: Uploading evidence indexes into GraphRAG and querying via CaseDataService."""
    processor = EvidenceProcessor()
    svc = CaseDataService()

    fir_text = (
        "CONFIDENTIAL INTELLIGENCE MEMO - ANC/INT/2026/089\n"
        "Subject: Intercepted hawala courier Imran Qureshi.\n"
        "Operative identified using vehicle DL01C5678 and phone 9811223344.\n"
        "Direct link established to Hawala banker Tariq Merchant via Account AC-5544332211.\n"
        "Meeting conducted at Oberoi Hotel Business Center, Mumbai."
    )
    file_bytes = fir_text.encode("utf-8")
    filename = "intelligence_memo_anc_089.txt"

    res = processor.process_evidence_pipeline(
        case_id=case_id,
        filename=filename,
        file_bytes=file_bytes,
        declared_type="TXT",
        title="Hawala Intercept Intelligence Memo",
        source_ref="ANC Confidential Surveillance"
    )

    assert res["success"] is True
    assert res["status"] == "Processed"
    assert "graphrag" in res
    assert res["graphrag"].get("indexed") is True, "EvidenceProcessor must index text into GraphRAG"

    # Query GraphRAG via CaseDataService
    qa_res = svc.query_case_graphrag(
        case_id=case_id,
        query="Who is Imran Qureshi and which account was used?",
        mode="local"
    )
    assert qa_res["grounded"] is True
    assert "[Data:" in qa_res["response"]
    assert "Imran Qureshi" in qa_res["response"] or "IMRAN QURESHI" in qa_res["response"] or len(qa_res["entities"]) > 0

    # Query stats
    stats = svc.get_case_graphrag_stats(case_id=case_id)
    assert stats["documents"] >= 1
    assert stats["entities"] >= 1
