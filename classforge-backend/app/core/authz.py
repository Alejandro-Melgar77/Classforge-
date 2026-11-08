"""Authorization policies and dependencies for ClassForge."""
from typing import Any, Dict, Optional
from bson import ObjectId
from fastapi import Depends, Path

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.errors import ForbiddenError, NotFoundError
from app.core.utils import validate_object_id


# ── Domain Policies (Pure python logic) ────────────────────────────────────────

def can_access_project(
    user: Dict[str, Any],
    project: Dict[str, Any],
    team: Optional[Dict[str, Any]] = None,
) -> bool:
    """Evaluates whether the user has access to a project.
    
    Access granted if:
    - User has admin role.
    - User is the project owner (owner_id).
    - User is the Scrum Master of the project's assigned team.
    - User is an active member in the project's assigned team (member_ids).
    """
    if not user or not project:
        return False

    user_id = str(user.get("_id") or user.get("id"))
    role = user.get("role")

    if role == "admin":
        return True

    if str(project.get("owner_id")) == user_id or str(project.get("created_by")) == user_id:
        return True

    project_members = [str(m) for m in project.get("member_ids", [])]
    if user_id in project_members:
        return True

    proj_team_id = str(project.get("team_id")) if project.get("team_id") else None
    if proj_team_id:
        user_teams = [str(t) for t in user.get("team_ids", [])]
        if proj_team_id in user_teams:
            return True

    if team:
        if str(team.get("scrum_master_id")) == user_id:
            return True
        team_members = [str(m) for m in team.get("member_ids", [])]
        if user_id in team_members:
            return True

    return False


def can_access_diagram(
    user: Dict[str, Any],
    diagram: Dict[str, Any],
    team: Optional[Dict[str, Any]] = None,
    project: Optional[Dict[str, Any]] = None,
) -> bool:
    """Evaluates whether the user has access to a diagram.
    
    Access granted if:
    - User has admin role.
    - User created the diagram (created_by / creator_id).
    - User is listed in the diagram's participants (member_ids).
    - User is Scrum Master or member of the diagram's assigned team.
    - User has access to the parent project if associated.
    """
    if not user or not diagram:
        return False

    user_id = str(user.get("_id") or user.get("id"))
    role = user.get("role")

    if role == "admin":
        return True

    creator = str(diagram.get("created_by") or diagram.get("creator_id") or "")
    if creator == user_id:
        return True

    diagram_members = [str(m) for m in diagram.get("member_ids", [])]
    if user_id in diagram_members:
        return True

    if team:
        if str(team.get("scrum_master_id")) == user_id:
            return True
        team_members = [str(m) for m in team.get("member_ids", [])]
        if user_id in team_members:
            return True

    if project:
        if can_access_project(user, project, team):
            return True

    return False


# ── FastAPI Dependencies ───────────────────────────────────────────────────────

async def require_project_member(
    project_id: str = Path(..., description="Project ObjectId"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> Dict[str, Any]:
    """Dependency ensuring the authenticated user is authorized to access the project."""
    oid = validate_object_id(project_id, "project_id")
    project = await db["projects"].find_one({"_id": oid, "is_deleted": False})
    if not project:
        raise NotFoundError("Proyecto no encontrado")

    team = None
    if project.get("team_id"):
        team = await db["teams"].find_one({"_id": ObjectId(project["team_id"]), "is_deleted": False})

    if not can_access_project(current_user, project, team):
        # Fallback: check if the user is a participant or creator of any diagram within this project
        user_id = str(current_user.get("_id") or current_user.get("id"))
        user_matches = [user_id]
        if ObjectId.is_valid(user_id):
            user_matches.append(ObjectId(user_id))
        has_diagram = await db["diagrams"].find_one({
            "project_id": {"$in": [project_id, oid]},
            "is_deleted": {"$ne": True},
            "$or": [
                {"created_by": {"$in": user_matches}},
                {"creator_id": {"$in": user_matches}},
                {"member_ids": {"$in": user_matches}}
            ]
        })
        if not has_diagram:
            raise ForbiddenError("No tienes acceso a este proyecto")

    return project


async def require_diagram_access(
    diagram_id: str = Path(..., description="Diagram ObjectId"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> Dict[str, Any]:
    """Dependency ensuring the authenticated user is authorized to access the diagram."""
    oid = validate_object_id(diagram_id, "diagram_id")
    diagram = await db["diagrams"].find_one({"_id": oid, "is_deleted": False})
    if not diagram:
        raise NotFoundError("Diagrama no encontrado")

    team = None
    if diagram.get("team_id"):
        team = await db["teams"].find_one({"_id": ObjectId(diagram["team_id"]), "is_deleted": False})

    project = None
    if diagram.get("project_id"):
        project = await db["projects"].find_one({"_id": ObjectId(diagram["project_id"]), "is_deleted": False})
        if project and not team and project.get("team_id"):
            team = await db["teams"].find_one({"_id": ObjectId(project["team_id"]), "is_deleted": False})

    if not can_access_diagram(current_user, diagram, team, project):
        raise ForbiddenError("No tienes acceso a este diagrama")

    return diagram


def _as_object_id(value: Any) -> Optional[ObjectId]:
    """Best-effort conversion of a stored reference to ObjectId."""
    if isinstance(value, ObjectId):
        return value
    if value and ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return None


async def require_folder_access(
    folder_id: str = Path(..., description="Folder ObjectId"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> Dict[str, Any]:
    """Dependency ensuring the authenticated user may read/modify a folder.

    Access is granted to admins, the folder owner, members of the folder's team
    and users with access to the folder's project. Without this check every
    authenticated user could read, rename and delete any folder by id.
    """
    oid = validate_object_id(folder_id, "folder_id")
    folder = await db["folders"].find_one({"_id": oid, "is_deleted": False})
    if not folder:
        raise NotFoundError("Carpeta no encontrada")

    user_id = str(current_user.get("_id") or current_user.get("id"))
    if current_user.get("role") == "admin":
        return folder
    if str(folder.get("owner_id")) == user_id:
        return folder

    team: Optional[Dict[str, Any]] = None
    team_oid = _as_object_id(folder.get("team_id"))
    if team_oid:
        team = await db["teams"].find_one({"_id": team_oid, "is_deleted": False})
        if team:
            team_members = [str(m) for m in team.get("member_ids", [])]
            if str(team.get("scrum_master_id")) == user_id or user_id in team_members:
                return folder

    project_oid = _as_object_id(folder.get("project_id"))
    if project_oid:
        project = await db["projects"].find_one({"_id": project_oid, "is_deleted": False})
        if project and can_access_project(current_user, project, team):
            return folder

    raise ForbiddenError("No tienes acceso a esta carpeta")
