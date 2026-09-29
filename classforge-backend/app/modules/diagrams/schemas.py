from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class CreateDiagram(BaseModel):
    name: str
    description: str = ""
    image_url: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    member_ids: Optional[List[str]] = []

class UpdateDiagram(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    team_id: Optional[str] = None
    member_ids: Optional[List[str]] = None
    status: Optional[str] = None

class UpdateParticipants(BaseModel):
    member_ids: List[str]

class ParticipantItem(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_assigned: bool = False

class DiagramParticipantsResponse(BaseModel):
    diagram_id: str
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    assigned_member_ids: List[str] = []
    available_members: List[ParticipantItem] = []

class SaveGraph(BaseModel):
    graph_data: Dict[str, Any]
    comment: Optional[str] = None

class HistoryEntry(BaseModel):
    version: int
    saved_by: str
    saved_at: datetime
    comment: Optional[str] = None

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            version=doc.get("version"),
            saved_by=str(doc.get("saved_by")),
            saved_at=doc.get("saved_at"),
            comment=doc.get("comment")
        )

class HistoryEntryFull(HistoryEntry):
    graph_data: Dict[str, Any]
    
    @classmethod
    def from_mongo(cls, doc):
        return cls(
            version=doc.get("version"),
            saved_by=str(doc.get("saved_by")),
            saved_at=doc.get("saved_at"),
            comment=doc.get("comment"),
            graph_data=doc.get("graph_data", {})
        )

class DiagramResponse(BaseModel):
    id: str
    name: str
    description: str
    image_url: Optional[str] = None
    project_id: str
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    member_ids: List[str] = []
    created_by: str
    status: str
    is_public: bool
    version: int
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_mongo(cls, doc):
        if not doc: return None
        raw_members = doc.get("member_ids", [])
        member_ids = [str(m) for m in raw_members] if isinstance(raw_members, list) else []
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name", "Diagrama UML"),
            description=doc.get("description", ""),
            image_url=doc.get("image_url"),
            project_id=str(doc.get("project_id", "")),
            team_id=str(doc.get("team_id")) if doc.get("team_id") else None,
            team_name=doc.get("team_name"),
            member_ids=member_ids,
            created_by=str(doc.get("created_by", "")),
            status=doc.get("status", "draft"),
            is_public=doc.get("is_public", False),
            version=doc.get("version", 1),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc))
        )

class DiagramResponseFull(DiagramResponse):
    graph_data: Dict[str, Any]
    thumbnail_url: Optional[str] = None

    @classmethod
    def from_mongo(cls, doc):
        if not doc: return None
        base = DiagramResponse.from_mongo(doc)
        return cls(
            **base.model_dump(),
            graph_data=doc.get("graph_data", {}),
            thumbnail_url=doc.get("thumbnail_url")
        )

class WsTokenResponse(BaseModel):
    token: str
    expires_at: datetime
