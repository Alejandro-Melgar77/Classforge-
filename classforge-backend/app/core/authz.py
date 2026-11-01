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

    if str(project.get("owner_id")) == user_id:
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
