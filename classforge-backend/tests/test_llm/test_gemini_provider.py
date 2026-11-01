from __future__ import annotations

import json
import pytest
import httpx
from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import ValidationError
from app.llm.errors import LlmBadResponse, LlmRateLimited, LlmUnavailable
from app.llm.gemini import CircuitBreaker, GeminiProvider
from app.llm.models import LlmMessage, LlmRequest, LlmUsage


def _make_gemini_response(
    text: str = "Test response",
    prompt_tokens: int = 15,
    candidates_tokens: int = 25,
    thoughts_tokens: int = 8,
) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "candidatesTokenCount": candidates_tokens,
            "totalTokenCount": prompt_tokens + candidates_tokens,
            "thoughtsTokenCount": thoughts_tokens,
        },
    }


@pytest.mark.asyncio
async def test_api_key_in_header_never_in_url():
    """Verify that x-goog-api-key is sent via header and NEVER in the URL or query string."""
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=_make_gemini_response("Ok response"))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(
        system="System prompt",
        messages=[LlmMessage(role="user", text="Hello Gemini")],
        api_key=SecretStr("test-secret-key-12345"),
    )

    res = await provider.generate(req)
    assert res.text == "Ok response"
    assert len(captured_requests) == 1

    recorded_req = captured_requests[0]
    # 1. Header has key
    assert recorded_req.headers.get("x-goog-api-key") == "test-secret-key-12345"
    # 2. URL does not have key or query params
    url_str = str(recorded_req.url)
    assert "test-secret-key-12345" not in url_str
    assert "?key=" not in url_str
    assert "key=" not in url_str
    assert "?" not in url_str


@pytest.mark.asyncio
async def test_payload_structure_and_thinking():
    """Verify payload formatting: system_instruction, roles, generationConfig, and thinking."""
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json=_make_gemini_response('{"result": "success"}'))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    schema = {"type": "object", "properties": {"result": {"type": "string"}}}
    req = LlmRequest(
        system="Act as a software architect.",
        messages=[
            LlmMessage(role="user", text="First user turn"),
            LlmMessage(role="model", text="First model turn"),
            LlmMessage(role="user", text="Second user turn"),
        ],
        temperature=0.2,
        max_output_tokens=4096,
        thinking="medium",
        json_schema=schema,
        purpose="task",
        api_key=SecretStr("dummy-key"),
    )

    res = await provider.generate(req)
    assert len(captured_payloads) == 1
    p = captured_payloads[0]

    # system_instruction separated
    assert "system_instruction" in p
    assert p["system_instruction"]["parts"][0]["text"] == "Act as a software architect."

    # contents: real alternated turns with user/model roles
    assert len(p["contents"]) == 3
    assert p["contents"][0]["role"] == "user"
    assert p["contents"][0]["parts"][0]["text"] == "First user turn"
    assert p["contents"][1]["role"] == "model"
    assert p["contents"][1]["parts"][0]["text"] == "First model turn"
    assert p["contents"][2]["role"] == "user"
    assert p["contents"][2]["parts"][0]["text"] == "Second user turn"

    # generationConfig
    gen_config = p["generationConfig"]
    assert gen_config["temperature"] == 0.2
    assert gen_config["maxOutputTokens"] == 4096
    assert gen_config["responseMimeType"] == "application/json"
    assert gen_config["responseSchema"] == schema
    assert gen_config["thinkingConfig"]["thinkingLevel"] == "MEDIUM"


@pytest.mark.asyncio
async def test_multimodal_image_inline_data():
    """Verify that images are encoded as inline_data with mime_type."""
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json=_make_gemini_response("Image recognized"))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    dummy_bytes = b"fake-png-image-bytes"
    req = LlmRequest(
        system="Vision assistant",
        messages=[
            LlmMessage(
                role="user",
                text="Analyze this diagram",
                image_bytes=dummy_bytes,
                mime_type="image/png",
            )
        ],
        purpose="vision",
        api_key=SecretStr("dummy-key"),
    )

    await provider.generate(req)
    p = captured_payloads[0]
    parts = p["contents"][0]["parts"]
    # Check that inline_data part exists
    inline_part = next(part for part in parts if "inline_data" in part)
    assert inline_part["inline_data"]["mime_type"] == "image/png"
    assert len(inline_part["inline_data"]["data"]) > 0


@pytest.mark.asyncio
async def test_retries_on_429_and_503():
    """Verify backoff retries when encountering 429 or 503, eventually succeeding."""
    calls_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls_count
        calls_count += 1
        if calls_count == 1:
            return httpx.Response(429, json={"error": {"message": "Resource exhausted"}})
        if calls_count == 2:
            return httpx.Response(503, json={"error": {"message": "Service Unavailable"}})
        return httpx.Response(200, json=_make_gemini_response("Recovered!"))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Hi")],
        api_key=SecretStr("dummy-key"),
    )

    res = await provider.generate(req)
    assert res.text == "Recovered!"
    assert calls_count == 3


@pytest.mark.asyncio
async def test_no_retry_on_400():
    """Verify fast-fail on 400 Bad Request without any retries."""
    calls_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls_count
        calls_count += 1
        return httpx.Response(400, json={"error": {"message": "Invalid argument"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Hi")],
        api_key=SecretStr("dummy-key"),
    )

    with pytest.raises(LlmBadResponse):
        await provider.generate(req)

    assert calls_count == 1, "Should fail fast on 400 without retrying"


@pytest.mark.asyncio
async def test_no_retry_on_401_or_403():
    """Verify fast-fail on 401/403 Authentication failures without any retries."""
    calls_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls_count
        calls_count += 1
        return httpx.Response(403, json={"error": {"message": "API key not valid"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Hi")],
        api_key=SecretStr("bad-key"),
    )

    with pytest.raises(LlmUnavailable):
        await provider.generate(req)

    assert calls_count == 1, "Should fail fast on 403 without retrying"


@pytest.mark.asyncio
async def test_fallback_to_next_model():
    """Verify that when the primary model fails repeatedly, it advances to the fallback model."""
    models_called = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # Extract model from URL
        model = url_str.split("/models/")[1].split(":")[0]
        models_called.append(model)
        if "gemini-3.8-flash" in model:
            return httpx.Response(500, json={"error": {"message": "Internal error in primary"}})
        # Fallback model succeeds
        return httpx.Response(200, json=_make_gemini_response("Fallback success!"))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Hello")],
        api_key=SecretStr("dummy-key"),
    )

    res = await provider.generate(req)
    assert res.text == "Fallback success!"
    # Verified that primary was attempted and then fallback model was called
    assert "gemini-3.8-flash" in models_called
    assert res.model != "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_n_failures():
    """Verify circuit breaker opens after consecutive failures and fails fast."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "Persistent outage"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(messages=[LlmMessage(role="user", text="Hello")], api_key=SecretStr("key"))

    # Attempt 1: fails
    with pytest.raises(LlmUnavailable):
        await provider.generate(req)

    # Attempt 2: fails, trips circuit breaker
    with pytest.raises(LlmUnavailable):
        await provider.generate(req)

    # Attempt 3: circuit breaker is now OPEN; should raise LlmUnavailable without hitting network
    with pytest.raises(LlmUnavailable) as exc_info:
        await provider.generate(req)

    assert "circuito abierto" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_usage_metadata_parsing():
    """Verify that prompt, candidates, total, and thinking tokens are parsed into LlmUsage."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_make_gemini_response("Hello", prompt_tokens=100, candidates_tokens=50, thoughts_tokens=20),
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    req = LlmRequest(messages=[LlmMessage(role="user", text="Hi")], api_key=SecretStr("key"))
    res = await provider.generate(req)

    assert res.usage.prompt_tokens == 100
    assert res.usage.candidates_tokens == 50
    assert res.usage.total_tokens == 150
    assert res.usage.thoughts_tokens == 20


@pytest.mark.asyncio
async def test_json_schema_single_repair_retry():
    """Verify single-retry repair when initial JSON response is malformed."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # Model returns invalid JSON
            return httpx.Response(200, json=_make_gemini_response("Sorry, not json: {bad"))
        else:
            # Repair attempt returns valid JSON
            return httpx.Response(200, json=_make_gemini_response('{"repaired": true, "count": 42}'))

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    provider = GeminiProvider(client=client, circuit_breaker=cb, retry_delay_base=0.0)

    schema = {"type": "object", "properties": {"repaired": {"type": "boolean"}}}
    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Produce json")],
        json_schema=schema,
        api_key=SecretStr("key"),
    )

    res = await provider.generate(req)
    assert attempts == 2
    assert res.raw_json == {"repaired": True, "count": 42}


@pytest.mark.asyncio
async def test_model_validation_rejects_unconfigured_model():
    """Verify that passing an unwhitelisted model name is rejected to prevent URL injection."""
    client = httpx.AsyncClient()
    cb = CircuitBreaker()
    provider = GeminiProvider(client=client, circuit_breaker=cb)

    req = LlmRequest(
        messages=[LlmMessage(role="user", text="Hi")],
        api_key=SecretStr("key"),
        model="unwhitelisted-model-exploit",
    )

    with pytest.raises(ValidationError) as exc_info:
        await provider.generate(req)

    assert "no permitido" in str(exc_info.value).lower()
