import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.ai_team.infrastructure.job_repository import AiJobRepository
from app.ai_team.domain.jobs import AiJob, JobStatus
from app.modules.collaboration.connection_manager import ConnectionManager
from app.modules.diagrams.service import DiagramService
from app.core.errors import NotFoundError, ConflictError


@pytest.mark.anyio
async def test_ai_worker_lease_and_reaper():
    """Verify worker lease timeout and reaper mechanics (REL-01)."""
    db = AsyncMongoMockClient().test_db
    repo = AiJobRepository(db)

    job_id = f"job-{ObjectId()}"
    now = datetime.now(timezone.utc)

    # Insert a job
    job = AiJob(
        id=job_id,
        project_id="proj-1",
        kind="answer_message",
        payload={"message": "Analyze system architecture"},
        status="queued",
        created_at=now,
        updated_at=now
    )
    await repo.enqueue(job)

    # Worker 1 acquires lease for 5 seconds
    acquired_job = await repo.acquire_next("worker-1", lease_seconds=5)
    assert acquired_job is not None
    assert acquired_job.id == job_id
    assert acquired_job.status == "running"

    # Worker 2 tries to acquire immediately; should get None since lease is active
    none_job = await repo.acquire_next("worker-2", lease_seconds=5)
    assert none_job is None

    # Simulate lease expiration in the database
    past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    await db["ai_jobs"].update_one(
        {"_id": job_id},
        {"$set": {"lease_until": past_time}}
    )

    # Run reaper
    reaped = await repo.reap_expired_leases()
    assert reaped >= 1

    # Reset backoff run_after to current time for immediate pick-up in test
    await db["ai_jobs"].update_one(
        {"_id": job_id},
        {"$set": {"run_after": datetime.now(timezone.utc) - timedelta(seconds=1)}}
    )

    # Worker 2 should now be able to acquire the recovered job
    recovered_job = await repo.acquire_next("worker-2", lease_seconds=10)
    assert recovered_job is not None
    assert recovered_job.id == job_id


@pytest.mark.anyio
async def test_diagram_element_lock_concurrency():
    """Verify collaborative element lock acquisition, contention, and release (REL-01)."""
    manager = ConnectionManager()
    diagram_id = "diagram-abc"
    element_id = "class-node-order"

    user_a = "user-alice"
    user_b = "user-bob"

    # User A acquires lock
    locked_a = manager.acquire_lock(diagram_id, user_a, element_id)
    assert locked_a is True

    # User B tries to lock the same element; must be rejected
    locked_b = manager.acquire_lock(diagram_id, user_b, element_id)
    assert locked_b is False

    # Check lock owner
    owner = manager.get_lock_owner(diagram_id, element_id)
    assert owner == user_a

    # User A releases lock
    released = manager.release_lock(diagram_id, user_a, element_id)
    assert released is True

    # Now User B can acquire the lock
    locked_b_after = manager.acquire_lock(diagram_id, user_b, element_id)
    assert locked_b_after is True
    assert manager.get_lock_owner(diagram_id, element_id) == user_b

    # Cleanup all user locks on disconnect
    manager.release_all_user_locks(diagram_id, user_b)
    assert manager.get_lock_owner(diagram_id, element_id) is None


@pytest.mark.anyio
async def test_diagram_version_increment_and_persistence():
    """Verify atomic version increment when saving diagram states (REL-01)."""
    db = AsyncMongoMockClient().test_db
    service = DiagramService(db)

    user_id = str(ObjectId())
    project_id = str(ObjectId())
    diag_id = str(ObjectId())

    # Create diagram at version 1
    await db.diagrams.insert_one({
        "_id": ObjectId(diag_id),
        "project_id": project_id,
        "name": "E-Commerce UML Model",
        "description": "Initial design",
        "version": 1,
        "graph_data": {"nodes": [{"id": "User", "type": "class"}], "edges": []},
        "created_by": user_id,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })

    # Save new version 2
    new_graph = {
        "nodes": [
            {"id": "User", "type": "class"},
            {"id": "Order", "type": "class"}
        ],
        "edges": [
            {"id": "rel-1", "source": "User", "target": "Order", "type": "association"}
        ]
    }

    from app.modules.diagrams.schemas import SaveGraph

    # Save new version 2 with correct base_version=1
    user_context = {"_id": ObjectId(user_id), "role": "admin"}
    save_data = SaveGraph(
        graph_data=new_graph,
        comment="Added Order class and association",
        base_version=1
    )

    result = await service.save_graph(
        diagram_id=diag_id,
        data=save_data,
        user=user_context
    )

    assert result is not None
    assert result.get("version") == 2

    # Attempting to save again with stale base_version=1 must fail with ConflictError
    stale_save = SaveGraph(
        graph_data=new_graph,
        comment="Stale update attempt",
        base_version=1
    )
    with pytest.raises(ConflictError, match="diagrama cambió"):
        await service.save_graph(
            diagram_id=diag_id,
            data=stale_save,
            user=user_context
        )

    # Verify database state in collection
    updated_doc = await db.diagrams.find_one({"_id": ObjectId(diag_id)})
    assert updated_doc["version"] == 2
    assert len(updated_doc["graph_data"]["nodes"]) == 2
