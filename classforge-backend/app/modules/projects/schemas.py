from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    name: str
    description: str
    team_id: Optional[str]
    owner_id: str
    type: str
    status: str
    color_tag: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    @classmethod
    def from_mongo(cls, doc):
        if not doc: return None
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name"),
            description=doc.get("description"),
            team_id=str(doc.get("team_id")) if doc.get("team_id") else None,
            owner_id=str(doc.get("owner_id")),
            type=doc.get("type"),
            status=doc.get("status"),
            color_tag=doc.get("color_tag"),
            tags=doc.get("tags", []),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
            completed_at=doc.get("completed_at")
        )
