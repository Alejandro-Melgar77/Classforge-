from datetime import datetime, timezone
import pytest
from mongomock_motor import AsyncMongoMockClient
from app.core.errors import ValidationError
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository


@pytest.mark.anyio
@pytest.mark.parametrize('personal', [False, True])
async def test_duplicate_timestamps_do_not_drop_messages(personal):
    db = AsyncMongoMockClient().test
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db.ai_messages.insert_many([{'_id': f'm{i:03}', 'project_id': 'p', 'thread': 'personal', 'owner_id': 'u', 'created_at': stamp} for i in range(11)])
    repo = AiMessageRepository(db)
    async def page(**kwargs):
        return await (repo.get_mine_history('p', 'u', **kwargs) if personal else repo.get_history('p', **kwargs))
    cursor, ids = None, []
    while True:
        items, _, next_cursor = await page(after=cursor, limit=3)
        if not items:
            break
        ids.extend(m['id'] for m in items)
        cursor = next_cursor
    assert ids == [f'm{i:03}' for i in range(11)]
    cursor, seen = '2026-01-02T00:00:00+00:00', []
    while True:
        items, _, next_cursor = await page(before=cursor, limit=3)
        if not items:
            break
        seen = [m['id'] for m in items] + seen
        cursor = next_cursor
    assert seen == ids
    with pytest.raises(ValidationError):
        await page(after='invalid', limit=3)
