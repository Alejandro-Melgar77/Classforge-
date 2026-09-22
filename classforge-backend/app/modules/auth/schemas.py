from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict, List
from datetime import datetime

class StandardResponse(BaseModel):
    success: bool
    data: Any = None
    message: str
    timestamp: datetime = datetime.utcnow()

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
