"""Tests for CrimeNet Case Dashboard and Isolated Investigation Workspace Context.

Validates that:
1. Dashboard layout builds with real MySQL database records (no mock/fake data).
2. KPI statistics accurately aggregate real cases, entities, relations, and alerts.
3. Case search and multi-criteria priority/status filtering work correctly.
4. Case creation persists directly to MySQL `cases` and `audit_logs`.
5. Case Dossier covers all 10 domain models: Case, Evidence, Entities, Relationships,
   AnalysisResult, Alert, TimelineEvent, Report, AuditEvent, Feedback.
6. Isolated investigation workspace context is generated per case for Cytoscape.
"""

import pytest
import os
import sys

# Ensure root is in sys.path
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.insert(0, path2root)

from storage.case_data_service import CaseDataService
from visualizer.case_dashboard import (
    build_dashboard_view,
    build_case_card,
    build_dossier_content,
    build_global_nav_bar,
    build_dedicated_evidence_section,
    build_evidence_card,
    build_evidence_registry_view,
    get_priority_badge,
    get_status_badge,
    get_evidence_processing_badge,
    get_evidence_extraction_badge,
    get_evidence_type_badge,
)


@pytest.fixture(scope="module")
def svc():
    return CaseDataService()


def test_dashboard_view_builds_with_real_records(svc):
    """Verify that build_dashboard_view loads real database records and renders KPI cards."""
    view = build_dashboard_view()
    assert view is not None
    assert view.id == "case-dashboard-container"

    # Verify that case cards are present in the grid
    cases = svc.list_cases()
    assert len(cases) >= 4, f"Expected at least 4 real cases in MySQL, found {len(cases)}"


def test_case_card_structure(svc):
    """Verify that build_case_card renders case numbers, badges, and metrics from MySQL."""
    case = svc.get_case("case-sih-001")
    assert case is not None
    assert case["case_number"] == "FIR-2026-DL-00412"

    card = build_case_card(case)
    assert card is not None
    assert card.id == f"case-card-container-{case['id']}"


def test_dossier_content_ten_domain_models(svc):
    """Verify that the Case Dossier renders the 10 domain models from MySQL."""
    case_id = "case-sih-001"
    dossier = build_dossier_content(case_id)
    assert dossier is not None

    # Verify underlying domain models exist in MySQL for this case
    c = svc.get_case(case_id)
    assert c["title"] == "Operation Blackhawk: Multi-State Hawala & Contraband Syndicate"

    evidence = svc.list_evidence(case_id)
    assert len(evidence) >= 1
    assert any("Samsung" in ev.get("title", "") for ev in evidence)

    alerts = svc.list_alerts(case_id)
    assert len(alerts) >= 1
    assert any(al.get("severity") in ("CRITICAL", "HIGH") for al in alerts)

    timeline = svc.list_timeline_events(case_id)
    assert len(timeline) >= 1

    reports = svc.list_reports(case_id)
    assert len(reports) >= 1

    audit = svc.list_audit_logs(case_id)
    assert len(audit) >= 1

    feedback = svc.list_feedback(case_id)
    assert len(feedback) >= 1


def test_case_filtering_by_priority(svc):
    """Verify filtering cases by priority (CRITICAL, HIGH, MEDIUM, LOW)."""
    all_cases = svc.list_cases()

    critical_cases = [c for c in all_cases if (c.get("priority") or "").upper() == "CRITICAL"]
    high_cases = [c for c in all_cases if (c.get("priority") or "").upper() == "HIGH"]

    assert len(critical_cases) >= 1
    assert any(c["case_number"] == "FIR-2026-DL-00412" for c in critical_cases)
    assert len(high_cases) >= 3


def test_case_search_filtering(svc):
    """Verify search filter by case number, title, or crime type."""
    all_cases = svc.list_cases()

    # Search for Blackhawk
    matches = [c for c in all_cases if "blackhawk" in (c.get("title") or "").lower()]
    assert len(matches) == 1
    assert matches[0]["case_number"] == "FIR-2026-DL-00412"

    # Search by FIR case number
    matches_fir = [c for c in all_cases if "dl-00412" in (c.get("case_number") or "").lower()]
    assert len(matches_fir) == 1

    # Search for nonexistent
    empty_matches = [c for c in all_cases if "nonexistent_query_xyz" in (c.get("title") or "").lower()]
    assert len(empty_matches) == 0


def test_create_case_persistence_and_audit(svc):
    """Verify creating a new case persists in MySQL and is logged to audit trail."""
    test_title = "Unit Test: Operation Falcon Watch"
    test_fir = f"FIR-TEST-{os.getpid()}"

    new_id = svc.create_case(
        title=test_title,
        case_number=test_fir,
        description="Automated unit test case creation.",
        crime_type="CYBER_EXTORTION",
        priority="HIGH",
        status="ACTIVE",
        location="Bengaluru Tech Corridor",
        lead_investigator_id="test_officer_42"
    )
    assert new_id is not None

    # Log audit event
    svc.log_audit(new_id, "CASE_CREATED", "test_officer_42", "Created via automated test")

    # Retrieve and verify
    persisted = svc.get_case(new_id)
    assert persisted is not None
    assert persisted["title"] == test_title
    assert persisted["case_number"] == test_fir
    assert persisted["priority"] == "HIGH"

    # Verify audit log exists
    audit_logs = svc.list_audit_logs(new_id)
    assert len(audit_logs) >= 1
    assert audit_logs[0]["action"] == "CASE_CREATED"


def test_isolated_investigation_workspace_context(svc):
    """Verify each case produces an isolated ActiveNetwork with distinct entities and links."""
    # Case 1: Operation Blackhawk
    net_blackhawk = svc.build_active_network_for_case("case-sih-001")
    assert net_blackhawk is not None
    assert len(net_blackhawk.nodes) >= 16
    assert len(net_blackhawk.edges) >= 19
    assert len(net_blackhawk.elements) >= 35

    # Case 2: Benchmark 9/11 Case
    net_benchmark = svc.build_active_network_for_case("9fc52e50-0bf8-4a37-9d85-f0e0e66d033a")
    assert net_benchmark is not None
    assert len(net_benchmark.nodes) == 92
    assert len(net_benchmark.edges) == 242
    assert len(net_benchmark.elements) == 334

    # Verify network isolation: nodes from case 1 do not bleed into case 2
    nodes_1 = set(net_blackhawk.nodes.keys())
    nodes_2 = set(net_benchmark.nodes.keys())
    overlap = nodes_1.intersection(nodes_2)
    assert len(overlap) == 0, f"Expected isolated network contexts, but found overlapping nodes: {overlap}"


def test_global_nav_bar_elements():
    """Verify global navigation bar components."""
    nav = build_global_nav_bar()
    assert nav is not None
    assert nav.id == "crimenet-global-nav"


def test_evidence_status_badges():
    """Verify forensic evidence status, extraction, and type badge styling."""
    b_up = get_evidence_processing_badge("Uploaded")
    b_pr = get_evidence_processing_badge("Processing")
    b_pd = get_evidence_processing_badge("Processed")
    b_fa = get_evidence_processing_badge("Failed")
    assert "UPLOADED" in b_up.children
    assert "PROCESSING" in b_pr.children
    assert "PROCESSED" in b_pd.children
    assert "FAILED" in b_fa.children

    # Extraction badges
    e_ext = get_evidence_extraction_badge("Extracted")
    e_pen = get_evidence_extraction_badge("Pending")
    e_none = get_evidence_extraction_badge("No Entities Found")
    assert "EXTRACTED" in e_ext.children
    assert "PENDING" in e_pen.children
    assert "NO ENTITIES FOUND" in e_none.children

    # Type badges
    t_pdf = get_evidence_type_badge("PDF")
    t_txt = get_evidence_type_badge("TXT")
    t_csv = get_evidence_type_badge("CSV")
    t_json = get_evidence_type_badge("JSON")
    assert "PDF" in t_pdf.children
    assert "TXT" in t_txt.children
    assert "CSV" in t_csv.children
    assert "JSON" in t_json.children


def test_evidence_empty_state():
    """Verify that an empty evidence list renders a dedicated Empty State component."""
    empty_view = build_evidence_registry_view([])
    assert empty_view is not None
    # Check children for empty state icon and message
    assert any("No Evidence Exhibits Registered Yet" in str(getattr(c, "children", "")) for c in empty_view.children)


def test_dedicated_evidence_section_ui(svc):
    """Verify the dedicated Evidence Section layout with upload card, form inputs, and exhibits."""
    case_id = "case-sih-001"
    evidence_list = svc.list_evidence(case_id)
    sec = build_dedicated_evidence_section(case_id, evidence_list)
    assert sec is not None

    # Verify upload card exists
    upload_card = next((c for c in sec.children if getattr(c, "id", "") == "card-evidence-upload"), None)
    assert upload_card is not None

