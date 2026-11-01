"""Domain exception hierarchy for ClassForge."""
from typing import Optional


class DomainError(Exception):
    """Base class for all business domain exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(DomainError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Recurso no encontrado",
        code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(message=message, code=code, status_code=404)


class ForbiddenError(DomainError):
    """Raised when the user does not have permission to access the resource."""

    def __init__(
        self,
        message: str = "Acceso denegado",
        code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(message=message, code=code, status_code=403)


class ConflictError(DomainError):
    """Raised when an operation conflicts with the current state of a resource."""

    def __init__(
        self,
        message: str = "Conflicto con el recurso actual",
        code: str = "CONFLICT",
    ) -> None:
        super().__init__(message=message, code=code, status_code=409)


class ValidationError(DomainError):
    """Raised when input validation fails in domain logic."""

    def __init__(
        self,
        message: str = "Error de validación",
        code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message=message, code=code, status_code=400)


class ExternalServiceError(DomainError):
    """Raised when a third-party or external dependency (e.g. AI provider) fails."""

    def __init__(
        self,
        message: str = "Error en servicio externo",
        code: str = "EXTERNAL_SERVICE_ERROR",
    ) -> None:
        super().__init__(message=message, code=code, status_code=502)


class RateLimitedError(DomainError):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Límite de solicitudes excedido. Intente más tarde.",
        code: str = "RATE_LIMITED",
    ) -> None:
        super().__init__(message=message, code=code, status_code=429)


class ServiceUnavailableError(DomainError):
    """Raised when a feature or service is temporarily disabled or unavailable."""

    def __init__(
        self,
        message: str = "Servicio temporalmente no disponible",
        code: str = "SERVICE_UNAVAILABLE",
    ) -> None:
        super().__init__(message=message, code=code, status_code=503)

