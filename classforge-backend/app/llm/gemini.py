from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import ValidationError
from app.llm.errors import (
    LlmBadResponse,
    LlmError,
    LlmQuotaExceeded,
    LlmRateLimited,
    LlmUnavailable,
)
from app.llm.models import LlmMessage, LlmRequest, LlmResponse, LlmUsage
from app.llm.usage import record_ai_usage

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Global shared client reference (configured during application lifespan)
_SHARED_CLIENT: Optional[httpx.AsyncClient] = None


def set_shared_client(client: Optional[httpx.AsyncClient]) -> None:
    """Sets the application-wide shared httpx.AsyncClient for GeminiProvider."""
    global _SHARED_CLIENT
    _SHARED_CLIENT = client


def get_shared_client() -> httpx.AsyncClient:
    """Gets the shared client or instantiates a default fallback client."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS)
    return _SHARED_CLIENT


class CircuitBreaker:
    """
    Simple circuit breaker to prevent cascading failures across models.
    Opens after consecutive failures and enters half-open recovery after cooldown.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def check(self) -> None:
        """Raises LlmUnavailable if the circuit is currently open."""
        async with self._lock:
            if self.consecutive_failures >= self.failure_threshold:
                elapsed = time.monotonic() - self.last_failure_time
                if elapsed < self.recovery_timeout:
                    remaining = int(self.recovery_timeout - elapsed)
                    logger.warning(
                        f"[CircuitBreaker] Circuito abierto ({self.consecutive_failures} fallos seguidos). "
                        f"Reintentos bloqueados por {remaining}s."
                    )
                    raise LlmUnavailable(
                        f"El servicio de IA está temporalmente en protección (circuito abierto). Intente en {remaining}s."
                    )
                else:
                    logger.info("[CircuitBreaker] Tiempo de enfriamiento concluido. Estado: HALF_OPEN.")

    async def record_success(self) -> None:
        """Resets the failure counter upon successful execution."""
        async with self._lock:
            if self.consecutive_failures > 0:
                logger.info("[CircuitBreaker] Solicitud exitosa. Circuito restablecido a CLOSED.")
            self.consecutive_failures = 0

    async def record_failure(self) -> None:
        """Increments consecutive failure count on network or server errors."""
        async with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.monotonic()
            if self.consecutive_failures >= self.failure_threshold:
                logger.error(
                    f"[CircuitBreaker] Umbral de {self.failure_threshold} fallos consecutivos alcanzado. "
                    f"Circuito abierto por {self.recovery_timeout}s."
                )

    async def reset(self) -> None:
        """Manually resets the circuit breaker state (useful for tests)."""
        async with self._lock:
            self.consecutive_failures = 0
            self.last_failure_time = 0.0


class GeminiProvider:
    """
    Unified, hardened Gemini LLM Provider adapter conforming to official API v1beta.
    
    Security & Reliability Guarantees:
    - API key sent strictly in 'x-goog-api-key' header, NEVER as a URL query parameter.
    - Keys stored as SecretStr; excluded from repr, logs, and tracebacks.
    - Model chain dynamically governed by GEMINI_MODELS configuration. No hardcoded lists.
    - Strict validation of requested model against configured whitelist to block URL injection.
    - Max output tokens bounded per purpose with hard ceiling of 65,536 tokens.
    - Thinking levels (LOW, MEDIUM, HIGH) exposed for Gemini 3.8 Flash reasoning.
    - Retries with exponential backoff & jitter solely on 429, 5xx, and network timeouts.
    - Fast-fail (no retries) on client errors: 400 Bad Request, 401 Unauthorized, 403 Forbidden.
    - Simple circuit breaker preventing model chain stalls on systemic outages.
    - Single-retry repair mechanism when structured JSON response schema is violated.
    - Extraction and telemetry persistence of usageMetadata (prompt, candidates, thinking tokens).
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_delay_base: float = 0.5,
    ) -> None:
        self._custom_client = client
        self.retry_delay_base = retry_delay_base
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=settings.LLM_CIRCUIT_BREAKER_FAILURES,
            recovery_timeout=settings.LLM_CIRCUIT_BREAKER_RECOVERY_SECONDS,
        )

    def _get_client(self) -> httpx.AsyncClient:
        return self._custom_client if self._custom_client is not None else get_shared_client()

    def _resolve_api_key(self, req: LlmRequest) -> SecretStr:
        """Resolves API key with priority: Request BYOK > Server GEMINI_API_KEY."""
        if req.api_key and req.api_key.get_secret_value().strip():
            return req.api_key
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.get_secret_value().strip():
            return settings.GEMINI_API_KEY
        raise LlmUnavailable("Clave de API de Gemini no configurada en el servidor ni en la petición.")

    def _build_model_chain(self, requested_model: Optional[str]) -> List[str]:
        """Validates and constructs the ordered list of candidate models."""
        configured_models = settings.gemini_models_list
        if not configured_models:
            raise LlmUnavailable("No hay modelos de Gemini configurados en GEMINI_MODELS.")

        if requested_model:
            clean_model = requested_model.strip()
            if clean_model not in configured_models:
                raise ValidationError(
                    f"Modelo '{clean_model}' no permitido. Modelos configurados: {', '.join(configured_models)}"
                )
            # Prioritize requested model, then remainder of chain
            chain = [clean_model] + [m for m in configured_models if m != clean_model]
            return chain

        return list(configured_models)

    def _build_payload(self, req: LlmRequest) -> Dict[str, Any]:
        """Constructs official REST request body for models.generateContent."""
        payload: Dict[str, Any] = {}

        # 1. System instruction
        if req.system.strip():
            payload["system_instruction"] = {
                "parts": [{"text": req.system.strip()}]
            }

        # 2. Conversational contents (multi-turn alternated real roles: user/model)
        contents: List[Dict[str, Any]] = []
        for msg in req.messages:
            parts: List[Dict[str, Any]] = []
            if msg.image_bytes:
                b64_data = base64.b64encode(msg.image_bytes).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": msg.mime_type or "image/jpeg",
                        "data": b64_data,
                    }
                })
            if msg.text:
                parts.append({"text": msg.text})

            if parts:
                contents.append({
                    "role": msg.role,
                    "parts": parts,
                })

        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})

        payload["contents"] = contents

        # 3. Generation configuration
        max_tokens = min(
            req.max_output_tokens or settings.get_max_output_tokens(req.purpose),
            65536,
        )
        gen_config: Dict[str, Any] = {
            "maxOutputTokens": max_tokens,
        }

        if req.temperature is not None:
            gen_config["temperature"] = req.temperature

        # Thinking configuration (reasoning features in Gemini 3.8 Flash)
        if req.thinking:
            gen_config["thinkingConfig"] = {
                "thinkingLevel": req.thinking.upper()
            }

        # Structured JSON Output
        if req.json_schema:
            gen_config["responseMimeType"] = "application/json"
            gen_config["responseSchema"] = req.json_schema

        payload["generationConfig"] = gen_config
        return payload

    def _extract_usage(self, response_json: Dict[str, Any]) -> LlmUsage:
        """Parses usageMetadata including reasoning/thinking tokens."""
        meta = response_json.get("usageMetadata", {})
        prompt_tokens = meta.get("promptTokenCount", 0)
        candidates_tokens = meta.get("candidatesTokenCount", 0)
        total_tokens = meta.get("totalTokenCount", prompt_tokens + candidates_tokens)

        # Reasoning tokens if present in metadata
        thoughts_tokens = (
            meta.get("thoughtsTokenCount")
            or meta.get("reasoningTokenCount")
            or meta.get("candidatesTokensDetails", {}).get("thoughtsTokenCount")
        )

        return LlmUsage(
            prompt_tokens=prompt_tokens,
            candidates_tokens=candidates_tokens,
            total_tokens=total_tokens,
            thoughts_tokens=thoughts_tokens,
        )

    def _extract_text(self, response_json: Dict[str, Any]) -> str:
        """Extracts text content from candidate parts."""
        candidates = response_json.get("candidates", [])
        if not candidates:
            # Check prompt feedback
            feedback = response_json.get("promptFeedback", {})
            block_reason = feedback.get("blockReason")
            if block_reason:
                raise LlmBadResponse(f"Generación bloqueada por política de seguridad: {block_reason}")
            raise LlmBadResponse("Gemini retornó una lista vacía de candidatos.")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise LlmBadResponse("Candidato sin partes de contenido.")

        text_parts = [p.get("text", "") for p in parts if "text" in p]
        return "".join(text_parts).strip()

    async def _attempt_json_repair(
        self,
        client: httpx.AsyncClient,
        model: str,
        api_key: SecretStr,
        req: LlmRequest,
        invalid_text: str,
    ) -> Dict[str, Any]:
        """
        Executes a single-retry repair request when the model ignores or violates
        the expected JSON schema (no regex fallback from first { to last }).
        """
        logger.info(f"[GeminiProvider] Intentando reparación en un único reintento para modelo {model}...")
        repair_messages = list(req.messages)
        repair_messages.append(LlmMessage(role="model", text=invalid_text))
        repair_messages.append(
            LlmMessage(
                role="user",
                text=(
                    "The previous response was not valid JSON conforming to the requested schema. "
                    "Output ONLY the valid JSON document conforming strictly to the schema, with no markdown fences, "
                    "no preamble, and no extra commentary."
                ),
            )
        )
        repair_req = req.model_copy(update={"messages": repair_messages})
        repair_payload = self._build_payload(repair_req)

        url = f"{GEMINI_BASE_URL}/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        try:
            resp = await client.post(url, json=repair_payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                clean_text = self._extract_text(data)
                # Strip markdown code fences if model enclosed it
                clean_text = self._clean_json_fences(clean_text)
                return json.loads(clean_text)
            else:
                logger.warning(f"[GeminiProvider] Reintento de reparación falló con HTTP {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[GeminiProvider] Error en reparación JSON: {exc}")

        raise LlmBadResponse("La respuesta del modelo de IA no es un JSON válido después del reintento de reparación.")

    @staticmethod
    def _clean_json_fences(raw: str) -> str:
        s = raw.strip()
        if s.startswith("```"):
            lines = s.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            s = "\n".join(lines).strip()
        return s

    async def generate(self, req: LlmRequest) -> LlmResponse:
        """
        Executes generateContent against Gemini REST endpoint, traversing the
        configured model chain, applying retries, circuit breaking, and telemetry.
        """
        # 1. Circuit breaker pre-check
        await self.circuit_breaker.check()

        # 2. Key and model chain resolution
        api_key = self._resolve_api_key(req)
        models_to_try = self._build_model_chain(req.model)
        client = self._get_client()

        payload = self._build_payload(req)
        headers = {
            "x-goog-api-key": api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        last_exception: Optional[Exception] = None

        for model_name in models_to_try:
            # Endpoint REST: clave en cabecera x-goog-api-key, NUNCA en la URL
            url = f"{GEMINI_BASE_URL}/{model_name}:generateContent"

            for attempt in range(1, settings.LLM_MAX_ATTEMPTS + 1):
                try:
                    logger.debug(f"[GeminiProvider] Invocando {model_name} (intento {attempt}/{settings.LLM_MAX_ATTEMPTS})...")
                    resp = await client.post(url, json=payload, headers=headers)

                    # Fast-fail non-retryable client errors (400, 401, 403)
                    if resp.status_code == 400:
                        err_msg = resp.text[:200]
                        logger.error(f"[GeminiProvider] 400 Bad Request en {model_name}: {err_msg}")
                        raise LlmBadResponse(f"Petición inválida a Gemini (HTTP 400): {err_msg}")

                    if resp.status_code in (401, 403):
                        err_msg = resp.text[:200]
                        logger.error(f"[GeminiProvider] Autenticación rechazada (HTTP {resp.status_code}): {err_msg}")
                        raise LlmUnavailable(f"Error de autenticación/autorización con Gemini (HTTP {resp.status_code})")

                    # Retryable rate limits
                    if resp.status_code == 429:
                        logger.warning(f"[GeminiProvider] Rate limit (429) en modelo {model_name}. Intento {attempt}.")
                        if attempt < settings.LLM_MAX_ATTEMPTS:
                            backoff = min(self.retry_delay_base * (2 ** (attempt - 1)) + (random.uniform(0.01, 0.05) if self.retry_delay_base > 0 else 0.0), 4.0)
                            if backoff > 0:
                                await asyncio.sleep(backoff)
                            continue
                        else:
                            # Move to next fallback model
                            last_exception = LlmRateLimited(f"Modelo {model_name} excedió rate limit (429)")
                            break

                    # Retryable server errors (5xx)
                    if resp.status_code >= 500:
                        logger.warning(f"[GeminiProvider] Error de servidor ({resp.status_code}) en {model_name}.")
                        if attempt < settings.LLM_MAX_ATTEMPTS:
                            backoff = min(self.retry_delay_base * (2 ** (attempt - 1)) + (random.uniform(0.01, 0.05) if self.retry_delay_base > 0 else 0.0), 4.0)
                            if backoff > 0:
                                await asyncio.sleep(backoff)
                            continue
                        else:
                            last_exception = LlmUnavailable(f"Modelo {model_name} falló con HTTP {resp.status_code}")
                            break

                    # Successful 200 OK
                    if resp.status_code == 200:
                        data = resp.json()
                        text = self._extract_text(data)
                        usage = self._extract_usage(data)
                        parsed_json = None

                        if req.json_schema:
                            cleaned_text = self._clean_json_fences(text)
                            try:
                                parsed_json = json.loads(cleaned_text)
                            except json.JSONDecodeError:
                                # Single-retry repair
                                parsed_json = await self._attempt_json_repair(
                                    client=client,
                                    model=model_name,
                                    api_key=api_key,
                                    req=req,
                                    invalid_text=text,
                                )
                                text = json.dumps(parsed_json)

                        latency_ms = (time.perf_counter() - start_time) * 1000.0
                        await self.circuit_breaker.record_success()

                        # Telemetry to ai_usage
                        await record_ai_usage(
                            project_id=req.project_id,
                            user_id=req.user_id,
                            purpose=req.purpose,
                            model=model_name,
                            tokens=usage,
                            latency_ms=latency_ms,
                            ok=True,
                        )

                        return LlmResponse(
                            text=text,
                            usage=usage,
                            model=model_name,
                            raw_json=parsed_json,
                            latency_ms=latency_ms,
                        )

                except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                    logger.warning(f"[GeminiProvider] Fallo de red/timeout en {model_name}: {net_err}")
                    if attempt < settings.LLM_MAX_ATTEMPTS:
                        backoff = min(self.retry_delay_base * (2 ** (attempt - 1)) + (random.uniform(0.01, 0.05) if self.retry_delay_base > 0 else 0.0), 4.0)
                        if backoff > 0:
                            await asyncio.sleep(backoff)
                        continue
                    else:
                        last_exception = LlmUnavailable(f"Timeout o fallo de conexión con {model_name}")
                        break

                except (LlmBadResponse, LlmUnavailable, ValidationError):
                    # Do not swallow non-retryable domain exceptions
                    raise

                except Exception as exc:
                    logger.error(f"[GeminiProvider] Excepción inesperada con {model_name}: {exc}")
                    last_exception = exc
                    break

        # If all models in the chain failed, record circuit breaker failure and propagate
        await self.circuit_breaker.record_failure()
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        await record_ai_usage(
            project_id=req.project_id,
            user_id=req.user_id,
            purpose=req.purpose,
            model=models_to_try[0] if models_to_try else "gemini",
            tokens={"prompt": 0, "candidates": 0, "total": 0, "thoughts": None},
            latency_ms=latency_ms,
            ok=False,
            error=str(last_exception),
        )

        if isinstance(last_exception, (LlmUnavailable, LlmRateLimited, LlmBadResponse, LlmQuotaExceeded)):
            raise last_exception
        raise LlmUnavailable(f"Todos los modelos de Gemini fallaron: {last_exception}")

    async def stream(self, req: LlmRequest) -> AsyncIterator[str]:
        """Streams content tokens using streamGenerateContent endpoint."""
        await self.circuit_breaker.check()
        api_key = self._resolve_api_key(req)
        models_to_try = self._build_model_chain(req.model)
        client = self._get_client()
        payload = self._build_payload(req)
        headers = {
            "x-goog-api-key": api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        target_model = models_to_try[0]
        url = f"{GEMINI_BASE_URL}/{target_model}:streamGenerateContent?alt=sse"

        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise LlmUnavailable(f"Streaming falló (HTTP {response.status_code}): {err_body.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            chunk_text = self._extract_text(chunk_json)
                            if chunk_text:
                                yield chunk_text
                        except Exception:
                            continue
        except (LlmError, ValidationError):
            raise
        except Exception as exc:
            logger.error(f"[GeminiProvider] Error de streaming: {exc}")
            raise LlmUnavailable(f"Fallo durante streaming de Gemini: {exc}")
