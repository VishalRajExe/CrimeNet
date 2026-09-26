"""Case Service for CrimeNet.

Encapsulates case retrieval, management, filtering, and graph assembly.
Single authoritative source of business logic for cases.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from database.case_repository import default_case_repository

logger = logging.getLogger("CrimeNet.CaseService")


class CaseService:
    def __init__(self, repo=None):
        self.repo = repo or default_case_repository

    def list_cases(
        self,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List cases with optional priority, status, and text search filters."""
        cases = self.repo.list_cases()
        if priority and priority != "ALL":
            cases = [c for c in cases if (c.get("priority") or "").upper() == priority.upper()]
        if status and status != "ALL":
            cases = [c for c in cases if (c.get("status") or "").upper() == status.upper()]
        if query and query.strip():
            q = query.strip().lower()
            cases = [
                c for c in cases
                if q in (c.get("title") or "").lower()
                or q in (c.get("case_number") or "").lower()
                or q in (c.get("description") or "").lower()
                or q in (c.get("crime_type") or "").lower()
            ]
        return cases

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single case metadata."""
        return self.repo.get_case(case_id)

    def create_case(
        self,
        title: str,
        case_number: Optional[str] = None,
        crime_type: str = "ORGANIZED_CRIME",
        priority: str = "MEDIUM",
        status: str = "OPEN",
        description: str = "",
        location: str = "Multi-Jurisdiction",
        lead_officer: str = "Lead Investigator",
        case_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Create a new case and persist in database."""
        return self.repo.create_case(
            title=title,
            case_number=case_number,
            crime_type=crime_type,
            priority=priority,
            status=status,
            description=description,
            location=location,
            lead_investigator_id=lead_officer,
            case_id=case_id,
            **kwargs,
        )

    def get_case_graph(self, case_id: str) -> Dict[str, Any]:
        """Retrieve unified Cytoscape-compatible node and edge elements for a case."""
        return self.repo.get_case_graph(case_id)

    def get_case_dossier(self, case_id: str) -> Dict[str, Any]:
        """Generate structured multi-domain case dossier."""
        return self.repo.get_case_dossier(case_id)

    def list_alerts(self, case_id: str) -> List[Dict[str, Any]]:
        """List forensic anomaly alerts for a case."""
        return self.repo.list_alerts(case_id)

    def create_alert(
        self,
        case_id: str,
        alert_type: str,
        title: str,
        explanation: str,
        severity: str = "MEDIUM",
        subject: Optional[str] = None,
        related_entities: Optional[List[str]] = None,
    ) -> str:
        """Create and persist a forensic anomaly alert for an investigation case."""
        return self.repo.create_alert(
            case_id=case_id,
            alert_type=alert_type,
            title=title,
            explanation=explanation,
            severity=severity,
            subject=subject,
            related_entities=related_entities,
        )

    def list_alerts_filtered(
        self,
        case_id: str,
        entity_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List alerts for a case with filtering."""
        return self.repo.list_alerts_filtered(
            case_id=case_id,
            entity_types=entity_types,
            statuses=statuses,
            severity=severity,
            alert_type=alert_type,
            limit=limit,
        )

    def get_case_timeline_aggregate(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve aggregated chronological timeline events for a case."""
        return self.repo.get_case_timeline_aggregate(case_id)

    def get_relationship_intelligence(self, edge_id: str, case_id: str = "") -> Dict[str, Any]:
        """Retrieve evidentiary provenance and intelligence for a relationship."""
        return self.repo.get_relationship_intelligence(edge_id, case_id)


# Singleton instance
default_case_service = CaseService()

