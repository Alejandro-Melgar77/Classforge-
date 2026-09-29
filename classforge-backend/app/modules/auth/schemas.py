from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class StandardResponse(BaseModel):
    success: bool
    data: Any = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: str = "Unknown Device"

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
