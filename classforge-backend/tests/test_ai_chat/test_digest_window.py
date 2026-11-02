"""Regression test for A5: Project digest reads the newest message window."""
from datetime import datetime, timedelta, timezone
import pytest

from app.core.database import db_instance
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository

PROJECT_ID = "507f1f77bcf86cd799439085"


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("ai_messages", "ai_project_state"):
        await db_instance.db[collection].delete_many({})
    yield


async def test_digest_window_uses_newest_messages():
    """A5: Message repository and digest must read the most recent N messages, not the oldest 50."""
    repo = AiMessageRepository(db_instance.db)
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Insert 60 messages in sequence
    for i in range(60):
        await db_instance.db["ai_messages"].insert_one({
            "_id": f"msg_{i:03d}",
            "project_id": PROJECT_ID,
            "thread": "group",
            "owner_id": "user1",
            "author_type": "user",
            "author_name": "Dev",
            "content": f"Mensaje número {i}",
            "status": "ok",
            "created_at": base_time + timedelta(minutes=i),
        })

    # When querying the latest window (e.g. for digest generation with order="desc")
    newest_messages, total, _ = await repo.get_history(PROJECT_ID, limit=50, order="desc")

    assert total == 60
    assert len(newest_messages) == 50
    # First item in newest-first order must be the latest message (number 59, not number 0)
    assert newest_messages[0]["content"] == "Mensaje número 59"
    # Last item in the 50-message slice must be message 10
    assert newest_messages[-1]["content"] == "Mensaje número 10"
