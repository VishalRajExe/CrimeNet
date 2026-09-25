"""Authentication, authorization, and CORS regression tests."""

from fastapi.testclient import TestClient

from backend.config import CRIMENET_API_KEY
from backend.main import app


client = TestClient(app)
valid_headers = {
    "X-API-Key": CRIMENET_API_KEY,
    "X-Officer-Badge": "INSP-4409",
}


def test_health_is_public_but_case_data_is_not():
    assert client.get("/").status_code == 200
    assert client.get("/api/cases").status_code == 401


def test_valid_api_key_and_officer_badge_are_accepted():
    response = client.get("/api/cases", headers=valid_headers)
    assert response.status_code == 200


def test_invalid_officer_badge_is_rejected():
    response = client.get(
        "/api/cases",
        headers={
            "X-API-Key": CRIMENET_API_KEY,
            "X-Officer-Badge": "UNKNOWN-99",
        },
    )
    assert response.status_code == 403


def test_body_badge_must_match_header():
    response = client.post(
        "/api/feedback",
        headers=valid_headers,
        json={
            "case_id": "CASE-2024-MH-088",
            "feedback_prompt": "@feedback E2 is victim",
            "officer_badge": "OTHER-1",
        },
    )
    assert response.status_code == 403


def test_cors_preflight_allows_only_configured_origin():
    response = client.options(
        "/api/cases",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key,x-officer-badge",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

    denied = client.options(
        "/api/cases",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.status_code == 400
