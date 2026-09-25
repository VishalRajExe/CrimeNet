"""Tests for CaseDataService and the 10 Conceptual Domain Models."""

import pytest
from datetime import datetime
from storage.case_data_service import CaseDataService


@pytest.fixture(scope="module")
def case_service():
    return CaseDataService()


def test_list_and_get_cases(case_service):
    cases = case_service.list_cases()
    assert len(cases) >= 4, "Expected at least 4 existing cases in MySQL"
    
    first_case = cases[0]
    assert "id" in first_case
    assert "case_number" in first_case
    assert "title" in first_case
    assert "status" in first_case
    assert "priority" in first_case
    assert "entity_count" in first_case
    assert "relationship_count" in first_case

    fetched = case_service.get_case(first_case["id"])
    assert fetched is not None
    assert fetched["case_number"] == first_case["case_number"]


def test_case_graph_generation(case_service):
    cases = case_service.list_cases()
    # Find case with entities (case-sih-001 has 121 entities and 273 relations)
    sih_case = next((c for c in cases if c["id"] == "case-sih-001"), None)
    if not sih_case:
        sih_case = cases[0]

    graph_data = case_service.get_case_graph(sih_case["id"])
    assert graph_data["case_id"] == sih_case["id"]
    assert "elements" in graph_data
    
    nodes = [e for e in graph_data["elements"] if e.get("group") == "nodes"]
    edges = [e for e in graph_data["elements"] if e.get("group") == "edges"]
    assert len(nodes) > 0, "Expected nodes in case graph"
    assert len(edges) > 0, "Expected edges in case graph"
    assert all("case_id" in n["data"] for n in nodes)
    assert all("case_id" in e["data"] for e in edges)


def test_evidence_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    ev_id = case_service.add_evidence(
        case_id=target_case_id,
        title="Seized Samsung Galaxy S23 (CDR Dump)",
        evidence_type="DIGITAL_DEVICE",
        source_ref="IMEI-358920192837192",
        content="Call logs spanning 2026-01-01 to 2026-03-01",
        collected_by="officer_sharma",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        metadata={"device": "SM-S911B", "storage": "256GB"}
    )
    assert ev_id is not None

    evidence_list = case_service.list_evidence(target_case_id)
    assert any(e["id"] == ev_id for e in evidence_list)
    added = next(e for e in evidence_list if e["id"] == ev_id)
    assert added["title"] == "Seized Samsung Galaxy S23 (CDR Dump)"
    assert added["case_id"] == target_case_id


def test_analysis_result_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    res_id = case_service.save_analysis_result(
        case_id=target_case_id,
        task_id="community_detection",
        algorithm="louvain",
        parameters={"resolution": 1.0},
        summary={"modularity": 0.442, "num_communities": 5},
        node_metrics={"node_1": {"community": 0}, "node_2": {"community": 1}},
        executed_by="officer_verma"
    )
    assert res_id is not None

    results = case_service.list_analysis_results(target_case_id)
    assert any(r["id"] == res_id for r in results)


def test_alert_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    alert_id = case_service.create_alert(
        case_id=target_case_id,
        alert_type="ODD_HOUR",
        title="Midnight Hawala Call Pattern",
        explanation="4 repeated calls between 01:00 and 04:00 to unknown Pakistani gateway",
        severity="HIGH",
        subject="+91 98200 11223",
        related_entities=["+91 98200 11223", "+92 300 9988776"]
    )
    assert alert_id is not None

    alerts = case_service.list_alerts(target_case_id)
    assert any(a["id"] == alert_id for a in alerts)
    alert = next(a for a in alerts if a["id"] == alert_id)
    assert alert["severity"] == "HIGH"
    assert alert["case_id"] == target_case_id


def test_timeline_event_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    event_id = case_service.add_timeline_event(
        case_id=target_case_id,
        event_type="TRANSACTION",
        timestamp=datetime(2026, 2, 14, 18, 30),
        title="Hawala Token Exchange at Dadar TT",
        description="Delivery of ₹50,00,000 in cash against currency note token serial",
        location="Dadar TT Circle, Mumbai",
        confidence=0.95
    )
    assert event_id is not None

    events = case_service.list_timeline_events(target_case_id)
    assert any(e["id"] == event_id for e in events)


def test_report_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    rep_id = case_service.create_report(
        case_id=target_case_id,
        title="Preliminary Network Intelligence Briefing",
        content="Subject network reveals a bifurcated structure led by Dubai coordination nodes.",
        report_type="INVESTIGATION_SUMMARY",
        generated_by="IO_Rathore"
    )
    assert rep_id is not None

    reports = case_service.list_reports(target_case_id)
    assert any(r["id"] == rep_id for r in reports)


def test_audit_event_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    log_id = case_service.record_audit(
        user_id="io_user_01",
        action="EXPORT_CASE_DOSSIER",
        resource_type="CASE",
        resource_id=target_case_id,
        case_id=target_case_id,
        status="SUCCESS",
        details="Generated court annexure report with SHA-256 evidence chain",
        username="IO Rathore"
    )
    assert log_id is not None

    logs = case_service.list_audit_logs(case_id=target_case_id)
    assert any(l["id"] == log_id for l in logs)


def test_feedback_domain_model(case_service):
    cases = case_service.list_cases()
    target_case_id = cases[0]["id"]

    fb_id = case_service.record_feedback(
        case_id=target_case_id,
        feedback_type="LINK_PREDICTION",
        target_id="phone:9820011223_phone:9820044556",
        action="DISMISSED",
        notes="Known legal counsel number; false operational connection",
        user_id="io_user_01"
    )
    assert fb_id is not None

    feedbacks = case_service.list_feedback(target_case_id)
    assert any(f["id"] == fb_id for f in feedbacks)
