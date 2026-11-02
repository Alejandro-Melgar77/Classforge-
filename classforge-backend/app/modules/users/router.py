from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from typing import List, Optional
from bson import ObjectId

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, get_user_repository
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.security import get_password_hash
from app.core.utils import validate_object_id
from app.modules.users.schemas import (
    StandardResponse, UserUpdate, RoleUpdate, UserCreateAdmin, UserPublic
)
from app.modules.users.repository import UserRepository

router = APIRouter()


@router.post("", response_model=StandardResponse, include_in_schema=False)
@router.post("/", response_model=StandardResponse)
async def create_user(
    data: UserCreateAdmin,
    request: Request,
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise ValidationError("El correo electrónico ya está registrado")
    
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


@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_users(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    skip = (page - 1) * limit
    if hasattr(user_repo, "count_all"):
        total = await user_repo.count_all()
    else:
        total = 0

    try:
        users = await user_repo.get_all(skip=skip, limit=limit)
    except TypeError:
        users = await user_repo.get_all()
        if not total:
            total = len(users)

    if not total and users:
        total = len(users)

    response.headers["X-Total-Count"] = str(total)
    
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


@router.get("/directory", response_model=StandardResponse)
async def user_directory(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Minimal user directory for participant pickers.

    Only ``id``, ``name`` and ``role`` are exposed. Non-admin callers see just the
    people they share a team with (plus themselves), never the full user table.
    """
    query: dict = {"is_deleted": False, "is_active": True}

    if current_user.get("role") != "admin":
        user_id = current_user.get("_id") or current_user.get("id")
        team_refs = []
        for raw_team_id in current_user.get("team_ids", []):
            if ObjectId.is_valid(str(raw_team_id)):
                team_refs.append(ObjectId(str(raw_team_id)))

        visible_ids = {user_id} if user_id else set()
        if team_refs:
            teams = await db["teams"].find(
                {"_id": {"$in": team_refs}, "is_deleted": False},
                {"member_ids": 1, "scrum_master_id": 1},
            ).to_list(length=100)
            for team in teams:
                if team.get("scrum_master_id"):
                    visible_ids.add(team["scrum_master_id"])
                for member_id in team.get("member_ids", []):
                    visible_ids.add(member_id)

        query["_id"] = {"$in": list(visible_ids)}

    users = await db["users"].find(query, {"name": 1, "role": 1}).sort("name", 1).to_list(length=500)
    data = [
        {
            "id": str(u["_id"]),
            "name": u.get("name", "Usuario"),
            "role": u.get("role", "dev"),
        }
        for u in users
    ]
    return StandardResponse(success=True, message="Directory retrieved", data=data)


@router.get("/{user_id}", response_model=StandardResponse)
async def get_user(
    user_id: str,
    current_user = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    validate_object_id(user_id, "user_id")
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise NotFoundError("User not found")
    user_public = UserPublic(
        id=str(user.get("_id") or user.get("id")),
        name=user.get("name", "Usuario"),
        email=user.get("email", ""),
        role=user.get("role", "dev"),
        avatar_url=user.get("avatar_url"),
        team_ids=[str(t) for t in user.get("team_ids", [])],
        is_active=user.get("is_active", True),
    )
    return StandardResponse(success=True, message="User found", data=user_public.model_dump())


@router.put("/{user_id}", response_model=StandardResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    request: Request,
    current_user = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    validate_object_id(user_id, "user_id")
    if str(current_user["_id"]) != user_id and current_user.get("role") != "admin":
        raise ForbiddenError("Not authorized to update this user")

    is_admin = current_user.get("role") == "admin"
    provided = {k: v for k, v in data.model_dump().items() if v is not None}

    # Privilege escalation guard: self-service only allows name/avatar_url.
    privileged = {"role", "is_active", "email"}
    attempted = sorted(privileged.intersection(provided))
    if attempted and not is_admin:
        raise ForbiddenError(
            "Solo un administrador puede modificar: " + ", ".join(attempted)
        )

    if "role" in provided and provided["role"] not in ["admin", "scrum_master", "dev"]:
        raise ValidationError("Rol inválido")

    await user_repo.update(user_id, provided)
    await user_repo.log_audit(str(current_user["_id"]), "UPDATE_USER", "users", user_id, metadata=provided, ip=request.client.host)
    return StandardResponse(success=True, message="User updated")


@router.delete("/{user_id}", response_model=StandardResponse)
async def delete_user(
    user_id: str,
    request: Request,
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    validate_object_id(user_id, "user_id")
    await user_repo.soft_delete(user_id)
    await user_repo.log_audit(str(current_user["_id"]), "DELETE_USER", "users", user_id, ip=request.client.host)
    return StandardResponse(success=True, message="User deleted")


@router.put("/{user_id}/role", response_model=StandardResponse)
async def change_role(
    user_id: str,
    data: RoleUpdate,
    request: Request,
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    validate_object_id(user_id, "user_id")
    if data.role not in ["admin", "scrum_master", "dev"]:
        raise ValidationError("Invalid role")
    await user_repo.update(user_id, {"role": data.role})
    await user_repo.log_audit(str(current_user["_id"]), "CHANGE_ROLE", "users", user_id, metadata={"role": data.role}, ip=request.client.host)
    return StandardResponse(success=True, message="Role updated")


@router.get("/{user_id}/audit-log", response_model=StandardResponse)
async def get_audit_log(
    user_id: str,
    current_user = Depends(require_role(["admin"])),
    user_repo: UserRepository = Depends(get_user_repository)
):
    validate_object_id(user_id, "user_id")
    logs = await user_repo.get_audit_logs(user_id)
    out = []
    for log in logs:
        log["id"] = str(log.pop("_id"))
        log["user_id"] = str(log["user_id"])
        out.append(log)
    return StandardResponse(success=True, message="Audit logs", data=out)
