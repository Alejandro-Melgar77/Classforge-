"""
Event triggers and in-process bus for ClassForge AI Team (P5 Bloque B).

Manages:
- diagram_changed with per-diagram debounce, canonical hash, and linter check
- user_message -> answer_message
- task_assigned -> run_task
- project_opened lazy check
- Mandatory guards: anti-loop (origin=='ai'), role cooldown, daily budget,
  global and project-level switches, publication limits.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from bson import ObjectId

from app.core.config import settings
from app.ai_team.domain.jobs import AiJob
from app.ai_team.domain.diagram_model import Diagram, from_graph_data
from app.ai_team.domain.lint import lint_diagram, Finding
from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
from app.modules.ai_chat.infrastructure.repositories import AiProjectStateRepository

logger = logging.getLogger(__name__)


def enforce_publication_limits(
    content: str,
    proposals: List[Any],
    max_words: int = 1200,
    max_proposals: int = 5,
) -> Tuple[str, List[Any]]:
    """Enforces strict boundaries on proactive and reactive publications."""
    trimmed_proposals = proposals[:max_proposals]
    words = content.split()
    if len(words) > max_words:
        truncated_content = " ".join(words[:max_words]) + "\n\n*(Publicación resumida por límite de extensión)*"
    else:
        truncated_content = content
    return truncated_content, trimmed_proposals


async def get_project_daily_usage(
    db,
    project_id: str,
    clock: Optional[Callable[[], datetime]] = None,
) -> Tuple[int, int]:
    """Calculates total AI calls and candidates tokens consumed today by project."""
    now = clock() if clock else datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    try:
        cursor = db["ai_usage"].find({
            "project_id": str(project_id),
            "created_at": {"$gte": start_of_day},
        })
        docs = await cursor.to_list(length=2000)
        total_calls = len(docs)
        total_output_tokens = sum(
            (d.get("tokens", {}) or {}).get("candidates", 0) or 0
            for d in docs
        )
        return total_calls, total_output_tokens
    except Exception as exc:
        logger.warning(f"[Triggers] Failed to query daily usage: {exc}")
        return 0, 0


class TriggersManager:
    """Orchestrates event triggers, debounce timers, and autonomy guards."""

    def __init__(self, db, clock: Optional[Callable[[], datetime]] = None):
        self.db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.job_repo = AiJobRepository(db, clock=self._clock)
        self.findings_repo = AiFindingsRepository(db, clock=self._clock)
        self.state_repo = AiProjectStateRepository(db)
        # diagram_id -> {"project_id": str, "deadline": datetime, "task": Optional[asyncio.Task]}
        self._debounce_registry: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> datetime:
        return self._clock()

    # ── Trigger 1: Diagram Changed ─────────────────────────────────────────────

    async def on_diagram_changed(
        self,
        project_id: str,
        diagram_id: str,
        origin: str = "human",
        quiet_seconds: Optional[int] = None,
    ) -> bool:
        """Triggered on PUT /graph or WS diagram edit operations.
        
        Guards:
        - origin == 'ai' NEVER triggers review (anti-loop rule)
        - global switch AI_AUTONOMY_ENABLED must be True
        """
        # Guard: Anti-loop (events caused by AI never trigger further AI reviews)
        if origin == "ai":
            logger.debug(f"[Triggers] Ignored diagram_changed from AI origin on diagram {diagram_id}")
            return False

        if not settings.AI_AUTONOMY_ENABLED:
            logger.debug("[Triggers] AI_AUTONOMY_ENABLED is False, skipping diagram_changed")
            return False

        secs = quiet_seconds if quiet_seconds is not None else settings.AI_REVIEW_QUIET_SECONDS
        now = self._now()
        deadline = now + timedelta(seconds=secs)

        entry = self._debounce_registry.get(diagram_id)
        if entry and entry.get("task") and not entry["task"].done():
            # Extend existing debounce window
            entry["deadline"] = deadline
            logger.debug(f"[Triggers] Debounce extended for diagram {diagram_id} until {deadline}")
            return True

        # Schedule debounce task
        async def _debounce_wait():
            while True:
                current_entry = self._debounce_registry.get(diagram_id)
                if not current_entry:
                    break
                current_now = self._now()
                target_deadline = current_entry["deadline"]
                if current_now >= target_deadline:
                    # Debounce period has elapsed cleanly
                    self._debounce_registry.pop(diagram_id, None)
                    await self._evaluate_diagram_after_debounce(project_id, diagram_id)
                    break
                else:
                    sleep_secs = max(0.1, (target_deadline - current_now).total_seconds())
                    await asyncio.sleep(min(sleep_secs, 1.0))

        task = asyncio.create_task(_debounce_wait())
        self._debounce_registry[diagram_id] = {
            "project_id": project_id,
            "deadline": deadline,
            "task": task,
        }
        return True

    async def flush_debounce(self, diagram_id: str) -> None:
        """Flushes an active debounce timer immediately (useful for testing or direct evaluation)."""
        entry = self._debounce_registry.pop(diagram_id, None)
        if entry:
            if entry.get("task") and not entry["task"].done():
                entry["task"].cancel()
            await self._evaluate_diagram_after_debounce(entry["project_id"], diagram_id)

    async def _evaluate_diagram_after_debounce(self, project_id: str, diagram_id: str) -> None:
        """Runs linter, verifies findings & structural delta, and enqueues review_diagram jobs."""
        now = self._now()

        # 1. Project-level participatory AI guard
        project_state = await self.state_repo.get_or_create(project_id)
        if not project_state or not project_state.get("participative", {}).get("enabled", False):
            logger.info(f"[Triggers] Participative AI disabled for project {project_id}, skipping review.")
            return

        # 2. Retrieve diagram data
        try:
            did = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            diagram_doc = await self.db["diagrams"].find_one({"_id": did})
            if not diagram_doc:
                return
        except Exception as e:
            logger.error(f"[Triggers] Could not fetch diagram {diagram_id}: {e}")
            return

        canonical_diagram = from_graph_data(diagram_doc.get("graph_data", {}))
        current_hash = canonical_diagram.compute_hash()
        last_hash = project_state.get("last_reviewed_diagram_hash")

        # 3. Run deterministic linter
        findings: List[Finding] = lint_diagram(canonical_diagram)

        # 4. Sync findings lifecycle (Bloque C)
        new_findings, resolved_findings = await self.findings_repo.sync_linter_findings(
            project_id=project_id,
            diagram_id=diagram_id,
            findings=findings,
        )

        has_new_findings = len(new_findings) > 0
        has_resolved_findings = len(resolved_findings) > 0
        has_structural_change = (current_hash != last_hash)

        # Only enqueue if there are new issues, resolved issues, or relevant structural changes
        if not has_new_findings and not has_resolved_findings and not has_structural_change:
            logger.info(f"[Triggers] No new findings or structural change for diagram {diagram_id}. Skipping.")
            return

        # 5. Check daily budget guard
        daily_calls, daily_tokens = await get_project_daily_usage(self.db, project_id, clock=self._clock)
        if daily_calls >= settings.AI_DAILY_CALLS_PER_PROJECT:
            logger.warning(f"[Triggers] Project {project_id} exceeded daily calls limit ({daily_calls}).")
            return
        if daily_tokens >= settings.AI_DAILY_OUTPUT_TOKENS_PER_PROJECT:
            logger.warning(f"[Triggers] Project {project_id} exceeded daily output tokens ({daily_tokens}).")
            return

        # 6. Evaluate candidate roles for diagram review
        roles_config = project_state.get("roles", [])
        role_cooldowns = project_state.get("role_cooldowns", {})
        cooldown_delta = timedelta(seconds=settings.AI_ROLE_COOLDOWN_SECONDS)
        enqueued_any = False

        for r in roles_config:
            role_id = r.get("role_id")
            # Mentor is strictly non-proactive (only responds on mention or explicit help)
            if role_id == "mentor":
                continue
            if not r.get("enabled", True) or r.get("autonomy") == "off":
                continue

            # Bloque B: verify trigger on_diagram_change is enabled for this role
            role_triggers = r.get("triggers")
            if role_triggers is None:
                # Architect and QA are the default roles with on_diagram_change trigger
                role_triggers = ["on_diagram_change"] if role_id in ("architect", "qa") else []
            if "on_diagram_change" not in role_triggers:
                continue

            # Role Cooldown guard
            last_posted_str = role_cooldowns.get(role_id)
            if last_posted_str:
                try:
                    last_posted = datetime.fromisoformat(last_posted_str)
                    if last_posted.tzinfo is None:
                        last_posted = last_posted.replace(tzinfo=timezone.utc)
                    if now - last_posted < cooldown_delta:
                        logger.info(f"[Triggers] Role {role_id} in project {project_id} is in cooldown.")
                        continue
                except Exception:
                    pass

            # Enqueue review_diagram job
            job = AiJob(
                project_id=project_id,
                role_id=role_id,
                kind="review_diagram",
                payload={
                    "diagram_id": diagram_id,
                    "diagram_hash": current_hash,
                    "new_finding_ids": [f.id for f in new_findings],
                    "resolved_finding_ids": [f.id for f in resolved_findings],
                },
                dedupe_key=f"review:{project_id}:{diagram_id}:{role_id}:{current_hash}",
                origin="human",
                status="queued",
            )
            await self.job_repo.enqueue(job)
            enqueued_any = True
            logger.info(f"[Triggers] Enqueued review_diagram job for role {role_id} in project {project_id}.")

        if enqueued_any:
            await self.db["ai_project_state"].update_one(
                {"project_id": project_id},
                {"$set": {"last_reviewed_diagram_hash": current_hash, "updated_at": now}},
            )

    # ── Trigger 2: User Message ────────────────────────────────────────────────

    async def on_user_message(
        self,
        project_id: str,
        user_id: str,
        ai_msg_id: str,
        role_id: str,
        trigger_text: str,
        diagram_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[AiJob]:
        """Enqueues an answer_message job for an AI role responder."""
        job = AiJob(
            project_id=project_id,
            role_id=role_id,
            kind="answer_message",
            payload={
                "ai_msg_id": ai_msg_id,
                "user_id": user_id,
                "trigger_text": trigger_text,
                "diagram_id": diagram_id,
                "api_key": api_key,
                "model": model,
            },
            dedupe_key=f"answer:{ai_msg_id}",
            origin="human",
            status="queued",
        )
        return await self.job_repo.enqueue(job)

    # ── Trigger 3: Task Assigned ───────────────────────────────────────────────

    async def on_task_assigned(
        self,
        project_id: str,
        task_id: str,
        role_id: str,
        assigned_by: str,
        origin: str = "human",
    ) -> Optional[AiJob]:
        """Enqueues a run_task job when an AI task is assigned or triggered for execution."""
        job = AiJob(
            project_id=project_id,
            role_id=role_id,
            kind="run_task",
            payload={
                "task_id": task_id,
                "assigned_by": assigned_by,
            },
            dedupe_key=f"task:{task_id}",
            origin=origin,
            status="queued",
        )
        return await self.job_repo.enqueue(job)

    # ── Trigger 4: Project Opened (Lazy Evaluation) ────────────────────────────

    async def on_project_opened(self, project_id: str, origin: str = "human") -> None:
        """Lazy periodic trigger executed when team members access the project.
        Checks if project has been without review for > AI_PERIODIC_HOURS and has activity.
        """
        if origin == "ai" or not settings.AI_AUTONOMY_ENABLED:
            return

        now = self._now()
        project_state = await self.state_repo.get_or_create(project_id)
        if not project_state or not project_state.get("participative", {}).get("enabled", False):
            return

        last_review_at = project_state.get("last_review_at")
        threshold = now - timedelta(hours=settings.AI_PERIODIC_HOURS)

        needs_review = False
        if not last_review_at:
            needs_review = True
        else:
            try:
                lr = datetime.fromisoformat(last_review_at) if isinstance(last_review_at, str) else last_review_at
                if lr.tzinfo is None:
                    lr = lr.replace(tzinfo=timezone.utc)
                if lr < threshold:
                    needs_review = True
            except Exception:
                needs_review = True

        if not needs_review:
            return

        # Check if project has an active diagram
        pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        cursor = self.db["diagrams"].find({"project_id": pid, "is_deleted": {"$ne": True}}).sort("updated_at", -1).limit(1)
        diagrams = await cursor.to_list(length=1)
        if diagrams:
            diagram_id = str(diagrams[0]["_id"])
            await self._evaluate_diagram_after_debounce(project_id, diagram_id)
            await self.db["ai_project_state"].update_one(
                {"project_id": project_id},
                {"$set": {"last_review_at": now.isoformat()}},
            )
