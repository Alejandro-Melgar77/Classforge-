from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from app.core.database import get_db
from app.llm.models import LlmUsage

logger = logging.getLogger(__name__)


async def record_ai_usage(
    project_id: Optional[str],
    user_id: Optional[str],
    purpose: str,
    model: str,
    tokens: Union[LlmUsage, Dict[str, Any]],
    latency_ms: float,
    ok: bool,
    error: Optional[str] = None,
    db: Any = None,
) -> None:
    """
    Safely records an LLM invocation in the 'ai_usage' MongoDB collection.
    Groundwork for P5 token quotas and budget management.
    """
    try:
        database = db if db is not None else get_db()
        if database is None:
            return

        if isinstance(tokens, LlmUsage):
            tokens_dict = {
                "prompt": tokens.prompt_tokens,
                "candidates": tokens.candidates_tokens,
                "total": tokens.total_tokens,
                "thoughts": tokens.thoughts_tokens,
            }
        elif isinstance(tokens, dict):
            tokens_dict = tokens
        else:
            tokens_dict = {"prompt": 0, "candidates": 0, "total": 0, "thoughts": None}

        record = {
            "project_id": project_id,
            "user_id": user_id,
            "purpose": purpose,
            "model": model,
            "tokens": tokens_dict,
            "latency_ms": round(latency_ms, 2),
            "ok": ok,
            "error": error,
            "created_at": datetime.now(timezone.utc),
        }
        await database["ai_usage"].insert_one(record)
    except Exception as exc:
        logger.warning(f"[ai_usage] Failed to persist AI usage entry: {exc}")
