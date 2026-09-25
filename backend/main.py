"""
CrimeNet AI - Unified REST API Gateway
Exposes all RAG, NER extraction, graph analytics, and agentic workflows to the React frontend.
Fulfills all contracts defined in FRONTEND_PLAN_AND_TIMELINE.md.
"""

import os
import shutil
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import BASE_DIR, UPLOADS_DIR, CORS_ORIGINS, HOST, PORT
from .security import api_access_middleware, require_matching_badge
from .rag.document_loader import DocumentLoader
from .rag.chunker import DocumentChunker
from .rag.vector_store import default_vector_store
from .extraction.ner_extractor import NarrativeExtractor, GraphNode, GraphEdge, default_extractor
from .agents.dossier_agent import default_dossier_agent
from .agents.financial_agent import default_financial_agent
from .agents.feedback_agent import default_feedback_agent
from .audit_ledger import default_audit_ledger

# Architecture Plan Components
from .storage.relational_store import default_relational_store
from .storage.graph_store import default_graph_store
from .storage.graph_rag import default_graph_rag
from .intelligence.network_analytics import default_network_analytics
from .intelligence.anomaly_detector import default_anomaly_detector
from .intelligence.node_embeddings import default_embedding_engine
from .agentic.investigative_workflow import investigative_app
from .agentic.gemini_agent import default_gemini_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crimenet.api")

app = FastAPI(
    title="CrimeNet AI API",
    description="Explainable Intelligence & Criminal Network Analysis Platform for Indian Law Enforcement",
    version="1.0.0"
)

# When the frontend is built, the same FastAPI process can serve the React
# bundle. This keeps the Render prototype to one web service.
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


def custom_openapi():
    """Document both required headers so Swagger UI has an Authorize button."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
        "OfficerBadge": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Officer-Badge",
        },
    }

    for path, path_item in schema.get("paths", {}).items():
        if not path.startswith("/api/"):
            continue
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation["security"] = [
                    {"ApiKeyAuth": [], "OfficerBadge": []}
                ]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

# Authenticate API requests before route handlers run. CORS is added after the
# auth middleware so preflight requests and auth errors still receive the
# correct browser CORS headers.
@app.middleware("http")
async def enforce_api_access(request: Request, call_next):
    return await api_access_middleware(request, call_next)


# Only explicitly configured local origins are accepted. Never use a wildcard
# origin together with credentialed browser requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-API-Key", "X-Officer-Badge"],
)


# --------------------------------------------------------------------------- #
# In-Memory Case & Graph State
# --------------------------------------------------------------------------- #
class CaseStore:
    def __init__(self):
        self.cases: Dict[str, Dict[str, Any]] = {
            "CASE-2024-MH-088": {
                "id": "CASE-2024-MH-088",
                "title": "Operation Golden Web",
                "type": "Organized Cyber Extortion",
                "status": "CRITICAL",
                "suspects": 8,
                "volume": "₹2.4 Cr",
                "police_station": "Cyber Crime Cell, Bandra Kurla Complex",
                "officer": "Inspector S. Deshmukh (Badge #4409)",
                "created_at": "2024-03-10"
            },
            "CASE-2024-DL-012": {
                "id": "CASE-2024-DL-012",
                "title": "NCR Hawala Network",
                "type": "Financial Money Laundering",
                "status": "ONGOING",
                "suspects": 14,
                "volume": "₹18.6 Cr",
                "police_station": "Special Cell, Lodhi Colony",
                "officer": "ACP R. K. Mishra",
                "created_at": "2024-02-15"
            },
            "CASE-2023-GJ-901": {
                "id": "CASE-2023-GJ-901",
                "title": "Surat Cargo Smuggling Cell",
                "type": "Narcotics & Logistics",
                "status": "COLD",
                "suspects": 5,
                "volume": "₹4.1 Cr",
                "police_station": "Crime Branch, Surat",
                "officer": "Inspector V. Patel",
                "created_at": "2023-11-20"
            }
        }
        self.graphs: Dict[str, Dict[str, Any]] = {}
        self.seed_default_graph()

    def seed_default_graph(self):
        """Seeds default investigation graph for immediate exploration."""
        cid = "CASE-2024-MH-088"
        nodes = [
            GraphNode(id="E1", label="Vikram Malhotra", type="PERSON", threat_level="CRITICAL", threat_score=0.95),
            GraphNode(id="E2", label="9876543210", type="PHONE", threat_level="HIGH", threat_score=0.82),
            GraphNode(id="E3", label="vikram@okhdfcbank", type="ACCOUNT", threat_level="CRITICAL", threat_score=0.91),
            GraphNode(id="E4", label="SBI-Mule-40912", type="ACCOUNT", threat_level="CRITICAL", threat_score=0.88),
            GraphNode(id="E5", label="Apex Global Logistics Ltd", type="ORGANIZATION", threat_level="HIGH", threat_score=0.79),
            GraphNode(id="E6", label="BVI Offshore Vault 99", type="ORGANIZATION", threat_level="CRITICAL", threat_score=0.96),
            GraphNode(id="E7", label="Surat Cargo Yard", type="LOCATION", threat_level="MEDIUM", threat_score=0.45),
            GraphNode(id="E8", label="MH04AB9901 (Fortuner)", type="VEHICLE", threat_level="HIGH", threat_score=0.72),
        ]
        edges = [
            GraphEdge(id="R1", source="E1", target="E2", type="USES_PHONE", label="Primary Contact"),
            GraphEdge(id="R2", source="E1", target="E3", type="OPERATES_ACCOUNT", label="Registered UPI"),
            GraphEdge(id="R3", source="E3", target="E4", type="TRANSFERRED_FUNDS", label="₹15,00,000 (UPI)", amount="₹15,00,000"),
            GraphEdge(id="R4", source="E4", target="E5", type="TRANSFERRED_FUNDS", label="₹42,00,000 (RTGS)", amount="₹42,00,000"),
            GraphEdge(id="R5", source="E5", target="E6", type="WIRE_TRANSFER", label="₹85,00,000 (Offshore)", amount="₹85,00,000"),
            GraphEdge(id="R6", source="E1", target="E8", type="USES_VEHICLE", label="Registered Transport"),
            GraphEdge(id="R7", source="E8", target="E7", type="SPOTTED_AT", label="Toll Plaza Footage"),
        ]
        self.graphs[cid] = {"nodes": {n.id: n for n in nodes}, "edges": edges}


case_store = CaseStore()
chunker = DocumentChunker()


# --------------------------------------------------------------------------- #
# Request & Response Schemas
# --------------------------------------------------------------------------- #
class NarrativeRequest(BaseModel):
    case_id: str = "CASE-2024-MH-088"
    narrative: str
    officer_badge: Optional[str] = None


class FeedbackRequest(BaseModel):
    case_id: str = "CASE-2024-MH-088"
    feedback_prompt: str
    officer_badge: Optional[str] = None


class ActionDispatchRequest(BaseModel):
    action_id: str
    entity_id: str
    case_id: str = "CASE-2024-MH-088"
    officer_badge: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class FollowMoneyRequest(BaseModel):
    seed_node_id: str
    case_id: str = "CASE-2024-MH-088"
    max_hops: int = 3


class NewCaseRequest(BaseModel):
    title: str
    type: str
    police_station: str
    officer: str
    officer_badge: Optional[str] = None
    initial_facts: Optional[str] = None


class AnalyzeRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    functionId: str
    algoId: str


class AnomaliesRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class GraphRAGRequest(BaseModel):
    case_id: str = "CASE-2024-MH-088"
    query: str
    top_k: int = 5


class AgenticWorkflowRequest(BaseModel):
    case_id: str = "CASE-2024-MH-088"
    query: str
    target_entity: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None


class GeminiChatRequest(BaseModel):
    message: str
    case_id: str = "CASE-2024-MH-088"
    history: Optional[List[Dict[str, str]]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None


# --------------------------------------------------------------------------- #
# API Routes
# --------------------------------------------------------------------------- #

def _health_payload():
    return {
        "status": "online",
        "service": "CrimeNet AI Unified API",
        "version": "1.0.0",
        "jurisdiction": "Indian Law Enforcement Edition"
    }


@app.get("/health")
def health_check():
    """Public liveness endpoint for Render and local monitoring."""
    return _health_payload()


@app.get("/")
def root_check():
    """Serve the built React prototype at the service root when available."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return _health_payload()


# 1. Cases Endpoints
@app.get("/api/cases")
def list_cases():
    return list(case_store.cases.values())


@app.post("/api/cases")
def create_case(req: NewCaseRequest, request: Request):
    officer_badge = require_matching_badge(request, req.officer_badge)
    cid = f"CASE-{len(case_store.cases) + 1:03d}"
    new_case = {
        "id": cid,
        "title": req.title,
        "type": req.type,
        "status": "CRITICAL",
        "suspects": 0,
        "volume": "₹0",
        "police_station": req.police_station,
        "officer": req.officer,
        "created_at": "Today"
    }
    case_store.cases[cid] = new_case
    case_store.graphs[cid] = {"nodes": {}, "edges": []}

    default_audit_ledger.record_action(
        action="REGISTER_CASE",
        case_id=cid,
        officer_badge=officer_badge,
        details={"title": req.title, "type": req.type}
    )

    if req.initial_facts:
        res = default_extractor.extract_from_narrative(req.initial_facts, case_id=cid)
        for n in res.nodes:
            case_store.graphs[cid]["nodes"][n.id] = n
        case_store.graphs[cid]["edges"].extend(res.edges)
        new_case["suspects"] = len(res.nodes)

    return new_case


# 2. Graph Canvas Endpoint
@app.get("/api/graph/{case_id}")
def get_graph(case_id: str):
    if case_id not in case_store.graphs:
        case_store.graphs[case_id] = {"nodes": {}, "edges": []}

    c_graph = case_store.graphs[case_id]
    return {
        "nodes": [n.to_dict() for n in c_graph["nodes"].values()],
        "edges": [e.to_dict() for e in c_graph["edges"]],
    }


# 3. Narrative Ingestion Endpoint (Text-to-Graph)
@app.post("/api/investigate/narrative")
def investigate_narrative(req: NarrativeRequest, request: Request):
    officer_badge = require_matching_badge(request, req.officer_badge)
    if req.case_id not in case_store.graphs:
        case_store.graphs[req.case_id] = {"nodes": {}, "edges": []}

    # Extract entities and relationships
    result = default_extractor.extract_from_narrative(req.narrative, case_id=req.case_id)

    # Merge into active case graph
    c_graph = case_store.graphs[req.case_id]
    for n in result.nodes:
        c_graph["nodes"][n.id] = n
    c_graph["edges"].extend(result.edges)

    # Index into GraphRAG triples
    try:
        default_graph_rag.index_evidence_text(
            case_id=req.case_id,
            text=req.narrative,
            source_doc="Investigator Narrative",
            chunk_id=f"narrative_{datetime.now().strftime('%H%M%S')}"
        )
    except Exception as e:
        logger.warning("GraphRAG indexing notice: %s", e)

    # Log to immutable audit ledger
    default_audit_ledger.record_action(
        action="NARRATIVE_INGESTION",
        case_id=req.case_id,
        officer_badge=officer_badge,
        details={
            "raw_length": len(req.narrative),
            "extracted_nodes": len(result.nodes),
            "extracted_edges": len(result.edges),
            "entities": [n.label for n in result.nodes]
        }
    )

    return {
        "status": "success",
        "extractedCount": len(result.nodes),
        "graph": {
            "nodes": [n.to_dict() for n in c_graph["nodes"].values()],
            "edges": [e.to_dict() for e in c_graph["edges"]],
        },
        "tokens": [t.normalized_value for t in result.tokens]
    }


# 4. Evidence Document Upload Endpoint (RAG Ingestion)
@app.post("/api/investigate/upload")
async def upload_evidence(
    request: Request,
    case_id: str = Form("CASE-2024-MH-088"),
    officer_badge: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    authenticated_badge = require_matching_badge(request, officer_badge)
    upload_path = UPLOADS_DIR / f"{case_id}_{file.filename}"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse and chunk document
    doc = DocumentLoader.load_file(str(upload_path), case_id=case_id)
    doc_chunks = chunker.chunk_document(doc)
    added_count = default_vector_store.add_chunks(doc_chunks, case_id=case_id)

    # Index chunks into GraphRAG knowledge triples
    for chunk in doc_chunks:
        try:
            default_graph_rag.index_evidence_text(
                case_id=case_id,
                text=chunk.text,
                source_doc=file.filename,
                chunk_id=chunk.chunk_id
            )
        except Exception:
            pass

    # Save to Relational Database
    try:
        default_relational_store.add_evidence({
            "id": f"EVID-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "case_id": case_id,
            "filename": file.filename,
            "file_path": str(upload_path),
            "file_size": os.path.getsize(upload_path),
            "extracted_entities_count": 0
        })
    except Exception as e:
        logger.warning("Relational evidence save notice: %s", e)

    # Extract entities from document text
    extraction = default_extractor.extract_from_narrative(doc.full_text[:5000], case_id=case_id)
    if case_id not in case_store.graphs:
        case_store.graphs[case_id] = {"nodes": {}, "edges": []}

    c_graph = case_store.graphs[case_id]
    for n in extraction.nodes:
        c_graph["nodes"][n.id] = n
    c_graph["edges"].extend(extraction.edges)

    # Audit log entry
    default_audit_ledger.record_action(
        action="DOCUMENT_UPLOAD",
        case_id=case_id,
        officer_badge=authenticated_badge,
        details={
            "filename": file.filename,
            "chunks_indexed": added_count,
            "entities_found": len(extraction.nodes)
        }
    )

    return {
        "status": "indexed",
        "filename": file.filename,
        "chunksIndexed": added_count,
        "extractedEntities": len(extraction.nodes),
        "graph": {
            "nodes": [n.to_dict() for n in c_graph["nodes"].values()],
            "edges": [e.to_dict() for e in c_graph["edges"]],
        }
    }


# 5. Entity Dossier Endpoint (Agentic Synthesis with RAG Citations)
@app.get("/api/entity/{node_id:path}/dossier")
def get_entity_dossier(node_id: str, case_id: str = Query("CASE-2024-MH-088")):
    if case_id not in case_store.graphs:
        case_store.graphs[case_id] = {"nodes": {}, "edges": []}

    c_graph = case_store.graphs[case_id]
    node = c_graph["nodes"].get(node_id)
    if not node:
        # Dynamically register node for intelligence synthesis
        clean_label = node_id.replace("_", " ").strip()
        lower_id = node_id.lower()
        if any(w in lower_id for w in ["org", "ltd", "corp", "logistics", "infotech", "enterprises", "vault"]):
            inferred_type = "organization"
        elif any(w in lower_id for w in ["bank", "acc", "mule", "upi", "@"]):
            inferred_type = "account"
        elif any(w in lower_id for w in ["veh", "car", "fortuner", "truck"]):
            inferred_type = "vehicle"
        elif any(w in lower_id for w in ["loc", "yard", "plaza", "delhi", "mumbai", "surat"]):
            inferred_type = "location"
        elif any(c.isdigit() for c in node_id) and len([c for c in node_id if c.isdigit()]) >= 10:
            inferred_type = "phone"
        else:
            inferred_type = "person"

        threat = "CRITICAL" if any(w in lower_id for w in ["malhotra", "sheikh", "yadav", "alshehri", "mule", "vault", "apex"]) else "HIGH"
        score = 0.92 if threat == "CRITICAL" else 0.75

        node = GraphNode(
            id=node_id,
            label=clean_label,
            type=inferred_type,
            threat_level=threat,
            threat_score=score,
            metadata={"source": "Dynamic Network Inspection"}
        )
        c_graph["nodes"][node_id] = node

    connected_edges = [e for e in c_graph["edges"] if e.source == node_id or e.target == node_id]
    dossier = default_dossier_agent.generate_dossier(
        node=node,
        connected_edges=connected_edges,
        all_nodes_dict=c_graph["nodes"],
        case_id=case_id
    )

    return dossier.to_dict()


# 6. Follow the Money 3-Hop Tracing Endpoint
@app.post("/api/analytics/follow-money")
def follow_the_money(req: FollowMoneyRequest):
    if req.case_id not in case_store.graphs:
        case_store.graphs[req.case_id] = {"nodes": {}, "edges": []}

    c_graph = case_store.graphs[req.case_id]
    if req.seed_node_id not in c_graph["nodes"]:
        clean_label = req.seed_node_id.replace("_", " ").strip()
        c_graph["nodes"][req.seed_node_id] = GraphNode(
            id=req.seed_node_id,
            label=clean_label,
            type="account" if "acc" in req.seed_node_id.lower() or "@" in req.seed_node_id else "person",
            threat_level="CRITICAL",
            threat_score=0.91
        )
    res = default_financial_agent.trace_money(
        seed_node_id=req.seed_node_id,
        nodes_dict=c_graph["nodes"],
        edges=c_graph["edges"],
        max_hops=req.max_hops
    )
    return res.to_dict()


# 7. Human-in-the-Loop @feedback Endpoint
@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    officer_badge = require_matching_badge(request, req.officer_badge)
    if req.case_id not in case_store.graphs:
        raise HTTPException(status_code=404, detail="Case not found")

    c_graph = case_store.graphs[req.case_id]
    res = default_feedback_agent.process_feedback(
        feedback_text=req.feedback_prompt,
        nodes_dict=c_graph["nodes"],
        edges=c_graph["edges"],
        case_id=req.case_id,
        officer_badge=officer_badge
    )
    return res.to_dict()


# 8. Threat Alerts Endpoint
@app.get("/api/alerts")
def get_threat_alerts(case_id: str = Query("CASE-2024-MH-088")):
    return [
        {
            "id": "ALT-101",
            "severity": "CRITICAL",
            "title": "Rapid Mule Layering Transfer Flagged",
            "timestamp": "10 mins ago",
            "description": "₹15,00,000 dispersed from vikram@okhdfcbank to SBI-Mule-40912, followed by immediate wire to Apex Global Logistics.",
            "targetNodeId": "E4",
            "actionLabel": "Freeze Mule Account",
            "actionId": "FREEZE"
        },
        {
            "id": "ALT-102",
            "severity": "HIGH",
            "title": "Border Transit Geofence Hit",
            "timestamp": "42 mins ago",
            "description": "Vehicle MH04AB9901 registered to Vikram Malhotra passed through Vapi Toll Plaza towards international container yard.",
            "targetNodeId": "E8",
            "actionLabel": "Dispatch Highway Patrol",
            "actionId": "ANPR_ALERT"
        },
        {
            "id": "ALT-103",
            "severity": "HIGH",
            "title": "Cross-Border Offshore Routing",
            "timestamp": "2 hours ago",
            "description": "Apex Global Logistics initiated ₹85,00,000 wire transfer to BVI Offshore Vault 99.",
            "targetNodeId": "E6",
            "actionLabel": "Requisition FIU-IND / Interpol Red Notice",
            "actionId": "FIU_NOTICE"
        }
    ]


# 9. Action Dispatch Endpoint (LOC, Freeze Account, Summons)
@app.post("/api/actions/dispatch")
def dispatch_action(req: ActionDispatchRequest, request: Request):
    officer_badge = require_matching_badge(request, req.officer_badge)
    entry = default_audit_ledger.record_action(
        action=f"ACTION_{req.action_id}",
        case_id=req.case_id,
        officer_badge=officer_badge,
        target_entity=req.entity_id,
        details={"parameters": req.parameters}
    )

    action_names = {
        "LOC": "Lookout Circular (LOC) transmitted to Bureau of Immigration",
        "FREEZE": "Account Freeze Order requisitioned to Bank Nodal Officer under Sec 102 CrPC",
        "SUMMONS": "Notice of Appearance issued under Section 35(3) BNSS",
        "ANPR_ALERT": "FASTag vehicle intercept broadcast dispatched to State Police Highway Patrol"
    }

    return {
        "status": "dispatched",
        "actionId": req.action_id,
        "entityId": req.entity_id,
        "title": action_names.get(req.action_id, "Police Action Executed"),
        "auditId": entry.audit_id,
        "timestamp": entry.timestamp,
        "message": f"{action_names.get(req.action_id, 'Action executed')} and permanently logged in audit trail."
    }


# 10. Chronological Timeline Endpoint
@app.get("/api/cases/{case_id}/timeline")
def get_case_timeline(case_id: str):
    return [
        {"time": "2024-03-10 09:15 AM", "type": "FIR", "title": "FIR Registered", "desc": "Victim reports extortion call demanding ₹15,00,000 under threat of violence."},
        {"time": "2024-03-10 11:30 AM", "type": "TRANSACTION", "title": "Primary UPI Transfer", "desc": "₹15,00,000 transferred via UPI to vikram@okhdfcbank."},
        {"time": "2024-03-10 11:42 AM", "type": "TRANSACTION", "title": "Mule Account Funneling", "desc": "₹15,00,000 forwarded to SBI-Mule-40912 in Surat."},
        {"time": "2024-03-11 02:20 PM", "type": "VEHICLE", "title": "Toll Plaza Camera Hit", "desc": "Fortuner MH04AB9901 spotted at Vapi Toll Plaza heading to Surat Cargo Yard."},
        {"time": "2024-03-12 04:00 PM", "type": "WIRE", "title": "Offshore Layering Wire", "desc": "Apex Logistics initiates ₹85,00,000 wire to BVI Offshore Vault."}
    ]


# 11. Immutable Audit Ledger Endpoint
@app.get("/api/cases/{case_id}/audit")
def get_audit_trail(case_id: str, limit: int = 25):
    return default_audit_ledger.get_recent_entries(case_id=case_id, limit=limit)


# 12. Prosecutor Briefing Report Endpoint (PDF / Markdown export)
@app.get("/api/cases/{case_id}/report")
def get_case_report(case_id: str):
    c_info = case_store.cases.get(case_id, {"title": "General Investigation", "type": "Unknown"})
    c_graph = case_store.graphs.get(case_id, {"nodes": {}, "edges": []})
    audits = default_audit_ledger.get_recent_entries(case_id=case_id, limit=10)

    report_markdown = f"""# CONFIDENTIAL // PROSECUTOR INTELLIGENCE BRIEFING
**Case Title**: {c_info.get('title')} ({case_id})
**Crime Category**: {c_info.get('type')}
**Jurisdiction**: {c_info.get('police_station', 'Cyber Crime Cell')}
**Investigating Officer**: {c_info.get('officer', 'IO In-charge')}

---

## 1. Executive Summary
This intelligence briefing integrates multi-source evidence including First Information Reports (FIRs),
Call Detail Records (CDRs), Banking Statements, and Automated Number Plate Recognition (ANPR) camera captures.
CrimeNet AI topological analysis has identified an active criminal syndicate consisting of **{len(c_graph['nodes'])} mapped entities**
and **{len(c_graph['edges'])} verified relationship links**.

## 2. Identified Key Operatives
"""
    for n in c_graph["nodes"].values():
        if n.threat_level in ["CRITICAL", "HIGH"]:
            report_markdown += f"- **{n.label}** ({n.type}) — Threat Level: `{n.threat_level}` (Score: {n.threat_score})\n"

    report_markdown += """
## 3. Financial Layering & Follow-the-Money Trail
Analysis of fund dispersal indicates structured layering operations:
1. Initial extorted capital collected via UPI handles.
2. Immediate intra-hour dispersal to regional mule accounts.
3. Commercial wire routing via logistics shells to offshore jurisdictions.

## 4. Dispatched Actions & Judicial Compliance Log
Every automated lead has undergone investigator review and has been logged with cryptographic SHA-256 hash verification:
"""
    for a in audits:
        report_markdown += f"- `[{a.get('timestamp')}]` **{a.get('action')}** by `{a.get('officer_badge')}`: {a.get('details', {})}\n"

    return {
        "case_id": case_id,
        "title": c_info.get("title"),
        "reportMarkdown": report_markdown,
        "entitiesCount": len(c_graph["nodes"]),
        "edgesCount": len(c_graph["edges"]),
        "generatedAt": "Live"
    }


# --------------------------------------------------------------------------- #
# 13. Python Intelligence Layer (NetworkX, scikit-learn, Embeddings)
# --------------------------------------------------------------------------- #
@app.post("/api/intelligence/analyze")
def run_python_analysis(req: AnalyzeRequest):
    """
    Executes Python graph analytics:
    - Community Detection (Louvain, Modularity, Label Propagation)
    - Social Influence (PageRank, Betweenness, Closeness, Degree Centrality)
    - Link Prediction (Jaccard, Adamic-Adar, Resource Allocation)
    - Node Embeddings (Node2Vec random walks & 2D PCA projection)
    """
    func_id = req.functionId
    algo_id = req.algoId

    # 1. Social Influence / Centrality
    if func_id == "social_influence":
        res = default_network_analytics.compute_centrality(req.nodes, req.edges, metric=algo_id)
        return {
            "type": "influence",
            "title": algo_id.replace("_", " ").title(),
            "scores": res["scores"],
            "data": res["rankings"]
        }

    # 2. Community Detection
    elif func_id == "community":
        res = default_network_analytics.detect_communities(req.nodes, req.edges, algorithm=algo_id)
        return {
            "type": "community",
            "title": algo_id.replace("_", " ").title(),
            "groups": res["groups"],
            "communityOf": res["communityOf"],
            "data": res
        }

    # 3. Link Prediction
    elif func_id == "link_prediction":
        preds = default_network_analytics.predict_links(req.nodes, req.edges, method=algo_id)
        return {
            "type": "links",
            "title": algo_id.replace("_", " ").title(),
            "data": preds
        }

    # 4. Node Embedding
    elif func_id == "node_embedding":
        embed_res = default_embedding_engine.compute_embeddings(req.nodes, req.edges, method=algo_id)
        return {
            "type": "embedding",
            "title": f"{algo_id.upper()} (2D Projection)",
            "roles": embed_res["roles"],
            "embeddings": embed_res["embeddings"],
            "data": [
                {
                    "id": nid,
                    "label": req.nodes[i].get("label", nid) if i < len(req.nodes) else nid,
                    "type": req.nodes[i].get("type", "UNKNOWN") if i < len(req.nodes) else "UNKNOWN",
                    "role": rinfo["role"],
                    "coords": [rinfo["x"], rinfo["y"]]
                }
                for i, (nid, rinfo) in enumerate(embed_res["roles"].items())
            ][:20]
        }

    raise HTTPException(status_code=400, detail=f"Unsupported analysis function: {func_id}")


# 14. scikit-learn Isolation Forest Anomaly Detection
@app.post("/api/intelligence/anomalies")
def get_isolation_forest_anomalies(req: AnomaliesRequest):
    """
    Runs scikit-learn Isolation Forest on graph nodes and edges to isolate
    mule funnel accounts, hub outliers, and unusual transaction bursts.
    """
    anomalies = default_anomaly_detector.detect_anomalies(req.nodes, req.edges)
    bottlenecks = default_network_analytics.find_network_bottlenecks(req.nodes, req.edges)
    return {
        "status": "success",
        "count": len(anomalies),
        "anomalies": anomalies,
        "bottlenecks": bottlenecks
    }


# 15. GraphRAG Knowledge Query Endpoint
@app.post("/api/intelligence/graphrag/query")
def query_graph_rag(req: GraphRAGRequest):
    """
    Executes hybrid GraphRAG query combining semantic text chunk search
    with multi-hop Knowledge Graph triples.
    """
    result = default_graph_rag.query(case_id=req.case_id, query_text=req.query, top_k=req.top_k)
    return result


# 16. LangGraph Agentic Investigative Workflow
@app.post("/api/intelligence/investigate")
def run_investigative_workflow(req: AgenticWorkflowRequest, request: Request):
    """
    Runs the complete LangGraph StateGraph pipeline:
    Extract/Ingest -> GraphRAG -> NetworkX/scikit-learn Intelligence -> LLM Explainable Synthesis.
    """
    officer_badge = require_matching_badge(request, None)

    # Grab nodes/edges from active case or request payload
    active_nodes = req.nodes
    active_edges = req.edges
    if not active_nodes:
        c_graph = case_store.graphs.get(req.case_id, {"nodes": {}, "edges": []})
        active_nodes = [n.to_dict() for n in c_graph["nodes"].values()]
        active_edges = [e.to_dict() for e in c_graph["edges"]]

    initial_state = {
        "case_id": req.case_id,
        "query": req.query,
        "target_entity": req.target_entity,
        "officer_badge": officer_badge,
        "nodes": active_nodes or [],
        "edges": active_edges or [],
        "extracted_entities": [],
        "graph_rag_context": {},
        "networkx_metrics": {},
        "isolation_forest_anomalies": [],
        "node_embeddings": {},
        "explainable_dossier": {},
        "actionable_recommendations": []
    }

    try:
        final_state = investigative_app.invoke(initial_state)

        # Sync back to in-memory case graph
        if req.case_id in case_store.graphs:
            c_graph = case_store.graphs[req.case_id]
            for n in final_state.get("nodes", []):
                nid = n.get("id")
                if nid and nid not in c_graph["nodes"]:
                    c_graph["nodes"][nid] = GraphNode(
                        id=str(nid),
                        label=str(n.get("label", nid)),
                        type=str(n.get("type", "UNKNOWN")),
                        threat_level=str(n.get("threat_level", n.get("threatLevel", "MEDIUM"))),
                        threat_score=float(n.get("threat_score", n.get("threatScore", 0.5))),
                        metadata=dict(n.get("metadata", {}))
                    )
            for e in final_state.get("edges", []):
                meta = dict(e.get("metadata", {}))
                if "timestamp" in e:
                    meta["timestamp"] = e["timestamp"]
                c_graph["edges"].append(GraphEdge(
                    id=str(e.get("id", f"{e.get('source')}->{e.get('target')}")),
                    source=str(e.get("source")),
                    target=str(e.get("target")),
                    type=str(e.get("type", "CONNECTED")),
                    label=str(e.get("label", e.get("type", "CONNECTED"))),
                    amount=e.get("amount"),
                    metadata=meta
                ))

        return {
            "status": "success",
            "case_id": req.case_id,
            "dossier": final_state.get("explainable_dossier", {}),
            "recommendations": final_state.get("actionable_recommendations", []),
            "anomalies": final_state.get("isolation_forest_anomalies", []),
            "networkx_metrics": final_state.get("networkx_metrics", {}),
            "graph_rag": final_state.get("graph_rag_context", {}),
            "nodesCount": len(final_state.get("nodes", [])),
            "edgesCount": len(final_state.get("edges", []))
        }
    except Exception as e:
        logger.error("LangGraph investigation pipeline error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 17. Relational Database Endpoints
@app.get("/api/database/cases")
def get_db_cases():
    return default_relational_store.list_cases()


@app.get("/api/database/evidence/{case_id}")
def get_db_evidence(case_id: str):
    return default_relational_store.list_evidence(case_id)


# 18. Google Gemini AI Agent Chat Endpoint
@app.post("/api/gemini/chat")
def gemini_chat(req: GeminiChatRequest):
    """
    Real-time interactive chat with CrimeNet Gemini AI Agent.
    Grounds LLM in operational graph, scikit-learn Isolation Forest, and GraphRAG.
    Automatically ingests new entities into network graph if suspect narrative is detected.
    """
    active_nodes = req.nodes
    active_edges = req.edges
    if not active_nodes and req.case_id in case_store.graphs:
        c_graph = case_store.graphs[req.case_id]
        active_nodes = [n.to_dict() for n in c_graph["nodes"].values()]
        active_edges = [e.to_dict() for e in c_graph["edges"]]

    res = default_gemini_agent.chat(
        message=req.message,
        case_id=req.case_id,
        history=req.history,
        nodes=active_nodes or [],
        edges=active_edges or []
    )

    # If new nodes/edges were extracted, update in-memory graph
    if res.get("newNodes") and req.case_id in case_store.graphs:
        c_graph = case_store.graphs[req.case_id]
        for n in res["newNodes"]:
            nid = n.get("id")
            if nid and nid not in c_graph["nodes"]:
                c_graph["nodes"][nid] = GraphNode(
                    id=str(nid),
                    label=str(n.get("label", nid)),
                    type=str(n.get("type", "UNKNOWN")),
                    threat_level=str(n.get("threat_level", n.get("threatLevel", "HIGH"))),
                    threat_score=float(n.get("threat_score", n.get("threatScore", 0.75))),
                    metadata=dict(n.get("metadata", {}))
                )
        for e in res.get("newEdges", []):
            c_graph["edges"].append(GraphEdge(
                id=str(e.get("id", f"{e.get('source')}->{e.get('target')}")),
                source=str(e.get("source")),
                target=str(e.get("target")),
                type=str(e.get("type", "CONNECTED")),
                label=str(e.get("label", e.get("type", "CONNECTED"))),
                amount=e.get("amount"),
                metadata=dict(e.get("metadata", {}))
            ))

    return res


# Serve the React build from the same process when frontend/dist exists.
# Unknown non-API paths fall back to index.html for client-side navigation.
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")

        root = FRONTEND_DIST.resolve()
        candidate = (FRONTEND_DIST / full_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise HTTPException(status_code=404, detail="File not found")

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
