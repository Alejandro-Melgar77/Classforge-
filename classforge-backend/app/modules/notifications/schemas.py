from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "info"  # info, project_update, diagram_update, ai_update, codegen, team_update
    project_id: Optional[str] = None
    diagram_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str
    project_id: Optional[str] = None
    diagram_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    meta: Optional[Dict[str, Any]] = None

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]):
        return cls(
            id=str(doc.get("_id")),
            user_id=str(doc.get("user_id")),
            title=doc.get("title", ""),
            message=doc.get("message", ""),
            type=doc.get("type", "info"),
            project_id=str(doc.get("project_id")) if doc.get("project_id") else None,
            diagram_id=str(doc.get("diagram_id")) if doc.get("diagram_id") else None,
            is_read=doc.get("is_read", False),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            meta=doc.get("meta")
        )


class NotificationsListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int
