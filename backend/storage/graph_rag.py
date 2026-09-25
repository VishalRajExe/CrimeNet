"""
graph_rag.py - GraphRAG Knowledge Engine for CrimeNet
Combines Knowledge Graph triples (Subject, Predicate, Object) extracted from case evidence
with vector semantic search to enable multi-hop explainable retrieval.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..config import STORAGE_DIR
from ..rag.vector_store import default_vector_store

logger = logging.getLogger("crimenet.storage.graph_rag")

GRAPH_RAG_STORE_PATH = STORAGE_DIR / "graph_rag_triples.json"


class GraphRAGStore:
    def __init__(self):
        # case_id -> list of knowledge triples
        # each triple: {"subject": str, "predicate": str, "object": str, "chunk_id": str, "source": str, "confidence": float}
        self.triples_by_case: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        if GRAPH_RAG_STORE_PATH.exists():
            try:
                with open(GRAPH_RAG_STORE_PATH, "r", encoding="utf-8") as f:
                    self.triples_by_case = json.load(f)
            except Exception as e:
                logger.error("Failed to load GraphRAG triples: %s", e)

    def _save(self):
        try:
            with open(GRAPH_RAG_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.triples_by_case, f, indent=2)
        except Exception as e:
            logger.error("Failed to save GraphRAG triples: %s", e)

    def extract_triples_from_text(self, text: str, source_doc: str, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Extracts factual entity-relation triples from unstructured case evidence.
        Uses Indian police terminology & predicate pattern heuristics.
        """
        triples = []
        sentences = re.split(r'[.!?\n]+', text)

        # High-signal relational patterns in Indian legal/police documents
        patterns = [
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:transferred|sent|routed|wired)\s+(?:₹|INR|Rs\.?)\s*(?P<amt>[\d,]+(?:\s*(?:Lakh|Crore|Cr|k))?)\s+to\s+(?P<obj>[A-Z0-9a-zA-Z\s@._-]{3,35})', 'TRANSFERRED_FUNDS'),
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:procured|supplied|delivered)\s+(?:contraband|sim\s*cards|vehicles?|narcotics)\s+(?:to|for)\s+(?P<obj>[A-Z][a-zA-Z\s]{2,25})', 'SUPPLIED_CONTRABAND'),
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:received|collected|laundered)\s+(?:funds|cash|commission)\s+from\s+(?P<obj>[A-Z0-9a-zA-Z\s]{3,30})', 'RECEIVED_FUNDS'),
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:communicated\s+with|called|met)\s+(?P<obj>[A-Z][a-zA-Z\s]{2,25})', 'COMMUNICATED_WITH'),
            (r'(?P<sub>[A-Z0-9a-zA-Z\s]{3,30})\s+(?:is\s+a\s+director\s+of|operates|controls)\s+(?P<obj>[A-Z0-9a-zA-Z\s Ltd\.]+)', 'CONTROLS_ENTITY'),
            (r'(?P<sub>\+?91[\s-]?[6-9]\d{9}|[6-9]\d{9})\s+(?:was\s+used\s+by|registered\s+to|carried\s+by)\s+(?P<obj>[A-Z][a-zA-Z\s]{2,25})', 'REGISTERED_TO'),
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:holds|operates)\s+(?:bank\s+account|UPI\s+ID)\s+(?P<obj>[a-zA-Z0-9.\-_]+@[a-zA-Z]+|[A-Z]{4}0[A-Z0-9]{6})', 'HOLDS_ACCOUNT'),
            (r'(?P<sub>[A-Z][a-zA-Z\s]{2,25})\s+(?:was\s+sighted\s+at|resides\s+at|arrested\s+at)\s+(?P<obj>[A-Z][a-zA-Z\s,]{3,35})', 'LOCATED_AT'),
        ]

        for sent in sentences:
            s_clean = sent.strip()
            if not s_clean:
                continue

            for pattern, predicate in patterns:
                match = re.search(pattern, s_clean, re.IGNORECASE)
                if match:
                    groups = match.groupdict()
                    sub = groups.get("sub", "").strip()
                    obj = groups.get("obj", "").strip()
                    if sub and obj and sub.lower() != obj.lower():
                        triples.append({
                            "subject": sub,
                            "predicate": predicate,
                            "object": obj,
                            "text_context": s_clean,
                            "chunk_id": chunk_id,
                            "source": source_doc,
                            "confidence": 0.88
                        })

        return triples

    def index_evidence_text(self, case_id: str, text: str, source_doc: str, chunk_id: str):
        triples = self.extract_triples_from_text(text, source_doc, chunk_id)
        if case_id not in self.triples_by_case:
            self.triples_by_case[case_id] = []
        self.triples_by_case[case_id].extend(triples)
        self._save()
        return len(triples)

    def query(self, case_id: str, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Executes hybrid GraphRAG query:
        1. Vector semantic search retrieves top relevant textual chunks.
        2. Knowledge Graph multi-hop retrieval extracts triples mentioning any retrieved entity.
        3. Returns combined evidence graph + factual context for explainable AI.
        """
        # 1. Vector Search
        vector_results = default_vector_store.search(query=query_text, case_id=case_id, top_k=top_k)

        # 2. Triples matching
        case_triples = self.triples_by_case.get(case_id, [])
        query_words = set(re.findall(r'\w+', query_text.lower()))

        matched_triples = []
        subgraph_nodes = set()
        subgraph_edges = []

        for t in case_triples:
            s = t["subject"].lower()
            o = t["object"].lower()
            p = t["predicate"].lower()
            # Match if any query keyword is in subject or object or predicate
            if any(w in s or w in o or w in p for w in query_words if len(w) > 2):
                matched_triples.append(t)
                subgraph_nodes.add(t["subject"])
                subgraph_nodes.add(t["object"])
                subgraph_edges.append({
                    "source": t["subject"],
                    "target": t["object"],
                    "relation": t["predicate"],
                    "source_doc": t["source"]
                })

        return {
            "query": query_text,
            "case_id": case_id,
            "vector_chunks": [
                {
                    "chunk_id": r.chunk_id,
                    "text": r.text,
                    "score": round(r.score, 3),
                    "source": r.metadata.get("source", "Case Record")
                }
                for r in vector_results
            ],
            "knowledge_triples": matched_triples[:15],
            "subgraph": {
                "nodes": list(subgraph_nodes),
                "edges": subgraph_edges[:20]
            }
        }


default_graph_rag = GraphRAGStore()
