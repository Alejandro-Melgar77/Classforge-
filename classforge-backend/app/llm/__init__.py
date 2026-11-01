from __future__ import annotations

from app.llm.models import LlmMessage, LlmRequest, LlmResponse, LlmUsage
from app.llm.ports import LlmProvider
from app.llm.errors import (
    LlmError,
    LlmUnavailable,
    LlmRateLimited,
    LlmBadResponse,
    LlmQuotaExceeded,
)
from app.llm.gemini import GeminiProvider, set_shared_client, get_shared_client
from app.llm.fake import FakeLlmProvider
from app.llm.ollama import OllamaProvider
from app.llm.registry import (
    get_provider,
    get_fake_provider,
    get_ollama_provider,
    set_global_provider,
    reset_providers,
)
from app.llm.usage import record_ai_usage

__all__ = [
    "LlmMessage",
    "LlmRequest",
    "LlmResponse",
    "LlmUsage",
    "LlmProvider",
    "LlmError",
    "LlmUnavailable",
    "LlmRateLimited",
    "LlmBadResponse",
    "LlmQuotaExceeded",
    "GeminiProvider",
    "FakeLlmProvider",
    "OllamaProvider",
    "get_provider",
    "get_fake_provider",
    "get_ollama_provider",
    "set_global_provider",
    "reset_providers",
    "set_shared_client",
    "get_shared_client",
    "record_ai_usage",
]
