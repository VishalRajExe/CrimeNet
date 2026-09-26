"""
Tests for Controlled Synthetic Investigation Dataset.
Verifies label 'TEST / SYNTHETIC DATA', presence of all required entity modalities,
known ground truth hidden links for link prediction evaluation, and anomaly ground truth.
"""

import pytest
from storage.synthetic_case_data import (
    DATASET_LABEL,
    CASE_ID,
    CASE_TITLE,
    SYNTHETIC_NODES,
    SYNTHETIC_OBSERVED_EDGES,
    GROUND_TRUTH_HIDDEN_LINKS,
    GROUND_TRUTH_NEGATIVE_LINKS,
    GROUND_TRUTH_ANOMALIES,
    SYNTHETIC_EVIDENCE,
    generate_synthetic_dataset_json_file,
    seed_synthetic_case_into_db,
    evaluate_synthetic_link_prediction,
)
from storage.case_data_service import CaseDataService
from storage.builtin_datasets import BuiltinDatasetsManager


def test_synthetic_dataset_metadata_and_labeling():
    """Verify explicit labeling: TEST / SYNTHETIC DATA and disclaimer."""
    assert DATASET_LABEL == "TEST / SYNTHETIC DATA"
    for n in SYNTHETIC_NODES:
        assert n["dataset"] == "TEST / SYNTHETIC DATA"


def test_synthetic_dataset_entity_coverage():
    """
    Verify coverage of required entity types:
    persons, phones, vehicles, locations, accounts, organizations, events.
    """
    types_present = {n["type"] for n in SYNTHETIC_NODES}
    required_types = {"PERSON", "PHONE", "VEHICLE", "LOCATION", "ACCOUNT", "ORGANIZATION", "EVENT"}
    assert required_types.issubset(types_present), f"Missing types: {required_types - types_present}"

    # Verify at least one of each
    for req in required_types:
        nodes_of_type = [n for n in SYNTHETIC_NODES if n["type"] == req]
        assert len(nodes_of_type) >= 2, f"Expected multiple nodes for {req}, got {len(nodes_of_type)}"


def test_evidence_provenance_on_edges():
    """Verify observed edges carry explicit evidentiary provenance (FIR, CDR, Transaction, Surveillance)."""
    assert len(SYNTHETIC_OBSERVED_EDGES) >= 15
    for e in SYNTHETIC_OBSERVED_EDGES:
        assert "provenance" in e or "evidence_source" in e
        prov = e.get("provenance") or e.get("evidence_source")
        assert prov in ("FIR_102", "CDR_001", "Transaction_44", "Intercept_09"), f"Unexpected provenance: {prov}"


def test_link_prediction_known_ground_truth():
    """Verify presence of known hidden links for link prediction benchmark."""
    assert len(GROUND_TRUTH_HIDDEN_LINKS) >= 4
    for link in GROUND_TRUTH_HIDDEN_LINKS:
        assert "source" in link
        assert "target" in link
        assert link["ground_truth"] is True
        assert len(link["evidence_lead"]) > 0

        # Ensure the hidden link is NOT present in the observed training split
        for obs in SYNTHETIC_OBSERVED_EDGES:
            assert not (obs["source"] == link["source"] and obs["target"] == link["target"]), (
                f"Hidden ground truth edge ({link['source']} -> {link['target']}) must not be in observed edges!"
            )


def test_anomaly_ground_truth():
    """Verify presence of known anomaly definitions with rationale and expected score ranges."""
    assert len(GROUND_TRUTH_ANOMALIES) >= 3
    node_ids = {n["id"] for n in SYNTHETIC_NODES}
    for anom in GROUND_TRUTH_ANOMALIES:
        assert anom["entity_id"] in node_ids, f"Anomaly entity {anom['entity_id']} not in nodes!"
        assert anom["anomaly_type"] in ("STRUCTURING_MULE_VELOCITY", "HIGH_BETWEENNESS_LOW_DEGREE_CONTROLLER", "SHELL_COMPANY_CIRCULAR_ROUTING")
        assert len(anom["reason"]) > 10


def test_builtin_dataset_manager_integration():
    """Verify that BuiltinDatasetsManager successfully loads the synthetic dataset."""
    json_path = generate_synthetic_dataset_json_file()
    mgr = BuiltinDatasetsManager(connector=None, params=None, load_on_construcion=True)
    assert 'synthetic_black_falcon' in mgr.datasets
    net = mgr.datasets['synthetic_black_falcon']['data']
    assert len(net.nodes) >= 18
    assert len(net.edges) >= 15


def test_database_seeding_and_retrieval():
    """Verify seeding into live CrimeNet MySQL database."""
    service = CaseDataService()
    cid = seed_synthetic_case_into_db(service, overwrite=True)
    assert cid == CASE_ID

    c = service.get_case(cid)
    assert c is not None
    assert "TEST / SYNTHETIC DATA" in c["title"]

    ev_list = service.list_evidence(cid)
    assert len(ev_list) >= 4
    ev_types = {e["evidence_type"] for e in ev_list}
    assert {"FIR", "CDR", "TRANSACTION", "SURVEILLANCE"}.issubset(ev_types)

    alerts = service.list_alerts(cid)
    assert len(alerts) >= 3

    timeline = service.list_timeline_events(cid)
    assert len(timeline) >= 2


def test_link_prediction_evaluation_with_ground_truth():
    """Verify link prediction evaluation against known positive hidden links and negative pairs."""
    # Simulate candidate predictions that successfully discover 3 hidden links with 1 false positive
    candidate_predictions = [
        {"source": "person_amit_verma", "target": "person_vikram_malhotra", "confidence": 0.91},
        {"source": "person_rahul_sharma", "target": "org_shell_corp_global", "confidence": 0.85},
        {"source": "person_vikram_malhotra", "target": "account_icici_9933", "confidence": 0.78},
        {"source": "person_priya_patel", "target": "loc_dubai_deira", "confidence": 0.65},  # False positive
    ]

    metrics = evaluate_synthetic_link_prediction(candidate_predictions, threshold=0.5)
    assert metrics["dataset_label"] == "TEST / SYNTHETIC DATA"
    assert metrics["is_synthetic"] is True
    assert metrics["true_positives"] == 3
    assert metrics["false_negatives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["true_negatives"] == 3
    assert metrics["recall"] == 0.75
    assert metrics["precision"] == 0.75


def test_production_isolation_and_all_modalities():
    """Verify that all 12 requested modalities are demonstrated and strictly marked as synthetic."""
    # 1. Modality check
    types = {n["type"] for n in SYNTHETIC_NODES}
    assert "PERSON" in types
    assert "PHONE" in types
    assert "VEHICLE" in types
    assert "LOCATION" in types
    assert "ACCOUNT" in types
    assert "ORGANIZATION" in types
    assert "EVENT" in types

    # Evidence check
    assert len(SYNTHETIC_EVIDENCE) >= 4
    # Hidden relationships check
    assert len(GROUND_TRUTH_HIDDEN_LINKS) >= 4
    # Anomalies check
    assert len(GROUND_TRUTH_ANOMALIES) >= 3
    # Transactions check
    transactions = [e for e in SYNTHETIC_OBSERVED_EDGES if "PAID" in e["type"] or "TRANSFERRED" in e["type"] or "WIRE" in e["type"]]
    assert len(transactions) >= 3

    # 2. Strict Synthetic Guard: Never confused with real data
    assert DATASET_LABEL == "TEST / SYNTHETIC DATA"
    assert "TEST / SYNTHETIC DATA" in CASE_TITLE
    for node in SYNTHETIC_NODES:
        assert node.get("dataset") == "TEST / SYNTHETIC DATA"
