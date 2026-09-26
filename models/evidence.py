"""CrimeNet Evidence Models."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EvidenceModel(BaseModel):
    id: str
    case_id: str
    title: str
    evidence_type: str = "EXHIBIT"
    source_ref: Optional[str] = None
    content: Optional[str] = None
    collected_by: Optional[str] = "Forensics Unit"
    sha256_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    filename: Optional[str] = None
    file_path: Optional[str] = None
    entity_count: int = 0
    relation_count: int = 0
