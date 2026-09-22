from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TeamMemberInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str

class TeamCreate(BaseModel):
    name: str
    description: str = ""
    scrum_master_id: str
    member_ids: Optional[List[str]] = []

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scrum_master_id: Optional[str] = None
    member_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

class AddMemberRequest(BaseModel):
    user_id: str

class TeamResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    scrum_master_id: str
    scrum_master_name: Optional[str] = None
    member_ids: List[str] = []
    members: List[TeamMemberInfo] = []
    avatar_color: str = "#2563eb"
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_mongo(cls, doc):
        if not doc: return None
        raw_members = doc.get("member_ids", [])
        m_ids = [str(m) for m in raw_members] if isinstance(raw_members, list) else []
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name", "Equipo"),
            description=doc.get("description", ""),
            scrum_master_id=str(doc.get("scrum_master_id", "")),
            scrum_master_name=doc.get("scrum_master_name"),
            member_ids=m_ids,
            members=doc.get("members", []),
            avatar_color=doc.get("avatar_color", "#2563eb"),
            is_active=doc.get("is_active", True),
            created_by=str(doc.get("created_by", "")) if doc.get("created_by") else None,
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at")
        )
