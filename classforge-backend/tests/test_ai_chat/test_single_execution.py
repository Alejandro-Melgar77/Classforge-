"""Regression test for A4: Single execution path for AI chat messages."""
import asyncio
import pytest
from bson import ObjectId

from app.core.database import db_instance
from app.modules.ai_chat.schemas import AiRoleChatRequest
from app.modules.ai_chat.service import AiChatService

PROJECT_ID = "507f1f77bcf86cd799439081"
USER_ID = ObjectId("507f1f77bcf86cd799439082")


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("ai_messages", "ai_jobs", "ai_tasks", "projects"):
        await db_instance.db[collection].delete_many({})
    yield


async def test_send_message_triggers_exactly_one_llm_execution(monkeypatch):
    """A4: A single user message must enqueue a durable job and NEVER spawn a competing background task."""
    await db_instance.db["projects"].insert_one({
        "_id": ObjectId(PROJECT_ID),
        "name": "Single Exec Test Project",
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
        message="¿Puedes revisar la arquitectura del diagrama?",
        ai_role="architect",
    )
    await service.send_message_with_role(
        request=request, user_id=str(USER_ID), username="Tester", user_role="dev"
    )
    await asyncio.sleep(0.01)

    # Exactly 0 inline/untracked executions (the worker is the single execution path)
    assert len(inline_calls) == 0
    # Exactly 1 queued job in ai_jobs
    job_count = await db_instance.db["ai_jobs"].count_documents({"project_id": PROJECT_ID})
    assert job_count == 1
