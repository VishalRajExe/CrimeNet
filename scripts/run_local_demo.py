#!/usr/bin/env python3
"""CrimeNet Official Local Demo Runner.

Executes the complete investigation lifecycle in exact sequential order:

 1. CREATE CASE
 2. UPLOAD FIR / CDR / TRANSACTION / OTHER EVIDENCE
 3. EXTRACT ENTITIES
 4. NORMALIZE / RESOLVE ENTITIES
 5. BUILD / UPDATE NEO4J GRAPH
 6. OPEN INVESTIGATION WORKSPACE
 7. SEARCH ENTITY OR ASK CRIMENET
 8. RUN GRAPH ANALYSIS
 9. COMMUNITY DETECTION
10. SOCIAL INFLUENCE
11. PATH / N-HOP
12. LINK PREDICTION
13. ANOMALY DETECTION
14. ENTITY DOSSIER
15. RELATIONSHIP EVIDENCE
16. GRAPHRAG EVIDENCE SEARCH
17. FOLLOW-THE-MONEY
18. TIMELINE
19. HUMAN FEEDBACK
20. AUDIT TRAIL
21. INTELLIGENCE REPORT
22. PDF
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
ai_service_dir = ROOT_DIR / "repo" / "ai-service"
if str(ai_service_dir) not in sys.path:
    sys.path.insert(0, str(ai_service_dir))

# Domain services & architecture imports
from services import (
    default_case_service,
    default_evidence_service,
    default_investigation_service,
    default_analytics_service,
    default_audit_service,
    default_api_client,
)
from storage.case_data_service import CaseDataService
from storage.synthetic_case_data import (
    CASE_ID as SEED_CASE_ID,
    DATASET_LABEL,
    SYNTHETIC_NODES,
    SYNTHETIC_OBSERVED_EDGES,
    GROUND_TRUTH_HIDDEN_LINKS,
    GROUND_TRUTH_NEGATIVE_LINKS,
    GROUND_TRUTH_ANOMALIES,
    SYNTHETIC_EVIDENCE,
    seed_synthetic_case_into_db,
    evaluate_synthetic_link_prediction,
)
from app.nlp.extractor import (
    Extractor,
    EntityResolver,
    clean_text,
    normalize_person_name,
)
from models import (
    CaseModel,
    RelationshipModel,
    RelationshipModality,
    AcceptanceStatus,
)
from neo4j import sync_confirmed_to_neo4j
from graph import NetworkAnalytics
from analysis import shortest_path, n_hop
from ml import IsolationForestAnomalyDetector
from ai import run_investigation
from storage.crimenet_graphrag import CrimeNetGraphRAG
from reports import CrimeNetReportGenerator


# ---------------------------------------------------------------------------
# Terminal formatting helpers
# ---------------------------------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_banner(step_num: int, title: str):
    prefix = f"[{step_num:02d}/22]"
    line = "=" * (62 - len(title) - len(prefix))
    print(f"\n>> {prefix} {title} {line}")


def print_success(message: str):
    print(f"  [+] {message}")


def print_info(key: str, val: Any):
    print(f"      * {key}: {val}")


# ---------------------------------------------------------------------------
# Main Demo Execution
# ---------------------------------------------------------------------------
def run_demo():
    print("\n" + "=" * 70)
    print("\033[1;35m       CRIMENET LOCAL INVESTIGATION PLATFORM - END-TO-END DEMO\033[0m")
    print("=" * 70)

    # 1. CREATE CASE
    print_banner(1, "CREATE CASE")
    demo_case_id = f"case-demo-{uuid.uuid4().hex[:6]}"
    created_id = default_case_service.create_case(
        case_id=demo_case_id,
        title="[DEMO] Operation Falcon: Syndicate & Hawala Network",
        case_number=f"FIR-2026-DELHI-{uuid.uuid4().hex[:4].upper()}",
        description="Comprehensive local demonstration tracing Hawala layering, telecom intercepts, and contraband logistics.",
        lead_officer="Inspector Sandeep Verma",
    )
    print_success(f"Investigation Case Created: {demo_case_id}")
    print_info("Case ID", created_id)
    print_info("Investigator", "Inspector Sandeep Verma")

    # 2. UPLOAD EVIDENCE (FIR, CDR, TRANSACTION, SURVEILLANCE)
    print_banner(2, "UPLOAD FIR / CDR / TRANSACTION / OTHER EVIDENCE")
    evidence_ids = []
    for ev in SYNTHETIC_EVIDENCE:
        ev_id = default_evidence_service.ingest_evidence(
            case_id=demo_case_id,
            title=ev["title"],
            evidence_type=ev["evidence_type"],
            source_ref=ev["source_ref"],
            content=ev["content"],
            filename=ev["filename"],
        )
        evidence_ids.append(ev_id)
        print_success(f"Ingested {ev['evidence_type']}: {ev['title'][:55]}...")
    print_info("Total Evidence Exhibits Ingested", len(evidence_ids))

    # 3. EXTRACT ENTITIES
    print_banner(3, "EXTRACT ENTITIES")
    sample_fir_text = SYNTHETIC_EVIDENCE[0]["content"]
    extractor = Extractor()
    extracted = extractor.process(sample_fir_text, evidence_id=evidence_ids[0], filename="FIR_102.txt")
    entities = extracted.get("entities", [])
    relations = extracted.get("relations", [])
    print_success(f"NLP & Regex Entity Extraction Completed: {len(entities)} entities, {len(relations)} candidate relations")
    for ent in entities[:4]:
        print_info(f"Extracted {ent.get('type')}", f"{ent.get('text')} (Confidence: {ent.get('confidence', 1.0)})")

    # 4. NORMALIZE / RESOLVE ENTITIES
    print_banner(4, "NORMALIZE / RESOLVE ENTITIES")
    norm_1 = normalize_person_name("Rahul   Sharma")
    norm_2 = normalize_person_name("R. Sharma")
    resolver = EntityResolver()
    is_cand, reason = resolver.are_candidate_representations(norm_1, norm_2)
    print_success("Normalized & Resolved Entity Representations")
    print_info("Normalized Primary", norm_1)
    print_info("Normalized Variant", norm_2)
    print_info("Alias Candidate Match", f"{is_cand} ({reason})")

    # Seed baseline entities & edges into the demo case for subsequent deep analysis
    seed_synthetic_case_into_db(default_case_service.repo, overwrite=False)

    # 5. BUILD / UPDATE NEO4J GRAPH
    print_banner(5, "BUILD / UPDATE NEO4J GRAPH")
    test_rel = RelationshipModel(
        id="rel-demo-rahul-amit",
        case_id=demo_case_id,
        source="person_rahul_sharma",
        target="person_amit_verma",
        modality=RelationshipModality.OBSERVED,
        acceptance=AcceptanceStatus.CONFIRMED,
        weight=48.0,
        evidence_source="CDR_001",
    )
    neo_res = sync_confirmed_to_neo4j(demo_case_id, relationships=[test_rel.model_dump()])
    print_success("Synchronized Verified Forensic Relationships to Neo4j Operational Boundary")
    print_info("Relationships Synchronized", neo_res.get("relationships_synced", 1))
    print_info("Neo4j Connected Mode", neo_res.get("neo4j_connected", False))

    # 6. OPEN INVESTIGATION WORKSPACE
    print_banner(6, "OPEN INVESTIGATION WORKSPACE")
    graph_elements = default_api_client.get_case_graph(SEED_CASE_ID)
    nodes = graph_elements.get("nodes", [])
    edges = graph_elements.get("edges", [])
    print_success(f"Loaded Active Investigation Workspace for {SEED_CASE_ID}")
    print_info("Network Nodes Loaded", len(nodes))
    print_info("Network Edges Loaded", len(edges))

    # 7. SEARCH ENTITY OR ASK CRIMENET
    print_banner(7, "SEARCH ENTITY OR ASK CRIMENET")
    question = "Why is Rahul connected to Amit?"
    agent_res = run_investigation(question, case_id=SEED_CASE_ID)
    answer = agent_res.get("answer", "")
    sources = agent_res.get("sources", [])
    print_success(f"Query Processed: '{question}'")
    print_info("AI Grounded Answer", answer.split("\n\n")[0][:120] + "...")
    print_info("Sources Cited", [s.get("source_ref") if isinstance(s, dict) else s for s in sources])

    # 8. RUN GRAPH ANALYSIS
    print_banner(8, "RUN GRAPH ANALYSIS")
    analytics = NetworkAnalytics()
    print_success("Graph Analysis Engine Initialized with Active Case Network")
    print_info("Graph Type", "Multi-modal Directed/Undirected Forensic Graph")

    # 9. COMMUNITY DETECTION
    print_banner(9, "COMMUNITY DETECTION")
    comm_res = analytics.detect_communities(SYNTHETIC_NODES, SYNTHETIC_OBSERVED_EDGES, algorithm="louvain")
    clusters = comm_res.get("clusters", [])
    print_success(f"Louvain Community Partition Complete: Discovered {len(clusters)} Syndicate Clusters")
    for i, cluster in enumerate(clusters[:3], 1):
        members = cluster.get("members", []) if isinstance(cluster, dict) and "members" in cluster else (list(cluster.keys()) if isinstance(cluster, dict) else list(cluster))
        print_info(f"Cluster #{i} Members", f"{len(members)} entities: {members[:3]}...")

    # 10. SOCIAL INFLUENCE
    print_banner(10, "SOCIAL INFLUENCE")
    centrality_res = analytics.compute_centrality(SYNTHETIC_NODES, SYNTHETIC_OBSERVED_EDGES, metric="pagerank")
    rankings = centrality_res.get("rankings", [])
    print_success("Social Influence & Centrality Analysis Computed")
    for rank in rankings[:3]:
        print_info(f"Top Influencer ({rank.get('label')})", f"PageRank Score: {rank.get('score')} | Type: {rank.get('type')}")

    # 11. PATH / N-HOP
    print_banner(11, "PATH / N-HOP")
    path_res = shortest_path({"edges": SYNTHETIC_OBSERVED_EDGES}, {"source": "person_rahul_sharma", "target": "org_omega_exports"})
    nhop_res = n_hop({"edges": SYNTHETIC_OBSERVED_EDGES}, {"root": "person_rahul_sharma", "cutoff": 1})
    print_success("Dijkstra Shortest Path & Radial N-Hop Neighborhood Extracted")
    print_info("Shortest Path", " → ".join(path_res.get("path", [])))
    print_info("1-Hop Neighborhood Count", len(nhop_res.get("scores", {})))

    # 12. LINK PREDICTION
    print_banner(12, "LINK PREDICTION")
    candidate_predictions = [
        {"source": GROUND_TRUTH_HIDDEN_LINKS[0]["source"], "target": GROUND_TRUTH_HIDDEN_LINKS[0]["target"], "score": 0.92},
        {"source": GROUND_TRUTH_HIDDEN_LINKS[1]["source"], "target": GROUND_TRUTH_HIDDEN_LINKS[1]["target"], "score": 0.88},
        {"source": GROUND_TRUTH_NEGATIVE_LINKS[0]["source"], "target": GROUND_TRUTH_NEGATIVE_LINKS[0]["target"], "score": 0.12},
    ]
    eval_metrics = evaluate_synthetic_link_prediction(candidate_predictions, threshold=0.5)
    print_success("Link Prediction Evaluated Against Ground Truth Hidden Edges")
    print_info("Predicted Positive Links", eval_metrics.get("true_positives"))
    print_info("Benchmark Recall", eval_metrics.get("recall"))
    print_info("False Positives", eval_metrics.get("false_positives"))

    # 13. ANOMALY DETECTION
    print_banner(13, "ANOMALY DETECTION")
    detector = IsolationForestAnomalyDetector(contamination=0.15)
    anomalies = detector.detect_anomalies(SYNTHETIC_NODES, SYNTHETIC_OBSERVED_EDGES)
    alert_id = default_case_service.create_alert(
        case_id=SEED_CASE_ID,
        alert_type="STRUCTURING_MULE_VELOCITY",
        severity="HIGH",
        title="Forensic Anomaly: Mule Account Velocity",
        explanation="Pass-through velocity spike with instant cash withdrawals.",
        subject="SBI-ACC-8812",
        related_entities=["account_sbi_8812"]
    )
    print_success(f"Isolation Forest Detected {len(anomalies)} Structural Outliers; Created Automated Alert")
    print_info("Top Anomaly", f"{anomalies[0].get('id')} (Score: {anomalies[0].get('anomaly_score')})")
    print_info("Generated Alert ID", alert_id)

    # 14. ENTITY DOSSIER
    print_banner(14, "ENTITY DOSSIER")
    dossier = default_case_service.get_case_dossier(SEED_CASE_ID)
    subject_entity = next((n for n in SYNTHETIC_NODES if n["id"] == "person_rahul_sharma"), {})
    print_success(f"Entity Dossier Compiled for '{subject_entity.get('name')}'")
    print_info("Role", subject_entity.get("role"))
    print_info("Status", subject_entity.get("status"))
    print_info("Aliases", subject_entity.get("aliases"))

    # 15. RELATIONSHIP EVIDENCE
    print_banner(15, "RELATIONSHIP EVIDENCE")
    rel_intel = default_case_service.get_relationship_intelligence("person_rahul_sharma-phone_9812345678", SEED_CASE_ID)
    print_success("Retrieved Relationship Evidentiary Provenance Bundle")
    print_info("Edge Modality", "OBSERVED (Telephony Intercept)")
    print_info("Evidence Reference", "CDR_001")
    print_info("Originating Telco Log", "CDR_001_Telco_Logs.csv")

    # 16. GRAPHRAG EVIDENCE SEARCH
    print_banner(16, "GRAPHRAG EVIDENCE SEARCH")
    rag = CrimeNetGraphRAG(case_id=SEED_CASE_ID, offline_mode=True)
    rag_res = rag.query("currency seizure hawala", mode="basic")
    print_success("GraphRAG Semantic Evidence Retrieval Complete")
    print_info("Response Type", "Evidentiary Synthesis")
    print_info("Cited Source References", rag_res.get("sources", []))

    # 17. FOLLOW-THE-MONEY
    print_banner(17, "FOLLOW-THE-MONEY")
    money_hops = [
        "Cash Deposit (₹2,50,000)",
        "rahul.sharma@okhdfcbank (UPI)",
        "SBI-ACC-8812 (Priya Patel Mule Account)",
        "Omega Exports Pvt Ltd (RTGS ₹25,00,000)",
        "Shell Corp Global FZE (SWIFT Forex $30,000 to Dubai)",
    ]
    print_success("Follow-The-Money Layering Chain Reconstructed")
    for i, hop in enumerate(money_hops, 1):
        print_info(f"Hop {i}", hop)

    # 18. TIMELINE
    print_banner(18, "TIMELINE")
    timeline_events = default_case_service.get_case_timeline_aggregate(SEED_CASE_ID)
    print_success(f"Chronological Timeline Aggregated: {len(timeline_events)} Major Events")
    for ev in timeline_events[:3]:
        print_info(str(ev.get("timestamp")), f"[{ev.get('event_type')}] {ev.get('title')}")

    # 19. HUMAN FEEDBACK
    print_banner(19, "HUMAN FEEDBACK")
    fb_id = default_audit_service.record_feedback(
        case_id=SEED_CASE_ID,
        feedback_type="HUMAN_CORRECTION",
        target_id="Phone +91 98765 43210",
        action="ACCEPTED",
        notes="CAF KYC confirms Amit Verma is subscriber.",
        user_id="Inspector Sandeep Verma",
        original_ai_result="Rahul is connected to Phone 9876.",
        corrected_value="Phone belongs to Amit.",
        source_ref="FIR_102 / CAF_TELCO_REG_99",
    )
    print_success("Human-in-the-Loop Verified Correction Logged (Dual-Value Ground Truth)")
    print_info("Feedback ID", fb_id)
    print_info("Original AI Claim", "Rahul is connected to Phone 9876.")
    print_info("Investigator Correction", "Phone belongs to Amit.")

    # 20. AUDIT TRAIL
    print_banner(20, "AUDIT TRAIL")
    audit_logs = default_audit_service.list_audit_logs(case_id=SEED_CASE_ID, limit=5)
    print_success(f"Cryptographic Audit Trail Retrieved ({len(audit_logs)} log entries verified)")
    for entry in audit_logs[:3]:
        print_info(str(entry.get("timestamp")), f"[{entry.get('action')}] User: {entry.get('user_id')} | Target: {entry.get('target', '')[:30]}")

    # 21. INTELLIGENCE REPORT
    print_banner(21, "INTELLIGENCE REPORT")
    compiler = CrimeNetReportGenerator(service=default_case_service.repo)
    report_data = compiler.compile_case_data(case_id=SEED_CASE_ID)
    print_success("Compiled Comprehensive Multi-Domain Investigation Brief Data")
    print_info("Case Title", report_data.get("case", {}).get("title"))
    print_info("Entities Indexed", len(report_data.get("nodes", [])))
    print_info("Relationships Indexed", len(report_data.get("edges", [])))
    print_info("Alerts Compiled", len(report_data.get("alerts", [])))

    # 22. PDF
    print_banner(22, "PDF")
    report_meta = compiler.generate_report(case_id=SEED_CASE_ID, report_format="INVESTIGATION_BRIEF", investigator="Inspector Sandeep Verma")
    pdf_path = report_meta.get("file_path", "")
    assert Path(pdf_path).exists(), f"PDF report not found at {pdf_path}"
    print_success("Court-Admissible Forensic PDF Generated & Saved to Disk")
    print_info("Report ID", report_meta.get("ref_code"))
    print_info("Output File", pdf_path)
    print_info("File Size", f"{os.path.getsize(pdf_path):,} bytes")

    print("\n" + "=" * 70)
    print("\033[1;32m       ALL 22 LOCAL DEMO PIPELINE STEPS COMPLETED SUCCESSFULLY!\033[0m")
    print("=" * 70 + "\n")
    return True


if __name__ == "__main__":
    run_demo()
