from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.modules.auth.schemas import UserPublic, validate_password_strength


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

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """Fields accepted by PUT /users/{id}.

    ``role``, ``is_active`` and ``email`` are privileged: the router rejects them
    for non-admin callers (self-service only allows name/avatar_url).
    """

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
