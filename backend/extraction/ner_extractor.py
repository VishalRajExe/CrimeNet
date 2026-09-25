"""
CrimeNet AI - Hybrid Entity & Relationship Extraction Engine
Combines deterministic Indian regex with NLP/LLM heuristics to build connected graph structures.
Extracts: Persons, Phones, Vehicles, Bank Accounts, UPI VPAs, Locations, and Organizations.
Infers directed relationships: OPERATES_ACCOUNT, TRANSFERRED_FUNDS, USES_PHONE, SPOTTED_AT, etc.
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from .indian_regex import IndianRegexExtractor, ExtractedToken

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str
    label: str
    type: str  # 'PERSON', 'PHONE', 'ACCOUNT', 'ORGANIZATION', 'VEHICLE', 'LOCATION'
    threat_level: str = "MEDIUM"  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    threat_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "threatLevel": self.threat_level,
            "threatScore": round(self.threat_score, 2),
            "metadata": self.metadata,
        }


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    type: str
    label: str
    confidence: float = 0.85
    amount: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "label": self.label,
            "confidence": round(self.confidence, 2),
            "metadata": self.metadata,
        }
        if self.amount:
            d["amount"] = self.amount
        return d


@dataclass
class ExtractionResult:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    tokens: List[ExtractedToken]
    raw_text: str

    def to_graph_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


class NarrativeExtractor:
    """Extracts entities and relationships from narrative text to build a queryable graph."""

    # Person honorifics and investigative role markers
    PERSON_CUES = re.compile(
        r"\b(?:Suspect|Accused|Operative|Ringleader|Complainant|Victim|Informant|Mr\.?|Ms\.?|Mrs\.?|Shri|Dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
    )

    # General capitalized 2-word names (fallback)
    CAPITALIZED_NAMES = re.compile(
        r"\b([A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15})\b"
    )

    # Organization markers (single line, reasonable length)
    ORG_CUES = re.compile(
        r"\b([A-Z][a-zA-Z0-9&.-]{1,25}(?:\s+[A-Z][a-zA-Z0-9&.-]{1,25}){0,4}\s+(?:Ltd|Pvt|Limited|Corp|Logistics|Enterprises|Vault|Syndicate|Bank|Agency|Cell))\b"
    )

    # Location markers
    LOCATION_CUES = re.compile(
        r"\b(?:in|at|near|towards|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Plaza|Border|Yard|Airport|Station|City|District))?)\b"
    )

    # Corporate or non-person terms
    CORP_TERMS = {"ltd", "pvt", "limited", "corp", "logistics", "enterprises", "vault", "syndicate", "bank", "cell", "agency"}

    STOP_WORDS = {
        "First Information", "Information Report", "Cyber Crime", "New Delhi", "Same Day", "Toll Plaza",
        "Police Station", "Apex Global", "Cctv Cameras", "Fortuner Vehicle", "High Court", "Supreme Court",
        "Rs", "Inr", "Upi Id", "Sbi Account", "Complainant States", "Victim Transferred"
    }

    def __init__(self):
        self.regex_extractor = IndianRegexExtractor()

    def extract_from_narrative(self, narrative: str, case_id: str = "CASE") -> ExtractionResult:
        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []
        edge_counter = 1

        # 1. Deterministic Token Extraction
        tokens = self.regex_extractor.extract_all(narrative)
        amounts = [t.normalized_value for t in tokens if t.token_type == "AMOUNT"]
        default_amount = amounts[0] if amounts else None

        # Create nodes for structured tokens
        for t in tokens:
            node_id = f"{t.token_type[:3]}_{abs(hash(t.normalized_value)) % 10000}"
            if t.token_type == "PHONE":
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=t.normalized_value,
                    type="PHONE",
                    threat_level="HIGH",
                    threat_score=0.75,
                    metadata={"phone": t.normalized_value, "raw": t.raw_value}
                )
            elif t.token_type in ["UPI_ACCOUNT", "BANK_ACCOUNT"]:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=t.normalized_value,
                    type="ACCOUNT",
                    threat_level="CRITICAL",
                    threat_score=0.88,
                    metadata={"account": t.normalized_value, "account_type": t.token_type}
                )
            elif t.token_type == "VEHICLE":
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=t.normalized_value,
                    type="VEHICLE",
                    threat_level="HIGH",
                    threat_score=0.70,
                    metadata={"registration": t.normalized_value}
                )

        # 2. Extract Organization Entities first
        org_matches = self.ORG_CUES.findall(narrative)
        org_names_cleaned = set()
        for org in org_matches:
            clean_org = org.strip()
            if len(clean_org) >= 4 and not any(clean_org.startswith(sw) for sw in ["In ", "At ", "On ", "The "]):
                org_id = f"ORG_{abs(hash(clean_org)) % 10000}"
                nodes[org_id] = GraphNode(
                    id=org_id,
                    label=clean_org,
                    type="ORGANIZATION",
                    threat_level="HIGH",
                    threat_score=0.80,
                    metadata={"org_name": clean_org}
                )
                org_names_cleaned.add(clean_org)

        # 3. Extract Person Entities
        person_matches = self.PERSON_CUES.findall(narrative)
        if not person_matches:
            raw_caps = self.CAPITALIZED_NAMES.findall(narrative)
            person_matches = [name for name in raw_caps]

        persons: List[GraphNode] = []
        for name in set(person_matches):
            name_clean = name.strip()
            # Skip if stop word or contains corp terms
            if name_clean in self.STOP_WORDS or any(w.lower() in self.CORP_TERMS for w in name_clean.split()):
                continue
            # Skip if already part of an organization
            if any(name_clean in org for org in org_names_cleaned):
                continue

            p_id = f"PER_{abs(hash(name_clean)) % 10000}"
            threat = "CRITICAL" if any(w in narrative.lower() for w in ["suspect", "accused", "threat", "ringleader"]) else "MEDIUM"
            score = 0.92 if threat == "CRITICAL" else 0.50
            p_node = GraphNode(
                id=p_id,
                label=name_clean,
                type="PERSON",
                threat_level=threat,
                threat_score=score,
                metadata={"name": name_clean, "role": "Investigative Subject"}
            )
            nodes[p_id] = p_node
            persons.append(p_node)

        # 4. Extract Locations
        loc_matches = self.LOCATION_CUES.findall(narrative)
        for loc in set(loc_matches):
            loc_clean = loc.strip()
            if loc_clean in self.STOP_WORDS or len(loc_clean) < 3:
                continue
            if any(loc_clean in org for org in org_names_cleaned):
                continue
            loc_id = f"LOC_{abs(hash(loc_clean)) % 10000}"
            nodes[loc_id] = GraphNode(
                id=loc_id,
                label=loc_clean,
                type="LOCATION",
                threat_level="LOW",
                threat_score=0.30,
                metadata={"location": loc_clean}
            )

        # 5. Infer Semantic Relationships
        node_list = list(nodes.values())
        persons_list = [n for n in node_list if n.type == "PERSON"]
        phones_list = [n for n in node_list if n.type == "PHONE"]
        accounts_list = [n for n in node_list if n.type == "ACCOUNT"]
        vehicles_list = [n for n in node_list if n.type == "VEHICLE"]
        orgs_list = [n for n in node_list if n.type == "ORGANIZATION"]
        locs_list = [n for n in node_list if n.type == "LOCATION"]

        # Link Person -> Phone
        if persons_list and phones_list:
            for p in persons_list:
                for ph in phones_list:
                    edges.append(
                        GraphEdge(
                            id=f"REL_{edge_counter}",
                            source=p.id,
                            target=ph.id,
                            type="USES_PHONE",
                            label="Associated Phone",
                            confidence=0.90
                        )
                    )
                    edge_counter += 1

        # Link Person -> Account
        if persons_list and accounts_list:
            primary_person = persons_list[0]
            edges.append(
                GraphEdge(
                    id=f"REL_{edge_counter}",
                    source=primary_person.id,
                    target=accounts_list[0].id,
                    type="OPERATES_ACCOUNT",
                    label="Operates Account",
                    confidence=0.92
                )
            )
            edge_counter += 1

        # Link Account -> Account / Org (Fund Transfer)
        if len(accounts_list) >= 2:
            edges.append(
                GraphEdge(
                    id=f"REL_{edge_counter}",
                    source=accounts_list[0].id,
                    target=accounts_list[1].id,
                    type="TRANSFERRED_FUNDS",
                    label=f"Funds Transfer ({default_amount or 'Flagged'})",
                    confidence=0.95,
                    amount=default_amount
                )
            )
            edge_counter += 1

        if accounts_list and orgs_list:
            edges.append(
                GraphEdge(
                    id=f"REL_{edge_counter}",
                    source=accounts_list[-1].id,
                    target=orgs_list[0].id,
                    type="TRANSFERRED_FUNDS",
                    label=f"Wire Transfer ({default_amount or 'Commercial'})",
                    confidence=0.88,
                    amount=default_amount
                )
            )
            edge_counter += 1

        # Link Person / Vehicle -> Location
        if vehicles_list and locs_list:
            edges.append(
                GraphEdge(
                    id=f"REL_{edge_counter}",
                    source=vehicles_list[0].id,
                    target=locs_list[0].id,
                    type="SPOTTED_AT",
                    label="ANPR / Toll Hit",
                    confidence=0.89
                )
            )
            edge_counter += 1

        if persons_list and vehicles_list:
            edges.append(
                GraphEdge(
                    id=f"REL_{edge_counter}",
                    source=persons_list[0].id,
                    target=vehicles_list[0].id,
                    type="USES_VEHICLE",
                    label="Registered Transport",
                    confidence=0.85
                )
            )
            edge_counter += 1

        return ExtractionResult(
            nodes=list(nodes.values()),
            edges=edges,
            tokens=tokens,
            raw_text=narrative
        )


# Global default instance
default_extractor = NarrativeExtractor()
