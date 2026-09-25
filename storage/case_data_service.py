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
        case_id: Optional[str] = None,
        investigator: Optional[str] = None,
    ) -> str:
        """Create a new investigation case."""
        case_id = case_id or str(uuid.uuid4())
        lead_id = lead_investigator_id or investigator
        if lead_id and len(lead_id) > 36:
            lead_id = lead_id[:36]
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
                    lead_id, created_by, location, incident_date, meta_str
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
        name: Optional[str] = None,
        entity_type: str = "PERSON",
        properties: Optional[Dict[str, Any]] = None,
        source_text: Optional[str] = None,
        added_by: str = "u-002",
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        """Insert or retrieve an investigation entity linked to a case."""
        actual_name = (name or entity_name or entity_id or "UNNAMED").strip()
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

        check_query = "SELECT id, properties FROM investigation_entities WHERE case_id = %s AND (id = %s OR (name = %s AND entity_type = %s));"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query, (case_id, entity_id or "", actual_name, e_type))
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

                ent_id = entity_id or str(uuid.uuid4())
                prop_dict = dict(properties) if properties else {}
                if role and "role" not in prop_dict:
                    prop_dict["role"] = role
                prop_str = json.dumps(prop_dict) if prop_dict else None
                insert_query = """
                INSERT INTO investigation_entities (
                    id, case_id, name, entity_type, properties, verified, source_text, added_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, 1, %s, %s, NOW());
                """
                cur.execute(insert_query, (ent_id, case_id, actual_name, e_type, prop_str, source_text, added_by))
                return ent_id

    def link_relationship_to_case(
        self,
        case_id: str,
        source_entity_id: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        relationship_type: str = "CONNECTED_TO",
        confidence: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        predicted: bool = False,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        weight: Optional[float] = None,
        source_ref: Optional[str] = None,
    ) -> str:
        """Insert a relationship between two entities in a case."""
        s_id = source_entity_id or source_id
        t_id = target_entity_id or target_id
        if not s_id or not t_id:
            raise ValueError("source_entity_id and target_entity_id are required")

        prop_dict = dict(properties) if properties else {}
        if weight is not None and "weight" not in prop_dict:
            prop_dict["weight"] = weight
        if source_ref and "source_ref" not in prop_dict:
            prop_dict["source_ref"] = source_ref

        check_query = """
        SELECT id, properties FROM entity_relationships 
        WHERE case_id = %s AND source_entity_id = %s AND target_entity_id = %s AND relationship_type = %s;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query, (case_id, s_id, t_id, relationship_type))
                existing = cur.fetchone()
                if existing:
                    if prop_dict:
                        existing_props = {}
                        if existing.get("properties"):
                            try:
                                existing_props = json.loads(existing["properties"]) if isinstance(existing["properties"], str) else existing["properties"]
                            except Exception:
                                existing_props = {}
                        merged_props = {**existing_props, **prop_dict}
                        cur.execute(
                            "UPDATE entity_relationships SET properties = %s, confidence = %s WHERE id = %s;",
                            (json.dumps(merged_props), confidence, existing["id"])
                        )
                    return existing["id"]

                rel_id = str(uuid.uuid4())
                prop_str = json.dumps(prop_dict) if prop_dict else None
                insert_query = """
                INSERT INTO entity_relationships (
                    id, case_id, source_entity_id, target_entity_id, relationship_type,
                    confidence, properties, predicted, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
                """
                cur.execute(insert_query, (
                    rel_id, case_id, s_id, t_id, relationship_type,
                    confidence, prop_str, 1 if predicted else 0
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
            modality = str(edge_props.get("modality") or ("PREDICTED" if e.get("predicted") else "OBSERVED")).upper()
            acceptance = str(edge_props.get("acceptance_status") or edge_props.get("acceptance") or ("PROPOSED" if e.get("predicted") else "CONFIRMED")).upper()
            provenance = edge_props.get("provenance", {})
            src_file = provenance.get("source_file") or edge_props.get("source_ref") or edge_props.get("source_file") or edge_props.get("evidence_id") or ""
            quote = provenance.get("verbatim_quote") or edge_props.get("quote") or edge_props.get("evidence_quote") or ""
            s_ref = edge_props.get("source_ref") or provenance.get("source_file") or src_file or ""

            elements.append({
                "group": "edges",
                "data": {
                    "id": e["id"],
                    "db_id": e["id"],
                    "source": e["source_entity_id"],
                    "target": e["target_entity_id"],
                    "label": e["relationship_type"],
                    "type": e["relationship_type"],
                    "confidence": float(e.get("confidence", 1.0)),
                    "predicted": bool(e.get("predicted", 0)),
                    "modality": modality,
                    "acceptance": acceptance,
                    "provenance": provenance,
                    "source_file": src_file,
                    "source_ref": s_ref,
                    "quote": quote,
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

    def get_analysis_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific analysis execution result by ID."""
        query = "SELECT * FROM analysis_results WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (analysis_id,))
                return cur.fetchone()


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

    def list_alerts_filtered(
        self,
        case_id: str,
        entity_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List alerts for a case with optional entity-type and status filtering.

        Extended fields (score, source, review_time, entity_type, entity_id)
        are parsed from the related_entities JSON column — fully backward-
        compatible with rows inserted by the original create_alert() method.

        :param entity_types: Filter by entity type e.g. ['PERSON', 'ACCOUNT'].
        :param statuses:     Filter by alert status (NEW, REVIEWED, DISMISSED, CONFIRMED).
        :param severity:     Filter by severity (CRITICAL, HIGH, MEDIUM, LOW).
        :param alert_type:   Filter by alert_type string.
        :param limit:        Maximum results to return.
        :returns: List of normalised alert dicts with all display fields.
        """
        base_query = "SELECT * FROM alerts WHERE case_id = %s"
        params: List[Any] = [case_id]

        if severity:
            base_query += " AND severity = %s"
            params.append(severity.upper())
        if alert_type:
            base_query += " AND alert_type = %s"
            params.append(alert_type)

        base_query += " ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(base_query, tuple(params))
                rows = cur.fetchall()

        results = []
        for row in rows:
            extended = {}
            rel_raw = row.get("related_entities")
            if rel_raw:
                try:
                    extended = json.loads(rel_raw) if isinstance(rel_raw, str) else rel_raw
                except Exception:
                    extended = {}

            # Effective status: JSON field takes precedence; map legacy 'OPEN' -> 'NEW'
            eff_status = extended.get("status") or row.get("status") or "NEW"
            if eff_status in ("OPEN",):
                eff_status = "NEW"

            entity_type = (extended.get("entity_type") or "UNKNOWN").upper()

            # Apply Python-side filters
            if statuses and eff_status not in [s.upper() for s in statuses]:
                continue
            if entity_types and entity_type not in [e.upper() for e in entity_types]:
                continue

            results.append({
                "alert_id":           row.get("id"),
                "case_id":            row.get("case_id"),
                "entity":             row.get("subject"),
                "entity_id":          extended.get("entity_id"),
                "entity_type":        entity_type,
                "type":               row.get("alert_type"),
                "severity":           row.get("severity"),
                "reason":             row.get("explanation", ""),
                "score":              extended.get("score"),
                "anomaly_rank":       extended.get("anomaly_rank"),
                "status":             eff_status,
                "source":             extended.get("source", "IsolationForest"),
                "created_time":       str(row.get("created_at", "")),
                "review_time":        extended.get("review_time"),
                "supporting_signals": extended.get("supporting_signals", {}),
            })

        return results

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single alert by ID."""
        query = "SELECT * FROM alerts WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (alert_id,))
                return cur.fetchone()


    def update_alert_status(
        self,
        alert_id: str,
        new_status: str,
        reviewer_notes: str = "",
    ) -> bool:
        """
        Transition an alert to a new status and record the review time.

        :param alert_id:       Alert UUID.
        :param new_status:     One of NEW | REVIEWED | DISMISSED | CONFIRMED.
        :param reviewer_notes: Optional free-text notes from the reviewing investigator.
        :returns: True if at least one row was updated.
        """
        valid = {"NEW", "REVIEWED", "DISMISSED", "CONFIRMED"}
        status_up = new_status.upper()
        if status_up not in valid:
            return False

        from datetime import datetime as _dt
        review_time = _dt.utcnow().isoformat() if status_up != "NEW" else None

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT related_entities FROM alerts WHERE id = %s;", (alert_id,))
                row = cur.fetchone()
                if not row:
                    return False

                extended = {}
                rel_raw = row.get("related_entities")
                if rel_raw:
                    try:
                        extended = json.loads(rel_raw) if isinstance(rel_raw, str) else rel_raw
                    except Exception:
                        extended = {}

                extended["status"]         = status_up
                extended["review_time"]    = review_time
                extended["reviewer_notes"] = reviewer_notes

                cur.execute(
                    "UPDATE alerts SET status = %s, related_entities = %s WHERE id = %s;",
                    (status_up, json.dumps(extended), alert_id),
                )
                return cur.rowcount > 0

    def run_anomaly_detection(
        self,
        case_id: str,
        contamination: float = 0.05,
        persist: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Run Isolation Forest anomaly detection on the case graph and return alerts.

        :param case_id:       Case to analyse.
        :param contamination: Expected fraction of anomalous nodes (0.01–0.20).
        :param persist:       If True, save detected alerts to the database.
        :returns: List of anomaly alert dicts.
        """
        from analyzer.anomaly_detection import detect_from_case
        return detect_from_case(case_id, contamination=contamination, persist_alerts=persist)

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

    def get_timeline_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chronological crime event by ID."""
        query = "SELECT * FROM timeline_events WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (event_id,))
                return cur.fetchone()


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
        file_path: Optional[str] = None,
        report_format: str = "TEXT",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a narrative FIR, briefing, or case report and log an audit event."""
        rep_id = str(uuid.uuid4())
        query = """
        INSERT INTO reports (id, case_id, title, content, report_type, generated_by, file_path, `format`, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    rep_id, case_id, title, content, report_type, generated_by,
                    file_path, report_format, json.dumps(metadata) if metadata else None
                ))

        # Log audit entry for report generation
        self.record_audit(
            user_id=generated_by,
            action="REPORT_GENERATED",
            resource_type="REPORT",
            resource_id=rep_id,
            case_id=case_id,
            target=title,
            result_id=rep_id,
            details=f"Generated {report_type} report: '{title}' ({report_format})"
        )
        return rep_id

    def list_reports(self, case_id: str) -> List[Dict[str, Any]]:
        """List reports belonging to a case."""
        query = "SELECT * FROM reports WHERE case_id = %s ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                return cur.fetchall()

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific report by ID."""
        query = "SELECT * FROM reports WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (report_id,))
                return cur.fetchone()

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
        target: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        source_ref: Optional[str] = None,
        result_id: Optional[str] = None,
    ) -> str:
        """Record an immutable, court-admissible audit log linked to an investigator and case."""
        log_id = str(uuid.uuid4())
        query = """
        INSERT INTO audit_logs (
            id, user_id, action, resource_type, resource_id, case_id,
            status, details, ip_address, timestamp, created_at, username,
            target, old_value, new_value, source_ref, result_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(6), %s, %s, %s, %s, %s, %s);
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    log_id, user_id, action, resource_type, resource_id, case_id,
                    status, details, ip_address, username or user_id,
                    target, old_value, new_value, source_ref, result_id
                ))
        return log_id

    def log_audit(
        self,
        case_id: str,
        action: str,
        username: str = "investigator",
        details: str = "",
        target: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        source_ref: Optional[str] = None,
        result_id: Optional[str] = None,
    ) -> str:
        """Convenience alias to record an audit log for a case with extended audit metadata."""
        return self.record_audit(
            user_id="u-002",
            action=action,
            case_id=case_id,
            resource_type="CASE",
            resource_id=case_id,
            details=details,
            username=username,
            target=target,
            old_value=old_value,
            new_value=new_value,
            source_ref=source_ref,
            result_id=result_id,
        )

    def list_audit_logs(
        self,
        case_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve append-oriented audit history, optionally filtered by case and action."""
        clauses = []
        params = []
        if case_id:
            clauses.append("case_id = %s")
            params.append(case_id)
        if action:
            clauses.append("action = %s")
            params.append(action)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"SELECT * FROM audit_logs {where_sql} ORDER BY timestamp DESC, created_at DESC LIMIT %s;"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.fetchall()

    def get_audit_log(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific immutable audit event by ID."""
        query = "SELECT * FROM audit_logs WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (audit_id,))
                return cur.fetchone()


    # ----------------------------------------------------------------------- #
    # 10. FEEDBACK & HUMAN-IN-THE-LOOP (HITL) DOMAIN MODEL
    # ----------------------------------------------------------------------- #
    def record_feedback(
        self,
        case_id: str,
        feedback_type: str,
        target_id: str,
        action: str,
        notes: str = "",
        user_id: Optional[str] = None,
        original_ai_result: Optional[str] = None,
        corrected_value: Optional[str] = None,
        reason: Optional[str] = None,
        source_ref: Optional[str] = None,
        correction_status: str = "ACCEPTED",
        investigator_id: Optional[str] = None,
    ) -> str:
        """
        Persist investigator feedback and human corrections on AI predictions/alerts.
        Never overwrites original result: preserves BOTH original AI output and human correction.
        """
        fb_id = str(uuid.uuid4())
        a_val = action.upper()
        if a_val not in ("ACCEPTED", "DISMISSED", "FLAGGED", "CONFIRMED"):
            a_val = "DISMISSED"

        actual_user = investigator_id or user_id or "investigator"

        # Log an immutable audit entry
        audit_id = self.record_audit(
            user_id=actual_user,
            action="CORRECTION_SUBMITTED" if corrected_value else "FEEDBACK_RECORDED",
            resource_type="FEEDBACK",
            resource_id=fb_id,
            case_id=case_id,
            target=target_id,
            old_value=original_ai_result,
            new_value=corrected_value,
            source_ref=source_ref,
            result_id=fb_id,
            details=f"Human feedback ({a_val}) on {target_id}: {reason or notes or 'No reason provided'}"
        )

        query = """
        INSERT INTO feedback (
            id, case_id, feedback_type, target_id, action, notes, user_id,
            original_ai_result, corrected_value, reason, source_ref, correction_status, audit_id, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    fb_id, case_id, feedback_type, target_id, a_val, notes, actual_user,
                    original_ai_result, corrected_value, reason, source_ref, correction_status, audit_id
                ))
        return fb_id

    def record_human_correction(
        self,
        case_id: str,
        target_id: str,
        original_ai_result: str,
        corrected_value: str,
        reason: str,
        source_ref: Optional[str] = None,
        feedback_type: str = "HUMAN_CORRECTION",
        user_id: str = "investigator",
        investigator_id: Optional[str] = None,
    ) -> str:
        """
        Dedicated Human-in-the-Loop correction helper.
        Maintains both original AI output and investigator correction with justification.
        """
        return self.record_feedback(
            case_id=case_id,
            feedback_type=feedback_type,
            target_id=target_id,
            action="ACCEPTED",
            notes=reason,
            user_id=investigator_id or user_id,
            original_ai_result=original_ai_result,
            corrected_value=corrected_value,
            reason=reason,
            source_ref=source_ref,
            correction_status="ACCEPTED"
        )

    def list_feedback(self, case_id: str, feedback_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List human feedback and corrections recorded for a case."""
        if feedback_type:
            query = "SELECT * FROM feedback WHERE case_id = %s AND feedback_type = %s ORDER BY created_at DESC;"
            params = (case_id, feedback_type)
        else:
            query = "SELECT * FROM feedback WHERE case_id = %s ORDER BY created_at DESC;"
            params = (case_id,)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def get_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific human feedback record by ID."""
        query = "SELECT * FROM feedback WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (feedback_id,))
                return cur.fetchone()


    def get_active_corrections(self, case_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve active accepted corrections indexed by target_id.
        Used by Graph, Analysis, and Report generators to apply investigator truth.
        """
        query = """
        SELECT * FROM feedback
        WHERE case_id = %s AND corrected_value IS NOT NULL AND action IN ('ACCEPTED', 'CONFIRMED')
        ORDER BY created_at ASC;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (case_id,))
                rows = cur.fetchall()
                # Latest correction wins if multiple exist for same target
                return {r["target_id"]: r for r in rows}

    # ----------------------------------------------------------------------- #
    # 11. INVESTIGATION ACTION WORKFLOWS (INTERNAL PROTOTYPES)
    # ----------------------------------------------------------------------- #
    def create_investigation_action(
        self,
        case_id: str,
        action_type: str,
        target_entity: str,
        reason: str,
        target_entity_type: Optional[str] = None,
        related_evidence: Optional[str] = None,
        investigator_id: str = "investigator",
        notes: Optional[str] = None,
    ) -> str:
        """
        Create an internal investigation action workflow request (e.g. Lookout Request,
        Account Freeze, Mark for Review, Escalate Case).
        Enforces required context/reason and records an audit trail.
        NOTE: These are INTERNAL PROTOTYPE WORKFLOWS and do not dispatch external enforcement actions.
        """
        if not reason or not reason.strip():
            raise ValueError("An explicit reason/context is strictly required for creating an investigation action.")

        valid_types = {
            "LOOKOUT_REQUEST", "ACCOUNT_FREEZE_REQUEST", "MARK_FOR_REVIEW",
            "ESCALATE_CASE", "SURVEILLANCE_REQUEST", "SUBPOENA_REQUEST"
        }
        normalized_type = action_type.upper().replace(" ", "_")
        if normalized_type not in valid_types:
            # Allow custom but normalize
            normalized_type = action_type.strip().upper()

        action_id = str(uuid.uuid4())
        audit_id = self.record_audit(
            user_id=investigator_id,
            action="ACTION_CREATED",
            resource_type="INVESTIGATION_ACTION",
            resource_id=action_id,
            case_id=case_id,
            target=target_entity,
            source_ref=related_evidence,
            result_id=action_id,
            details=f"Created {normalized_type} for '{target_entity}': {reason}"
        )

        query = """
        INSERT INTO investigation_actions (
            id, case_id, action_type, target_entity, target_entity_type,
            reason, status, related_evidence, investigator_id, audit_id, notes, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, 'PENDING_APPROVAL', %s, %s, %s, %s, NOW(), NOW());
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    action_id, case_id, normalized_type, target_entity,
                    target_entity_type, reason, related_evidence, investigator_id,
                    audit_id, notes
                ))
        return action_id

    def list_investigation_actions(
        self,
        case_id: str,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List investigation action workflows recorded for a case."""
        clauses = ["case_id = %s"]
        params = [case_id]
        if status:
            clauses.append("status = %s")
            params.append(status.upper())
        if action_type:
            clauses.append("action_type = %s")
            params.append(action_type.upper())

        where_sql = "WHERE " + " AND ".join(clauses)
        query = f"SELECT * FROM investigation_actions {where_sql} ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.fetchall()

    def get_investigation_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific investigation action record by ID."""
        query = "SELECT * FROM investigation_actions WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (action_id,))
                return cur.fetchone()


    def update_investigation_action_status(
        self,
        action_id: str,
        status: str,
        notes: Optional[str] = None,
        investigator_id: str = "investigator"
    ) -> bool:
        """Update an action's review status (e.g. APPROVED, REJECTED, COMPLETED) with audit tracking."""
        query_fetch = "SELECT * FROM investigation_actions WHERE id = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_fetch, (action_id,))
                existing = cur.fetchone()

        if not existing:
            return False

        old_status = existing["status"]
        new_status = status.upper()

        query_update = """
        UPDATE investigation_actions
        SET status = %s, notes = COALESCE(%s, notes), updated_at = NOW()
        WHERE id = %s;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_update, (new_status, notes, action_id))

        self.record_audit(
            user_id=investigator_id,
            action="ACTION_STATUS_UPDATED",
            resource_type="INVESTIGATION_ACTION",
            resource_id=action_id,
            case_id=existing["case_id"],
            target=existing["target_entity"],
            old_value=old_status,
            new_value=new_status,
            result_id=action_id,
            details=f"Action '{existing['action_type']}' on '{existing['target_entity']}' changed: {old_status} -> {new_status}. {notes or ''}"
        )
        return True

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
            edge_props = {}
            if e.get("properties"):
                try:
                    edge_props = json.loads(e["properties"]) if isinstance(e["properties"], str) else e["properties"]
                except Exception:
                    edge_props = {"raw": e["properties"]}

            modality = str(edge_props.get("modality") or ("PREDICTED" if e.get("predicted") else "OBSERVED")).upper()
            acceptance = str(edge_props.get("acceptance_status") or edge_props.get("acceptance") or ("PROPOSED" if e.get("predicted") else "CONFIRMED")).upper()
            provenance = edge_props.get("provenance", {})
            src_file = provenance.get("source_file") or edge_props.get("source_file") or edge_props.get("evidence_id") or ""
            quote = provenance.get("verbatim_quote") or edge_props.get("quote") or edge_props.get("evidence_quote") or ""

            edge_obj = {
                "source": src,
                "target": tgt,
                "properties": {
                    "id": e["id"],
                    "db_id": e["id"],
                    "label": rel,
                    "type": rel,
                    "confidence": float(e.get("confidence", 1.0)),
                    "predicted": bool(e.get("predicted", 0)),
                    "modality": modality,
                    "acceptance": acceptance,
                    "provenance": provenance,
                    "source_file": src_file,
                    "quote": quote,
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
        net.initialize(params={"network_name": case_title, "case_id": case_id})
        return net

    # ----------------------------------------------------------------------- #
    # 9. MICROSOFT GRAPHRAG INVESTIGATION RETRIEVAL & Q&A
    # ----------------------------------------------------------------------- #
    def query_case_graphrag(
        self,
        case_id: str,
        query: str,
        mode: str = "local",
        community_level: int = 0,
        response_type: str = "Forensic Investigation Briefing",
    ) -> Dict[str, Any]:
        """Query Microsoft GraphRAG for unstructured evidence understanding and Q&A."""
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id)
        return rag.query(query, mode=mode, community_level=community_level, response_type=response_type)

    def get_case_graphrag_stats(self, case_id: str) -> Dict[str, int]:
        """Return counts of indexed GraphRAG artifacts for a case."""
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id)
        return rag.get_indexed_stats()

    def correlate_case_graphrag_with_neo4j(self, case_id: str) -> Dict[str, Any]:
        """Correlate unstructured evidence entities with Neo4j operational graph."""
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        from storage.graphrag_crimenet_boundary import GraphRAGCrimeNetBoundary
        rag = CrimeNetGraphRAG(case_id=case_id)
        driver = GraphRAGCrimeNetBoundary.get_neo4j_driver()
        return rag.correlate_with_neo4j(neo4j_driver=driver)

    # ----------------------------------------------------------------------- #
    # 11. ENTITY INTELLIGENCE AGGREGATION  (Entity Dossier data bundle)
    # ----------------------------------------------------------------------- #
    def get_entity_intelligence(self, entity_id: str, case_id: str = "") -> Dict[str, Any]:
        """Aggregate ALL intelligence about one entity for the Entity Dossier panel.

        Combines:
          - Identity & Properties
          - Neo4j operational graph relationships
          - Case information & cross-case links
          - Evidence documents & source files
          - Forensic anomaly alerts (Isolation Forest)
          - Network analytics (Communities, Centrality, Roles)
          - GraphRAG local context (Narrative retrieval & community reports)
          - Human-in-the-Loop (HITL) active corrections
          - Potential AI-predicted links & hypotheses

        Returns a dict with keys:
          entity, properties, relationships, related_nodes,
          alerts, timeline, evidence, case, linked_cases, analysis,
          community, graphrag_ctx, neo4j_relationships,
          human_corrections, potential_links
        """
        result: Dict[str, Any] = {
            "entity": None,
            "properties": {},
            "relationships": [],
            "related_nodes": {},
            "alerts": [],
            "timeline": [],
            "evidence": [],
            "case": None,
            "linked_cases": [],
            "analysis": None,
            "community": None,
            "graphrag_ctx": None,
            "neo4j_relationships": [],
            "human_corrections": [],
            "potential_links": [],
        }
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Flexible Entity Resolution (by id or exact/case-insensitive name)
                    ent = None
                    if case_id:
                        cur.execute(
                            "SELECT * FROM investigation_entities WHERE (id = %s OR name = %s) AND case_id = %s LIMIT 1;",
                            (entity_id, entity_id, case_id)
                        )
                        ent = cur.fetchone()

                    if not ent:
                        cur.execute(
                            "SELECT * FROM investigation_entities WHERE id = %s OR name = %s LIMIT 1;",
                            (entity_id, entity_id)
                        )
                        ent = cur.fetchone()

                    if not ent and entity_id:
                        # Fallback: search by partial name
                        cur.execute(
                            "SELECT * FROM investigation_entities WHERE LOWER(name) LIKE %s LIMIT 1;",
                            (f"%{str(entity_id).lower()}%",)
                        )
                        ent = cur.fetchone()

                    if not ent:
                        return result

                    result["entity"] = ent
                    if not case_id and ent.get("case_id"):
                        case_id = ent["case_id"]

                    actual_entity_id = ent["id"]
                    entity_name = ent.get("name", "")

                    try:
                        result["properties"] = json.loads(ent["properties"]) if ent.get("properties") and isinstance(ent["properties"], str) else (ent.get("properties") or {})
                    except Exception:
                        result["properties"] = {}

                    # 2. Case Information & Cross-Case Links
                    if case_id:
                        cur.execute("SELECT * FROM cases WHERE id = %s LIMIT 1;", (case_id,))
                        result["case"] = cur.fetchone()

                    if entity_name:
                        cur.execute("""
                            SELECT c.id, c.case_number, c.title, c.crime_type, c.status, c.priority, c.incident_date, c.location
                            FROM cases c
                            INNER JOIN investigation_entities ie ON ie.case_id = c.id
                            WHERE ie.name = %s AND (c.id != %s OR %s IS NULL);
                        """, (entity_name, case_id or "", case_id or ""))
                        result["linked_cases"] = cur.fetchall()

                    # 3. Relationships from MySQL
                    cur.execute("""
                        SELECT er.*,
                               src.name AS source_name, src.entity_type AS source_type,
                               tgt.name AS target_name, tgt.entity_type AS target_type
                        FROM entity_relationships er
                        LEFT JOIN investigation_entities src ON er.source_entity_id = src.id
                        LEFT JOIN investigation_entities tgt ON er.target_entity_id = tgt.id
                        WHERE (er.case_id = %s OR %s IS NULL OR %s = '')
                          AND (er.source_entity_id = %s OR er.target_entity_id = %s)
                        ORDER BY er.confidence DESC, er.created_at DESC;
                    """, (case_id, case_id, case_id, actual_entity_id, actual_entity_id))
                    rels = cur.fetchall()
                    parsed_rels = []
                    potential_links = []
                    for r in rels:
                        rp = {}
                        try:
                            rp = json.loads(r["properties"]) if r.get("properties") and isinstance(r["properties"], str) else (r.get("properties") or {})
                        except Exception:
                            rp = {}
                        r["_props"] = rp
                        mod = str(rp.get("modality") or ("PREDICTED" if r.get("predicted") else "OBSERVED")).upper()
                        r["_modality"] = mod
                        parsed_rels.append(r)

                        if r.get("predicted") or mod in ("PREDICTED", "INFERRED"):
                            potential_links.append({
                                "source_id": r["source_entity_id"],
                                "target_id": r["target_entity_id"],
                                "source_name": r.get("source_name") or r["source_entity_id"],
                                "target_name": r.get("target_name") or r["target_entity_id"],
                                "relationship_type": r.get("relationship_type") or "POTENTIAL_LINK",
                                "confidence": float(r.get("confidence") or 0.65),
                                "algorithm": rp.get("algorithm", "Graph Topology Heuristic"),
                                "modality": mod,
                                "quote": rp.get("quote") or rp.get("verbatim_quote") or "",
                                "source_file": rp.get("source_file") or "",
                            })

                    result["relationships"] = parsed_rels
                    result["potential_links"] = potential_links

                    # 4. Related Node Profiles
                    neighbour_ids = set()
                    for r in parsed_rels:
                        neighbour_ids.add(r["source_entity_id"])
                        neighbour_ids.add(r["target_entity_id"])
                    neighbour_ids.discard(actual_entity_id)
                    if neighbour_ids:
                        placeholders = ",".join(["%s"] * len(neighbour_ids))
                        cur.execute(
                            f"SELECT id, name, entity_type FROM investigation_entities WHERE id IN ({placeholders});",
                            list(neighbour_ids)
                        )
                        for row in cur.fetchall():
                            result["related_nodes"][row["id"]] = {"name": row["name"], "type": row["entity_type"]}

                    # 5. Alerts referencing this entity
                    cur.execute("""
                        SELECT * FROM alerts
                        WHERE (case_id = %s OR %s IS NULL OR %s = '')
                          AND (LOWER(subject) LIKE %s OR LOWER(related_entities) LIKE %s)
                        ORDER BY created_at DESC LIMIT 20;
                    """, (case_id, case_id, case_id, f"%{entity_name.lower()}%", f"%{entity_name.lower()}%"))
                    result["alerts"] = cur.fetchall()

                    # 6. Timeline events
                    cur.execute("""
                        SELECT * FROM timeline_events
                        WHERE (case_id = %s OR %s IS NULL OR %s = '')
                          AND (primary_entity_id = %s OR secondary_entity_id = %s
                               OR LOWER(title) LIKE %s OR LOWER(description) LIKE %s)
                        ORDER BY timestamp ASC LIMIT 50;
                    """, (case_id, case_id, case_id, actual_entity_id, actual_entity_id,
                          f"%{entity_name.lower()}%", f"%{entity_name.lower()}%"))
                    result["timeline"] = cur.fetchall()

                    # 7. Evidence
                    if case_id:
                        cur.execute(
                            "SELECT id, title, evidence_type, filename, source_ref, collected_at, sha256_hash FROM evidence WHERE case_id = %s ORDER BY collected_at DESC;",
                            (case_id,)
                        )
                        result["evidence"] = cur.fetchall()

                    # 8. Analysis & Community Detection Metrics
                    if case_id:
                        cur.execute(
                            "SELECT * FROM analysis_results WHERE case_id = %s ORDER BY created_at DESC LIMIT 1;",
                            (case_id,)
                        )
                        ar = cur.fetchone()
                        if ar:
                            nm = {}
                            try:
                                nm = json.loads(ar["node_metrics"]) if ar.get("node_metrics") and isinstance(ar["node_metrics"], str) else (ar.get("node_metrics") or {})
                            except Exception:
                                nm = {}
                            ar["_node_metrics"] = nm
                            entity_metrics = nm.get(actual_entity_id) or nm.get(entity_name) or {}
                            ar["_entity_metrics"] = entity_metrics
                            result["community"] = entity_metrics.get("community")
                        result["analysis"] = ar

                    # 9. Human-in-the-Loop Corrections
                    try:
                        cur.execute(
                            """SELECT * FROM feedback
                               WHERE case_id = %s AND corrected_value IS NOT NULL AND action IN ('ACCEPTED', 'CONFIRMED')
                               ORDER BY created_at ASC;""",
                            (case_id,)
                        )
                        rows = cur.fetchall()
                        ent_corr = []
                        ename_l = entity_name.lower()
                        eid_l = actual_entity_id.lower()
                        for c in rows:
                            tid = str(c.get("target_id") or "")
                            orig = str(c.get("original_ai_result") or "").lower()
                            corr = str(c.get("corrected_value") or "").lower()
                            notes = str(c.get("notes") or "").lower()
                            reason = str(c.get("reason") or "").lower()
                            if (
                                tid in (actual_entity_id, entity_name)
                                or ename_l in tid.lower()
                                or eid_l in tid.lower()
                                or ename_l in orig
                                or ename_l in corr
                                or ename_l in notes
                                or ename_l in reason
                            ):
                                ent_corr.append(c)
                        result["human_corrections"] = ent_corr
                    except Exception:
                        result["human_corrections"] = []

            # 10. Query Neo4j Operational Graph
            try:
                from storage.graphrag_crimenet_boundary import GraphRAGCrimeNetBoundary
                driver = GraphRAGCrimeNetBoundary.get_neo4j_driver()
                if driver:
                    with driver.session() as session:
                        cypher = """
                        MATCH (e:Entity)-[r]-(target:Entity)
                        WHERE (e.id = $eid OR e.name = $name)
                        RETURN e.name as source_name, e.id as source_id, type(r) as rel_type,
                               target.name as target_name, target.id as target_id,
                               target.entity_type as target_type, properties(r) as props
                        LIMIT 50;
                        """
                        records = session.run(cypher, eid=actual_entity_id, name=entity_name).data()
                        result["neo4j_relationships"] = records
            except Exception as n_err:
                import logging
                logging.getLogger("CrimeNet.DataService").debug("Neo4j query deferred in get_entity_intelligence: %s", n_err)

            # 11. GraphRAG Local Context
            if case_id and entity_name:
                try:
                    from storage.crimenet_graphrag import CrimeNetGraphRAG
                    rag = CrimeNetGraphRAG(case_id=case_id)
                    rag_res = rag.query(query_text=entity_name, mode="local")
                    if rag_res and rag_res.get("grounded"):
                        result["graphrag_ctx"] = rag_res
                except Exception as r_err:
                    import logging
                    logging.getLogger("CrimeNet.DataService").debug("GraphRAG context deferred in get_entity_intelligence: %s", r_err)

        except Exception as exc:
            import logging
            logging.getLogger("CrimeNet.DataService").warning(
                "get_entity_intelligence(%s, %s) failed: %s", entity_id, case_id, exc
            )
        return result

    # ----------------------------------------------------------------------- #
    # 12. RELATIONSHIP INTELLIGENCE  (Edge Investigation Panel data bundle)
    # ----------------------------------------------------------------------- #
    def get_relationship_intelligence(self, edge_id: str, case_id: str = "") -> Dict[str, Any]:
        """Fetch full provenance bundle for a single relationship edge."""
        result: Dict[str, Any] = {
            "relationship": None, "properties": {}, "source_entity": None,
            "target_entity": None, "evidence": [], "modality": "OBSERVED",
            "acceptance": "CONFIRMED", "provenance": {}, "case": None,
            "date": "", "time": "", "duration": "", "originating_record": "—",
            "extraction_method": "", "confidence": 1.0,
        }
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM entity_relationships WHERE id = %s LIMIT 1;",
                        (edge_id,)
                    )
                    rel = cur.fetchone()

                    # Fallback lookup by source-target pair if edge_id has format 'u_v' or not matched directly
                    if not rel and "-" in edge_id or "_" in edge_id:
                        parts = edge_id.split("-") if "-" in edge_id else edge_id.split("_")
                        if len(parts) >= 2:
                            cur.execute(
                                "SELECT * FROM entity_relationships WHERE (source_entity_id = %s AND target_entity_id = %s) OR (source_entity_id = %s AND target_entity_id = %s) LIMIT 1;",
                                (parts[0], parts[1], parts[1], parts[0])
                            )
                            rel = cur.fetchone()

                    if not rel:
                        return {}

                    result["relationship"] = rel
                    if not case_id and rel.get("case_id"):
                        case_id = rel["case_id"]

                    props = {}
                    try:
                        props = json.loads(rel["properties"]) if rel.get("properties") and isinstance(rel["properties"], str) else (rel.get("properties") or {})
                    except Exception:
                        props = {}
                    result["properties"] = props
                    modality = str(props.get("modality") or ("PREDICTED" if rel.get("predicted") else "OBSERVED")).upper()
                    result["modality"] = modality
                    result["acceptance"] = str(props.get("acceptance_status") or props.get("acceptance") or ("PROPOSED" if rel.get("predicted") else "CONFIRMED")).upper()
                    result["confidence"] = float(rel.get("confidence") or props.get("confidence") or 1.0)

                    prov = props.get("provenance", {})
                    result["provenance"] = prov

                    # Date, time, duration, originating record, extraction method
                    result["source_file"] = prov.get("source_file") or props.get("source_file") or ""
                    result["date"] = prov.get("date") or props.get("date") or str(rel.get("created_at") or "")[:10]
                    result["time"] = prov.get("time") or props.get("time") or str(rel.get("created_at") or "")[11:19]
                    result["duration"] = prov.get("duration") or props.get("duration") or props.get("call_duration") or ""
                    result["originating_record"] = prov.get("originating_record") or props.get("record_id") or props.get("row_id") or ""
                    result["extraction_method"] = prov.get("extraction_method") or (
                        "AI Link Prediction (Graph Topology)" if modality in ("PREDICTED", "INFERRED") else
                        "Direct Telephony Ingestion (CDR)" if "CALL" in str(rel.get("relationship_type", "")).upper() else
                        "Banking Ledger Ingestion (Financial Transaction)" if any(x in str(rel.get("relationship_type", "")).upper() for x in ("TRANS", "WIRE", "BENEF")) else
                        "Forensic NLP / Document Extraction"
                    )

                    # Source & Target entities
                    cur.execute("SELECT * FROM investigation_entities WHERE id = %s LIMIT 1;", (rel["source_entity_id"],))
                    result["source_entity"] = cur.fetchone()
                    cur.execute("SELECT * FROM investigation_entities WHERE id = %s LIMIT 1;", (rel["target_entity_id"],))
                    result["target_entity"] = cur.fetchone()

                    # Supporting evidence matching
                    src_file = prov.get("source_file") or props.get("source_file") or ""
                    ev_id_ref = prov.get("evidence_id") or ""
                    if case_id and (src_file or ev_id_ref):
                        cur.execute(
                            """SELECT id, title, evidence_type, filename, source_ref, content, collected_at, sha256_hash
                               FROM evidence
                               WHERE case_id = %s
                                 AND (filename = %s OR source_ref = %s OR id = %s OR id = %s
                                      OR LOWER(filename) LIKE %s OR LOWER(source_ref) LIKE %s);""",
                            (case_id, src_file, src_file, src_file, ev_id_ref,
                             f"%{src_file.lower()}%" if src_file else "",
                             f"%{src_file.lower()}%" if src_file else "")
                        )
                        result["evidence"] = cur.fetchall()

                    if case_id:
                        cur.execute("SELECT * FROM cases WHERE id = %s LIMIT 1;", (case_id,))
                        result["case"] = cur.fetchone()

        except Exception as exc:
            import logging
            logging.getLogger("CrimeNet.DataService").warning(
                "get_relationship_intelligence(%s, %s) failed: %s", edge_id, case_id, exc
            )
        return result


    # ----------------------------------------------------------------------- #
    # 13. CASE TIMELINE AGGREGATE  (Timeline Panel data bundle)               #
    # ----------------------------------------------------------------------- #
    def get_case_timeline_aggregate(self, case_id: str) -> "List[Dict[str, Any]]":
        """Aggregate ALL case events from every source table into one chronological stream.

        Each returned event dict has normalised keys:
          ts          - datetime (sortable, may be None)
          event_type  - canonical string (EVIDENCE_UPLOADED, ENTITY_DETECTED, ...)
          icon        - display emoji
          title       - short one-line label
          description - fuller explanation (may be empty string)
          severity    - CRITICAL | HIGH | MEDIUM | LOW | INFO
          object_type - EVIDENCE | ENTITY | RELATIONSHIP | ANALYSIS | ALERT |
                        TIMELINE_EVENT | REPORT | AUDIT | FEEDBACK
          object_id   - primary key of the related object (click-to-open)
          meta        - raw DB row dict
          source_ref  - file / table reference string
          actor       - investigator username or "system"
        """
        from datetime import datetime as _dt
        from typing import Optional

        events = []

        def _ts(val):
            if val is None:
                return None
            if isinstance(val, _dt):
                return val
            try:
                return _dt.fromisoformat(str(val).replace("Z", ""))
            except Exception:
                return None

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:

                    # ── 1. Evidence uploaded / extraction completed ────────────────────
                    cur.execute(
                        "SELECT id, title, filename, evidence_type, processing_status, "
                        "extraction_status, collected_by, collected_at, created_at, "
                        "entity_count, relation_count "
                        "FROM evidence WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        ts = _ts(row.get("created_at") or row.get("collected_at"))
                        label = row.get("filename") or row.get("title") or row["id"][:8]
                        events.append({
                            "ts": ts, "event_type": "EVIDENCE_UPLOADED",
                            "icon": "📁", "severity": "INFO",
                            "title": "Evidence uploaded: " + str(label),
                            "description": "Type: " + str(row.get("evidence_type")) + " | Status: " + str(row.get("processing_status")),
                            "object_type": "EVIDENCE", "object_id": row["id"],
                            "source_ref": row.get("filename") or "",
                            "actor": row.get("collected_by") or "system",
                            "meta": row,
                        })
                        if (row.get("extraction_status") or "").lower() == "completed":
                            events.append({
                                "ts": ts, "event_type": "EXTRACTION_COMPLETED",
                                "icon": "⚙️", "severity": "INFO",
                                "title": "Extraction completed: " + str(label),
                                "description": (
                                    str(row.get("entity_count", 0)) + " entities · "
                                    + str(row.get("relation_count", 0)) + " relationships extracted"
                                ),
                                "object_type": "EVIDENCE", "object_id": row["id"],
                                "source_ref": row.get("filename") or "",
                                "actor": "system", "meta": row,
                            })

                    # ── 2. Entities detected ───────────────────────────────────────────
                    cur.execute(
                        "SELECT id, name, entity_type, verified, source_text, created_at "
                        "FROM investigation_entities WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": "ENTITY_DETECTED",
                            "icon": "👤", "severity": "INFO",
                            "title": "Entity detected: " + str(row.get("name")) + " (" + str(row.get("entity_type")) + ")",
                            "description": (row.get("source_text") or "")[:200],
                            "object_type": "ENTITY", "object_id": row["id"],
                            "source_ref": "", "actor": "system", "meta": row,
                        })

                    # ── 3. Relationships / potential links ─────────────────────────────
                    cur.execute(
                        "SELECT er.id, er.relationship_type, er.confidence, er.predicted, "
                        "er.created_at, "
                        "src.name AS source_name, tgt.name AS target_name "
                        "FROM entity_relationships er "
                        "LEFT JOIN investigation_entities src ON er.source_entity_id = src.id "
                        "LEFT JOIN investigation_entities tgt ON er.target_entity_id = tgt.id "
                        "WHERE er.case_id = %s ORDER BY er.created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        is_pred = bool(row.get("predicted"))
                        etype = "POTENTIAL_LINK_GENERATED" if is_pred else "RELATIONSHIP_DETECTED"
                        icon  = "🔮" if is_pred else "🔗"
                        sev   = "MEDIUM" if is_pred else "INFO"
                        src_n = row.get("source_name") or "?"
                        tgt_n = row.get("target_name") or "?"
                        conf  = int(float(row.get("confidence") or 1.0) * 100)
                        desc  = "Confidence: " + str(conf) + "%"
                        if is_pred:
                            desc += " | AI PREDICTED — HYPOTHESIS ONLY"
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": etype, "icon": icon, "severity": sev,
                            "title": src_n + " → [" + str(row.get("relationship_type")) + "] → " + tgt_n,
                            "description": desc,
                            "object_type": "RELATIONSHIP", "object_id": row["id"],
                            "source_ref": "", "actor": "system", "meta": row,
                        })

                    # ── 4. Analysis runs ───────────────────────────────────────────────
                    cur.execute(
                        "SELECT id, task_id, algorithm, summary, executed_by, created_at "
                        "FROM analysis_results WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": "ANALYSIS_RUN",
                            "icon": "📊", "severity": "INFO",
                            "title": "Analysis run: " + str(row.get("algorithm")),
                            "description": (row.get("summary") or "")[:200],
                            "object_type": "ANALYSIS", "object_id": row["id"],
                            "source_ref": row.get("task_id") or "",
                            "actor": row.get("executed_by") or "system", "meta": row,
                        })

                    # ── 5. Anomaly / Alert generated ───────────────────────────────────
                    cur.execute(
                        "SELECT id, alert_type, severity, title, explanation, subject, status, created_at "
                        "FROM alerts WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    _sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
                    for row in cur.fetchall():
                        sev = str(row.get("severity") or "MEDIUM").upper()
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": "ANOMALY_GENERATED",
                            "icon": _sev_icon.get(sev, "🚨"), "severity": sev,
                            "title": "Anomaly: " + str(row.get("title")),
                            "description": (row.get("explanation") or "")[:200],
                            "object_type": "ALERT", "object_id": row["id"],
                            "source_ref": row.get("subject") or "",
                            "actor": "system", "meta": row,
                        })

                    # ── 6. Crime-level timeline events ─────────────────────────────────
                    cur.execute(
                        "SELECT id, event_type, timestamp, title, description, source_ref, "
                        "confidence, location, created_at "
                        "FROM timeline_events WHERE case_id = %s ORDER BY timestamp ASC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        events.append({
                            "ts": _ts(row.get("timestamp") or row.get("created_at")),
                            "event_type": "TIMELINE_EVENT",
                            "icon": "📅", "severity": "INFO",
                            "title": row.get("title") or row.get("event_type") or "Event",
                            "description": (row.get("description") or "")[:200],
                            "object_type": "TIMELINE_EVENT", "object_id": row["id"],
                            "source_ref": row.get("source_ref") or row.get("location") or "",
                            "actor": "system", "meta": row,
                        })

                    # ── 7. Reports generated ───────────────────────────────────────────
                    cur.execute(
                        "SELECT id, title, report_type, generated_by, created_at "
                        "FROM reports WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": "REPORT_GENERATED",
                            "icon": "📄", "severity": "INFO",
                            "title": "Report generated: " + str(row.get("title")),
                            "description": "Type: " + str(row.get("report_type")) + " | Author: " + str(row.get("generated_by")),
                            "object_type": "REPORT", "object_id": row["id"],
                            "source_ref": "",
                            "actor": row.get("generated_by") or "system", "meta": row,
                        })

                    # ── 8. Audit / Investigator actions ───────────────────────────────
                    _audit_map = {
                        "QUERY_SUBMITTED":   ("INVESTIGATOR_QUERY",  "🔍"),
                        "EVIDENCE_VIEWED":   ("INVESTIGATOR_REVIEW", "👁️"),
                        "ALERT_REVIEWED":    ("INVESTIGATOR_REVIEW", "🔎"),
                        "ALERT_DISMISSED":   ("HUMAN_FEEDBACK",      "🗑️"),
                        "EDGE_ACCEPTED":     ("HUMAN_FEEDBACK",      "✅"),
                        "EDGE_REJECTED":     ("HUMAN_FEEDBACK",      "❌"),
                        "CASE_CREATED":      ("INVESTIGATOR_ACTION", "💼"),
                        "CASE_UPDATED":      ("INVESTIGATOR_ACTION", "✏️"),
                        "WORKSPACE_OPENED":  ("INVESTIGATOR_ACTION", "🖥️"),
                        "REPORT_VIEWED":     ("INVESTIGATOR_REVIEW", "📖"),
                    }
                    cur.execute(
                        "SELECT id, action, resource_type, resource_id, username, user_id, "
                        "details, status, timestamp "
                        "FROM audit_logs WHERE case_id = %s ORDER BY timestamp DESC LIMIT 300;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        ak = str(row.get("action") or "").upper()
                        etype2, icon2 = _audit_map.get(ak, ("INVESTIGATOR_ACTION", "🗂️"))
                        events.append({
                            "ts": _ts(row.get("timestamp")),
                            "event_type": etype2, "icon": icon2, "severity": "INFO",
                            "title": str(row.get("action")) + " by " + str(row.get("username") or row.get("user_id") or "investigator"),
                            "description": (row.get("details") or "")[:200],
                            "object_type": "AUDIT",
                            "object_id": row.get("resource_id") or row["id"],
                            "source_ref": row.get("resource_type") or "",
                            "actor": row.get("username") or "investigator", "meta": row,
                        })

                    # ── 9. Human feedback ──────────────────────────────────────────────
                    _fb_icon = {"ACCEPTED": "✅", "DISMISSED": "❌", "FLAGGED": "🚩", "CONFIRMED": "🔒"}
                    cur.execute(
                        "SELECT id, feedback_type, target_id, action, notes, user_id, created_at "
                        "FROM feedback WHERE case_id = %s ORDER BY created_at DESC;",
                        (case_id,)
                    )
                    for row in cur.fetchall():
                        act = str(row.get("action") or "ACCEPTED").upper()
                        events.append({
                            "ts": _ts(row.get("created_at")),
                            "event_type": "HUMAN_FEEDBACK",
                            "icon": _fb_icon.get(act, "💬"), "severity": "INFO",
                            "title": "Human feedback: " + str(row.get("feedback_type")) + " → " + act,
                            "description": (row.get("notes") or ("Target: " + str(row.get("target_id"))))[:200],
                            "object_type": "FEEDBACK", "object_id": row["id"],
                            "source_ref": row.get("target_id") or "",
                            "actor": row.get("user_id") or "investigator", "meta": row,
                        })

        except Exception as exc:
            import logging
            logging.getLogger("CrimeNet.DataService").warning(
                "get_case_timeline_aggregate(%s) failed: %s", case_id, exc
            )

        from datetime import datetime as _dt2
        events.sort(key=lambda e: e["ts"] or _dt2.min)
        return events
