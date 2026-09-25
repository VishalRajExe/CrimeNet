"""CrimeNet Evidence Processing Pipeline.

Architecture:
Case -> Evidence -> Upload -> Validate -> Store metadata -> Process -> Extract -> Analyze -> Link to investigation graph

Supports:
- PDF (via pypdf text-stream extraction and NLP extraction)
- TXT (via UTF-8 decoding and NLP extraction)
- CSV (auto-detects CDR, transactions, cell tower pings, or unstructured text columns)
- JSON (graph nodes/edges format, record feeds, or intelligence payloads)

Status lifecycle:
- Uploaded
- Processing
- Processed
- Failed

Accurate error capturing: Real exceptions are captured and stored in MySQL without faking success.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

# Ensure repo/ai-service and tracked ai-service are in sys.path for NLP extractor
ROOT_DIR = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = ROOT_DIR / "repo" / "ai-service"
TRACKED_AI_DIR = ROOT_DIR / "ai-service"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))
if str(TRACKED_AI_DIR) not in sys.path:
    sys.path.insert(0, str(TRACKED_AI_DIR))

try:
    from app.nlp.extractor import Extractor
except ImportError:
    from repo.ai_service.app.nlp.extractor import Extractor  # type: ignore

from storage.case_data_service import CaseDataService


class EvidenceValidationError(Exception):
    """Raised when evidence file validation fails."""
    pass


class EvidenceProcessingError(Exception):
    """Raised when parsing or extraction of evidence fails."""
    pass


class EvidenceProcessor:
    """End-to-end evidence processing pipeline for CrimeNet cases."""

    SUPPORTED_TYPES = {"PDF", "TXT", "CSV", "JSON"}

    def __init__(self, svc: Optional[CaseDataService] = None, extractor: Optional[Extractor] = None):
        self.svc = svc or CaseDataService()
        self.extractor = extractor or Extractor()

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Compute cryptographic SHA-256 digest for evidence integrity."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def detect_file_type(filename: str, declared_type: Optional[str] = None) -> str:
        """Determine file type from extension or declared override."""
        if declared_type and declared_type.upper() in EvidenceProcessor.SUPPORTED_TYPES:
            return declared_type.upper()
        ext = os.path.splitext(filename)[1].lower().strip(".")
        if ext == "pdf":
            return "PDF"
        elif ext in ("txt", "text", "log"):
            return "TXT"
        elif ext == "csv":
            return "CSV"
        elif ext in ("json", "geojson"):
            return "JSON"
        raise EvidenceValidationError(f"Unsupported file format '.{ext}'. Supported formats: PDF, TXT, CSV, JSON.")

    def validate_evidence(self, filename: str, file_bytes: bytes, file_type: str) -> None:
        """Validate format integrity, size, and header signatures.
        
        Raises EvidenceValidationError with exact root cause if invalid.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise EvidenceValidationError(f"File '{filename}' is empty (0 bytes). Cannot process empty exhibit.")

        # Max 50 MB limit
        if len(file_bytes) > 50 * 1024 * 1024:
            raise EvidenceValidationError(f"File '{filename}' exceeds maximum allowed size of 50 MB ({len(file_bytes):,} bytes).")

        ftype = file_type.upper()
        if ftype not in self.SUPPORTED_TYPES:
            raise EvidenceValidationError(f"Format '{ftype}' is not supported. Initially supported: PDF, TXT, CSV, JSON.")

        # Signature & structural checks
        if ftype == "PDF":
            if not file_bytes.startswith(b"%PDF"):
                # Check within first 1024 bytes (some PDFs have leading comments)
                if b"%PDF" not in file_bytes[:1024]:
                    raise EvidenceValidationError(f"Invalid PDF header in '{filename}'. Missing standard '%PDF' magic bytes.")
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                if len(reader.pages) == 0:
                    raise EvidenceValidationError(f"PDF '{filename}' contains 0 pages.")
            except Exception as e:
                raise EvidenceValidationError(f"Corrupted or invalid PDF file '{filename}': {str(e)}")

        elif ftype == "TXT":
            try:
                # Must be decodable as utf-8 or latin-1
                try:
                    file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    file_bytes.decode("latin-1")
            except Exception as e:
                raise EvidenceValidationError(f"Text encoding failure in '{filename}': {str(e)}")

        elif ftype == "CSV":
            try:
                text = file_bytes.decode("utf-8", errors="replace")
                sniffer = csv.Sniffer()
                # Test first 4096 bytes
                sample = text[:4096]
                if "\n" not in sample and "\r" not in sample and len(text) > 200:
                    raise EvidenceValidationError(f"CSV file '{filename}' does not contain line breaks.")
                reader = csv.reader(io.StringIO(text))
                first_row = next(reader, None)
                if not first_row:
                    raise EvidenceValidationError(f"CSV file '{filename}' is empty or has no header.")
            except EvidenceValidationError:
                raise
            except Exception as e:
                raise EvidenceValidationError(f"Malformed CSV content in '{filename}': {str(e)}")

        elif ftype == "JSON":
            try:
                text = file_bytes.decode("utf-8")
                json.loads(text)
            except UnicodeDecodeError as e:
                raise EvidenceValidationError(f"JSON encoding error in '{filename}': {str(e)}")
            except json.JSONDecodeError as e:
                raise EvidenceValidationError(f"Invalid JSON syntax in '{filename}' at line {e.lineno}, col {e.colno}: {e.msg}")

    # ----------------------------------------------------------------------- #
    # EXTRACTORS FOR EACH FORMAT
    # ----------------------------------------------------------------------- #
    def _extract_pdf(self, file_bytes: bytes, filename: str, evidence_id: str = "") -> Dict[str, Any]:
        """Extract text from PDF pages and execute NLP information extraction."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    raise EvidenceProcessingError(f"PDF '{filename}' is encrypted and password-protected.")

            pages_text = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(txt)

            full_text = "\n\n".join(pages_text).strip()
            if not full_text:
                raise EvidenceProcessingError(
                    f"Scanned / image-only PDF '{filename}': No extractable text stream found across {len(reader.pages)} page(s)."
                )

            extracted = self.extractor.process(full_text, evidence_id=evidence_id, filename=filename)
            return {
                "raw_text": extracted.get("raw_text", full_text)[:10000],  # Preview
                "entities": extracted.get("entities", []),
                "relations": extracted.get("relations", []),
                "stats": {
                    "pages": len(reader.pages),
                    "characters": len(full_text),
                    "entities_found": len(extracted.get("entities", [])),
                    "relations_found": len(extracted.get("relations", []))
                }
            }
        except EvidenceProcessingError:
            raise
        except Exception as e:
            raise EvidenceProcessingError(f"PDF parsing error in '{filename}': {str(e)}")

    def _extract_txt(self, file_bytes: bytes, filename: str, evidence_id: str = "") -> Dict[str, Any]:
        """Extract text from TXT and execute NLP information extraction."""
        try:
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = file_bytes.decode("latin-1")

            if not text.strip():
                raise EvidenceProcessingError(f"Text file '{filename}' contains only whitespace.")

            extracted = self.extractor.process(text, evidence_id=evidence_id, filename=filename)
            return {
                "raw_text": extracted.get("raw_text", text)[:10000],
                "entities": extracted.get("entities", []),
                "relations": extracted.get("relations", []),
                "stats": {
                    "characters": len(text),
                    "lines": text.count("\n") + 1,
                    "entities_found": len(extracted.get("entities", [])),
                    "relations_found": len(extracted.get("relations", []))
                }
            }
        except EvidenceProcessingError:
            raise
        except Exception as e:
            raise EvidenceProcessingError(f"Text extraction error in '{filename}': {str(e)}")

    def _extract_csv(self, file_bytes: bytes, filename: str, evidence_id: str = "") -> Dict[str, Any]:
        """Extract entities and relationships from CSV feeds (CDR, TXN, Pings, or tabular)."""
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            if not rows:
                raise EvidenceProcessingError(f"CSV '{filename}' has no data rows.")

            fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
            entities: List[Dict[str, Any]] = []
            relations: List[Dict[str, Any]] = []
            seen_entities: set = set()

            def add_ent(name: str, etype: str, conf: float = 1.0, evid: str = "CSV Record", tier: str = "STRUCTURED_CSV"):
                name = str(name).strip()
                if not name or (name.lower(), etype.upper()) in seen_entities:
                    return
                seen_entities.add((name.lower(), etype.upper()))
                entities.append({
                    "text": name,
                    "type": etype.lower(),
                    "confidence": conf,
                    "evidence": evid,
                    "provenance": {
                        "source_evidence_id": evidence_id,
                        "source_file": filename,
                        "extraction_tier": tier,
                        "context_quote": evid,
                        "confidence": conf,
                        "extracted_at": datetime.now().isoformat(),
                    }
                })

            # Schema 1: CDR (Call Detail Records)
            if any(k in fieldnames for k in ("caller", "caller_id", "calling_num", "source_num")) and \
               any(k in fieldnames for k in ("callee", "callee_id", "called_num", "destination_num")):
                caller_key = next(k for k in reader.fieldnames if k.strip().lower() in ("caller", "caller_id", "calling_num", "source_num"))
                callee_key = next(k for k in reader.fieldnames if k.strip().lower() in ("callee", "callee_id", "called_num", "destination_num"))
                dur_key = next((k for k in reader.fieldnames if "dur" in k.strip().lower()), None)
                ts_key = next((k for k in reader.fieldnames if any(t in k.strip().lower() for t in ("ts", "time", "date"))), None)

                for r in rows:
                    c1 = r.get(caller_key, "").strip()
                    c2 = r.get(callee_key, "").strip()
                    if c1 and c2:
                        add_ent(c1, "PHONE", 0.98, f"CDR Caller in {filename}", "STRUCTURED_CSV:CDR")
                        add_ent(c2, "PHONE", 0.98, f"CDR Callee in {filename}", "STRUCTURED_CSV:CDR")
                        dur = r.get(dur_key, "") if dur_key else ""
                        ts = r.get(ts_key, "") if ts_key else ""
                        detail = f"{dur}s call at {ts}".strip() if dur else (f"Call at {ts}" if ts else "Call Record")
                        relations.append({
                            "source": c1, "source_type": "phone",
                            "target": c2, "target_type": "phone",
                            "type": "CALLED",
                            "confidence": 0.95,
                            "evidence": f"CDR: {detail}",
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_CSV:CDR",
                                "rule_name": "TELECOM_CDR_CALLED",
                                "context_quote": f"CDR: {detail}",
                                "confidence": 0.95,
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

            # Schema 2: Financial Transactions
            elif any(k in fieldnames for k in ("from_entity", "from_account", "sender", "from", "source_account")) and \
                 any(k in fieldnames for k in ("to_entity", "to_account", "receiver", "to", "dest_account")):
                from_key = next(k for k in reader.fieldnames if k.strip().lower() in ("from_entity", "from_account", "sender", "from", "source_account"))
                to_key = next(k for k in reader.fieldnames if k.strip().lower() in ("to_entity", "to_account", "receiver", "to", "dest_account"))
                amt_key = next((k for k in reader.fieldnames if "amount" in k.strip().lower() or "amt" in k.strip().lower()), None)
                mode_key = next((k for k in reader.fieldnames if "mode" in k.strip().lower() or "type" in k.strip().lower()), None)

                for r in rows:
                    f_val = r.get(from_key, "").strip()
                    t_val = r.get(to_key, "").strip()
                    if f_val and t_val:
                        add_ent(f_val, "BANK_ACCOUNT" if f_val.isdigit() and len(f_val) > 8 else "PERSON", 0.95, f"Transaction Origin in {filename}", "STRUCTURED_CSV:FINANCIAL")
                        add_ent(t_val, "BANK_ACCOUNT" if t_val.isdigit() and len(t_val) > 8 else "PERSON", 0.95, f"Transaction Beneficiary in {filename}", "STRUCTURED_CSV:FINANCIAL")
                        amt = r.get(amt_key, "") if amt_key else ""
                        mode = r.get(mode_key, "") if mode_key else ""
                        relations.append({
                            "source": f_val, "source_type": "account" if f_val.isdigit() else "person",
                            "target": t_val, "target_type": "account" if t_val.isdigit() else "person",
                            "type": "TRANSFERRED_TO",
                            "confidence": 0.97,
                            "evidence": f"Banking transfer {amt} via {mode}".strip(),
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_CSV:FINANCIAL",
                                "rule_name": "BANKING_TRANSFER",
                                "context_quote": f"Banking transfer {amt} via {mode}".strip(),
                                "confidence": 0.97,
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

            # Schema 3: Cell Tower Pings
            elif any(k in fieldnames for k in ("phone", "msisdn", "mobile")) and \
                 any(k in fieldnames for k in ("location", "tower", "cell_site", "cell_id")):
                p_key = next(k for k in reader.fieldnames if k.strip().lower() in ("phone", "msisdn", "mobile"))
                loc_key = next(k for k in reader.fieldnames if k.strip().lower() in ("location", "tower", "cell_site", "cell_id"))

                for r in rows:
                    pval = r.get(p_key, "").strip()
                    lval = r.get(loc_key, "").strip()
                    if pval and lval:
                        add_ent(pval, "PHONE", 0.95, f"Cell Ping Phone in {filename}", "STRUCTURED_CSV:CELL_TOWER")
                        add_ent(lval, "LOCATION", 0.90, f"Cell Site Location in {filename}", "STRUCTURED_CSV:CELL_TOWER")
                        relations.append({
                            "source": pval, "source_type": "phone",
                            "target": lval, "target_type": "location",
                            "type": "PINGED_AT",
                            "confidence": 0.92,
                            "evidence": f"Cell Tower Ping at {lval}",
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_CSV:CELL_TOWER",
                                "rule_name": "CELL_TOWER_PING",
                                "context_quote": f"Cell Tower Ping at {lval}",
                                "confidence": 0.92,
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

            # Schema 4: Generic / Unstructured Free Text Column in CSV
            else:
                text_col = next((k for k in reader.fieldnames if any(w in k.strip().lower() for w in ("text", "description", "statement", "notes", "narrative", "details", "fir"))), None)
                if text_col:
                    combined_text = "\n".join(r.get(text_col, "") for r in rows[:100] if r.get(text_col, "").strip())
                    nlp_res = self.extractor.process(combined_text, evidence_id=evidence_id, filename=filename)
                    entities = nlp_res.get("entities", [])
                    relations = nlp_res.get("relations", [])
                else:
                    # Generic entity pairs (source, target, relationship)
                    s_key = next((k for k in reader.fieldnames if "source" in k.strip().lower()), None)
                    t_key = next((k for k in reader.fieldnames if "target" in k.strip().lower()), None)
                    r_key = next((k for k in reader.fieldnames if any(w in k.strip().lower() for w in ("rel", "type", "link"))), None)
                    if s_key and t_key:
                        for r in rows:
                            s = r.get(s_key, "").strip()
                            t = r.get(t_key, "").strip()
                            rel = r.get(r_key, "ASSOCIATE_OF").strip() if r_key else "ASSOCIATE_OF"
                            if s and t:
                                add_ent(s, "PERSON", 0.9, f"CSV Source in {filename}", "STRUCTURED_CSV:PAIR")
                                add_ent(t, "PERSON", 0.9, f"CSV Target in {filename}", "STRUCTURED_CSV:PAIR")
                                relations.append({
                                    "source": s, "source_type": "person",
                                    "target": t, "target_type": "person",
                                    "type": rel,
                                    "confidence": 0.9,
                                    "evidence": f"CSV Link: {rel}",
                                    "provenance": {
                                        "source_evidence_id": evidence_id,
                                        "source_file": filename,
                                        "extraction_tier": "STRUCTURED_CSV:PAIR",
                                        "rule_name": "CSV_EXPLICIT_LINK",
                                        "context_quote": f"CSV Link: {rel}",
                                        "confidence": 0.9,
                                        "extracted_at": datetime.now().isoformat(),
                                    }
                                })

            return {
                "raw_text": f"CSV Dataset: {len(rows)} rows, columns: {list(reader.fieldnames or [])}",
                "entities": entities,
                "relations": relations,
                "stats": {
                    "rows": len(rows),
                    "columns": len(reader.fieldnames or []),
                    "entities_found": len(entities),
                    "relations_found": len(relations)
                }
            }
        except EvidenceProcessingError:
            raise
        except Exception as e:
            raise EvidenceProcessingError(f"CSV extraction failed for '{filename}': {str(e)}")

    def _extract_json(self, file_bytes: bytes, filename: str, evidence_id: str = "") -> Dict[str, Any]:
        """Extract entities and relations from structured JSON feeds or graph dumps."""
        try:
            data = json.loads(file_bytes.decode("utf-8"))
            entities: List[Dict[str, Any]] = []
            relations: List[Dict[str, Any]] = []

            # Format 1: Direct entities & relations format
            if isinstance(data, dict) and ("entities" in data or "relations" in data):
                for e in data.get("entities", []):
                    name = e.get("name") or e.get("text") or e.get("id")
                    if name:
                        entities.append({
                            "text": str(name),
                            "type": str(e.get("type", "PERSON")).lower(),
                            "confidence": float(e.get("confidence", 1.0)),
                            "evidence": str(e.get("evidence", f"JSON entity in {filename}")),
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_JSON:ENTITIES",
                                "context_quote": str(e.get("evidence", f"JSON entity in {filename}")),
                                "confidence": float(e.get("confidence", 1.0)),
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })
                for r in data.get("relations", []):
                    src = r.get("source") or r.get("from")
                    tgt = r.get("target") or r.get("to")
                    rtype = r.get("type") or r.get("relationship") or "ASSOCIATE_OF"
                    if src and tgt:
                        relations.append({
                            "source": str(src),
                            "source_type": str(r.get("source_type", "person")).lower(),
                            "target": str(tgt),
                            "target_type": str(r.get("target_type", "person")).lower(),
                            "type": str(rtype),
                            "confidence": float(r.get("confidence", 1.0)),
                            "evidence": str(r.get("evidence", f"JSON relation in {filename}")),
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_JSON:RELATIONS",
                                "rule_name": "JSON_EXPLICIT_RELATION",
                                "context_quote": str(r.get("evidence", f"JSON relation in {filename}")),
                                "confidence": float(r.get("confidence", 1.0)),
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

            # Format 2: Cytoscape elements format {"nodes": [...], "edges": [...]} or elements list
            elif isinstance(data, dict) and ("nodes" in data or "elements" in data or "edges" in data):
                nodes = data.get("nodes", [])
                edges = data.get("edges", [])
                if "elements" in data and isinstance(data["elements"], list):
                    nodes = [el for el in data["elements"] if el.get("group") == "nodes"]
                    edges = [el for el in data["elements"] if el.get("group") == "edges"]

                for n in nodes:
                    nd = n.get("data", n)
                    name = nd.get("label") or nd.get("name") or nd.get("id")
                    ntype = nd.get("type") or nd.get("entity_type") or "PERSON"
                    if name:
                        entities.append({
                            "text": str(name),
                            "type": str(ntype).lower(),
                            "confidence": 1.0,
                            "evidence": f"Cytoscape Node #{nd.get('id', '')}",
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_JSON:CYTOSCAPE",
                                "context_quote": f"Cytoscape Node #{nd.get('id', '')}",
                                "confidence": 1.0,
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

                for ed in edges:
                    edd = ed.get("data", ed)
                    src = edd.get("source")
                    tgt = edd.get("target")
                    rtype = edd.get("label") or edd.get("type") or "LINKED_TO"
                    if src and tgt:
                        relations.append({
                            "source": str(src),
                            "source_type": "person",
                            "target": str(tgt),
                            "target_type": "person",
                            "type": str(rtype),
                            "confidence": float(edd.get("confidence", 1.0)),
                            "evidence": f"Cytoscape Edge #{edd.get('id', '')}",
                            "provenance": {
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "extraction_tier": "STRUCTURED_JSON:CYTOSCAPE",
                                "rule_name": "CYTOSCAPE_GRAPH_EDGE",
                                "context_quote": f"Cytoscape Edge #{edd.get('id', '')}",
                                "confidence": float(edd.get("confidence", 1.0)),
                                "extracted_at": datetime.now().isoformat(),
                            }
                        })

            # Format 3: Array of records or narrative text
            elif isinstance(data, list):
                # Text check
                texts = [item for item in data if isinstance(item, str)]
                if texts:
                    nlp_res = self.extractor.process("\n".join(texts[:50]), evidence_id=evidence_id, filename=filename)
                    entities = nlp_res.get("entities", [])
                    relations = nlp_res.get("relations", [])
                else:
                    # Check objects for person/phone/target fields
                    for item in data[:200]:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if any(sub in k.lower() for sub in ("phone", "mobile", "tel")):
                                    entities.append({
                                        "text": str(v), "type": "phone", "confidence": 0.95, "evidence": f"JSON field {k}",
                                        "provenance": {
                                            "source_evidence_id": evidence_id, "source_file": filename,
                                            "extraction_tier": "STRUCTURED_JSON:FIELD", "context_quote": f"JSON field {k}: {v}",
                                            "confidence": 0.95, "extracted_at": datetime.now().isoformat()
                                        }
                                    })
                                elif any(sub in k.lower() for sub in ("name", "suspect", "accused", "person")):
                                    entities.append({
                                        "text": str(v), "type": "person", "confidence": 0.9, "evidence": f"JSON field {k}",
                                        "provenance": {
                                            "source_evidence_id": evidence_id, "source_file": filename,
                                            "extraction_tier": "STRUCTURED_JSON:FIELD", "context_quote": f"JSON field {k}: {v}",
                                            "confidence": 0.9, "extracted_at": datetime.now().isoformat()
                                        }
                                    })
                                elif any(sub in k.lower() for sub in ("vehicle", "plate", "car")):
                                    entities.append({
                                        "text": str(v), "type": "vehicle", "confidence": 0.9, "evidence": f"JSON field {k}",
                                        "provenance": {
                                            "source_evidence_id": evidence_id, "source_file": filename,
                                            "extraction_tier": "STRUCTURED_JSON:FIELD", "context_quote": f"JSON field {k}: {v}",
                                            "confidence": 0.9, "extracted_at": datetime.now().isoformat()
                                        }
                                    })
            else:
                # Top level dict with text or attributes
                text_dump = json.dumps(data, indent=2)
                nlp_res = self.extractor.process(text_dump[:10000], evidence_id=evidence_id, filename=filename)
                entities = nlp_res.get("entities", [])
                relations = nlp_res.get("relations", [])

            return {
                "raw_text": json.dumps(data)[:10000],
                "entities": entities,
                "relations": relations,
                "stats": {
                    "entities_found": len(entities),
                    "relations_found": len(relations)
                }
            }
        except EvidenceProcessingError:
            raise
        except Exception as e:
            raise EvidenceProcessingError(f"JSON extraction failed for '{filename}': {str(e)}")

    # ----------------------------------------------------------------------- #
    # PIPELINE STAGES: ANALYZE & LINK TO INVESTIGATION GRAPH
    # ----------------------------------------------------------------------- #
    def analyze_extracted_data(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Produce forensic analytics and distribution metrics on extracted intelligence."""
        ents = extracted.get("entities", [])
        rels = extracted.get("relations", [])

        type_counts: Dict[str, int] = {}
        for e in ents:
            t = e.get("type", "unknown").upper()
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_counts: Dict[str, int] = {}
        for r in rels:
            rt = r.get("type", "LINKED_TO").upper()
            rel_counts[rt] = rel_counts.get(rt, 0) + 1

        return {
            "entity_breakdown": type_counts,
            "relationship_breakdown": rel_counts,
            "total_entities": len(ents),
            "total_relations": len(rels),
            "density_ratio": round(len(rels) / max(len(ents), 1), 3),
            "analyzed_at": datetime.now().isoformat()
        }

    def link_to_investigation_graph(
        self,
        case_id: str,
        evidence_id: str,
        extracted: Dict[str, Any],
        user_id: str = "u-002"
    ) -> Tuple[int, int]:
        """Inject extracted entities and relationships directly into MySQL investigation tables."""
        ents = extracted.get("entities", [])
        rels = extracted.get("relations", [])

        # Map entity text/name -> database UUID in investigation_entities
        name_to_id: Dict[str, str] = {}
        entities_created = 0
        relationships_created = 0

        for ent in ents:
            name = ent.get("text", "").strip()
            etype = ent.get("type", "PERSON").upper()
            if not name:
                continue

            provenance = ent.get("provenance", {})
            props = {
                "confidence": ent.get("confidence", 1.0),
                "evidence_id": evidence_id,
                "evidence_quote": ent.get("evidence", ""),
                "normalized_text": ent.get("normalized_text", name),
                "extraction_tier": provenance.get("extraction_tier", "UNKNOWN"),
                "provenance": provenance,
                "linked_at": datetime.now().isoformat()
            }
            ent_id = self.svc.link_entity_to_case(
                case_id=case_id,
                name=name,
                entity_type=etype,
                properties=props,
                source_text=ent.get("evidence", ""),
                added_by=user_id
            )
            name_to_id[name.lower()] = ent_id
            entities_created += 1

        for rel in rels:
            src_name = rel.get("source", "").strip()
            tgt_name = rel.get("target", "").strip()
            rtype = rel.get("type", "ASSOCIATE_OF").upper()
            conf = float(rel.get("confidence", 1.0))
            if not src_name or not tgt_name:
                continue

            # Ensure both endpoints exist in investigation_entities
            src_id = name_to_id.get(src_name.lower())
            if not src_id:
                src_id = self.svc.link_entity_to_case(
                    case_id=case_id,
                    name=src_name,
                    entity_type=rel.get("source_type", "PERSON").upper(),
                    properties={"evidence_id": evidence_id},
                    added_by=user_id
                )
                name_to_id[src_name.lower()] = src_id

            tgt_id = name_to_id.get(tgt_name.lower())
            if not tgt_id:
                tgt_id = self.svc.link_entity_to_case(
                    case_id=case_id,
                    name=tgt_name,
                    entity_type=rel.get("target_type", "PERSON").upper(),
                    properties={"evidence_id": evidence_id},
                    added_by=user_id
                )
                name_to_id[tgt_name.lower()] = tgt_id

            rel_prov = rel.get("provenance", {})
            rel_props = {
                "evidence_id": evidence_id,
                "evidence_quote": rel.get("evidence", ""),
                "confidence": conf,
                "rule_name": rel_prov.get("rule_name", "UNKNOWN"),
                "extraction_tier": rel_prov.get("extraction_tier", "UNKNOWN"),
                "provenance": rel_prov,
            }
            is_predicted = (rtype == "POTENTIAL_ALIAS" or conf < 0.70)
            self.svc.link_relationship_to_case(
                case_id=case_id,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relationship_type=rtype,
                confidence=conf,
                properties=rel_props,
                predicted=is_predicted
            )
            relationships_created += 1

        return entities_created, relationships_created

    # ----------------------------------------------------------------------- #
    # MASTER PIPELINE EXECUTION
    # ----------------------------------------------------------------------- #
    def process_evidence_pipeline(
        self,
        case_id: str,
        filename: str,
        file_bytes: bytes,
        declared_type: Optional[str] = None,
        title: Optional[str] = None,
        source_ref: Optional[str] = None,
        description: Optional[str] = None,
        user_id: str = "u-002"
    ) -> Dict[str, Any]:
        """Execute the complete 7-stage evidence pipeline.
        
        Case
        -> Evidence
        -> Upload
        -> Validate
        -> Store metadata
        -> Process
        -> Extract
        -> Analyze
        -> Link to investigation graph
        
        Statuses: Uploaded, Processing, Processed, Failed.
        Accurately reports real errors without faking success.
        """
        # Stage 1: Upload received & determine parameters
        evidence_title = title.strip() if title and title.strip() else os.path.basename(filename)
        sha256 = self.compute_sha256(file_bytes)

        # Stage 2: Validate
        try:
            file_type = self.detect_file_type(filename, declared_type)
            self.validate_evidence(filename, file_bytes, file_type)
        except Exception as val_err:
            real_err = str(val_err)
            # Store initial failed metadata
            ev_id = self.svc.add_evidence(
                case_id=case_id,
                title=evidence_title,
                evidence_type=declared_type or "UNKNOWN",
                source_ref=source_ref,
                sha256_hash=sha256,
                filename=filename,
                processing_status="Failed",
                extraction_status="Failed",
                description=description,
                error_message=real_err,
                entity_count=0,
                relation_count=0,
                metadata={"validation_error": real_err, "file_size": len(file_bytes)}
            )
            self.svc.log_audit(
                case_id=case_id,
                action="EVIDENCE_VALIDATION_FAILED",
                username="Investigator",
                details=f"Evidence validation failed for '{filename}': {real_err}"
            )
            return {
                "success": False,
                "evidence_id": ev_id,
                "status": "Failed",
                "stage": "Validate",
                "error": real_err,
                "filename": filename,
                "sha256": sha256
            }

        # Stage 3: Store initial metadata (status: Processing)
        ev_id = self.svc.add_evidence(
            case_id=case_id,
            title=evidence_title,
            evidence_type=file_type,
            source_ref=source_ref or f"Exhibit: {filename}",
            sha256_hash=sha256,
            filename=filename,
            processing_status="Processing",
            extraction_status="Pending",
            description=description,
            error_message=None,
            metadata={"file_size": len(file_bytes), "upload_time": datetime.now().isoformat()}
        )

        # Stage 4 & 5: Process file & Extract entities + relations
        try:
            if file_type == "PDF":
                extracted = self._extract_pdf(file_bytes, filename, evidence_id=ev_id)
            elif file_type == "TXT":
                extracted = self._extract_txt(file_bytes, filename, evidence_id=ev_id)
            elif file_type == "CSV":
                extracted = self._extract_csv(file_bytes, filename, evidence_id=ev_id)
            elif file_type == "JSON":
                extracted = self._extract_json(file_bytes, filename, evidence_id=ev_id)
            else:
                raise EvidenceProcessingError(f"Unsupported processor for type {file_type}")
        except Exception as proc_err:
            real_err = str(proc_err)
            self.svc.update_evidence(
                ev_id,
                processing_status="Failed",
                extraction_status="Failed",
                error_message=real_err
            )
            self.svc.log_audit(
                case_id=case_id,
                action="EVIDENCE_PROCESSING_FAILED",
                username="Investigator",
                details=f"Processing failed for evidence #{ev_id[:8]} ({filename}): {real_err}"
            )
            return {
                "success": False,
                "evidence_id": ev_id,
                "status": "Failed",
                "stage": "Process/Extract",
                "error": real_err,
                "filename": filename,
                "sha256": sha256
            }

        # Stage 6: Analyze
        try:
            analysis_meta = self.analyze_extracted_data(extracted)
        except Exception as ana_err:
            analysis_meta = {"analysis_error": str(ana_err)}

        # Stage 7: Link to investigation graph
        try:
            ents_count, rels_count = self.link_to_investigation_graph(
                case_id=case_id,
                evidence_id=ev_id,
                extracted=extracted,
                user_id=user_id
            )
        except Exception as link_err:
            real_err = f"Failed to link entities to investigation graph: {str(link_err)}"
            self.svc.update_evidence(
                ev_id,
                processing_status="Failed",
                extraction_status="Failed",
                error_message=real_err
            )
            return {
                "success": False,
                "evidence_id": ev_id,
                "status": "Failed",
                "stage": "Link to Graph",
                "error": real_err,
                "filename": filename,
                "sha256": sha256
            }

        # Stage 7b: Index into Microsoft GraphRAG (for unstructured evidence understanding & Q&A)
        graphrag_meta = {}
        raw_text_content = extracted.get("raw_text", "")
        if raw_text_content and len(raw_text_content.strip()) > 20:
            try:
                from storage.crimenet_graphrag import CrimeNetGraphRAG
                rag = CrimeNetGraphRAG(case_id=case_id)
                rag.add_evidence_document(
                    doc_id=ev_id,
                    filename=filename,
                    content=raw_text_content,
                    metadata={"evidence_id": ev_id, "title": evidence_title, "file_type": file_type}
                )
                graphrag_stats = rag.build_index(extractor=self.extractor)
                graphrag_meta = {
                    "indexed": True,
                    "entities": graphrag_stats.get("entity_count", 0),
                    "reports": graphrag_stats.get("report_count", 0),
                }
            except Exception as gr_err:
                graphrag_meta = {"indexed": False, "error": str(gr_err)}

        # Stage 8: Transition to Processed
        extraction_status = "Extracted" if ents_count > 0 or rels_count > 0 else "No Entities Found"
        full_metadata = {
            "file_size": len(file_bytes),
            "sha256": sha256,
            "analysis": analysis_meta,
            "stats": extracted.get("stats", {}),
            "graphrag": graphrag_meta,
            "processed_at": datetime.now().isoformat()
        }

        self.svc.update_evidence(
            ev_id,
            content=extracted.get("raw_text", "")[:10000],
            processing_status="Processed",
            extraction_status=extraction_status,
            error_message=None,
            entity_count=ents_count,
            relation_count=rels_count,
            metadata=full_metadata
        )

        self.svc.log_audit(
            case_id=case_id,
            action="EVIDENCE_PROCESSED_AND_LINKED",
            username="Investigator",
            details=f"Exhibit '{filename}' processed ({file_type}): {ents_count} entities, {rels_count} links linked to graph."
        )

        return {
            "success": True,
            "evidence_id": ev_id,
            "status": "Processed",
            "extraction_status": extraction_status,
            "filename": filename,
            "file_type": file_type,
            "graphrag": graphrag_meta,
            "sha256": sha256,
            "entities_count": ents_count,
            "relations_count": rels_count,
            "analysis": analysis_meta,
            "entities_sample": extracted.get("entities", [])[:10]
        }
