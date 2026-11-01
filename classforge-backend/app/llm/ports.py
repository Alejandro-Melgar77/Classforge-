from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable
from app.llm.models import LlmRequest, LlmResponse


@runtime_checkable
class LlmProvider(Protocol):
    """Protocol for LLM provider adapters."""

    async def generate(self, req: LlmRequest) -> LlmResponse:
        """Generates a complete response for the given LLM request."""
        ...

    async def stream(self, req: LlmRequest) -> AsyncIterator[str]:
        """Streams text response chunks for the given LLM request."""
        ...
