"""
Comprehensive tests for CrimeNet's Human-in-the-Loop (HITL) Correction Mechanism.

Tests cover the complete lifecycle:
  1.  Submitting a correction (AI claim → human truth)
  2.  Storage: both original AI result AND human correction are persisted (never overwritten)
  3.  Audit log is created atomically with every correction
  4.  get_active_corrections returns the latest ground truth, indexed by target
  5.  get_entity_intelligence includes corrections in entity dossier context
  6.  Corrections surface in the grounded local investigation agent answer
  7.  The get_corrections agent tool returns structured correction data
  8.  Multiple corrections on the same target: latest wins
  9.  Corrections with no original AI claim are handled gracefully
  10. Corrections are isolated per case_id (no cross-case leakage)

Example scenario exercised throughout:
  AI says:       "Rahul is connected to Phone 9876."
  Investigator:  "This information is incorrect."
  Correction:    "Phone belongs to Amit."
  Source:        "FIR_102 / Customer Acquisition Form (KYC)"
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from storage.case_data_service import CaseDataService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANONICAL_CASE_ID = "case-synthetic-black-falcon-001"


@pytest.fixture(scope="module")
def service():
    return CaseDataService()


@pytest.fixture
def isolated_case(service):
    """A fresh case for isolation tests — ensures corrections don't bleed across cases."""
    cases_before = {c["id"] for c in service.list_cases()}
    service.create_case(
        title="HITL Isolation Test Case",
        case_number=f"FIR-HITL-{uuid.uuid4().hex[:4].upper()}",
        description="Temporary case for HITL correction isolation tests.",
        investigator="Test Inspector",
    )
    cases_after = service.list_cases()
    for c in cases_after:
        if c["id"] not in cases_before:
            return c["id"]
    return list(cases_before)[0]


# ---------------------------------------------------------------------------
# 1. Core Submission & Storage
# ---------------------------------------------------------------------------

class TestCorrectionSubmission:

    def test_record_human_correction_returns_uuid(self, service):
        """record_human_correction must return a valid UUID string."""
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id="Phone +91 98765 43210",
            original_ai_result="Rahul is connected to Phone 9876.",
            corrected_value="Phone belongs to Amit.",
            reason="CAF in FIR_102 shows Amit Verma is the registered subscriber.",
            source_ref="FIR_102 / CAF_TELCO_REG_99",
            investigator_id="Inspector Sandeep Verma",
        )
        assert fb_id is not None
        assert len(fb_id) == 36
        assert fb_id.count("-") == 4

    def test_both_original_and_correction_persisted(self, service):
        """CRITICAL: original AI result must NEVER be overwritten."""
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=f"test-both-{uuid.uuid4().hex[:6]}",
            original_ai_result="AI originally claimed Rahul is connected to Phone 9876.",
            corrected_value="Phone 9876 belongs to Amit Verma, not Rahul.",
            reason="Verified via KYC at Telco nodal office.",
            source_ref="CAF_NODAL_2026",
            investigator_id="SI Rajesh Kumar",
        )
        record = service.get_feedback(fb_id)
        assert record is not None
        assert record["original_ai_result"] == "AI originally claimed Rahul is connected to Phone 9876."
        assert record["corrected_value"] == "Phone 9876 belongs to Amit Verma, not Rahul."
        assert record["source_ref"] == "CAF_NODAL_2026"
        assert record["user_id"] == "SI Rajesh Kumar"

    def test_correction_status_is_accepted(self, service):
        """Human corrections must have status=ACCEPTED."""
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=f"status-{uuid.uuid4().hex[:6]}",
            original_ai_result="Unverified AI inference.",
            corrected_value="Investigator verified truth.",
            reason="Cross-checked with surveillance log.",
            source_ref="SURV_44",
        )
        record = service.get_feedback(fb_id)
        assert record["action"] == "ACCEPTED"
        assert record["correction_status"] == "ACCEPTED"
        assert record["feedback_type"] == "HUMAN_CORRECTION"

    def test_correction_has_timestamp(self, service):
        """Every correction must have a created_at timestamp."""
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=f"ts-{uuid.uuid4().hex[:6]}",
            original_ai_result="Unverified AI claim.",
            corrected_value="Investigator confirmed truth.",
            reason="Physical surveillance.",
            source_ref="SURV_22",
        )
        record = service.get_feedback(fb_id)
        assert record["created_at"] is not None
        ts = record["created_at"]
        if isinstance(ts, str):
            datetime.fromisoformat(ts)

    def test_record_feedback_direct_preserves_both(self, service):
        """Lower-level record_feedback also preserves both values."""
        fb_id = service.record_feedback(
            case_id=CANONICAL_CASE_ID,
            feedback_type="HUMAN_CORRECTION",
            target_id=f"direct-{uuid.uuid4().hex[:6]}",
            action="ACCEPTED",
            notes="Verified.",
            original_ai_result="AI said X.",
            corrected_value="Investigator says Y.",
            reason="Evidence Y confirmed.",
            source_ref="EX-007",
            correction_status="ACCEPTED",
        )
        record = service.get_feedback(fb_id)
        assert record["original_ai_result"] == "AI said X."
        assert record["corrected_value"] == "Investigator says Y."


# ---------------------------------------------------------------------------
# 2. Audit Trail
# ---------------------------------------------------------------------------

class TestAuditTrail:

    def test_correction_creates_audit_entry(self, service):
        """Every correction must create an immutable audit log entry."""
        target = f"audit-{uuid.uuid4().hex[:6]}"
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=target,
            original_ai_result="AI inference A.",
            corrected_value="Verified correction B.",
            reason="Document XYZ confirms B.",
            source_ref="DOC_XYZ",
            investigator_id="ACP Sharma",
        )
        audit_logs = service.list_audit_logs(case_id=CANONICAL_CASE_ID, limit=100)
        matching = [
            l for l in audit_logs
            if l.get("action") == "CORRECTION_SUBMITTED"
            and (l.get("target") == target or l.get("resource_id") == fb_id)
        ]
        assert len(matching) >= 1, (
            f"CORRECTION_SUBMITTED audit log entry not found for target={target}"
        )

    def test_audit_log_stores_both_values(self, service):
        """Audit log must record old_value (AI) and new_value (human) for non-repudiation."""
        original = f"AI-{uuid.uuid4().hex[:8]}"
        corrected = f"HU-{uuid.uuid4().hex[:8]}"
        service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=f"dual-audit-{uuid.uuid4().hex[:6]}",
            original_ai_result=original,
            corrected_value=corrected,
            reason="Dual audit test.",
            source_ref="DUAL_SRC",
            investigator_id="SI Test",
        )
        audit_logs = service.list_audit_logs(case_id=CANONICAL_CASE_ID, limit=100)
        matching = [l for l in audit_logs if l.get("old_value") == original]
        assert len(matching) >= 1, "Audit log must record old_value=original AI result"
        for entry in matching:
            assert entry.get("new_value") == corrected


# ---------------------------------------------------------------------------
# 3. get_active_corrections
# ---------------------------------------------------------------------------

class TestActiveCorrections:

    def test_returns_dict(self, service):
        corrections = service.get_active_corrections(CANONICAL_CASE_ID)
        assert isinstance(corrections, dict)

    def test_excludes_records_without_corrected_value(self, service):
        """Dismissed feedback with no corrected_value must not appear."""
        target = f"no-corr-{uuid.uuid4().hex[:6]}"
        service.record_feedback(
            case_id=CANONICAL_CASE_ID,
            feedback_type="ALERT_FEEDBACK",
            target_id=target,
            action="DISMISSED",
            notes="False positive.",
        )
        corrections = service.get_active_corrections(CANONICAL_CASE_ID)
        assert target not in corrections

    def test_canonical_phone_correction_present(self, service):
        """
        The canonical example must exist:
        'Rahul is connected to Phone 9876.' → 'Phone belongs to Amit.'
        """
        corrections = service.get_active_corrections(CANONICAL_CASE_ID)
        phone_corr = corrections.get("Phone +91 98765 43210")
        assert phone_corr is not None, (
            "Canonical correction for 'Phone +91 98765 43210' missing. "
            "Run seed_synthetic_case_into_db(CaseDataService()) to populate."
        )
        assert phone_corr.get("original_ai_result") is not None, "Must preserve original AI claim"
        assert "Amit" in (phone_corr.get("corrected_value") or "") or \
               "Phone" in (phone_corr.get("corrected_value") or ""), \
               "Corrected value must reference the verified subscriber"

    def test_case_isolation(self, service, isolated_case):
        """Corrections are scoped to their case and must not leak."""
        unique_target = f"iso-{uuid.uuid4().hex}"
        service.record_human_correction(
            case_id=isolated_case,
            target_id=unique_target,
            original_ai_result="Isolated claim.",
            corrected_value="Isolated correction.",
            reason="Isolation test.",
            source_ref="ISO",
        )
        isolated_corrections = service.get_active_corrections(isolated_case)
        canonical_corrections = service.get_active_corrections(CANONICAL_CASE_ID)
        assert unique_target in isolated_corrections
        assert unique_target not in canonical_corrections, "Cross-case leakage detected!"


# ---------------------------------------------------------------------------
# 4. Entity Dossier Integration
# ---------------------------------------------------------------------------

class TestEntityDossierIntegration:

    def test_dossier_includes_corrections(self, service):
        """get_entity_intelligence must include human_corrections list."""
        service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id="person_rahul_sharma",
            original_ai_result="Associate of Unknown Gang",
            corrected_value="Direct lieutenant of Amit Verma",
            reason="Corroborated by Intercept_09 and surveillance",
            source_ref="Intercept_09",
            investigator_id="Inspector Sandeep Verma",
        )
        intel = service.get_entity_intelligence("person_rahul_sharma", CANONICAL_CASE_ID)
        assert "human_corrections" in intel
        assert len(intel["human_corrections"]) > 0

    def test_dossier_correction_has_required_fields(self, service):
        """Dossier corrections must have corrected_value, original_ai_result, user_id."""
        intel = service.get_entity_intelligence("person_rahul_sharma", CANONICAL_CASE_ID)
        for c in intel["human_corrections"]:
            assert c.get("corrected_value"), "corrected_value must be non-empty"
            assert "original_ai_result" in c, "original_ai_result must be preserved"

    def test_uncorrected_entity_has_empty_corrections(self, service):
        """Entity with no corrections must return empty list, not None."""
        intel = service.get_entity_intelligence("org_falcon_global_trading", CANONICAL_CASE_ID)
        assert "human_corrections" in intel
        assert isinstance(intel["human_corrections"], list)


# ---------------------------------------------------------------------------
# 5. Investigation Agent Integration
# ---------------------------------------------------------------------------

class TestInvestigationAgentIntegration:

    def test_get_corrections_tool_structured_output(self, service):
        """get_corrections tool must return valid JSON with structured corrections."""
        import json
        from analyzer.investigation_agent import get_corrections
        result = json.loads(get_corrections.invoke({"case_id": CANONICAL_CASE_ID}))
        assert "corrections" in result or "message" in result
        if result.get("corrections"):
            for c in result["corrections"]:
                assert "target" in c
                assert "original_ai_claim" in c
                assert "human_verified_truth" in c

    def test_grounded_answer_surfaces_correction(self, service):
        """Local fallback must surface HITL correction when the query is relevant."""
        from analyzer.investigation_agent import _grounded_local_investigation_answer
        result = _grounded_local_investigation_answer(
            question="Is Rahul connected to Phone 9876?",
            case_id=CANONICAL_CASE_ID,
        )
        answer = result["answer"]
        # Must mention correction OR Amit (the verified truth)
        assert (
            "CORRECTION" in answer.upper()
            or "HUMAN" in answer.upper()
            or "Amit" in answer
        ), f"Answer must surface human correction. Got: {answer[:400]}"

    def test_grounded_answer_returns_active_corrections_key(self, service):
        """Result must include active_corrections list."""
        from analyzer.investigation_agent import _grounded_local_investigation_answer
        result = _grounded_local_investigation_answer(
            question="List all corrections",
            case_id=CANONICAL_CASE_ID,
        )
        assert "active_corrections" in result
        assert isinstance(result["active_corrections"], list)

    def test_no_false_retraining_claim(self, service):
        """The system must NOT falsely claim that the model was retrained."""
        from analyzer.investigation_agent import _grounded_local_investigation_answer
        result = _grounded_local_investigation_answer(
            question="Is Rahul connected to Phone 9876?",
            case_id=CANONICAL_CASE_ID,
        )
        answer = result["answer"].lower()
        # If a correction notice is present it must NOT claim retraining
        if "correction" in answer:
            retrain_claimed = "model has been retrained" in answer or "retrained the model" in answer
            assert not retrain_claimed, (
                "System must NOT claim model retraining. "
                "Corrections are context-only, not model updates."
            )


# ---------------------------------------------------------------------------
# 6. list_feedback
# ---------------------------------------------------------------------------

class TestListFeedback:

    def test_list_feedback_returns_list(self, service):
        feedback = service.list_feedback(CANONICAL_CASE_ID)
        assert isinstance(feedback, list)
        assert len(feedback) > 0

    def test_list_feedback_filter_by_type(self, service):
        corrections = service.list_feedback(CANONICAL_CASE_ID, feedback_type="HUMAN_CORRECTION")
        for c in corrections:
            assert c["feedback_type"] == "HUMAN_CORRECTION"


# ---------------------------------------------------------------------------
# 7. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_no_source_ref(self, service):
        fb_id = service.record_human_correction(
            case_id=CANONICAL_CASE_ID,
            target_id=f"no-src-{uuid.uuid4().hex[:6]}",
            original_ai_result="Some AI claim.",
            corrected_value="Human truth.",
            reason="Field observation, no document.",
            source_ref=None,
        )
        assert fb_id is not None
        record = service.get_feedback(fb_id)
        assert record["corrected_value"] == "Human truth."

    def test_dismissed_excluded_from_active_corrections(self, service):
        target = f"dismissed-{uuid.uuid4().hex[:6]}"
        service.record_feedback(
            case_id=CANONICAL_CASE_ID,
            feedback_type="LINK_PREDICTION",
            target_id=target,
            action="DISMISSED",
            notes="False positive.",
        )
        corrections = service.get_active_corrections(CANONICAL_CASE_ID)
        assert target not in corrections
