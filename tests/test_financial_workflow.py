"""Tests for Dedicated Financial Investigation Workflow.

Verifies:
- Account nodes and transaction relationships
- Amount, currency, timestamp, source account, destination account, transaction ID
- Multi-hop fund flow tracing (Forward, Backward)
- Canonical Person ➔ UPI ➔ Mule ➔ Company ➔ Offshore pipeline
- Automated anomaly indicators (Rapid Layering, Mule Intake, Offshore Freezone Flight)
- Cytoscape graph canvas money-flow highlighting with formatted amount labels
"""

import pytest
from typing import Dict, Any, List

from analyzer.financial_investigation import (
    FinancialInvestigationService,
    FinancialTransaction,
    FinancialPath,
    FinancialAccountSummary,
)
from visualizer.financial_workflow_panel import (
    build_financial_workflow_modal,
    render_transaction_hop_card,
)
from storage.synthetic_case_data import CASE_ID, seed_synthetic_case_into_db
from storage.case_data_service import CaseDataService


@pytest.fixture(scope="module")
def setup_case():
    """Ensure synthetic case with financial entities is seeded."""
    cds = CaseDataService()
    cid = seed_synthetic_case_into_db(cds, overwrite=False)
    return cid


def test_account_nodes_retrieval(setup_case):
    """Test retrieval and categorization of financial accounts."""
    case_id = setup_case
    svc = FinancialInvestigationService()
    accounts = svc.get_account_nodes(case_id)

    assert len(accounts) >= 3, "Expected at least 3 account/financial nodes"
    acc_map = {a.entity_id: a for a in accounts}

    # 1. UPI Account
    assert "account_upi_rahul" in acc_map
    upi_acc = acc_map["account_upi_rahul"]
    assert "upi" in upi_acc.account_type.lower() or "rahul" in upi_acc.name.lower()
    assert "okhdfcbank" in upi_acc.account_number

    # 2. Mule Account
    assert "account_sbi_8812" in acc_map
    mule_acc = acc_map["account_sbi_8812"]
    assert mule_acc.is_mule is True, "SBI-ACC-8812 must be flagged as a Mule account"
    assert "SAVINGS (MULE)" in mule_acc.account_type or "mule" in mule_acc.name.lower()

    # 3. Offshore Entity / Account
    assert "org_shell_corp_global" in acc_map or any(a.is_offshore for a in accounts)


def test_financial_transactions_provenance(setup_case):
    """Test all required transaction specification fields."""
    case_id = setup_case
    svc = FinancialInvestigationService()
    txns = svc.get_financial_transactions(case_id)

    assert len(txns) >= 4, "Expected at least 4 financial transactions in case"

    for t in txns:
        # Core fields verification
        assert t.id, "Must have relation ID"
        assert t.transaction_id, "Must have transaction ID"
        assert t.source_id, "Must have source ID"
        assert t.target_id, "Must have target ID"
        assert t.source_account, "Must have source account"
        assert t.destination_account, "Must have destination account"
        assert t.amount >= 0, "Must have non-negative amount"
        assert t.currency in ("INR", "USD", "EUR", "AED"), f"Unexpected currency {t.currency}"
        assert t.timestamp, "Must have timestamp"
        assert t.date, "Must have date"
        assert t.evidence_source, "Must cite supporting evidence source"
        assert t.modality == "OBSERVED", "Synthetic financial transactions are observed facts"

    # Specific check for UPI transaction
    upi_txns = [t for t in txns if "UPI" in t.relationship_type or "upi" in t.source_id]
    assert len(upi_txns) >= 1, "Must contain at least one UPI transfer"
    upi_t = upi_txns[0]
    assert "2024" in upi_t.date
    assert upi_t.amount > 0


def test_canonical_five_tier_laundering_pipeline(setup_case):
    """Test tracing the canonical Person -> UPI -> Mule -> Company -> Offshore pipeline."""
    case_id = setup_case
    svc = FinancialInvestigationService()
    canonical_paths = svc.get_canonical_investigation_paths(case_id)

    assert len(canonical_paths) >= 1, "Must discover the canonical 5-tier laundering pipeline"
    primary_path = canonical_paths[0]

    assert primary_path.is_canonical is True
    assert primary_path.hops >= 4, f"Expected at least 4 hops, got {primary_path.hops}"

    # Verify sequential node chain
    node_ids = primary_path.node_ids
    assert node_ids[0] == "person_rahul_sharma", "Path must begin with Person (Rahul Sharma)"
    assert "account_upi_rahul" in node_ids, "Path must pass through UPI Account"
    assert "account_sbi_8812" in node_ids, "Path must pass through Mule Account (SBI-ACC-8812)"
    assert "org_omega_exports" in node_ids, "Path must pass through Company (Omega Exports Pvt Ltd)"
    assert node_ids[-1] == "org_shell_corp_global", "Path must terminate at Offshore Entity (Shell Corp Global FZE)"

    # Total amount check
    assert primary_path.total_amount_inr >= 2500000.0, "Total amount should reflect the transfer volume"
    assert len(primary_path.currencies) >= 1


def test_multi_hop_fund_flow_tracing(setup_case):
    """Test forward and backward fund flow traversal."""
    case_id = setup_case
    svc = FinancialInvestigationService()

    # 1. Forward tracing from UPI account
    forward_paths = svc.trace_money_flow(
        case_id=case_id,
        start_entity_id="account_upi_rahul",
        direction="forward",
        max_hops=4
    )
    assert len(forward_paths) >= 1
    assert any("org_shell_corp_global" in p.node_ids for p in forward_paths)

    # 2. Backward tracing from Offshore Entity (finding funding sources)
    backward_paths = svc.trace_money_flow(
        case_id=case_id,
        start_entity_id="org_shell_corp_global",
        direction="backward",
        max_hops=4
    )
    assert len(backward_paths) >= 1
    assert any("org_omega_exports" in p.node_ids for p in backward_paths)


def test_automated_anomaly_detection(setup_case):
    """Test automated detection of statutory financial anomalies along the money flow."""
    case_id = setup_case
    svc = FinancialInvestigationService()
    canonical_paths = svc.get_canonical_investigation_paths(case_id)
    assert canonical_paths

    path = canonical_paths[0]
    anomalies = path.anomaly_indicators

    assert len(anomalies) >= 2, f"Expected multiple anomaly flags on canonical path, got {anomalies}"
    # Check for rapid layering / velocity anomaly
    assert any("Layering" in a or "Velocity" in a for a in anomalies), "Must flag rapid velocity layering"
    # Check for mule account intake
    assert any("Mule" in a for a in anomalies), "Must flag mule account involvement"
    # Check for offshore flight
    assert any("Offshore" in a or "Tax-Haven" in a for a in anomalies), "Must flag offshore flight"


def test_cyto_money_flow_highlight_generation(setup_case):
    """Test Cytoscape graph canvas money-flow highlighting element transformation."""
    case_id = setup_case
    svc = FinancialInvestigationService()
    canonical_paths = svc.get_canonical_investigation_paths(case_id)
    assert canonical_paths

    path = canonical_paths[0]

    # Mock Cytoscape graph elements
    mock_elements = [
        {"group": "nodes", "data": {"id": "person_rahul_sharma", "name": "Rahul Sharma", "type": "PERSON"}},
        {"group": "nodes", "data": {"id": "account_upi_rahul", "name": "rahul.sharma@okhdfcbank", "type": "ACCOUNT"}},
        {"group": "nodes", "data": {"id": "account_sbi_8812", "name": "SBI-ACC-8812", "type": "ACCOUNT", "account_type": "SAVINGS (MULE)"}},
        {"group": "nodes", "data": {"id": "org_omega_exports", "name": "Omega Exports Pvt Ltd", "type": "ORGANIZATION"}},
        {"group": "nodes", "data": {"id": "org_shell_corp_global", "name": "Shell Corp Global FZE", "type": "ORGANIZATION"}},
        {"group": "nodes", "data": {"id": "phone_9876543210", "name": "+91-9876543210", "type": "PHONE"}},  # Unrelated node
        {"group": "edges", "data": {"id": "e1", "source": "person_rahul_sharma", "target": "account_upi_rahul"}},
        {"group": "edges", "data": {"id": "e2", "source": "account_upi_rahul", "target": "account_sbi_8812"}},
        {"group": "edges", "data": {"id": "e3", "source": "account_sbi_8812", "target": "org_omega_exports"}},
        {"group": "edges", "data": {"id": "e4", "source": "org_omega_exports", "target": "org_shell_corp_global"}},
        {"group": "edges", "data": {"id": "e5", "source": "person_rahul_sharma", "target": "phone_9876543210"}},  # Unrelated edge
    ]

    highlighted, stats = svc.build_cyto_highlight_elements(path, mock_elements)

    assert stats["total_nodes"] == 5
    assert stats["total_edges"] == 4

    # Verify classes applied to nodes
    for el in highlighted:
        if el.get("group") == "nodes":
            nid = el["data"]["id"]
            if nid == "account_sbi_8812":
                assert "crimenet-mule-node" in el["classes"], "Mule account must have crimenet-mule-node class"
            elif nid == "org_shell_corp_global":
                assert "crimenet-offshore-node" in el["classes"], "Offshore node must have crimenet-offshore-node class"
            elif nid in path.node_ids:
                assert "crimenet-money-node" in el["classes"]
            else:
                assert "crimenet-dimmed" in el["classes"], "Unrelated nodes must be dimmed"

        elif el.get("group") == "edges":
            src = el["data"]["source"]
            tgt = el["data"]["target"]
            if (src, tgt) in [("person_rahul_sharma", "account_upi_rahul"),
                              ("account_upi_rahul", "account_sbi_8812"),
                              ("account_sbi_8812", "org_omega_exports"),
                              ("org_omega_exports", "org_shell_corp_global")]:
                assert "crimenet-money-edge" in el["classes"]
                assert "money_label" in el["data"], "Highlighted money edges must have formatted amount label"
            else:
                assert "crimenet-dimmed" in el["classes"], "Unrelated edges must be dimmed"


def test_financial_workflow_modal_layout():
    """Test that the Financial Workflow Modal renders cleanly with all required components."""
    modal = build_financial_workflow_modal()
    assert modal is not None

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

    collect_text(modal)
    all_text = " ".join(text_blobs)

    assert "FINANCIAL INVESTIGATION WORKFLOW" in all_text
    assert "Multi-Hop Fund Flow Tracing" in all_text
    assert "Highlight Money Flow on Graph" in all_text
