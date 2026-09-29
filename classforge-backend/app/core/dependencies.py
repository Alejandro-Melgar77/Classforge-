from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_db
from app.modules.users.repository import UserRepository

security = HTTPBearer()


def get_user_repository(db: Any = Depends(get_db)) -> UserRepository:
    """Dependency provider for UserRepository instance."""
    return UserRepository(db)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Dict[str, Any]:
    """Validate JWT access token and retrieve current active user."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await user_repo.get_by_id(user_id)
    if user is None or user.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")

    last_activity = user.get("last_activity")
    if last_activity:
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        if now - last_activity > timedelta(minutes=settings.INACTIVITY_TIMEOUT_MINUTES):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired due to inactivity")

    await user_repo.update_last_activity(user_id)
    
    return user


def require_role(roles: List[str]) -> Callable:
    """Dependency factory checking that the authenticated user possesses one of the required roles."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return role_checker

