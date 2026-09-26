"""Investigation Service for CrimeNet.

Coordinates AI Agent reasoning, grounded evidentiary search, and GraphRAG queries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CrimeNet.InvestigationService")


class InvestigationService:
    def __init__(self):
        pass

    def run_investigation(
        self,
        case_id: str,
        query: str,
        max_hops: int = 2,
        focus_entity_id: Optional[str] = None,
        include_financial: bool = True,
        confidence_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """Execute grounded AI investigation over case graph and evidence."""
        from analyzer.investigation_agent import run_investigation
        return run_investigation(
            case_id=case_id,
            query=query,
            max_hops=max_hops,
            focus_entity_id=focus_entity_id,
            include_financial=include_financial,
            confidence_threshold=confidence_threshold,
        )

    def query_graphrag(
        self,
        case_id: str,
        query: str,
        search_type: str = "local",
    ) -> Dict[str, Any]:
        """Execute GraphRAG query with preserved source citations and legal disclaimers."""
        from storage.case_data_service import CaseDataService
        svc = CaseDataService()
        return svc.correlate_case_graphrag_with_neo4j(case_id)


default_investigation_service = InvestigationService()
