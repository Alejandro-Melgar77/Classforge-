"""
AiWorker: Durable background worker for ClassForge autonomous AI jobs (P5 Bloque A & D).

Executes:
- answer_message: Asynchronous response to user messages
- run_task: Autonomous execution of assigned tasks
- review_diagram: Proactive diagram analysis by specialized roles
- summarize_digest: Periodic shared project memory compilation

Ensures atomic acquisition via MongoDB leases, handles backoff on failure,
runs periodic lease reaper and stale job skipper.
Safe across multiple server instances.
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
from bson import ObjectId

from app.core.config import settings
from app.llm import LlmMessage, LlmRequest, get_provider
from app.ai_team.domain.jobs import AiJob
from app.ai_team.domain.roles import get_role, RoleDefinition
from app.ai_team.domain.diagram_model import from_graph_data
from app.ai_team.application.prompt_builder import AiTeamResponse, ProposalItem, PromptBuilder
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.application.triggers import enforce_publication_limits
from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
from app.modules.collaboration.connection_manager import manager
from app.modules.ai_chat.domain.models import AiMessage
from app.modules.ai_chat.infrastructure.repositories import (
    AiMessageRepository,
    AiProjectStateRepository,
    AiTaskRepository,
)
from app.modules.ai_chat.application.project_digest import ProjectDigestService
from app.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)


class AiWorker:
    """Manages background job polling, execution, retries, and lifecycle."""

    def __init__(
        self,
        db,
        clock: Optional[Callable[[], datetime]] = None,
        concurrency: Optional[int] = None,
        lease_seconds: Optional[int] = None,
        poll_interval: Optional[float] = None,
    ):
        self.db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.concurrency = concurrency or settings.AI_WORKER_CONCURRENCY
        self.lease_seconds = lease_seconds or settings.AI_WORKER_LEASE_SECONDS
        self.poll_interval = poll_interval or settings.AI_WORKER_POLL_INTERVAL_SECONDS
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"

        self.job_repo = AiJobRepository(db, clock=self._clock)
        self.findings_repo = AiFindingsRepository(db, clock=self._clock)
        self.state_repo = AiProjectStateRepository(db)
        self.msg_repo = AiMessageRepository(db)
        self.task_repo = AiTaskRepository(db)
        self.digest_service = ProjectDigestService(db)
        self.diagram_editor = ServerDiagramEditor(db)
        self.notif_service = NotificationService(db)

        self._stop_event = asyncio.Event()
        self._main_task: Optional[asyncio.Task] = None
        self._active_tasks: set[asyncio.Task] = set()

    def _now(self) -> datetime:
        return self._clock()

    def start(self) -> None:
        """Starts the worker background task."""
        if self._main_task and not self._main_task.done():
            return
        self._stop_event.clear()
        self._main_task = asyncio.create_task(self._worker_loop())
        logger.info(f"[AiWorker] Started worker instance {self.worker_id}")

    async def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stops the worker."""
        self._stop_event.set()
        if self._main_task:
            self._main_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._main_task), timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        # Wait for any active jobs to finish or cancel
        if self._active_tasks:
            for t in list(self._active_tasks):
                if not t.done():
                    t.cancel()
        logger.info(f"[AiWorker] Stopped worker instance {self.worker_id}")

    async def _worker_loop(self) -> None:
        """Main polling loop with concurrency limiter and periodic housekeeping."""
        sem = asyncio.Semaphore(self.concurrency)
        last_maintenance = self._now()

        while not self._stop_event.is_set():
            try:
                # Periodic reaper and stale-job skipper (every 30s)
                now = self._now()
                if (now - last_maintenance).total_seconds() >= 30:
                    last_maintenance = now
                    try:
                        await self.job_repo.reap_expired_leases()
                        await self.job_repo.skip_stale_jobs(max_age_hours=24)
                    except Exception as m_err:
                        logger.error(f"[AiWorker] Maintenance error: {m_err}")

                # Acquire next job
                job = await self.job_repo.acquire_next(self.worker_id, lease_seconds=self.lease_seconds)
                if not job:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Run job under concurrency semaphore
                await sem.acquire()
                task = asyncio.create_task(self._run_job_wrapper(job, sem))
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AiWorker] Polling loop error: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _run_job_wrapper(self, job: AiJob, sem: asyncio.Semaphore) -> None:
        try:
            await self._execute_job(job)
        finally:
            sem.release()

    async def process_next_job(self) -> Optional[AiJob]:
        """Manually acquires and executes a single job (ideal for unit testing)."""
        job = await self.job_repo.acquire_next(self.worker_id, lease_seconds=self.lease_seconds)
        if not job:
            return None
        await self._execute_job(job)
        return await self.job_repo.get_by_id(job.id)

    async def _execute_job(self, job: AiJob) -> None:
        """Routes and executes a specific AiJob."""
        logger.info(f"[AiWorker] Executing job {job.id} (kind={job.kind}, role={job.role_id})")
        try:
            if job.kind == "answer_message":
                await self._handle_answer_message(job)
            elif job.kind == "run_task":
                await self._handle_run_task(job)
            elif job.kind == "review_diagram":
                await self._handle_review_diagram(job)
            elif job.kind == "summarize_digest":
                await self._handle_summarize_digest(job)
            else:
                logger.warning(f"[AiWorker] Unknown job kind: {job.kind}")
                await self.job_repo.complete(job.id)

        except Exception as exc:
            logger.error(f"[AiWorker] Job {job.id} failed: {exc}", exc_info=True)
            await self.job_repo.fail(job.id, error=str(exc), max_attempts=job.max_attempts)

    # ── Job Handlers ───────────────────────────────────────────────────────────

    async def _handle_answer_message(self, job: AiJob) -> None:
        """Executes answer_message job by calling AiChatService."""
        from app.modules.ai_chat.service import AiChatService
        chat_service = AiChatService(self.db)

        payload = job.payload
        ai_msg_id = payload.get("ai_msg_id")
        role_id = job.role_id or "architect"
        role_def = get_role(role_id)

        await chat_service._process_ai_response(
            ai_msg_id=ai_msg_id,
            project_id=job.project_id,
            role_def=role_def,
            user_id=payload.get("user_id", ""),
            trigger_text=payload.get("trigger_text", ""),
            diagram_id=payload.get("diagram_id"),
            api_key=payload.get("api_key"),
            model=payload.get("model"),
        )
        await self.job_repo.complete(job.id, result_ref={"message_id": ai_msg_id})

    async def _handle_run_task(self, job: AiJob) -> None:
        """Executes an AI task autonomously (Bloque F)."""
        task_id = job.payload.get("task_id")
        project_id = job.project_id
        room_key = f"project:{project_id}"

        task_doc = await self.task_repo.get_by_id(task_id)
        if not task_doc:
            await self.job_repo.complete(job.id)
            return

        role_id = task_doc.get("ai_role", job.role_id or "tech_lead")
        role_def = get_role(role_id)

        # 1. Update task to in_progress
        await self.task_repo.update_task(task_id, {
            "status": "in_progress",
            "attempts": task_doc.get("attempts", 0) + 1,
        })
        in_progress_task = await self.task_repo.get_by_id(task_id)
        await manager.broadcast(room_key, {
            "type": "AI_TASK_UPDATED",
            "task": self._serialize_task(in_progress_task),
        })

        # 2. Gather context
        project_doc = await self.db["projects"].find_one({"_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id}) or {}
        diagram_doc = None
        if task_doc.get("diagram_id"):
            did = ObjectId(task_doc["diagram_id"]) if ObjectId.is_valid(task_doc["diagram_id"]) else task_doc["diagram_id"]
            diagram_doc = await self.db["diagrams"].find_one({"_id": did})

        task_prompt = (
            f"TAREA ASIGNADA: {task_doc['title']}\n\n"
            f"DESCRIPCIÓN: {task_doc['description']}\n\n"
            "Completa esta tarea con tu criterio profesional de IA. Proporciona soluciones técnicas "
            "claras, criterios de diseño y propuestas de cambio UML si aplica."
        )

        llm_req = PromptBuilder.build(
            role=role_def,
            project=project_doc,
            diagram=diagram_doc.get("graph_data") if diagram_doc else None,
            trigger=task_prompt,
            purpose="task",
        )

        provider = get_provider(purpose="task")
        res = await provider.generate(llm_req)

        structured_resp: Optional[AiTeamResponse] = None
        raw_text = res.text
        if res.raw_json and isinstance(res.raw_json, dict):
            try:
                structured_resp = AiTeamResponse.model_validate(res.raw_json)
            except Exception:
                pass

        if not structured_resp and raw_text and raw_text.strip().startswith("{"):
            try:
                structured_resp = AiTeamResponse.model_validate(json.loads(raw_text))
            except Exception:
                pass

        reply_content = structured_resp.reply_markdown if structured_resp else raw_text
        proposals = structured_resp.proposals if structured_resp else []
        needs_context = structured_resp.needs_context if structured_resp else False

        # Enforce publication limits
        reply_content, proposals = enforce_publication_limits(
            reply_content, proposals, max_words=settings.AI_MAX_WORDS_PER_POST, max_proposals=settings.AI_MAX_PROPOSALS_PER_POST
        )

        # 3. Determine status: needs_input vs completed
        if needs_context:
            final_status = "needs_input"
            status_text = "Se requiere información adicional del equipo para completar la tarea."
        else:
            final_status = "completed"
            status_text = reply_content

        # 4. Publish result message in project thread
        ai_msg = AiMessage(
            project_id=project_id,
            thread="project",
            owner_id=None,
            author_type="ai",
            author_name=f"{role_def.emoji} {role_def.label}",
            author_role_label=f"{role_id}_ai",
            ai_role=role_id,
            content=f"📋 **Resultado de Tarea:** {task_doc['title']}\n\n{status_text}",
            proposals=proposals,
            trigger="task",
            status="ok",
        )
        saved_msg = await self.msg_repo.create_message(ai_msg)

        # 5. Update task record
        await self.task_repo.update_status(
            task_id=task_id,
            status=final_status,
            result=status_text,
            result_message_id=saved_msg["id"],
        )
        updated_task = await self.task_repo.get_by_id(task_id)

        # 6. Broadcast updates & notify assigner
        await manager.broadcast(room_key, {
            "type": "AI_TASK_UPDATED",
            "task": self._serialize_task(updated_task),
        })
        await manager.broadcast(room_key, {
            "type": "AI_MESSAGE_CREATED",
            "message": saved_msg,
        })

        assigned_by = task_doc.get("assigned_by")
        if assigned_by and ObjectId.is_valid(str(assigned_by)):
            try:
                await self.notif_service.create_notification(
                    user_id=str(assigned_by),
                    title=f"Tarea {final_status}: {task_doc['title']}",
                    message=f"El rol {role_def.label} ha finalizado el procesamiento de la tarea.",
                    type="ai_task",
                )
            except Exception as n_err:
                logger.warning(f"[AiWorker] Notification failed: {n_err}")

        await self.job_repo.complete(job.id, result_ref={"task_id": task_id, "message_id": saved_msg["id"]})

    async def _handle_review_diagram(self, job: AiJob) -> None:
        """Autonomous proactive review of diagram by an AI role (Bloques B, C, D, E)."""
        project_id = job.project_id
        role_id = job.role_id or "architect"
        role_def = get_role(role_id)
        room_key = f"project:{project_id}"
        diagram_id = job.payload.get("diagram_id")
        now = self._now()

        # Check project state & participative switch
        project_state = await self.state_repo.get_or_create(project_id)
        if not project_state or not project_state.get("participative", {}).get("enabled", False):
            await self.job_repo.complete(job.id)
            return

        # Fetch diagram doc
        did = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
        diagram_doc = await self.db["diagrams"].find_one({"_id": did})
        if not diagram_doc:
            await self.job_repo.complete(job.id)
            return

        canonical = from_graph_data(diagram_doc.get("graph_data", {}))

        # Check role autonomy config (suggest vs apply)
        role_config = next((r for r in project_state.get("roles", []) if r.get("role_id") == role_id), {})
        autonomy = role_config.get("autonomy", "suggest")
        if not role_config.get("enabled", True) or autonomy == "off":
            await self.job_repo.complete(job.id)
            return

        # Fetch findings
        new_finding_ids = job.payload.get("new_finding_ids", [])
        resolved_finding_ids = job.payload.get("resolved_finding_ids", [])

        new_findings_docs = []
        if new_finding_ids:
            for fid in new_finding_ids:
                doc = await self.db["ai_findings"].find_one({"_id": fid})
                if doc:
                    new_findings_docs.append(doc)

        resolved_findings_docs = []
        if resolved_finding_ids:
            for fid in resolved_finding_ids:
                doc = await self.db["ai_findings"].find_one({"_id": fid})
                if doc:
                    resolved_findings_docs.append(doc)

        # Build role-specific proactive prompt (Bloque D)
        findings_summary_lines = []
        for f in new_findings_docs:
            findings_summary_lines.append(f"- Regla [{f['rule']}] (severidad {f['severity']}): elementos {f.get('element_ids')}")

        resolved_summary_lines = []
        for rf in resolved_findings_docs:
            resolved_summary_lines.append(f"- Resuelto: [{rf['rule']}] sobre elementos {rf.get('element_ids')}")

        role_instruction = ""
        if role_id == "architect":
            role_instruction = (
                "Como Arquitecto, analiza la estructura del diagrama: acoplamiento, cohesión, "
                "clases con muchas responsabilidades, ciclos de herencia y modelado N-N. "
                "Propón comandos UML concretos (uml_command) para resolver problemas estructurales. "
                "Si falta información del dominio, formula preguntas precisas en lugar de asumir."
            )
        elif role_id == "qa":
            role_instruction = (
                "Como QA, analiza las inconsistencias y reglas violadas detectadas. "
                "Explica claramente el impacto en calidad y sugiere criterios de aceptación o casos de prueba."
            )
        elif role_id == "tech_lead":
            role_instruction = (
                "Como Tech Lead, prioriza las mejoras técnicas y propone tareas ejecutables "
                "(proposal.kind='task') para el equipo. Resume el consenso técnico."
            )
        else:
            role_instruction = f"Revisa el modelo UML según tu especialidad como {role_def.label}."

        review_prompt = (
            f"REVISIÓN PROACTIVA DEL DIAGRAMA: '{diagram_doc.get('name', 'Diagrama')}'\n\n"
            f"{role_instruction}\n\n"
            f"Hallazgos detectados recientemente por el linter:\n"
            + ("\n".join(findings_summary_lines) if findings_summary_lines else "Sin nuevos errores críticos.")
            + "\n\n"
            + ("Problemas que acaban de ser resueltos en esta versión:\n" + "\n".join(resolved_summary_lines) if resolved_summary_lines else "")
        )

        project_doc = await self.db["projects"].find_one({"_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id}) or {}
        llm_req = PromptBuilder.build(
            role=role_def,
            project=project_doc,
            diagram=canonical.to_graph_data(),
            trigger=review_prompt,
            purpose="task",
        )

        # Execute LLM
        provider = get_provider(purpose="task")
        res = await provider.generate(llm_req)

        structured_resp: Optional[AiTeamResponse] = None
        raw_text = res.text
        if res.raw_json and isinstance(res.raw_json, dict):
            try:
                structured_resp = AiTeamResponse.model_validate(res.raw_json)
            except Exception:
                pass

        if not structured_resp and raw_text and raw_text.strip().startswith("{"):
            try:
                structured_resp = AiTeamResponse.model_validate(json.loads(raw_text))
            except Exception:
                pass

        reply_content = structured_resp.reply_markdown if structured_resp else raw_text
        proposals = structured_resp.proposals if structured_resp else []

        # If there are resolved findings, append acknowledgment in the text
        if resolved_findings_docs and "resuelto" not in reply_content.lower():
            resolved_names = [r.get("rule") for r in resolved_findings_docs]
            reply_content += f"\n\n✨ **Actualización de calidad:** Listo, quedó resuelto: {', '.join(resolved_names)}."

        # Enforce publication limits: <= 5 proposals, <= 1200 words
        reply_content, proposals = enforce_publication_limits(
            reply_content, proposals, max_words=settings.AI_MAX_WORDS_PER_POST, max_proposals=settings.AI_MAX_PROPOSALS_PER_POST
        )

        # Bloque E: If autonomy is 'apply', execute through ServerDiagramEditor
        applied_notes = []
        if autonomy == "apply":
            from app.modules.ai.schemas import UMLCommandResponse
            for p in proposals:
                if p.kind == "uml_command" and p.command:
                    try:
                        cmd_obj = p.command
                        if isinstance(cmd_obj, dict):
                            cmd_obj = UMLCommandResponse.model_validate(cmd_obj)
                        success, op_count, msg = await self.diagram_editor.apply_command(
                            diagram_id=diagram_id,
                            role_id=role_id,
                            command=cmd_obj,
                            title=p.title,
                        )
                        if success:
                            applied_notes.append(f"⚡ *[Autonomía Apply]* Se aplicó automáticamente la propuesta '{p.title}' ({op_count} cambios).")
                    except Exception as apply_err:
                        logger.error(f"[AiWorker] Failed to apply command autonomously: {apply_err}")

        if applied_notes:
            reply_content += "\n\n" + "\n".join(applied_notes)

        # Publish proactive message to project thread (visible to whole team)
        ai_msg = AiMessage(
            project_id=project_id,
            thread="project",
            owner_id=None,
            author_type="ai",
            author_name=f"{role_def.emoji} {role_def.label}",
            author_role_label=f"{role_id}_ai",
            ai_role=role_id,
            content=reply_content,
            proposals=proposals,
            trigger="proactive_review",
            status="ok",
            diagram_snapshot=canonical.to_graph_data(),
        )
        saved_msg = await self.msg_repo.create_message(ai_msg)

        # Broadcast to project WebSocket
        await manager.broadcast(room_key, {
            "type": "AI_MESSAGE_CREATED",
            "message": saved_msg,
        })

        # Update role cooldown and project last review
        cooldowns = project_state.get("role_cooldowns", {})
        cooldowns[role_id] = now.isoformat()
        await self.db["ai_project_state"].update_one(
            {"project_id": project_id},
            {
                "$set": {
                    f"role_cooldowns.{role_id}": now.isoformat(),
                    "last_review_at": now.isoformat(),
                    "updated_at": now,
                }
            },
        )

        await self.job_repo.complete(job.id, result_ref={"message_id": saved_msg["id"]})

    async def _handle_summarize_digest(self, job: AiJob) -> None:
        """Periodically compiles executive project digest."""
        await self.digest_service.generate_digest(job.project_id)
        await self.job_repo.complete(job.id)

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
