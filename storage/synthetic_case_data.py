"""
Controlled Synthetic Investigation Dataset for CrimeNet.

LABEL: TEST / SYNTHETIC DATA
DISCLAIMER: This dataset is synthetic and created strictly for automated testing,
benchmarking, and link prediction / anomaly detection evaluation.
It does NOT contain real police information and MUST NOT be used as production intelligence.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

DATASET_LABEL = "TEST / SYNTHETIC DATA"
CASE_ID = "case-synthetic-black-falcon-001"
CASE_TITLE = "[TEST / SYNTHETIC DATA] Operation Black Falcon: Hawala & Contraband Network"

# ── Ground Truth Hidden Relationships (for evaluating link prediction) ────────
# These edges exist in ground truth but are withheld from the observed graph training split.
# Models must recover these candidate edges.
GROUND_TRUTH_HIDDEN_LINKS = [
    {
        "source": "person_amit_verma",
        "target": "person_vikram_malhotra",
        "relationship_type": "COORDINATES_WITH",
        "ground_truth": True,
        "evidence_lead": "Encrypted VoIP channel metadata; both connected to burner device in Dubai.",
        "description": "Amit Verma coordinates local money distribution directly with overseas kingpin Vikram Malhotra."
    },
    {
        "source": "person_rahul_sharma",
        "target": "org_shell_corp_global",
        "relationship_type": "CASH_COURIER_FOR",
        "ground_truth": True,
        "evidence_lead": "Physical courier logs and CCTV at Chandni Chowk Hawala point.",
        "description": "Rahul Sharma delivers bulk cash drops for Shell Corp Global accounts."
    },
    {
        "source": "person_vikram_malhotra",
        "target": "account_icici_9933",
        "relationship_type": "BENEFICIAL_OWNER",
        "ground_truth": True,
        "evidence_lead": "Foreign offshore incorporation registry and nominee proxy declaration.",
        "description": "Vikram Malhotra is the ultimate beneficial owner of the ICICI corporate account."
    },
    {
        "source": "person_neha_singh",
        "target": "account_sbi_8812",
        "relationship_type": "FUNDS_CONTROLLER",
        "ground_truth": True,
        "evidence_lead": "IP address login correlation on netbanking portal.",
        "description": "Neha Singh operates the netbanking credentials for mule account SBI-8812."
    }
]

# ── Ground Truth Negative Edge Pairs (for Link Prediction specificity / ROC evaluation) ──
GROUND_TRUTH_NEGATIVE_LINKS = [
    {
        "source": "person_priya_patel",
        "target": "loc_dubai_deira",
        "relationship_type": "NO_RELATION",
        "ground_truth": False,
        "description": "Priya Patel is a domestic mule account holder with no direct offshore presence or travel."
    },
    {
        "source": "vehicle_hr26cd5678",
        "target": "loc_connaught_place",
        "relationship_type": "NO_RELATION",
        "ground_truth": False,
        "description": "Secondary transport vehicle operated strictly on interstate highway routes, never entered CP perimeter."
    },
    {
        "source": "person_neha_singh",
        "target": "phone_9899887766",
        "relationship_type": "NO_RELATION",
        "ground_truth": False,
        "description": "Neha Singh had zero telephony contact with the Dubai roaming burner device."
    },
    {
        "source": "account_sbi_8812",
        "target": "org_falcon_logistics",
        "relationship_type": "NO_RELATION",
        "ground_truth": False,
        "description": "No ledger entries or fund routing between mule account SBI-8812 and Falcon Logistics."
    }
]


def evaluate_synthetic_link_prediction(
    predicted_edges: List[Dict[str, Any]] | Dict[Tuple[str, str], float],
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Evaluates a candidate link prediction model or algorithm against known ground truth.
    Computes True Positives (recovered hidden links), False Positives, and overall benchmark recall.
    """
    if isinstance(predicted_edges, list):
        score_map = {}
        for edge in predicted_edges:
            s = edge.get("source") or edge.get("source_id")
            t = edge.get("target") or edge.get("target_id")
            score = float(edge.get("confidence") or edge.get("score") or 1.0)
            score_map[(s, t)] = score
            score_map[(t, s)] = score
    else:
        score_map = dict(predicted_edges)
        for (s, t), val in list(score_map.items()):
            score_map[(t, s)] = val

    true_positives = 0
    false_negatives = 0
    detailed_results = []

    for hidden in GROUND_TRUTH_HIDDEN_LINKS:
        s, t = hidden["source"], hidden["target"]
        score = score_map.get((s, t), 0.0)
        detected = score >= threshold
        if detected:
            true_positives += 1
        else:
            false_negatives += 1
        detailed_results.append({
            "pair": (s, t),
            "expected_ground_truth": True,
            "predicted_score": score,
            "detected": detected,
            "lead": hidden["evidence_lead"]
        })

    false_positives = 0
    true_negatives = 0
    for neg in GROUND_TRUTH_NEGATIVE_LINKS:
        s, t = neg["source"], neg["target"]
        score = score_map.get((s, t), 0.0)
        flagged = score >= threshold
        if flagged:
            false_positives += 1
        else:
            true_negatives += 1
        detailed_results.append({
            "pair": (s, t),
            "expected_ground_truth": False,
            "predicted_score": score,
            "detected": flagged,
            "lead": neg["description"]
        })

    total_positives = len(GROUND_TRUTH_HIDDEN_LINKS)
    recall = true_positives / total_positives if total_positives > 0 else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0

    return {
        "dataset_label": DATASET_LABEL,
        "is_synthetic": True,
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "detailed_evaluations": detailed_results
    }

# ── Ground Truth Anomalies (for evaluating Isolation Forest & Anomaly Detection) ─
GROUND_TRUTH_ANOMALIES = [
    {
        "entity_id": "account_sbi_8812",
        "entity_type": "ACCOUNT",
        "name": "SBI-ACC-8812 (Priya Patel)",
        "anomaly_type": "STRUCTURING_MULE_VELOCITY",
        "reason": "Sudden 4,500% turnover increase in 72 hours with instant pass-through withdrawals under Rs 50,000 threshold.",
        "expected_score_range": (0.85, 1.0)
    },
    {
        "entity_id": "person_vikram_malhotra",
        "entity_type": "PERSON",
        "name": "Vikram Malhotra",
        "anomaly_type": "HIGH_BETWEENNESS_LOW_DEGREE_CONTROLLER",
        "reason": "Disproportionate influence / betweenness centrality with minimal direct edges (broker archetype).",
        "expected_score_range": (0.80, 1.0)
    },
    {
        "entity_id": "org_shell_corp_global",
        "entity_type": "ORGANIZATION",
        "name": "Shell Corp Global",
        "anomaly_type": "SHELL_COMPANY_CIRCULAR_ROUTING",
        "reason": "Zero tax filings, residential registered address, multi-crore international wire throughput.",
        "expected_score_range": (0.80, 1.0)
    }
]

# ── Ground Truth Evidence Registry ───────────────────────────────────────────
SYNTHETIC_EVIDENCE = [
    {
        "id": "FIR_102",
        "title": "FIR No. 102/2024 - Special Cell: Unaccounted Currency Seizure",
        "evidence_type": "FIR",
        "source_ref": "FIR_102_SPECIAL_CELL",
        "content": "On 14-March-2024, a search was conducted near Connaught Place Outer Circle. Rahul Sharma was intercepted driving vehicle DL-01-AB-1234. Recovery of Rs 48 Lakhs in unaccounted cash. Rahul named Amit Verma as his coordinator and identified a Hawala hub in Chandni Chowk.",
        "filename": "FIR_102_Seizure_Memo.pdf"
    },
    {
        "id": "CDR_001",
        "title": "CDR Analysis Report - Mobile Numbers +91-9812345678 and +91-9876543210",
        "evidence_type": "CDR",
        "source_ref": "CDR_TELCO_EXTRACT_001",
        "content": "Detailed call records between Rahul Sharma (+91-9812345678) and Amit Verma (+91-9876543210). Total 48 calls recorded over 30 days, heavily clustered between 22:00 and 03:00 hrs. IMEI tracking matches towers in Chandni Chowk and Karol Bagh.",
        "filename": "CDR_001_Telco_Logs.csv"
    },
    {
        "id": "Transaction_44",
        "title": "FIU-IND Suspicious Transaction Report STR-44/2024",
        "evidence_type": "TRANSACTION",
        "source_ref": "FIU_STR_44",
        "content": "FIU-IND Suspicious Transaction Report STR-44/2024. Multi-hop money laundering sequence identified:\n1. 2024-02-20 11:15:00: Rahul Sharma loads INR 2,50,000 cash to UPI handle rahul.sharma@okhdfcbank (TxID: TXN_UPI_INTAKE_001).\n2. 2024-02-20 11:22:15: UPI transfer of INR 2,50,000 to nominal mule account SBI-ACC-8812 held by Priya Patel (TxID: UPI/20240220/889102451).\n3. 2024-02-21 14:45:00: Aggregate RTGS wire transfer of INR 25,00,000 from SBI-ACC-8812 to commercial account of Omega Exports Pvt Ltd (TxID: RTGS/20240221/SBI4401928).\n4. 2024-02-22 17:10:00: Cross-border SWIFT forex wire of USD 30,000 (~INR 25,00,000) from Omega Exports (ICICI-ACC-9933) to Shell Corp Global FZE (ACC_DXB_9921) in UAE Freezone (TxID: SWIFT/20240222/DXB881029) without trade bill of entry.",
        "filename": "FIU_STR_Transaction_44.json"
    },
    {
        "id": "Intercept_09",
        "title": "Surveillance Field Note & CCTV Log - Chandni Chowk",
        "evidence_type": "SURVEILLANCE",
        "source_ref": "CCTV_SURV_09",
        "content": "Vehicle DL-01-AB-1234 captured entering Kucha Mahajani, Chandni Chowk at 16:42. Driver Rahul Sharma handed a duffel bag to an unidentified associate linked to Falcon Logistics.",
        "filename": "Intercept_09_Field_Report.txt"
    }
]

# ── Complete Nodes Specification ─────────────────────────────────────────────
SYNTHETIC_NODES = [
    # Persons
    {
        "id": "person_rahul_sharma",
        "name": "Rahul Sharma",
        "type": "PERSON",
        "role": "Hawala Courier / Field Operative",
        "status": "ARRESTED",
        "aliases": ["Rahul", "Chhotu"],
        "dataset": DATASET_LABEL
    },
    {
        "id": "person_amit_verma",
        "name": "Amit Verma",
        "type": "PERSON",
        "role": "Regional Coordinator & Director",
        "status": "UNDER_SURVEILLANCE",
        "aliases": ["Amit Bhai", "AV"],
        "dataset": DATASET_LABEL
    },
    {
        "id": "person_vikram_malhotra",
        "name": "Vikram Malhotra",
        "type": "PERSON",
        "role": "Syndicate Kingpin / Controller",
        "status": "WANTED / LOOKOUT",
        "aliases": ["VM", "The Chairman"],
        "dataset": DATASET_LABEL
    },
    {
        "id": "person_neha_singh",
        "name": "Neha Singh",
        "type": "PERSON",
        "role": "Financial Front Administrator",
        "status": "QUESTIONED",
        "aliases": ["Neha"],
        "dataset": DATASET_LABEL
    },
    {
        "id": "person_priya_patel",
        "name": "Priya Patel",
        "type": "PERSON",
        "role": "Mule Account Holder",
        "status": "FLAGGED",
        "aliases": ["Priya"],
        "dataset": DATASET_LABEL
    },
    {
        "id": "person_tariq_ahmed",
        "name": "Tariq Ahmed",
        "type": "PERSON",
        "role": "Logistics & Transport Handler",
        "status": "UNDER_INVESTIGATION",
        "aliases": ["Tariq Transport"],
        "dataset": DATASET_LABEL
    },

    # Phones
    {
        "id": "phone_9812345678",
        "name": "+91-9812345678",
        "type": "PHONE",
        "carrier": "Airtel Delhi",
        "imei": "864192040182910",
        "dataset": DATASET_LABEL
    },
    {
        "id": "phone_9876543210",
        "name": "+91-9876543210",
        "type": "PHONE",
        "carrier": "Jio Delhi",
        "imei": "864192040998877",
        "dataset": DATASET_LABEL
    },
    {
        "id": "phone_9899887766",
        "name": "+91-9899887766",
        "type": "PHONE",
        "carrier": "Vodafone Dubai Roaming",
        "imei": "358129040112233",
        "dataset": DATASET_LABEL
    },
    {
        "id": "phone_9822334455",
        "name": "+91-9822334455",
        "type": "PHONE",
        "carrier": "Airtel Haryana",
        "imei": "358129040445566",
        "dataset": DATASET_LABEL
    },

    # Vehicles
    {
        "id": "vehicle_dl01ab1234",
        "name": "DL-01-AB-1234",
        "type": "VEHICLE",
        "model": "Toyota Fortuner (White)",
        "registration_authority": "RTO Delhi North",
        "dataset": DATASET_LABEL
    },
    {
        "id": "vehicle_hr26cd5678",
        "name": "HR-26-CD-5678",
        "type": "VEHICLE",
        "model": "Hyundai Creta (Silver)",
        "registration_authority": "RTO Gurugram",
        "dataset": DATASET_LABEL
    },

    # Locations
    {
        "id": "loc_connaught_place",
        "name": "Connaught Place, New Delhi",
        "type": "LOCATION",
        "category": "Interception / Meeting Point",
        "dataset": DATASET_LABEL
    },
    {
        "id": "loc_chandni_chowk",
        "name": "Chandni Chowk, Old Delhi",
        "type": "LOCATION",
        "category": "Hawala Market / Cash Node",
        "dataset": DATASET_LABEL
    },
    {
        "id": "loc_igi_airport",
        "name": "IGI Airport Cargo Terminal",
        "type": "LOCATION",
        "category": "Transit / Contraband Gateway",
        "dataset": DATASET_LABEL
    },
    {
        "id": "loc_dubai_deira",
        "name": "Deira Commercial District, Dubai",
        "type": "LOCATION",
        "category": "Offshore Coordination Hub",
        "dataset": DATASET_LABEL
    },

    # Accounts
    {
        "id": "account_hdfc_4491",
        "name": "HDFC-ACC-4491",
        "type": "ACCOUNT",
        "bank": "HDFC Bank Connaught Place",
        "account_type": "CURRENT",
        "dataset": DATASET_LABEL
    },
    {
        "id": "account_sbi_8812",
        "name": "SBI-ACC-8812",
        "type": "ACCOUNT",
        "bank": "State Bank of India Karol Bagh",
        "account_type": "SAVINGS (MULE)",
        "dataset": DATASET_LABEL
    },
    {
        "id": "account_icici_9933",
        "name": "ICICI-ACC-9933",
        "type": "ACCOUNT",
        "bank": "ICICI Bank Overseas Banking Unit",
        "account_type": "CORPORATE FOREX",
        "dataset": DATASET_LABEL
    },
    {
        "id": "account_upi_rahul",
        "name": "rahul.sharma@okhdfcbank",
        "type": "ACCOUNT",
        "bank": "HDFC Bank (Virtual Payment Address)",
        "account_type": "UPI ACCOUNT",
        "upi_id": "rahul.sharma@okhdfcbank",
        "vpa": "rahul.sharma@okhdfcbank",
        "holder_name": "Rahul Sharma",
        "dataset": DATASET_LABEL
    },

    # Organizations
    {
        "id": "org_omega_exports",
        "name": "Omega Exports Pvt Ltd",
        "type": "ORGANIZATION",
        "business": "Gems & Spices Trading Front",
        "cin": "U51909DL2018PTC321456",
        "dataset": DATASET_LABEL
    },
    {
        "id": "org_shell_corp_global",
        "name": "Shell Corp Global FZE",
        "type": "ORGANIZATION",
        "business": "Consulting & Holdings Shell",
        "registration": "UAE Freezone",
        "dataset": DATASET_LABEL
    },
    {
        "id": "org_falcon_logistics",
        "name": "Falcon Logistics Fleet",
        "type": "ORGANIZATION",
        "business": "Interstate Freight Transport",
        "dataset": DATASET_LABEL
    },

    # Events
    {
        "id": "event_seizure_meet",
        "name": "Seizure & Cash Intercept (14-Mar-2024)",
        "type": "EVENT",
        "timestamp": "2024-03-14 16:30:00",
        "dataset": DATASET_LABEL
    },
    {
        "id": "event_hawala_transfer",
        "name": "Hawala Bulk Transfer (22-Feb-2024)",
        "type": "EVENT",
        "timestamp": "2024-02-22 21:15:00",
        "dataset": DATASET_LABEL
    }
]

# ── Observed Edges (with explicit evidence source provenance) ─────────────────
SYNTHETIC_OBSERVED_EDGES = [
    # Communications
    {
        "source": "person_rahul_sharma",
        "target": "phone_9812345678",
        "type": "USES_PHONE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "CDR_001",
        "evidence_source": "CDR_001",
        "properties": {"frequency": "Daily", "active_since": "2023-01"}
    },
    {
        "source": "person_amit_verma",
        "target": "phone_9876543210",
        "type": "USES_PHONE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"kyc_verified": True}
    },
    {
        "source": "phone_9812345678",
        "target": "phone_9876543210",
        "type": "COMMUNICATED_WITH",
        "weight": 48.0,
        "modality": "OBSERVED",
        "provenance": "CDR_001",
        "evidence_source": "CDR_001",
        "properties": {"call_count": 48, "sms_count": 114, "duration_seconds": 14200}
    },
    {
        "source": "person_vikram_malhotra",
        "target": "phone_9899887766",
        "type": "USES_PHONE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"roaming": True}
    },
    {
        "source": "person_tariq_ahmed",
        "target": "phone_9822334455",
        "type": "USES_PHONE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {}
    },
    {
        "source": "phone_9876543210",
        "target": "phone_9822334455",
        "type": "COMMUNICATED_WITH",
        "weight": 12.0,
        "modality": "OBSERVED",
        "provenance": "CDR_001",
        "evidence_source": "CDR_001",
        "properties": {"call_count": 12}
    },

    # Financial Flows / Transactions
    {
        "source": "person_amit_verma",
        "target": "org_omega_exports",
        "type": "DIRECTOR_OF",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"shareholding_pct": 65.0}
    },
    {
        "source": "org_omega_exports",
        "target": "account_hdfc_4491",
        "type": "OPERATES_ACCOUNT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {}
    },
    {
        "source": "account_hdfc_4491",
        "target": "account_sbi_8812",
        "type": "TRANSFERRED_FUNDS",
        "weight": 2500000.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {"amount_inr": 2500000, "txn_reference": "TXN_44_OMEGA_SBI", "flagged_str": True}
    },
    {
        "source": "person_priya_patel",
        "target": "account_sbi_8812",
        "type": "NOMINAL_HOLDER",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {"is_mule": True}
    },
    {
        "source": "person_rahul_sharma",
        "target": "account_upi_rahul",
        "type": "USES_ACCOUNT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {
            "amount": 250000.0,
            "amount_inr": 250000.0,
            "currency": "INR",
            "timestamp": "2024-02-20 11:15:00",
            "source_account": "CASH_DEPOSIT",
            "destination_account": "rahul.sharma@okhdfcbank",
            "transaction_id": "TXN_UPI_INTAKE_001",
            "anomaly_indicators": ["Unverified Cash Load", "Rapid Funneling"]
        }
    },
    {
        "source": "account_upi_rahul",
        "target": "account_sbi_8812",
        "type": "PAID_VIA_UPI",
        "weight": 250000.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {
            "amount": 250000.0,
            "amount_inr": 250000.0,
            "currency": "INR",
            "timestamp": "2024-02-20 11:22:15",
            "source_account": "rahul.sharma@okhdfcbank",
            "destination_account": "SBI-ACC-8812",
            "transaction_id": "UPI/20240220/889102451",
            "anomaly_indicators": ["Rapid Layering (<10 mins)", "Mule Intake", "Velocity Anomaly"]
        }
    },
    {
        "source": "account_sbi_8812",
        "target": "org_omega_exports",
        "type": "TRANSFERRED_FUNDS",
        "weight": 2500000.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {
            "amount": 2500000.0,
            "amount_inr": 2500000.0,
            "currency": "INR",
            "timestamp": "2024-02-21 14:45:00",
            "source_account": "SBI-ACC-8812",
            "destination_account": "HDFC-ACC-4491",
            "transaction_id": "RTGS/20240221/SBI4401928",
            "is_mule_transfer": True,
            "flagged_str": True,
            "anomaly_indicators": ["Mule Pass-through", "Structuring Aggregation", "FIU STR Flagged"]
        }
    },
    {
        "source": "org_omega_exports",
        "target": "org_shell_corp_global",
        "type": "WIRE_TRANSFER",
        "weight": 30000.0,
        "modality": "OBSERVED",
        "provenance": "Transaction_44",
        "evidence_source": "Transaction_44",
        "properties": {
            "amount": 30000.0,
            "currency": "USD",
            "amount_inr": 2500000.0,
            "timestamp": "2024-02-22 17:10:00",
            "source_account": "ICICI-ACC-9933",
            "destination_account": "ACC_DXB_FREEZONE_9921",
            "transaction_id": "SWIFT/20240222/DXB881029",
            "intermediary_bank": "Standard Chartered UAE",
            "anomaly_indicators": ["Offshore Freezone Diversion", "Round-tripping Shell", "No Customs Bill of Entry"]
        }
    },
    {
        "source": "person_neha_singh",
        "target": "org_omega_exports",
        "type": "EMPLOYED_BY",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"title": "Accounts Officer"}
    },

    # Logistics & Physical Movements
    {
        "source": "person_rahul_sharma",
        "target": "vehicle_dl01ab1234",
        "type": "DRIVES_VEHICLE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"seized": True}
    },
    {
        "source": "vehicle_dl01ab1234",
        "target": "loc_chandni_chowk",
        "type": "SPOTTED_AT",
        "weight": 5.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {"frequency": 5, "cctv_confirmed": True}
    },
    {
        "source": "vehicle_dl01ab1234",
        "target": "loc_connaught_place",
        "type": "SPOTTED_AT",
        "weight": 3.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {"intercept_location": True}
    },
    {
        "source": "person_tariq_ahmed",
        "target": "vehicle_hr26cd5678",
        "type": "OPERATES_VEHICLE",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {}
    },
    {
        "source": "person_tariq_ahmed",
        "target": "org_falcon_logistics",
        "type": "ASSOCIATED_WITH",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {}
    },
    {
        "source": "org_falcon_logistics",
        "target": "loc_igi_airport",
        "type": "OPERATES_AT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {"cargo_access": True}
    },

    # Case & Event links
    {
        "source": "person_rahul_sharma",
        "target": "event_seizure_meet",
        "type": "ARRESTED_AT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {}
    },
    {
        "source": "event_seizure_meet",
        "target": "loc_connaught_place",
        "type": "OCCURRED_AT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "FIR_102",
        "evidence_source": "FIR_102",
        "properties": {}
    },
    {
        "source": "person_amit_verma",
        "target": "event_hawala_transfer",
        "type": "COORDINATED",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "CDR_001",
        "evidence_source": "CDR_001",
        "properties": {}
    },
    {
        "source": "event_hawala_transfer",
        "target": "loc_chandni_chowk",
        "type": "OCCURRED_AT",
        "weight": 1.0,
        "modality": "OBSERVED",
        "provenance": "Intercept_09",
        "evidence_source": "Intercept_09",
        "properties": {}
    }
]


def generate_synthetic_dataset_json_file(output_path: Optional[str] = None) -> str:
    """Generate the preprocessed JSON dataset file for CrimeNet BuiltinDatasetsManager."""
    if not output_path:
        root_dir = Path(__file__).resolve().parent.parent
        output_path = str(root_dir / "datasets" / "preprocessed" / "synthetic_investigation_test_data.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        # Header comment with dataset disclaimer
        f.write(f"# {DATASET_LABEL} - DO NOT USE AS REAL POLICE DATA\n")
        f.write("# Synthetic Ground Truth Dataset for Link Prediction and Anomaly Detection Benchmarking\n")

        for n in SYNTHETIC_NODES:
            line_obj = {
                "type": "node",
                "id": n["id"],
                "properties": {k: v for k, v in n.items() if k != "id"}
            }
            f.write(json.dumps(line_obj) + "\n")

        for e in SYNTHETIC_OBSERVED_EDGES:
            props = dict(e.get("properties", {}))
            props["type"] = e["type"]
            props["weight"] = e.get("weight", 1.0)
            props["modality"] = e.get("modality", "OBSERVED")
            props["provenance"] = e.get("provenance", "UNKNOWN")
            props["evidence_source"] = e.get("evidence_source", "UNKNOWN")
            line_obj = {
                "type": "edge",
                "source": e["source"],
                "target": e["target"],
                "properties": props
            }
            f.write(json.dumps(line_obj) + "\n")

    return output_path


def seed_synthetic_case_into_db(service: Any, overwrite: bool = False) -> str:
    """
    Seed the controlled synthetic investigation case into MySQL database.
    Idempotent: skips if case already exists unless overwrite=True.
    """
    existing_case = service.get_case(CASE_ID)
    if existing_case and not overwrite:
        return CASE_ID

    # 1. Create Case
    if not existing_case:
        service.create_case(
            case_id=CASE_ID,
            title=CASE_TITLE,
            case_number="FIR-TEST-FALCON-2024",
            description=(
                f"[{DATASET_LABEL}] Ground truth test case demonstrating cross-border Hawala syndicate, "
                "mule bank accounts, shell corporate entities, and physical contraband movements. "
                "Constructed specifically to evaluate Link Prediction (hidden ground truth links) "
                "and Anomaly Detection (structuring and high-betweenness brokers)."
            ),
            investigator="u-002",
            metadata={
                "is_synthetic": True,
                "label": DATASET_LABEL,
                "ground_truth_hidden_links_count": len(GROUND_TRUTH_HIDDEN_LINKS),
                "ground_truth_anomalies_count": len(GROUND_TRUTH_ANOMALIES),
            }
        )

    # 2. Insert Evidence Records
    for ev in SYNTHETIC_EVIDENCE:
        service.add_evidence(
            case_id=CASE_ID,
            title=ev["title"],
            evidence_type=ev["evidence_type"],
            source_ref=ev["source_ref"],
            content=ev["content"],
            metadata={"filename": ev["filename"], "is_synthetic": True, "label": DATASET_LABEL}
        )

    # 3. Insert Entities and Link to Case
    for n in SYNTHETIC_NODES:
        service.link_entity_to_case(
            case_id=CASE_ID,
            entity_id=n["id"],
            entity_name=n["name"],
            entity_type=n["type"],
            role=n.get("role", "ENT_NODE"),
            properties={k: v for k, v in n.items() if k not in ("id", "name", "type")}
        )

    # 4. Insert Relationships and Link to Case
    for e in SYNTHETIC_OBSERVED_EDGES:
        service.link_relationship_to_case(
            case_id=CASE_ID,
            source_id=e["source"],
            target_id=e["target"],
            relationship_type=e["type"],
            weight=float(e.get("weight", 1.0)),
            source_ref=e.get("evidence_source"),
            properties=e.get("properties", {})
        )

    # 5. Insert Timeline Events
    service.add_timeline_event(
        case_id=CASE_ID,
        event_type="SEIZURE",
        timestamp="2024-03-14 16:30:00",
        title="Physical Interception & Cash Recovery",
        description="Rahul Sharma intercepted in vehicle DL-01-AB-1234 carrying Rs 48 Lakhs unaccounted cash.",
        source_ref="FIR_102",
        primary_entity_id="person_rahul_sharma",
        secondary_entity_id="vehicle_dl01ab1234",
        confidence=1.0,
        location="Connaught Place, New Delhi"
    )
    service.add_timeline_event(
        case_id=CASE_ID,
        event_type="FINANCIAL_TRANSFER",
        timestamp="2024-02-22 14:10:00",
        title="Suspicious High-Value Transfer to Mule Account",
        description="Wire transfer of INR 25,00,000 from Omega Exports to SBI-ACC-8812 (Priya Patel).",
        source_ref="Transaction_44",
        primary_entity_id="account_hdfc_4491",
        secondary_entity_id="account_sbi_8812",
        confidence=1.0,
        location="Karol Bagh, New Delhi"
    )

    # 6. Pre-generate Ground Truth Alerts
    for anom in GROUND_TRUTH_ANOMALIES:
        service.create_alert(
            case_id=CASE_ID,
            alert_type=anom["anomaly_type"],
            severity="HIGH",
            title=f"Forensic Anomaly: {anom['name']}",
            explanation=anom["reason"],
            subject=anom["name"],
            related_entities=[anom["entity_id"]]
        )

    # 7. Seed Canonical Analysis Results (for ANALYSIS_RUN timeline events)
    try:
        with service._get_connection() as conn:
            with conn.cursor() as cur:
                # Mark evidence extraction as completed
                cur.execute(
                    """UPDATE evidence 
                       SET extraction_status = 'Completed', 
                           entity_count = %s, relation_count = %s 
                       WHERE case_id = %s;""",
                    (len(SYNTHETIC_NODES), len(SYNTHETIC_OBSERVED_EDGES), CASE_ID)
                )

                # Seed analysis results
                analysis_seeds = [
                    (
                        "task_louvain_001", CASE_ID, "task_louvain_001", "Louvain Community Detection",
                        json.dumps({"resolution": 1.0, "random_state": 42}),
                        "Discovered 3 operational syndicate communities: Hawala Cash Cell, Omega Corporate Layer, and Falcon Transport Fleet.",
                        "system-engine", datetime.now()
                    ),
                    (
                        "task_iso_forest_002", CASE_ID, "task_iso_forest_002", "Isolation Forest Anomaly Detection",
                        json.dumps({"contamination": 0.12, "n_estimators": 100}),
                        "Flagged 3 critical network anomalies: SBI-ACC-8812 (Mule structuring), Vikram Malhotra (Broker centrality), and Shell Corp Global (Offshore shell).",
                        "system-engine", datetime.now()
                    ),
                    (
                        "task_betweenness_003", CASE_ID, "task_betweenness_003", "Betweenness Centrality Analysis",
                        json.dumps({"normalized": True}),
                        "Identified Amit Verma and Vikram Malhotra as top structural bridge entities between field logistics and offshore routing.",
                        "system-engine", datetime.now()
                    ),
                ]
                for aid, cid, tid, algo, params, summ, exec_by, dt in analysis_seeds:
                    cur.execute(
                        """INSERT INTO analysis_results (id, case_id, task_id, algorithm, parameters, summary, executed_by, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE summary=VALUES(summary);""",
                        (aid, cid, tid, algo, params, summ, exec_by, dt)
                    )

                # Seed AI predicted link hypothesis (for POTENTIAL_LINK_GENERATED timeline event)
                cur.execute(
                    """INSERT INTO entity_relationships 
                       (id, case_id, source_entity_id, target_entity_id, relationship_type, confidence, predicted, is_predicted, properties, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE confidence=VALUES(confidence);""",
                    (
                        "rel_pred_rahul_vikram", CASE_ID, "person_rahul_sharma", "person_vikram_malhotra",
                        "POTENTIAL_ASSOCIATE", 0.82, 1, 1,
                        json.dumps({
                            "modality": "PREDICTED", "acceptance": "PROPOSED", "confidence": 0.82,
                            "provenance": {"source_file": "Graph Topology Link Prediction", "algorithm": "Adamic-Adar"}
                        }),
                        datetime.now()
                    )
                )

                # Seed Investigator Review & Actions
                audit_seeds = [
                    ("aud_rev_cdr", "EVIDENCE_VIEWED", "EVIDENCE", "CDR_001", "lead_investigator", "Investigator reviewed telephony logs for +91-9812345678"),
                    ("aud_rev_str", "EVIDENCE_VIEWED", "EVIDENCE", "Transaction_44", "lead_investigator", "Investigator reviewed FIU-IND Suspicious Transaction Report STR-44/2024"),
                    ("aud_alert_rev", "ALERT_REVIEWED", "ALERT", "account_sbi_8812", "lead_investigator", "Investigator reviewed Mule Account Anomaly for SBI-ACC-8812"),
                    ("aud_act_subpoena", "INVESTIGATION_ACTION_CREATED", "ACTION", "act_subpoena_hdfc", "lead_investigator", "Issued Section 91 CrPC notice for bank statements"),
                    ("aud_query_001", "QUERY_SUBMITTED", "QUERY", "q_001", "lead_investigator", "What are the primary communication links for Rahul Sharma?"),
                ]
                for aid, act, rtype, rid, uname, details in audit_seeds:
                    service.record_audit(
                        user_id=uname,
                        action=act,
                        resource_type=rtype,
                        resource_id=rid,
                        case_id=CASE_ID,
                        details=details,
                        username=uname
                    )

                # Seed Human-in-the-loop Feedback & Verified Corrections
                cur.execute(
                    """INSERT INTO feedback (id, case_id, feedback_type, target_id, action, notes, user_id, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE notes=VALUES(notes);""",
                    (
                        "fb_pred_link_001", CASE_ID, "LINK_PREDICTION", "rel_pred_rahul_vikram",
                        "ACCEPTED", "Corroborated by Intercept_09 surveillance report.", "lead_investigator", datetime.now()
                    )
                )

                # Seed Canonical Example: AI claimed "Rahul is connected to Phone 9876." -> Corrected to "Phone belongs to Amit."
                cur.execute(
                    """INSERT INTO feedback 
                       (id, case_id, feedback_type, target_id, action, notes, user_id, 
                        original_ai_result, corrected_value, reason, source_ref, correction_status, audit_id, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE corrected_value=VALUES(corrected_value), notes=VALUES(notes);""",
                    (
                        "fb_corr_phone_ownership_001", CASE_ID, "HUMAN_CORRECTION", "Phone +91 98765 43210",
                        "ACCEPTED", "Customer Acquisition Form (CAF) and biometric KYC verification in FIR_102 confirm Amit Verma is registered subscriber, not Rahul Sharma.",
                        "Inspector Sandeep Verma",
                        "Rahul is connected to Phone 9876.", "Phone belongs to Amit.",
                        "Customer Acquisition Form (CAF) and biometric KYC verification in FIR_102 confirm Amit Verma is registered subscriber, not Rahul Sharma.",
                        "FIR_102 / CAF_TELCO_REG_99", "ACCEPTED", "aud_fb_phone_corr_001", datetime.now()
                    )
                )
                cur.execute(
                    """INSERT INTO audit_logs 
                       (id, user_id, action, resource_type, resource_id, case_id, target, old_value, new_value, source_ref, result_id, details, timestamp, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE details=VALUES(details);""",
                    (
                        "aud_fb_phone_corr_001", "Inspector Sandeep Verma", "CORRECTION_SUBMITTED", "FEEDBACK",
                        "fb_corr_phone_ownership_001", CASE_ID, "Phone +91 98765 43210",
                        "Rahul is connected to Phone 9876.", "Phone belongs to Amit.",
                        "FIR_102 / CAF_TELCO_REG_99", "fb_corr_phone_ownership_001",
                        "Human-in-the-loop correction: Phone 9876 belongs to Amit Verma (CAF verified).",
                        datetime.now(), datetime.now()
                    )
                )


                # Seed Investigation Report
                cur.execute(
                    """INSERT INTO reports (id, case_id, title, content, report_type, generated_by, created_at, format)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE title=VALUES(title);""",
                    (
                        "rep_falcon_brief_001", CASE_ID, "Operation Black Falcon Comprehensive Brief",
                        "Comprehensive inter-agency intelligence brief on Hawala contraband network.",
                        "INVESTIGATION_BRIEF", "lead_investigator", datetime.now(), "PDF"
                    )
                )

    except Exception as exc:
        import logging
        logging.getLogger("CrimeNet.SyntheticSeed").warning("Timeline enrich seeding failed: %s", exc)

    # 8. Seed Investigation Action Workflows (Internal Prototypes: Lookout, Freeze, Review, Escalate)
    try:
        action_seeds = [
            (
                "LOOKOUT_REQUEST", "Vikram Malhotra", "PERSON",
                "Primary suspect identified in Hawala syndicate with active passport; intercepted voice calls suggest flight risk to Dubai. Border control alert requested.",
                "CDR_001", "APPROVED", "Approved by Special CP for internal immigration monitoring."
            ),
            (
                "ACCOUNT_FREEZE_REQUEST", "Mule Account 33190 (HDFC Bank)", "BANK_ACCOUNT",
                "Section 102 CrPC debit freeze requested. Account exhibits rapid 45,00,000 INR layering dispersal to offshore shells within 180 seconds.",
                "Bank_Ledger_2026.csv", "APPROVED", "Bank nodal officer notified; debit freeze active."
            ),
            (
                "MARK_FOR_REVIEW", "Falcon Global Trading LLC (Shell Corp)", "ORGANIZATION",
                "Shell company registered at residential address with 22 Crore INR transaction throughput and zero commercial footprint. Priority supervisory review flagged.",
                "ROC_Filing_2024.pdf", "PENDING_APPROVAL", None
            ),
            (
                "ESCALATE_CASE", "Black Falcon Multi-Jurisdictional Hawala Network", "CASE_MODULE",
                "Cross-border fund flow tracing confirms foreign currency layering exceeding 50 Crore INR across UAE and Mauritius conduits. Escalated to Enforcement Directorate and FIU-IND.",
                "Interim_Investigation_FIR.pdf", "APPROVED", "Transferred to Special Central Economic Offences Wing."
            ),
            (
                "SURVEILLANCE_REQUEST", "Suspect Phone +91 98201 99887", "PHONE",
                "Technical surveillance authorization requested under Section 5(2) Indian Telegraph Act for active communication intercept with overseas operators.",
                "Telco_Tower_Dump.csv", "PENDING_APPROVAL", None
            ),
        ]
        existing_actions = {a["target_entity"]: a for a in service.list_investigation_actions(CASE_ID)}
        for atype, atarget, atarget_type, areason, aev, astatus, anotes in action_seeds:
            if atarget not in existing_actions:
                act_id = service.create_investigation_action(
                    case_id=CASE_ID,
                    action_type=atype,
                    target_entity=atarget,
                    target_entity_type=atarget_type,
                    reason=areason,
                    related_evidence=aev,
                    investigator_id="lead_investigator",
                    notes=anotes
                )
                if astatus != "PENDING_APPROVAL":
                    service.update_investigation_action_status(
                        action_id=act_id,
                        status=astatus,
                        notes=anotes or f"Marked {astatus} during synthetic case initialization.",
                        investigator_id="supervisor-001"
                    )
    except Exception as a_exc:
        import logging
        logging.getLogger("CrimeNet.SyntheticSeed").warning("Investigation actions seeding failed: %s", a_exc)


    # 8. Record Audit Trail Initialization
    service.record_audit(
        user_id="system-seed",
        action="SYNTHETIC_DATASET_INITIALIZED",
        resource_type="CASE",
        resource_id=CASE_ID,
        case_id=CASE_ID,
        target=CASE_TITLE,
        details=f"Initialized {DATASET_LABEL} with {len(SYNTHETIC_NODES)} nodes, {len(SYNTHETIC_OBSERVED_EDGES)} edges, and {len(GROUND_TRUTH_HIDDEN_LINKS)} ground truth hidden links."
    )

    return CASE_ID
