from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    team_id: Optional[str] = None
    type: str = "personal" # team | personal
    tags: List[str] = []

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    color_tag: Optional[str] = None

class ProjectStatusUpdate(BaseModel):
    status: str # in_progress | completed | review | archived

class ProjectResponse(BaseModel):
    id: str
    name: str = "Sin título"
    description: Optional[str] = ""
    team_id: Optional[str] = None
    owner_id: Optional[str] = ""
    type: str = "personal"
    status: str = "in_progress"
    color_tag: Optional[str] = "#3b82f6"
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def from_mongo(cls, doc):
        if not doc:
            return None
        now = datetime.now(timezone.utc)
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name") or "Sin título",
            description=doc.get("description") or "",
            team_id=str(doc.get("team_id")) if doc.get("team_id") else None,
            owner_id=str(doc.get("owner_id") or ""),
            type=doc.get("type") or "personal",
            status=doc.get("status") or "in_progress",
            color_tag=doc.get("color_tag") or "#3b82f6",
            tags=doc.get("tags") or [],
            created_at=doc.get("created_at") or now,
            updated_at=doc.get("updated_at") or now,
            completed_at=doc.get("completed_at"),
        )
