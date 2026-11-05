import pytest
from datetime import datetime, timezone
from mongomock_motor import AsyncMongoMockClient

from app.core.errors import ValidationError, ForbiddenError, NotFoundError
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository


@pytest.mark.anyio
async def test_chat_privacy_and_isolation():
    db = AsyncMongoMockClient().test
    repo = AiMessageRepository(db)

    user_a = "usr_001"
    user_b = "usr_002"
    project_1 = "proj_001"
    project_2 = "proj_002"

    t0 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

    # 1. User A personal message in Project 1 (private)
    await db.ai_messages.insert_one({
        "_id": "msg_a_personal",
        "project_id": project_1,
        "owner_id": user_a,
        "thread": "personal",
        "visibility": "private",
        "content": "Personal plan of user A",
        "role": "user",
        "created_at": t0,
    })

    # 2. Project 1 team message (shared)
    await db.ai_messages.insert_one({
        "_id": "msg_team",
        "project_id": project_1,
        "owner_id": user_a,
        "thread": "project",
        "visibility": "team",
        "content": "Team update by user A",
        "role": "user",
        "created_at": t0,
    })

    # 3. User B personal message in Project 1 (private)
    await db.ai_messages.insert_one({
        "_id": "msg_b_personal",
        "project_id": project_1,
        "owner_id": user_b,
        "thread": "personal",
        "visibility": "private",
        "content": "Secret note of user B",
        "role": "user",
        "created_at": t0,
    })

    # 4. User A personal message in Project 2 (isolated project)
    await db.ai_messages.insert_one({
        "_id": "msg_p2_personal",
        "project_id": project_2,
        "owner_id": user_a,
        "thread": "personal",
        "visibility": "private",
        "content": "User A note in project 2",
        "role": "user",
        "created_at": t0,
    })

    # User A reads Project 1 group history
    items_a, _, _ = await repo.get_history(project_1, user_id=user_a)
    ids_seen_by_a = {m["id"] for m in items_a}
    assert "msg_a_personal" in ids_seen_by_a, "User A must see their own personal message in group history"
    assert "msg_team" in ids_seen_by_a, "User A must see team message"
    assert "msg_b_personal" not in ids_seen_by_a, "User A must NEVER see User B's private personal message"
    assert "msg_p2_personal" not in ids_seen_by_a, "Project 2 messages must never leak into Project 1"

    # User B reads Project 1 group history
    items_b, _, _ = await repo.get_history(project_1, user_id=user_b)
    ids_seen_by_b = {m["id"] for m in items_b}
    assert "msg_b_personal" in ids_seen_by_b, "User B must see their own personal message"
    assert "msg_team" in ids_seen_by_b, "User B must see team message"
    assert "msg_a_personal" not in ids_seen_by_b, "User B must NEVER see User A's private personal message"
    assert "msg_p2_personal" not in ids_seen_by_b, "Project 2 messages must never leak into Project 1"

    # User B reads my-history
    mine_b, _, _ = await repo.get_mine_history(project_1, user_b)
    ids_mine_b = {m["id"] for m in mine_b}
    assert "msg_b_personal" in ids_mine_b
    assert "msg_a_personal" not in ids_mine_b, "User A's personal messages must never leak into User B's private history"


@pytest.mark.anyio
async def test_publish_personal_message_to_team():
    db = AsyncMongoMockClient().test
    repo = AiMessageRepository(db)

    user_a = "usr_001"
    user_b = "usr_002"
    project_1 = "proj_001"
    t0 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

    await db.ai_messages.insert_one({
        "_id": "msg_publishable",
        "project_id": project_1,
        "owner_id": user_a,
        "thread": "personal",
        "visibility": "private",
        "content": "Proposal to publish",
        "role": "assistant",
        "created_at": t0,
    })

    # Non-owner User B cannot publish User A's message
    with pytest.raises(ForbiddenError):
        await repo.publish_message(message_id="msg_publishable", user_id=user_b, project_id=project_1)

    # Owner User A publishes the message
    published = await repo.publish_message(message_id="msg_publishable", user_id=user_a, project_id=project_1)
    assert published["visibility"] == "team"
    assert published["thread"] == "project"

    # Now User B CAN see it in group history!
    items_b, _, _ = await repo.get_history(project_1, user_id=user_b)
    ids_b = {m["id"] for m in items_b}
    assert "msg_publishable" in ids_b


@pytest.mark.anyio
async def test_1000_messages_identical_timestamps_pagination_h08():
    """
    H08: Composite cursor pagination (created_at, _id).
    Tests 1000 messages with identical timestamps paginated in forward (after)
    and backward (before) directions, verifying zero omissions and zero duplicates.
    """
    db = AsyncMongoMockClient().test
    repo = AiMessageRepository(db)
    project_id = "proj_h08"
    user_id = "user_h08"

    fixed_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    total_messages = 1000

    docs = []
    for i in range(total_messages):
        docs.append({
            "_id": f"msg_{i:04d}",
            "project_id": project_id,
            "owner_id": user_id,
            "thread": "personal",
            "visibility": "team",
            "role": "user",
            "content": f"Message number {i}",
            "created_at": fixed_time,
        })
    await db.ai_messages.insert_many(docs)

    # Forward pagination using 'after'
    page_size = 75
    forward_ids = []
    cursor = None

    while True:
        items, _, next_cursor = await repo.get_history(
            project_id=project_id,
            user_id=user_id,
            after=cursor,
            limit=page_size,
        )
        if not items:
            break
        forward_ids.extend(m["id"] for m in items)
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    assert len(forward_ids) == total_messages, f"Expected {total_messages} messages forward, got {len(forward_ids)}"
    assert len(set(forward_ids)) == total_messages, "Detected duplicates in forward pagination"
    assert forward_ids == [f"msg_{i:04d}" for i in range(total_messages)], "Pagination order mismatch forward"

    # Backward pagination using 'before'
    backward_ids = []
    # Start before a timestamp in the future
    cursor = "2026-03-02T00:00:00+00:00"

    while True:
        items, _, next_cursor = await repo.get_history(
            project_id=project_id,
            user_id=user_id,
            before=cursor,
            limit=page_size,
        )
        if not items:
            break
        # Prepend items because 'before' walks backwards
        backward_ids = [m["id"] for m in items] + backward_ids
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    assert len(backward_ids) == total_messages, f"Expected {total_messages} messages backward, got {len(backward_ids)}"
    assert len(set(backward_ids)) == total_messages, "Detected duplicates in backward pagination"
    assert backward_ids == forward_ids, "Backward pagination order mismatch"

    # Invalid cursor validation error
    with pytest.raises(ValidationError):
        await repo.get_history(project_id=project_id, user_id=user_id, after="malformed-cursor-string-123")
