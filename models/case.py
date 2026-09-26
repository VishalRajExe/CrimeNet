"""CrimeNet Case Domain Models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CasePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class CaseModel(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str] = None
    crime_type: str = "ORGANIZED_CRIME"
    priority: CasePriority = CasePriority.MEDIUM
    status: CaseStatus = CaseStatus.OPEN
    entity_count: int = 0
    relationship_count: int = 0
    alert_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
