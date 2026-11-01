"""
AI Chat Router — Team AI chat with personal thread (Chat) vs shared history (Historial),
role-based personas, real-time WebSocket token generation, and shared audited state.
All project endpoints require authentication and project membership (require_project_member).
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.authz import require_project_member
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.errors import DomainError, ExternalServiceError, ForbiddenError, NotFoundError, ServiceUnavailableError, ValidationError
from app.core.middleware import limiter
from app.core.utils import validate_object_id
from app.modules.collaboration.connection_manager import manager
from app.modules.collaboration.service import generate_project_ws_token
from app.ai_team.domain.roles import list_roles, ROLES_REGISTRY
from app.ai_team.infrastructure.knowledge_loader import knowledge_loader
from app.modules.ai_chat.infrastructure.repositories import (
    AiMessageRepository,
    AiProjectStateRepository,
    AiTaskRepository,
)
from app.modules.ai_chat.schemas import (
    AiMessage,
    AiMessageCreate,
    AiRoleActivate,
    AiRoleStatus,
    AiRoleChatRequest,
    AiSendMessageResponse,
    AiHistoryResponse,
    AiProjectStateResponse,
    AiProjectStateUpdateRequest,
    ProposalStateUpdateRequest,
    AiTask,
    AiTaskCreate,
    AiTaskUpdateRequest,
    WsTokenResponse,
)
from app.modules.ai_chat.service import AiChatService

logger = logging.getLogger(__name__)


def verify_ai_chat_enabled() -> None:
    if not settings.AI_CHAT_ENABLED:
        raise ServiceUnavailableError("El servicio de chat con IA está temporalmente deshabilitado.")


router = APIRouter(dependencies=[Depends(verify_ai_chat_enabled)])


def _get_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AiChatService:
    return AiChatService(db)


# ── Knowledge Base Endpoints (Admin Only) ──────────────────────────────────────

@router.get(
    "/knowledge/manifest",
    summary="Get knowledge base files and token sizes (admin only)",
)
async def get_knowledge_manifest(
    admin_user: dict = Depends(require_role(["admin"])),
):
    """Returns metadata manifest of all loaded knowledge files with their byte and token counts."""
    return knowledge_loader.get_manifest()


# ── Global Roles Catalog Endpoint ──────────────────────────────────────────────

@router.get(
    "/roles",
    summary="Get all available AI role definitions and UI skins",
)
async def get_all_roles(
    current_user: dict = Depends(get_current_user),
):
    """Returns all AI roles configured in the system along with their UI skins and triggers."""
    return [r.model_dump() for r in list_roles()]


# ── Project WebSocket Token ───────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/ws-token",
    summary="Generate a single-use token for project WebSocket connection",
)
async def get_project_ws_token_endpoint(
    project_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
):
    """Generates a single-use token for authenticating into the project-level WebSocket room."""
    token_data = await generate_project_ws_token(project_id, str(current_user["_id"]))
    return {
        "success": True,
        "message": "Token generated",
        "data": WsTokenResponse(**token_data).model_dump(),
    }


# ── Message Endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/messages",
    response_model=AiSendMessageResponse,
    summary="Send a message to the project's AI chat",
)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    project_id: str,
    body: AiRoleChatRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Sends a user message to the project AI chat.
    Idempotent by client_id. ai_role is optional.
    Responds immediately with {message, ai_pending: [...]};
    AI responses are generated in the background and delivered via WS or history?after=.
    """
    try:
        if body.api_key:
            logger.warning("[AiChat] Field 'api_key' in request body is deprecated; use header 'X-Gemini-Key'")
        body.api_key = x_gemini_key or body.api_key
        body.project_id = project_id
        return await service.send_message_with_role(
            request=body,
            user_id=str(current_user["_id"]),
            username=current_user.get("name", "Usuario"),
            user_role=current_user.get("role", "dev"),
        )
    except DomainError:
        raise
    except Exception as e:
        logger.error(f"[AiChatRouter] send_message error: {e}")
        raise ExternalServiceError("Error al procesar el mensaje con el asistente de IA")


@router.post(
    "/projects/{project_id}/messages/{message_id}/retry",
    summary="Retry a failed AI response message",
)
async def retry_message(
    project_id: str,
    message_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Retries generation for an AI message that previously failed with status 'error'."""
    try:
        return await service.retry_ai_message(message_id, project_id, current_user)
    except DomainError:
        raise
    except Exception as e:
        logger.error(f"[AiChatRouter] retry_message error: {e}")
        raise ExternalServiceError("Error al reintentar el mensaje")


@router.get(
    "/projects/{project_id}/history",
    response_model=AiHistoryResponse,
    summary="Get full group chat history for a project (cursor paginated)",
)
async def get_group_history(
    project_id: str,
    before: Optional[str] = None,
    after: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    member: Optional[str] = None,
    role: Optional[str] = None,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns the full message history (all personal threads + project announcements) paginated in MongoDB."""
    repo = AiMessageRepository(db)
    messages, total, next_cursor = await repo.get_history(
        project_id,
        before=before,
        after=after,
        limit=limit,
        member=member,
        role=role,
    )
    return {
        "project_id": project_id,
        "messages": messages,
        "total": total,
        "next_cursor": next_cursor,
    }


@router.get(
    "/projects/{project_id}/history/mine",
    response_model=AiHistoryResponse,
    summary="Get personal chat history (current user thread + project announcements)",
)
async def get_my_history(
    project_id: str,
    before: Optional[str] = None,
    after: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns only the current user's personal thread plus project-level AI announcements."""
    repo = AiMessageRepository(db)
    messages, total, next_cursor = await repo.get_mine_history(
        project_id,
        user_id=str(current_user["_id"]),
        before=before,
        after=after,
        limit=limit,
    )
    return {
        "project_id": project_id,
        "messages": messages,
        "total": total,
        "next_cursor": next_cursor,
    }


# ── Proposal State Endpoint ───────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/messages/{message_id}/proposals/{proposal_id}/state",
    summary="Mark a structured proposal as applied or dismissed",
)
async def set_proposal_state(
    project_id: str,
    message_id: str,
    proposal_id: str,
    body: ProposalStateUpdateRequest,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Audits whether a proposed UML command was applied or dismissed by a team member."""
    repo = AiMessageRepository(db)
    updated_msg = await repo.update_proposal_state(
        message_id=message_id,
        proposal_id=proposal_id,
        status=body.status,
        user_id=str(current_user["_id"]),
    )
    if not updated_msg:
        raise NotFoundError("Mensaje no encontrado para actualizar propuesta")

    # Broadcast update via project WS
    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_MESSAGE_UPDATED",
        "message": updated_msg,
    })
    return {"message": updated_msg, "proposal_id": proposal_id, "status": body.status}


# ── Project AI State Endpoints ────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/state",
    response_model=AiProjectStateResponse,
    summary="Get shared project AI state (participative mode, role autonomy, digest)",
)
async def get_project_state(
    project_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns the shared and audited AI project state."""
    repo = AiProjectStateRepository(db)
    state = await repo.get_or_create(project_id)
    return state


@router.put(
    "/projects/{project_id}/state",
    response_model=AiProjectStateResponse,
    summary="Update participative mode or role autonomy settings",
)
async def update_project_state(
    project_id: str,
    body: AiProjectStateUpdateRequest,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Updates shared project state.
    Any member can toggle participative or enabled roles.
    Setting autonomy: 'apply' is strictly restricted to owner, scrum_master, or admin.
    """
    user_id = str(current_user["_id"])
    user_role = current_user.get("role", "dev")
    is_owner = str(project.get("owner_id", "")) == user_id
    can_apply = is_owner or user_role in ("admin", "scrum_master")

    repo = AiProjectStateRepository(db)

    # 1. Update participative flag if provided
    if body.participative is not None and "enabled" in body.participative:
        is_enabled = bool(body.participative["enabled"])
        await repo.update_participative(
            project_id=project_id,
            enabled=is_enabled,
            user_id=user_id,
        )
        if not is_enabled:
            from app.ai_team.infrastructure.job_repository import AiJobRepository
            await AiJobRepository(db).cancel_project_queued_jobs(project_id)

    # 2. Update roles if provided
    if body.roles is not None:
        for r in body.roles:
            if r.get("autonomy") == "apply" and not can_apply:
                raise ForbiddenError("Solo Scrum Master, Owner o Admin pueden configurar autonomía 'apply'")
        await repo.update_roles(project_id, body.roles, user_id=user_id)

    # 3. Update local_only privacy flag if provided
    if body.local_only is not None:
        await repo.update_local_only(project_id, bool(body.local_only), user_id=user_id)

    updated_state = await repo.get_or_create(project_id)

    # Broadcast state change to all connected project members
    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_STATE_CHANGED",
        "state": updated_state,
    })

    return updated_state


@router.put(
    "/projects/{project_id}/roles",
    summary="Activate/deactivate role or set autonomy (alias for state/roles)",
)
async def set_role_alias(
    project_id: str,
    body: Dict[str, Any] = Body(...),
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Preserved alias for activating/deactivating a specific role."""
    user_id = str(current_user["_id"])
    user_role = current_user.get("role", "dev")
    is_owner = str(project.get("owner_id", "")) == user_id
    can_apply = is_owner or user_role in ("admin", "scrum_master")

    repo = AiProjectStateRepository(db)

    if isinstance(body, dict):
        role_id = body.get("role_id")
        active = body.get("active", True)
        autonomy = body.get("autonomy")
    else:
        role_id = getattr(body, "role_id", None)
        active = getattr(body, "active", True)
        autonomy = getattr(body, "autonomy", None)

    if autonomy == "apply" and not can_apply:
        raise ForbiddenError("Solo Scrum Master, Owner o Admin pueden configurar autonomía 'apply'")

    role_update = [{"role_id": role_id, "enabled": active}]
    if autonomy:
        role_update[0]["autonomy"] = autonomy

    updated_state = await repo.update_roles(project_id, role_update, user_id=user_id)

    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_STATE_CHANGED",
        "state": updated_state,
    })

    active_roles = [r["role_id"] for r in updated_state.get("roles", []) if r.get("enabled")]
    return {"project_id": project_id, "active_ai_roles": active_roles}


@router.get(
    "/projects/{project_id}/roles",
    response_model=List[AiRoleStatus],
    summary="Get active AI roles and UI skins for a project",
)
async def get_roles(
    project_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns all available roles with their active status, skin, and triggers for the project."""
    repo = AiProjectStateRepository(db)
    state = await repo.get_or_create(project_id)
    roles_map = {r["role_id"]: r for r in state.get("roles", [])}

    result = []
    for role in list_roles():
        cfg = roles_map.get(role.id, {})
        is_active = cfg.get("enabled", True)
        result.append(
            AiRoleStatus(
                role_id=role.id,
                label=role.label,
                emoji=role.emoji,
                description=role.description,
                is_active=is_active,
                skin=role.skin,
                triggers=role.triggers,
            )
        )
    return result


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
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Creates a new task for an AI role to execute."""
    repo = AiTaskRepository(db)
    task_id = await repo.create(project_id, str(current_user["_id"]), body)
    if not task_id:
        raise ExternalServiceError("Error al crear la tarea en la base de datos.")
    return {"task_id": task_id, "status": "pending", "message": "Tarea creada exitosamente."}


@router.get(
    "/projects/{project_id}/tasks",
    summary="List all AI tasks for a project",
)
async def list_tasks(
    project_id: str,
    project: dict = Depends(require_project_member),
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
    "/projects/{project_id}/tasks/{task_id}",
    summary="Update, cancel or reassign an AI task",
)
async def update_task(
    project_id: str,
    task_id: str,
    body: AiTaskUpdateRequest,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Updates mutable fields (title, description, ai_role, status) of an existing task."""
    repo = AiTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError("Tarea no encontrada")
    if str(task.get("project_id", "")) != str(project_id):
        raise ForbiddenError("La tarea no pertenece a este proyecto")

    updates = body.model_dump(exclude_unset=True)
    await repo.update_task(task_id, updates)
    updated_doc = await repo.get_by_id(task_id)

    # Broadcast task update
    updated_serialized = {
        "id": str(updated_doc.get("_id", "")),
        "project_id": str(updated_doc.get("project_id", "")),
        "title": updated_doc.get("title", ""),
        "description": updated_doc.get("description", ""),
        "ai_role": updated_doc.get("ai_role", ""),
        "status": updated_doc.get("status", ""),
        "result": updated_doc.get("result"),
    }
    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_TASK_UPDATED",
        "task": updated_serialized,
    })

    return updated_serialized


@router.delete(
    "/projects/{project_id}/tasks/{task_id}",
    summary="Delete or cancel an AI task",
)
async def delete_task(
    project_id: str,
    task_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Deletes an AI task from the project."""
    repo = AiTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise NotFoundError("Tarea no encontrada")
    if str(task.get("project_id", "")) != str(project_id):
        raise ForbiddenError("La tarea no pertenece a este proyecto")

    await repo.delete_task(task_id)

    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_TASK_UPDATED",
        "task": {"id": task_id, "project_id": project_id, "status": "deleted"},
    })

    return {"success": True, "message": "Tarea eliminada exitosamente"}


@router.patch(
    "/projects/{project_id}/tasks/{task_id}/execute",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronously enqueues execution of a pending AI task",
)
async def execute_task(
    project_id: str,
    task_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Enqueues execution of a pending AI task in the background and immediately responds 202 Accepted."""
    try:
        return await service.execute_task_async(task_id, project_id, current_user)
    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"[AiChatRouter] execute_task error: {e}")
        raise ExternalServiceError("Error durante la ejecución de la tarea de IA")


# ── AI Findings Endpoints (P5 Bloque C) ─────────────────────────────────────────

@router.get(
    "/projects/{project_id}/findings",
    summary="List diagram quality findings with lifecycle tracking (P5 Bloque C)",
)
async def list_findings(
    project_id: str,
    diagram_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns detected linter findings for the project with their current lifecycle status."""
    from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
    repo = AiFindingsRepository(db)
    findings = await repo.list_findings(project_id, diagram_id=diagram_id, status=status)
    return {
        "success": True,
        "total": len(findings),
        "findings": [f.model_dump() for f in findings],
    }


@router.post(
    "/projects/{project_id}/findings/{finding_id}/acknowledge",
    summary="Acknowledge a quality finding",
)
async def acknowledge_finding(
    project_id: str,
    finding_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Marks a finding as acknowledged by the current user."""
    from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
    repo = AiFindingsRepository(db)
    user_id = str(current_user["_id"])
    success = await repo.acknowledge_finding(finding_id, user_id=user_id)
    if not success:
        raise NotFoundError("Hallazgo no encontrado o ya no está en estado 'open'")
    return {"success": True, "message": "Hallazgo reconocido correctamente"}


@router.post(
    "/projects/{project_id}/findings/{finding_id}/dismiss",
    summary="Dismiss a quality finding",
)
async def dismiss_finding(
    project_id: str,
    finding_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Marks a finding as dismissed by the current user."""
    from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
    repo = AiFindingsRepository(db)
    user_id = str(current_user["_id"])
    success = await repo.dismiss_finding(finding_id, user_id=user_id)
    if not success:
        raise NotFoundError("Hallazgo no encontrado o no activo")
    return {"success": True, "message": "Hallazgo descartado correctamente"}
