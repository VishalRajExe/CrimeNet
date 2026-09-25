"""
CrimeNet AI - Hybrid Vector & Evidence Retrieval Store
Provides case-isolated semantic and lexical search over ingested investigative documents.
Operates completely in-memory with optional JSON/Pickle persistence.
Combines TF-IDF N-gram matching (critical for Indian phone/account numbers) with cosine similarity.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunker import TextChunk
from ..config import VECTOR_INDEX_DIR, SIMILARITY_TOP_K, SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    case_id: str
    source_file: str
    page_num: int
    paragraph_num: int
    text: str
    citation_label: str
    score: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "case_id": self.case_id,
            "source_file": self.source_file,
            "page_num": self.page_num,
            "paragraph_num": self.paragraph_num,
            "text": self.text,
            "citation": self.citation_label,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class VectorStore:
    """Case-isolated evidence index for investigative documents."""

    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = index_dir or VECTOR_INDEX_DIR
        self.chunks_by_case: Dict[str, List[TextChunk]] = {}
        self.vectorizers: Dict[str, TfidfVectorizer] = {}
        self.matrices: Dict[str, Any] = {}

    def add_chunks(self, chunks: List[TextChunk], case_id: str = "DEFAULT") -> int:
        """Adds text chunks to the specified case index and updates vector representations."""
        if not chunks:
            return 0

        if case_id not in self.chunks_by_case:
            self.chunks_by_case[case_id] = []

        # Avoid duplicates by chunk_id
        existing_ids = {c.chunk_id for c in self.chunks_by_case[case_id]}
        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

        if not new_chunks:
            return 0

        self.chunks_by_case[case_id].extend(new_chunks)
        self._rebuild_index(case_id)
        logger.info(f"Added {len(new_chunks)} chunks to case {case_id}. Total: {len(self.chunks_by_case[case_id])}")
        return len(new_chunks)

    def _rebuild_index(self, case_id: str) -> None:
        """Fits TF-IDF matrix with word and character n-grams for robust entity retrieval."""
        chunks = self.chunks_by_case.get(case_id, [])
        if not chunks:
            return

        corpus = [c.text for c in chunks]
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="word",
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w@.-]+\b",  # Preserve email, UPI, and hyphenated vehicle numbers
        )
        matrix = vectorizer.fit_transform(corpus)
        self.vectorizers[case_id] = vectorizer
        self.matrices[case_id] = matrix

    def search(
        self,
        query: str,
        case_id: Optional[str] = None,
        top_k: int = SIMILARITY_TOP_K,
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> List[SearchResult]:
        """Searches the evidence corpus for relevant chunks matching the query."""
        if not query or not query.strip():
            return []

        target_cases = [case_id] if case_id and case_id in self.chunks_by_case else list(self.chunks_by_case.keys())
        all_results: List[SearchResult] = []

        for cid in target_cases:
            chunks = self.chunks_by_case.get(cid, [])
            vectorizer = self.vectorizers.get(cid)
            matrix = self.matrices.get(cid)

            if not chunks or vectorizer is None or matrix is None:
                continue

            try:
                query_vec = vectorizer.transform([query])
                scores = cosine_similarity(query_vec, matrix).flatten()

                top_indices = np.argsort(scores)[::-1][:top_k]
                for idx in top_indices:
                    score = float(scores[idx])
                    if score >= threshold:
                        chunk = chunks[idx]
                        all_results.append(
                            SearchResult(
                                chunk_id=chunk.chunk_id,
                                case_id=chunk.case_id,
                                source_file=chunk.source_file,
                                page_num=chunk.page_num,
                                paragraph_num=chunk.paragraph_num,
                                text=chunk.text,
                                citation_label=chunk.citation_label,
                                score=score,
                                metadata=chunk.metadata,
                            )
                        )
            except Exception as e:
                logger.error(f"Search failed for case {cid}: {e}")

        # Sort combined results by score descending
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k]

    def get_all_chunks(self, case_id: str) -> List[TextChunk]:
        return self.chunks_by_case.get(case_id, [])

    def save_index(self, case_id: str) -> None:
        """Serializes chunks for a case to disk."""
        chunks = self.chunks_by_case.get(case_id, [])
        if not chunks:
            return
        out_file = self.index_dir / f"{case_id}_chunks.json"
        data = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "case_id": c.case_id,
                "source_file": c.source_file,
                "page_num": c.page_num,
                "paragraph_num": c.paragraph_num,
                "text": c.text,
                "citation_label": c.citation_label,
                "metadata": c.metadata,
            }
            for c in chunks
        ]
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_index(self, case_id: str) -> bool:
        """Loads serialized chunks for a case from disk."""
        inp_file = self.index_dir / f"{case_id}_chunks.json"
        if not inp_file.exists():
            return False
        with open(inp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        chunks = [TextChunk(**d) for d in data]
        self.add_chunks(chunks, case_id=case_id)
        return True


# Global default instance
default_vector_store = VectorStore()
