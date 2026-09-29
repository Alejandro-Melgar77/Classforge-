from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field


class StandardResponse(BaseModel):
    success: bool
    data: Any = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreateAdmin(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "dev"
    team_ids: Optional[List[str]] = []

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None

class RoleUpdate(BaseModel):
    role: str

class UserResponseAdmin(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    team_ids: List[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
