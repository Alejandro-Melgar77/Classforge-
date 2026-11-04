import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from mongomock_motor import AsyncMongoMockClient
from app.ai_team.application.worker import AiWorker
from app.ai_team.domain.jobs import AiJob
from app.ai_team.infrastructure.job_repository import AiJobRepository


@pytest.mark.anyio
async def test_lease_is_not_acquired_before_worker_capacity():
    db = AsyncMongoMockClient().test
    worker = AiWorker(db, concurrency=1, poll_interval=0.01)
    first = AiJob(project_id='p', kind='answer_message')
    executing = asyncio.Event()
    release = asyncio.Event()

    async def execute(job):
        executing.set()
        await release.wait()

    acquire = AsyncMock(side_effect=[first, None, None])
    with patch.object(worker.job_repo, 'acquire_next', acquire), patch.object(worker, '_execute_job', execute):
        worker.start()
        await asyncio.wait_for(executing.wait(), timeout=1)
        await asyncio.sleep(0.05)
        assert acquire.await_count == 1
        release.set()
        await asyncio.sleep(0.03)
        await worker.stop()


@pytest.mark.anyio
async def test_reaper_does_not_overwrite_renewed_lease():
    db = AsyncMongoMockClient().test
    now = datetime.now(timezone.utc)
    repo = AiJobRepository(db, clock=lambda: now)
    await db.ai_jobs.insert_one({'_id': 'j', 'status': 'running', 'attempts': 1,
                                'lease_until': now - timedelta(seconds=1)})
    original_update = repo.col.update_one

    async def renew_before_update(query, update):
        await original_update({'_id': 'j'}, {'$set': {'lease_until': now + timedelta(minutes=1)}})
        return await original_update(query, update)

    with patch.object(repo.col, 'update_one', side_effect=renew_before_update):
        assert await repo.reap_expired_leases() == 0
    assert (await db.ai_jobs.find_one({'_id': 'j'}))['status'] == 'running'
