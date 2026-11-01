from __future__ import annotations

import json
import pytest
import httpx
from typing import Any, Dict
from pydantic import SecretStr

from app.core.config import settings
from app.llm.errors import LlmBadResponse, LlmUnavailable
from app.llm.gemini import CircuitBreaker
from app.llm.models import LlmMessage, LlmRequest, LlmResponse
from app.llm.ollama import (
    OllamaProvider,
    validate_and_sanitize_ollama_url,
    sanitize_json_text,
)
from app.llm.registry import resolve_routing_chain
from app.ai_team.infrastructure.retrieval import (
    BM25Retriever,
    normalize_token,
    tokenize,
    bm25_retriever,
)
from app.modules.ai.schemas import PromptRequest, UMLCommandResponse
from app.modules.ai.service import process_prompt, validate_command_with_linter


# ── 1. Mock Transport Tests for OllamaProvider ────────────────────────────────

@pytest.mark.asyncio
async def test_ollama_provider_generate_json_success():
    """Verify OllamaProvider.generate calls /api/chat with format='json' and passes secret header."""
    recorded_headers = {}
    recorded_body = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal recorded_headers, recorded_body
        recorded_headers = dict(request.headers)
        recorded_body = json.loads(request.content.decode("utf-8"))

        sample_response = {
            "model": "qwen2.5:1.5b",
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "action": "create_class",
                    "classes": [{"name": "Factura", "attributes": [], "methods": []}],
                    "relations": [],
                    "explanation": "Clase Factura creada"
                })
            },
            "prompt_eval_count": 15,
            "eval_count": 42,
            "done": True
        }
        return httpx.Response(200, json=sample_response)

    transport = httpx.MockTransport(handler)

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:1.5b",
        secret=SecretStr("test-secret-token"),
        transport=transport
    )

    req = LlmRequest(
        system="Compila a UML",
        messages=[
            LlmMessage(role="user", content="crear clase Factura")
        ],
        purpose="uml_command",
        temperature=0.1
    )

    res = await provider.generate(req)
    assert isinstance(res, LlmResponse)
    assert "Factura" in res.text
    assert res.model == "qwen2.5:1.5b"
    assert res.usage.candidates_tokens == 42
    assert res.usage.prompt_tokens == 15
    assert res.raw_json is not None
    assert res.raw_json["action"] == "create_class"

    # Verify secret header and body format
    assert recorded_headers.get("x-local-llm-secret") == "test-secret-token"
    assert recorded_body.get("format") == "json"
    assert recorded_body.get("stream") is False


@pytest.mark.asyncio
async def test_ollama_provider_stream_ndjson():
    """Verify OllamaProvider.stream properly yields streaming text chunks."""
    def handler(request: httpx.Request) -> httpx.Response:
        lines = [
            json.dumps({"message": {"content": "Hola "}, "done": False}) + "\n",
            json.dumps({"message": {"content": "Mundo"}, "done": False}) + "\n",
            json.dumps({"message": {"content": "!"}, "done": True}) + "\n"
        ]
        return httpx.Response(200, content="".join(lines).encode("utf-8"))

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", transport=transport)

    req = LlmRequest(messages=[LlmMessage(role="user", content="Saluda")])
    chunks = []
    async for chunk in provider.stream(req):
        chunks.append(chunk)

    assert chunks == ["Hola ", "Mundo", "!"]


# ── 2. Circuit Breaker Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_after_threshold():
    """Verify CircuitBreaker transitions to OPEN after consecutive failures and fast-fails."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

    # Record 3 failures
    await breaker.record_failure()
    assert breaker.consecutive_failures == 1
    await breaker.record_failure()
    assert breaker.consecutive_failures == 2
    await breaker.record_failure()
    assert breaker.consecutive_failures == 3

    # check() must raise LlmUnavailable
    with pytest.raises(LlmUnavailable) as exc_info:
        await breaker.check()

    assert "circuito abierto" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_cooldown():
    """Verify CircuitBreaker allows retry after recovery timeout and resets on success."""
    import asyncio
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.02)
    await breaker.record_failure()
    await breaker.record_failure()

    # Fast-fails immediately
    with pytest.raises(LlmUnavailable):
        await breaker.check()

    # Wait for cooldown
    await asyncio.sleep(0.03)

    # Check succeeds (entering half-open)
    await breaker.check()

    # Successful call resets counter
    await breaker.record_success()
    assert breaker.consecutive_failures == 0


# ── 3. Single-Attempt JSON Repair Loop ────────────────────────────────────────

@pytest.mark.asyncio
async def test_ollama_json_repair_loop_success():
    """Verify single-attempt repair loop corrects malformed JSON on second call."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First attempt: invalid JSON string (unclosed bracket)
            return httpx.Response(200, json={
                "message": {"content": '{"action": "create_class", "classes": ['}
            })
        else:
            # Second attempt (repair): valid JSON
            return httpx.Response(200, json={
                "message": {"content": json.dumps({
                    "action": "create_class",
                    "classes": [{"name": "User", "attributes": [], "methods": []}],
                    "relations": [],
                    "explanation": "JSON reparado correctamente"
                })}
            })

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", transport=transport)

    req = LlmRequest(
        messages=[LlmMessage(role="user", content="crear clase User")],
        purpose="uml_command"
    )

    res = await provider.generate(req)
    assert call_count == 2
    assert res.raw_json is not None
    assert res.raw_json["action"] == "create_class"
    assert res.raw_json["classes"][0]["name"] == "User"


@pytest.mark.asyncio
async def test_ollama_json_repair_fails_gracefully():
    """Verify that if repair also fails on second attempt, it raises LlmBadResponse without looping infinitely."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={
            "message": {"content": "Esto no es JSON de ninguna manera"}
        })

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", transport=transport)

    req = LlmRequest(
        messages=[LlmMessage(role="user", content="crear clase User")],
        purpose="uml_command"
    )

    with pytest.raises(LlmBadResponse) as exc_info:
        await provider.generate(req)

    assert call_count == 2  # exactly 1 initial + 1 repair attempt
    assert "inválida" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()


# ── 4. SSRF and URL Security Validation ───────────────────────────────────────

def test_ollama_provider_blocks_invalid_schemes():
    """Verify OllamaProvider rejects non-http/https schemes."""
    with pytest.raises(ValueError) as exc1:
        validate_and_sanitize_ollama_url("ftp://evil.com/api")
    assert "scheme" in str(exc1.value).lower()

    with pytest.raises(ValueError) as exc2:
        validate_and_sanitize_ollama_url("javascript:alert(1)")
    assert "scheme" in str(exc2.value).lower()


def test_prompt_request_blocks_client_ollama_url_ssrf():
    """Verify PromptRequest rejects client attempts to pass ollama_url or local_url (Anti-SSRF)."""
    with pytest.raises(ValueError) as exc1:
        PromptRequest(prompt="test", ollama_url="http://169.254.169.254/latest/meta-data")
    assert "ssrf" in str(exc1.value).lower()

    with pytest.raises(ValueError) as exc2:
        PromptRequest(prompt="test", local_url="http://localhost:8080")
    assert "ssrf" in str(exc2.value).lower()


# ── 5. Purpose-Based Routing and Fallback Chains ──────────────────────────────

def test_resolve_routing_chain_uml_command():
    """Verify routing chain for uml_command contains local model first, then gemini, then heuristic."""
    chain = resolve_routing_chain(purpose="uml_command")
    assert chain == ["ollama", "gemini", "heuristic"]


def test_resolve_routing_chain_role_chat():
    """Verify role_chat only routes to gemini (open reasoning retained in Gemini 3.8 Flash)."""
    chain = resolve_routing_chain(purpose="role_chat")
    assert chain == ["gemini"]


def test_resolve_routing_chain_local_only():
    """Verify privacy mode local_only=True strips gemini completely from all chains."""
    chain_uml = resolve_routing_chain(purpose="uml_command", local_only=True)
    assert "gemini" not in chain_uml
    assert chain_uml == ["ollama", "heuristic"]

    chain_chat = resolve_routing_chain(purpose="role_chat", local_only=True)
    assert "gemini" not in chain_chat
    assert chain_chat == []


def test_resolve_routing_chain_preferred_provider():
    """Verify preferred_provider='gemini' prioritizes gemini at front of chain."""
    chain = resolve_routing_chain(purpose="uml_command", preferred_provider="gemini")
    assert chain[0] == "gemini"


# ── 6. Full Service Fallback (Ollama Down -> Heuristic) ────────────────────────

@pytest.mark.asyncio
async def test_execute_ai_prompt_falls_back_when_local_fails():
    """
    Verify that when Ollama is unavailable (or times out),
    and local_only=True, it falls back cleanly to the heuristic engine with source='heuristic'.
    """
    res = await process_prompt(
        prompt="crear clase Cliente con id:Long, nombre:String",
        local_only=True,  # Blocks Gemini -> Local fails -> Heuristic
    )

    assert res is not None
    assert res.action == "create_class"
    assert len(res.classes) == 1
    assert res.classes[0].name.lower() == "cliente"
    assert res.source in ("heuristic", "offline_nlu")


# ── 7. Lightweight BM25 RAG Tests ─────────────────────────────────────────────

def test_bm25_token_normalization_and_stopwords():
    """Verify Spanish diacritics are normalized and punctuation stripped."""
    assert normalize_token("Facturación") == "facturacion"
    assert normalize_token("MÉDICO") == "medico"
    assert tokenize("¡Gestión de Facturas!") == ["gestion", "facturas"]


def test_bm25_retriever_query():
    """Verify BM25Retriever indexes knowledge chunks and retrieves relevant UML rules."""
    retriever = BM25Retriever()
    # Query for composition / aggregate rules
    chunks = retriever.retrieve("cardinalidad composicion agregacion", top_k=2)
    assert len(chunks) > 0
    text = retriever.retrieve_context_text("cardinalidad composicion", max_tokens=500)
    assert len(text) > 0
    assert "---" in text


# ── 8. Linter Validation of UMLCommandResponse ────────────────────────────────

def test_validate_command_with_linter():
    """Verify P3 deterministic linter validation rejects duplicate class names and broken relations."""
    valid_cmd = UMLCommandResponse(
        action="create_class",
        classes=[{"name": "Usuario", "attributes": [], "methods": []}],
        relations=[],
        explanation="OK",
        source="local"
    )
    assert validate_command_with_linter(valid_cmd) is True

    # Duplicate classes should be rejected
    dup_cmd = UMLCommandResponse(
        action="create_class",
        classes=[
            {"name": "Usuario", "attributes": [], "methods": []},
            {"name": "Usuario", "attributes": [], "methods": []}
        ],
        relations=[],
        explanation="Duplicate class",
        source="local"
    )
    assert validate_command_with_linter(dup_cmd) is False
