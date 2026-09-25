"""
Comprehensive test suite verifying:
1. Grounded Q&A for "Why is Rahul connected to Amit?"
   - Multi-modal corroboration: Telecom (CDR_001), FIR (FIR_102), Financial (Transaction_44)
   - Structured sources extraction
   - Explicit Sources section in output
   - Prominent evidentiary disclaimer
2. GraphRAG Search Modes (local, basic, drift, global):
   - Structured sources preservation
   - Rich source_context extraction with snippets
   - Evidentiary disclaimer inclusion
3. Human-in-the-Loop Ground Truth Integration:
   - Active corrections surfaced as context, not model retraining
"""
import pytest
from analyzer.investigation_agent import (
    run_investigation,
    extract_supporting_sources,
    _grounded_local_investigation_answer,
)
from storage.case_data_service import CaseDataService
from storage.synthetic_case_data import CASE_ID


@pytest.fixture(scope="module")
def case_id():
    return CASE_ID


class TestRahulAmitConnectionCorroboration:
    """Verify the canonical 'Why is Rahul connected to Amit?' Q&A pipeline."""

    def test_run_investigation_rahul_amit(self, case_id):
        res = run_investigation("Why is Rahul connected to Amit?", case_id=case_id)
        assert res is not None
        answer = res.get("answer", "")
        sources = res.get("sources", [])

        # 1. Assert multi-modal corroboration
        assert "CDR_001" in answer
        assert "FIR_102" in answer or "FIR No. 102" in answer or "FIR_102_SPECIAL_CELL" in answer
        assert "Transaction_44" in answer

        # 2. Assert explicit Sources section
        assert "Sources:" in answer
        assert "- CDR_001" in answer
        assert "- Transaction_44" in answer

        # 3. Assert Evidentiary Notice disclaimer
        assert "Evidentiary Notice" in answer
        assert "not verified legal facts" in answer

        # 4. Assert structured sources returned
        source_refs = [s.get("source_ref") for s in sources]
        assert "CDR_001" in source_refs
        assert "Transaction_44" in source_refs
        assert any("FIR_102" in str(r) for r in source_refs)

    def test_grounded_local_answer_rahul_amit(self, case_id):
        res = _grounded_local_investigation_answer("Why is Rahul connected to Amit?", case_id=case_id)
        answer = res.get("answer", "")
        sources = res.get("sources", [])

        # Check all three evidentiary modalities are explained
        assert "Telecommunications Corroboration" in answer
        assert "48 calls" in answer or "SMS" in answer
        assert "Corporate & Case Interception" in answer
        assert "Financial Money Laundering Trail" in answer

        # Check sources
        source_refs = [s.get("source_ref") for s in sources]
        assert "CDR_001" in source_refs
        assert "Transaction_44" in source_refs

    def test_hitl_override_with_rahul_amit_query(self, case_id):
        svc = CaseDataService()
        # Submit a human correction
        fb_id = svc.record_human_correction(
            case_id=case_id,
            target_id="Rahul is connected to Phone 9876",
            original_ai_result="Rahul is connected to Phone 9876",
            corrected_value="Phone belongs to Amit (Verified Subscriber KYC)",
            reason="CAF record CAF_TELCO_REG_99 verifies Amit is legal subscriber",
            source_ref="CAF_TELCO_REG_99",
            investigator_id="inv_inspector_malik",
        )
        assert fb_id is not None

        # Ask question
        res = run_investigation("Is Rahul connected to Phone 9876?", case_id=case_id)
        ans = res.get("answer", "")

        # Verify ground truth is prepended
        assert "HUMAN-VERIFIED CORRECTION" in ans
        assert "Phone belongs to Amit" in ans
        assert "CAF_TELCO_REG_99" in ans
        # Verify no false claim of retraining
        assert "retrained" in ans.lower() or "retrain" in ans.lower()
        assert "not been retrained" in ans


class TestGraphRAGSourceContextAndDisclaimers:
    """Verify GraphRAG engine sources, source_context, and disclaimers."""

    def test_graphrag_local_search_sources(self, case_id):
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id, offline_mode=True)
        res = rag.query("Who is Rahul Sharma connected to?", mode="local")

        assert "response" in res
        assert "sources" in res
        assert "source_context" in res
        assert "Evidentiary Notice" in res["response"]
        assert len(res["sources"]) > 0
        assert len(res["source_context"]) > 0
        # Check source_context item structure
        ctx0 = res["source_context"][0]
        assert "source_ref" in ctx0
        assert "snippet" in ctx0

    def test_graphrag_basic_search_sources(self, case_id):
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id, offline_mode=True)
        res = rag.query("currency seizure hawala", mode="basic")

        assert "response" in res
        assert "sources" in res
        assert "source_context" in res
        assert "Evidentiary Notice" in res["response"]
        assert len(res["sources"]) > 0

    def test_graphrag_drift_search_sources(self, case_id):
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id, offline_mode=True)
        res = rag.query("Rahul Sharma Amit Verma syndicate", mode="drift")

        assert "response" in res
        assert "sources" in res
        assert "source_context" in res
        assert "Evidentiary Notice" in res["response"]

    def test_graphrag_global_search_sources(self, case_id):
        from storage.crimenet_graphrag import CrimeNetGraphRAG
        rag = CrimeNetGraphRAG(case_id=case_id, offline_mode=True)
        res = rag.query("summarize syndicate structure", mode="global")

        assert "response" in res
        assert "sources" in res
        assert "source_context" in res
        assert "Evidentiary Notice" in res["response"]
