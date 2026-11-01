"""
Domain models for AI findings lifecycle (P5 Bloque C).
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

FindingStatus = Literal["open", "acknowledged", "resolved", "dismissed"]
FindingSeverity = Literal["info", "warn", "critical"]


class AiFinding(BaseModel):
    """Represents a structural or semantic issue detected in a diagram with lifecycle tracking."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    diagram_id: str
    fingerprint: str
    rule: str
    role_id: str = "qa"
    severity: FindingSeverity = "warn"
    element_ids: List[str] = Field(default_factory=list)
    status: FindingStatus = "open"
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    dismissed_by: Optional[str] = None

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["_id"] = self.id
        return d

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "AiFinding":
        if not doc:
            raise ValueError("Document cannot be empty")
        data = dict(doc)
        if "_id" in data and "id" not in data:
            data["id"] = str(data["_id"])
        elif "_id" in data:
            data["id"] = str(data.get("id") or data["_id"])
        data.pop("_id", None)
        return cls.model_validate(data)


def compute_finding_fingerprint(rule: str, element_ids: List[str]) -> str:
    """Generates a deterministic fingerprint for a finding."""
    sorted_ids = ",".join(sorted(str(e) for e in element_ids))
    return f"{rule}:{sorted_ids}"
