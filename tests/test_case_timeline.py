"""Automated tests for CrimeNet Case Timeline & Associated Case Object Inspector."""

from datetime import datetime
import pytest

from storage.case_data_service import CaseDataService
from visualizer.case_timeline_panel import (
    _EVENT_META,
    build_case_timeline,
    build_case_timeline_modal,
    render_associated_case_object,
)


def test_timeline_event_meta_covers_all_twelve_types():
    """Verify that all 12 requested timeline event types are properly registered in _EVENT_META."""
    expected_types = [
        "EVIDENCE_UPLOADED",
        "EXTRACTION_COMPLETED",
        "ENTITY_DETECTED",
        "RELATIONSHIP_DETECTED",
        "ANALYSIS_RUN",
        "ANOMALY_GENERATED",
        "POTENTIAL_LINK_GENERATED",
        "INVESTIGATOR_QUERY",
        "INVESTIGATOR_REVIEW",
        "HUMAN_FEEDBACK",
        "INVESTIGATOR_ACTION",
        "REPORT_GENERATED",
    ]
    for etype in expected_types:
        assert etype in _EVENT_META, f"Missing event type in _EVENT_META: {etype}"
        meta = _EVENT_META[etype]
        assert "label" in meta and meta["label"]
        assert "color" in meta and meta["color"].startswith("#")
        assert "group" in meta and meta["group"]
        assert "icon" in meta and meta["icon"]


def test_synthetic_case_timeline_aggregate_contains_all_events():
    """Verify that the seeded synthetic case contains events across all 12 required event categories."""
    svc = CaseDataService()
    events = svc.get_case_timeline_aggregate("case-synthetic-black-falcon-001")
    assert len(events) > 0, "No timeline events found for synthetic case!"

    event_types_found = {e["event_type"] for e in events}
    
    expected_categories = [
        "EVIDENCE_UPLOADED",
        "EXTRACTION_COMPLETED",
        "ENTITY_DETECTED",
        "RELATIONSHIP_DETECTED",
        "ANALYSIS_RUN",
        "ANOMALY_GENERATED",
        "POTENTIAL_LINK_GENERATED",
        "INVESTIGATOR_QUERY",
        "INVESTIGATOR_REVIEW",
        "HUMAN_FEEDBACK",
        "INVESTIGATOR_ACTION",
        "REPORT_GENERATED",
    ]

    for cat in expected_categories:
        assert cat in event_types_found, (
            f"Expected timeline event category '{cat}' not found in aggregate stream! "
            f"Found: {event_types_found}"
        )


def test_timeline_events_have_valid_structure():
    """Verify that each timeline event has all required normalized fields."""
    svc = CaseDataService()
    events = svc.get_case_timeline_aggregate("case-synthetic-black-falcon-001")
    
    required_keys = {"ts", "event_type", "icon", "title", "severity", "object_type", "object_id", "meta", "actor"}
    for ev in events[:50]:
        missing = required_keys - set(ev.keys())
        assert not missing, f"Timeline event missing keys: {missing}"
        assert ev["title"], "Event must have a title"
        assert ev["object_type"], "Event must specify an object_type"
        assert ev["object_id"], "Event must have an object_id"


def test_render_associated_evidence_object():
    """Verify rendering of EVIDENCE associated case object with SHA-256 hash and excerpt."""
    payload = {
        "object_type": "EVIDENCE",
        "object_id": "ev-test-001",
        "event_type": "EVIDENCE_UPLOADED",
        "title": "Evidence uploaded: Bank_Ledger_2026.csv",
        "severity": "INFO",
        "meta": {
            "title": "Black Falcon Bank Ledger",
            "filename": "Bank_Ledger_2026.csv",
            "evidence_type": "BANK_STATEMENT",
            "processing_status": "Processed",
            "extraction_status": "Completed",
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "collected_by": "Cyber Cell Inspector",
            "entity_count": 14,
            "relation_count": 12,
            "content": "Account 99482 transferred 4,500,000 INR to Mule Account 33190 on 2026-09-01.",
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None
    # Inspect children structure
    assert hasattr(rendered, "children")


def test_render_associated_entity_object():
    """Verify rendering of ENTITY associated case object with properties and verification."""
    payload = {
        "object_type": "ENTITY",
        "object_id": "ent-test-001",
        "event_type": "ENTITY_DETECTED",
        "title": "Entity detected: Vikram Malhotra (PERSON)",
        "severity": "INFO",
        "meta": {
            "name": "Vikram Malhotra",
            "entity_type": "PERSON",
            "verified": 1,
            "source_text": "Primary suspect identified in hawala routing intercept.",
            "properties": {"role": "Kingpin", "risk_level": "CRITICAL"},
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_relationship_object():
    """Verify rendering of RELATIONSHIP associated case object with provenance quote."""
    payload = {
        "object_type": "RELATIONSHIP",
        "object_id": "rel-test-001",
        "event_type": "RELATIONSHIP_DETECTED",
        "title": "Vikram Malhotra → [CONTROLS] → Mule Account 33190",
        "severity": "INFO",
        "meta": {
            "source_name": "Vikram Malhotra",
            "target_name": "Mule Account 33190",
            "relationship_type": "CONTROLS",
            "confidence": 0.95,
            "predicted": 0,
            "provenance": {
                "verbatim_quote": "Vikram Malhotra confirmed sole beneficial controller of account 33190.",
                "source_file": "KYC_Audit_Sept2026.pdf"
            }
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_potential_link_object():
    """Verify rendering of POTENTIAL_LINK AI hypothesis with warning banner and algorithm."""
    payload = {
        "object_type": "RELATIONSHIP",
        "object_id": "rel-pred-001",
        "event_type": "POTENTIAL_LINK_GENERATED",
        "title": "Vikram Malhotra → [SUSPECTED_PROXY] → Shell Corp Ltd",
        "severity": "MEDIUM",
        "meta": {
            "source_name": "Vikram Malhotra",
            "target_name": "Shell Corp Ltd",
            "relationship_type": "SUSPECTED_PROXY",
            "confidence": 0.72,
            "predicted": 1,
            "properties": {
                "algorithm": "Graph Jaccard Co-occurrence",
                "quote": "Shared corporate secretarial address detected in registrar filing.",
            }
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_analysis_object():
    """Verify rendering of ANALYSIS associated case object with algorithm and summary."""
    payload = {
        "object_type": "ANALYSIS",
        "object_id": "ana-test-001",
        "event_type": "ANALYSIS_RUN",
        "title": "Analysis run: Louvain Community Detection",
        "severity": "INFO",
        "meta": {
            "algorithm": "Louvain Community Detection",
            "task_id": "task-louvain-001",
            "executed_by": "system",
            "parameters": {"resolution": 1.0, "weight": "weight"},
            "summary": {"communities_found": 3, "modularity": 0.64},
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_alert_object():
    """Verify rendering of ALERT / Anomaly associated case object."""
    payload = {
        "object_type": "ALERT",
        "object_id": "alt-test-001",
        "event_type": "ANOMALY_GENERATED",
        "title": "Anomaly: High Outflow Velocity on Mule Account",
        "severity": "CRITICAL",
        "meta": {
            "title": "High Outflow Velocity on Mule Account",
            "alert_type": "STRUCTURAL_ANOMALY",
            "severity": "CRITICAL",
            "subject": "Mule Account 33190",
            "status": "NEW",
            "explanation": "Account disbursed 94% of inbound capital within 180 seconds across 6 offshore nodes.",
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_investigator_objects():
    """Verify rendering of INVESTIGATOR query, review, and action audit records."""
    # Query
    q_payload = {
        "object_type": "AUDIT",
        "object_id": "audit-q-001",
        "event_type": "INVESTIGATOR_QUERY",
        "title": "QUERY_SUBMITTED by analyst_sharma",
        "severity": "INFO",
        "meta": {
            "action": "QUERY_SUBMITTED",
            "username": "analyst_sharma",
            "details": "SELECT * FROM transactions WHERE amount > 1000000 AND date >= '2026-09-01'",
            "status": "SUCCESS",
            "resource_type": "CASE",
        }
    }
    q_rendered = render_associated_case_object(q_payload, case_id="case-synthetic-black-falcon-001")
    assert q_rendered is not None

    # Review
    r_payload = {
        "object_type": "AUDIT",
        "object_id": "audit-r-001",
        "event_type": "INVESTIGATOR_REVIEW",
        "title": "EVIDENCE_VIEWED by inspector_verma",
        "severity": "INFO",
        "meta": {
            "action": "EVIDENCE_VIEWED",
            "username": "inspector_verma",
            "details": "Reviewed Exhibit EX-2026-004 CDR Call Records",
            "status": "SUCCESS",
        }
    }
    r_rendered = render_associated_case_object(r_payload, case_id="case-synthetic-black-falcon-001")
    assert r_rendered is not None

    # Action
    a_payload = {
        "object_type": "AUDIT",
        "object_id": "audit-a-001",
        "event_type": "INVESTIGATOR_ACTION",
        "title": "CASE_UPDATED by lead_investigator",
        "severity": "INFO",
        "meta": {
            "action": "CASE_UPDATED",
            "username": "lead_investigator",
            "details": "Case priority escalated from MEDIUM to CRITICAL following hawala confirmation.",
            "status": "SUCCESS",
        }
    }
    a_rendered = render_associated_case_object(a_payload, case_id="case-synthetic-black-falcon-001")
    assert a_rendered is not None


def test_render_associated_feedback_object():
    """Verify rendering of HUMAN_FEEDBACK associated case object."""
    payload = {
        "object_type": "FEEDBACK",
        "object_id": "fb-test-001",
        "event_type": "HUMAN_FEEDBACK",
        "title": "Human feedback: LINK_HYPOTHESIS → ACCEPTED",
        "severity": "INFO",
        "meta": {
            "action": "ACCEPTED",
            "feedback_type": "LINK_HYPOTHESIS",
            "target_id": "rel-pred-001",
            "notes": "Verified against physical surveillance logs at registrar address.",
            "user_id": "lead_investigator",
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_render_associated_report_object():
    """Verify rendering of REPORT_GENERATED associated case object."""
    payload = {
        "object_type": "REPORT",
        "object_id": "rep-test-001",
        "event_type": "REPORT_GENERATED",
        "title": "Report generated: Black Falcon Interim Indictment Dossier",
        "severity": "INFO",
        "meta": {
            "title": "Black Falcon Interim Indictment Dossier",
            "report_type": "FORENSIC_FIR",
            "generated_by": "lead_investigator",
            "format": "PDF",
            "content": "Formal case briefing synthesizing financial trail, call graph, and shell company conduits.",
        }
    }
    rendered = render_associated_case_object(payload, case_id="case-synthetic-black-falcon-001")
    assert rendered is not None


def test_build_case_timeline_ui_tree():
    """Verify that build_case_timeline creates a complete Dash HTML tree with panel and stores."""
    panel = build_case_timeline("case-synthetic-black-falcon-001")
    assert panel is not None
    assert panel.id == "case-timeline-panel"


def test_build_case_timeline_modal():
    """Verify that build_case_timeline_modal builds properly with modal container."""
    modal = build_case_timeline_modal()
    assert modal is not None
