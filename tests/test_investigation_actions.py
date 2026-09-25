"""
Unit tests for Investigation Actions (internal prototype workflows),
Human-in-the-Loop (HITL) correction mechanisms, and Append-Oriented Audit Trails.
"""

import pytest
import uuid
from storage.case_data_service import CaseDataService


@pytest.fixture
def service():
    return CaseDataService()


@pytest.fixture
def test_case(service):
    # Retrieve first available case or create a mock case ID
    cases = service.list_cases()
    if cases:
        return cases[0]["id"]
    # Fallback create a test case
    cid = f"test-case-{uuid.uuid4().hex[:8]}"
    service.create_case(
        title="Automated Test Case: Hawala Syndicate",
        case_number=f"FIR-TEST-{uuid.uuid4().hex[:4].upper()}",
        description="Test case for action workflows and HITL corrections",
        investigator="Inspector Verma"
    )
    return service.list_cases()[0]["id"]


def test_investigation_action_creation_and_lifecycle(service, test_case):
    """Verify creation, validation, status progression, and audit trail of internal action workflows."""
    # 1. Validation: reason is required
    with pytest.raises(ValueError):
        service.create_investigation_action(
            case_id=test_case,
            action_type="LOOKOUT_REQUEST",
            target_entity="Vikram Malhotra",
            reason=""  # Must raise ValueError
        )

    # 2. Create Lookout Request
    action_id = service.create_investigation_action(
        case_id=test_case,
        action_type="LOOKOUT_REQUEST",
        target_entity="Vikram Malhotra",
        target_entity_type="PERSON",
        reason="Flight risk identified at IGI Airport departure terminal.",
        related_evidence="CDR_001",
        investigator_id="inv-007",
        notes="Internal prototype request pending supervisor review."
    )
    assert action_id is not None
    assert len(action_id) == 36

    # 3. Retrieve and verify action
    actions = service.list_investigation_actions(case_id=test_case)
    created_act = next((a for a in actions if a["id"] == action_id), None)
    assert created_act is not None
    assert created_act["action_type"] == "LOOKOUT_REQUEST"
    assert created_act["target_entity"] == "Vikram Malhotra"
    assert created_act["status"] == "PENDING_APPROVAL"
    assert "Flight risk" in created_act["reason"]
    assert created_act["related_evidence"] == "CDR_001"
    assert created_act["audit_id"] is not None

    # 4. Update status with audit tracking
    success = service.update_investigation_action_status(
        action_id=action_id,
        status="APPROVED",
        notes="Approved by Special CP for internal monitoring.",
        investigator_id="supervisor-001"
    )
    assert success is True

    # 5. Check updated status
    actions_updated = service.list_investigation_actions(case_id=test_case, status="APPROVED")
    act_updated = next((a for a in actions_updated if a["id"] == action_id), None)
    assert act_updated is not None
    assert act_updated["status"] == "APPROVED"

    # 6. Verify audit logs were appended
    logs = service.list_audit_logs(case_id=test_case, limit=20)
    creation_log = next((l for l in logs if l.get("result_id") == action_id and l["action"] == "ACTION_CREATED"), None)
    assert creation_log is not None
    assert creation_log["target"] == "Vikram Malhotra"
    assert "LOOKOUT_REQUEST" in creation_log["details"]

    status_log = next((l for l in logs if l.get("result_id") == action_id and l["action"] == "ACTION_STATUS_UPDATED"), None)
    assert status_log is not None
    assert status_log["old_value"] == "PENDING_APPROVAL"
    assert status_log["new_value"] == "APPROVED"


def test_human_in_the_loop_correction_preservation(service, test_case):
    """
    Verify Human-in-the-Loop mechanism:
    AI says: 'Rahul is connected to Phone 9876.'
    Investigator says: 'This information is incorrect. Phone belongs to Amit.'
    Ensure BOTH original AI result and human correction are stored without overwriting.
    """
    target = "PHONE_+91-9876543210"
    ai_claim = "AI inferred Rahul Sharma is subscriber to +91-9876543210 based on co-occurrence in CDR_001."
    human_correction = "Phone +91-9876543210 belongs to Amit Verma (KYC document verified)."
    reason = "CAF (Customer Acquisition Form) attached in FIR_102 confirms Amit Verma as registered SIM owner."
    source = "FIR_102"

    fb_id = service.record_human_correction(
        case_id=test_case,
        target_id=target,
        original_ai_result=ai_claim,
        corrected_value=human_correction,
        reason=reason,
        source_ref=source,
        investigator_id="inv-007"
    )
    assert fb_id is not None

    # Retrieve feedback rows
    feedbacks = service.list_feedback(case_id=test_case)
    saved_fb = next((f for f in feedbacks if f["id"] == fb_id), None)
    assert saved_fb is not None

    # CRITICAL: Verify BOTH original AI claim and human correction are maintained
    assert saved_fb["original_ai_result"] == ai_claim
    assert saved_fb["corrected_value"] == human_correction
    assert saved_fb["reason"] == reason
    assert saved_fb["source_ref"] == source
    assert saved_fb["action"] == "ACCEPTED"
    assert saved_fb["correction_status"] == "ACCEPTED"

    # Verify active corrections index
    active_corrections = service.get_active_corrections(case_id=test_case)
    assert target in active_corrections
    assert active_corrections[target]["corrected_value"] == human_correction

    # Verify audit entry was appended
    logs = service.list_audit_logs(case_id=test_case, limit=20)
    corr_log = next((l for l in logs if l.get("result_id") == fb_id and l["action"] == "CORRECTION_SUBMITTED"), None)
    assert corr_log is not None
    assert corr_log["old_value"] == ai_claim
    assert corr_log["new_value"] == human_correction
    assert corr_log["target"] == target
    assert corr_log["source_ref"] == source


def test_investigation_report_audit_logging(service, test_case):
    """Verify report generation records court-admissible audit log with report ID."""
    rep_title = "Interagency Intelligence Brief: Hawala Channel Alpha"
    rep_content = "Comprehensive summary of financial nodes and communication links."

    rep_id = service.create_report(
        case_id=test_case,
        title=rep_title,
        content=rep_content,
        report_type="INTERAGENCY_BRIEF",
        generated_by="Inspector Verma",
        file_path="reports/brief_alpha.pdf",
        report_format="PDF",
        metadata={"nodes_analyzed": 42, "anomalies_detected": 3}
    )
    assert rep_id is not None

    # Fetch report
    rep = service.get_report(rep_id)
    assert rep is not None
    assert rep["title"] == rep_title
    assert rep["format"] == "PDF"
    assert rep["file_path"] == "reports/brief_alpha.pdf"

    # Verify audit log
    logs = service.list_audit_logs(case_id=test_case, action="REPORT_GENERATED", limit=10)
    rep_log = next((l for l in logs if l.get("result_id") == rep_id), None)
    assert rep_log is not None
    assert rep_log["target"] == rep_title
    assert "PDF" in rep_log["details"]


def test_investigation_action_all_four_examples(service, test_case):
    """
    Verify all 4 canonical example action workflows inspired by target LEA systems:
    1. Create Lookout Request (LOC)
    2. Request Account Freeze
    3. Mark for Review
    4. Escalate Case
    """
    examples = [
        ("LOOKOUT_REQUEST", "Vikram Malhotra", "PERSON", "Suspect holds international passport and active travel tickets to Dubai.", "CDR_001"),
        ("ACCOUNT_FREEZE_REQUEST", "Mule Account 33190", "BANK_ACCOUNT", "Disbursed 45,00,000 INR across 6 offshore shell entities within 180s.", "Bank_Ledger_2026.csv"),
        ("MARK_FOR_REVIEW", "Falcon Global Trading LLC", "ORGANIZATION", "Shell entity with zero commercial activity at registered Bandra address.", "ROC_Filing_2024.pdf"),
        ("ESCALATE_CASE", "Black Falcon Hawala Syndicate", "CASE_MODULE", "Cross-border layering exceeding 50 Crore INR involving UAE/Mauritius shell conduits.", "Interim_FIR_102.pdf"),
    ]

    for atype, target, ttype, reason, ev in examples:
        act_id = service.create_investigation_action(
            case_id=test_case,
            action_type=atype,
            target_entity=target,
            target_entity_type=ttype,
            reason=reason,
            related_evidence=ev,
            investigator_id="lead_investigator"
        )
        assert act_id is not None
        act = service.get_investigation_action(act_id)
        assert act is not None
        assert act["action_type"] == atype
        assert act["target_entity"] == target
        assert act["target_entity_type"] == ttype
        assert act["reason"] == reason
        assert act["related_evidence"] == ev
        assert act["status"] == "PENDING_APPROVAL"
        assert act["audit_id"] is not None


def test_investigation_action_stored_attributes(service, test_case):
    """
    Verify all 8 mandatory fields are stored:
    - action type
    - case
    - target entity
    - reason
    - timestamp (created_at)
    - status
    - related evidence
    - audit entry
    """
    reason_text = "Factual evidence confirms high volume debit velocity indicative of mule activity."
    act_id = service.create_investigation_action(
        case_id=test_case,
        action_type="ACCOUNT_FREEZE_REQUEST",
        target_entity="SBI-ACC-9921",
        target_entity_type="BANK_ACCOUNT",
        reason=reason_text,
        related_evidence="FIU_STR_Report.pdf",
        investigator_id="inv-fraud-01"
    )

    act = service.get_investigation_action(act_id)
    assert act is not None

    # Check all 8 required fields
    assert act["action_type"] == "ACCOUNT_FREEZE_REQUEST"
    assert act["case_id"] == test_case
    assert act["target_entity"] == "SBI-ACC-9921"
    assert act["reason"] == reason_text
    assert act["created_at"] is not None
    assert act["status"] == "PENDING_APPROVAL"
    assert act["related_evidence"] == "FIU_STR_Report.pdf"
    assert act["audit_id"] is not None

    # Verify audit entry exists in audit_logs
    audit_log = service.get_audit_log(act["audit_id"])
    assert audit_log is not None
    assert audit_log["action"] == "ACTION_CREATED"
    assert audit_log["resource_type"] == "INVESTIGATION_ACTION"
    assert audit_log["resource_id"] == act_id


def test_investigation_action_reason_required_validation(service, test_case):
    """Verify that creating an action without context/reason is strictly rejected."""
    with pytest.raises(ValueError):
        service.create_investigation_action(
            case_id=test_case,
            action_type="LOOKOUT_REQUEST",
            target_entity="Suspect X",
            reason=""  # Blank reason
        )

    with pytest.raises(ValueError):
        service.create_investigation_action(
            case_id=test_case,
            action_type="ESCALATE_CASE",
            target_entity="Syndicate Y",
            reason="    \n   "  # Whitespace only
        )


def test_actions_workflow_ui_components(test_case):
    """Verify that build_actions_workflow_panel and build_actions_workflow_modal construct valid Dash trees."""
    from visualizer.actions_workflow_modal import build_actions_workflow_panel, build_actions_workflow_modal

    panel = build_actions_workflow_panel(test_case)
    assert panel is not None
    assert panel.id == "investigation-actions-panel"

    modal = build_actions_workflow_modal()
    assert modal is not None
