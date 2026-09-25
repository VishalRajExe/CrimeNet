"""
Unit and Integration Tests for CrimeNet RAG & Agentic Backend
"""

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.config import CRIMENET_API_KEY
from backend.extraction.indian_regex import IndianRegexExtractor
from backend.extraction.ner_extractor import NarrativeExtractor
from backend.rag.document_loader import DocumentLoader
from backend.rag.chunker import DocumentChunker
from backend.rag.vector_store import VectorStore
from backend.agents.financial_agent import FinancialAgent
from backend.agents.feedback_agent import FeedbackAgent


@pytest.fixture
def client():
    return TestClient(
        app,
        headers={
            "X-API-Key": CRIMENET_API_KEY,
            "X-Officer-Badge": "INSP-4409",
        },
    )


def test_indian_regex_phone():
    text = "Call suspect at +91-9876543210 or 8765432109 immediately."
    tokens = IndianRegexExtractor.extract_all(text)
    phones = [t.normalized_value for t in tokens if t.token_type == "PHONE"]
    assert "9876543210" in phones
    assert "8765432109" in phones


def test_indian_regex_upi_and_vehicle():
    text = "Send 15L to vikram@okhdfcbank. White Fortuner MH04AB9901 seen near toll."
    tokens = IndianRegexExtractor.extract_all(text)
    upis = [t.normalized_value for t in tokens if t.token_type == "UPI_ACCOUNT"]
    vehicles = [t.normalized_value for t in tokens if t.token_type == "VEHICLE"]
    assert "vikram@okhdfcbank" in upis
    assert "MH04AB9901" in vehicles


def test_ner_extraction():
    narrative = "Suspect Vikram Malhotra operates UPI vikram@okhdfcbank and drove MH04AB9901 in Surat."
    extractor = NarrativeExtractor()
    result = extractor.extract_from_narrative(narrative, case_id="TEST-01")
    labels = [n.label for n in result.nodes]
    assert "Vikram Malhotra" in labels
    assert "vikram@okhdfcbank" in labels
    assert "MH04AB9901" in labels
    assert len(result.edges) > 0


def test_vector_store_retrieval(tmp_path):
    f = tmp_path / "fir.txt"
    f.write_text("Victim Ramesh was extorted by Vikram Malhotra syndicate for Rs 15,00,000.", encoding="utf-8")

    doc = DocumentLoader.load_file(str(f), case_id="CASE-TEST")
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)

    store = VectorStore()
    store.add_chunks(chunks, case_id="CASE-TEST")

    res = store.search("Vikram Malhotra extortion", case_id="CASE-TEST", threshold=0.01)
    assert len(res) > 0
    assert "Ramesh" in res[0].text


def test_api_endpoints(client):
    # 1. Health check
    r = client.get("/")
    assert r.status_code == 200

    # 2. Cases
    r = client.get("/api/cases")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # 3. Narrative ingestion
    narrative = "Operative Rahul Sen (Phone: 9988776655) linked to Account 1234567890."
    r = client.post("/api/investigate/narrative", json={"case_id": "CASE-2024-MH-088", "narrative": narrative})
    assert r.status_code == 200
    assert r.json()["extractedCount"] >= 2

    # 4. Follow money
    r = client.post("/api/analytics/follow-money", json={"case_id": "CASE-2024-MH-088", "seed_node_id": "E3", "max_hops": 2})
    assert r.status_code == 200
    assert "flowChain" in r.json()

    # 5. Feedback override
    r = client.post("/api/feedback", json={"case_id": "CASE-2024-MH-088", "feedback_prompt": "@feedback E2 is victim"})
    assert r.status_code == 200
    assert r.json()["status"] == "applied"
