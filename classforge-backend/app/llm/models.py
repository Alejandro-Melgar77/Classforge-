from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LlmMessage(BaseModel):
    """Represents a single conversational turn for an LLM."""
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "model"]
    text: str = ""
    image_bytes: Optional[bytes] = Field(default=None, repr=False)
    mime_type: Optional[str] = None


class LlmUsage(BaseModel):
    """Token usage metrics extracted from provider response."""
    model_config = ConfigDict(extra="ignore")

    prompt_tokens: int = 0
    candidates_tokens: int = 0
    total_tokens: int = 0
    thoughts_tokens: Optional[int] = None


class LlmResponse(BaseModel):
    """Standardized response from an LLM provider."""
    model_config = ConfigDict(extra="ignore")

    text: str
    usage: LlmUsage = Field(default_factory=LlmUsage)
    model: str
    raw_json: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0


class LlmRequest(BaseModel):
    """Standardized request sent to an LLM provider."""
    model_config = ConfigDict(extra="ignore")

    system: str = ""
    messages: List[LlmMessage] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    json_schema: Optional[Dict[str, Any]] = None
    thinking: Optional[Literal["low", "medium", "high"]] = None
    purpose: str = "chat"  # "chat" | "task" | "codegen" | "vision"
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key: Optional[SecretStr] = Field(default=None, repr=False)
    model: Optional[str] = None
