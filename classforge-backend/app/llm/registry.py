from __future__ import annotations

import logging
from typing import List, Optional
from app.core.config import settings
from app.llm.fake import FakeLlmProvider
from app.llm.gemini import GeminiProvider
from app.llm.ports import LlmProvider

logger = logging.getLogger(__name__)

_GLOBAL_PROVIDER: Optional[LlmProvider] = None
_GLOBAL_FAKE_PROVIDER: Optional[FakeLlmProvider] = None
_GLOBAL_GEMINI_PROVIDER: Optional[GeminiProvider] = None
_GLOBAL_OLLAMA_PROVIDER: Optional[LlmProvider] = None


def get_fake_provider() -> FakeLlmProvider:
    """Returns the singleton FakeLlmProvider instance for test setups."""
    global _GLOBAL_FAKE_PROVIDER
    if _GLOBAL_FAKE_PROVIDER is None:
        _GLOBAL_FAKE_PROVIDER = FakeLlmProvider()
    return _GLOBAL_FAKE_PROVIDER


def get_gemini_provider() -> GeminiProvider:
    """Returns the singleton GeminiProvider instance."""
    global _GLOBAL_GEMINI_PROVIDER
    if _GLOBAL_GEMINI_PROVIDER is None:
        _GLOBAL_GEMINI_PROVIDER = GeminiProvider()
    return _GLOBAL_GEMINI_PROVIDER


def get_ollama_provider() -> LlmProvider:
    """Returns the singleton OllamaProvider instance."""
    global _GLOBAL_OLLAMA_PROVIDER
    if _GLOBAL_OLLAMA_PROVIDER is None:
        from app.llm.ollama import OllamaProvider
        _GLOBAL_OLLAMA_PROVIDER = OllamaProvider()
    return _GLOBAL_OLLAMA_PROVIDER


def set_global_provider(provider: Optional[LlmProvider]) -> None:
    """Explicitly overrides the global LLM provider (useful for testing)."""
    global _GLOBAL_PROVIDER
    _GLOBAL_PROVIDER = provider


def reset_providers() -> None:
    """Resets all provider instances."""
    global _GLOBAL_PROVIDER, _GLOBAL_FAKE_PROVIDER, _GLOBAL_GEMINI_PROVIDER, _GLOBAL_OLLAMA_PROVIDER
    _GLOBAL_PROVIDER = None
    if _GLOBAL_FAKE_PROVIDER is not None:
        _GLOBAL_FAKE_PROVIDER.reset()
    _GLOBAL_FAKE_PROVIDER = None
    _GLOBAL_GEMINI_PROVIDER = None
    _GLOBAL_OLLAMA_PROVIDER = None


def get_provider(purpose: str = "chat", custom_provider: Optional[str] = None) -> LlmProvider:
    """
    Returns an LlmProvider instance based on configuration and optional override.
    
    Settings:
        LLM_PROVIDER: "gemini" | "fake" | "ollama" (default: "gemini", but "fake" mandatory in tests/E2E).
    """
    global _GLOBAL_PROVIDER

    if _GLOBAL_PROVIDER is not None:
        return _GLOBAL_PROVIDER

    provider_name = (custom_provider or settings.LLM_PROVIDER or "gemini").strip().lower()

    if provider_name == "fake":
        return get_fake_provider()

    if provider_name in ("ollama", "local"):
        return get_ollama_provider()

    if provider_name == "gemini":
        return get_gemini_provider()

    logger.warning(f"Proveedor LLM desconocido '{provider_name}'. Usando 'gemini'.")
    return get_gemini_provider()


def resolve_routing_chain(
    purpose: str,
    local_only: bool = False,
    preferred_provider: Optional[str] = None,
) -> List[str]:
    """
    Resolves the ordered fallback chain for a given purpose.
    
    Example base routing for purpose='uml_command':
        ["ollama", "gemini", "heuristic"]
    
    Rules:
    - If a global test provider is explicitly set, routes through it then heuristic.
    - If LLM_PROVIDER is "fake" (test environment), maps providers to "fake".
    - If preferred_provider is specified, moves it to the front of the chain.
    - If local_only is True (or AI_LOCAL_ONLY is enabled), completely removes "gemini".
    """
    global _GLOBAL_PROVIDER
    if _GLOBAL_PROVIDER is not None:
        return ["global_override", "heuristic"]

    if settings.LLM_PROVIDER == "fake":
        return ["fake"]

    base_chain = settings.get_routing_chain(purpose)
    chain = list(base_chain)

    # Normalize preferred_provider
    pref = (preferred_provider or "").strip().lower()
    if pref in ("local", "ollama"):
        pref = "ollama"

    if pref and pref in chain:
        chain.remove(pref)
        chain.insert(0, pref)

    # Filter out gemini if local_only is enforced
    if local_only or settings.AI_LOCAL_ONLY:
        chain = [c for c in chain if c != "gemini"]

    return chain
