from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_user_repository
from app.core.middleware import limiter
from app.modules.auth.schemas import RegisterRequest, LoginRequest, RefreshRequest, StandardResponse, TokenResponse
from app.modules.auth.repository import SessionRepository
from app.modules.users.repository import UserRepository
from app.core.security import get_password_hash, verify_password, create_access_token, generate_refresh_token, hash_refresh_token
from app.core.config import settings
from datetime import datetime, timedelta

router = APIRouter()

def get_session_repo(db = Depends(get_db)):
    return SessionRepository(db)

@router.post("/register", response_model=StandardResponse)
@limiter.limit("5/minute")
async def register(request: Request, data: RegisterRequest, user_repo: UserRepository = Depends(get_user_repository)):
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_data = {
        "email": data.email,
        "password_hash": get_password_hash(data.password),
        "name": data.name,
        "role": "dev",
        "avatar_url": None,
        "team_ids": []
    }
    user_id = await user_repo.create(user_data)
    await user_repo.log_audit(user_id, "REGISTER", "users", user_id, ip=request.client.host)
    
    return StandardResponse(success=True, message="User registered successfully", data={"id": user_id})

@router.post("/login", response_model=StandardResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, user_repo: UserRepository = Depends(get_user_repository), session_repo: SessionRepository = Depends(get_session_repo)):
    user = await user_repo.get_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(subject=str(user["_id"]))
    refresh_token = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token)
    
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await session_repo.create_session(str(user["_id"]), refresh_hash, data.device_info, request.client.host, expires_at)
    await user_repo.update_last_activity(str(user["_id"]))
    await user_repo.log_audit(str(user["_id"]), "LOGIN", "sessions", ip=request.client.host)
    
    user_profile = {
        "id": str(user["_id"]),
        "name": user.get("name", "Usuario"),
        "email": user.get("email"),
        "role": user.get("role", "dev"),
        "avatar_url": user.get("avatar_url"),
        "team_ids": [str(tid) for tid in user.get("team_ids", [])]
    }
    
    token_data = TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_profile)
    return StandardResponse(success=True, message="Login successful", data=token_data.model_dump())

@router.post("/refresh", response_model=StandardResponse)
async def refresh(data: RefreshRequest, session_repo: SessionRepository = Depends(get_session_repo), user_repo: UserRepository = Depends(get_user_repository)):
    old_hash = hash_refresh_token(data.refresh_token)
    session = await session_repo.get_active_session_by_hash(old_hash)
    if not session or session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    await session_repo.invalidate_session(str(session["_id"]))
    
    user_id = str(session["user_id"])
    access_token = create_access_token(subject=user_id)
    new_refresh = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh)
    
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await session_repo.create_session(user_id, new_hash, session["device_info"], session["ip_address"], expires_at)
    
    user = await user_repo.get_by_id(user_id)
    user_profile = None
    if user:
        user_profile = {
            "id": str(user["_id"]),
            "name": user.get("name", "Usuario"),
            "email": user.get("email"),
            "role": user.get("role", "dev"),
            "avatar_url": user.get("avatar_url"),
            "team_ids": [str(tid) for tid in user.get("team_ids", [])]
        }
    
    token_data = TokenResponse(access_token=access_token, refresh_token=new_refresh, user=user_profile)
    return StandardResponse(success=True, message="Token refreshed", data=token_data.model_dump())

@router.post("/logout", response_model=StandardResponse)
async def logout(request: Request, current_user = Depends(get_current_user), user_repo: UserRepository = Depends(get_user_repository)):
    await user_repo.log_audit(str(current_user["_id"]), "LOGOUT", "sessions", ip=request.client.host)
    return StandardResponse(success=True, message="Logged out successfully")

@router.post("/logout-all", response_model=StandardResponse)
async def logout_all(request: Request, current_user = Depends(get_current_user), session_repo: SessionRepository = Depends(get_session_repo), user_repo: UserRepository = Depends(get_user_repository)):
    await session_repo.invalidate_all_user_sessions(str(current_user["_id"]))
    await user_repo.log_audit(str(current_user["_id"]), "LOGOUT_ALL", "sessions", ip=request.client.host)
    return StandardResponse(success=True, message="Logged out from all sessions")

@router.get("/me", response_model=StandardResponse)
async def get_me(current_user = Depends(get_current_user)):
    user_data = dict(current_user)
    user_data["id"] = str(user_data.pop("_id"))
    return StandardResponse(success=True, message="User profile", data=user_data)

@router.get("/sessions", response_model=StandardResponse)
async def get_sessions(current_user = Depends(get_current_user), session_repo: SessionRepository = Depends(get_session_repo)):
    sessions = await session_repo.get_user_sessions(str(current_user["_id"]))
    sess_list = []
    for s in sessions:
        s["id"] = str(s.pop("_id"))
        s["user_id"] = str(s["user_id"])
        sess_list.append(s)
    return StandardResponse(success=True, message="Active sessions", data=sess_list)
