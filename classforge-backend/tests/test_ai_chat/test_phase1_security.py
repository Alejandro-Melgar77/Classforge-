import pytest
import asyncio
from unittest.mock import AsyncMock
from mongomock_motor import AsyncMongoMockClient

from app.ai_team.application.triggers import TriggersManager
from app.ai_team.domain.jobs import AiJob
from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.core.errors import ValidationError
from app.modules.collaboration.router import _current_ws_access
from app.core.config import settings
from app.llm.errors import LlmUnavailable
from app.llm.ollama import OllamaProvider
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository


@pytest.mark.anyio
async def test_personal_proposal_cannot_be_changed_by_another_member():
    db = AsyncMongoMockClient().test
    await db.ai_messages.insert_one({'_id': 'm', 'project_id': 'a', 'thread': 'personal',
                                     'owner_id': 'alice', 'proposals': [{'id': 'p'}]})
    result = await AiMessageRepository(db).update_proposal_state('m', 'p', 'dismissed', 'bob', 'a')
    assert result is None
    assert 'proposal_state' not in await db.ai_messages.find_one({'_id': 'm'})


@pytest.mark.anyio
async def test_client_cannot_claim_proposal_was_applied():
    db = AsyncMongoMockClient().test
    await db.ai_messages.insert_one({'_id': 'm', 'project_id': 'a', 'thread': 'personal',
                                     'owner_id': 'alice', 'proposals': [{'id': 'p'}]})
    with pytest.raises(ValidationError):
        await AiMessageRepository(db).update_proposal_state('m', 'p', 'applied', 'alice', 'a')
    assert 'proposal_state' not in await db.ai_messages.find_one({'_id': 'm'})


@pytest.mark.anyio
async def test_job_does_not_persist_supplied_api_key():
    db = AsyncMongoMockClient().test
    triggers = TriggersManager(db)
    with pytest.raises(ValidationError):
        await triggers.on_user_message('a', 'alice', 'm', 'architect', 'hi', api_key='secret-test-key')
    assert await db.ai_jobs.count_documents({}) == 0


@pytest.mark.anyio
async def test_old_worker_cannot_finish_reclaimed_job():
    db = AsyncMongoMockClient().test
    repo = AiJobRepository(db)
    job = AiJob(project_id='a', kind='answer_message')
    await repo.enqueue(job)
    first = await repo.acquire_next('first')
    await db.ai_jobs.update_one({'_id': job.id}, {'$set': {'status': 'queued'}})
    second = await repo.acquire_next('second')
    assert not await repo.complete(job.id, 'first', first.attempts)
    assert not await repo.fail(job.id, 'first', first.attempts, 'old')
    assert await repo.complete(job.id, 'second', second.attempts)


@pytest.mark.anyio
async def test_repository_rejects_nested_credentials():
    db = AsyncMongoMockClient().test
    job = AiJob(project_id='a', kind='answer_message', payload={'provider': {'api_key': 'secret'}})
    with pytest.raises(ValueError):
        await AiJobRepository(db).enqueue(job)
    assert await db.ai_jobs.count_documents({}) == 0


@pytest.mark.anyio
async def test_websocket_access_rechecks_removed_team_member():
    db = AsyncMongoMockClient().test
    await db.users.insert_one({'_id': 'u', 'is_active': True, 'is_deleted': False, 'team_ids': ['t']})
    await db.teams.insert_one({'_id': 't', 'is_deleted': False, 'member_ids': ['u']})
    await db.projects.insert_one({'_id': 'p', 'team_id': 't', 'is_deleted': False})
    await db.diagrams.insert_one({'_id': 'd', 'project_id': 'p', 'is_deleted': False})
    assert await _current_ws_access(db, 'u', 'd', False)
    await db.teams.update_one({'_id': 't'}, {'$set': {'member_ids': []}})
    assert not await _current_ws_access(db, 'u', 'd', False)


@pytest.mark.anyio
async def test_active_dedupe_index_scopes_to_project_and_kind():
    db = AsyncMongoMockClient().test
    await db.ai_jobs.create_index([('project_id', 1), ('kind', 1), ('active_dedupe_key', 1)],
                                  unique=True, partialFilterExpression={'active_dedupe_key': {'$type': 'string'}})
    repo = AiJobRepository(db)
    jobs = [AiJob(project_id='a', kind='answer_message', dedupe_key='same') for _ in range(2)]
    result = await asyncio.gather(*(repo.enqueue(job) for job in jobs))
    assert result[0].id == result[1].id
    assert await db.ai_jobs.count_documents({}) == 1
    await repo.enqueue(AiJob(project_id='b', kind='answer_message', dedupe_key='same'))
    assert await db.ai_jobs.count_documents({}) == 2


@pytest.mark.anyio
async def test_local_mode_rejects_remote_ollama_before_network(monkeypatch):
    monkeypatch.setattr(settings, 'AI_LOCAL_ONLY', True)
    provider = OllamaProvider(base_url='https://example.invalid')
    client = AsyncMock()
    with pytest.raises(LlmUnavailable):
        await provider._post_chat(client, {})
    client.post.assert_not_awaited()
