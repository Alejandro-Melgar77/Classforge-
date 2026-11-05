import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.ai_team.domain.jobs import AiJob
from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.ai_team.application.worker import AiWorker
from app.modules.ai_chat.service import AiChatService


@pytest.mark.anyio
async def test_job_lease_renewal_and_reaping():
    db = AsyncMongoMockClient().test
    repo = AiJobRepository(db)

    # 1. Enqueue job
    job = AiJob(
        project_id="p1",
        kind="run_task",
        payload={"action": "analyze"},
        dedupe_key="dedupe_123"
    )
    enqueued = await repo.enqueue(job)
    assert enqueued is not None
    job_id = enqueued.id

    # 2. Acquire lease
    worker_1 = "worker_alpha"
    acquired = await repo.acquire_next(worker_1, lease_seconds=60)
    assert acquired is not None
    assert acquired.id == job_id
    assert acquired.status == "running"
    initial_lease_expiry = acquired.lease_until

    # 3. Renew lease with correct worker
    renewed = await repo.renew_lease(job_id, worker_1, attempts=acquired.attempts, additional_seconds=180)
    assert renewed is True

    updated_job_doc = await db.ai_jobs.find_one({"_id": job_id})
    expiry_in_doc = updated_job_doc["lease_until"]
    if expiry_in_doc.tzinfo is None and initial_lease_expiry.tzinfo is not None:
        expiry_in_doc = expiry_in_doc.replace(tzinfo=timezone.utc)
    assert expiry_in_doc > initial_lease_expiry

    # 4. Attempt to renew lease with wrong worker fails
    wrong_renew = await repo.renew_lease(job_id, "worker_beta", attempts=acquired.attempts, additional_seconds=180)
    assert wrong_renew is False

    # 5. Simulate expired lease and reap it
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db.ai_jobs.update_one({"_id": job_id}, {"$set": {"lease_until": past_time}})

    reaped_count = await repo.reap_expired_leases()
    assert reaped_count >= 1

    reaped_doc = await db.ai_jobs.find_one({"_id": job_id})
    assert reaped_doc["status"] == "queued"
    assert reaped_doc.get("lease_until") is None


@pytest.mark.anyio
async def test_job_deduplication():
    db = AsyncMongoMockClient().test
    repo = AiJobRepository(db)

    job1 = AiJob(
        project_id="p1",
        kind="run_task",
        payload={"data": 1},
        dedupe_key="unique_analysis_key"
    )
    enqueued1 = await repo.enqueue(job1)
    assert enqueued1 is not None

    # Second enqueue with same active dedupe key returns the existing job without inserting another
    job2 = AiJob(
        project_id="p1",
        kind="run_task",
        payload={"data": 2},
        dedupe_key="unique_analysis_key"
    )
    enqueued2 = await repo.enqueue(job2)
    assert enqueued2 is not None
    assert enqueued2.id == enqueued1.id

    total_jobs = await db.ai_jobs.count_documents({"dedupe_key": "unique_analysis_key"})
    assert total_jobs == 1


@pytest.mark.anyio
async def test_worker_cleans_pending_message_when_autonomy_disabled(monkeypatch):
    """
    Verifies that when AI_AUTONOMY_ENABLED=False, jobs do not leave orphaned
    messages in 'pending' status. Instead, the pending message is cleanly
    transitioned to status='error' with error_code='AUTONOMY_DISABLED'.
    """
    db = AsyncMongoMockClient().test
    worker = AiWorker(db)

    # Create a pending AI message in db
    msg_id = "msg_pending_autonomy_test"
    await db.ai_messages.insert_one({
        "_id": msg_id,
        "project_id": "proj_1",
        "thread": "project",
        "visibility": "team",
        "role": "assistant",
        "content": "",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    # Prepare job
    job = AiJob(
        project_id="proj_1",
        kind="run_task",
        payload={"task_id": "task_1", "ai_msg_id": msg_id},
    )

    # Disable autonomy in settings
    from app.core.config import settings
    monkeypatch.setattr(settings, "AI_AUTONOMY_ENABLED", False)

    # Execute job
    await worker._execute_job(job)

    # Confirm the message is no longer stuck in 'pending'
    msg = await db.ai_messages.find_one({"_id": msg_id})
    assert msg is not None
    assert msg["status"] == "error", f"Message should be in error status, got {msg['status']}"
    assert msg.get("error_code") == "AUTONOMY_DISABLED"


@pytest.mark.anyio
async def test_task_cancellation_and_job_abort():
    """
    Verifies that cancelling a task cancels the task and its queued job,
    preventing unintended async execution.
    """
    db = AsyncMongoMockClient().test
    job_repo = AiJobRepository(db)
    chat_service = AiChatService(db)

    project_id = str(ObjectId())
    user_id = str(ObjectId())
    task_id = str(ObjectId())

    user_oid = ObjectId(user_id)
    current_user = {"_id": user_oid, "role": "dev"}

    # Create task in database
    await db.ai_tasks.insert_one({
        "_id": ObjectId(task_id),
        "project_id": ObjectId(project_id),
        "creator_id": user_oid,
        "assigned_by": user_oid,
        "ai_role": "software_architect",
        "title": "Build Architecture Plan",
        "description": "Create detailed diagram and services",
        "status": "queued",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # Enqueue corresponding worker job
    job = AiJob(
        project_id=project_id,
        kind="run_task",
        payload={"task_id": task_id},
        dedupe_key=f"task_{task_id}"
    )
    enqueued_job = await job_repo.enqueue(job)
    assert enqueued_job is not None

    # Cancel task via service
    res = await chat_service.cancel_task(task_id=task_id, project_id=project_id, current_user=current_user)
    assert res["success"] is True
    assert res["task"]["status"] == "cancelled"

    # Verify task in db
    task = await db.ai_tasks.find_one({"_id": ObjectId(task_id)})
    assert task["status"] == "cancelled"

    # Verify job in db was cancelled
    job_doc = await db.ai_jobs.find_one({"payload.task_id": task_id})
    assert job_doc is not None
    assert job_doc["status"] == "cancelled"
