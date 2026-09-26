"""CrimeNet API Client.

Allows Dash UI components to consume the FastAPI service layer
without tight coupling to direct internal database or graph functions.
Supports HTTP REST communication with automatic direct service fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

from config.settings import API_BASE_URL, CRIMENET_API_KEY
from services.case_service import default_case_service
from services.investigation_service import default_investigation_service
from services.analytics_service import default_analytics_service
from services.evidence_service import default_evidence_service
from services.audit_service import default_audit_service

logger = logging.getLogger("CrimeNet.ApiClient")


class CrimeNetClient:
    """Client for consuming CrimeNet API & Service layer."""

    def __init__(self, base_url: str = API_BASE_URL, api_key: str = CRIMENET_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "X-Officer-Badge": "INSP-4409",
        }
        if api_key:
            self.headers["X-API-Key"] = api_key
        self.timeout = 2.0  # Fast timeout for local API check

    def _http_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self.headers, params=params)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    def _http_post(self, endpoint: str, json_data: Dict[str, Any]) -> Optional[Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self.headers, json=json_data)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    # ── Cases ────────────────────────────────────────────────────────────────
    def list_cases(
        self,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List cases via REST API or service layer."""
        data = self._http_get("/api/cases")
        if data is not None and isinstance(data, list):
            cases = data
            if priority and priority != "ALL":
                cases = [c for c in cases if (c.get("priority") or "").upper() == priority.upper()]
            if status and status != "ALL":
                cases = [c for c in cases if (c.get("status") or "").upper() == status.upper()]
            if query and query.strip():
                q = query.strip().lower()
                cases = [c for c in cases if q in (c.get("title") or "").lower() or q in (c.get("case_number") or "").lower()]
            return cases
        return default_case_service.list_cases(priority=priority, status=status, query=query)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case metadata."""
        data = self._http_get("/api/cases")
        if data is not None and isinstance(data, list):
            for c in data:
                if c.get("id") == case_id:
                    return c
        return default_case_service.get_case(case_id)

    def create_case(self, **kwargs) -> str:
        """Create case via REST API or service layer."""
        res = self._http_post("/api/cases", kwargs)
        if res and isinstance(res, dict) and "id" in res:
            return res["id"]
        return default_case_service.create_case(**kwargs)

    def get_case_graph(self, case_id: str) -> Dict[str, Any]:
        """Get Cytoscape graph elements for a case."""
        data = self._http_get(f"/api/graph/{case_id}")
        if data is not None and isinstance(data, dict) and "nodes" in data:
            return data
        return default_case_service.get_case_graph(case_id)

    def get_case_dossier(self, case_id: str) -> Dict[str, Any]:
        """Get full multi-domain dossier for a case."""
        return default_case_service.get_case_dossier(case_id)

    # ── Investigation & AI ───────────────────────────────────────────────────
    def run_investigation(self, case_id: str, query: str, **kwargs) -> Dict[str, Any]:
        """Run grounded investigation query."""
        payload = {"case_id": case_id, "query": query, **kwargs}
        res = self._http_post("/api/intelligence/investigate", payload)
        if res is not None and isinstance(res, dict) and "answer" in res:
            return res
        return default_investigation_service.run_investigation(case_id=case_id, query=query, **kwargs)

    # ── Analytics ────────────────────────────────────────────────────────────
    def run_analytics(
        self, function_id: str, algo_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute graph analytics algorithms."""
        payload = {
            "functionId": function_id,
            "algoId": algo_id,
            "nodes": nodes,
            "edges": edges,
        }
        res = self._http_post("/api/intelligence/analyze", payload)
        if res is not None and isinstance(res, dict):
            return res

        if function_id in ("social_influence", "centrality"):
            return default_analytics_service.compute_centrality(nodes, edges, metric=algo_id)
        elif function_id == "community":
            return default_analytics_service.detect_communities(nodes, edges, algorithm=algo_id)
        elif function_id == "link_prediction":
            return {"data": default_analytics_service.predict_links(nodes, edges, method=algo_id)}
        return {}

    def find_shortest_path(self, elements: List[Dict[str, Any]], source_id: str, target_id: str) -> Dict[str, Any]:
        """Find shortest path between entities."""
        return default_analytics_service.find_path(elements, source_id, target_id)

    # ── Evidence ─────────────────────────────────────────────────────────────
    def list_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        """List case evidence exhibits."""
        data = self._http_get(f"/api/database/evidence/{case_id}")
        if data is not None and isinstance(data, list):
            return data
        return default_evidence_service.list_evidence(case_id)

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get single evidence record."""
        return default_evidence_service.get_evidence(evidence_id)

    def list_alerts(self, case_id: str) -> List[Dict[str, Any]]:
        """List forensic anomaly alerts for a case."""
        data = self._http_get("/api/alerts")
        if data is not None and isinstance(data, list):
            return [a for a in data if a.get("case_id") == case_id]
        return default_case_service.list_alerts(case_id)

    def get_case_timeline_aggregate(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve timeline events for a case."""
        data = self._http_get(f"/api/cases/{case_id}/timeline")
        if data is not None and isinstance(data, list):
            return data
        return default_case_service.get_case_timeline_aggregate(case_id)

    def get_relationship_intelligence(self, edge_id: str, case_id: str = "") -> Dict[str, Any]:
        """Retrieve relationship intelligence and provenance."""
        return default_case_service.get_relationship_intelligence(edge_id, case_id)

    # ── Audit & Feedback ─────────────────────────────────────────────────────
    def record_feedback(self, **kwargs) -> str:
        """Submit Human-in-the-loop feedback."""
        res = self._http_post("/api/feedback", kwargs)
        if res and isinstance(res, dict) and "id" in res:
            return res["id"]
        return default_audit_service.record_feedback(**kwargs)

    def record_human_correction(self, **kwargs) -> str:
        """Submit structured Human-in-the-loop correction."""
        return default_audit_service.record_human_correction(**kwargs)

    def get_active_corrections(self, case_id: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve active corrections dictionary."""
        return default_audit_service.get_active_corrections(case_id)

    def get_audit_trail(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit log."""
        data = self._http_get(f"/api/cases/{case_id}/audit")
        if data is not None and isinstance(data, list):
            return data
        return default_audit_service.get_audit_trail(case_id)


# Global client singleton
default_api_client = CrimeNetClient()

