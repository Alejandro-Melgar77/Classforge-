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
    ProposalApplyRequest,
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
    latest: bool = False,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Returns the message history visible to the team (project announcements, published messages, and own personal messages)."""
    repo = AiMessageRepository(db)
    messages, total, next_cursor = await repo.get_history(
        project_id,
        user_id=str(current_user["_id"]),
        before=before,
        after=after,
        limit=limit,
        member=member,
        role=role,
        order='desc' if latest and not before and not after else 'asc',
    )
    if latest and not before and not after:
        messages.reverse()
    return {
        "project_id": project_id,
        "messages": messages,
        "total": total,
        "next_cursor": next_cursor,
    }


@router.post(
    "/projects/{project_id}/messages/{message_id}/publish",
    summary="Publish a personal chat message or proposal to the project team",
)
async def publish_message_to_team(
    project_id: str,
    message_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Allows an authorized user to publish a message from their personal thread to the team."""
    repo = AiMessageRepository(db)
    user_id = str(current_user["_id"])
    published_msg = await repo.publish_message(message_id, user_id=user_id, project_id=project_id)
    if not published_msg:
        raise NotFoundError("Mensaje no encontrado o sin permisos para publicarlo")

    # Broadcast to all members in the project room
    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_MESSAGE_UPDATED",
        "message": published_msg,
    })
    return {"success": True, "message": published_msg}


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
        project_id=project_id,
    )
    if not updated_msg:
        raise NotFoundError("Mensaje no encontrado para actualizar propuesta")

    # Broadcast update via project WS
    await manager.broadcast(f"project:{project_id}", {
        "type": "AI_MESSAGE_UPDATED",
        "message": updated_msg,
    })
    return {"message": updated_msg, "proposal_id": proposal_id, "status": body.status}


@router.post(
    "/projects/{project_id}/messages/{message_id}/proposals/{proposal_id}/apply",
    summary="Applies an approved AI proposal to modify the diagram using Phase 2 engine",
)
async def apply_proposal_endpoint(
    project_id: str,
    message_id: str,
    proposal_id: str,
    body: Optional[ProposalApplyRequest] = None,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Executes real diagram modification for an AI proposal with base version verification and audit."""
    req_data = body or ProposalApplyRequest()
    return await service.apply_proposal(
        project_id=project_id,
        message_id=message_id,
        proposal_id=proposal_id,
        user_id=str(current_user["_id"]),
        diagram_id=req_data.diagram_id,
        base_version=req_data.base_version,
    )


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

    # Only the creator or an admin may delete a task; any project member could
    # previously delete someone else's work.
    assigned_by = str(task.get("assigned_by") or "")
    is_creator = assigned_by == str(current_user["_id"])
    if not is_creator and current_user.get("role") != "admin":
        raise ForbiddenError("Solo el creador de la tarea o un administrador puede eliminarla")

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


@router.post(
    "/projects/{project_id}/tasks/{task_id}/cancel",
    summary="Cancels a pending or in-progress AI task",
)
async def cancel_task_endpoint(
    project_id: str,
    task_id: str,
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    service: AiChatService = Depends(_get_service),
):
    """Cancels an active or pending AI task and cancels its associated worker job."""
    return await service.cancel_task(task_id, project_id, current_user)


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


# ── Autonomous Diagram Analysis ───────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/analyze-diagram",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Triggers autonomous diagram analysis and creates tasks for active roles",
)
async def analyze_diagram_endpoint(
    project_id: str,
    diagram_id: Optional[str] = Query(None),
    project: dict = Depends(require_project_member),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    1. Finds the diagram (current or most recent).
    2. Runs linter on diagram to detect real inconsistencies/findings.
    3. Creates AiTask records for detected issues and active specialist roles.
    4. Triggers background review jobs.
    5. Broadcasts AI_ANALYSIS_STARTED to WS room.
    Returns list of created task IDs.
    """
    from app.ai_team.application.triggers import get_triggers
    from app.ai_team.domain.roles import get_role, ROLES_REGISTRY
    from app.ai_team.domain.diagram_model import from_graph_data
    from app.ai_team.domain.lint import lint_diagram

    user_id = str(current_user["_id"])
    triggers = get_triggers(db)

    # 1. Ensure participative mode is enabled in project state
    state_repo = AiProjectStateRepository(db)
    state = await state_repo.get_or_create(project_id)
    if not state.get("participative", {}).get("enabled", False):
        try:
            state = await state_repo.set_participative(project_id, True, user_id)
        except Exception as e:
            logger.warning(f"[AnalyzeDiagram] Could not set participative mode: {e}")

    # Resolve any stale in_progress tasks so they appear completed and don't block
    try:
        pid_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        await db["ai_tasks"].update_many(
            {"project_id": {"$in": [pid_obj, str(project_id)]}, "status": "in_progress"},
            {"$set": {"status": "completed", "result": "Tarea completada en ciclo previo de análisis."}}
        )
    except Exception as e:
        logger.warning(f"[AnalyzeDiagram] Stale tasks cleanup: {e}")

    # 2. Find the target diagram
    diagram_doc = None
    try:
        pid_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        if diagram_id:
            did_obj = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            diagram_doc = await db["diagrams"].find_one({
                "_id": did_obj,
                "project_id": {"$in": [pid_obj, str(project_id)]},
                "is_deleted": {"$ne": True}
            })

        if not diagram_doc:
            cursor = db["diagrams"].find(
                {"project_id": pid_obj, "is_deleted": {"$ne": True}}
            ).sort("updated_at", -1).limit(1)
            diagrams = await cursor.to_list(length=1)
            if diagrams:
                diagram_doc = diagrams[0]
                diagram_id = str(diagram_doc["_id"])
    except Exception as e:
        logger.warning(f"[AnalyzeDiagram] Could not fetch diagram: {e}")

    task_repo = AiTaskRepository(db)
    created_tasks: List[str] = []

    # 3. If diagram found, lint it to detect real domain tasks
    findings = []
    if diagram_doc and diagram_doc.get("graph_data"):
        try:
            canonical_diagram = from_graph_data(diagram_doc["graph_data"])
            findings = lint_diagram(canonical_diagram)
        except Exception as e:
            logger.warning(f"[AnalyzeDiagram] Error during diagram lint: {e}")

    # Create tasks from findings if any
    for finding in findings[:4]:
        try:
            target_role = "qa" if finding.severity in ("warn", "critical") else "architect"
            task_data = AiTaskCreate(
                ai_role=target_role,
                title=f"Resolver: {finding.title}",
                description=f"{finding.description}. Sugerencia: {finding.suggestion or 'Corregir inconsistencia en el lienzo.'}",
                diagram_id=diagram_id,
            )
            task_id = await task_repo.create(project_id, user_id, task_data)
            if task_id:
                created_tasks.append(str(task_id))
        except Exception as e:
            logger.warning(f"[AnalyzeDiagram] Could not create finding task: {e}")

    # 4. Also create domain tasks for active roles that don't have pending tasks
    for role_cfg in state.get("roles", []):
        role_id = role_cfg.get("role_id")
        if not role_cfg.get("enabled", True):
            continue
        autonomy = role_cfg.get("autonomy", "suggest")
        if autonomy == "off":
            continue
        if role_id not in ROLES_REGISTRY:
            continue
        try:
            role_def = get_role(role_id)
            # Custom title per role
            role_action_map = {
                "architect": ("Revisión de arquitectura y modularidad", "Evaluar cohesión de clases y dependencias circulares en el lienzo."),
                "qa": ("Auditoría de consistencia y cardinalidades", "Verificar multiplicidades, nomenclatura y relaciones huérfanas."),
                "tech_lead": ("Factibilidad para codegen", "Verificar que las clases tengan visibilidad, tipos de retorno y convenciones limpias."),
                "dba": ("Diseño de persistencia relacional", "Verificar claves foráneas, normalización y tipos de atributos."),
                "security": ("Auditoría de control de acceso", "Verificar encapsulamiento y superficie de exposición de métodos."),
                "analyst": ("Verificación de requisitos de negocio", "Validar trazabilidad entre casos de uso y modelos de dominio."),
            }
            title, desc = role_action_map.get(
                role_id,
                (f"Revisión autónoma: {role_def.label}", f"Analizar diagrama como {role_def.label}.")
            )
            task_data = AiTaskCreate(
                ai_role=role_id,
                title=title,
                description=desc,
                diagram_id=diagram_id,
            )
            task_id = await task_repo.create(project_id, user_id, task_data)
            if task_id:
                created_tasks.append(str(task_id))
        except Exception as e:
            logger.warning(f"[AnalyzeDiagram] Could not create task for {role_id}: {e}")

    # 5. Trigger background review jobs (non-blocking)
    if diagram_id:
        try:
            await triggers._evaluate_diagram_after_debounce(project_id, diagram_id)
        except Exception as e:
            logger.warning(f"[AnalyzeDiagram] evaluate_diagram trigger failed: {e}")

    # 6. Broadcast task list refresh signal
    try:
        await manager.broadcast(f"project:{project_id}", {
            "type": "AI_ANALYSIS_STARTED",
            "task_ids": created_tasks,
            "diagram_id": diagram_id,
        })
    except Exception as e:
        logger.warning(f"[AnalyzeDiagram] Broadcast failed: {e}")

    return {
        "success": True,
        "task_ids": created_tasks,
        "diagram_id": diagram_id,
        "tasks_created": len(created_tasks),
    }
