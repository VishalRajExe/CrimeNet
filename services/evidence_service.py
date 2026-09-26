"""Evidence Service for CrimeNet.

Manages evidence documents, exhibits, OCR text, and cryptographic SHA-256 integrity.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from database.case_repository import default_case_repository
from utils.crypto import compute_evidence_hash

logger = logging.getLogger("CrimeNet.EvidenceService")


class EvidenceService:
    def __init__(self, repo=None):
        self.repo = repo or default_case_repository

    def list_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        """List all evidentiary exhibits attached to a case."""
        return self.repo.list_evidence(case_id)

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single evidence record by ID."""
        return self.repo.get_evidence(evidence_id)

    def ingest_evidence(
        self,
        case_id: str,
        title: str,
        evidence_type: str = "EXHIBIT",
        content: str = "",
        collected_by: str = "Forensics Unit",
        filename: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> str:
        """Ingest a new piece of evidence, calculating its non-repudiation SHA-256 hash."""
        sha_hash = compute_evidence_hash(content)
        ev_id = self.repo.add_evidence(
            case_id=case_id,
            title=title,
            evidence_type=evidence_type,
            source_ref=source_ref or f"EXHIBIT-{sha_hash[:8].upper()}",
            content=content,
            collected_by=collected_by,
            sha256_hash=sha_hash,
            filename=filename or f"{title.lower().replace(' ', '_')}.txt",
        )
        return ev_id

    # Canonical alias
    add_evidence = ingest_evidence


default_evidence_service = EvidenceService()
