"""AI team/chat regressions (audit A4, A5, A13, A29, A30, A32, A33)."""
import pytest
from bson import ObjectId

from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.application.worker import AiWorker
from app.ai_team.domain.jobs import AiJob
from app.core.database import db_instance
from app.modules.ai.schemas import UMLClassCommand, UMLCommandResponse, UMLRelationCommand
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository
from app.modules.ai_chat.infrastructure.repositories.task_repository import AiTaskRepository
from app.modules.ai_chat.infrastructure.repositories import AiMessageRepository as _MsgRepo  # noqa: F401
from app.core.config import settings
from app.core.errors import NotFoundError

PROJECT_ID = "507f1f77bcf86cd799439081"
USER_ID = ObjectId("507f1f77bcf86cd799439082")
DIAGRAM_ID = ObjectId("507f1f77bcf86cd799439083")


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("ai_messages", "ai_jobs", "ai_tasks", "ai_project_state",
                       "diagrams", "diagram_versions", "ai_usage", "ai_findings"):
        await db_instance.db[collection].delete_many({})
    yield


# ── A5: digest/history window ──────────────────────────────────────────────────

async def test_history_desc_returns_the_newest_window():
    from datetime import datetime, timedelta, timezone

    repo = AiMessageRepository(db_instance.db)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(60):
        await db_instance.db["ai_messages"].insert_one({
            "_id": f"m{i:03d}",
            "project_id": PROJECT_ID,
            "thread": "personal",
            "owner_id": "u",
            "author_type": "user",
            "author_name": "U",
            "content": f"mensaje {i}",
            "status": "ok",
            "created_at": base + timedelta(minutes=i),
        })

    asc, total_asc, _ = await repo.get_history(PROJECT_ID, limit=50)
    desc, total_desc, _ = await repo.get_history(PROJECT_ID, limit=50, order="desc")

    assert total_asc == total_desc == 60
    assert asc[0]["content"] == "mensaje 0"
    assert desc[0]["content"] == "mensaje 59"  # newest first
    assert asc[-1]["content"] == "mensaje 49"


async def test_history_total_honours_filters():
    from datetime import datetime, timezone

    repo = AiMessageRepository(db_instance.db)
    now = datetime.now(timezone.utc)
    for i, role in enumerate(["architect", "qa", "qa"]):
        await db_instance.db["ai_messages"].insert_one({
            "_id": f"f{i}",
            "project_id": PROJECT_ID,
            "thread": "personal",
            "owner_id": "u",
            "author_type": "ai",
            "ai_role": role,
            "content": "x",
            "created_at": now,
        })

    _, total, _ = await repo.get_history(PROJECT_ID, role="qa")
    assert total == 2


# ── A30: proposal existence ───────────────────────────────────────────────────

async def test_proposal_state_rejects_unknown_proposal():
    repo = AiMessageRepository(db_instance.db)
    await db_instance.db["ai_messages"].insert_one({
        "_id": "msg-1",
        "project_id": PROJECT_ID,
        "thread": "personal",
        "owner_id": "u",
        "author_type": "ai",
        "content": "propuesta",
        "proposals": [{"id": "p-1", "title": "Agregar clase"}],
    })

    with pytest.raises(NotFoundError):
        await repo.update_proposal_state("msg-1", "p-no-existe", "applied", "u", PROJECT_ID)

    updated = await repo.update_proposal_state("msg-1", "p-1", "applied", "u", PROJECT_ID)
    assert updated["proposal_state"]["p-1"]["status"] == "applied"


# ── A13 / A32: server-side AI editor ─────────────────────────────────────────

def _diagram_doc():
    return {
        "_id": DIAGRAM_ID,
        "name": "D",
        "created_by": USER_ID,
        "member_ids": [],
        "team_id": None,
        "project_id": None,
        "is_deleted": False,
        "version": 1,
        "graph_data": {
            "nodes": [
                {"id": "n1", "type": "class", "position": {"x": 0, "y": 0},
                 "size": {"width": 200, "height": 120},
                 "data": {"name": "Usuario", "attributes": [], "methods": []}},
            ],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
    }


async def test_editor_refuses_to_overwrite_human_locks():
    """A13: the AI must not write while a human holds the element lock."""
    from app.modules.collaboration.connection_manager import manager

    await db_instance.db["diagrams"].insert_one(_diagram_doc())
    editor = ServerDiagramEditor(db_instance.db)

    # A human holds the lock on the class the AI wants to touch.
    assert manager.acquire_lock(str(DIAGRAM_ID), "human-1", "n1") is True

    command = UMLCommandResponse(
        action="create_class",
        classes=[UMLClassCommand(name="Usuario", attributes=[], methods=[])],
        explanation="ok",
        source="n8n",
    )

    ok, ops, message = await editor.apply_command(str(DIAGRAM_ID), "architect", command)
    manager.release_all_user_locks(str(DIAGRAM_ID), "human-1")

    assert ok is False
    assert ops == 0
    assert "editados" in message.lower()


async def test_editor_rejects_relation_to_missing_class():
    """A32: dangling relations were silently dropped instead of rejected."""
    await db_instance.db["diagrams"].insert_one(_diagram_doc())
    editor = ServerDiagramEditor(db_instance.db)

    command = UMLCommandResponse(
        action="create_relation",
        relations=[UMLRelationCommand(source="Usuario", target="NoExiste", type="association")],
        explanation="ok",
        source="n8n",
    )

    ok, ops, message = await editor.apply_command(str(DIAGRAM_ID), "architect", command)

    assert ok is False
    assert "inexistentes" in message.lower()

    stored = await db_instance.db["diagrams"].find_one({"_id": DIAGRAM_ID})
    assert stored["graph_data"]["edges"] == []


# ── A33: autonomy switch gates queued jobs ───────────────────────────────────

async def test_worker_skips_jobs_when_autonomy_disabled(monkeypatch):
    worker = AiWorker(db_instance.db)
    job = AiJob(id="job-1", project_id=PROJECT_ID, kind="review_diagram")

    executed = []

    async def fake_handler(_job):
        executed.append(_job.id)

    monkeypatch.setattr(worker, "_handle_review_diagram", fake_handler)
    monkeypatch.setattr(settings, "AI_AUTONOMY_ENABLED", False)

    await worker._execute_job(job)

    assert executed == []


# ── A4: a message must be answered exactly once ──────────────────────────────

async def test_send_message_enqueues_one_job_and_never_runs_inline(monkeypatch):
    import asyncio

    from app.modules.ai_chat.schemas import AiRoleChatRequest
    from app.modules.ai_chat.service import AiChatService

    await db_instance.db["projects"].insert_one({
        "_id": ObjectId(PROJECT_ID),
        "name": "P",
        "owner_id": USER_ID,
        "type": "personal",
        "is_deleted": False,
    })

    service = AiChatService(db_instance.db)
    inline_calls = []

    async def fake_process(**kwargs):
        inline_calls.append(kwargs)

    monkeypatch.setattr(AiChatService, "_process_ai_response", fake_process)

    request = AiRoleChatRequest(
        project_id=PROJECT_ID,
        message="¿Qué opinas del diseño?",
        ai_role="architect",
    )
    await service.send_message_with_role(
        request=request, user_id=str(USER_ID), username="U", user_role="dev"
    )
    await asyncio.sleep(0)

    # The durable job is the only execution path.
    assert inline_calls == []
    assert await db_instance.db["ai_jobs"].count_documents({"project_id": PROJECT_ID}) == 1


# ── A29: task deletion is restricted to its creator ─────────────────────────

async def test_task_delete_requires_creator_or_admin():
    from app.core.errors import ForbiddenError
    from app.modules.ai_chat.router import delete_task

    repo = AiTaskRepository(db_instance.db)
    await db_instance.db["ai_tasks"].insert_one({
        "_id": "task-1",
        "project_id": PROJECT_ID,
        "assigned_by": USER_ID,
        "ai_role": "architect",
        "status": "pending",
    })

    with pytest.raises(ForbiddenError):
        await delete_task(
            PROJECT_ID,
            "task-1",
            project={},
            current_user={"_id": ObjectId(), "role": "dev"},
            db=db_instance.db,
        )

    # The creator can delete it.
    result = await delete_task(
        PROJECT_ID,
        "task-1",
        project={},
        current_user={"_id": USER_ID, "role": "dev"},
        db=db_instance.db,
    )
    assert result["success"] is True
    assert await repo.get_by_id("task-1") is None
