from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> str:
    """Enforces the minimum password policy shared by register/create/change.

    Raises ValueError so Pydantic turns it into a 422 validation error.
    """
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("La contraseña debe incluir al menos una letra")
    if not re.search(r"\d", password):
        raise ValueError("La contraseña debe incluir al menos un dígito")
    return password


class StandardResponse(BaseModel):
    success: bool
    data: Any = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str = "dev"
    avatar_url: Optional[str] = None
    team_ids: List[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = {"extra": "ignore"}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)

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

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class SessionPublic(BaseModel):
    """Public projection of a session; never exposes refresh_token_hash."""

    id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    current: bool = False

    model_config = {"extra": "ignore"}


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
