from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProjectModel(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    team_id: Optional[str]
    owner_id: str
    type: str
    status: str
    color_tag: str
    tags: List[str]
    is_deleted: bool
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
