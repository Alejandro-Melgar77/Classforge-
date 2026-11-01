"""
AiChatService: Scalable team AI chat and autonomous task execution.
Orchestrates:
- Personal thread (Chat) vs shared project history (Historial)
- 4-step AI role routing (Explicit > @Mention > Participative > None)
- Asynchronous background LLM generation with real-time WebSocket events
- Structured proposals, retry flow, and shared project memory (digest)
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.llm import LlmMessage, LlmRequest, get_provider
from app.ai_team.domain.roles import get_role, RoleDefinition, ROLES_REGISTRY
from app.ai_team.application.prompt_builder import AiTeamResponse, ProposalItem
from app.modules.collaboration.connection_manager import manager
from app.modules.ai_chat.domain.models import AiMessage
from app.modules.ai_chat.domain.router_logic import route_ai_roles
from app.modules.ai_chat.application.project_digest import ProjectDigestService
from app.modules.ai_chat.application.chat_context import assemble_chat_request
from app.modules.ai_chat.infrastructure.repositories import (
    AiMessageRepository,
    AiProjectStateRepository,
    AiTaskRepository,
)
from app.modules.ai_chat.schemas import (
    AiRoleChatRequest,
    AiSendMessageResponse,
    AiPendingItem,
    AiTask,
    AiTaskCreate,
)

logger = logging.getLogger(__name__)


class AiChatService:
    """Core service for AI Chat operations in ClassForge projects."""

    def __init__(self, db):
        self.db = db
        self.msg_repo = AiMessageRepository(db)
        self.state_repo = AiProjectStateRepository(db)
        self.task_repo = AiTaskRepository(db)
        self.digest_service = ProjectDigestService(db)
        from app.ai_team.application.triggers import TriggersManager
        self.triggers = TriggersManager(db)

    async def send_message_with_role(
        self,
        request: AiRoleChatRequest,
        user_id: str,
        username: str,
        user_role: str = "dev",
    ) -> AiSendMessageResponse:
        """Processes and saves a user message, resolves AI role responders,
        spawns background LLM tasks, and returns immediate response with ai_pending.
        """
        project_id = str(request.project_id)
        content_text = (request.content or request.message or "").strip()

        # 1. Idempotency Check with client_id
        if request.client_id:
            existing = await self.msg_repo.find_by_client_id(project_id, request.client_id)
            if existing:
                logger.info(f"[AiChatService] Idempotent hit for client_id {request.client_id}")
                pending_ai = await self.msg_repo.find_pending_ai_for_user_message(existing["id"])
                pending_items = [
                    AiPendingItem(role=p["ai_role"], message_id=p["id"])
                    for p in pending_ai
                    if p.get("ai_role")
                ]
                return AiSendMessageResponse(
                    message=existing,
                    ai_pending=pending_items,
                    ai_message=existing,
                )

        # 2. Gather project and team context
        project_doc = await self._get_project(project_id)
        team_doc = await self._get_team(project_doc)
        team_members = await self._get_members(team_doc)
        project_state = await self.state_repo.get_or_create(project_id)

        # 3. Save User Message (personal thread)
        user_msg = AiMessage(
            project_id=project_id,
            thread="personal",
            owner_id=user_id,
            author_type="user",
            author_id=user_id,
            author_name=username,
            author_role_label=user_role,
            content=content_text,
            client_id=request.client_id,
            reply_to=request.reply_to,
            status="ok",
        )
        saved_user_msg = await self.msg_repo.create_message(user_msg)

        # Broadcast user message creation to project room
        await manager.broadcast(f"project:{project_id}", {
            "type": "AI_MESSAGE_CREATED",
            "message": saved_user_msg,
        })

        # 4. Determine AI responders via Domain Router Logic
        from app.modules.ai_chat.domain.models import AiProjectState
        state_model = AiProjectState.model_validate(project_state) if project_state else None
        selected_roles, trigger_reason, all_mentions = route_ai_roles(
            explicit_role=request.ai_role,
            content=content_text,
            project_state=state_model,
            team_members=team_members,
        )

        # 5. Create pending AI messages and schedule background generation
        ai_pending_list: List[AiPendingItem] = []

        for role_id in selected_roles:
            role_def: RoleDefinition = get_role(role_id)
            ai_pending_msg = AiMessage(
                project_id=project_id,
                thread="personal",
                owner_id=user_id,
                author_type="ai",
                author_id=None,
                author_name=f"{role_def.emoji} {role_def.label}",
                author_role_label=f"{role_id}_ai",
                ai_role=role_id,
                content="",
                status="pending",
                trigger=trigger_reason,
                reply_to=saved_user_msg["id"],
            )
            saved_ai_msg = await self.msg_repo.create_message(ai_pending_msg)
            ai_pending_list.append(AiPendingItem(role=role_id, message_id=saved_ai_msg["id"]))

            # Broadcast pending AI message creation
            await manager.broadcast(f"project:{project_id}", {
                "type": "AI_MESSAGE_CREATED",
                "message": saved_ai_msg,
            })

            # 1. Enqueue durable job in ai_jobs (P5 Bloque A)
            await self.triggers.on_user_message(
                project_id=project_id,
                user_id=user_id,
                ai_msg_id=saved_ai_msg["id"],
                role_id=role_id,
                trigger_text=content_text,
                diagram_id=request.diagram_id,
                api_key=request.api_key,
                model=request.model,
            )

            # 2. Fire and forget in-process processing
            asyncio.create_task(
                self._process_ai_response(
                    ai_msg_id=saved_ai_msg["id"],
                    project_id=project_id,
                    role_def=role_def,
                    user_id=user_id,
                    trigger_text=content_text,
                    diagram_id=request.diagram_id,
                    api_key=request.api_key,
                    model=request.model,
                )
            )

        return AiSendMessageResponse(
            message=saved_user_msg,
            ai_pending=ai_pending_list,
            ai_message=saved_user_msg,
        )

    async def _process_ai_response(
        self,
        ai_msg_id: str,
        project_id: str,
        role_def: RoleDefinition,
        user_id: str,
        trigger_text: str,
        diagram_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Asynchronously calls the LLM provider, updates ai_messages, and broadcasts WebSocket events."""
        room_key = f"project:{project_id}"
        role_id = role_def.id

        try:
            # 1. Notify that AI started typing
            await manager.broadcast(room_key, {
                "type": "AI_TYPING",
                "role": role_id,
                "state": "start",
            })

            # 2. Gather context
            project_doc = await self._get_project(project_id)
            team_doc = await self._get_team(project_doc)
            team_members = await self._get_members(team_doc)
            diagram_doc = await self._get_diagram(diagram_id, project_id)
            project_state = await self.state_repo.get_or_create(project_id)
            digest_text = project_state.get("digest", {}).get("text", "")

            user_turns = await self.msg_repo.get_recent_user_turns(project_id, user_id, limit=10)
            other_activity = await self.msg_repo.get_recent_team_activity(project_id, user_id, limit=10)

            # 3. Assemble priority-trimmed request or enforce local_only privacy
            if project_state.get("local_only"):
                logger.info(f"[AiChatService] Proyecto en modo local_only. Rol '{role_id}' deshabilitado para proteger la privacidad.")
                reply_content = (
                    f"🔒 **Modo Privado (Local Only) Activo**\n\n"
                    f"El rol **{role_def.name} ({role_def.label_es})** requiere capacidades de razonamiento abierto "
                    f"de Gemini 3.8 Flash, pero este proyecto tiene forzado el modo estrictamente local para proteger datos confidenciales.\n\n"
                    f"Las órdenes de modelado directo pueden ejecutarse desde la **Consola de Comandos UML**, servida 100% por tu modelo local Ollama."
                )
                structured_resp = AiTeamResponse(
                    reply_markdown=reply_content,
                    proposals=[],
                    questions=[],
                    needs_context=False,
                )
                raw_text = reply_content
                model_name = "local-privacy-guard"
            else:
                llm_req = assemble_chat_request(
                    role=role_def,
                    project=project_doc,
                    diagram=diagram_doc.get("graph_data") if diagram_doc else None,
                    user_id=user_id,
                    trigger=trigger_text,
                    team_members=team_members,
                    digest_text=digest_text,
                    user_turns=user_turns,
                    other_activity=other_activity,
                    api_key=api_key,
                    model=model,
                )

                # 4. Execute LLM call
                structured_resp, raw_text, model_name = await self._execute_llm(llm_req)

            # 5. Extract results
            reply_content = raw_text
            proposals: List[ProposalItem] = []
            questions: List[str] = []
            needs_context = False

            if structured_resp:
                reply_content = structured_resp.reply_markdown
                proposals = structured_resp.proposals
                questions = structured_resp.questions
                needs_context = structured_resp.needs_context
            else:
                has_changes, changes_json = self._detect_diagram_changes(reply_content)
                if has_changes and changes_json:
                    from app.modules.ai.schemas import UMLCommandResponse
                    cmd_obj = None
                    try:
                        cmd_obj = UMLCommandResponse.model_validate(changes_json)
                    except Exception:
                        pass
                    proposals.append(
                        ProposalItem(
                            id="prop-fallback-1",
                            kind="uml_command",
                            title="Cambios propuestos al diagrama",
                            rationale="Generado automáticamente por el asistente.",
                            command=cmd_obj,
                        )
                    )

            # 6. Update message status to 'ok'
            await self.msg_repo.update_ai_response(
                message_id=ai_msg_id,
                content=reply_content,
                proposals=proposals,
                status="ok",
                model=model_name,
                questions=questions,
                needs_context=needs_context,
                diagram_snapshot=diagram_doc.get("graph_data") if diagram_doc else None,
            )

            updated_msg = await self.msg_repo.find_by_id(ai_msg_id)
            if updated_msg:
                await manager.broadcast(room_key, {
                    "type": "AI_MESSAGE_UPDATED",
                    "message": updated_msg,
                })

            # 7. Check if project digest should be updated
            try:
                await self.digest_service.summarize_digest(project_id, force=False)
            except Exception as dig_err:
                logger.warning(f"[AiChatService] Non-blocking digest update error: {dig_err}")

        except Exception as e:
            logger.error(f"[AiChatService] Background AI processing failed for {ai_msg_id}: {e}")
            await self.msg_repo.update_ai_response(
                message_id=ai_msg_id,
                content="Ocurrió un error al procesar la respuesta del asistente de IA. Puedes reintentar con el botón 'Reintentar'.",
                status="error",
                error_code="AI_PROCESSING_ERROR",
            )
            updated_msg = await self.msg_repo.find_by_id(ai_msg_id)
            if updated_msg:
                await manager.broadcast(room_key, {
                    "type": "AI_MESSAGE_UPDATED",
                    "message": updated_msg,
                })
        finally:
            # 8. Notify that AI stopped typing
            await manager.broadcast(room_key, {
                "type": "AI_TYPING",
                "role": role_id,
                "state": "stop",
            })

    async def retry_ai_message(self, message_id: str, project_id: str, current_user: dict) -> Dict[str, Any]:
        """Retries generating an AI message that previously failed with status 'error'."""
        msg = await self.msg_repo.find_by_id(message_id)
        if not msg:
            raise NotFoundError(f"Mensaje {message_id} no encontrado")
        if str(msg.get("project_id")) != str(project_id):
            raise ForbiddenError("El mensaje no pertenece a este proyecto")
        if msg.get("status") != "error":
            raise ValidationError("Solo mensajes con estado 'error' pueden ser reintentados")

        role_id = msg.get("ai_role", "architect")
        role_def = get_role(role_id)
        user_id = str(current_user["_id"])

        # Reset message status to 'pending'
        await self.msg_repo.update_ai_response(
            message_id=message_id,
            content="",
            status="pending",
            error_code=None,
        )

        updated_msg = await self.msg_repo.find_by_id(message_id)
        await manager.broadcast(f"project:{project_id}", {
            "type": "AI_MESSAGE_UPDATED",
            "message": updated_msg,
        })

        # Fetch original user trigger message
        reply_to_id = msg.get("reply_to")
        trigger_text = "Por favor, continúa con la evaluación del proyecto."
        if reply_to_id:
            parent_msg = await self.msg_repo.find_by_id(reply_to_id)
            if parent_msg:
                trigger_text = parent_msg.get("content", trigger_text)

        # Trigger background processing
        asyncio.create_task(
            self._process_ai_response(
                ai_msg_id=message_id,
                project_id=project_id,
                role_def=role_def,
                user_id=user_id,
                trigger_text=trigger_text,
            )
        )

        return {"message_id": message_id, "status": "pending"}

    async def execute_task_async(self, task_id: str, project_id: str, current_user: dict) -> Dict[str, Any]:
        """Enqueues autonomous execution of a pending AI task without blocking the HTTP request."""
        task_doc = await self.task_repo.get_by_id(task_id)
        if not task_doc:
            raise NotFoundError(f"Tarea {task_id} no encontrada")
        if str(task_doc.get("project_id", "")) != str(project_id):
            raise ForbiddenError("La tarea no pertenece a este proyecto")

        # Mark in_progress
        await self.task_repo.update_status(task_id, "in_progress")
        updated_doc = await self.task_repo.get_by_id(task_id)

        # Broadcast AI_TASK_UPDATED
        serialized_task = self._serialize_task(updated_doc)
        await manager.broadcast(f"project:{project_id}", {
            "type": "AI_TASK_UPDATED",
            "task": serialized_task,
        })

        # Enqueue durable run_task job in ai_jobs (P5 Bloque A)
        role_id = task_doc.get("ai_role", "architect")
        user_id = str(current_user.get("_id", ""))
        await self.triggers.on_task_assigned(
            project_id=project_id,
            task_id=task_id,
            role_id=role_id,
            assigned_by=user_id,
            origin="human",
        )

        # Launch in-process execution
        asyncio.create_task(self._run_task_background(task_id, project_id))

        return {
            "task_id": task_id,
            "status": "in_progress",
            "message": "Tarea encolada para ejecución en segundo plano.",
        }

    async def _run_task_background(self, task_id: str, project_id: str) -> None:
        """Executes task with LLM in background, writes result, posts project message, and broadcasts WS."""
        task_doc = await self.task_repo.get_by_id(task_id)
        if not task_doc:
            return

        role_id = task_doc.get("ai_role", "architect")
        role_def = get_role(role_id)
        room_key = f"project:{project_id}"

        try:
            project_doc = await self._get_project(project_id)
            team_doc = await self._get_team(project_doc)
            team_members = await self._get_members(team_doc)
            diag_id = str(task_doc.get("diagram_id", "")) or None
            diagram_doc = await self._get_diagram(diag_id, project_id)

            task_prompt = (
                f"TAREA ASIGNADA: {task_doc['title']}\n\n"
                f"DESCRIPCIÓN: {task_doc['description']}\n\n"
                "Completa esta tarea de forma autónoma. Presenta tu análisis fundamentado "
                "y propuestas de comando UML si requiere cambios en el modelo."
            )

            from app.ai_team.application.prompt_builder import PromptBuilder
            llm_req = PromptBuilder.build(
                role=role_def,
                project=project_doc,
                diagram=diagram_doc.get("graph_data") if diagram_doc else None,
                trigger=task_prompt,
                team_members=team_members,
                purpose="task",
            )

            structured_resp, raw_text, _ = await self._execute_llm(llm_req)
            result_text = structured_resp.reply_markdown if structured_resp else raw_text
            needs_context = structured_resp.needs_context if structured_resp else False
            final_status = "needs_input" if needs_context else "completed"

            # Publish result to project thread (visible to all)
            ai_msg = AiMessage(
                project_id=project_id,
                thread="project",
                owner_id=None,
                author_type="ai",
                author_name=f"{role_def.emoji} {role_def.label}",
                author_role_label=f"{role_id}_ai",
                ai_role=role_id,
                content=f"✅ **Tarea completada:** {task_doc['title']}\n\n{result_text}" if not needs_context else f"⚠️ **Tarea requiere información:** {task_doc['title']}\n\n{result_text}",
                proposals=structured_resp.proposals if structured_resp else [],
                trigger="task",
                status="ok",
            )
            saved_ai_msg = await self.msg_repo.create_message(ai_msg)

            await self.task_repo.update_status(task_id, final_status, result_text, result_message_id=saved_ai_msg["id"])
            completed_task = await self.task_repo.get_by_id(task_id)

            await manager.broadcast(room_key, {
                "type": "AI_TASK_UPDATED",
                "task": self._serialize_task(completed_task),
            })

            assigned_by = task_doc.get("assigned_by")
            if assigned_by and ObjectId.is_valid(str(assigned_by)):
                try:
                    from app.modules.notifications.service import NotificationService
                    notif_svc = NotificationService(self.db)
                    await notif_svc.create_notification(
                        user_id=str(assigned_by),
                        title=f"Tarea {final_status}: {task_doc['title']}",
                        message=f"El rol {role_def.label} ha procesado la tarea asignada.",
                        type="ai_task",
                    )
                except Exception as n_err:
                    logger.debug(f"[AiChatService] Notification error: {n_err}")



        except Exception as e:
            logger.error(f"[AiChatService] Background task {task_id} failed: {e}")
            await self.task_repo.update_status(task_id, "failed", "Error durante la ejecución de la tarea")
            failed_task = await self.task_repo.get_by_id(task_id)
            await manager.broadcast(room_key, {
                "type": "AI_TASK_UPDATED",
                "task": self._serialize_task(failed_task),
            })

    async def _execute_llm(self, req: LlmRequest) -> Tuple[Optional[AiTeamResponse], str, str]:
        """Calls LLM provider and returns (structured_response, raw_text, model_name)."""
        provider = get_provider(purpose=req.purpose)
        try:
            res = await provider.generate(req)
            model_name = res.model or "unknown"
            if res.raw_json and isinstance(res.raw_json, dict):
                try:
                    structured = AiTeamResponse.model_validate(res.raw_json)
                    return structured, res.text, model_name
                except Exception as val_err:
                    logger.warning(f"[AiChatService] Validation error on structured response: {val_err}")

            if res.text and res.text.strip().startswith("{"):
                try:
                    parsed = json.loads(res.text)
                    structured = AiTeamResponse.model_validate(parsed)
                    return structured, structured.reply_markdown, model_name
                except Exception:
                    pass

            return None, res.text, model_name
        except Exception as e:
            logger.warning(f"[AiChatService] Exception calling LLM provider: {e}")
            return None, "No se pudo conectar con el asistente de IA en este momento.", "error"

    async def _get_project(self, project_id: str) -> dict:
        try:
            pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            doc = await self.db["projects"].find_one({"_id": pid})
            return doc or {}
        except Exception:
            return {}

    async def _get_team(self, project: dict) -> Optional[dict]:
        team_id = project.get("team_id")
        if not team_id:
            return None
        try:
            tid = ObjectId(team_id) if ObjectId.is_valid(team_id) else team_id
            return await self.db["teams"].find_one({"_id": tid})
        except Exception:
            return None

    async def _get_members(self, team: Optional[dict]) -> List[dict]:
        if not team:
            return []
        member_ids = team.get("member_ids", [])
        if not member_ids:
            return []
        try:
            oids = [ObjectId(m) if ObjectId.is_valid(m) else m for m in member_ids]
            cursor = self.db["users"].find({"_id": {"$in": oids}}, {"name": 1, "email": 1, "role": 1})
            return await cursor.to_list(length=50)
        except Exception:
            return []

    async def _get_diagram(self, diagram_id: Optional[str], project_id: str) -> Optional[dict]:
        if diagram_id:
            try:
                did = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
                doc = await self.db["diagrams"].find_one({"_id": did})
                if doc:
                    return doc
            except Exception:
                pass
        try:
            pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            cursor = self.db["diagrams"].find(
                {"project_id": pid, "is_deleted": {"$ne": True}}
            ).sort("updated_at", -1).limit(1)
            docs = await cursor.to_list(length=1)
            return docs[0] if docs else None
        except Exception:
            return None

    def _detect_diagram_changes(self, content: str) -> Tuple[bool, Optional[dict]]:
        if not content:
            return False, None
        indicators = ['"action"', '"classes"', '"relations"', "generate_system", "add_class"]
        if not any(ind in content for ind in indicators):
            return False, None
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                if "classes" in parsed or "action" in parsed:
                    return True, parsed
        except Exception:
            pass
        return False, None

    def _serialize_task(self, doc: dict) -> dict:
        if not doc:
            return {}
        res = dict(doc)
        res["id"] = str(res.pop("_id", ""))
        res["project_id"] = str(res.get("project_id", ""))
        if res.get("diagram_id"):
            res["diagram_id"] = str(res["diagram_id"])
        if res.get("assigned_by"):
            res["assigned_by"] = str(res["assigned_by"])
        return res
