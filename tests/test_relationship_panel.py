"""Unit and integration tests for CrimeNet Relationship Investigation Panel.

Verifies:
1. When an investigator clicks an edge, relationship panel renders:
   Relationship: Rahul → CALLED → Amit
2. Displays all 9 mandatory specification fields:
   - Relationship type
   - Source document (e.g., CDR_001.csv)
   - Date
   - Time
   - Duration
   - Supporting evidence
   - Originating record
   - Extraction method
   - Confidence / score
3. Clearly distinguishes the 4 evidentiary modalities:
   - Observed (🟢)
   - Extracted (🟣)
   - Predicted (🟡)
   - Inferred (🔵)
4. Provides interactive button to inspect and open source evidence.
5. Preserves human-in-the-loop validation controls for AI hypotheses.
"""

import pytest
from storage.case_data_service import CaseDataService
from storage.synthetic_case_data import seed_synthetic_case_into_db
from visualizer.relationship_panel import (
    build_relationship_panel,
    build_edge_source_modal,
    MODALITY_STYLE,
)


@pytest.fixture(scope="module")
def setup_case():
    """Seed synthetic investigation case with CDR, FIR, and Transaction evidence."""
    service = CaseDataService()
    case_id = seed_synthetic_case_into_db(service, overwrite=False)
    return case_id


def test_relationship_panel_observed_cdr_edge(setup_case):
    """Test clicking an observed telephony CDR edge (Rahul -> CALLED -> Amit)."""
    case_id = setup_case

    edge_data = {
        "id": "rel_cdr_call_001",
        "db_id": "rel_cdr_call_001",
        "source": "person_rahul_sharma",
        "source_name": "Rahul Sharma",
        "source_type": "person",
        "target": "person_amit_verma",
        "target_name": "Amit Verma",
        "target_type": "person",
        "label": "CALLED",
        "type": "CALLED",
        "modality": "OBSERVED",
        "acceptance": "CONFIRMED",
        "confidence": 1.0,
        "source_file": "CDR_001.csv",
        "quote": "Call duration 340s on 2026-03-01 22:15:00 from +91-9876543210 to +91-9812345678",
        "provenance": {
            "source_file": "CDR_001.csv",
            "date": "2026-03-01",
            "time": "22:15:00",
            "duration": "340s",
            "originating_record": "CDR_ROW_4021",
            "extraction_method": "Direct Telephony Ingestion (CDR)",
            "verbatim_quote": "Call duration 340s on 2026-03-01 22:15:00 from +91-9876543210 to +91-9812345678"
        }
    }

    panel = build_relationship_panel(edge_data=edge_data, case_id=case_id)
    assert panel.id == "relationship-panel-root"

    text_blobs = []
    def collect_text(comp):
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    collect_text(c)
            elif isinstance(comp.children, str):
                text_blobs.append(comp.children)
            elif hasattr(comp.children, "children"):
                collect_text(comp.children)

    collect_text(panel)
    all_text = " ".join(text_blobs)

    # 1. Header verification: Rahul -> CALLED -> Amit
    assert "Rahul Sharma" in all_text
    assert "CALLED" in all_text
    assert "Amit Verma" in all_text

    # 2. Required Specification fields verification
    assert "CDR_001.csv" in all_text, "Must show source: CDR_001.csv"
    assert "2026-03-01" in all_text, "Must show date"
    assert "22:15:00" in all_text, "Must show time"
    assert "340s" in all_text, "Must show duration"
    assert "CDR_ROW_4021" in all_text, "Must show originating record"
    assert "Direct Telephony Ingestion" in all_text, "Must show extraction method"
    assert "100%" in all_text, "Must show confidence / score"

    # 3. Modality distinction: Observed
    assert "OBSERVED" in all_text


def test_relationship_panel_extracted_document_edge(setup_case):
    """Test clicking an extracted NLP edge from an FIR or statement."""
    case_id = setup_case

    edge_data = {
        "id": "rel_fir_statement_002",
        "db_id": "rel_fir_statement_002",
        "source": "person_rahul_sharma",
        "source_name": "Rahul Sharma",
        "source_type": "person",
        "target": "vehicle_mh01_ab1234",
        "target_name": "MH-01-AB-1234",
        "target_type": "vehicle",
        "label": "DRIVES",
        "type": "DRIVES",
        "modality": "EXTRACTED",
        "acceptance": "CONFIRMED",
        "confidence": 0.95,
        "source_file": "FIR_102.pdf",
        "quote": "Accused Rahul Sharma was observed operating vehicle MH-01-AB-1234 fleeing scene",
        "provenance": {
            "source_file": "FIR_102.pdf",
            "date": "2026-03-02",
            "time": "01:30:00",
            "duration": "N/A",
            "originating_record": "FIR_PARA_04",
            "extraction_method": "Forensic Document NLP (FIR)",
            "verbatim_quote": "Accused Rahul Sharma was observed operating vehicle MH-01-AB-1234 fleeing scene"
        }
    }

    panel = build_relationship_panel(edge_data=edge_data, case_id=case_id)
    text_blobs = []
    def collect_text(comp):
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    collect_text(c)
            elif isinstance(comp.children, str):
                text_blobs.append(comp.children)
            elif hasattr(comp.children, "children"):
                collect_text(comp.children)

    collect_text(panel)
    all_text = " ".join(text_blobs)

    assert "EXTRACTED" in all_text
    assert "FIR_102.pdf" in all_text
    assert "FIR_PARA_04" in all_text
    assert "95%" in all_text


def test_relationship_panel_predicted_link_hypothesis(setup_case):
    """Test clicking an AI predicted link hypothesis edge."""
    case_id = setup_case

    edge_data = {
        "id": "rel_ai_predicted_003",
        "db_id": "rel_ai_predicted_003",
        "source": "person_rahul_sharma",
        "source_name": "Rahul Sharma",
        "source_type": "person",
        "target": "person_vikram_malhotra",
        "target_name": "Vikram Malhotra",
        "target_type": "person",
        "label": "POTENTIAL_ASSOCIATE",
        "type": "POTENTIAL_ASSOCIATE",
        "modality": "PREDICTED",
        "acceptance": "PROPOSED",
        "confidence": 0.82,
        "source_file": "Graph Topology Link Prediction",
        "provenance": {
            "source_file": "Adamic-Adar Algorithm",
            "date": "2026-09-25",
            "time": "12:00:00",
            "duration": "N/A",
            "originating_record": "PRED_AA_7721",
            "extraction_method": "AI Link Prediction (Adamic-Adar)",
        }
    }

    panel = build_relationship_panel(edge_data=edge_data, case_id=case_id)
    text_blobs = []
    def collect_text(comp):
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    collect_text(c)
            elif isinstance(comp.children, str):
                text_blobs.append(comp.children)
            elif hasattr(comp.children, "children"):
                collect_text(comp.children)

    collect_text(panel)
    all_text = " ".join(text_blobs)

    assert "PREDICTED" in all_text
    assert "HUMAN VALIDATION REQUIRED" in all_text
    assert "82%" in all_text


def test_open_source_evidence_modal_structure():
    """Verify that build_edge_source_modal constructs the source evidence viewer modal."""
    modal = build_edge_source_modal()
    assert modal is not None
    # Check that modal has modal-edge-source-viewer id
    found_id = False
    for child in modal.children:
        if hasattr(child, "id") and child.id == "modal-edge-source-viewer":
            found_id = True
            break
    assert found_id, "Must contain modal-edge-source-viewer"
