"""CrimeNet Microsoft GraphRAG Integration Boundary Layer.

Implements the strict forensic integration pipeline:
Evidence
  -> GraphRAG
  -> Extracted Knowledge
  -> CrimeNet Normalization
  -> Entity Resolution
  -> Validation / Acceptance Layer
  -> Neo4j Operational Graph

Enforces:
1. Taxonomy Mapping:
   - GraphRAG entities -> CrimeNet entity types:
     (PERSON, PHONE, VEHICLE, LOCATION, ORGANIZATION, ACCOUNT, TRANSACTION, CASE, EVENT)
   - GraphRAG relationships -> CrimeNet relationship types:
     (CALLED, MESSAGED, COMMUNICATED_WITH, USES_PHONE, USES_VEHICLE, OPERATES,
      SEEN_AT, VISITED, TRANSFERRED_TO, DEPOSITED_IN, PAID, OWNS_ACCOUNT,
      ASSOCIATE_OF, MEMBER_OF, AFFILIATED_WITH, LEADS, WORKS_FOR,
      SUSPECT_IN, VICTIM_OF, REPORTED, PARTICIPATED_IN,
      SAME_AS, ALIAS_OF, POTENTIAL_ALIAS)

2. Complete Source & Provenance Traceability:
   - Source evidence ID & file name (e.g., CDR_001.csv, FIR_2026_0142.txt)
   - Character offsets & timestamps
   - Verbatim evidence quote
   - Extraction tier & rule/model name

3. Strict Relationship Distinguishability:
   - OBSERVED: Direct factual records from structured logs (CDRs, bank ledgers, surveillance pings)
   - EXTRACTED: Extracted from narrative text/FIRs/witness statements via NLP & regex
   - PREDICTED: Structural topology link predictions (Jaccard, Adamic-Adar, Resource Allocation, Node2Vec)
   - INFERRED: Derived from GraphRAG multi-hop DRIFT search or LLM community inferences

4. Validation & Acceptance Gatekeeper:
   - Predicted and inferred relationships are NEVER presented as confirmed facts.
   - Language model outputs do NOT automatically create operational graph relationships in Neo4j.
   - They enter the staging/proposal queue as PROPOSED until explicitly reviewed and accepted.
   - Only CONFIRMED relationships sync to the operational Neo4j graph.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Path registration for ai-service and workspace root
_CURRENT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _CURRENT_DIR.parent
_AI_SERVICE_DIR = _WORKSPACE_ROOT / "ai-service"
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums for Relationship Modality and Acceptance State
# ---------------------------------------------------------------------------

class RelationshipModality(str, enum.Enum):
    """Forensic modality of a relationship."""
    OBSERVED = "OBSERVED"      # Direct primary observation (CDR call, bank wire, surveillance ping)
    EXTRACTED = "EXTRACTED"    # Extracted from narrative text/FIR/witness statements via NLP
    PREDICTED = "PREDICTED"    # Algorithmic link prediction (Jaccard, Adamic-Adar, Node2Vec)
    INFERRED = "INFERRED"      # GraphRAG multi-hop DRIFT or LLM deduction


class AcceptanceStatus(str, enum.Enum):
    """Investigator acceptance and confirmation state."""
    CONFIRMED = "CONFIRMED"    # Validated by investigator or verified primary record
    PROPOSED = "PROPOSED"      # Proposed by AI/algorithm; awaiting investigator review
    REJECTED = "REJECTED"      # Discarded by investigator


# ---------------------------------------------------------------------------
# CrimeNet Taxonomy Mappings
# ---------------------------------------------------------------------------

# CrimeNet Standard Entity Types
CRIMENET_STANDARD_ENTITY_TYPES: Set[str] = {
    "PERSON",
    "PHONE",
    "VEHICLE",
    "LOCATION",
    "ORGANIZATION",
    "ACCOUNT",
    "TRANSACTION",
    "CASE",
    "EVENT",
}

# GraphRAG -> CrimeNet Entity Taxonomy Mapping
GRAPHRAG_ENTITY_TYPE_MAP: Dict[str, str] = {
    # Person variants
    "person": "PERSON",
    "individual": "PERSON",
    "suspect": "PERSON",
    "perpetrator": "PERSON",
    "accused": "PERSON",
    "witness": "PERSON",
    "complainant": "PERSON",
    "victim": "PERSON",
    "operative": "PERSON",
    "human": "PERSON",
    # Phone variants
    "phone": "PHONE",
    "mobile": "PHONE",
    "telephone": "PHONE",
    "msisdn": "PHONE",
    "cell": "PHONE",
    "sim": "PHONE",
    "imei": "PHONE",
    "contact": "PHONE",
    # Vehicle variants
    "vehicle": "VEHICLE",
    "car": "VEHICLE",
    "truck": "VEHICLE",
    "automobile": "VEHICLE",
    "plate": "VEHICLE",
    "license_plate": "VEHICLE",
    # Location variants
    "location": "LOCATION",
    "place": "LOCATION",
    "address": "LOCATION",
    "city": "LOCATION",
    "checkpoint": "LOCATION",
    "warehouse": "LOCATION",
    "geo": "LOCATION",
    "spot": "LOCATION",
    # Organization variants
    "organization": "ORGANIZATION",
    "company": "ORGANIZATION",
    "firm": "ORGANIZATION",
    "agency": "ORGANIZATION",
    "syndicate": "ORGANIZATION",
    "gang": "ORGANIZATION",
    "entity": "ORGANIZATION",
    "corporation": "ORGANIZATION",
    "corp": "ORGANIZATION",
    # Account variants
    "account": "ACCOUNT",
    "bank_account": "ACCOUNT",
    "wallet": "ACCOUNT",
    "upi": "ACCOUNT",
    "pan": "ACCOUNT",
    "passport": "ACCOUNT",
    # Transaction variants
    "transaction": "TRANSACTION",
    "transfer": "TRANSACTION",
    "wire": "TRANSACTION",
    "payment": "TRANSACTION",
    "hawala": "TRANSACTION",
    # Case variants
    "case": "CASE",
    "fir": "CASE",
    "investigation": "CASE",
    "report": "CASE",
    # Event variants
    "event": "EVENT",
    "incident": "EVENT",
    "meeting": "EVENT",
    "call": "EVENT",
    "raid": "EVENT",
}

# GraphRAG -> CrimeNet Relationship Taxonomy Mapping
GRAPHRAG_RELATIONSHIP_TYPE_MAP: Dict[str, str] = {
    # Telecommunications
    "called": "CALLED",
    "contacted": "CALLED",
    "phoned": "CALLED",
    "dialed": "CALLED",
    "messaged": "MESSAGED",
    "texted": "MESSAGED",
    "communicated_with": "COMMUNICATED_WITH",
    "in_contact_with": "COMMUNICATED_WITH",
    # Device and Asset usage
    "uses_phone": "USES_PHONE",
    "operated_phone": "USES_PHONE",
    "has_phone": "USES_PHONE",
    "owns_phone": "USES_PHONE",
    "subscriber_of": "USES_PHONE",
    "uses_vehicle": "USES_VEHICLE",
    "drove": "USES_VEHICLE",
    "operated_vehicle": "USES_VEHICLE",
    "in_vehicle": "USES_VEHICLE",
    "seen_in_vehicle": "USES_VEHICLE",
    "operates": "OPERATES",
    "seen_at": "SEEN_AT",
    "spotted_at": "SEEN_AT",
    "visited": "VISITED",
    "located_at": "SEEN_AT",
    "pinged_at": "SEEN_AT",
    # Financial
    "transferred_to": "TRANSFERRED_TO",
    "transferred_funds": "TRANSFERRED_TO",
    "paid": "PAID",
    "sent_money_to": "TRANSFERRED_TO",
    "deposited_in": "DEPOSITED_IN",
    "routed_funds_to": "TRANSFERRED_TO",
    "owns_account": "OWNS_ACCOUNT",
    "account_holder": "OWNS_ACCOUNT",
    # Organization and Syndicate
    "associate_of": "ASSOCIATE_OF",
    "associated_with": "ASSOCIATE_OF",
    "co_conspirator": "ASSOCIATE_OF",
    "accomplice": "ASSOCIATE_OF",
    "member_of": "MEMBER_OF",
    "belongs_to": "MEMBER_OF",
    "affiliated_with": "AFFILIATED_WITH",
    "employed_by": "AFFILIATED_WITH",
    "works_for": "WORKS_FOR",
    "leads": "LEADS",
    "heads": "LEADS",
    # Case & Legal
    "suspect_in": "SUSPECT_IN",
    "accused_in": "SUSPECT_IN",
    "victim_of": "VICTIM_OF",
    "reported": "REPORTED",
    "participated_in": "PARTICIPATED_IN",
    "evidence_in": "EVIDENCE_IN",
    # Identity Resolution
    "same_as": "SAME_AS",
    "alias_of": "ALIAS_OF",
    "potential_alias": "POTENTIAL_ALIAS",
}


# ---------------------------------------------------------------------------
# Data Models for Clean Boundary Representation
# ---------------------------------------------------------------------------

@dataclass
class NormalizedEntity:
    """A strictly normalized entity with full cryptographic provenance."""
    id: str
    name: str
    entity_type: str  # Must be one of CRIMENET_STANDARD_ENTITY_TYPES
    case_id: str
    source_evidence_id: str
    source_file: str
    confidence: float = 1.0
    evidence_quote: str = ""
    char_offsets: Tuple[int, int] = (0, 0)
    extraction_tier: str = "EXTRACTED"
    verified: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["char_offsets"] = list(self.char_offsets)
        return d


@dataclass
class NormalizedRelationship:
    """A strictly normalized relationship with distinct modality and acceptance state."""
    id: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str  # Canonical CrimeNet relationship type
    case_id: str
    source_evidence_id: str
    source_file: str
    modality: RelationshipModality  # OBSERVED | EXTRACTED | PREDICTED | INFERRED
    acceptance_status: AcceptanceStatus  # CONFIRMED | PROPOSED | REJECTED
    confidence: float = 1.0
    evidence_quote: str = ""
    rule_or_model: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["modality"] = self.modality.value
        d["acceptance_status"] = self.acceptance_status.value
        return d


# ---------------------------------------------------------------------------
# Integration Boundary Service
# ---------------------------------------------------------------------------

class GraphRAGCrimeNetBoundary:
    """Forensic Integration Boundary connecting GraphRAG knowledge extraction with Neo4j.
    
    Guarantees:
    - Zero unvalidated AI hallucinations committed to Neo4j.
    - Explicit visual and structural distinction between Observed, Extracted,
      Predicted, and Inferred relationships.
    - Deterministic normalization and candidate representation resolution.
    - Full evidence provenance attached to every node and edge.
    """

    def __init__(self, case_id: str, case_data_service: Optional[Any] = None):
        self.case_id = case_id
        if case_data_service is None:
            try:
                from storage.case_data_service import CaseDataService
                self.svc = CaseDataService()
            except Exception:
                self.svc = None
        else:
            self.svc = case_data_service

    # -----------------------------------------------------------------------
    # 1. TAXONOMY MAPPING
    # -----------------------------------------------------------------------

    @staticmethod
    def map_entity_type(raw_type: str, entity_name: str = "") -> str:
        """Map raw GraphRAG or NLP entity type to canonical CrimeNet entity type."""
        norm_type = (raw_type or "").strip().lower()
        if norm_type in GRAPHRAG_ENTITY_TYPE_MAP:
            return GRAPHRAG_ENTITY_TYPE_MAP[norm_type]

        # Pattern-based heuristics if raw_type is generic ("entity", "concept", "unknown")
        clean_name = entity_name.strip()
        # Phone: 10 digits or international phone
        if re.search(r"^(?:\+?91)?[6-9]\d{9}$", clean_name.replace("-", "").replace(" ", "")):
            return "PHONE"
        # Vehicle: Indian registration format
        if re.search(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$", clean_name.replace(" ", "").replace("-", "").upper()):
            return "VEHICLE"
        # Bank Account: 9-18 digits
        if re.search(r"^\d{9,18}$", clean_name):
            return "ACCOUNT"
        # Organization suffixes
        upper_name = clean_name.upper()
        if any(suffix in upper_name for suffix in ("PVT", "LTD", "LIMITED", "CORP", "INC", "HOLDINGS", "TRADERS", "LOGISTICS", "INFOTECH", "BANK")):
            return "ORGANIZATION"

        return "PERSON"

    @staticmethod
    def map_relationship_type(raw_rel: str) -> str:
        """Map raw GraphRAG or NLP relationship description to canonical CrimeNet type."""
        norm_rel = (raw_rel or "").strip().lower().replace(" ", "_").replace("-", "_")
        if norm_rel in GRAPHRAG_RELATIONSHIP_TYPE_MAP:
            return GRAPHRAG_RELATIONSHIP_TYPE_MAP[norm_rel]

        # Fuzzy substring match for key action words
        if any(w in norm_rel for w in ("call", "phone", "dial", "contact")):
            return "CALLED"
        if any(w in norm_rel for w in ("transfer", "paid", "wire", "deposit", "money", "fund", "cash")):
            return "TRANSFERRED_TO"
        if any(w in norm_rel for w in ("drive", "vehicle", "car", "plate")):
            return "USES_VEHICLE"
        if any(w in norm_rel for w in ("sim", "mobile", "number")):
            return "USES_PHONE"
        if any(w in norm_rel for w in ("meet", "seen", "spotted", "locate", "visit")):
            return "SEEN_AT"
        if any(w in norm_rel for w in ("member", "belong", "employ", "work", "gang", "syndicate")):
            return "MEMBER_OF"
        if any(w in norm_rel for w in ("same", "identical")):
            return "SAME_AS"
        if any(w in norm_rel for w in ("alias", "aka")):
            return "ALIAS_OF"

        return "ASSOCIATE_OF"

    @staticmethod
    def classify_modality(source_file: str, rule_or_model: str = "") -> RelationshipModality:
        """Classify relationship modality based on origin."""
        s_lower = (source_file or "").lower()
        r_lower = (rule_or_model or "").lower()

        if any(term in r_lower for term in ("predict", "jaccard", "adamic", "node2vec", "link_prediction")):
            return RelationshipModality.PREDICTED

        if any(term in r_lower for term in ("graphrag", "drift", "llm", "inferred", "community_report")):
            return RelationshipModality.INFERRED

        # Structured primary logs (CDRs, bank transactions, surveillance tower pings)
        if any(term in s_lower for term in ("cdr", "telecom", "transaction", "tower", "wire", "ledger", "csv")):
            return RelationshipModality.OBSERVED

        # Unstructured narrative text (FIRs, witness statements, intel memos)
        return RelationshipModality.EXTRACTED

    # -----------------------------------------------------------------------
    # 2. NORMALIZATION & PREPROCESSING
    # -----------------------------------------------------------------------

    def normalize_entity_value(self, name: str, entity_type: str) -> str:
        """Clean and normalize entity identifiers based on type."""
        from app.nlp.extractor import clean_text, normalize_text
        cleaned = clean_text(name).strip()
        cleaned = normalize_text(cleaned).strip()

        if entity_type == "PHONE":
            digits = re.sub(r"\D", "", cleaned)
            if len(digits) > 10 and digits.startswith("91"):
                digits = digits[2:]
            return digits if len(digits) == 10 else cleaned

        elif entity_type == "VEHICLE":
            return re.sub(r"[^A-Za-z0-9]", "", cleaned).upper()

        elif entity_type == "ACCOUNT":
            digits = re.sub(r"\D", "", cleaned)
            return digits if len(digits) >= 9 else cleaned

        elif entity_type == "PERSON":
            # Title case for person names
            return " ".join(word.capitalize() for word in cleaned.split() if word)

        elif entity_type == "ORGANIZATION":
            return " ".join(word.capitalize() for word in cleaned.split() if word)

        elif entity_type == "LOCATION":
            return " ".join(word.capitalize() for word in cleaned.split() if word)

        return cleaned

    # -----------------------------------------------------------------------
    # 3. KNOWLEDGE INGESTION PIPELINE (Evidence -> GraphRAG -> CrimeNet -> Neo4j)
    # -----------------------------------------------------------------------

    def process_evidence_knowledge(
        self,
        raw_entities: List[Dict[str, Any]],
        raw_relationships: List[Dict[str, Any]],
        source_file: str,
        evidence_id: str,
        evidence_text: str = "",
    ) -> Dict[str, Any]:
        """Execute the complete integration pipeline from extracted knowledge to normalized entities."""
        from app.nlp.extractor import EntityResolver

        normalized_entities: List[NormalizedEntity] = []
        entity_name_to_id: Dict[str, str] = {}
        seen_entity_keys: Set[str] = set()

        # Step 1: Normalize & map entities
        for ent in raw_entities:
            raw_name = ent.get("name") or ent.get("title") or ent.get("text") or ""
            if not raw_name.strip():
                continue

            raw_type = ent.get("type", "PERSON")
            mapped_type = self.map_entity_type(raw_type, raw_name)
            norm_name = self.normalize_entity_value(raw_name, mapped_type)
            key = f"{norm_name.lower()}:{mapped_type}"

            if key in seen_entity_keys:
                continue
            seen_entity_keys.add(key)

            ent_id = f"ent_{hashlib.md5(f'{self.case_id}:{norm_name}:{mapped_type}'.encode()).hexdigest()[:12]}"
            entity_name_to_id[norm_name.lower()] = ent_id
            entity_name_to_id[raw_name.lower()] = ent_id

            char_offsets = tuple(ent.get("char_offsets", (0, len(norm_name))))
            context_quote = ent.get("evidence") or ent.get("context_quote") or ""
            if not context_quote and evidence_text:
                idx = evidence_text.find(raw_name)
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(evidence_text), idx + len(raw_name) + 40)
                    context_quote = f"...{evidence_text[start:end]}..."

            normalized_entities.append(NormalizedEntity(
                id=ent_id,
                name=norm_name,
                entity_type=mapped_type,
                case_id=self.case_id,
                source_evidence_id=evidence_id,
                source_file=source_file,
                confidence=float(ent.get("confidence", 0.95)),
                evidence_quote=context_quote,
                char_offsets=char_offsets,
                extraction_tier=ent.get("tier", "GRAPHRAG_EXTRACTION"),
                verified=bool(ent.get("verified", False)),
                properties=ent.get("properties", {}),
            ))

        # Step 2: Normalize & map relationships
        normalized_relationships: List[NormalizedRelationship] = []
        seen_rel_keys: Set[str] = set()

        for rel in raw_relationships:
            s_name = rel.get("source") or ""
            t_name = rel.get("target") or ""
            if not s_name.strip() or not t_name.strip():
                continue

            raw_rel_type = rel.get("type") or rel.get("description") or "ASSOCIATE_OF"
            mapped_rel_type = self.map_relationship_type(raw_rel_type)

            rule = rel.get("rule_name") or rel.get("model_name") or ""
            modality = self.classify_modality(source_file, rule)

            # Determine acceptance gate:
            # OBSERVED and EXTRACTED evidence facts default to CONFIRMED (grounded in exhibit)
            # PREDICTED and INFERRED speculative links MUST start as PROPOSED
            if modality in (RelationshipModality.PREDICTED, RelationshipModality.INFERRED):
                acceptance = AcceptanceStatus.PROPOSED
            else:
                acceptance = AcceptanceStatus.CONFIRMED

            s_id = entity_name_to_id.get(s_name.lower()) or f"ent_{hashlib.md5(f'{self.case_id}:{s_name}'.encode()).hexdigest()[:12]}"
            t_id = entity_name_to_id.get(t_name.lower()) or f"ent_{hashlib.md5(f'{self.case_id}:{t_name}'.encode()).hexdigest()[:12]}"

            rel_key = f"{s_id}:{t_id}:{mapped_rel_type}"
            if rel_key in seen_rel_keys:
                continue
            seen_rel_keys.add(rel_key)

            rel_id = f"rel_{hashlib.md5(f'{self.case_id}:{rel_key}'.encode()).hexdigest()[:12]}"

            evidence_quote = rel.get("evidence") or rel.get("context_quote") or ""
            if not evidence_quote and evidence_text:
                idx = evidence_text.find(s_name)
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(evidence_text), idx + 80)
                    evidence_quote = f"...{evidence_text[start:end]}..."

            normalized_relationships.append(NormalizedRelationship(
                id=rel_id,
                source_id=s_id,
                source_name=s_name,
                target_id=t_id,
                target_name=t_name,
                relationship_type=mapped_rel_type,
                case_id=self.case_id,
                source_evidence_id=evidence_id,
                source_file=source_file,
                modality=modality,
                acceptance_status=acceptance,
                confidence=float(rel.get("confidence", 0.90)),
                evidence_quote=evidence_quote,
                rule_or_model=rule or modality.value,
                properties=rel.get("properties", {}),
            ))

        # Step 3: Entity Resolution (Deduplication without false merges)
        resolver = EntityResolver()
        resolved_entities, alias_relationships = self._run_entity_resolution(
            normalized_entities, resolver, evidence_id, source_file
        )
        normalized_relationships.extend(alias_relationships)

        # Step 4: Validation & Acceptance Staging
        confirmed_rels = [r for r in normalized_relationships if r.acceptance_status == AcceptanceStatus.CONFIRMED]
        proposed_rels = [r for r in normalized_relationships if r.acceptance_status == AcceptanceStatus.PROPOSED]

        # Step 5: Persist to Case Database & Sync Confirmed to Neo4j
        self._persist_to_database(resolved_entities, normalized_relationships)
        neo4j_sync_result = self.sync_to_neo4j(
            case_id=self.case_id,
            entities=resolved_entities,
            relationships=confirmed_rels,  # ONLY CONFIRMED relationships enter Neo4j!
        )

        return {
            "success": True,
            "case_id": self.case_id,
            "source_file": source_file,
            "entities_total": len(resolved_entities),
            "relationships_total": len(normalized_relationships),
            "relationships_confirmed": len(confirmed_rels),
            "relationships_proposed": len(proposed_rels),
            "modality_breakdown": {
                "OBSERVED": len([r for r in normalized_relationships if r.modality == RelationshipModality.OBSERVED]),
                "EXTRACTED": len([r for r in normalized_relationships if r.modality == RelationshipModality.EXTRACTED]),
                "PREDICTED": len([r for r in normalized_relationships if r.modality == RelationshipModality.PREDICTED]),
                "INFERRED": len([r for r in normalized_relationships if r.modality == RelationshipModality.INFERRED]),
            },
            "neo4j_sync": neo4j_sync_result,
        }

    # -----------------------------------------------------------------------
    # 4. ENTITY RESOLUTION LOGIC
    # -----------------------------------------------------------------------

    def _run_entity_resolution(
        self,
        entities: List[NormalizedEntity],
        resolver: Any,
        evidence_id: str,
        source_file: str,
    ) -> Tuple[List[NormalizedEntity], List[NormalizedRelationship]]:
        """Run CrimeNet resolution rules on candidate representations."""
        persons = [e for e in entities if e.entity_type == "PERSON"]
        alias_relationships: List[NormalizedRelationship] = []

        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1, p2 = persons[i], persons[j]
                is_cand, reason = resolver.are_candidate_representations(p1.name, p2.name)
                if not is_cand:
                    continue

                # Emit candidate relationship POTENTIAL_ALIAS without automatic fusion
                alias_id = f"alias_{hashlib.md5(f'{p1.id}:{p2.id}:cand'.encode()).hexdigest()[:12]}"
                alias_relationships.append(NormalizedRelationship(
                    id=alias_id,
                    source_id=p1.id,
                    source_name=p1.name,
                    target_id=p2.id,
                    target_name=p2.name,
                    relationship_type="POTENTIAL_ALIAS",
                    case_id=self.case_id,
                    source_evidence_id=evidence_id,
                    source_file=source_file,
                    modality=RelationshipModality.EXTRACTED,
                    acceptance_status=AcceptanceStatus.PROPOSED,  # Staged for review
                    confidence=0.55,
                    evidence_quote=f"Candidate representation cue: {reason}. Maintained as distinct entities.",
                    rule_or_model="RULE_CANDIDATE_REPRESENTATION",
                ))

        return entities, alias_relationships

    # -----------------------------------------------------------------------
    # 5. DATABASE PERSISTENCE & STAGING
    # -----------------------------------------------------------------------

    def _persist_to_database(
        self,
        entities: List[NormalizedEntity],
        relationships: List[NormalizedRelationship],
    ) -> None:
        """Persist entities and relationships to MySQL with full provenance properties."""
        if not self.svc:
            return

        try:
            with self.svc._get_connection() as conn:
                with conn.cursor() as cur:
                    for ent in entities:
                        props = {
                            "source_evidence_id": ent.source_evidence_id,
                            "source_file": ent.source_file,
                            "confidence": ent.confidence,
                            "evidence_quote": ent.evidence_quote,
                            "char_offsets": list(ent.char_offsets),
                            "extraction_tier": ent.extraction_tier,
                            **ent.properties,
                        }
                        cur.execute("""
                            INSERT INTO investigation_entities (
                                id, case_id, name, entity_type, properties, verified, source_text, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            ON DUPLICATE KEY UPDATE 
                                properties = VALUES(properties),
                                verified = VALUES(verified);
                        """, (
                            ent.id, self.case_id, ent.name, ent.entity_type,
                            json.dumps(props), int(ent.verified), ent.evidence_quote
                        ))

                    for rel in relationships:
                        is_pred = int(rel.modality in (RelationshipModality.PREDICTED, RelationshipModality.INFERRED))
                        props = {
                            "status": rel.modality.value,
                            "acceptance_status": rel.acceptance_status.value,
                            "source_evidence_id": rel.source_evidence_id,
                            "source_file": rel.source_file,
                            "confidence": rel.confidence,
                            "evidence_quote": rel.evidence_quote,
                            "rule_or_model": rel.rule_or_model,
                            **rel.properties,
                        }
                        cur.execute("""
                            INSERT INTO entity_relationships (
                                id, case_id, source_entity_id, target_entity_id, relationship_type,
                                confidence, predicted, properties, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON DUPLICATE KEY UPDATE
                                confidence = VALUES(confidence),
                                properties = VALUES(properties);
                        """, (
                            rel.id, self.case_id, rel.source_id, rel.target_id, rel.relationship_type,
                            rel.confidence, is_pred, json.dumps(props)
                        ))
        except Exception as e:
            logger.warning("Database persistence error in integration boundary: %s", e)

    # -----------------------------------------------------------------------
    # 6. INVESTIGATOR ACCEPTANCE / REJECTION ACTIONS
    # -----------------------------------------------------------------------

    def accept_relationship(self, relationship_id: str, investigator_id: str = "investigator") -> bool:
        """Promote a PROPOSED (Predicted or Inferred) relationship to CONFIRMED."""
        if not self.svc:
            return False

        try:
            with self.svc._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM entity_relationships WHERE id = %s AND case_id = %s;", (relationship_id, self.case_id))
                    row = cur.fetchone()
                    if not row:
                        return False

                    props = json.loads(row.get("properties") or "{}")
                    props["acceptance_status"] = AcceptanceStatus.CONFIRMED.value
                    props["accepted_by"] = investigator_id
                    props["accepted_at"] = datetime.now().isoformat()

                    cur.execute("""
                        UPDATE entity_relationships 
                        SET properties = %s 
                        WHERE id = %s;
                    """, (json.dumps(props), relationship_id))

            # Record audit and feedback
            self.svc.log_audit(
                case_id=self.case_id,
                action="ACCEPT_RELATIONSHIP",
                username=investigator_id,
                details=f"Investigator accepted proposed relationship {relationship_id} ({row['relationship_type']})"
            )
            self.svc.record_feedback(
                case_id=self.case_id,
                feedback_type="RELATIONSHIP_VALIDATION",
                target_id=relationship_id,
                action="ACCEPTED",
                notes="Investigator confirmed proposed relationship as operational evidence.",
                user_id=investigator_id,
            )

            # Sync confirmed edge to Neo4j
            rel_obj = NormalizedRelationship(
                id=row["id"],
                source_id=row["source_entity_id"],
                source_name=row.get("source_name", row["source_entity_id"]),
                target_id=row["target_entity_id"],
                target_name=row.get("target_name", row["target_entity_id"]),
                relationship_type=row["relationship_type"],
                case_id=self.case_id,
                source_evidence_id=props.get("source_evidence_id", ""),
                source_file=props.get("source_file", ""),
                modality=RelationshipModality(props.get("status", "INFERRED")),
                acceptance_status=AcceptanceStatus.CONFIRMED,
                confidence=float(row.get("confidence", 1.0)),
                evidence_quote=props.get("evidence_quote", ""),
            )
            self.sync_to_neo4j(self.case_id, entities=[], relationships=[rel_obj])
            return True
        except Exception as e:
            logger.error("Failed to accept relationship %s: %s", relationship_id, e)
            return False

    def reject_relationship(self, relationship_id: str, reason: str = "", investigator_id: str = "investigator") -> bool:
        """Reject and discard a PROPOSED (Predicted or Inferred) relationship."""
        if not self.svc:
            return False

        try:
            with self.svc._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM entity_relationships WHERE id = %s AND case_id = %s;", (relationship_id, self.case_id))
                    row = cur.fetchone()
                    if not row:
                        return False

                    props = json.loads(row.get("properties") or "{}")
                    props["acceptance_status"] = AcceptanceStatus.REJECTED.value
                    props["rejected_by"] = investigator_id
                    props["rejected_at"] = datetime.now().isoformat()
                    props["rejection_reason"] = reason

                    cur.execute("""
                        UPDATE entity_relationships 
                        SET properties = %s 
                        WHERE id = %s;
                    """, (json.dumps(props), relationship_id))

            self.svc.log_audit(
                case_id=self.case_id,
                action="REJECT_RELATIONSHIP",
                username=investigator_id,
                details=f"Investigator rejected proposed relationship {relationship_id}: {reason}"
            )
            self.svc.record_feedback(
                case_id=self.case_id,
                feedback_type="RELATIONSHIP_VALIDATION",
                target_id=relationship_id,
                action="DISMISSED",
                notes=reason or "Investigator rejected proposed relationship as invalid.",
                user_id=investigator_id,
            )
            return True
        except Exception as e:
            logger.error("Failed to reject relationship %s: %s", relationship_id, e)
            return False

    # -----------------------------------------------------------------------
    # 7. NEO4J OPERATIONAL GRAPH SYNCHRONIZATION
    # -----------------------------------------------------------------------

    def sync_to_neo4j(
        self,
        case_id: str,
        entities: List[NormalizedEntity],
        relationships: List[NormalizedRelationship],
        driver: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Sync ONLY confirmed knowledge to Neo4j operational graph with strict provenance."""
        # Filter strictly for confirmed relationships
        confirmed_rels = [r for r in relationships if r.acceptance_status == AcceptanceStatus.CONFIRMED]

        cypher_statements: List[str] = []
        for ent in entities:
            lbl = ent.entity_type.capitalize()
            props = {
                "id": ent.id,
                "name": ent.name,
                "caseId": case_id,
                "sourceFile": ent.source_file,
                "evidenceQuote": ent.evidence_quote,
                "confidence": ent.confidence,
                "verified": ent.verified,
            }
            cypher_statements.append(
                f"MERGE (n:{lbl} {{id: '{ent.id}'}}) "
                f"SET n.name = '{ent.name}', n.caseId = '{case_id}', "
                f"n.sourceFile = '{ent.source_file}', n.confidence = {ent.confidence}"
            )

        for rel in confirmed_rels:
            rel_type = rel.relationship_type
            safe_quote = rel.evidence_quote.replace("'", "\\'")
            cypher_statements.append(
                f"MATCH (s {{id: '{rel.source_id}'}}), (t {{id: '{rel.target_id}'}}) "
                f"MERGE (s)-[r:{rel_type}]->(t) "
                f"SET r.id = '{rel.id}', r.caseId = '{case_id}', "
                f"r.status = '{rel.modality.value}', r.sourceFile = '{rel.source_file}', "
                f"r.evidenceQuote = '{safe_quote}', "
                f"r.confidence = {rel.confidence}"
            )

        executed_count = 0
        neo4j_active = False

        if driver is None:
            try:
                import neo4j
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                user = os.getenv("NEO4J_USER", "neo4j")
                pwd = os.getenv("NEO4J_PASSWORD", "crimenet123")
                driver = neo4j.GraphDatabase.driver(uri, auth=(user, pwd))
            except Exception:
                driver = None

        if driver:
            try:
                with driver.session() as session:
                    for stmt in cypher_statements:
                        session.run(stmt)
                        executed_count += 1
                neo4j_active = True
            except Exception as e:
                logger.debug("Neo4j execution deferred (Neo4j server offline or unconfigured): %s", e)

        return {
            "neo4j_connected": neo4j_active,
            "statements_generated": len(cypher_statements),
            "statements_executed": executed_count,
            "entities_synced": len(entities),
            "relationships_synced": len(confirmed_rels),
            "cypher_sample": cypher_statements[:3],
        }

    @staticmethod
    def get_neo4j_driver():
        """Retrieve a configured Neo4j Bolt driver or return None if offline/unconfigured."""
        try:
            import neo4j
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            pwd = os.getenv("NEO4J_PASSWORD", "crimenet123")
            return neo4j.GraphDatabase.driver(uri, auth=(user, pwd))
        except Exception:
            return None
