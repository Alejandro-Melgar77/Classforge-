"""Regression test for A23: Gemini status matrix (404 fast-fail, 401 breaker, usage list)."""
from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.llm.errors import LlmUnavailable
from app.llm.gemini import CircuitBreaker, GeminiProvider
from app.llm.models import LlmMessage, LlmRequest


def _ok(text="ok"):
    return {
        "candidates": [{"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
    }


def _provider(handler, breaker=None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GeminiProvider(
        client=client,
        circuit_breaker=breaker or CircuitBreaker(failure_threshold=5, recovery_timeout=30.0),
        retry_delay_base=0.0,
    )


def _req(model=None):
    return LlmRequest(
        system="s",
        messages=[LlmMessage(role="user", text="hola")],
        api_key=SecretStr("k"),
        model=model,
    )


@pytest.mark.asyncio
async def test_404_fails_the_model_fast_and_falls_back(monkeypatch):
    """A23: a 404 on a model must not burn all retries before falling back."""
    monkeypatch.setattr(settings, "GEMINI_MODELS", "gemini-missing,gemini-ok", raising=False)
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-missing", raising=False)
    monkeypatch.setattr(settings, "LLM_MAX_ATTEMPTS", 3)

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "gemini-missing" in str(request.url):
            return httpx.Response(404, json={"error": {"code": 404, "message": "model not found"}})
        return httpx.Response(200, json=_ok("desde el segundo modelo"))

    provider = _provider(handler)
    res = await provider.generate(_req(model="gemini-missing"))

    assert res.text == "desde el segundo modelo"
    assert sum(1 for u in calls if "gemini-missing" in u) == 1


@pytest.mark.asyncio
async def test_auth_error_opens_the_circuit():
    """A23: 401/403 must count as a breaker failure and open circuit."""
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
    provider = _provider(lambda request: httpx.Response(401, json={"error": "bad key"}), breaker)

    with pytest.raises(LlmUnavailable):
        await provider.generate(_req())

    assert breaker.consecutive_failures >= 1


def test_extract_usage_accepts_list_and_dict_details():
    """A23: candidatesTokensDetails parsed cleanly whether list or dict."""
    provider = GeminiProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))

    as_list = provider._extract_usage({
        "usageMetadata": {
            "promptTokenCount": 3,
            "candidatesTokenCount": 4,
            "candidatesTokensDetails": [{"thoughtsTokenCount": 7}],
        }
    })
    assert as_list.thoughts_tokens == 7

    as_dict = provider._extract_usage({
        "usageMetadata": {"candidatesTokensDetails": {"thoughtsTokenCount": 5}}
    })
    assert as_dict.thoughts_tokens == 5
