"""Tests for the Gemini agent's provider selection and offline fallback."""

from backend.agentic.gemini_agent import GeminiInvestigativeAgent


def test_offline_provider_uses_local_fallback(monkeypatch):
    """Offline mode must not attempt a Gemini network request."""
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    agent = GeminiInvestigativeAgent(api_key="your_gemini_api_key_here")

    def unexpected_api_call(*args, **kwargs):
        raise AssertionError("offline mode attempted a Gemini API request")

    monkeypatch.setattr(agent, "_call_gemini_api", unexpected_api_call)
    result = agent.chat(
        "Identify the kingpin",
        nodes=[{"id": "A", "label": "Test suspect", "type": "PERSON"}],
        edges=[],
    )

    assert agent.is_configured() is False
    assert result["model"] == "CrimeNet Gemini Engine (Local Grounded)"
    assert result["reply"]


def test_placeholder_key_is_not_treated_as_configured(monkeypatch):
    """The key copied from .env.example must not trigger a real request."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    agent = GeminiInvestigativeAgent(api_key="your_gemini_api_key_here")

    assert agent.is_configured() is False
