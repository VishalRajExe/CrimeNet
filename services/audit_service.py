"""Audit & Compliance Service for CrimeNet.

Maintains tamper-evident SHA-256 chained audit logs and Human-In-The-Loop feedback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from database.case_repository import default_case_repository

logger = logging.getLogger("CrimeNet.AuditService")


class AuditService:
    def __init__(self, repo=None):
        self.repo = repo or default_case_repository

    def record_action(
        self,
        case_id: str,
        action: str,
        actor: str = "investigator",
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an action into the cryptographic audit trail."""
        return self.repo.record_audit_action(
            case_id=case_id,
            action=action,
            actor=actor,
            details=details or {},
        )

    def get_audit_trail(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit log entries for a case."""
        return self.repo.get_audit_trail(case_id)

    def record_feedback(
        self,
        case_id: str,
        feedback_type: str,
        target_id: str,
        action: str,
        notes: Optional[str] = None,
        user_id: str = "investigator",
        original_ai_result: Optional[str] = None,
        corrected_value: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> str:
        """Record investigator feedback or dispute."""
        return self.repo.record_feedback(
            case_id=case_id,
            feedback_type=feedback_type,
            target_id=target_id,
            action=action,
            notes=notes,
            user_id=user_id,
            original_ai_result=original_ai_result,
            corrected_value=corrected_value,
            source_ref=source_ref,
        )

    def record_human_correction(
        self,
        case_id: str,
        target_id: str,
        original_ai_result: str,
        corrected_value: str,
        reason: str,
        source_ref: Optional[str] = None,
        feedback_type: str = "HUMAN_CORRECTION",
        user_id: str = "investigator",
        investigator_id: Optional[str] = None,
    ) -> str:
        """Record structured HITL correction preserving original and corrected value."""
        return self.repo.record_human_correction(
            case_id=case_id,
            target_id=target_id,
            original_ai_result=original_ai_result,
            corrected_value=corrected_value,
            reason=reason,
            source_ref=source_ref,
            feedback_type=feedback_type,
            user_id=user_id,
            investigator_id=investigator_id,
        )

    def get_active_corrections(self, case_id: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve dictionary of active investigator corrections for a case."""
        return self.repo.get_active_corrections(case_id)


default_audit_service = AuditService()
