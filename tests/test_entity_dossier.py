"""Unit and integration tests for CrimeNet Entity Intelligence Dossier.

Verifies:
1. Complete entity intelligence aggregation across Neo4j, case, evidence, alerts,
   analytics, GraphRAG context, HITL human corrections, and link predictions.
2. Flexible entity lookup (by ID, exact name, partial name, and with/without case_id).
3. Complete tabbed UI component construction with all 13 forensic sections:
   - Identity
   - Phones
   - Vehicles
   - Locations
   - Accounts
   - Cases
   - Relationships
   - Communities
   - Alerts
   - Timeline
   - Potential Links
   - AI Summary
   - Sources
4. Strict evidence grounding policy: every claim tagged with [SOURCE: ...].
5. Actionable follow-up investigation questions grounded in actual data gaps.
"""

import os
import pytest
from datetime import datetime

from storage.case_data_service import CaseDataService
from storage.synthetic_case_data import seed_synthetic_case_into_db
from visualizer.entity_dossier_panel import (
    build_entity_dossier,
    _build_identity_tab,
    _build_neighbours_tab,
    _build_cases_tab,
    _build_relationships_tab,
    _build_communities_tab,
    _build_alerts_tab,
    _build_timeline_tab,
    _build_potential_links_tab,
    _build_ai_summary_tab,
    _build_sources_tab,
)


@pytest.fixture(scope="module")
def setup_synthetic_case():
    """Ensure controlled synthetic investigation case is seeded in DB."""
    service = CaseDataService()
    case_id = seed_synthetic_case_into_db(service, overwrite=False)
    return case_id


def test_get_entity_intelligence_aggregation(setup_synthetic_case):
    """Test full intelligence aggregation for a target entity in the synthetic case."""
    service = CaseDataService()
    case_id = setup_synthetic_case

    # Query target: Rahul Sharma (person_rahul_sharma)
    intel = service.get_entity_intelligence("person_rahul_sharma", case_id)

    # 1. Structure Verification
    expected_keys = [
        "entity", "properties", "relationships", "related_nodes",
        "alerts", "timeline", "evidence", "case", "linked_cases",
        "analysis", "community", "graphrag_ctx", "neo4j_relationships",
        "human_corrections", "potential_links"
    ]
    for k in expected_keys:
        assert k in intel, f"Missing key {k} in get_entity_intelligence output"

    # 2. Entity & Case verification
    assert intel["entity"] is not None
    assert intel["entity"]["name"] == "Rahul Sharma"
    assert intel["case"] is not None
    assert intel["case"]["id"] == case_id

    # 3. Relationships and Evidence
    assert len(intel["relationships"]) > 0
    assert len(intel["evidence"]) > 0

    # 4. Modality and Provenance
    for r in intel["relationships"]:
        assert "_props" in r
        assert "_modality" in r
        assert r["_modality"] in ("OBSERVED", "EXTRACTED", "PREDICTED", "INFERRED")


def test_flexible_entity_resolution(setup_synthetic_case):
    """Test looking up entity by name without specifying case_id."""
    service = CaseDataService()

    # Query by exact name
    intel_name = service.get_entity_intelligence("Rahul Sharma")
    assert intel_name["entity"] is not None
    assert intel_name["entity"]["name"] == "Rahul Sharma"
    assert intel_name["case"] is not None

    # Query by another synthetic entity: Amit Verma
    intel_amit = service.get_entity_intelligence("Amit Verma")
    assert intel_amit["entity"] is not None
    assert intel_amit["entity"]["name"] == "Amit Verma"


def test_build_entity_dossier_tabs(setup_synthetic_case):
    """Test that build_entity_dossier builds all 13 required forensic tabs."""
    case_id = setup_synthetic_case
    panel = build_entity_dossier(
        entity_id="person_rahul_sharma",
        node_data={"id": "person_rahul_sharma", "name": "Rahul Sharma", "type": "person"},
        case_id=case_id
    )

    assert panel.id == "entity-dossier-root"
    tabs_comp = None
    for child in panel.children:
        if hasattr(child, "id") and child.id == "entity-dossier-tabs":
            tabs_comp = child
            break

    assert tabs_comp is not None, "entity-dossier-tabs component not found"

    tab_values = [t.value for t in tabs_comp.children]
    expected_tabs = [
        "tab-id",  # Identity
        "tab-ph",  # Phones
        "tab-ve",  # Vehicles
        "tab-lo",  # Locations
        "tab-ac",  # Accounts
        "tab-ca",  # Cases
        "tab-re",  # Relationships
        "tab-co",  # Communities
        "tab-al",  # Alerts
        "tab-ti",  # Timeline
        "tab-pl",  # Potential Links
        "tab-ai",  # AI Summary
        "tab-so",  # Sources
    ]
    for et in expected_tabs:
        assert et in tab_values, f"Missing tab {et} in entity dossier tabs"


def test_ai_summary_strict_grounding(setup_synthetic_case):
    """Test that the AI summary tab enforces strict source grounding and follow-up questions."""
    service = CaseDataService()
    case_id = setup_synthetic_case
    intel = service.get_entity_intelligence("person_rahul_sharma", case_id)

    ai_tab = _build_ai_summary_tab(intel)

    # Check for Grounding Policy banner
    has_policy = False
    has_followups = False
    found_citations = False

    def check_comp(comp):
        nonlocal has_policy, has_followups, found_citations
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    check_comp(c)
            elif isinstance(comp.children, str):
                if "STRICT GROUNDING POLICY" in comp.children:
                    has_policy = True
                if "Follow-up Investigation Inquiries" in comp.children:
                    has_followups = True
                if "[SOURCE:" in comp.children:
                    found_citations = True
            elif hasattr(comp.children, "children"):
                check_comp(comp.children)

    check_comp(ai_tab)
    assert has_policy, "AI Summary must display Strict Grounding Policy disclaimer"
    assert has_followups, "AI Summary must provide useful follow-up investigation questions"
    assert found_citations, "AI Summary claims must contain [SOURCE: ...] citations"


def test_potential_links_hypothesis_notice(setup_synthetic_case):
    """Test that potential links tab prominently displays the statistical hypothesis notice."""
    service = CaseDataService()
    case_id = setup_synthetic_case
    intel = service.get_entity_intelligence("person_rahul_sharma", case_id)

    pl_tab = _build_potential_links_tab(intel)

    notice_found = False
    def check_comp(comp):
        nonlocal notice_found
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    check_comp(c)
            elif isinstance(comp.children, str):
                if "INVESTIGATOR HYPOTHESIS NOTICE" in comp.children or "STATISTICAL HYPOTHESIS" in comp.children:
                    notice_found = True
            elif hasattr(comp.children, "children"):
                check_comp(comp.children)

    check_comp(pl_tab)
    assert notice_found, "Potential links must clearly state that they are unverified statistical hypotheses"


def test_hitl_human_corrections_in_dossier(setup_synthetic_case):
    """Test that recorded HITL human corrections appear in the entity dossier."""
    service = CaseDataService()
    case_id = setup_synthetic_case

    # Record a human correction for Rahul Sharma
    corr_id = service.record_human_correction(
        case_id=case_id,
        target_id="person_rahul_sharma",
        original_ai_result="Associate of Unknown Gang",
        corrected_value="Direct lieutenant of Amit Verma",
        reason="Corroborated by Intercept_09 transcript and physical surveillance log",
        source_ref="Intercept_09",
        investigator_id="Inspector Sandeep Verma"
    )
    assert corr_id is not None

    intel = service.get_entity_intelligence("person_rahul_sharma", case_id)
    assert len(intel["human_corrections"]) > 0

    id_tab = _build_identity_tab(intel)
    found_corr_text = False

    def check_comp(comp):
        nonlocal found_corr_text
        if hasattr(comp, "children"):
            if isinstance(comp.children, list):
                for c in comp.children:
                    check_comp(c)
            elif isinstance(comp.children, str):
                if "Active Human Corrections" in comp.children or "Direct lieutenant of Amit Verma" in comp.children:
                    found_corr_text = True
            elif hasattr(comp.children, "children"):
                check_comp(comp.children)

    check_comp(id_tab)
    assert found_corr_text, "Identity tab must display active HITL corrections"
