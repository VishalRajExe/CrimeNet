"""Entity + relation extraction from unstructured police report and evidence text.

Pipeline Architecture:
Evidence
-> Text/Structured Data Extraction
-> Cleaning (hyphenation repair, unprintable char removal, whitespace standardization)
-> Normalization (Unicode NFKC, quote regularization, currency canonicalization)
-> Regex (phone, account, vehicle, case IDs, dates, PAN, Passport, IMEI, UPI)
-> spaCy (NLP named entity recognition: PERSON, ORG, LOC/GPE, DATE, MONEY)
-> Hugging Face Transformers (advanced extraction where justified; no unnecessary models for appearance)
-> Entity Extraction (structured entities with start/end offsets and provenance)
-> Relationship Candidates (cued co-occurrence, syntactic cues, associate links)
-> Entity Normalization & Duplicate Resolution (candidate representations like Rahul Kumar,
   Rahul, R. Kumar treated as potentially related, but NEVER automatically assumed identical
   without appropriate evidence/rules: shared identifier or explicit textual alias).

Every extracted item carries confidence, evidence text snippet, and cryptographic provenance
so investigators can always trace findings back to the source exhibit.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 1. STRUCTURED REGEX IDENTIFIERS (DETERMINISTIC TIER)
# --------------------------------------------------------------------------- #

# Phone numbers: Indian 10-digit mobile, +91- or 0-prefixed
PHONE_RE = re.compile(r"(?:(?:\+91[\-\s]?)|(?:\b0))?([6-9]\d{9})\b")

# Bank account numbers and IFSC
ACCOUNT_RE = re.compile(r"\b(?:A/?c\.?|Account)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d{9,18})\b", re.I)
IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

# Vehicle registration plates: Indian RTO pattern (e.g. MH04AB1234, DL 8C AF 5031, UP16BX7742)
VEHICLE_RE = re.compile(r"\b([A-Z]{2}[\s\-]?[0-9]{1,2}[A-Z]{0,3}[\s\-]?[A-Z]{0,3}[\s\-]?[0-9]{4})\b")

# Case IDs / FIR references (e.g. FIR-2026/0142, FIR No. 2026/0142, Crime No. 45/2026, ECIR/05/DL/2026)
CASE_ID_RE = re.compile(
    r"\b((?:FIR|Crime|Case|ECIR|RC)\s*(?:No\.?|Ref\.?|Number)?\s*[:\-\s]?\s*[A-Za-z0-9\-_/]+)\b",
    re.I,
)

# Calendar dates (e.g. 2026-02-11, 11/02/2026, 11-02-2026, 11th February 2026, 11 Feb 2026)
DATE_RE = re.compile(
    r"\b((?:\d{4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,2})|(?:\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{2,4})|"
    r"(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}))\b",
    re.I,
)

# Known Identifiers:
# - Income Tax PAN card (5 letters + 4 digits + 1 letter)
PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

# - Indian Passport number (1 letter + 7 digits)
PASSPORT_RE = re.compile(r"\b([A-Z][0-9]{7})\b")

# - IMEI 15-digit handset identifier
IMEI_RE = re.compile(r"\b(\d{15})\b")

# - Unified Payments Interface (UPI) VPA
UPI_RE = re.compile(r"\b([a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32})\b")

# - Statutory Legal Section (IPC / BNS / NDPS / PMLA)
SECTION_RE = re.compile(
    r"\b(?:Sec(?:tion)?\.?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:IPC|BNS|NDPS|PMLA|CrPC|IT\s+Act|Arms\s+Act))\b",
    re.I,
)

# Money / Currency mentions
MONEY_RE = re.compile(r"(?:\u20b9|Rs\.?\s?)([\d,]{4,})")

# Commercial / Corporate entity suffix pattern
ORG_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z&]+\s){1,3}(?:Traders|Enterprises|Logistics|Infotech|Exports|Imports|Motors|"
    r"Solutions|Services|Industries|Consultancy|Pvt\.?\s?Ltd\.?|LLP))\b"
)

# Person role cues before proper noun (supports case-insensitive cue, multi-token names and initials)
PERSON_CUES = re.compile(
    r"(?i:accused|suspect|complainant|witness|one|named|shri|smt\.?|mr\.?|ms\.?|mrs\.?|handler|courier|driver|owner)\s+"
    r"([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+){0,2})"
)

# Indian name with initial (e.g. R. Kumar, A. Nair, S. Ansari)
NAME_WITH_INITIAL_RE = re.compile(r"\b([A-Z]\.\s+[A-Z][a-z]+)\b")

# Explicit alias statement cues in text (e.g. "X alias Y", "X @ Y", "X also known as Y")
ALIAS_CUE_RE = re.compile(
    r"\b([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+){0,2})\s+(?i:alias|@|a\.k\.a\.?|also\s+known\s+as|known\s+as)\s+([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+){0,2})\b"
)

# Relationship cue terms
REL_CUES = {
    "USES_PHONE": ("mobile", "phone", "number", "contact", "whatsapp", "called from", "sim", "operated"),
    "USES_VEHICLE": ("vehicle", "car", "bike", "scooter", "registration", "driving", "bearing", "drove"),
    "SEEN_AT": ("seen", "spotted", "cctv", "residing", "met at", "delivered at", "near", "location"),
    "AFFILIATED_WITH": ("employed", "working", "director", "partner", "proprietor", "account of", "firm", "company"),
    "ASSOCIATE_OF": ("along with", "accompanied", "associate", "together with", "handler", "paid", "coordinated"),
    "USES_ACCOUNT": ("account", "a/c", "transferred", "deposit", "routed", "credited", "beneficiary"),
}


# --------------------------------------------------------------------------- #
# 2. CLEANING & NORMALIZATION STAGES
# --------------------------------------------------------------------------- #

def clean_text(raw_text: str) -> str:
    """Cleaning stage:
    - Strips non-printable and control characters (preserves newlines, tabs)
    - Reconnects hyphenated words broken across line breaks (e.g. 'sus-\\npect' -> 'suspect')
    - Standardizes excessive horizontal whitespace while preserving paragraph structure
    - Collapses 3+ newlines to standard double newline
    """
    if not raw_text:
        return ""

    # 1. Filter out control characters (retain \n, \r, \t, printable ascii/unicode)
    filtered = "".join(
        ch for ch in raw_text
        if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 127)
    )

    # 2. Fix hyphenation at line breaks (OCR / column-wrap artifacts)
    # e.g., "sus-\npect" -> "suspect", "complain-\r\n ant" -> "complainant"
    dehyphenated = re.sub(
        r"(\b[A-Za-z]+)-\s*[\r\n]+\s*([A-Za-z]+\b)",
        r"\1\2",
        filtered
    )

    # 3. Standardize whitespace per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in dehyphenated.splitlines()]

    # 4. Collapse excessive blank lines
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def normalize_text(text: str) -> str:
    """Normalization stage:
    - Unicode NFKC normalization (canonical decomposition + compatibility composition)
    - Regularize quotation marks, apostrophes, and typographical dashes
    - Standardize currency representations (INR -> Rs.)
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Standardize quotation marks and apostrophes
    text = re.sub(r"[\u2018\u2019\u201A\u201B`]", "'", text)
    text = re.sub(r"[\u201C\u201D\u201E\u201F«»]", '"', text)

    # 3. Standardize typographical dashes (en-dash, em-dash, minus)
    text = re.sub(r"[\u2013\u2014\u2212]", "-", text)

    # 4. Standardize currency expressions
    text = re.sub(r"\bINR\s*", "Rs. ", text, flags=re.I)

    return text


def normalize_person_name(name: str) -> str:
    """Strips titles, legal cues, and extraneous punctuation from person mentions
    to produce a canonical representation for candidate comparison."""
    if not name:
        return ""
    # Strip common prefixes / honorifics / role cues
    cue_pattern = (
        r"^(?:accused|suspect|complainant|witness|one|named|handler|courier|driver|owner|"
        r"shri|smt\.?|mr\.?|ms\.?|mrs\.?|dr\.?|adv\.?)\s+"
    )
    clean = re.sub(cue_pattern, "", name.strip(), flags=re.I)
    # Remove surrounding punctuation
    clean = clean.strip(" .,;:'\"()[]{}")
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean)
    # Title-case tokens
    tokens = clean.split()
    title_tokens = [t.capitalize() if not (t.isupper() and len(t) <= 3) else t for t in tokens]
    return " ".join(title_tokens)


# --------------------------------------------------------------------------- #
# 3. DOMAIN DATACLASSES WITH PROVENANCE
# --------------------------------------------------------------------------- #

@dataclass
class Entity:
    text: str
    type: str
    confidence: float
    evidence: str
    start: int = 0
    end: int = 0
    normalized_text: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    source_type: str
    target: str
    target_type: str
    type: str
    confidence: float
    evidence: str
    provenance: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 4. ENTITY RESOLUTION & DUPLICATE RESOLUTION MODULE
# --------------------------------------------------------------------------- #

class EntityResolver:
    """Handles entity normalization and duplicate resolution.

    Core Principle:
    Names like 'Rahul Kumar', 'Rahul', and 'R. Kumar' are treated as potentially
    related representations, but NEVER automatically assumed identical without
    appropriate evidence/rules:
      1. Corroborated Identity: Shared unique identifier (phone, account, vehicle,
         PAN, or UPI) -> Confirmed alias ('SAME_AS', confidence >= 0.95).
      2. Explicit Textual Cue: Direct alias statement in evidence ('Rahul Kumar alias Rahul')
         -> Confirmed alias ('ALIAS_OF', confidence >= 0.98).
      3. Uncorroborated Candidate: Potential name variant representation without shared
         identifier or explicit alias statement -> Maintained as distinct entities,
         emitting a candidate relationship ('POTENTIAL_ALIAS', confidence 0.55) with
         transparent reasoning and provenance.
    """

    @staticmethod
    def decompose_name(name: str) -> Dict[str, Any]:
        """Decompose a normalized person name into first name, surname, and initials."""
        norm = normalize_person_name(name)
        tokens = norm.split()
        if not tokens:
            return {"raw": name, "normalized": "", "tokens": [], "first": "", "last": "", "first_initial": ""}

        if len(tokens) == 1:
            return {
                "raw": name,
                "normalized": norm,
                "tokens": tokens,
                "first": tokens[0],
                "last": "",
                "first_initial": tokens[0][0].upper(),
                "is_single": True,
            }

        first_token = tokens[0].rstrip(".")
        last_token = tokens[-1]
        is_first_initial = len(first_token) == 1

        return {
            "raw": name,
            "normalized": norm,
            "tokens": tokens,
            "first": "" if is_first_initial else tokens[0],
            "last": last_token,
            "first_initial": tokens[0][0].upper(),
            "is_single": False,
        }

    @classmethod
    def are_candidate_representations(cls, name_a: str, name_b: str) -> Tuple[bool, str]:
        """Determine if name_a and name_b are candidate representations of the same person.
        
        Examples:
          'Rahul Kumar' vs 'Rahul' -> (True, 'Given name match')
          'Rahul Kumar' vs 'R. Kumar' -> (True, 'Initial + Surname match')
          'Rahul' vs 'R. Kumar' -> (True, 'First initial match with candidate surname')
          'Rahul Kumar' vs 'Suresh Kumar' -> (False, 'Different given names')
          'Rahul Kumar' vs 'Rahul Sharma' -> (False, 'Different surnames')
        """
        da = cls.decompose_name(name_a)
        db = cls.decompose_name(name_b)

        if not da["normalized"] or not db["normalized"]:
            return False, "Empty or invalid name"

        if da["normalized"].lower() == db["normalized"].lower():
            return False, "Identical surface string"

        # Case 1: Both have surnames
        if da["last"] and db["last"]:
            if da["last"].lower() != db["last"].lower():
                return False, f"Different surnames: '{da['last']}' vs '{db['last']}'"

            # Same surname ('Kumar' and 'Kumar')
            # Subcase 1a: One is initial, one is full first name ('R.' vs 'Rahul')
            if da["first"] and not db["first"]:
                if da["first_initial"] == db["first_initial"]:
                    return True, f"Initial '{db['first_initial']}' matches first name '{da['first']}' with shared surname '{da['last']}'"
            elif db["first"] and not da["first"]:
                if da["first_initial"] == db["first_initial"]:
                    return True, f"Initial '{da['first_initial']}' matches first name '{db['first']}' with shared surname '{da['last']}'"
            elif da["first"] and db["first"]:
                if da["first"].lower() == db["first"].lower():
                    return True, f"Identical first name '{da['first']}' and surname '{da['last']}'"
                else:
                    return False, f"Different given names: '{da['first']}' vs '{db['first']}'"
            else:
                if da["first_initial"] == db["first_initial"]:
                    return True, f"Shared initial '{da['first_initial']}' and surname '{da['last']}'"

        # Case 2: One is a single name ('Rahul') and one has surname ('Rahul Kumar' or 'R. Kumar')
        single_d = da if da.get("is_single") else (db if db.get("is_single") else None)
        full_d = db if da.get("is_single") else (da if db.get("is_single") else None)

        if single_d and full_d:
            single_name = single_d["tokens"][0]
            # Match 2a: single name matches full name's first name ('Rahul' matches 'Rahul Kumar')
            if full_d["first"] and single_name.lower() == full_d["first"].lower():
                return True, f"Single name '{single_name}' matches given name of '{full_d['normalized']}'"

            # Match 2b: single name matches initial of full name ('Rahul' starts with 'R' of 'R. Kumar')
            if not full_d["first"] and single_name[0].upper() == full_d["first_initial"]:
                return True, f"Single name '{single_name}' matches initial '{full_d['first_initial']}' of '{full_d['normalized']}'"

        return False, "No candidate match"

    def resolve_duplicates(
        self,
        entities: List[Entity],
        relations: List[Relation],
        full_text: str,
        evidence_id: str = "",
        filename: str = "",
    ) -> List[Relation]:
        """Apply evidence-based duplicate resolution rules across extracted person entities.
        
        Returns new relationship candidates (e.g. SAME_AS, ALIAS_OF, or POTENTIAL_ALIAS).
        Never merges entities or assumes identity without appropriate evidence/rules.
        """
        people = [e for e in entities if e.type == "person"]
        if len(people) < 2:
            return []

        # 1. Index identifiers associated with each person
        person_identifiers: Dict[str, Set[Tuple[str, str]]] = {p.text.lower(): set() for p in people}
        for r in relations:
            s_low = r.source.lower()
            t_low = r.target.lower()
            if r.source_type == "person" and r.target_type in ("phone", "account", "vehicle", "pan", "upi", "imei"):
                if s_low in person_identifiers:
                    person_identifiers[s_low].add((r.target_type, r.target.lower()))
            elif r.target_type == "person" and r.source_type in ("phone", "account", "vehicle", "pan", "upi", "imei"):
                if t_low in person_identifiers:
                    person_identifiers[t_low].add((r.source_type, r.source.lower()))

        candidate_relations: List[Relation] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for i, p1 in enumerate(people):
            for p2 in people[i + 1:]:
                pair_key = tuple(sorted([p1.text.lower(), p2.text.lower()]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                is_cand, reason = self.are_candidate_representations(p1.text, p2.text)
                if not is_cand:
                    continue

                # ----------------------------------------------------------- #
                # RULE 1: SHARED UNIQUE IDENTIFIER (PHONE / ACCOUNT / VEHICLE)
                # ----------------------------------------------------------- #
                p1_ids = person_identifiers.get(p1.text.lower(), set())
                p2_ids = person_identifiers.get(p2.text.lower(), set())
                shared_ids = p1_ids & p2_ids

                if shared_ids:
                    shared_type, shared_val = next(iter(shared_ids))
                    evidence_str = (
                        f"Corroborated identity between '{p1.text}' and '{p2.text}' via shared "
                        f"{shared_type.upper()}: {shared_val}"
                    )
                    candidate_relations.append(
                        Relation(
                            source=p1.text,
                            source_type="person",
                            target=p2.text,
                            target_type="person",
                            type="SAME_AS",
                            confidence=0.96,
                            evidence=evidence_str,
                            provenance={
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "rule_name": "RULE_SHARED_IDENTIFIER",
                                "extraction_tier": "CORROBORATION_RULE",
                                "shared_identifier": f"{shared_type}:{shared_val}",
                                "reasoning": reason,
                                "status": "CONFIRMED_ALIAS",
                                "extracted_at": datetime.now().isoformat(),
                            },
                        )
                    )
                    continue

                # ----------------------------------------------------------- #
                # RULE 2: EXPLICIT TEXTUAL ALIAS CUE IN EVIDENCE
                # ----------------------------------------------------------- #
                esc1 = re.escape(p1.text)
                esc2 = re.escape(p2.text)
                cue_pattern_1 = rf"\b{esc1}\s+(?:alias|@|a\.k\.a\.?|also\s+known\s+as|known\s+as)\s+{esc2}\b"
                cue_pattern_2 = rf"\b{esc2}\s+(?:alias|@|a\.k\.a\.?|also\s+known\s+as|known\s+as)\s+{esc1}\b"
                cue_paren_1 = rf"\b{esc1}\s*\(\s*(?:alias\s+)?{esc2}\s*\)\b"
                cue_paren_2 = rf"\b{esc2}\s*\(\s*(?:alias\s+)?{esc1}\s*\)\b"

                m_cue = (
                    re.search(cue_pattern_1, full_text, re.I)
                    or re.search(cue_pattern_2, full_text, re.I)
                    or re.search(cue_paren_1, full_text, re.I)
                    or re.search(cue_paren_2, full_text, re.I)
                )

                if m_cue:
                    snippet = m_cue.group(0)
                    evidence_str = f"Explicit alias statement in evidence: '{snippet}'"
                    candidate_relations.append(
                        Relation(
                            source=p1.text,
                            source_type="person",
                            target=p2.text,
                            target_type="person",
                            type="ALIAS_OF",
                            confidence=0.98,
                            evidence=evidence_str,
                            provenance={
                                "source_evidence_id": evidence_id,
                                "source_file": filename,
                                "rule_name": "RULE_EXPLICIT_ALIAS_CUE",
                                "extraction_tier": "TEXTUAL_EVIDENCE_RULE",
                                "context_quote": snippet,
                                "status": "CONFIRMED_ALIAS",
                                "extracted_at": datetime.now().isoformat(),
                            },
                        )
                    )
                    continue

                # ----------------------------------------------------------- #
                # RULE 3: UNCORROBORATED CANDIDATE (NEVER ASSUME IDENTITY)
                # ----------------------------------------------------------- #
                evidence_str = (
                    f"Potential name variant candidate ('{p1.text}' vs '{p2.text}'): {reason}. "
                    f"Maintained as distinct entities pending corroborating evidence (shared phone, account, or verified alias)."
                )
                candidate_relations.append(
                    Relation(
                        source=p1.text,
                        source_type="person",
                        target=p2.text,
                        target_type="person",
                        type="POTENTIAL_ALIAS",
                        confidence=0.55,
                        evidence=evidence_str,
                        provenance={
                            "source_evidence_id": evidence_id,
                            "source_file": filename,
                            "rule_name": "NAME_VARIANT_CANDIDATE",
                            "extraction_tier": "NAME_VARIANT_HEURISTIC",
                            "reasoning": reason,
                            "corroboration_found": False,
                            "status": "UNCONFIRMED_CANDIDATE",
                            "extracted_at": datetime.now().isoformat(),
                        },
                    )
                )

        return candidate_relations


# --------------------------------------------------------------------------- #
# 5. MASTER EXTRACTOR CLASS
# --------------------------------------------------------------------------- #

class Extractor:
    """CrimeNet Extraction Architecture.
    
    Pipeline:
    Evidence -> Text -> Cleaning -> Normalization -> Regex -> spaCy -> Hugging Face
    -> Entity Extraction -> Relationship Candidates -> Duplicate Resolution.
    """

    def __init__(
        self,
        locations: Optional[List[str]] = None,
        model: Optional[str] = None,
        hf_model: Optional[str] = None,
    ):
        self.locations = locations or [
            "Karol Bagh", "Nehru Place", "Sector 62 Noida", "Bhiwandi", "Wagle Estate",
            "Andheri East", "Kurla West", "Vashi", "Dadar", "Connaught Place",
            "Sector 21", "Thane", "Bandra", "Saki Naka",
        ]
        # spaCy model loading: defaults to en_core_web_sm if available, gracefully handles missing
        self.model_name = model if model is not None else os.getenv("CRIMENET_NLP_MODEL", "en_core_web_sm")
        self._nlp = self._load_spacy_model()

        # Hugging Face Transformers: only if explicitly specified and justified
        self.hf_model_name = hf_model or os.getenv("CRIMENET_HF_MODEL")
        self._hf_pipeline = self._load_hf_pipeline() if self.hf_model_name else None

        self.resolver = EntityResolver()

    def _load_spacy_model(self):
        """Attempt loading spaCy model, falling back gracefully if not installed."""
        if not self.model_name:
            return None
        try:
            import spacy
            return spacy.load(self.model_name)
        except Exception as e:
            logger.debug(f"spaCy model '{self.model_name}' could not be loaded: {e}")
            return None

    def _load_hf_pipeline(self):
        """Attempt loading Hugging Face transformer pipeline only where justified."""
        if not self.hf_model_name:
            return None
        try:
            from transformers import pipeline
            return pipeline("token-classification", model=self.hf_model_name, aggregation_strategy="simple")
        except Exception as e:
            logger.debug(f"Hugging Face pipeline '{self.hf_model_name}' could not be loaded: {e}")
            return None

    # ------------------------------------------------------------------ #
    # ENTITY EXTRACTION
    # ------------------------------------------------------------------ #
    def entities(
        self,
        text: str,
        evidence_id: str = "doc-001",
        filename: str = "evidence.txt",
    ) -> List[Entity]:
        """Extract structured entities using Regex, spaCy NLP, and optional Hugging Face tier."""
        found: List[Entity] = []
        seen: Set[Tuple[str, str]] = set()

        def push(
            value: str,
            kind: str,
            conf: float,
            why: str,
            start: int = 0,
            end: int = 0,
            tier: str = "DETERMINISTIC_REGEX",
            normalized: str = "",
        ) -> None:
            value = value.strip(" .,;:'\"()")
            if not value:
                return
            key = (kind, value.lower())
            if key in seen:
                return
            seen.add(key)

            if end <= start:
                end = start + len(value)

            # Build contextual quote for forensic provenance
            q_start = max(0, start - 40)
            q_end = min(len(text), end + 40)
            context = text[q_start:q_end].replace("\n", " ").strip()

            prov = {
                "source_evidence_id": evidence_id,
                "source_file": filename,
                "extraction_tier": tier,
                "char_offsets": [start, end],
                "context_quote": context,
                "confidence": conf,
                "extracted_at": datetime.now().isoformat(),
            }

            ent = Entity(
                text=value,
                type=kind,
                confidence=conf,
                evidence=why,
                start=start,
                end=end,
                normalized_text=normalized or value,
                provenance=prov,
            )
            found.append(ent)

        # --------------------------------------------------------------- #
        # TIER 1: DETERMINISTIC REGEX PATTERNS (CRITICAL IDENTIFIERS)
        # --------------------------------------------------------------- #

        # 1. Phone numbers
        for m in PHONE_RE.finditer(text):
            num = m.group(1) if m.lastindex and m.group(1) else m.group(0)
            push(num, "phone", 0.98, "10-digit Indian mobile pattern", m.start(), m.end(), "REGEX:PHONE", num)

        # 2. Account numbers
        for m in ACCOUNT_RE.finditer(text):
            acct = m.group(1)
            push(acct, "account", 0.93, "bank account number pattern", m.start(), m.end(), "REGEX:ACCOUNT", acct)

        # 3. IFSC codes
        for m in IFSC_RE.finditer(text):
            ifsc = m.group(1)
            push(ifsc, "account", 0.95, "IFSC bank branch code pattern", m.start(), m.end(), "REGEX:IFSC", ifsc)

        # 4. Vehicle registration plates
        for m in VEHICLE_RE.finditer(text):
            raw_plate = m.group(0).replace(" ", "").replace("-", "").upper()
            push(raw_plate, "vehicle", 0.95, "RTO registration plate pattern", m.start(), m.end(), "REGEX:VEHICLE", raw_plate)

        # 5. Case IDs
        for m in CASE_ID_RE.finditer(text):
            cid = m.group(1).strip()
            push(cid, "case_id", 0.95, "FIR/Case reference identifier pattern", m.start(), m.end(), "REGEX:CASE_ID", cid)

        # 6. Dates
        for m in DATE_RE.finditer(text):
            dt = m.group(1).strip()
            push(dt, "date", 0.90, "calendar date pattern", m.start(), m.end(), "REGEX:DATE", dt)

        # 7. Known Identifiers: PAN, Passport, IMEI, UPI, Legal Sections
        for m in PAN_RE.finditer(text):
            pan = m.group(1).upper()
            push(pan, "pan", 0.98, "income tax PAN card pattern", m.start(), m.end(), "REGEX:PAN", pan)

        for m in PASSPORT_RE.finditer(text):
            pass_num = m.group(1).upper()
            push(pass_num, "passport", 0.96, "passport number pattern", m.start(), m.end(), "REGEX:PASSPORT", pass_num)

        for m in IMEI_RE.finditer(text):
            imei = m.group(1)
            push(imei, "imei", 0.95, "15-digit IMEI handset identifier pattern", m.start(), m.end(), "REGEX:IMEI", imei)

        for m in UPI_RE.finditer(text):
            upi = m.group(1).lower()
            push(upi, "upi", 0.94, "UPI virtual payment address pattern", m.start(), m.end(), "REGEX:UPI", upi)

        for m in SECTION_RE.finditer(text):
            sec = m.group(0).strip()
            push(sec, "case_id", 0.92, "statutory legal section reference", m.start(), m.end(), "REGEX:SECTION", sec)

        # 8. Organizations
        for m in ORG_RE.finditer(text):
            push(m.group(1), "organization", 0.86, "company suffix in entity name", m.start(), m.end(), "REGEX:ORG", m.group(1))

        # 9. Role Cues + Proper Noun (Accused, Suspect, etc.)
        for m in PERSON_CUES.finditer(text):
            raw_p = m.group(1)
            norm_p = normalize_person_name(raw_p)
            push(raw_p, "person", 0.92, f"role cue '{m.group(0).split()[0]}' before a proper noun", m.start(), m.end(), "REGEX:PERSON_CUE", norm_p)

        # 10. Initial + Surname pattern (e.g. R. Kumar, A. Nair, S. Ansari)
        for m in NAME_WITH_INITIAL_RE.finditer(text):
            raw_init = m.group(1).strip()
            push(raw_init, "person", 0.90, "initial and surname pattern", m.start(), m.end(), "REGEX:NAME_INITIAL", raw_init)

        # 11. Names in alias statements (e.g. Rahul Kumar alias R. Kumar)
        for m in ALIAS_CUE_RE.finditer(text):
            n1 = m.group(1).strip()
            n2 = m.group(2).strip()
            push(n1, "person", 0.94, "name in alias statement", m.start(1), m.end(1), "REGEX:ALIAS_NAME", normalize_person_name(n1))
            push(n2, "person", 0.94, "name in alias statement", m.start(2), m.end(2), "REGEX:ALIAS_NAME", normalize_person_name(n2))

        # 10. Gazetteer Locations
        for loc in self.locations:
            idx = 0
            while True:
                idx = text.find(loc, idx)
                if idx < 0:
                    break
                push(loc, "location", 0.88, "matched policing-area gazetteer", idx, idx + len(loc), "GAZETTEER:LOCATION", loc)
                idx += len(loc)

        # 11. Currency / Amount
        for m in MONEY_RE.finditer(text):
            push(m.group(0), "amount", 0.90, "currency pattern", m.start(), m.end(), "REGEX:AMOUNT", m.group(0))

        # --------------------------------------------------------------- #
        # TIER 2: spaCy NLP ENTITY RECOGNITION
        # --------------------------------------------------------------- #
        if self._nlp is not None:
            try:
                doc = self._nlp(text)
                for ent in doc.ents:
                    lbl = ent.label_
                    kind = {
                        "PERSON": "person",
                        "ORG": "organization",
                        "GPE": "location",
                        "LOC": "location",
                        "FAC": "location",
                        "DATE": "date",
                        "MONEY": "amount",
                    }.get(lbl)

                    if not kind:
                        continue

                    raw_val = ent.text.strip()
                    norm_val = normalize_person_name(raw_val) if kind == "person" else raw_val
                    # Filter out short or punctuation-only artifacts
                    if len(raw_val) <= 1:
                        continue

                    push(
                        value=raw_val,
                        kind=kind,
                        conf=0.90,
                        why=f"{self.model_name} NER ({lbl})",
                        start=ent.start_char,
                        end=ent.end_char,
                        tier=f"SPACY_NER:{lbl}",
                        normalized=norm_val,
                    )
            except Exception as spacy_err:
                logger.warning(f"spaCy NLP extraction warning: {spacy_err}")

        # --------------------------------------------------------------- #
        # TIER 3: HUGGING FACE TRANSFORMERS (WHERE JUSTIFIED)
        # --------------------------------------------------------------- #
        if self._hf_pipeline is not None:
            try:
                hf_results = self._hf_pipeline(text)
                for item in hf_results:
                    val = item.get("word", "").strip()
                    entity_group = item.get("entity_group", "").upper()
                    score = float(item.get("score", 0.85))
                    start_char = int(item.get("start", 0))
                    end_char = int(item.get("end", start_char + len(val)))

                    hf_kind = {
                        "PER": "person", "PERSON": "person",
                        "ORG": "organization",
                        "LOC": "location", "GPE": "location",
                        "MISC": "case_id",
                    }.get(entity_group)

                    if hf_kind and val:
                        push(
                            value=val,
                            kind=hf_kind,
                            conf=round(score, 2),
                            why=f"Hugging Face Transformer ({self.hf_model_name}: {entity_group})",
                            start=start_char,
                            end=end_char,
                            tier="HF_TRANSFORMER",
                            normalized=normalize_person_name(val) if hf_kind == "person" else val,
                        )
            except Exception as hf_err:
                logger.warning(f"Hugging Face extraction warning: {hf_err}")

        return found

    # ------------------------------------------------------------------ #
    # RELATION EXTRACTION
    # ------------------------------------------------------------------ #
    def relations(
        self,
        text: str,
        entities: List[Entity],
        evidence_id: str = "doc-001",
        filename: str = "evidence.txt",
    ) -> List[Relation]:
        """Extract relationship candidates between entities based on sentence co-occurrence
        and forensic linguistic cue phrases."""
        rels: List[Relation] = []
        by_type: Dict[str, List[Entity]] = {}
        for e in entities:
            by_type.setdefault(e.type, []).append(e)

        for sentence in re.split(r"(?<=[.!?])\s+", text):
            low = sentence.lower()
            here = {t: [e for e in v if e.text in sentence] for t, v in by_type.items()}
            people = here.get("person", [])
            if not people:
                continue

            def cued(rel_type: str) -> float:
                return 0.08 if any(c in low for c in REL_CUES.get(rel_type, ())) else 0.0

            def add_rel(src: str, src_t: str, tgt: str, tgt_t: str, rtype: str, base_conf: float, rule: str):
                conf = round(min(base_conf + cued(rtype), 0.99), 2)
                if conf < 0.6:
                    return
                prov = {
                    "source_evidence_id": evidence_id,
                    "source_file": filename,
                    "extraction_tier": "RELATION_CUE",
                    "rule_name": rule,
                    "context_quote": sentence.strip(),
                    "confidence": conf,
                    "extracted_at": datetime.now().isoformat(),
                }
                rels.append(
                    Relation(
                        source=src,
                        source_type=src_t,
                        target=tgt,
                        target_type=tgt_t,
                        type=rtype,
                        confidence=conf,
                        evidence=sentence.strip(),
                        provenance=prov,
                    )
                )

            for person in people:
                for phone in here.get("phone", []):
                    add_rel(person.text, "person", phone.text, "phone", "USES_PHONE", 0.86, "PERSON_USES_PHONE")
                for veh in here.get("vehicle", []):
                    add_rel(person.text, "person", veh.text, "vehicle", "USES_VEHICLE", 0.82, "PERSON_USES_VEHICLE")
                for loc in here.get("location", []):
                    add_rel(person.text, "person", loc.text, "location", "SEEN_AT", 0.70, "PERSON_SEEN_AT")
                for org in here.get("organization", []):
                    add_rel(person.text, "person", org.text, "organization", "AFFILIATED_WITH", 0.74, "PERSON_AFFILIATED_WITH")
                for acct in here.get("account", []):
                    add_rel(person.text, "person", acct.text, "account", "USES_ACCOUNT", 0.75, "PERSON_USES_ACCOUNT")
                for cid in here.get("case_id", []):
                    add_rel(person.text, "person", cid.text, "case_id", "NAMED_IN_CASE", 0.80, "PERSON_NAMED_IN_CASE")

            for i, a in enumerate(people):
                for b in people[i + 1:]:
                    if a.text.lower() != b.text.lower():
                        add_rel(a.text, "person", b.text, "person", "ASSOCIATE_OF", 0.62, "PERSON_COOCCURRENCE")

        return [r for r in rels if r.confidence >= 0.6]

    # ------------------------------------------------------------------ #
    # MASTER PIPELINE EXECUTION
    # ------------------------------------------------------------------ #
    def process(
        self,
        text: str,
        evidence_id: str = "doc-001",
        filename: str = "evidence.txt",
    ) -> dict:
        """Execute full extraction pipeline:
        Evidence -> Text -> Cleaning -> Normalization -> Regex -> spaCy -> Hugging Face
        -> Entity Extraction -> Relationship Candidates -> Duplicate Resolution.
        """
        # 1. Cleaning
        cleaned = clean_text(text)

        # 2. Normalization
        normalized = normalize_text(cleaned)

        # 3. Entity Extraction
        ents = self.entities(normalized, evidence_id=evidence_id, filename=filename)

        # 4. Relationship Candidates
        rels = self.relations(normalized, ents, evidence_id=evidence_id, filename=filename)

        # 5. Entity Normalization and Duplicate Resolution
        duplicate_relations = self.resolver.resolve_duplicates(
            entities=ents,
            relations=rels,
            full_text=normalized,
            evidence_id=evidence_id,
            filename=filename,
        )
        rels.extend(duplicate_relations)

        return {
            "raw_text": normalized,
            "entities": [asdict(e) for e in ents],
            "relations": [asdict(r) for r in rels],
            "stats": {
                "entities": len(ents),
                "relations": len(rels),
                "characters": len(normalized),
                "provenance_recorded": True,
            },
        }
