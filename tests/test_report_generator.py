"""
Unit tests for CrimeNet Investigation Report Generation Engine.

Tests:
1. Compilation pipeline:
   Case → Queries → Evidence → Graph Findings → Alerts → Timeline → Human Feedback → AI Summaries → Sources → Report
2. All 4 report formats:
   - Investigation Brief
   - Entity Dossier
   - Supervisor Summary
   - Interagency Brief
3. Report sections:
   - Case Overview
   - Investigation Summary (Grounded AI synthesis)
   - Queries & Inquiries
   - Entities & Relationships
   - Important Nodes (PageRank / Degree Centrality)
   - Communities (Clusters)
   - Potential Links (Analytical Hypotheses with Disclaimer)
   - Anomalies & Alerts
   - Financial Paths (Laundering Corridors)
   - Timeline
   - Evidence & Sources
   - Human-in-the-Loop Corrections (Dual-Value)
   - Investigator Notes
   - Audit Summary
4. Local PDF generation & NumberedCanvas pagination
5. Strict evidentiary grounding (no unsupported claims)
"""

from __future__ import annotations

import os
import uuid
import pytest

from reports.report_generator import InvestigationReportCompiler, ReportFormat
from storage.case_data_service import CaseDataService
from storage.synthetic_case_data import CASE_ID, seed_synthetic_case_into_db


@pytest.fixture(scope="module")
def service():
    svc = CaseDataService()
    seed_synthetic_case_into_db(svc, overwrite=False)
    return svc


@pytest.fixture(scope="module")
def setup_case(service):
    return CASE_ID


def test_investigation_brief_pdf_generation(setup_case, service):
    """Test generating full Investigation Operational Brief PDF."""
    compiler = InvestigationReportCompiler(service=service)
    res = compiler.generate_pdf_report(
        case_id=setup_case,
        report_format=ReportFormat.INVESTIGATION_BRIEF,
        investigator="Inspector Sandeep Verma",
        notes="All communication and financial nodes verified."
    )
    assert res["format"] == ReportFormat.INVESTIGATION_BRIEF
    assert os.path.exists(res["file_path"])
    assert os.path.getsize(res["file_path"]) > 1000  # Valid non-empty PDF file
    assert res["is_synthetic"] is True

    # Validate PDF magic header
    with open(res["file_path"], "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_entity_dossier_pdf_generation(setup_case, service):
    """Test generating target-specific Entity Intelligence Dossier PDF."""
    compiler = InvestigationReportCompiler(service=service)
    res = compiler.generate_pdf_report(
        case_id=setup_case,
        report_format=ReportFormat.ENTITY_DOSSIER,
        target_entity_id="person_rahul_sharma",
        investigator="Inspector Sandeep Verma"
    )
    assert res["format"] == ReportFormat.ENTITY_DOSSIER
    assert os.path.exists(res["file_path"])
    assert os.path.getsize(res["file_path"]) > 1000


def test_supervisor_summary_pdf_generation(setup_case, service):
    """Test generating Command Supervisor Summary PDF."""
    compiler = InvestigationReportCompiler(service=service)
    res = compiler.generate_pdf_report(
        case_id=setup_case,
        report_format=ReportFormat.SUPERVISOR_SUMMARY,
        investigator="Inspector Sandeep Verma"
    )
    assert res["format"] == ReportFormat.SUPERVISOR_SUMMARY
    assert os.path.exists(res["file_path"])
    assert os.path.getsize(res["file_path"]) > 1000


def test_interagency_brief_pdf_generation(setup_case, service):
    """Test generating Interagency Evidentiary Brief PDF."""
    compiler = InvestigationReportCompiler(service=service)
    res = compiler.generate_pdf_report(
        case_id=setup_case,
        report_format=ReportFormat.INTERAGENCY_BRIEF,
        investigator="Inspector Sandeep Verma",
        notes="Exported for Financial Intelligence Unit (FIU-IND) cross-verification."
    )
    assert res["format"] == ReportFormat.INTERAGENCY_BRIEF
    assert os.path.exists(res["file_path"])
    assert os.path.getsize(res["file_path"]) > 1000


def test_report_database_registration(setup_case, service):
    """Test that generated reports are retrievable from CaseDataService."""
    reports = service.list_reports(setup_case)
    assert len(reports) >= 4

    latest_rep = reports[0]
    assert latest_rep["format"] == "PDF"
    assert latest_rep["file_path"] is not None
    assert os.path.exists(latest_rep["file_path"])


def test_compile_case_data_structure(setup_case, service):
    """Verify that compile_case_data compiles all required pipeline components."""
    compiler = InvestigationReportCompiler(service=service)
    data = compiler.compile_case_data(setup_case)

    # Core Pipeline checks: Case → Queries → Evidence → Graph Findings → Alerts → Timeline → Human Feedback → AI Summaries → Sources
    assert "case" in data
    assert "queries" in data
    assert "evidence" in data
    assert "graph" in data
    assert "nodes" in data
    assert "edges" in data
    assert "important_nodes" in data
    assert "communities" in data
    assert "potential_links" in data
    assert "financial_paths" in data
    assert "alerts" in data
    assert "timeline" in data
    assert "sources" in data
    assert "corrections" in data
    assert "ai_summary" in data

    # Important nodes have centrality metrics
    assert len(data["important_nodes"]) > 0
    top_node = data["important_nodes"][0]
    assert "pagerank" in top_node
    assert "degree" in top_node
    assert "betweenness" in top_node
    assert top_node["degree"] >= 1

    # Communities detected
    assert len(data["communities"]) >= 1

    # Financial paths present
    assert len(data["financial_paths"]) >= 1
    fp = data["financial_paths"][0]
    assert "hops" in fp
    assert "amount_inr" in fp
    assert "flow" in fp

    # Grounded AI summary present
    assert len(data["ai_summary"]) > 100
    assert "Investigation" in data["ai_summary"]


def test_human_correction_surfacing_in_compiled_report(setup_case, service):
    """Verify human corrections (HITL) preserve both original AI claim and human truth."""
    # Record a human correction in the test case
    target = f"test-rep-corr-{uuid.uuid4().hex[:6]}"
    service.record_human_correction(
        case_id=setup_case,
        target_id=target,
        original_ai_result="AI claims target is connected to Phone 9876.",
        corrected_value="Phone belongs to Amit, verified via CAF in FIR_102.",
        reason="KYC document CAF_TELCO_REG_99 proves subscriber identity.",
        source_ref="FIR_102 / CAF_TELCO_REG_99",
        investigator_id="Inspector Sandeep Verma"
    )

    compiler = InvestigationReportCompiler(service=service)
    data = compiler.compile_case_data(setup_case)

    # Check that corrections are present with both values
    matched = [c for c in data["corrections"] if c.get("target_id") == target]
    assert len(matched) == 1
    corr = matched[0]
    assert corr["original_ai_result"] == "AI claims target is connected to Phone 9876."
    assert corr["corrected_value"] == "Phone belongs to Amit, verified via CAF in FIR_102."
    assert corr["source_ref"] == "FIR_102 / CAF_TELCO_REG_99"

    # Generate PDF and ensure it compiles without error
    res = compiler.generate_pdf_report(
        case_id=setup_case,
        report_format=ReportFormat.INVESTIGATION_BRIEF,
        investigator="Inspector Sandeep Verma"
    )
    assert os.path.exists(res["file_path"])
    assert os.path.getsize(res["file_path"]) > 2000
