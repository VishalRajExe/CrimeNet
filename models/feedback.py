"""CrimeNet Human-In-The-Loop Feedback & Audit Models."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HumanFeedbackModel(BaseModel):
    id: str
    case_id: str
    feedback_type: str
    target_id: str
    action: str  # ACCEPTED, DISMISSED, OVERRIDDEN, CORRECTED
    user_id: str = "investigator"
    notes: Optional[str] = None
    original_ai_result: Optional[str] = None
    corrected_value: Optional[str] = None
    source_ref: Optional[str] = None
    timestamp: Optional[str] = None


class AuditEntryModel(BaseModel):
    id: str
    case_id: str
    action: str
    actor: str = "investigator"
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    prev_hash: Optional[str] = None
    block_hash: str
