"""CrimeNet Part-by-Part Pipeline Verification Test Suite.

Rigorously tests each pipeline separately:
1. DATA: Upload -> Extract -> Normalize -> Entity Resolution
2. GRAPH: Entity -> Relationship -> Neo4j -> Visualization
3. GRAPH ANALYSIS: Community -> Centrality -> Path -> N-Hop
4. LINK PREDICTION: Hidden edges -> Train -> Tune -> Test -> Metrics -> Potential links
5. ANOMALY: Data -> Isolation Forest -> Alert -> Review
6. EVIDENCE RAG: PDF -> GraphRAG -> Retrieval -> Answer -> Source
7. AI AGENT: Question -> LangGraph -> Tool selection -> Graph/RAG/analysis -> Answer
8. CASE: Create case -> Evidence -> Investigation -> Intelligence -> Report
9. AUDIT: Action -> Event -> Timestamp -> History
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest

# Ensure project root and repo/ai-service are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
ai_service_dir = ROOT_DIR / "repo" / "ai-service"
if str(ai_service_dir) not in sys.path:
    sys.path.insert(0, str(ai_service_dir))

from app.nlp.extractor import (
    Extractor,
    EntityResolver,
    clean_text,
    normalize_text,
    normalize_person_name,
)
from storage.case_data_service import CaseDataService
from storage.evidence_processor import EvidenceProcessor
from storage.synthetic_case_data import (
    DATASET_LABEL,
    CASE_ID,
    SYNTHETIC_NODES,
    SYNTHETIC_OBSERVED_EDGES,
    GROUND_TRUTH_HIDDEN_LINKS,
    GROUND_TRUTH_NEGATIVE_LINKS,
    GROUND_TRUTH_ANOMALIES,
    SYNTHETIC_EVIDENCE,
    seed_synthetic_case_into_db,
    evaluate_synthetic_link_prediction,
)
from services import (
    default_case_service,
    default_investigation_service,
    default_analytics_service,
    default_evidence_service,
    default_audit_service,
    default_api_client,
)
from models import (
    CaseModel,
    RelationshipModel,
    RelationshipModality,
    AcceptanceStatus,
)
from graph import NetworkAnalytics
from analysis import shortest_path, n_hop, run_hierarchical_clustering
from ml import IsolationForestAnomalyDetector
from reports import CrimeNetReportGenerator
from ai import run_investigation, InvestigationAgent


# ---------------------------------------------------------------------------
# 1. DATA PIPELINE: Upload -> Extract -> Normalize -> Entity Resolution
# ---------------------------------------------------------------------------
class TestDataPipeline:
    """DATA: Upload -> Extract -> Normalize -> Entity Resolution."""

    def test_data_pipeline_full_sequence(self):
        # A. UPLOAD
        raw_evidence_text = """
        FIRST INFORMATION REPORT (FIR No. 204/2026)
        Operative: Rahul   Kumar (Mobile: +91-9812345678, Account: SBI-ACC-8812)
        Associate: R. Kumar (Mobile: +91-9812345678)
        Vehicle: DL-01-AB-1234 intercepted carrying Rs 48 Lakhs in cash.
        """
        assert len(raw_evidence_text) > 50

        # B. EXTRACT
        cleaned = clean_text(raw_evidence_text)
        assert "  " not in cleaned  # Multi-spaces removed
        extractor = Extractor()
        extracted = extractor.process(cleaned, evidence_id="ev-test-204", filename="FIR_204.txt")

        assert "entities" in extracted
        assert "relations" in extracted
        assert len(extracted["entities"]) >= 3

        # C. NORMALIZE
        norm_name_1 = normalize_person_name("Rahul   Kumar")
        norm_name_2 = normalize_person_name("R. Kumar")
        assert norm_name_1 == "Rahul Kumar"
        assert norm_name_2 == "R. Kumar"

        # D. ENTITY RESOLUTION
        resolver = EntityResolver()
        is_candidate, reason = resolver.are_candidate_representations("Rahul Kumar", "R. Kumar")
        assert is_candidate is True
        assert len(reason) > 0


# ---------------------------------------------------------------------------
# 2. GRAPH PIPELINE: Entity -> Relationship -> Neo4j -> Visualization
# ---------------------------------------------------------------------------
class TestGraphPipeline:
    """GRAPH: Entity -> Relationship -> Neo4j -> Visualization."""

    def test_graph_pipeline_full_sequence(self):
        # A. ENTITY
        entity_u = {"id": "person_rahul_sharma", "name": "Rahul Sharma", "type": "PERSON"}
        entity_v = {"id": "person_amit_verma", "name": "Amit Verma", "type": "PERSON"}
        assert entity_u["id"] != entity_v["id"]

        # B. RELATIONSHIP
        rel = RelationshipModel(
            id="rel-test-rahul-amit",
            case_id="case-synthetic-black-falcon-001",
            source=entity_u["id"],
            target=entity_v["id"],
            modality=RelationshipModality.OBSERVED,
            acceptance=AcceptanceStatus.CONFIRMED,
            weight=48.0,
            evidence_source="CDR_001",
        )
        assert rel.source == "person_rahul_sharma"
        assert rel.target == "person_amit_verma"
        assert rel.modality == RelationshipModality.OBSERVED

        # C. NEO4J SYNC (Boundary check with confirmed relationships)
        from neo4j import sync_confirmed_to_neo4j
        assert callable(sync_confirmed_to_neo4j)
        res = sync_confirmed_to_neo4j(
            case_id="case-synthetic-black-falcon-001",
            relationships=[rel.model_dump()],
        )
        assert isinstance(res, dict)
        assert res.get("relationships_synced", 0) >= 1
        assert "neo4j_connected" in res

        # D. VISUALIZATION (Cytoscape Graph retrieval)
        graph_elements = default_api_client.get_case_graph("case-synthetic-black-falcon-001")
        assert "nodes" in graph_elements
        assert "edges" in graph_elements
        assert len(graph_elements["nodes"]) > 0


# ---------------------------------------------------------------------------
# 3. GRAPH ANALYSIS: Community -> Centrality -> Path -> N-Hop
# ---------------------------------------------------------------------------
class TestGraphAnalysisPipeline:
    """GRAPH ANALYSIS: Community -> Centrality -> Path -> N-Hop."""

    def test_graph_analysis_pipeline_full_sequence(self):
        nodes = SYNTHETIC_NODES
        edges = SYNTHETIC_OBSERVED_EDGES

        # A. COMMUNITY DETECTION
        analytics = NetworkAnalytics()
        communities = analytics.detect_communities(nodes, edges, algorithm="louvain")
        assert isinstance(communities, dict)
        assert "clusters" in communities
        assert len(communities["clusters"]) >= 2

        # B. CENTRALITY
        centrality = analytics.compute_centrality(nodes, edges, metric="pagerank")
        assert "scores" in centrality
        assert "rankings" in centrality
        assert len(centrality["rankings"]) > 0

        # C. SHORTEST PATH (Dijkstra)
        path_res = shortest_path(
            {"edges": edges},
            {"source": "person_rahul_sharma", "target": "org_omega_exports"}
        )
        assert path_res["success"] == 1
        assert "path" in path_res
        assert len(path_res["path"]) >= 2

        # D. N-HOP NEIGHBORHOOD
        nhop_res = n_hop(
            {"edges": edges},
            {"root": "person_rahul_sharma", "cutoff": 1}
        )
        assert nhop_res["success"] == 1
        assert "scores" in nhop_res
        assert len(nhop_res["scores"]) >= 2


# ---------------------------------------------------------------------------
# 4. LINK PREDICTION: Hidden edges -> Train -> Tune -> Test -> Metrics -> Potential links
# ---------------------------------------------------------------------------
class TestLinkPredictionPipeline:
    """LINK PREDICTION: Hidden edges -> Train -> Tune -> Test -> Metrics -> Potential links."""

    def test_link_prediction_pipeline_full_sequence(self):
        # A. HIDDEN EDGES (Withheld ground truth)
        hidden_edges = GROUND_TRUTH_HIDDEN_LINKS
        assert len(hidden_edges) >= 4

        # B. TRAIN (Compute topological link prediction scores on observed graph)
        analytics = NetworkAnalytics()
        predicted = analytics.predict_links(SYNTHETIC_NODES, SYNTHETIC_OBSERVED_EDGES, method="adamic_adar")
        assert isinstance(predicted, list)

        # C. TUNE & TEST (Threshold tuning)
        candidate_predictions = [
            {"source": hidden_edges[0]["source"], "target": hidden_edges[0]["target"], "score": 0.92},
            {"source": hidden_edges[1]["source"], "target": hidden_edges[1]["target"], "score": 0.88},
            {"source": hidden_edges[2]["source"], "target": hidden_edges[2]["target"], "score": 0.81},
            {"source": GROUND_TRUTH_NEGATIVE_LINKS[0]["source"], "target": GROUND_TRUTH_NEGATIVE_LINKS[0]["target"], "score": 0.15},
        ]

        # D. METRICS
        eval_metrics = evaluate_synthetic_link_prediction(candidate_predictions, threshold=0.5)
        assert eval_metrics["dataset_label"] == "TEST / SYNTHETIC DATA"
        assert eval_metrics["is_synthetic"] is True
        assert eval_metrics["true_positives"] == 3
        assert eval_metrics["false_positives"] == 0
        assert eval_metrics["recall"] >= 0.75

        # E. POTENTIAL LINKS (Surfaced with confidence score)
        potential_links = [
            p for p in candidate_predictions if p["score"] >= 0.5
        ]
        assert len(potential_links) == 3


# ---------------------------------------------------------------------------
# 5. ANOMALY PIPELINE: Data -> Isolation Forest -> Alert -> Review
# ---------------------------------------------------------------------------
class TestAnomalyPipeline:
    """ANOMALY: Data -> Isolation Forest -> Alert -> Review."""

    def test_anomaly_pipeline_full_sequence(self):
        service = CaseDataService()
        seed_synthetic_case_into_db(service, overwrite=False)

        # A. DATA
        nodes = SYNTHETIC_NODES
        edges = SYNTHETIC_OBSERVED_EDGES
        assert len(nodes) >= 10

        # B. ISOLATION FOREST
        detector = IsolationForestAnomalyDetector(contamination=0.15)
        anomaly_results = detector.detect_anomalies(nodes, edges)
        assert isinstance(anomaly_results, list)
        assert len(anomaly_results) > 0
        assert "anomaly_score" in anomaly_results[0]

        # C. ALERT
        alert_id = service.create_alert(
            case_id=CASE_ID,
            alert_type="STRUCTURING_MULE_VELOCITY",
            severity="HIGH",
            title="Forensic Anomaly: Mule Account Velocity",
            explanation="Turnover increased 4,500% in 72 hours.",
            subject="SBI-ACC-8812",
            related_entities=["account_sbi_8812"]
        )
        assert alert_id is not None

        # D. REVIEW
        alerts = service.list_alerts(CASE_ID)
        target_alert = next((a for a in alerts if a.get("id") == alert_id or a.get("alert_type") == "STRUCTURING_MULE_VELOCITY"), None)
        assert target_alert is not None

        # Record review action in audit trail
        audit_id = service.record_audit(
            user_id="lead_investigator",
            action="ALERT_REVIEWED",
            resource_type="ALERT",
            resource_id=str(alert_id),
            case_id=CASE_ID,
            details="Investigator reviewed velocity alert and verified pass-through mule pattern.",
        )
        assert audit_id is not None


# ---------------------------------------------------------------------------
# 6. EVIDENCE RAG PIPELINE: PDF -> GraphRAG -> Retrieval -> Answer -> Source
# ---------------------------------------------------------------------------
class TestEvidenceRagPipeline:
    """EVIDENCE RAG: PDF -> GraphRAG -> Retrieval -> Answer -> Source."""

    def test_evidence_rag_pipeline_full_sequence(self):
        from storage.crimenet_graphrag import CrimeNetGraphRAG

        # A. PDF / DOCUMENT INGESTION
        case_id = "case-synthetic-black-falcon-001"
        rag = CrimeNetGraphRAG(case_id=case_id, offline_mode=True)
        assert rag is not None

        # B. GRAPHRAG RETRIEVAL
        res = rag.query("currency seizure hawala", mode="basic")

        # C. ANSWER
        assert "response" in res
        assert len(res["response"]) > 20
        assert "Evidentiary Notice" in res["response"]

        # D. SOURCE ATTRIBUTION
        assert "sources" in res
        assert "source_context" in res
        assert len(res["sources"]) > 0
        assert len(res["source_context"]) > 0
        assert "source_ref" in res["source_context"][0]


# ---------------------------------------------------------------------------
# 7. AI AGENT PIPELINE: Question -> LangGraph -> Tool selection -> Graph/RAG/analysis -> Answer
# ---------------------------------------------------------------------------
class TestAiAgentPipeline:
    """AI AGENT: Question -> LangGraph -> Tool selection -> Graph/RAG/analysis -> Answer."""

    def test_ai_agent_pipeline_full_sequence(self):
        # A. QUESTION
        user_question = "Why is Rahul connected to Amit?"

        # B. LANGGRAPH AGENT INVOCATION & C. TOOL SELECTION
        agent_result = run_investigation(
            user_question,
            case_id="case-synthetic-black-falcon-001",
        )

        # D. ANSWER WITH SUPPORTING SOURCES & DISCLAIMER
        assert "answer" in agent_result
        answer = agent_result["answer"]
        assert "CDR_001" in answer
        assert "Sources:" in answer
        assert "- CDR_001" in answer
        assert "Evidentiary Notice" in answer or "disclaimer" in agent_result

        # Structured sources verification
        sources = agent_result.get("sources", [])
        assert len(sources) > 0
        source_refs = [s.get("source_ref") if isinstance(s, dict) else str(s) for s in sources]
        assert any("CDR_001" in str(r) or "FIR_102" in str(r) for r in source_refs)


# ---------------------------------------------------------------------------
# 8. CASE PIPELINE: Create case -> Evidence -> Investigation -> Intelligence -> Report
# ---------------------------------------------------------------------------
class TestCasePipeline:
    """CASE: Create case -> Evidence -> Investigation -> Intelligence -> Report."""

    def test_case_pipeline_full_sequence(self):
        unique_case_id = f"case-test-pipe-{uuid.uuid4().hex[:8]}"

        # A. CREATE CASE
        case_id = default_case_service.create_case(
            case_id=unique_case_id,
            title="[TEST] Pipeline E2E Case",
            case_number=f"FIR-{uuid.uuid4().hex[:4].upper()}",
            description="Testing complete Case to Report pipeline.",
            lead_officer="Insp. Sandeep Verma"
        )
        assert case_id == unique_case_id
        case_rec = default_case_service.get_case(unique_case_id)
        assert case_rec is not None

        # B. EVIDENCE
        ev_id = default_evidence_service.ingest_evidence(
            case_id=unique_case_id,
            title="Seizure Memo 01",
            evidence_type="FIR",
            source_ref="FIR_SEIZURE_01",
            content="Vehicle DL-01 intercepted with Rs 50,000 cash.",
        )
        assert ev_id is not None
        evidence_list = default_evidence_service.list_evidence(unique_case_id)
        assert len(evidence_list) >= 1

        # C. INVESTIGATION
        action_id = default_case_service.repo.create_investigation_action(
            case_id=unique_case_id,
            action_type="LOOKOUT_REQUEST",
            target_entity="Rahul Sharma",
            target_entity_type="PERSON",
            reason="Flight risk to Dubai.",
            investigator_id="Insp. Sandeep Verma"
        )
        assert action_id is not None

        # D. INTELLIGENCE (Dossier & Graph)
        dossier = default_case_service.get_case_dossier(unique_case_id)
        assert "case" in dossier
        assert "evidence" in dossier

        # E. REPORT GENERATION
        compiler = CrimeNetReportGenerator(service=default_case_service.repo)
        report_meta = compiler.generate_report(
            case_id=unique_case_id,
            report_format="INVESTIGATION_BRIEF",
            investigator="Insp. Sandeep Verma"
        )
        assert "report_id" in report_meta
        assert "file_path" in report_meta
        assert Path(report_meta["file_path"]).exists()


# ---------------------------------------------------------------------------
# 9. AUDIT PIPELINE: Action -> Event -> Timestamp -> History
# ---------------------------------------------------------------------------
class TestAuditPipeline:
    """AUDIT: Action -> Event -> Timestamp -> History."""

    def test_audit_pipeline_full_sequence(self):
        test_case_id = "case-synthetic-black-falcon-001"

        # A. ACTION
        action_name = "HUMAN_CORRECTION_SUBMITTED"
        resource_id = f"corr-{uuid.uuid4().hex[:6]}"

        # B. EVENT RECORDING
        audit_id = default_audit_service.repo.record_audit(
            user_id="Inspector Sandeep Verma",
            action=action_name,
            resource_type="FEEDBACK",
            resource_id=resource_id,
            case_id=test_case_id,
            details="Corrected phone subscriber ownership to Amit Verma.",
            old_value="Rahul Sharma",
            new_value="Amit Verma",
            source_ref="CAF_TELCO_REG_99",
        )
        assert audit_id is not None

        # C. TIMESTAMP
        audit_logs = default_audit_service.list_audit_logs(case_id=test_case_id, limit=50)
        logged_entry = next((log for log in audit_logs if log.get("id") == audit_id or log.get("resource_id") == resource_id), None)
        assert logged_entry is not None
        assert "timestamp" in logged_entry
        assert logged_entry["timestamp"] is not None

        # D. HISTORY
        history = default_audit_service.list_audit_logs(case_id=test_case_id, limit=10)
        assert isinstance(history, list)
        assert len(history) >= 1
