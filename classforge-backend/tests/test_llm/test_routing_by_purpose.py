"""Regression test for A24: Routing by purpose."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.llm import registry


def test_get_provider_honours_routing_purpose(monkeypatch):
    """A24: LLM_ROUTING must select the provider per purpose (role_chat, vision, uml_command)."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(
        settings,
        "LLM_ROUTING",
        '{"vision":["ollama"],"role_chat":["gemini"],"uml_command":["gemini"]}',
    )
    registry.reset_providers()

    try:
        vision = registry.get_provider(purpose="vision")
        role_chat = registry.get_provider(purpose="role_chat")
        uml = registry.get_provider(purpose="uml_command")
        assert type(vision).__name__ == "OllamaProvider"
        assert type(role_chat).__name__ == "GeminiProvider"
        assert type(uml).__name__ == "GeminiProvider"
    finally:
        registry.reset_providers()
