from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.llm.fake import FakeLlmProvider
from app.llm.gemini import GeminiProvider
from app.llm.registry import get_fake_provider, get_provider, reset_providers, set_global_provider
from app.main import app


@pytest.fixture(autouse=True)
def cleanup_providers():
    reset_providers()
    yield
    reset_providers()


def test_registry_resolves_gemini_and_fake():
    """Verify registry resolves GeminiProvider or FakeLlmProvider depending on settings."""
    original_provider = settings.LLM_PROVIDER
    try:
        settings.LLM_PROVIDER = "fake"
        reset_providers()
        p_fake = get_provider()
        assert isinstance(p_fake, FakeLlmProvider)

        settings.LLM_PROVIDER = "gemini"
        reset_providers()
        p_gemini = get_provider()
        assert isinstance(p_gemini, GeminiProvider)
    finally:
        settings.LLM_PROVIDER = original_provider
        reset_providers()


def test_registry_manual_override():
    """Verify set_global_provider allows explicit test overrides."""
    fake = FakeLlmProvider()
    set_global_provider(fake)
    assert get_provider() is fake


def test_ai_health_endpoint_contract():
    """
    Verify GET /api/v1/ai/health contract:
    Reports active provider, model chain, has_server_key boolean, and Ollama status.
    Does NOT make any paid Gemini calls.
    """
    client = TestClient(app)
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200

    data = response.json()
    assert "provider" in data
    assert "models" in data
    assert "has_server_key" in data
    assert "ollama_available" in data

    assert data["provider"] in ("gemini", "fake")
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0
    assert data["models"][0] == "gemini-3.8-flash"
    assert isinstance(data["has_server_key"], bool)
    assert isinstance(data["ollama_available"], bool)


def test_ai_chat_enabled_switch_503(monkeypatch):
    """
    Verify AI_CHAT_ENABLED functions as a real circuit switch.
    When False, ai_chat endpoints return HTTP 503 with clear message.
    """
    client = TestClient(app)
    monkeypatch.setattr(settings, "AI_CHAT_ENABLED", False)

    response = client.post(
        "/api/v1/ai-chat/projects/000000000000000000000001/messages",
        json={"message": "hello", "ai_role": "architect", "project_id": "000000000000000000000001"},
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "SERVICE_UNAVAILABLE"
    assert "deshabilitado" in payload["message"].lower()
