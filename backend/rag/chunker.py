"""
CrimeNet AI - Semantic & Paragraph Chunker
Divides documents into searchable units while preserving precise court-admissible citations.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from .document_loader import LoadedDocument


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    case_id: str
    source_file: str
    page_num: int
    paragraph_num: int
    text: str
    citation_label: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentChunker:
    """Chunks documents into semantic blocks with full citation traceability."""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: LoadedDocument) -> List[TextChunk]:
        chunks: List[TextChunk] = []

        for page in doc.pages:
            raw_text = page.text.strip()
            if not raw_text:
                continue

            # First attempt paragraph splitting (double newlines or lines starting with bullet/para)
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
            if not paragraphs:
                paragraphs = [raw_text]

            for para_idx, para in enumerate(paragraphs, start=1):
                # If paragraph fits within chunk size, keep it intact
                if len(para) <= self.chunk_size * 1.5:
                    chunk_id = f"{doc.doc_id}_p{page.page_num}_para{para_idx}"
                    citation = f"{doc.filename} (Page {page.page_num}, Para {para_idx})"
                    chunks.append(
                        TextChunk(
                            chunk_id=chunk_id,
                            doc_id=doc.doc_id,
                            case_id=doc.case_id,
                            source_file=doc.filename,
                            page_num=page.page_num,
                            paragraph_num=para_idx,
                            text=para,
                            citation_label=citation,
                            metadata={"char_len": len(para), "file_type": doc.file_type}
                        )
                    )
                else:
                    # Slide window with overlap
                    words = para.split()
                    word_chunk_size = self.chunk_size // 5  # ~5 chars per word
                    word_overlap = self.chunk_overlap // 5

                    sub_idx = 1
                    for start in range(0, len(words), word_chunk_size - word_overlap):
                        end = min(start + word_chunk_size, len(words))
                        sub_text = " ".join(words[start:end])
                        chunk_id = f"{doc.doc_id}_p{page.page_num}_para{para_idx}_sub{sub_idx}"
                        citation = f"{doc.filename} (Page {page.page_num}, Para {para_idx})"
                        chunks.append(
                            TextChunk(
                                chunk_id=chunk_id,
                                doc_id=doc.doc_id,
                                case_id=doc.case_id,
                                source_file=doc.filename,
                                page_num=page.page_num,
                                paragraph_num=para_idx,
                                text=sub_text,
                                citation_label=citation,
                                metadata={"char_len": len(sub_text), "file_type": doc.file_type}
                            )
                        )
                        sub_idx += 1
                        if end >= len(words):
                            break

        return chunks
