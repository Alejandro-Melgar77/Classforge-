from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FolderCreate(BaseModel):
    name: str
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    parent_folder_id: Optional[str] = None
    type: str # personal | team | project

class FolderUpdate(BaseModel):
    name: str

class FolderResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    team_id: Optional[str]
    project_id: Optional[str]
    parent_folder_id: Optional[str]
    type: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_mongo(cls, doc):
        if not doc: return None
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name"),
            owner_id=str(doc.get("owner_id")),
            team_id=str(doc.get("team_id")) if doc.get("team_id") else None,
            project_id=str(doc.get("project_id")) if doc.get("project_id") else None,
            parent_folder_id=str(doc.get("parent_folder_id")) if doc.get("parent_folder_id") else None,
            type=doc.get("type"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at")
        )
