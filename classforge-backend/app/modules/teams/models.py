from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TeamModel(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    scrum_master_id: str
    member_ids: List[str]
    avatar_color: str
    is_active: bool
    is_deleted: bool
    deleted_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
