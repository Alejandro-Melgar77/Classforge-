"""
AI Chat Router — Group collaborative AI chat with role-based personas.
All endpoints require authentication via JWT.
"""
from __future__ import annotations
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.ai_chat.schemas import (
    AiMessage,
    AiMessageCreate,
    AiRoleActivate,
    AiRoleStatus,
    AiRoleChatRequest,
    AiRoleChatResponse,
    AiTask,
    AiTaskCreate,
)
from app.modules.ai_chat.service import AiChatService
from app.modules.ai_chat.repository import AiConversationRepository, AiTaskRepository
from app.modules.ai.role_prompts import AI_ROLE_CONFIGS

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AiChatService:
    return AiChatService(db)


# ── Message Endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/messages",
    response_model=AiRoleChatResponse,
    summary="Send a message to the project's AI chat",
)
async def send_message(
    project_id: str,
    body: AiRoleChatRequest,
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Sends a user message to the group AI chat.
    If an AI role is active, automatically generates and saves the AI response.
    """
    try:
        body.project_id = project_id
        return await service.send_message_with_role(
            request=body,
            user_id=str(current_user["_id"]),
            username=current_user.get("username", "Usuario"),
            user_role=current_user.get("role", "dev"),
        )
    except Exception as e:
        logger.error(f"[AiChatRouter] send_message error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/history",
    summary="Get full group chat history for a project",
)
async def get_group_history(
    project_id: str,
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns the full message history of all team members + AI for a project."""
    repo = AiConversationRepository(db)
    messages = await repo.get_all_messages(project_id, limit=limit)
    return {"project_id": project_id, "messages": messages, "total": len(messages)}


@router.get(
    "/projects/{project_id}/history/mine",
    summary="Get personal chat history (current user + AI responses)",
)
async def get_my_history(
    project_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns only the current user's messages and AI responses to them."""
    repo = AiConversationRepository(db)
    messages = await repo.get_messages_for_user(
        project_id, str(current_user["_id"]), limit=limit
    )
    return {"project_id": project_id, "messages": messages, "total": len(messages)}


# ── Role Endpoints ─────────────────────────────────────────────────────────────

@router.put(
    "/projects/{project_id}/roles",
    summary="Activate or deactivate an AI role for a project",
)
async def set_role(
    project_id: str,
    body: AiRoleActivate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Activates or deactivates a specific AI role for the project.
    Only admins and scrum masters can change role configuration.
    """
    user_role = current_user.get("role", "dev")
    if user_role not in ("admin", "scrum_master"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Scrum Master o Admin pueden activar roles de IA.",
        )
    repo = AiConversationRepository(db)
    current_roles = await repo.get_active_roles(project_id)
    roles_set = set(current_roles)
    if body.active:
        roles_set.add(body.role_id)
    else:
        roles_set.discard(body.role_id)
    await repo.set_active_roles(project_id, list(roles_set))
    return {"project_id": project_id, "active_ai_roles": list(roles_set)}


@router.get(
    "/projects/{project_id}/roles",
    response_model=list[AiRoleStatus],
    summary="Get active AI roles for a project",
)
async def get_roles(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns all available roles with their active status for the project."""
    repo = AiConversationRepository(db)
    active = await repo.get_active_roles(project_id)
    active_set = set(active)
    return [
        AiRoleStatus(
            role_id=cfg["id"],
            label=cfg["label"],
            emoji=cfg["emoji"],
            description=cfg["description"],
            is_active=cfg["id"] in active_set,
        )
        for cfg in AI_ROLE_CONFIGS.values()
    ]


# ── Task Endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/tasks",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task assigned to an AI role",
)
async def create_task(
    project_id: str,
    body: AiTaskCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Creates a new task for an AI role to execute."""
    repo = AiTaskRepository(db)
    task_id = await repo.create(project_id, str(current_user["_id"]), body)
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear la tarea.",
        )
    return {"task_id": task_id, "status": "pending", "message": "Tarea creada exitosamente."}


@router.get(
    "/projects/{project_id}/tasks",
    summary="List all AI tasks for a project",
)
async def list_tasks(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns all tasks assigned to AI roles within a project."""
    repo = AiTaskRepository(db)
    tasks = await repo.list_by_project(project_id)
    serialized = []
    for t in tasks:
        t["id"] = str(t.pop("_id", ""))
        t["project_id"] = str(t.get("project_id", ""))
        if t.get("diagram_id"):
            t["diagram_id"] = str(t["diagram_id"])
        if t.get("assigned_by"):
            t["assigned_by"] = str(t["assigned_by"])
        serialized.append(t)
    return {"project_id": project_id, "tasks": serialized, "total": len(serialized)}


@router.patch(
    "/projects/{project_id}/tasks/{task_id}/execute",
    response_model=AiTask,
    summary="Force execution of a pending AI task",
)
async def execute_task(
    project_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Triggers immediate execution of a pending or failed AI task."""
    try:
        return await service.execute_task(task_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[AiChatRouter] execute_task error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
