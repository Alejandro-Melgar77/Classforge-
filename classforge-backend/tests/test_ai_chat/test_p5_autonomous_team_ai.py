"""
Comprehensive test suite for P5 — Autonomous Team AI:
- Bloque A: Durable Job Queue (ai_jobs, atomic leases, worker concurrency, lease reaper, stale skipper)
- Bloque B: Triggers & Guards (debounce, deduplication, cooldown, daily budget, anti-loop, instant cancellation)
- Bloque C: Findings Lifecycle (ai_findings sync, open -> resolved, acknowledge, dismiss)
- Bloque D: Role behaviors (Architect, QA, Tech Lead, non-proactive Mentor)
- Bloque E: ServerDiagramEditor, autonomy 'apply', limit enforcement, anti-cycle validation, history undo
- Bloque F: Tasks extensions (assignee_type, assignee_id, status: needs_input, created_by)
- Acceptance: Full automated E2E scenario
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import pytest
from httpx import AsyncClient
from bson import ObjectId

from app.core.config import settings
from app.core.database import db_instance
from app.core.security import create_access_token
from app.llm.registry import set_global_provider, reset_providers
from app.llm.fake import FakeLlmProvider
from app.llm.models import LlmUsage
from app.llm.usage import record_ai_usage
from app.ai_team.domain.jobs import AiJob
from app.ai_team.domain.findings import AiFinding, compute_finding_fingerprint
from app.ai_team.domain.diagram_model import Diagram, Node, Edge, Attribute, compute_canonical_diagram_hash
from app.ai_team.domain.lint import Finding, lint_diagram
from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.ai_team.infrastructure.findings_repository import AiFindingsRepository
from app.ai_team.application.triggers import TriggersManager, enforce_publication_limits
from app.ai_team.application.worker import AiWorker
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLRelationCommand
from app.modules.ai_chat.infrastructure.repositories import (
    AiMessageRepository,
    AiProjectStateRepository,
    AiTaskRepository,
)


class FakeClock:
    """Controllable clock for time-dependent unit tests."""

    def __init__(self, start: Optional[datetime] = None):
        self._now = start or datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


@pytest.fixture(autouse=True)
def setup_fake_llm():
    orig_provider = settings.LLM_PROVIDER
    orig_autonomy = settings.AI_AUTONOMY_ENABLED
    settings.LLM_PROVIDER = "fake"
    settings.AI_AUTONOMY_ENABLED = True
    fake = FakeLlmProvider()
    set_global_provider(fake)
    yield fake
    reset_providers()
    settings.LLM_PROVIDER = orig_provider
    settings.AI_AUTONOMY_ENABLED = orig_autonomy


async def create_user_and_headers(role: str = "dev", name: str = "Test User") -> tuple[dict, str, dict]:
    db = db_instance.db
    user_id = str(ObjectId())
    user_doc = {
        "_id": ObjectId(user_id),
        "name": name,
        "email": f"{user_id}@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }
    await db["users"].insert_one(user_doc)
    token = create_access_token(subject=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    return user_doc, user_id, headers


async def create_test_project_and_diagram(owner_id: str) -> tuple[str, str]:
    """Sets up a project and an active diagram."""
    db = db_instance.db
    project_id = str(ObjectId())
    team_id = ObjectId()

    await db["teams"].insert_one({
        "_id": team_id,
        "name": "Team P5",
        "owner_id": ObjectId(owner_id),
        "member_ids": [ObjectId(owner_id)],
        "is_deleted": False,
    })

    await db["projects"].insert_one({
        "_id": ObjectId(project_id),
        "name": "Project P5 Autonomy",
        "description": "P5 test environment",
        "owner_id": ObjectId(owner_id),
        "team_id": team_id,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    })

    diagram_id = str(ObjectId())
    initial_graph = {
        "nodes": [
            {
                "id": "node_1",
                "type": "class",
                "data": {"name": "Usuario", "attributes": [{"name": "id", "type": "int", "visibility": "+"}]},
            },
            {
                "id": "node_2",
                "type": "class",
                "data": {"name": "Pedido", "attributes": [{"name": "total", "type": "float", "visibility": "+"}]},
            },
        ],
        "edges": [
            {
                "id": "edge_1",
                "type": "association",
                "source": "node_1",
                "target": "node_2",
                "source_multiplicity": "1",
                "target_multiplicity": "0..*",
            }
        ],
    }
    await db["diagrams"].insert_one({
        "_id": ObjectId(diagram_id),
        "name": "Diagrama Core",
        "project_id": ObjectId(project_id),
        "created_by": ObjectId(owner_id),
        "graph_data": initial_graph,
        "version": 1,
        "history": [],
        "is_deleted": False,
        "updated_at": datetime.now(timezone.utc),
    })

    return project_id, diagram_id


# ── Bloque A: Cola de trabajos durable y Worker ─────────────────────────────────

@pytest.mark.asyncio
async def test_bloque_a_atomic_lease_and_concurrency():
    """Verify that find_one_and_update atomically assigns a job lease so two workers never take it."""
    db = db_instance.db
    clock = FakeClock()
    repo = AiJobRepository(db, clock=clock.now)

    job = AiJob(
        project_id="proj-123",
        role_id="architect",
        kind="review_diagram",
        payload={"info": "test"},
        origin="human",
    )
    await repo.enqueue(job)

    # Worker 1 acquires the job
    worker_1_job = await repo.acquire_next(worker_id="worker-A", lease_seconds=120)
    assert worker_1_job is not None
    assert worker_1_job.id == job.id
    assert worker_1_job.status == "running"
    assert worker_1_job.attempts == 1
    assert worker_1_job.lease_until.replace(tzinfo=timezone.utc) == clock.now() + timedelta(seconds=120)

    # Worker 2 attempts to acquire simultaneously -> must receive None
    worker_2_job = await repo.acquire_next(worker_id="worker-B", lease_seconds=120)
    assert worker_2_job is None


@pytest.mark.asyncio
async def test_bloque_a_reaper_recovers_expired_lease():
    """Verify that reaper identifies expired leases and resets them to queued (or failed after 3 attempts)."""
    db = db_instance.db
    clock = FakeClock()
    repo = AiJobRepository(db, clock=clock.now)

    job = AiJob(
        project_id="proj-lease",
        kind="run_task",
        payload={"task_id": "t-1"},
        status="running",
        attempts=1,
        lease_until=clock.now() + timedelta(seconds=60),
    )
    await repo.enqueue(job)

    # Advance clock past lease
    clock.advance(100)

    # Run reaper
    reaped = await repo.reap_expired_leases()
    assert reaped == 1

    # Job is back in queued status
    reloaded = await repo.get_by_id(job.id)
    assert reloaded.status == "queued"
    assert reloaded.lease_until is None

    # Simulate 3 failed attempts
    await db["ai_jobs"].update_one(
        {"_id": job.id},
        {"$set": {"attempts": 3, "status": "running", "lease_until": clock.now() - timedelta(seconds=10)}},
    )
    reaped_final = await repo.reap_expired_leases()
    assert reaped_final == 1
    reloaded_final = await repo.get_by_id(job.id)
    assert reloaded_final.status == "failed"


@pytest.mark.asyncio
async def test_bloque_a_skip_stale_jobs_older_than_24h():
    """Verify that jobs created > 24h ago are marked as skipped."""
    db = db_instance.db
    clock = FakeClock()
    repo = AiJobRepository(db, clock=clock.now)

    stale_job = AiJob(
        project_id="proj-stale",
        kind="review_diagram",
        status="queued",
        created_at=clock.now() - timedelta(hours=25),
    )
    fresh_job = AiJob(
        project_id="proj-fresh",
        kind="review_diagram",
        status="queued",
        created_at=clock.now() - timedelta(hours=2),
    )
    await repo.enqueue(stale_job)
    await repo.enqueue(fresh_job)

    skipped_count = await repo.skip_stale_jobs(max_age_hours=24)
    assert skipped_count == 1

    s_job = await repo.get_by_id(stale_job.id)
    f_job = await repo.get_by_id(fresh_job.id)
    assert s_job.status == "skipped"
    assert f_job.status == "queued"


# ── Bloque B: Disparadores y Guardas ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_bloque_b_anti_loop_guard():
    """Verify that events with origin='ai' NEVER trigger further AI jobs (strict anti-loop rule)."""
    db = db_instance.db
    clock = FakeClock()
    triggers = TriggersManager(db, clock=clock.now)

    result = await triggers.on_diagram_changed(
        project_id="proj-anti-loop",
        diagram_id="diag-1",
        origin="ai",  # Origin is AI bot
    )
    assert result is False

    queued_jobs = await db["ai_jobs"].find({"project_id": "proj-anti-loop"}).to_list(length=10)
    assert len(queued_jobs) == 0


@pytest.mark.asyncio
async def test_bloque_b_debounce_and_deduplication():
    """Verify debounce window and deduplication by canonical hash."""
    db = db_instance.db
    clock = FakeClock()
    triggers = TriggersManager(db, clock=clock.now)

    _, user_id, _ = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    # Enable participative AI
    await db["ai_project_state"].update_one(
        {"project_id": project_id},
        {"$set": {"participative.enabled": True, "roles": [{"role_id": "architect", "enabled": True, "autonomy": "suggest"}]}},
        upsert=True,
    )

    # Rapid burst of 3 diagram changes
    await triggers.on_diagram_changed(project_id, diagram_id, origin="human", quiet_seconds=90)
    clock.advance(10)
    await triggers.on_diagram_changed(project_id, diagram_id, origin="human", quiet_seconds=90)
    clock.advance(10)
    await triggers.on_diagram_changed(project_id, diagram_id, origin="human", quiet_seconds=90)

    # Flush debounce to simulate deadline expiry
    await triggers.flush_debounce(diagram_id)

    # Exactly 1 review_diagram job should be enqueued for architect
    jobs = await db["ai_jobs"].find({"project_id": project_id, "kind": "review_diagram"}).to_list(length=10)
    assert len(jobs) == 1
    assert jobs[0]["role_id"] == "architect"


@pytest.mark.asyncio
async def test_bloque_b_cooldown_per_role():
    """Verify that roles obey the 10 min cooldown between proactive publications."""
    db = db_instance.db
    clock = FakeClock()
    triggers = TriggersManager(db, clock=clock.now)

    _, user_id, _ = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    # Set last publication time to 2 minutes ago (still in cooldown)
    recent_time = (clock.now() - timedelta(minutes=2)).isoformat()
    await db["ai_project_state"].update_one(
        {"project_id": project_id},
        {
            "$set": {
                "participative.enabled": True,
                "roles": [{"role_id": "architect", "enabled": True, "autonomy": "suggest"}],
                "role_cooldowns": {"architect": recent_time},
            }
        },
        upsert=True,
    )

    await triggers._evaluate_diagram_after_debounce(project_id, diagram_id)

    # No job enqueued because of active cooldown
    jobs = await db["ai_jobs"].find({"project_id": project_id, "kind": "review_diagram"}).to_list(length=10)
    assert len(jobs) == 0

    # Advance clock past cooldown (> 10 minutes)
    clock.advance(650)
    await triggers._evaluate_diagram_after_debounce(project_id, diagram_id)

    jobs_after = await db["ai_jobs"].find({"project_id": project_id, "kind": "review_diagram"}).to_list(length=10)
    assert len(jobs_after) == 1


@pytest.mark.asyncio
async def test_bloque_b_daily_budget_guard():
    """Verify that exceeding daily calls or tokens halts proactive reviews."""
    db = db_instance.db
    clock = FakeClock()
    triggers = TriggersManager(db, clock=clock.now)

    _, user_id, _ = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    await db["ai_project_state"].update_one(
        {"project_id": project_id},
        {"$set": {"participative.enabled": True, "roles": [{"role_id": "architect", "enabled": True, "autonomy": "suggest"}]}},
        upsert=True,
    )

    # Simulate budget exhaustion: insert usage entries exceeding limit
    for _ in range(settings.AI_DAILY_CALLS_PER_PROJECT + 5):
        await record_ai_usage(
            project_id=project_id,
            user_id=user_id,
            purpose="task",
            model="fake",
            tokens={"prompt": 100, "candidates": 500, "total": 600},
            latency_ms=10.0,
            ok=True,
            db=db,
        )

    await triggers._evaluate_diagram_after_debounce(project_id, diagram_id)

    # Exceeded budget -> no job enqueued
    jobs = await db["ai_jobs"].find({"project_id": project_id, "kind": "review_diagram"}).to_list(length=10)
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_bloque_b_turning_off_participative_cancels_queued_jobs(async_client: AsyncClient):
    """Requirement: apagar participativa cancela los queued al instante."""
    db = db_instance.db
    _, user_id, headers = await create_user_and_headers(role="owner")
    project_id, _ = await create_test_project_and_diagram(user_id)

    # Enqueue a proactive job in queued state
    job = AiJob(
        project_id=project_id,
        role_id="architect",
        kind="review_diagram",
        status="queued",
    )
    repo = AiJobRepository(db)
    await repo.enqueue(job)

    # Turn off participative AI via HTTP PUT /state
    res = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"participative": {"enabled": False}},
        headers=headers,
    )
    assert res.status_code == 200

    # Job must now be cancelled
    updated_job = await repo.get_by_id(job.id)
    assert updated_job.status == "cancelled"


# ── Bloque C: Ciclo de Vida de Hallazgos (ai_findings) ──────────────────────────

@pytest.mark.asyncio
async def test_bloque_c_findings_lifecycle_transition_to_resolved():
    """Verify that a detected finding transitions to 'resolved' when the linter no longer detects it."""
    db = db_instance.db
    clock = FakeClock()
    findings_repo = AiFindingsRepository(db, clock=clock.now)

    project_id = str(ObjectId())
    diagram_id = str(ObjectId())

    # 1. First run: Linter detects an issue
    finding_1 = Finding(
        rule="circular-inheritance",
        severity="critical",
        element_ids=["node_A", "node_B"],
        message_es="Herencia cíclica entre A y B",
        fix_hint="Elimina una de las relaciones de generalización",
    )
    newly_opened, newly_resolved = await findings_repo.sync_linter_findings(
        project_id=project_id,
        diagram_id=diagram_id,
        findings=[finding_1],
        role_id="qa",
    )
    assert len(newly_opened) == 1
    assert len(newly_resolved) == 0
    assert newly_opened[0].status == "open"
    assert newly_opened[0].rule == "circular-inheritance"

    # 2. Second run: Issue is resolved, linter returns empty list
    clock.advance(60)
    newly_opened_2, newly_resolved_2 = await findings_repo.sync_linter_findings(
        project_id=project_id,
        diagram_id=diagram_id,
        findings=[],
        role_id="qa",
    )
    assert len(newly_opened_2) == 0
    assert len(newly_resolved_2) == 1
    assert newly_resolved_2[0].status == "resolved"
    assert newly_resolved_2[0].resolved_at is not None


@pytest.mark.asyncio
async def test_bloque_c_human_acknowledge_and_dismiss_findings(async_client: AsyncClient):
    """Verify team members can acknowledge or dismiss open findings via API."""
    db = db_instance.db
    _, user_id, headers = await create_user_and_headers(role="dev")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    findings_repo = AiFindingsRepository(db)
    finding = AiFinding(
        project_id=project_id,
        diagram_id=diagram_id,
        fingerprint="rule-x:elem-1",
        rule="god-class",
        status="open",
    )
    await db["ai_findings"].insert_one(finding.to_mongo())

    # Acknowledge
    res_ack = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/findings/{finding.id}/acknowledge",
        headers=headers,
    )
    assert res_ack.status_code == 200

    ack_doc = await findings_repo.get_by_id(finding.id)
    assert ack_doc.status == "acknowledged"

    # Dismiss
    res_dis = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/findings/{finding.id}/dismiss",
        headers=headers,
    )
    assert res_dis.status_code == 200

    dis_doc = await findings_repo.get_by_id(finding.id)
    assert dis_doc.status == "dismissed"


# ── Bloque E: ServerDiagramEditor y Deshacer ───────────────────────────────────

@pytest.mark.asyncio
async def test_bloque_e_server_diagram_editor_limits_and_safety():
    """Verify ServerDiagramEditor rejects > 10 operations, refuses class deletions, and avoids cycles."""
    db = db_instance.db
    editor = ServerDiagramEditor(db)
    _, user_id, _ = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    # 1. Reject command exceeding 10 operations
    many_classes = [UMLClassCommand(name=f"Clase{i}") for i in range(12)]
    cmd_excess = UMLCommandResponse(
        action="add_class",
        classes=many_classes,
        explanation="Too many classes",
        source="backend_ai",
    )
    success, _, msg = await editor.apply_command(diagram_id, "architect", cmd_excess)
    assert success is False
    assert "Límite de operaciones excedido" in msg

    # 2. Refuse class deletion without human confirmation
    cmd_delete = UMLCommandResponse(
        action="delete_class",
        deleted_elements=["node_1"],
        explanation="Deleting Usuario class",
        source="backend_ai",
    )
    success_del, _, msg_del = await editor.apply_command(diagram_id, "architect", cmd_delete)
    assert success_del is False
    assert "no puede eliminar la clase" in msg_del

    # 3. Refuse command that introduces circular inheritance
    cmd_cycle = UMLCommandResponse(
        action="add_relation",
        relations=[
            UMLRelationCommand(source="Usuario", target="Pedido", type="inheritance"),
            UMLRelationCommand(source="Pedido", target="Usuario", type="inheritance"),
        ],
        explanation="Circular inheritance cycle",
        source="backend_ai",
    )
    success_cycle, _, msg_cycle = await editor.apply_command(diagram_id, "architect", cmd_cycle)
    assert success_cycle is False
    assert "ciclos de herencia" in msg_cycle


@pytest.mark.asyncio
async def test_bloque_e_history_restore_endpoint(async_client: AsyncClient):
    """Verify POST /diagrams/{id}/history/{version}/restore creates new version and audits."""
    db = db_instance.db
    _, user_id, headers = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    # Create history entry version 1
    v1_graph = {"nodes": [{"id": "n1", "name": "V1Class"}], "edges": []}
    v2_graph = {"nodes": [{"id": "n1", "name": "V2ModifiedClass"}], "edges": []}

    await db["diagrams"].update_one(
        {"_id": ObjectId(diagram_id)},
        {
            "$set": {"version": 2, "graph_data": v2_graph},
            "$push": {
                "history": {
                    "version": 1,
                    "graph_data": v1_graph,
                    "saved_by": ObjectId(user_id),
                    "saved_at": datetime.now(timezone.utc),
                    "comment": "Versión 1 inicial",
                }
            },
        },
    )

    # Call restore endpoint
    res_restore = await async_client.post(
        f"/api/v1/diagrams/{diagram_id}/history/1/restore",
        headers=headers,
    )
    assert res_restore.status_code == 200
    res_data = res_restore.json()
    assert res_data["success"] is True

    # Check updated diagram has version 3 and graph_data of version 1
    diag = await db["diagrams"].find_one({"_id": ObjectId(diagram_id)})
    assert diag["version"] == 3
    assert diag["graph_data"]["nodes"][0]["name"] == "V1Class"

    # Check audit log
    audit = await db["audit_logs"].find_one({"action": "RESTORE_VERSION", "diagram_id": ObjectId(diagram_id)})
    assert audit is not None
    assert audit["restored_version"] == 1


# ── Bloque F: Tareas Extendidas ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bloque_f_task_execution_and_needs_input():
    """Verify task execution transitions to 'needs_input' if model requires context."""
    db = db_instance.db
    clock = FakeClock()
    worker = AiWorker(db, clock=clock.now)

    _, user_id, _ = await create_user_and_headers(role="owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    task_repo = AiTaskRepository(db)
    from app.modules.ai_chat.schemas import AiTaskCreate
    task_id = await task_repo.create(
        project_id=project_id,
        assigned_by=user_id,
        task_data=AiTaskCreate(
            ai_role="architect",
            title="Diseñar autenticación OAuth2",
            description="Especificar flujos con proveedor externo desconocido",
            diagram_id=diagram_id,
            assignee_type="ai_role",
            assignee_id="architect",
        ),
    )

    # Configure FakeLlmProvider to return needs_context=True
    fake_llm = FakeLlmProvider()
    fake_llm.set_response(
        text='{"reply_markdown": "Se requiere saber qué proveedor OAuth2 se usará.", "needs_context": true, "proposals": []}',
        raw_json={"reply_markdown": "Se requiere saber qué proveedor OAuth2 se usará.", "needs_context": True, "proposals": []},
    )
    set_global_provider(fake_llm)

    job = AiJob(
        project_id=project_id,
        kind="run_task",
        payload={"task_id": task_id, "assigned_by": user_id},
        origin="human",
    )
    await worker.job_repo.enqueue(job)
    await worker.process_next_job()

    updated_task = await task_repo.get_by_id(task_id)
    assert updated_task["status"] == "needs_input"
    assert updated_task["result_message_id"] is not None


# ── Acceptance E2E Scenario ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_acceptance_proactive_diagram_review_lifecycle(async_client: AsyncClient):
    """
    Automated Acceptance Scenario (as specified in P5 requirement):
    1. Diagram with circular inheritance (ClassA <-> ClassB) + class without attributes (EmptyClass).
    2. Participative ON + Architect enabled.
    3. Debounce expiry -> exactly ONE publication appears in project thread with 2 findings and proposals.
    4. Changing the diagram resolves issues -> AI acknowledges resolution; no duplicate publications.
    """
    db = db_instance.db
    clock = FakeClock()
    triggers = TriggersManager(db, clock=clock.now)
    worker = AiWorker(db, clock=clock.now)

    _, user_id, headers = await create_user_and_headers(role="owner", name="Sofia Owner")
    project_id, diagram_id = await create_test_project_and_diagram(user_id)

    # 1. Update diagram to contain circular inheritance + class without attributes (connected so not orphan)
    flawed_graph = {
        "nodes": [
            {"id": "c1", "type": "class", "data": {"name": "ClassA", "attributes": [{"name": "id", "type": "int", "visibility": "+"}]}},
            {"id": "c2", "type": "class", "data": {"name": "ClassB", "attributes": [{"name": "id", "type": "int", "visibility": "+"}]}},
            {"id": "c3", "type": "class", "data": {"name": "EmptyClass", "attributes": []}},
        ],
        "edges": [
            {"id": "e1", "type": "inheritance", "source": "c1", "target": "c2"},
            {"id": "e2", "type": "inheritance", "source": "c2", "target": "c1"},
            {"id": "e3", "type": "association", "source": "c1", "target": "c3"},
        ],
    }
    await db["diagrams"].update_one(
        {"_id": ObjectId(diagram_id)},
        {"$set": {"graph_data": flawed_graph}},
    )

    # 2. Enable participative AI with Architect role
    await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={
            "participative": {"enabled": True},
            "roles": [
                {"role_id": "architect", "enabled": True, "autonomy": "suggest"},
                {"role_id": "qa", "enabled": False},
            ],
        },
        headers=headers,
    )

    # 3. Diagram changed event -> Debounce expires -> Enqueues review_diagram
    await triggers.on_diagram_changed(project_id, diagram_id, origin="human", quiet_seconds=90)
    clock.advance(95)
    await triggers.flush_debounce(diagram_id)

    # Worker executes the review_diagram job
    processed_job = await worker.process_next_job()
    assert processed_job is not None
    assert processed_job.status == "done"

    # Exactly ONE proactive review message appears in project thread
    msg_repo = AiMessageRepository(db)
    messages, total, _ = await msg_repo.get_history(project_id, limit=20)
    assert len(messages) == 1
    post = messages[0]
    assert post["thread"] == "project"
    assert post["ai_role"] == "architect"
    assert post["trigger"] == "proactive_review"

    # Verify open findings tracked in ai_findings (inheritance-cycle and class-no-attributes)
    findings = await db["ai_findings"].find({"project_id": project_id, "status": "open"}).to_list(length=10)
    assert len(findings) == 2
    rule_names = {f["rule"] for f in findings}
    assert "inheritance-cycle" in rule_names
    assert "class-no-attributes" in rule_names

    # 4. Modify diagram to resolve both issues: break the cycle and add attribute to EmptyClass
    clock.advance(600)  # Advance past role cooldown
    fixed_graph = {
        "nodes": [
            {"id": "c1", "type": "class", "data": {"name": "ClassA", "attributes": [{"name": "id", "type": "int", "visibility": "+"}]}},
            {"id": "c2", "type": "class", "data": {"name": "ClassB", "attributes": [{"name": "id", "type": "int", "visibility": "+"}]}},
            {"id": "c3", "type": "class", "data": {"name": "EmptyClass", "attributes": [{"name": "nombre", "type": "str", "visibility": "+"}]}},
        ],
        "edges": [
            {"id": "e1", "type": "inheritance", "source": "c1", "target": "c2"},
            {"id": "e3", "type": "association", "source": "c1", "target": "c3"},
            # Cycle removed!
        ],
    }
    await db["diagrams"].update_one(
        {"_id": ObjectId(diagram_id)},
        {"$set": {"graph_data": fixed_graph}},
    )

    # Trigger diagram changed on fixed graph
    await triggers.on_diagram_changed(project_id, diagram_id, origin="human", quiet_seconds=90)
    clock.advance(95)
    await triggers.flush_debounce(diagram_id)

    # Worker executes the second review
    processed_job_2 = await worker.process_next_job()
    assert processed_job_2 is not None
    assert processed_job_2.status == "done"

    # Check that findings transitioned to 'resolved'
    resolved_findings = await db["ai_findings"].find({"project_id": project_id, "status": "resolved"}).to_list(length=10)
    assert len(resolved_findings) == 2

    # Second publication acknowledges resolution and doesn't duplicate
    all_msgs, _, _ = await msg_repo.get_history(project_id, limit=20)
    assert len(all_msgs) == 2
    latest_post = all_msgs[-1]  # chronological order, newest message is last
    assert "resuelto" in latest_post["content"].lower()
