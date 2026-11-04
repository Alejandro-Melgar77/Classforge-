import pytest
from bson import ObjectId
from unittest.mock import AsyncMock, patch
from mongomock_motor import AsyncMongoMockClient

from app.modules.ai_chat.context_builder import ProjectContextBuilder
from app.modules.ai_chat.service import AiChatService
from app.modules.collaboration.service import verify_ws_token


@pytest.mark.anyio
async def test_context_builder_excludes_foreign_diagram():
    db = AsyncMongoMockClient().test
    project, other, diagram = ObjectId(), ObjectId(), ObjectId()
    await db.diagrams.insert_one({'_id': diagram, 'project_id': other, 'name': 'CONFIDENTIAL', 'is_deleted': False})
    context = await ProjectContextBuilder().build(db, str(project), str(diagram))
    assert 'CONFIDENTIAL' not in context


@pytest.mark.anyio
async def test_inactive_user_cannot_use_diagram_token():
    db = AsyncMongoMockClient().test
    user, diagram = ObjectId(), ObjectId()
    await db.users.insert_one({'_id': user, 'is_deleted': False, 'is_active': False})
    await db.ws_tokens.insert_one({'token': 'test', 'diagram_id': diagram, 'user_id': user})
    with patch('app.modules.collaboration.service._get_db', return_value=db):
        assert await verify_ws_token(str(diagram), 'test') is None


@pytest.mark.anyio
async def test_retry_uses_durable_job():
    db = AsyncMongoMockClient().test
    await db.ai_messages.insert_one({'_id': 'm', 'project_id': 'p', 'status': 'error', 'ai_role': 'architect'})
    service = AiChatService(db)
    enqueue = AsyncMock(return_value=object())
    with patch.object(service.triggers, 'on_user_message', enqueue), patch('app.modules.ai_chat.service.manager.broadcast', new=AsyncMock()):
        await service.retry_ai_message('m', 'p', {'_id': ObjectId()})
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs['ai_msg_id'] == 'm'
    assert (await db.ai_messages.find_one({'_id': 'm'}))['status'] == 'pending'
