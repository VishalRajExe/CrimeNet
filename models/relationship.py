"""CrimeNet Relationship Models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RelationshipModality(str, Enum):
    OBSERVED = "OBSERVED"
    EXTRACTED = "EXTRACTED"
    PREDICTED = "PREDICTED"
    INFERRED = "INFERRED"


class AcceptanceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROPOSED = "PROPOSED"
    REJECTED = "REJECTED"


class RelationshipModel(BaseModel):
    id: str
    case_id: str
    source: str
    target: str
    relationship_type: str = "CONNECTED_TO"
    modality: RelationshipModality = RelationshipModality.OBSERVED
    acceptance: AcceptanceStatus = AcceptanceStatus.CONFIRMED
    confidence: float = 1.0
    weight: float = 1.0
    source_ref: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
