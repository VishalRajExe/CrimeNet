"""CrimeNet Database Layer - Case Repository & Connection Management.

Provides unified database operations across MySQL and SQLite without duplication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from storage.case_data_service import CaseDataService


class CaseRepository(CaseDataService):
    """Authoritative Case Data Repository for CrimeNet."""

    def get_case_dossier(self, case_id: str) -> Dict[str, Any]:
        """Aggregate case records, evidence, graph, and alerts into a dossier."""
        case = self.get_case(case_id)
        evidence = self.list_evidence(case_id)
        graph = self.get_case_graph(case_id)
        alerts = self.list_alerts(case_id)
        actions = self.list_investigation_actions(case_id)
        timeline = self.list_timeline_events(case_id)
        return {
            "case": case,
            "evidence": evidence,
            "graph": graph,
            "alerts": alerts,
            "actions": actions,
            "timeline": timeline,
        }

    # Canonical aliases
    create_evidence = CaseDataService.add_evidence


# Global singleton instance
default_case_repository = CaseRepository()
