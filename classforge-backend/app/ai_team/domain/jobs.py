"""
Domain models for background AI jobs (P5 Bloque A).
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

JobKind = Literal["review_diagram", "answer_message", "run_task", "summarize_digest"]
JobOrigin = Literal["human", "ai"]
JobStatus = Literal["queued", "running", "done", "failed", "skipped", "cancelled"]


class AiJob(BaseModel):
    """Represents a durable asynchronous job executed by the AI worker."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    role_id: Optional[str] = None
    kind: JobKind
    payload: Dict[str, Any] = Field(default_factory=dict)
    dedupe_key: Optional[str] = None
    origin: JobOrigin = "human"
    status: JobStatus = "queued"
    attempts: int = 0
    max_attempts: int = 3
    run_after: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lease_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result_ref: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_mongo(self) -> Dict[str, Any]:
        """Converts model to MongoDB document dictionary."""
        d = self.model_dump()
        d["_id"] = self.id
        return d

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "AiJob":
        """Builds AiJob instance from MongoDB document."""
        if not doc:
            raise ValueError("Document cannot be empty")
        data = dict(doc)
        if "_id" in data and "id" not in data:
            data["id"] = str(data["_id"])
        elif "_id" in data:
            data["id"] = str(data.get("id") or data["_id"])
        data.pop("_id", None)
        for dt_field in ("run_after", "lease_until", "created_at", "updated_at"):
            val = data.get(dt_field)
            if isinstance(val, datetime) and val.tzinfo is None:
                data[dt_field] = val.replace(tzinfo=timezone.utc)
        return cls.model_validate(data)
