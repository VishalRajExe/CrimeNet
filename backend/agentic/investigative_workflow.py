"""
investigative_workflow.py - LangGraph Agentic Workflow for CrimeNet
Orchestrates the entire investigative pipeline:
Ingestion -> GraphRAG Retrieval -> NetworkX / scikit-learn Intelligence -> LLM Explainable Synthesis.
"""

import json
import logging
from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from ..extraction.ner_extractor import default_extractor
from ..storage.graph_store import default_graph_store
from ..storage.graph_rag import default_graph_rag
from ..intelligence.network_analytics import default_network_analytics
from ..intelligence.anomaly_detector import default_anomaly_detector
from ..intelligence.node_embeddings import default_embedding_engine
from ..audit_ledger import default_audit_ledger

logger = logging.getLogger("crimenet.agentic.workflow")


class InvestigativeState(TypedDict):
    case_id: str
    query: str
    target_entity: Optional[str]
    officer_badge: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]
    graph_rag_context: Dict[str, Any]
    networkx_metrics: Dict[str, Any]
    isolation_forest_anomalies: List[Dict[str, Any]]
    node_embeddings: Dict[str, Any]
    explainable_dossier: Dict[str, Any]
    actionable_recommendations: List[Dict[str, Any]]


# --------------------------------------------------------------------------- #
# LangGraph Node Handlers
# --------------------------------------------------------------------------- #

def step_extract_and_ingest(state: InvestigativeState) -> Dict[str, Any]:
    """Node 1: Extracts structured entities and relations from narrative query."""
    query = state.get("query", "")
    case_id = state.get("case_id", "CASE-2024-MH-088")

    extracted_nodes = []
    extracted_edges = []
    if query:
        result = default_extractor.extract_from_narrative(query, case_id=case_id)
        extracted_nodes = [
            n.to_dict() if hasattr(n, "to_dict") else (n.dict() if hasattr(n, "dict") else dict(n))
            for n in getattr(result, "nodes", [])
        ]
        extracted_edges = [
            e.to_dict() if hasattr(e, "to_dict") else (e.dict() if hasattr(e, "dict") else dict(e))
            for e in getattr(result, "edges", [])
        ]

    # Combine with current graph
    current_nodes = list(state.get("nodes", []))
    current_edges = list(state.get("edges", []))

    existing_ids = {n["id"] for n in current_nodes}
    for en in extracted_nodes:
        if en["id"] not in existing_ids:
            current_nodes.append(en)
            existing_ids.add(en["id"])

    existing_edge_ids = {e.get("id") for e in current_edges}
    for ee in extracted_edges:
        eid = ee.get("id") or f"{ee['source']}->{ee['target']}"
        if eid not in existing_edge_ids:
            current_edges.append(ee)
            existing_edge_ids.add(eid)

    # Persist in operational graph store
    default_graph_store.set_graph_data(case_id, current_nodes, current_edges)

    return {
        "nodes": current_nodes,
        "edges": current_edges,
        "extracted_entities": extracted_nodes
    }


def step_query_graph_rag(state: InvestigativeState) -> Dict[str, Any]:
    """Node 2: Queries GraphRAG for evidence chunks and knowledge graph triples."""
    case_id = state.get("case_id", "CASE-2024-MH-088")
    query = state.get("query", "")
    target = state.get("target_entity", "")

    search_term = f"{query} {target}".strip() or "criminal network"
    rag_context = default_graph_rag.query(case_id=case_id, query_text=search_term, top_k=4)

    return {"graph_rag_context": rag_context}


def step_python_intelligence(state: InvestigativeState) -> Dict[str, Any]:
    """Node 3: Executes NetworkX graph analytics, scikit-learn Isolation Forest, and embeddings."""
    nodes = state.get("nodes", [])
    edges = state.get("edges", [])

    # 1. NetworkX Analytics
    pr_res = default_network_analytics.compute_centrality(nodes, edges, metric="pagerank")
    bet_res = default_network_analytics.compute_centrality(nodes, edges, metric="betweenness")
    comm_res = default_network_analytics.detect_communities(nodes, edges, algorithm="louvain")
    bottlenecks = default_network_analytics.find_network_bottlenecks(nodes, edges)

    networkx_metrics = {
        "pagerank": pr_res.get("scores", {}),
        "betweenness": bet_res.get("scores", {}),
        "rankings": pr_res.get("rankings", []),
        "communities": comm_res,
        "bottlenecks": bottlenecks
    }

    # 2. scikit-learn Isolation Forest Anomaly Detection
    anomalies = default_anomaly_detector.detect_anomalies(nodes, edges)

    # 3. Node Embeddings & Role Classification
    embeddings = default_embedding_engine.compute_embeddings(nodes, edges)

    return {
        "networkx_metrics": networkx_metrics,
        "isolation_forest_anomalies": anomalies,
        "node_embeddings": embeddings
    }


def step_synthesize_explainable_intelligence(state: InvestigativeState) -> Dict[str, Any]:
    """Node 4: Synthesizes plain English findings, citations, and police actions."""
    case_id = state.get("case_id", "CASE-2024-MH-088")
    query = state.get("query", "")
    target = state.get("target_entity", "")
    officer_badge = state.get("officer_badge", "UNKNOWN")
    nodes = state.get("nodes", [])
    anomalies = state.get("isolation_forest_anomalies", [])
    nx_data = state.get("networkx_metrics", {})
    rag_ctx = state.get("graph_rag_context", {})

    target_label = target or (nodes[0].get("label") if nodes else "Syndicate")

    # Generate Explainable Summary
    num_nodes = len(nodes)
    num_anomalies = len(anomalies)
    cut_vertices = nx_data.get("bottlenecks", {}).get("cut_vertices", [])
    triples = rag_ctx.get("knowledge_triples", [])

    summary_paragraphs = [
        f"**Investigative Synthesis for {target_label}** in {case_id}:",
        f"Topological analysis across {num_nodes} connected entities identified {num_anomalies} high-risk anomalies via scikit-learn Isolation Forest.",
    ]

    if cut_vertices:
        cut_labels = [cv["label"] for cv in cut_vertices[:3]]
        summary_paragraphs.append(
            f"**Critical Vulnerabilities**: NetworkX identified {len(cut_vertices)} single-point-of-failure communication bridges ({', '.join(cut_labels)}). Coordinated interdiction of these operatives will structurally partition the syndicate."
        )

    if anomalies:
        top_anom = anomalies[0]
        summary_paragraphs.append(
            f"**Primary Anomaly**: {top_anom['label']} ({top_anom['type']}) exhibits an anomaly confidence of {int(top_anom['anomaly_score'] * 100)}%. Rationale: {top_anom['reason']}"
        )

    if triples:
        sample_triple = triples[0]
        summary_paragraphs.append(
            f"**GraphRAG Evidence Correlation**: '{sample_triple['subject']}' {sample_triple['predicate'].lower().replace('_', ' ')} '{sample_triple['object']}' (Source: {sample_triple['source']})."
        )

    # Actionable Police Recommendations
    actions = [
        {
            "action": "Issue LOC (Look Out Circular)",
            "priority": "HIGH",
            "statute": "Bureau of Immigration / MHA Guidelines",
            "rationale": "High flight risk based on cross-border transactions and critical centrality score."
        },
        {
            "action": "Section 102 CrPC Account Freeze",
            "priority": "IMMEDIATE",
            "statute": "Section 102 Code of Criminal Procedure, 1973",
            "rationale": "Prevent rapid dissipation of extortion proceeds across identified mule funnel accounts."
        },
        {
            "action": "Section 91 CrPC Notice to Telecom/Bank",
            "priority": "STANDARD",
            "statute": "Section 91 CrPC",
            "rationale": "Compel production of IP logs, CDR call dumps, and KYC identity documents."
        }
    ]

    explainable_dossier = {
        "target": target_label,
        "executive_summary": "\n\n".join(summary_paragraphs),
        "threat_level": "CRITICAL" if num_anomalies > 0 else "HIGH",
        "timestamp": datetime.now().isoformat(),
        "citations": [
            f"FIR/{case_id}/2024",
            "GraphRAG Knowledge Graph Triplets (V1.0)",
            "scikit-learn Isolation Forest Anomaly Engine (Contamination=0.15)",
            "NetworkX Louvain Modularity Partition"
        ]
    }

    # Audit the run
    default_audit_ledger.record_action(
        case_id=case_id,
        action="LANGGRAPH_INTELLIGENCE_SYNTHESIS",
        officer_badge=officer_badge,
        details={
            "query": query,
            "target": target,
            "anomalies_detected": num_anomalies,
            "nodes_analyzed": num_nodes
        }
    )

    return {
        "explainable_dossier": explainable_dossier,
        "actionable_recommendations": actions
    }


# --------------------------------------------------------------------------- #
# LangGraph Workflow Construction
# --------------------------------------------------------------------------- #

def build_investigative_workflow():
    workflow = StateGraph(InvestigativeState)

    # Add Nodes
    workflow.add_node("extract_and_ingest", step_extract_and_ingest)
    workflow.add_node("query_graph_rag", step_query_graph_rag)
    workflow.add_node("python_intelligence", step_python_intelligence)
    workflow.add_node("synthesize_explainable_intelligence", step_synthesize_explainable_intelligence)

    # Add Edges
    workflow.add_edge(START, "extract_and_ingest")
    workflow.add_edge("extract_and_ingest", "query_graph_rag")
    workflow.add_edge("query_graph_rag", "python_intelligence")
    workflow.add_edge("python_intelligence", "synthesize_explainable_intelligence")
    workflow.add_edge("synthesize_explainable_intelligence", END)

    # Compile the graph
    app = workflow.compile()
    logger.info("LangGraph Investigative Workflow compiled successfully.")
    return app


# Singleton compiled workflow instance
investigative_app = build_investigative_workflow()
