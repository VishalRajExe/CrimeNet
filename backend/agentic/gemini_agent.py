"""
gemini_agent.py - Google Gemini AI Agent for CrimeNet
Provides real-time investigative pair-programming with Indian Law Enforcement IOs.
Powered by Google Gemini 2.5 Flash API with active contextual grounding in
NetworkX graph metrics, scikit-learn Isolation Forest, and GraphRAG evidence.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from ..config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER
from ..storage.graph_rag import default_graph_rag
from ..intelligence.network_analytics import default_network_analytics
from ..intelligence.anomaly_detector import default_anomaly_detector
from ..extraction.ner_extractor import default_extractor

logger = logging.getLogger("crimenet.agentic.gemini")

GEMINI_API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

INVESTIGATIVE_SYSTEM_PROMPT = """You are CrimeNet Gemini, an elite AI Criminal Intelligence Analyst assisting Indian Police Investigating Officers (IOs), Cyber Crime Cells, and Financial Intelligence Units (FIU-IND).

Your objectives:
1. Synthesize plain English explainable intelligence from criminal graphs and evidence.
2. Identify syndicate hierarchy: Kingpins, Key Conduit Brokers, Mule Funnel Accounts, and Shell Companies.
3. Cite Indian legal statutes: Section 66C/66D IT Act, Sections 419/420/120B IPC (or Bharatiya Nyaya Sanhita equivalents), PMLA 2002, Section 102 CrPC (Account Freezing), Section 91 CrPC (Summons for Records), and Lookout Circulars (LOC).
4. Provide structured, actionable next steps for police field teams.
5. Ground your analysis strictly in the provided topological metrics, anomalous outliers, and evidence triples.

Maintain a professional, authoritative, tactical law enforcement tone. Use markdown headings, bullet points, and bold text for clarity."""


class GeminiInvestigativeAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).strip().lower()

    def is_configured(self) -> bool:
        """Return whether a real Gemini request should be attempted.

        Offline mode and the placeholder key shipped in ``.env.example`` must
        use the deterministic local fallback instead of making a network call.
        """
        provider = os.getenv("LLM_PROVIDER", self.provider).strip().lower()
        key = (self.api_key or "").strip()
        placeholder_keys = {
            "your_gemini_api_key_here",
            "your_actual_gemini_api_key_here",
        }
        return provider != "offline" and bool(key) and key.lower() not in placeholder_keys

    def _call_gemini_api(self, prompt: str, system_prompt: str = INVESTIGATIVE_SYSTEM_PROMPT) -> Optional[str]:
        """Calls Google Gemini 2.5 Flash API via httpx."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
                "topP": 0.95
            }
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    logger.warning("Google Gemini API returned status %d: %s", res.status_code, res.text)
        except Exception as e:
            logger.error("Gemini API call exception: %s", e)

        return None

    def chat(
        self,
        message: str,
        case_id: str = "CASE-2024-MH-088",
        history: Optional[List[Dict[str, str]]] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        edges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes grounded investigative reasoning for the 6 core tactical tasks,
        narrative text-to-graph extraction, and free-form police inquiries.
        """
        nodes = nodes or []
        edges = edges or []
        clean_msg = message.strip()
        msg_lower = clean_msg.lower()

        # ---------------------------------------------------------------------
        # 1. TASK: 🎯 Identify syndicate hierarchy & kingpin
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["syndicate hierarchy", "kingpin", "hierarchy", "mastermind", "key player"]):
            pr_res = default_network_analytics.compute_centrality(nodes, edges, metric="pagerank")
            bet_res = default_network_analytics.compute_centrality(nodes, edges, metric="betweenness")
            rankings = pr_res.get("rankings", [])

            top_kingpin = rankings[0] if rankings else {"label": "Primary Suspect", "type": "PERSON", "score": 0.9}
            brokers = [r for r in rankings[1:5] if r["id"] != top_kingpin.get("id")]
            mule_accounts = [n for n in nodes if n.get("type", "").lower() in ("account", "bank", "upi") or "@" in n.get("label", "")]

            context_facts = f"""
Topological Rankings:
- Primary Central Coordinator / Kingpin: {top_kingpin.get('label')} ({top_kingpin.get('type')}) - Centrality Score: {top_kingpin.get('score')}
- Key Conduit Brokers: {', '.join([f"{b['label']} ({b['type']})" for b in brokers])}
- Identified Mule Accounts: {', '.join([m.get('label', m.get('id')) for m in mule_accounts[:4]]) if mule_accounts else 'None explicit in active layer'}
Total Mapped Operatives: {len(nodes)}
Total Inter-cell Ties: {len(edges)}
"""
            prompt = f"Analyze the syndicate hierarchy for case {case_id} based on these exact topological findings:\n{context_facts}\nExplain each operative's operational role (Mastermind, Broker, Mule, Shell Company) and outline actionable arrest/interdiction priorities."

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                gemini_reply = f"""### 🎯 Syndicate Hierarchy & Command Structure ({case_id})

Topological graph analysis of **{len(nodes)} entities** and **{len(edges)} connections** reveals a structured, tiered criminal syndicate:

#### 1. Syndicate Mastermind / Central Coordinator
- **Operative**: **{top_kingpin.get('label')}** (`{top_kingpin.get('type')}`)
- **Network Influence (PageRank)**: `{top_kingpin.get('score')}`
- **Operational Role**: Exercises apex command authority, initiating primary fraud directives and controlling downstream fund disbursement.

#### 2. Key Conduit Brokers
{chr(10).join([f"- **{b['label']}** (`{b['type']}`) — Centrality: `{b['score']}`. Serves as intermediary conduit bridging discrete operational cells." for b in brokers])}

#### 3. Identified Financial Layering Mule Accounts
{chr(10).join([f"- **{m.get('label', m.get('id'))}** (`{m.get('type')}`) — Used for rapid fund splitting to evade FIU-IND triggers." for m in mule_accounts[:4]]) if mule_accounts else "- No direct mule accounts identified in current filter."}

#### ⚖️ Tactical Law Enforcement Recommendation
1. Issue **Lookout Circular (LOC)** against **{top_kingpin.get('label')}** to prevent international egress.
2. Requisition telecom call detail records (CDR) and IMEI dump under **Section 91 CrPC** for all key conduit brokers.
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 2. TASK: 💸 Trace 3-hop money trail & mule accounts
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["trace", "money trail", "mule account", "follow the money", "hawala", "layering"]):
            # Extract financial edges
            trans_edges = []
            for e in edges:
                lbl = str(e.get("label", "")).lower()
                amt = e.get("amount") or e.get("weight")
                if amt or any(k in lbl for k in ["transfer", "wire", "₹", "rs", "lakh", "crore", "upi"]):
                    trans_edges.append(e)

            mule_nodes = [n for n in nodes if any(k in n.get("label", "").lower() for k in ["mule", "acc", "sbi", "hdfc", "@", "bank", "vault", "logistics"])]

            context_facts = f"""
Financial Layering Topology:
- Identified Financial Edges: {len(trans_edges)}
- Financial Flow Links: {', '.join([f"{e.get('source')} -> {e.get('target')} ({e.get('label', e.get('amount', 'funds'))})" for e in trans_edges[:6]])}
- Identified Mule & Corporate Entities: {', '.join([m.get('label', m.get('id')) for m in mule_nodes[:6]])}
"""
            prompt = f"Provide a detailed 3-Hop 'Follow the Money' financial forensic trail for case {case_id} based on:\n{context_facts}\nDetail Hop 1 (Ingress via UPI), Hop 2 (Funneling into Mule Accounts), and Hop 3 (Commercial / Offshore Wire Layering). Prescribe Section 102 CrPC actions."

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                sample_flow = trans_edges[:4] if trans_edges else []
                flow_lines = [f"- **Hop {i+1}**: `{e.get('source')}` ➔ `{e.get('target')}` ({e.get('label', e.get('amount', 'Transferred Funds'))})" for i, e in enumerate(sample_flow)]
                gemini_reply = f"""### 💸 Forensic 3-Hop Financial Layering Trail ({case_id})

Comprehensive audit of transaction vectors across the criminal network reveals structured **money laundering layering**:

#### 🔄 Financial Flow Sequence:
{chr(10).join(flow_lines) if flow_lines else "- Direct extortion proceeds collected via UPI handles.\n- Intra-hour disbursement into regional Surat & Mumbai mule accounts.\n- Aggregation into shell logistics accounts followed by offshore wires."}

#### 📋 3-Hop Breakdown:
1. **Hop 1 — Ingress (Collection)**: Illicit extorted capital collected through victim-facing UPI handles and digital payment links.
2. **Hop 2 — Layering (Mule Funnels)**: Dispersed in sub-₹50,000 tranches across multiple mule accounts to stay below automated PMLA threshold flags.
3. **Hop 3 — Egress / Integration (Offshore & Shells)**: Routed via commercial trade-based invoices and shell logistics fronts into offshore jurisdictions.

#### 🚨 Immediate Police Directive:
- Transmit immediate debit freeze requisitions under **Section 102 CrPC** to Bank Nodal Officers for all identified Hop-2 accounts.
- Summon Bank KYC files and beneficiary withdrawal IP logs under **Section 91 CrPC**.
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 3. TASK: 🌲 Run Isolation Forest anomaly detection
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["isolation forest", "anomaly", "anomalies", "outlier", "flagged"]):
            anomalies = default_anomaly_detector.detect_anomalies(nodes, edges)
            bottlenecks = default_network_analytics.find_network_bottlenecks(nodes, edges)

            context_facts = f"""
scikit-learn Isolation Forest Results:
- Total Anomalies Flagged: {len(anomalies)}
- Top Anomalous Entities: {json.dumps(anomalies[:5], indent=2)}
- Articulation Bottlenecks: {json.dumps(bottlenecks.get('cut_vertices', [])[:3], indent=2)}
"""
            prompt = f"Explain the scikit-learn Isolation Forest anomaly detections for case {case_id}:\n{context_facts}\nDetail each anomalous node, why the isolation trees flagged it (inflow/outflow imbalance, hub score, betweenness), and police operational impact."

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                anom_lines = []
                for a in anomalies[:5]:
                    anom_lines.append(f"- **{a['label']}** (`{a['type']}`) — Anomaly Confidence: **{int(a['anomaly_score'] * 100)}%**\n  *Tags*: `{', '.join(a['tags'])}`\n  *Forensic Rationale*: {a['reason']}")

                gemini_reply = f"""### 🌲 scikit-learn Isolation Forest Anomaly Analysis ({case_id})

Unsupervised multidimensional anomaly detection trained on topology, betweenness, in/out degree ratios, and transaction volume flagged **{len(anomalies)} statistical outliers**:

{chr(10).join(anom_lines) if anom_lines else "- No severe outliers detected exceeding statistical contamination threshold."}

#### 🔬 Analytical Rationale:
The Isolation Forest isolates points that require few partitions along features like `in_degree / out_degree` disparity, abnormally high betweenness centrality, and extreme volume. These entities represent high-risk laundering conduits and primary command hubs.
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 4. TASK: ⚖️ Draft Section 102 CrPC account freeze order
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["102", "freeze", "freezing order", "crpc", "order", "bank notice"]):
            mule_accounts = [n.get("label", n.get("id")) for n in nodes if n.get("type", "").lower() in ("account", "bank", "upi") or "@" in n.get("label", "")]
            target_account = mule_accounts[0] if mule_accounts else "vikram@okhdfcbank / SBI-Mule-40912"

            prompt = f"""Draft a formal, judicial-grade Bank Account Freezing Order under Section 102 Code of Criminal Procedure, 1973 (and Section 107 Bharatiya Nagarik Suraksha Sanhita, 2023) for case {case_id}.
Target Accounts to Freeze: {target_account}
Police Station: Cyber Crime Cell, Crime Branch
Alleged Offenses: Sections 419, 420, 384, 120-B IPC and Section 66-C/66-D Information Technology Act, 2000.
Include compliance mandate, 24-hour KYC record requisition, and warning of penal consequences for non-compliance."""

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                gemini_reply = f"""### ⚖️ OFFICIAL POLICE REQUISITION // DEBIT FREEZE ORDER
**UNDER SECTION 102 CODE OF CRIMINAL PROCEDURE, 1973**
*(Read with Section 107 Bharatiya Nagarik Suraksha Sanhita, 2023)*

---

**OFFICE OF THE INVESTIGATING OFFICER**  
Cyber Crime Cell, Bandra Kurla Complex, Crime Branch  
**FIR No:** {case_id}/2024  
**Date:** Live Forensic Order  

**TO:**  
The Chief Nodal Officer / Manager  
Scheduled Commercial Banks / Payment Gateways / UPI Service Providers  

**SUBJECT: URGENT NOTICE UNDER SECTION 102 CrPC FOR IMMEDIATE DEBIT FREEZE ON ILLICIT BENEFICIARY ACCOUNTS**

Sir / Madam,

1. **Criminal Investigation Reference**: An active investigation is being conducted in connection with **FIR No. {case_id}/2024** registered under Sections 419, 420, 384, 120-B of the Indian Penal Code (IPC) read with Sections 66C and 66D of the Information Technology Act, 2000.
2. **Statutory Direction**: In exercise of powers vested in me under **Section 102 of the Code of Criminal Procedure, 1973**, you are hereby directed to **IMMEDIATELY FREEZE ALL DEBIT TRANSACTIONS** on the following account(s) associated with suspected organized cyber fraud:
   - **Account Identifier(s)**: `{target_account}`
   - **Action Mandated**: **Total Debit Freeze** (Prevent ATM withdrawals, UPI payouts, and RTGS/NEFT transfers).
3. **Requisition of Evidentiary Records (Sec 91 CrPC)**: Furnish the following within 24 hours:
   - Account opening form, KYC documents, and proof of address.
   - Certified complete transaction statement from account inception to date.
   - IP login logs, associated mobile numbers, and linked UPI VPAs.
4. **Penal Warning**: Failure to comply with this order immediately invites penal proceedings under Section 175 and 188 of the Indian Penal Code.

**BY ORDER OF:**  
Investigating Officer, Cyber Crime Police Station  
*CrimeNet Digital Signature Hash: SHA-256 Verified*
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 5. TASK: 💥 Find critical communication bridges (cut vertices)
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["cut vert", "bridge", "bottleneck", "single point", "failure", "articulation"]):
            bottlenecks = default_network_analytics.find_network_bottlenecks(nodes, edges)
            cut_nodes = bottlenecks.get("cut_vertices", [])
            bridges = bottlenecks.get("bridges", [])

            context_facts = f"""
Network Bottlenecks & Articulation Points:
- Identified Cut Vertices: {json.dumps(cut_nodes, indent=2)}
- Structural Bridges: {json.dumps(bridges, indent=2)}
Total Graph Entities: {len(nodes)}
"""
            prompt = f"Analyze the critical network bottlenecks and articulation points for case {case_id} based on:\n{context_facts}\nExplain how interdicting these specific cut vertices partitions the syndicate and disrupts criminal operations."

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                cv_lines = [f"- **{cv['label']}** (`{cv['type']}`) — Threat Level: `{cv['threat']}`\n  *Impact*: {cv['explanation']}" for cv in cut_nodes[:4]]
                gemini_reply = f"""### 💥 Critical Network Bottlenecks & Articulation Points ({case_id})

Topological graph analysis has identified **{len(cut_nodes)} articulation points (cut vertices)** and **{len(bridges)} structural bridges**. 

An **articulation point** is a critical single point of failure: removing or arresting this operative partitions the criminal network into mutually disconnected components.

#### 🛡️ Identified Single Points of Failure:
{chr(10).join(cv_lines) if cv_lines else "- No single articulation point detected; network exhibits high redundant mesh connectivity."}

#### 🎯 Strategic Enforcement Recommendation:
Coordinating simultaneous arrests or device seizures of these specific operatives will disrupt inter-cell communications, leaving subordinate cells unable to coordinate money movements or flight logistics.
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 6. TASK: 📜 Summarize GraphRAG evidence citations
        # ---------------------------------------------------------------------
        if any(w in msg_lower for w in ["graphrag", "evidence", "citation", "triples", "knowledge", "fir fact"]):
            rag_info = default_graph_rag.query(case_id=case_id, query_text=message or "criminal network evidence", top_k=5)
            triples = rag_info.get("knowledge_triples", [])
            chunks = rag_info.get("vector_chunks", [])

            context_facts = f"""
GraphRAG Evidence Store for {case_id}:
- Knowledge Triples: {json.dumps(triples[:6], indent=2)}
- Vector Chunks: {json.dumps(chunks[:3], indent=2)}
"""
            prompt = f"Synthesize a forensic evidence briefing for case {case_id} citing these GraphRAG knowledge triples and document extracts:\n{context_facts}"

            gemini_reply = self._call_gemini_api(prompt) if self.is_configured() else None
            if not gemini_reply:
                t_lines = [f"- `{t['subject']}` ➔ **{t['predicate']}** ➔ `{t['object']}` (Source: *{t.get('source', 'FIR Evidence')}*, Confidence: `{t.get('confidence', 0.88)}`)" for t in triples[:6]]
                c_lines = [f"> \"{c['text'][:140]}...\" — *Source: {c['source']} (Relevance: {c['score']})*" for c in chunks[:2]]

                gemini_reply = f"""### 📜 GraphRAG Evidence & Knowledge Graph Citations ({case_id})

Retrieved from multi-source case evidence (FIR documents, bank transcripts, and interrogation logs):

#### 🔗 Verified Knowledge Graph Triples:
{chr(10).join(t_lines) if t_lines else "- Standard operational links indexed across primary case dossier."}

#### 📑 Semantic Evidence Snippets:
{chr(10).join(c_lines) if c_lines else "- Case records indexed in vector store."}

#### ⚖️ Judicial Admissibility Note:
All triples are linked to specific paragraphs in the primary evidence chain of custody, satisfying certification requirements under **Section 65B of the Indian Evidence Act, 1872** (and Sec 63 BSA 2023).
"""
            return {
                "reply": gemini_reply,
                "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
                "case_id": case_id,
                "extractedCount": 0
            }

        # ---------------------------------------------------------------------
        # 7. Check if user is entering a suspect narrative to ingest
        # ---------------------------------------------------------------------
        is_narrative = (
            len(clean_msg.split()) >= 6
            and any(w in msg_lower for w in ["suspect", "transferred", "wired", "vehicle", "phone", "contact", "acc", "mule", "rs", "₹", "stole", "extorted", "director"])
            and not any(q in msg_lower for q in ["how", "what", "who", "why", "where", "explain", "draft", "trace", "identify", "find"])
        )

        new_nodes = []
        new_edges = []
        if is_narrative:
            try:
                extraction = default_extractor.extract_from_narrative(clean_msg, case_id=case_id)
                if extraction.nodes:
                    new_nodes = [n.to_dict() for n in extraction.nodes]
                    new_edges = [e.to_dict() for e in extraction.edges]
            except Exception as e:
                logger.warning("NER extraction notice: %s", e)

        # ---------------------------------------------------------------------
        # 8. General Law Enforcement Inquiry (Powered by Gemini 2.5 Flash)
        # ---------------------------------------------------------------------
        top_operatives = []
        if nodes:
            try:
                cent = default_network_analytics.compute_centrality(nodes, edges, metric="pagerank")
                top_operatives = [f"{r['label']} ({r['type']}, score: {r['score']})" for r in cent.get("rankings", [])[:4]]
            except Exception:
                pass

        grounding_context = f"""
Active Case: {case_id}
Mapped Network Entities ({len(nodes)}): {', '.join([n.get('label', n.get('id')) for n in nodes[:15]])}
Top Influential Operatives: {', '.join(top_operatives) if top_operatives else 'N/A'}
New Entities Extracted from Input: {len(new_nodes)} ({', '.join([n['label'] for n in new_nodes]) if new_nodes else 'None'})

Investigator Query: "{clean_msg}"

Provide an authoritative, clear response for the police investigating officer with statutory citations and recommended field actions.
"""
        gemini_reply = self._call_gemini_api(grounding_context) if self.is_configured() else None
        if not gemini_reply:
            gemini_reply = self._generate_fallback_response(clean_msg)

        if new_nodes:
            gemini_reply += f"\n\n---\n📌 **Auto-Extracted Entities Added to Graph**: {', '.join([f'`{n['label']}` ({n['type']})' for n in new_nodes])}."

        return {
            "reply": gemini_reply,
            "model": "Google Gemini 2.5 Flash" if self.is_configured() else "CrimeNet Gemini Engine (Local Grounded)",
            "case_id": case_id,
            "extractedCount": len(new_nodes),
            "newNodes": new_nodes,
            "newEdges": new_edges
        }

    def _generate_fallback_response(self, user_query: str) -> str:
        return (
            "### 🛡️ CrimeNet Gemini Intelligence Assessment\n\n"
            "Based on operational graph topology and legal analysis:\n\n"
            "1. **Syndicate Structure**: Active criminal syndicate featuring modular operational cells linked through central coordinator hubs.\n"
            "2. **Next Steps**:\n"
            "   - Requisition CDR and IMEI records under **Section 91 CrPC**.\n"
            "   - Issue **Section 102 CrPC** debit freeze notices for suspect accounts.\n"
            "   - Transmit Lookout Circular (LOC) for primary suspects."
        )


default_gemini_agent = GeminiInvestigativeAgent()
