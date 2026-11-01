from __future__ import annotations

from app.core.errors import DomainError


class LlmError(DomainError):
    """Base exception for all LLM-related failures."""

    def __init__(
        self,
        message: str = "Error en el servicio de IA",
        code: str = "LLM_ERROR",
        status_code: int = 502,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class LlmUnavailable(LlmError):
    """Raised when the LLM provider is down, network fails, or circuit breaker is open."""

    def __init__(
        self,
        message: str = "El servicio de IA no está disponible temporalmente",
        code: str = "LLM_UNAVAILABLE",
    ) -> None:
        super().__init__(message=message, code=code, status_code=503)


class LlmRateLimited(LlmError):
    """Raised when the upstream provider returns HTTP 429 (rate limit)."""

    def __init__(
        self,
        message: str = "Límite de peticiones de IA excedido. Por favor intenta más tarde.",
        code: str = "LLM_RATE_LIMITED",
    ) -> None:
        super().__init__(message=message, code=code, status_code=429)


class LlmBadResponse(LlmError):
    """Raised when the model response is invalid, unparseable, or fails JSON schema validation."""

    def __init__(
        self,
        message: str = "Respuesta del modelo de IA no válida o no conforme al esquema",
        code: str = "LLM_BAD_RESPONSE",
    ) -> None:
        super().__init__(message=message, code=code, status_code=502)


class LlmQuotaExceeded(LlmError):
    """Raised when project or user AI budget/token quota is exhausted."""

    def __init__(
        self,
        message: str = "Cuota de tokens o presupuesto de IA excedido",
        code: str = "LLM_QUOTA_EXCEEDED",
    ) -> None:
        super().__init__(message=message, code=code, status_code=429)
