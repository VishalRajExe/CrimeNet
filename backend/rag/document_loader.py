"""
CrimeNet AI - Multi-format Document Loader
Parses FIR PDFs, CDR CSVs, Bank Transaction Statements, and Text narratives.
Preserves page-level and row-level metadata for court-admissible source citations.
"""

import os
import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdf

logger = logging.getLogger(__name__)


@dataclass
class DocumentPage:
    page_num: int
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedDocument:
    doc_id: str
    filename: str
    file_type: str  # 'pdf', 'csv', 'txt', 'json'
    case_id: str
    pages: List[DocumentPage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


class DocumentLoader:
    """Loads documents of various formats into standardized LoadedDocument objects."""

    @staticmethod
    def load_file(file_path: str, case_id: str = "DEFAULT") -> LoadedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        ext = path.suffix.lower()
        filename = path.name
        doc_id = f"DOC_{case_id}_{path.stem}"

        if ext == ".pdf":
            return DocumentLoader._load_pdf(path, doc_id, filename, case_id)
        elif ext == ".csv":
            return DocumentLoader._load_csv(path, doc_id, filename, case_id)
        elif ext == ".json":
            return DocumentLoader._load_json(path, doc_id, filename, case_id)
        elif ext in [".txt", ".log", ".md"]:
            return DocumentLoader._load_text(path, doc_id, filename, case_id)
        else:
            # Fallback to plain text
            return DocumentLoader._load_text(path, doc_id, filename, case_id)

    @staticmethod
    def _load_pdf(path: Path, doc_id: str, filename: str, case_id: str) -> LoadedDocument:
        pages = []
        try:
            reader = pypdf.PdfReader(str(path))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(DocumentPage(page_num=idx + 1, text=text.strip(), metadata={"total_pages": len(reader.pages)}))
        except Exception as e:
            logger.error(f"Error loading PDF {filename}: {e}")
            pages.append(DocumentPage(page_num=1, text=f"[PDF extraction error: {e}]"))

        return LoadedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="pdf",
            case_id=case_id,
            pages=pages,
            metadata={"pages_count": len(pages)}
        )

    @staticmethod
    def _load_csv(path: Path, doc_id: str, filename: str, case_id: str) -> LoadedDocument:
        """Parses CDR / Bank CSVs into readable evidence narrative sentences."""
        pages = []
        rows_per_page = 50
        current_rows = []
        page_num = 1

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            is_cdr = any("call" in h.lower() or "imei" in h.lower() or "duration" in h.lower() for h in headers)
            is_bank = any("amount" in h.lower() or "upi" in h.lower() or "balance" in h.lower() or "debit" in h.lower() for h in headers)

            for row_idx, row in enumerate(reader, start=1):
                clean_row = {k.strip(): v.strip() for k, v in row.items() if k and v}
                if is_cdr:
                    sentence = (
                        f"[Row {row_idx}] Call from {clean_row.get('Calling_No', clean_row.get('caller', 'Unknown'))} "
                        f"to {clean_row.get('Called_No', clean_row.get('receiver', 'Unknown'))} "
                        f"on {clean_row.get('Date', '')} {clean_row.get('Time', '')} "
                        f"(Duration: {clean_row.get('Duration', 'N/A')}s, Tower: {clean_row.get('Tower_ID', clean_row.get('Location', 'N/A'))})"
                    )
                elif is_bank:
                    sentence = (
                        f"[Row {row_idx}] Transaction: From {clean_row.get('Sender', clean_row.get('From_Account', 'Unknown'))} "
                        f"to {clean_row.get('Receiver', clean_row.get('To_Account', 'Unknown'))} "
                        f"Amount: ₹{clean_row.get('Amount', clean_row.get('amount', '0'))} "
                        f"Date: {clean_row.get('Date', clean_row.get('timestamp', 'N/A'))} "
                        f"Type: {clean_row.get('Type', clean_row.get('channel', 'UPI/Bank'))}"
                    )
                else:
                    items = ", ".join(f"{k}: {v}" for k, v in clean_row.items())
                    sentence = f"[Row {row_idx}] {items}"

                current_rows.append(sentence)
                if len(current_rows) >= rows_per_page:
                    pages.append(DocumentPage(page_num=page_num, text="\n".join(current_rows)))
                    current_rows = []
                    page_num += 1

            if current_rows:
                pages.append(DocumentPage(page_num=page_num, text="\n".join(current_rows)))

        return LoadedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="csv",
            case_id=case_id,
            pages=pages,
            metadata={"headers": headers, "is_cdr": is_cdr, "is_bank": is_bank}
        )

    @staticmethod
    def _load_text(path: Path, doc_id: str, filename: str, case_id: str) -> LoadedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return LoadedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="txt",
            case_id=case_id,
            pages=[DocumentPage(page_num=1, text=content)]
        )

    @staticmethod
    def _load_json(path: Path, doc_id: str, filename: str, case_id: str) -> LoadedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        text = json.dumps(data, indent=2)
        return LoadedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="json",
            case_id=case_id,
            pages=[DocumentPage(page_num=1, text=text)],
            metadata={"keys": list(data.keys()) if isinstance(data, dict) else []}
        )
