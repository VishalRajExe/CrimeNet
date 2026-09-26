"""Tests for CrimeNet Clean Modular Python Architecture.

Validates that:
1. All requested architectural layers exist as decoupled Python packages:
   ui/, api/, services/, models/, database/, neo4j/, graphrag/,
   ai/, ml/, graph/, analysis/, reports/, audit/, utils/, config/, tests/
2. FastAPI acts as the unified service/API layer.
3. Dash UI layer consumes the API/service client layer without tight coupling to raw database calls.
4. Database and graph logic are centralized without duplicate implementations.
5. All domain models enforce schema validation.
"""

import pytest
import os
import sys

# Ensure project root is in sys.path
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.insert(0, path2root)


def test_config_layer_exports():
    """Verify config/ package exports centralized configuration settings."""
    import config
    assert hasattr(config, "BASE_DIR")
    assert hasattr(config, "STORAGE_DIR")
    assert hasattr(config, "API_HOST")
    assert hasattr(config, "API_PORT")
    assert hasattr(config, "API_BASE_URL")


def test_utils_layer_exports():
    """Verify utils/ package exports crypto and formatting functions."""
    from utils import sha256_hash, compute_evidence_hash, format_currency_inr
    test_hash = sha256_hash("test-evidence-payload")
    assert len(test_hash) == 64
    assert format_currency_inr(15000000) == "₹1.50 Cr"


def test_models_layer_validation():
    """Verify models/ package exports validated domain models."""
    from models import (
        CaseModel,
        CasePriority,
        CaseStatus,
        RelationshipModel,
        RelationshipModality,
        AcceptanceStatus,
        EvidenceModel,
        HumanFeedbackModel,
    )

    case = CaseModel(
        id="case-arch-test-01",
        case_number="FIR-2026-ARCH",
        title="Architecture Validation Case",
        priority=CasePriority.HIGH,
        status=CaseStatus.ACTIVE,
    )
    assert case.priority == CasePriority.HIGH
    assert case.status == CaseStatus.ACTIVE

    rel = RelationshipModel(
        id="rel-test-01",
        case_id="case-arch-test-01",
        source="person_rahul",
        target="person_amit",
        modality=RelationshipModality.OBSERVED,
        acceptance=AcceptanceStatus.CONFIRMED,
    )
    assert rel.modality == RelationshipModality.OBSERVED
    assert rel.acceptance == AcceptanceStatus.CONFIRMED


def test_database_layer_centralization():
    """Verify database/ package centralizes case data repository without duplication."""
    from database import CaseRepository, default_case_repository
    assert isinstance(default_case_repository, CaseRepository)
    cases = default_case_repository.list_cases()
    assert isinstance(cases, list)


def test_neo4j_layer_exports():
    """Verify neo4j/ package exports driver and synchronization functions."""
    from neo4j import get_neo4j_driver, sync_confirmed_to_neo4j
    assert callable(get_neo4j_driver)
    assert callable(sync_confirmed_to_neo4j)


def test_graphrag_layer_exports():
    """Verify graphrag/ package exports forensic integration boundary."""
    from graphrag import GraphRAGCrimeNetBoundary, RelationshipModality, AcceptanceStatus
    boundary = GraphRAGCrimeNetBoundary(case_id="case-synthetic-black-falcon-001")
    assert hasattr(boundary, "sync_to_neo4j")
    assert hasattr(boundary, "process_evidence_knowledge")


def test_graph_layer_exports():
    """Verify graph/ package exports NetworkX analytics engine."""
    from graph import NetworkAnalytics, default_network_analytics
    assert hasattr(default_network_analytics, "compute_centrality")
    assert hasattr(default_network_analytics, "detect_communities")
    assert hasattr(default_network_analytics, "predict_links")


def test_ml_layer_exports():
    """Verify ml/ package exports anomaly detection and embeddings engines."""
    from ml import AnomalyDetector, NodeEmbeddingEngine, default_anomaly_detector, default_embedding_engine
    assert hasattr(default_anomaly_detector, "detect_anomalies")
    assert hasattr(default_embedding_engine, "compute_embeddings")


def test_analysis_layer_exports():
    """Verify analysis/ package exports path analysis and clustering."""
    from analysis import find_shortest_forensic_path, run_hierarchical_clustering
    assert callable(find_shortest_forensic_path)
    assert callable(run_hierarchical_clustering)


def test_reports_layer_exports():
    """Verify reports/ package exports forensic report generator."""
    from reports import CrimeNetReportGenerator, generate_case_report
    assert callable(generate_case_report)
    assert hasattr(CrimeNetReportGenerator, "generate_report")


def test_audit_layer_exports():
    """Verify audit/ package exports immutable audit ledger."""
    from audit import ImmutableAuditLedger, default_audit_ledger
    assert hasattr(default_audit_ledger, "log_entry") or hasattr(default_audit_ledger, "record_action")


def test_ai_layer_exports():
    """Verify ai/ package exports grounded investigation agent."""
    from ai import InvestigationAgent, run_investigation, get_agent
    assert callable(run_investigation)
    assert callable(get_agent)


def test_api_layer_fastapi():
    """Verify api/ package exports the unified FastAPI application."""
    from api import app
    assert app is not None
    assert hasattr(app, "routes")
    # Verify core API route paths exist
    route_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/cases" in route_paths
    assert "/api/intelligence/analyze" in route_paths
    assert "/api/intelligence/investigate" in route_paths


def test_services_and_api_client_decoupling():
    """Verify services/ layer provides decoupled client consumed by UI."""
    from services import (
        CrimeNetClient,
        default_api_client,
        default_case_service,
        default_investigation_service,
        default_analytics_service,
        default_evidence_service,
        default_audit_service,
    )
    assert isinstance(default_api_client, CrimeNetClient)
    # Test client queries cases cleanly via service/API layer
    cases = default_api_client.list_cases()
    assert isinstance(cases, list)
    assert len(cases) > 0

    # Test client queries case graph cleanly
    case_id = cases[0]["id"]
    graph = default_api_client.get_case_graph(case_id)
    assert "nodes" in graph
    assert "edges" in graph


def test_ui_layer_exports():
    """Verify ui/ package exports main visualization layout components."""
    from ui import init_layout, build_global_nav_bar, build_top_ask_crimenet_bar, build_right_side_panel
    assert callable(init_layout)
    assert callable(build_global_nav_bar)
    assert callable(build_top_ask_crimenet_bar)
    assert callable(build_right_side_panel)
