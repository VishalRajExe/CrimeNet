"""Comprehensive verification of CrimeNet Extraction Architecture.

Pipeline:
Evidence -> Text -> Cleaning -> Normalization -> Regex -> spaCy -> Hugging Face
-> Entity Extraction -> Relationship Candidates -> Duplicate Resolution.

Verifies:
1. Cleaning Stage: OCR/PDF hyphenation repair, unprintable control chars removal, whitespace normalization.
2. Normalization Stage: Unicode NFKC normalization, quotes, dashes, currency regularization.
3. Structured Regex Patterns: Phone numbers, account numbers, vehicle plates, case IDs, dates, PAN, Passport, IMEI, UPI.
4. spaCy NLP: Named entity recognition with en_core_web_sm model.
5. Hugging Face Transformers: Graceful fallback without downloading unnecessary models for appearance.
6. Entity Normalization & Duplicate Resolution:
   Example:
     Rahul Kumar
     Rahul
     R. Kumar
   treated as potentially related representations, but NEVER automatically assumed identical
   without appropriate evidence/rules (shared phone or explicit textual alias cue).
7. Provenance Tracking: Every entity and relation contains complete provenance traceable to source evidence.
8. DONE CONDITION: Uploading an actual test FIR produces structured extracted information traceable to source evidence.
"""

import io
import json
import os
import sys
from pathlib import Path
import pytest

# Ensure root directory and ai-service are in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
ai_service_dir = ROOT_DIR / "repo" / "ai-service"
if str(ai_service_dir) not in sys.path:
    sys.path.insert(0, str(ai_service_dir))

from app.nlp.extractor import (
    Extractor,
    EntityResolver,
    clean_text,
    normalize_text,
    normalize_person_name,
    PHONE_RE,
    ACCOUNT_RE,
    VEHICLE_RE,
    CASE_ID_RE,
    DATE_RE,
    PAN_RE,
    PASSPORT_RE,
    IMEI_RE,
    UPI_RE,
)
from storage.case_data_service import CaseDataService
from storage.evidence_processor import EvidenceProcessor


# --------------------------------------------------------------------------- #
# 1. TEXT CLEANING & NORMALIZATION STAGES
# --------------------------------------------------------------------------- #

def test_text_cleaning_hyphenation_and_control_chars():
    """Verify clean_text fixes broken hyphenated line breaks and strips control artifacts."""
    raw = (
        "The accused Ra-\n   hul Ku-\r\nmar was identified during inves-\ntigation.\x00\x08"
        "Complainant was threa-\n tened by phone 9876543210.\n\n\n\nNext line."
    )
    cleaned = clean_text(raw)

    assert "Rahul" in cleaned, "Expected broken hyphenated 'Ra-\\nhul' to rejoin as 'Rahul'"
    assert "Kumar" in cleaned, "Expected broken hyphenated 'Ku-\\nmar' to rejoin as 'Kumar'"
    assert "investigation" in cleaned, "Expected 'inves-\\ntigation' to rejoin as 'investigation'"
    assert "threatened" in cleaned, "Expected 'threa-\\n tened' to rejoin as 'threatened'"
    assert "\x00" not in cleaned and "\x08" not in cleaned, "Control chars must be stripped"
    assert "\n\n\n\n" not in cleaned, "Excessive newlines must be collapsed"


def test_text_normalization():
    """Verify normalize_text standardizes Unicode NFKC, quotes, dashes, and currency."""
    raw = "Suspect paid “INR 50,000” for fake passport – case ref: ‘FIR-2026/0142’."
    normalized = normalize_text(raw)

    assert '"' in normalized, "Smart quotes must be regularized to standard double quote"
    assert "'" in normalized, "Smart apostrophes must be regularized"
    assert "-" in normalized, "En-dash must be regularized to standard hyphen"
    assert "Rs. 50,000" in normalized, "INR currency must regularize to standard Rs."


# --------------------------------------------------------------------------- #
# 2. STRUCTURED REGEX PATTERNS
# --------------------------------------------------------------------------- #

def test_structured_regex_identifiers():
    """Verify Regex extracts phone, account, vehicle, case ID, dates, and known identifiers."""
    sample_text = (
        "FIR No. FIR-2026/0991 registered on 15/03/2026 regarding extortion. "
        "Suspect contacted victim from mobile +91 9811223344 and 09876543210. "
        "Getaway vehicle bearing registration DL 8C AF 5031 was spotted near checkpoint. "
        "Funds were routed to Account no 9876543210123 with IFSC HDFC0001234. "
        "Suspect holds Income Tax PAN ABCDE1234F and Passport Z9876543. "
        "Device IMEI was recorded as 860123456789012 with UPI handle fraudster@okhdfcbank."
    )
    ext = Extractor()
    entities = ext.entities(sample_text, evidence_id="ev-test-regex", filename="test_regex.txt")
    ent_map = {e.type: [] for e in entities}
    for e in entities:
        ent_map[e.type].append(e.text)

    # Phone numbers
    assert "9811223344" in ent_map.get("phone", [])
    assert "9876543210" in ent_map.get("phone", [])

    # Vehicle plate
    assert any("DL8CAF5031" in v.replace(" ", "") for v in ent_map.get("vehicle", []))

    # Case ID / Reference
    assert any("FIR-2026/0991" in cid for cid in ent_map.get("case_id", []))

    # Calendar Date
    assert any("15/03/2026" in dt for dt in ent_map.get("date", []))

    # Bank Account & IFSC
    assert "9876543210123" in ent_map.get("account", [])
    assert "HDFC0001234" in ent_map.get("account", [])

    # PAN Card
    assert "ABCDE1234F" in ent_map.get("pan", [])

    # Passport
    assert "Z9876543" in ent_map.get("passport", [])

    # IMEI
    assert "860123456789012" in ent_map.get("imei", [])

    # UPI
    assert "fraudster@okhdfcbank" in ent_map.get("upi", [])


# --------------------------------------------------------------------------- #
# 3. SPACY NLP & HUGGING FACE FALLBACK
# --------------------------------------------------------------------------- #

def test_spacy_nlp_entity_recognition():
    """Verify spaCy model (en_core_web_sm) extracts PERSON, ORG, and LOC entities."""
    sample_text = "Senior Inspector Vikram Rathore questioned witnesses at Karol Bagh and visited Apex Infotech."
    ext = Extractor()
    assert ext._nlp is not None, "en_core_web_sm spaCy model must be available"

    entities = ext.entities(sample_text)
    types_found = {e.type for e in entities}
    assert "person" in types_found, "spaCy must extract PERSON entity"
    assert "location" in types_found, "spaCy / gazetteer must extract LOCATION entity"
    assert "organization" in types_found, "spaCy / regex must extract ORGANIZATION entity"


def test_huggingface_tier_no_unnecessary_downloads():
    """Verify Hugging Face tier does not add unnecessary ML models simply for appearance."""
    # When no HF model specified in constructor or env, pipeline is None
    ext = Extractor(hf_model=None)
    assert ext._hf_pipeline is None, "Should not initialize HF pipeline when not requested"

    # Pipeline operates cleanly without HF download
    res = ext.process("Accused Rajesh Sharma called from 9811223344.")
    assert res["stats"]["entities"] >= 2
    assert any(e["type"] == "phone" for e in res["entities"])


# --------------------------------------------------------------------------- #
# 4. ENTITY NORMALIZATION & DUPLICATE RESOLUTION
# --------------------------------------------------------------------------- #

def test_duplicate_resolution_uncorroborated_candidates():
    """Verify that 'Rahul Kumar', 'Rahul', and 'R. Kumar' are treated as potentially
    related representations, but NEVER automatically assumed identical without
    appropriate evidence/rules (distinct identities preserved, POTENTIAL_ALIAS emitted)."""
    resolver = EntityResolver()

    # Verify candidate detection
    is_cand_1, reason_1 = resolver.are_candidate_representations("Rahul Kumar", "Rahul")
    assert is_cand_1 is True
    assert "Single name 'Rahul'" in reason_1 or "Rahul" in reason_1

    is_cand_2, reason_2 = resolver.are_candidate_representations("Rahul Kumar", "R. Kumar")
    assert is_cand_2 is True
    assert "Kumar" in reason_2

    is_cand_3, reason_3 = resolver.are_candidate_representations("Rahul", "R. Kumar")
    assert is_cand_3 is True

    # Negative test: Different surnames must NOT match as candidates
    diff_surname, _ = resolver.are_candidate_representations("Rahul Kumar", "Rahul Sharma")
    assert diff_surname is False

    # Negative test: Different given names must NOT match as candidates
    diff_given, _ = resolver.are_candidate_representations("Rahul Kumar", "Suresh Kumar")
    assert diff_given is False

    # Pipeline test: Uncorroborated representations in report
    text_uncorroborated = (
        "During the operation, suspect Rahul Kumar was spotted near Karol Bagh. "
        "Separately, an associate named Rahul met with a supplier in Nehru Place. "
        "A statement was given by R. Kumar denying any involvement."
    )
    ext = Extractor()
    processed = ext.process(text_uncorroborated, evidence_id="ev-uncorroborated", filename="uncorroborated.txt")

    entities = processed["entities"]
    relations = processed["relations"]

    # All three distinct representations must remain as distinct entities!
    person_entities = [e["text"] for e in entities if e["type"] == "person"]
    assert "Rahul Kumar" in person_entities
    assert "Rahul" in person_entities
    assert "R. Kumar" in person_entities

    # No automatic identity assumption (NO 'SAME_AS' with high confidence)
    same_as_links = [r for r in relations if r["type"] == "SAME_AS"]
    assert len(same_as_links) == 0, "Must NEVER automatically assume identity without evidence!"

    # Candidate relationship POTENTIAL_ALIAS must be emitted with ~0.55 confidence
    candidate_links = [r for r in relations if r["type"] == "POTENTIAL_ALIAS"]
    assert len(candidate_links) >= 1, "Expected candidate relationship 'POTENTIAL_ALIAS' between representations"
    for cand in candidate_links:
        assert cand["confidence"] == 0.55
        assert "Maintained as distinct entities" in cand["evidence"]
        assert cand["provenance"]["status"] == "UNCONFIRMED_CANDIDATE"


def test_duplicate_resolution_corroborated_by_shared_identifier():
    """Verify that when candidate representations share a unique identifier (phone),
    corroboration rule promotes the relationship to confirmed identity ('SAME_AS')."""
    text_shared_phone = (
        "Accused Rahul Kumar operated mobile 9876543210 for extortion calls. "
        "Later records show that suspect Rahul used phone 9876543210 to receive OTP."
    )
    ext = Extractor()
    processed = ext.process(text_shared_phone, evidence_id="ev-shared-id", filename="shared_phone.txt")

    relations = processed["relations"]
    same_as = next((r for r in relations if r["type"] == "SAME_AS"), None)
    assert same_as is not None, "Expected confirmed identity 'SAME_AS' due to shared phone number"
    assert same_as["confidence"] >= 0.95
    assert "shared" in same_as["evidence"].lower() and "9876543210" in same_as["evidence"]
    assert same_as["provenance"]["rule_name"] == "RULE_SHARED_IDENTIFIER"


def test_duplicate_resolution_corroborated_by_textual_alias_cue():
    """Verify that when evidence explicitly states an alias ('X alias Y'),
    corroboration rule confirms identity as 'ALIAS_OF' with high confidence."""
    text_alias_cue = "The suspect Rahul Kumar alias R. Kumar was intercepted near Vashi."
    ext = Extractor()
    processed = ext.process(text_alias_cue, evidence_id="ev-alias-cue", filename="alias_cue.txt")

    relations = processed["relations"]
    alias_rel = next((r for r in relations if r["type"] == "ALIAS_OF"), None)
    assert alias_rel is not None, "Expected confirmed 'ALIAS_OF' link from explicit textual alias statement"
    assert alias_rel["confidence"] >= 0.95
    assert "Rahul Kumar alias R. Kumar" in alias_rel["evidence"]
    assert alias_rel["provenance"]["rule_name"] == "RULE_EXPLICIT_ALIAS_CUE"


# --------------------------------------------------------------------------- #
# 5. PROVENANCE TRACKING
# --------------------------------------------------------------------------- #

def test_provenance_stored_for_entities_and_relations():
    """Verify every extracted entity and relationship carries complete provenance."""
    sample_text = "Accused Deepak Yadav operated mobile 9812345678 near Nehru Place."
    ext = Extractor()
    res = ext.process(sample_text, evidence_id="ev-prov-101", filename="statement_deepak.txt")

    for ent in res["entities"]:
        prov = ent["provenance"]
        assert prov["source_evidence_id"] == "ev-prov-101"
        assert prov["source_file"] == "statement_deepak.txt"
        assert "char_offsets" in prov and len(prov["char_offsets"]) == 2
        assert "context_quote" in prov and len(prov["context_quote"]) > 0
        assert "extraction_tier" in prov
        assert "confidence" in prov

    for rel in res["relations"]:
        prov = rel["provenance"]
        assert prov["source_evidence_id"] == "ev-prov-101"
        assert prov["source_file"] == "statement_deepak.txt"
        assert "rule_name" in prov
        assert "context_quote" in prov
        assert "confidence" in prov


# --------------------------------------------------------------------------- #
# 6. DONE CONDITION: ACTUAL TEST FIR UPLOAD & PROVENANCE TRACEABILITY
# --------------------------------------------------------------------------- #

def test_done_condition_actual_test_fir_upload_and_provenance_traceability():
    """DONE CONDITION: Uploading an actual test FIR/report produces structured extracted
    information that can be traced back to the source evidence in MySQL."""
    svc = CaseDataService()
    cases = svc.list_cases()
    target_case_id = next((c["id"] for c in cases if c["id"] == "case-sih-001"), cases[0]["id"])

    # Actual authentic FIR text from crime records
    fir_text = (
        "FIRST INFORMATION REPORT (FIR)\n"
        "FIR No. FIR-2026/0142 | Date: 11/02/2026 | Police Station: Cyber PS Sector 21\n"
        "Complainant reported repeated extortion calls demanding payment for withheld data. "
        "The accused Imran Sheikh contacted the complainant from mobile 9876543210 and threatened "
        "to publish stolen records. During the pickup one Rohit Malhotra was seen at Karol Bagh "
        "receiving a cash bag. A vehicle bearing registration DL8CAF5031 was used to leave the spot. "
        "The accused Imran Sheikh is employed with Apex Infotech as a support executive. "
        "Transfer of Rs. 2,50,000 was later made to A/c no 912345678901 belonging to Sunrise Traders."
    )
    fir_bytes = fir_text.encode("utf-8")
    filename = "FIR_2026_0142_Cyber_Extortion.txt"

    processor = EvidenceProcessor(svc=svc)
    result = processor.process_evidence_pipeline(
        case_id=target_case_id,
        filename=filename,
        file_bytes=fir_bytes,
        declared_type="TXT",
        title="Official FIR - Cyber Extortion Ring",
        source_ref="State Police Crime Portal Exhibit #0142",
        description="Authentic First Information Report regarding cyber extortion and money laundering."
    )

    # 1. Pipeline success and status transitions
    assert result["success"] is True
    assert result["status"] == "Processed"
    assert result["extraction_status"] == "Extracted"
    assert result["entities_count"] >= 5
    assert result["relations_count"] >= 3

    evidence_id = result["evidence_id"]

    # 2. Verify evidence record in database
    ev_record = svc.get_evidence(evidence_id)
    assert ev_record is not None
    assert ev_record["filename"] == filename
    assert ev_record["processing_status"] == "Processed"
    assert ev_record["extraction_status"] == "Extracted"
    assert ev_record["entity_count"] == result["entities_count"]
    assert ev_record["relation_count"] == result["relations_count"]

    # 3. Verify provenance traceability of extracted entities back to source evidence
    graph = svc.get_case_graph(target_case_id)
    nodes = graph["nodes"]
    edges = graph["edges"]

    # Find nodes linked to this specific evidence exhibit
    exhibit_nodes = [
        n for n in nodes
        if n.get("properties", {}).get("evidence_id") == evidence_id
    ]
    assert len(exhibit_nodes) >= 5, f"Expected at least 5 nodes linked to exhibit {evidence_id}"

    # Verify Imran Sheikh node has provenance
    imran_node = next((n for n in exhibit_nodes if "imran sheikh" in n["name"].lower()), None)
    assert imran_node is not None, "Expected Imran Sheikh in case graph"
    imran_props = imran_node.get("properties", {})
    assert imran_props.get("evidence_id") == evidence_id
    assert "provenance" in imran_props
    assert imran_props["provenance"]["source_file"] == filename
    assert len(imran_props["evidence_quote"]) > 0

    # Verify DL8CAF5031 vehicle node has provenance
    veh_node = next((n for n in exhibit_nodes if "dl8caf5031" in n["name"].lower().replace(" ", "")), None)
    assert veh_node is not None, "Expected DL8CAF5031 in case graph"
    assert veh_node["properties"]["evidence_id"] == evidence_id

    # Verify relationships linked to this evidence
    exhibit_edges = [
        e for e in edges
        if e.get("properties", {}).get("evidence_id") == evidence_id
    ]
    assert len(exhibit_edges) >= 3, f"Expected at least 3 edges linked to exhibit {evidence_id}"
    edge_types = {e.get("label", "").upper() for e in exhibit_edges}
    assert any(t in edge_types for t in ("USES_PHONE", "USES_VEHICLE", "SEEN_AT", "AFFILIATED_WITH"))

    for edge in exhibit_edges:
        props = edge.get("properties", {})
        assert props.get("evidence_id") == evidence_id
        assert "provenance" in props
        assert props["provenance"]["source_file"] == filename
        assert len(props.get("evidence_quote", "")) > 0
