"""CrimeNet Case-Oriented Data Service Layer.

Provides complete Python access to the 10 conceptual domain models:
1. Case
2. Evidence
3. Entity
4. Relationship
5. AnalysisResult
6. Alert
7. TimelineEvent
8. Report
9. AuditEvent
10. Feedback

Every domain object is traceable to a Case where appropriate.
Loads credentials strictly from .env without hardcoding.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import pymysql
from dotenv import load_dotenv

load_dotenv()


class CaseDataService:
    """Thread-safe connection and query interface for CrimeNet case data."""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", 3306))
        self.db = os.getenv("DB_NAME", "crimenet")
        self.user = os.getenv("DB_USERNAME", "root")
        self.password = os.getenv("DB_PASSWORD", "admin")

    def _get_connection(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )

    # ----------------------------------------------------------------------- #
    # 1. CASE DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def list_cases(self) -> List[Dict[str, Any]]:
        """List all cases with summarized entity, relationship, and alert counts."""
        query = """
        SELECT 
            c.id, c.case_number, c.title, c.description, c.crime_type,
            c.status, c.priority, c.lead_investigator_id, c.created_by,
            c.location, c.incident_date, c.created_at, c.updated_at, c.metadata,
            (SELECT COUNT(*) FROM investigation_entities WHERE case_id = c.id) AS entity_count,
            (SELECT COUNT(*) FROM entity_relationships WHERE case_id = c.id) AS relationship_count,
            (SELECT COUNT(*) FROM alerts WHERE case_id = c.id) AS alert_count
        FROM cases c
        ORDER BY 
            CASE c.priority 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
                ELSE 5 
            END,
            c.updated_at DESC;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific case by id or case_number."""
        query = "SELECT * FROM cases WHERE id = %s OR case_number = %s LIMIT 1;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id, case_id))
                return cur.fetchone()

    def create_case(
        self,
        title: str,
        case_number: Optional[str] = None,
        description: str = "",
        crime_type: str = "ORGANIZED_CRIME",
        priority: str = "HIGH",
        status: str = "OPEN",
        lead_investigator_id: Optional[str] = None,
        created_by: str = "u-002",
        location: str = "",
        incident_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new investigation case."""
        case_id = str(uuid.uuid4())
        c_num = case_number or f"CASE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        p_val = priority.upper()
        if p_val not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            p_val = "HIGH"
        s_val = status.upper()
        if s_val not in ("ACTIVE", "ARCHIVED", "CLOSED", "OPEN", "UNDER_REVIEW"):
            s_val = "OPEN"
        meta_str = json.dumps(metadata) if metadata else None

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Ensure created_by satisfies foreign key constraint
                cur.execute("SELECT id FROM users WHERE id = %s LIMIT 1;", (created_by,))
                if not cur.fetchone():
                    cur.execute("SELECT id FROM users LIMIT 1;")
                    first_u = cur.fetchone()
                    created_by = first_u["id"] if first_u else "u-002"

                query = """
                INSERT INTO cases (
                    id, case_number, title, description, crime_type, status, priority,
                    lead_investigator_id, created_by, location, incident_date, metadata, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                );
                """
                cur.execute(query, (
                    case_id, c_num, title, description, crime_type, s_val, p_val,
                    lead_investigator_id, created_by, location, incident_date, meta_str
                ))
        return case_id

    # ----------------------------------------------------------------------- #
    # 2. EVIDENCE DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def add_evidence(
        self,
        case_id: str,
        title: str,
        evidence_type: str,
        source_ref: Optional[str] = None,
        content: Optional[str] = None,
        collected_by: Optional[str] = None,
        sha256_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None,
        processing_status: str = "Uploaded",
        extraction_status: str = "Pending",
        description: Optional[str] = None,
        error_message: Optional[str] = None,
        entity_count: int = 0,
        relation_count: int = 0,
    ) -> str:
        """Register evidence traceable to a specific case with full metadata."""
        ev_id = str(uuid.uuid4())
        meta_str = json.dumps(metadata) if metadata else None
        query = """
        INSERT INTO evidence (
            id, case_id, title, evidence_type, source_ref, content,
            collected_at, collected_by, sha256_hash, metadata, created_at,
            filename, processing_status, extraction_status, description,
            error_message, entity_count, relation_count
        ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s);
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    ev_id, case_id, title, evidence_type, source_ref, content,
                    collected_by, sha256_hash, meta_str,
                    filename, processing_status, extraction_status, description,
                    error_message, entity_count, relation_count
                ))
        return ev_id

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single evidence record by ID."""
        query = "SELECT * FROM evidence WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (evidence_id,))
                return cur.fetchone()

    def update_evidence(self, evidence_id: str, **kwargs) -> bool:
        """Dynamically update evidence fields (processing_status, extraction_status, etc.)."""
        if not kwargs:
            return False
        
        valid_cols = {
            "title", "evidence_type", "source_ref", "content", "collected_by",
            "sha256_hash", "metadata", "filename", "processing_status",
            "extraction_status", "description", "error_message",
            "entity_count", "relation_count"
        }
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in valid_cols:
                updates.append(f"`{k}` = %s")
                if k == "metadata" and isinstance(v, dict):
                    params.append(json.dumps(v))
                else:
                    params.append(v)
        
        if not updates:
            return False
            
        params.append(evidence_id)
        query = f"UPDATE evidence SET {', '.join(updates)} WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.rowcount > 0

    def list_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        """List all evidence linked to a case."""
        query = "SELECT * FROM evidence WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    def link_entity_to_case(
        self,
        case_id: str,
        name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source_text: Optional[str] = None,
        added_by: str = "u-002"
    ) -> str:
        """Insert or retrieve an investigation entity linked to a case."""
        allowed = {'BANK_ACCOUNT', 'CASE_REF', 'EVENT', 'LOCATION', 'ORGANIZATION', 'PERSON', 'PHONE', 'VEHICLE'}
        e_type = entity_type.upper()
        if e_type not in allowed:
            mapping = {
                "ACCOUNT": "BANK_ACCOUNT",
                "MOBILE": "PHONE",
                "ORG": "ORGANIZATION",
                "CAR": "VEHICLE",
                "BIKE": "VEHICLE",
                "LOC": "LOCATION",
                "GPE": "LOCATION",
                "FAC": "LOCATION",
                "CASE_ID": "CASE_REF",
                "DATE": "EVENT",
                "PAN": "CASE_REF",
                "PASSPORT": "CASE_REF",
                "UPI": "BANK_ACCOUNT",
                "IMEI": "PHONE",
                "AMOUNT": "EVENT",
            }
            e_type = mapping.get(e_type, "PERSON")

        check_query = "SELECT id, properties FROM investigation_entities WHERE case_id = %s AND name = %s AND entity_type = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query, (case_id, name.strip(), e_type))
                existing = cur.fetchone()
                if existing:
                    if properties:
                        existing_props = {}
                        if existing.get("properties"):
                            try:
                                existing_props = json.loads(existing["properties"]) if isinstance(existing["properties"], str) else existing["properties"]
                            except Exception:
                                existing_props = {}
                        merged_props = {**existing_props, **properties}
                        cur.execute(
                            "UPDATE investigation_entities SET properties = %s WHERE id = %s;",
                            (json.dumps(merged_props), existing["id"])
                        )
                    return existing["id"]

                ent_id = str(uuid.uuid4())
                prop_str = json.dumps(properties) if properties else None
                insert_query = """
                INSERT INTO investigation_entities (
                    id, case_id, name, entity_type, properties, verified, source_text, added_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, 1, %s, %s, NOW());
                """
                cur.execute(insert_query, (ent_id, case_id, name.strip(), e_type, prop_str, source_text, added_by))
                return ent_id

    def link_relationship_to_case(
        self,
        case_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        predicted: bool = False
    ) -> str:
        """Insert a relationship between two entities in a case."""
        check_query = """
        SELECT id, properties FROM entity_relationships 
        WHERE case_id = %s AND source_entity_id = %s AND target_entity_id = %s AND relationship_type = %s;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query, (case_id, source_entity_id, target_entity_id, relationship_type))
                existing = cur.fetchone()
                if existing:
                    if properties:
                        existing_props = {}
                        if existing.get("properties"):
                            try:
                                existing_props = json.loads(existing["properties"]) if isinstance(existing["properties"], str) else existing["properties"]
                            except Exception:
                                existing_props = {}
                        merged_props = {**existing_props, **properties}
                        cur.execute(
                            "UPDATE entity_relationships SET properties = %s, confidence = %s WHERE id = %s;",
                            (json.dumps(merged_props), confidence, existing["id"])
                        )
                    return existing["id"]

                rel_id = str(uuid.uuid4())
                prop_str = json.dumps(properties) if properties else None
                insert_query = """
                INSERT INTO entity_relationships (
                    id, case_id, source_entity_id, target_entity_id, relationship_type,
                    confidence, predicted, properties, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
                """
                cur.execute(insert_query, (
                    rel_id, case_id, source_entity_id, target_entity_id,
                    relationship_type, confidence, int(predicted), prop_str
                ))
                return rel_id

    # ----------------------------------------------------------------------- #
    # 3. ENTITY & 4. RELATIONSHIP (CYTOSCAPE GRAPH)
    # ----------------------------------------------------------------------- #
    def get_case_graph(self, case_id: str) -> Dict[str, Any]:
        """Fetch nodes and edges for a case formatted for Cytoscape visualization."""
        node_query = "SELECT * FROM investigation_entities WHERE case_id = %s;"
        edge_query = "SELECT * FROM entity_relationships WHERE case_id = %s;"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(node_query, (case_id,))
                raw_nodes = cur.fetchall()
                cur.execute(edge_query, (case_id,))
                raw_edges = cur.fetchall()

        elements = []
        for n in raw_nodes:
            props = {}
            if n.get("properties"):
                try:
                    props = json.loads(n["properties"]) if isinstance(n["properties"], str) else n["properties"]
                except Exception:
                    props = {"raw": n["properties"]}
            elements.append({
                "group": "nodes",
                "data": {
                    "id": n["id"],
                    "label": n["name"],
                    "name": n["name"],
                    "type": (n["entity_type"] or "PERSON").lower(),
                    "verified": bool(n.get("verified", 0)),
                    "info": props,
                    "properties": props,
                    "case_id": case_id,
                }
            })

        for e in raw_edges:
            edge_props = {}
            if e.get("properties"):
                try:
                    edge_props = json.loads(e["properties"]) if isinstance(e["properties"], str) else e["properties"]
                except Exception:
                    edge_props = {"raw": e["properties"]}
            elements.append({
                "group": "edges",
                "data": {
                    "id": e["id"],
                    "source": e["source_entity_id"],
                    "target": e["target_entity_id"],
                    "label": e["relationship_type"],
                    "type": e["relationship_type"],
                    "confidence": float(e.get("confidence", 1.0)),
                    "predicted": bool(e.get("predicted", 0)),
                    "info": edge_props,
                    "properties": edge_props,
                    "case_id": case_id,
                }
            })

        return {
            "case_id": case_id,
            "nodes_count": len(raw_nodes),
            "edges_count": len(raw_edges),
            "elements": elements,
            "nodes": [el["data"] for el in elements if el.get("group") == "nodes"],
            "edges": [el["data"] for el in elements if el.get("group") == "edges"],
        }

    # ----------------------------------------------------------------------- #
    # 5. ANALYSIS RESULT DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def save_analysis_result(
        self,
        case_id: str,
        task_id: str,
        algorithm: str,
        parameters: Optional[Dict[str, Any]] = None,
        summary: Optional[Dict[str, Any]] = None,
        node_metrics: Optional[Dict[str, Any]] = None,
        edge_metrics: Optional[Any] = None,
        executed_by: Optional[str] = None,
    ) -> str:
        """Persist a complete analytical execution run traceable to a case."""
        res_id = str(uuid.uuid4())
        query = """
        INSERT INTO analysis_results (
            id, case_id, task_id, algorithm, parameters, summary,
            node_metrics, edge_metrics, executed_by, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    res_id, case_id, task_id, algorithm,
                    json.dumps(parameters) if parameters else None,
                    json.dumps(summary) if summary else None,
                    json.dumps(node_metrics) if node_metrics else None,
                    json.dumps(edge_metrics) if edge_metrics else None,
                    executed_by
                ))
        return res_id

    def list_analysis_results(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve historical analysis runs for a case."""
        query = "SELECT * FROM analysis_results WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    # ----------------------------------------------------------------------- #
    # 6. ALERT (FORENSIC ANOMALY) DOMAIN MODEL
    # ----------------------------------------------------------------------- #
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
        """Record an explainable forensic anomaly alert for an investigation case."""
        alert_id = str(uuid.uuid4())
        s_val = severity.upper()
        if s_val not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            s_val = "MEDIUM"
        rel_str = json.dumps(related_entities) if related_entities else None

        query = """
        INSERT INTO alerts (
            id, case_id, alert_type, severity, title, explanation,
            subject, related_entities, status, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'OPEN', NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    alert_id, case_id, alert_type, s_val, title, explanation, subject, rel_str
                ))
        return alert_id

    def list_alerts(self, case_id: str) -> List[Dict[str, Any]]:
        """List active and reviewed alerts for a case."""
        query = "SELECT * FROM alerts WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    # ----------------------------------------------------------------------- #
    # 7. TIMELINE EVENT DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def add_timeline_event(
        self,
        case_id: str,
        event_type: str,
        timestamp: datetime,
        title: str,
        description: str = "",
        source_ref: Optional[str] = None,
        primary_entity_id: Optional[str] = None,
        secondary_entity_id: Optional[str] = None,
        confidence: float = 1.0,
        location: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a chronological event traceable to a case."""
        ev_id = str(uuid.uuid4())
        query = """
        INSERT INTO timeline_events (
            id, case_id, event_type, timestamp, title, description, source_ref,
            primary_entity_id, secondary_entity_id, confidence, location, metadata, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    ev_id, case_id, event_type, timestamp, title, description, source_ref,
                    primary_entity_id, secondary_entity_id, confidence, location,
                    json.dumps(metadata) if metadata else None
                ))
        return ev_id

    def list_timeline_events(self, case_id: str) -> List[Dict[str, Any]]:
        """Fetch all chronological events for a case."""
        query = "SELECT * FROM timeline_events WHERE case_id = %s ORDER BY timestamp ASC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    # ----------------------------------------------------------------------- #
    # 8. REPORT DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def create_report(
        self,
        case_id: str,
        title: str,
        content: str,
        report_type: str = "INVESTIGATION_SUMMARY",
        generated_by: str = "system",
    ) -> str:
        """Save a narrative FIR, briefing, or case report."""
        rep_id = str(uuid.uuid4())
        query = """
        INSERT INTO reports (id, case_id, title, content, report_type, generated_by, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (rep_id, case_id, title, content, report_type, generated_by))
        return rep_id

    def list_reports(self, case_id: str) -> List[Dict[str, Any]]:
        """List reports belonging to a case."""
        query = "SELECT * FROM reports WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    # ----------------------------------------------------------------------- #
    # 9. AUDIT EVENT (AUDIT LOG) DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def record_audit(
        self,
        user_id: str,
        action: str,
        resource_type: str = "CASE",
        resource_id: Optional[str] = None,
        case_id: Optional[str] = None,
        status: str = "SUCCESS",
        details: str = "",
        ip_address: str = "127.0.0.1",
        username: Optional[str] = None,
    ) -> str:
        """Record an immutable, court-admissible audit log linked to an investigator and case."""
        log_id = str(uuid.uuid4())
        query = """
        INSERT INTO audit_logs (
            id, user_id, action, resource_type, resource_id, case_id,
            status, details, ip_address, timestamp, created_at, username
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(6), %s);
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    log_id, user_id, action, resource_type, resource_id, case_id,
                    status, details, ip_address, username or user_id
                ))
        return log_id

    def log_audit(self, case_id: str, action: str, username: str = "investigator", details: str = "") -> str:
        """Convenience alias to record an audit log for a case."""
        return self.record_audit(
            user_id="u-002",
            action=action,
            case_id=case_id,
            resource_type="CASE",
            resource_id=case_id,
            details=details,
            username=username
        )

    def list_audit_logs(self, case_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve audit history, optionally filtered by case."""
        if case_id:
            query = "SELECT * FROM audit_logs WHERE case_id = %s ORDER BY timestamp DESC LIMIT %s;"
            params = (case_id, limit)
        else:
            query = "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT %s;"
            params = (limit,)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    # ----------------------------------------------------------------------- #
    # 10. FEEDBACK (HUMAN-IN-THE-LOOP) DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def record_feedback(
        self,
        case_id: str,
        feedback_type: str,
        target_id: str,
        action: str,
        notes: str = "",
        user_id: Optional[str] = None,
    ) -> str:
        """Persist investigator feedback (Accept, Dismiss, Flag) on AI predictions/alerts."""
        fb_id = str(uuid.uuid4())
        a_val = action.upper()
        if a_val not in ("ACCEPTED", "DISMISSED", "FLAGGED", "CONFIRMED"):
            a_val = "DISMISSED"

        query = """
        INSERT INTO feedback (
            id, case_id, feedback_type, target_id, action, notes, user_id, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (fb_id, case_id, feedback_type, target_id, a_val, notes, user_id))
        return fb_id

    def list_feedback(self, case_id: str) -> List[Dict[str, Any]]:
        """List all human feedback recorded for a case."""
        query = "SELECT * FROM feedback WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    def build_active_network_for_case(self, case_id: str):
        """Construct a fully-initialized ActiveNetwork populated with a case's entities and relations."""
        from storage.builtin_datasets import ActiveNetwork

        c = self.get_case(case_id)
        if not c:
            return None

        real_case_id = c["id"]
        case_title = c.get("title") or c.get("case_number") or real_case_id

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM investigation_entities WHERE case_id = %s;", (real_case_id,))
                db_nodes = cur.fetchall()
                cur.execute("SELECT * FROM entity_relationships WHERE case_id = %s;", (real_case_id,))
                db_edges = cur.fetchall()

        net = ActiveNetwork(path_2_data=None, from_file=False, uploaded=False, initialize=False)
        net.network_name = case_title
        net.nodes = {n["id"]: {
            "name": n["name"],
            "type": (n["entity_type"] or "person").lower(),
            "label": n["name"],
            "verified": bool(n.get("verified", 0)),
            "case_id": case_id
        } for n in db_nodes}
        net.edges = []
        net.adj_list = {n["id"]: [] for n in db_nodes}

        for i, e in enumerate(db_edges):
            src = e["source_entity_id"]
            tgt = e["target_entity_id"]
            rel = e["relationship_type"]
            edge_obj = {
                "source": src,
                "target": tgt,
                "properties": {
                    "label": rel,
                    "type": rel,
                    "confidence": float(e.get("confidence", 1.0)),
                    "predicted": bool(e.get("predicted", 0)),
                    "case_id": case_id
                }
            }
            net.edges.append(edge_obj)
            if src in net.adj_list:
                net.adj_list[src].append(i)
            if tgt in net.adj_list:
                net.adj_list[tgt].append(i)

        net.node_types = {net.nodes[n]["type"]: {} for n in net.nodes}
        net.edge_types = {e["properties"]["type"]: {} for e in net.edges}
        net.initialize(params={"network_name": case_title})
        return net
