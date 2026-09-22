from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_current_user, require_role, get_user_repository
from app.modules.users.schemas import StandardResponse, UserUpdate, RoleUpdate, UserCreateAdmin, UserResponseAdmin
from app.modules.users.repository import UserRepository
from app.core.security import get_password_hash
from typing import List

router = APIRouter()

@router.post("/", response_model=StandardResponse)
async def create_user(
    data: UserCreateAdmin,
    request: Request,
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    user_data = {
        "name": data.name,
        "email": data.email,
        "password_hash": get_password_hash(data.password),
        "role": data.role if data.role in ["admin", "scrum_master", "dev"] else "dev",
        "avatar_url": None,
        "team_ids": data.team_ids or [],
        "is_active": True
    }
    user_id = await user_repo.create(user_data)
    await user_repo.log_audit(str(current_user["_id"]), "CREATE_USER", "users", user_id, metadata={"role": user_data["role"]}, ip=request.client.host)
    return StandardResponse(success=True, message="Usuario creado exitosamente", data={"id": user_id})

@router.get("/", response_model=StandardResponse)
async def list_users(current_user = Depends(get_current_user), user_repo: UserRepository = Depends(get_user_repository)):
    users = await user_repo.get_all()
    out = []
    for u in users:
        uid = str(u.pop("_id"))
        out.append({
            "id": uid,
            "name": u.get("name", "Usuario"),
            "email": u.get("email", ""),
            "role": u.get("role", "dev"),
            "avatar_url": u.get("avatar_url"),
            "team_ids": [str(t) for t in u.get("team_ids", [])],
            "is_active": u.get("is_active", True),
            "created_at": u.get("created_at"),
            "last_activity": u.get("last_activity")
        })
    return StandardResponse(success=True, message="Users listed", data=out)

@router.get("/{user_id}", response_model=StandardResponse)
async def get_user(user_id: str, current_user = Depends(get_current_user), user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["id"] = str(user.pop("_id"))
    return StandardResponse(success=True, message="User found", data=user)

@router.put("/{user_id}", response_model=StandardResponse)
async def update_user(user_id: str, data: UserUpdate, request: Request, current_user = Depends(get_current_user), user_repo: UserRepository = Depends(get_user_repository)):
    if str(current_user["_id"]) != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    await user_repo.update(user_id, update_data)
    await user_repo.log_audit(str(current_user["_id"]), "UPDATE_USER", "users", user_id, metadata=update_data, ip=request.client.host)
    return StandardResponse(success=True, message="User updated")

@router.delete("/{user_id}", response_model=StandardResponse)
async def delete_user(user_id: str, request: Request, current_user = Depends(require_role(["admin"])), user_repo: UserRepository = Depends(get_user_repository)):
    await user_repo.soft_delete(user_id)
    await user_repo.log_audit(str(current_user["_id"]), "DELETE_USER", "users", user_id, ip=request.client.host)
    return StandardResponse(success=True, message="User deleted")

@router.put("/{user_id}/role", response_model=StandardResponse)
async def change_role(user_id: str, data: RoleUpdate, request: Request, current_user = Depends(require_role(["admin"])), user_repo: UserRepository = Depends(get_user_repository)):
    if data.role not in ["admin", "scrum_master", "dev"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    await user_repo.update(user_id, {"role": data.role})
    await user_repo.log_audit(str(current_user["_id"]), "CHANGE_ROLE", "users", user_id, metadata={"role": data.role}, ip=request.client.host)
    return StandardResponse(success=True, message="Role updated")

@router.get("/{user_id}/audit-log", response_model=StandardResponse)
async def get_audit_log(user_id: str, current_user = Depends(require_role(["admin"])), user_repo: UserRepository = Depends(get_user_repository)):
    logs = await user_repo.get_audit_logs(user_id)
    out = []
    for log in logs:
        log["id"] = str(log.pop("_id"))
        log["user_id"] = str(log["user_id"])
        out.append(log)
    return StandardResponse(success=True, message="Audit logs", data=out)
