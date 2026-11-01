from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse
import httpx
from pydantic import SecretStr

from app.core.config import settings
from app.llm.errors import (
    LlmBadResponse,
    LlmError,
    LlmUnavailable,
)
from app.llm.gemini import CircuitBreaker
from app.llm.models import LlmMessage, LlmRequest, LlmResponse, LlmUsage

logger = logging.getLogger(__name__)


def validate_and_sanitize_ollama_url(url: str) -> str:
    """
    Validates that the Ollama URL uses http/https and has a valid hostname.
    Guarantees that URLs cannot be forged or hijacked from client requests (anti-SSRF).
    """
    if not url or not isinstance(url, str):
        raise ValueError("OLLAMA_URL must be a non-empty string")
    clean = url.strip().rstrip("/")
    parsed = urlparse(clean)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"OLLAMA_URL scheme must be http or https, got '{parsed.scheme}'")
    if not parsed.hostname:
        raise ValueError("OLLAMA_URL must specify a valid host")
    return clean


def sanitize_json_text(text: str) -> str:
    """Strips markdown code fences and whitespace from model JSON output."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


class OllamaProvider:
    """
    Local LLM Provider adapter for Ollama (Mode A: Local PC / Tunnel).
    Conforms to the LlmProvider Protocol.
    
    Security & Architecture Guarantees:
    - OLLAMA_URL is strictly derived from environment configuration; NEVER from client request parameters.
    - URL scheme and hostname are validated on startup to prevent SSRF vulnerabilities.
    - Optional X-Local-LLM-Secret header passed to authenticate Cloudflare Tunnel reverse proxies.
    - Circuit breaker to fast-fail when the team PC or tunnel is offline.
    - Single-attempt repair loop when structured JSON output is requested but invalid.
    - Telemetry tracking for latency, tokens, and health state.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: Optional[float] = None,
        secret: Optional[SecretStr] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        raw_url = base_url or settings.OLLAMA_URL
        self.base_url = validate_and_sanitize_ollama_url(raw_url)
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")
        self.timeout_s = timeout_s if timeout_s is not None else getattr(settings, "OLLAMA_TIMEOUT_S", 12.0)
        self.secret = secret if secret is not None else getattr(settings, "LOCAL_LLM_SECRET", None)
        self.transport = transport
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, "LLM_CIRCUIT_BREAKER_FAILURES", 5),
            recovery_timeout=getattr(settings, "LLM_CIRCUIT_BREAKER_RECOVERY_SECONDS", 30.0),
        )
        self.last_latency_ms: Optional[float] = None
        self.last_health_status: bool = False

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.secret:
            secret_val = self.secret.get_secret_value() if hasattr(self.secret, "get_secret_value") else str(self.secret)
            if secret_val:
                headers["X-Local-LLM-Secret"] = secret_val
        return headers

    def _build_messages(self, req: LlmRequest) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        for msg in req.messages:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.text})
        return messages

    async def _post_chat(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        resp = await client.post(url, json=payload, headers=self._get_headers())
        if resp.status_code in (401, 403):
            raise LlmUnavailable("Autenticación fallida con el túnel local (secreto inválido o acceso denegado)")
        if resp.status_code == 404:
            raise LlmBadResponse(f"El modelo '{payload.get('model')}' no está disponible o no existe en Ollama")
        resp.raise_for_status()
        return resp.json()

    async def check_health(self, timeout_s: float = 2.0) -> Dict[str, Any]:
        """
        Pings Ollama /api/tags to verify connectivity and measure latency.
        Does not count against the operational circuit breaker.
        """
        start = time.monotonic()
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=timeout_s, transport=self.transport) as client:
                resp = await client.get(url, headers=self._get_headers())
                latency_ms = round((time.monotonic() - start) * 1000, 2)
                if resp.status_code == 200:
                    self.last_latency_ms = latency_ms
                    self.last_health_status = True
                    data = resp.json()
                    models = [m.get("name") for m in data.get("models", []) if isinstance(m, dict)]
                    return {
                        "available": True,
                        "latency_ms": latency_ms,
                        "model": self.model,
                        "installed_models": models,
                    }
                else:
                    self.last_health_status = False
                    return {
                        "available": False,
                        "latency_ms": latency_ms,
                        "model": self.model,
                        "status_code": resp.status_code,
                    }
        except Exception as e:
            self.last_health_status = False
            return {
                "available": False,
                "latency_ms": None,
                "model": self.model,
                "error": str(e),
            }

    async def generate(self, req: LlmRequest) -> LlmResponse:
        """
        Executes a single generate request against Ollama /api/chat.
        Includes single-attempt JSON repair if required.
        """
        # 1. Circuit breaker check
        await self.circuit_breaker.check()

        # 2. Build payload
        messages = self._build_messages(req)
        target_model = req.model or self.model
        format_param: Optional[Any] = None
        if req.json_schema or req.purpose in ("task", "uml_command"):
            format_param = "json"

        options: Dict[str, Any] = {
            "temperature": req.temperature if req.temperature is not None else 0.1,
            "num_predict": req.max_output_tokens or 2048,
        }

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if format_param:
            payload["format"] = format_param

        # 3. Call Ollama
        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                data = await self._post_chat(client, payload)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            await self.circuit_breaker.record_failure()
            logger.warning(f"[OllamaProvider] Error de red o timeout ({e}) hacia {self.base_url}")
            raise LlmUnavailable(f"Modelo local no disponible o tiempo de espera excedido: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                await self.circuit_breaker.record_failure()
            raise LlmBadResponse(f"Error HTTP del servicio local Ollama: {e}")
        except LlmError:
            raise
        except Exception as e:
            await self.circuit_breaker.record_failure()
            raise LlmUnavailable(f"Error inesperado al conectar con Ollama: {e}")

        # Solicitud HTTP exitosa
        await self.circuit_breaker.record_success()
        latency_ms = round((time.monotonic() - start_time) * 1000, 2)
        self.last_latency_ms = latency_ms

        # Extract text & token usage
        msg_obj = data.get("message") or {}
        raw_text = msg_obj.get("content", "")

        prompt_tokens = int(data.get("prompt_eval_count", 0))
        candidates_tokens = int(data.get("eval_count", 0))
        usage = LlmUsage(
            prompt_tokens=prompt_tokens,
            candidates_tokens=candidates_tokens,
            total_tokens=prompt_tokens + candidates_tokens,
        )

        # 4. JSON parsing and single-attempt repair loop
        parsed_json: Optional[Dict[str, Any]] = None
        if req.json_schema or req.purpose in ("task", "uml_command"):
            clean_str = sanitize_json_text(raw_text)
            try:
                parsed_json = json.loads(clean_str)
            except json.JSONDecodeError as err:
                logger.warning(
                    f"[OllamaProvider] Salida no fue JSON válido ({err}). Ejecutando UN intento de reparación..."
                )
                repair_messages = list(messages)
                repair_messages.append({"role": "assistant", "content": raw_text})
                repair_messages.append({
                    "role": "user",
                    "content": (
                        "Tu respuesta anterior NO fue un JSON válido. "
                        "Corrige la sintaxis y devuelve EXCLUSIVAMENTE el objeto JSON válido "
                        "sin bloques de código markdown, sin explicaciones."
                    ),
                })
                repair_payload = {
                    "model": target_model,
                    "messages": repair_messages,
                    "stream": False,
                    "format": "json",
                    "options": options,
                }
                try:
                    async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                        rep_data = await self._post_chat(client, repair_payload)
                        rep_msg = rep_data.get("message") or {}
                        rep_text = rep_msg.get("content", "")
                        clean_rep = sanitize_json_text(rep_text)
                        parsed_json = json.loads(clean_rep)
                        raw_text = rep_text
                        logger.info("[OllamaProvider] Reparación de JSON exitosa.")
                except Exception as rep_err:
                    logger.error(f"[OllamaProvider] Falló la reparación de JSON: {rep_err}")
                    raise LlmBadResponse(f"El modelo local generó una respuesta JSON inválida: {rep_err}")

        return LlmResponse(
            text=raw_text,
            usage=usage,
            model=target_model,
            raw_json=parsed_json,
            latency_ms=latency_ms,
        )

    async def stream(self, req: LlmRequest) -> AsyncIterator[str]:
        """Streams text chunks from Ollama /api/chat."""
        await self.circuit_breaker.check()
        messages = self._build_messages(req)
        payload = {
            "model": req.model or self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": req.temperature if req.temperature is not None else 0.1,
                "num_predict": req.max_output_tokens or 2048,
            },
        }

        url = f"{self.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                async with client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
                    response.raise_for_status()
                    await self.circuit_breaker.record_success()
                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        try:
                            chunk_data = json.loads(line)
                            chunk_msg = chunk_data.get("message") or {}
                            content = chunk_msg.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.warning(f"[OllamaProvider] Streaming failed: {e}")
            raise LlmUnavailable(f"Error en streaming de modelo local: {e}")
