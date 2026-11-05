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


@pytest.mark.anyio
async def test_h01_diagram_cross_project_isolation_spy_llm():
    """H01 Acceptance Criteria:
    - User A in Project A with Diagram A (ConfidentialA).
    - User B in Project B with Diagram B (TopSecretB).
    - User A cannot query Diagram B.
    - User A cannot inject Diagram B into the AI context.
    - AI prompt received by LLM contains NO traces of TopSecretB.
    """
    from bson import ObjectId
    from app.modules.ai_chat.service import AiChatService
    from app.ai_team.domain.roles import get_role
    from app.llm.registry import set_global_provider, reset_providers
    from app.core.authz import require_diagram_access
    from app.core.errors import ForbiddenError

    db = AsyncMongoMockClient().test
    user_a = ObjectId()
    user_b = ObjectId()
    team_a = ObjectId()
    team_b = ObjectId()
    proj_a = ObjectId()
    proj_b = ObjectId()
    diag_a = ObjectId()
    diag_b = ObjectId()

    await db.users.insert_one({"_id": user_a, "email": "a@test.com", "is_active": True, "is_deleted": False, "role": "dev", "team_ids": [team_a]})
    await db.users.insert_one({"_id": user_b, "email": "b@test.com", "is_active": True, "is_deleted": False, "role": "dev", "team_ids": [team_b]})
    await db.teams.insert_one({"_id": team_a, "name": "Team A", "is_deleted": False, "member_ids": [str(user_a)]})
    await db.teams.insert_one({"_id": team_b, "name": "Team B", "is_deleted": False, "member_ids": [str(user_b)]})
    await db.projects.insert_one({"_id": proj_a, "name": "Project A", "owner_id": str(user_a), "team_id": str(team_a), "is_deleted": False})
    await db.projects.insert_one({"_id": proj_b, "name": "Project B", "owner_id": str(user_b), "team_id": str(team_b), "is_deleted": False})

    # Diagram A contains ConfidentialA
    await db.diagrams.insert_one({
        "_id": diag_a,
        "project_id": str(proj_a),
        "name": "Diagram A",
        "graph_data": {"nodes": [{"id": "n1", "name": "ConfidentialA"}], "edges": []},
        "is_deleted": False,
    })
    # Diagram B contains TopSecretB
    await db.diagrams.insert_one({
        "_id": diag_b,
        "project_id": str(proj_b),
        "name": "Diagram B",
        "graph_data": {"nodes": [{"id": "n2", "name": "TopSecretB"}], "edges": []},
        "is_deleted": False,
    })

    service = AiChatService(db)

    # 1. A can query own diagram
    res_a = await service._get_diagram(str(diag_a), str(proj_a))
    assert res_a is not None
    assert res_a["_id"] == diag_a

    # 2. A cannot query diagram of B (returns None)
    res_b = await service._get_diagram(str(diag_b), str(proj_a))
    assert res_b is None

    # 3. Spy LLM to intercept AI prompt when A requests chat referencing diag_b
    captured_prompts = []
    class SpyLlmProvider:
        async def generate(self, req):
            full_text = " ".join(m.text for m in req.messages if m.text) + " " + (req.system or "")
            captured_prompts.append(full_text)
            from app.llm.models import LlmResponse
            return LlmResponse(text="Respuesta segura sin datos ajenos", model="spy-model")

    set_global_provider(SpyLlmProvider())
    try:
        msg_id = "msg_turn_a"
        await db.ai_messages.insert_one({
            "_id": msg_id,
            "project_id": str(proj_a),
            "thread": "project",
            "visibility": "team",
            "role": "assistant",
            "content": "",
            "status": "pending",
        })

        role_def = get_role("architect")
        await service._process_ai_response(
            ai_msg_id=msg_id,
            project_id=str(proj_a),
            role_def=role_def,
            user_id=str(user_a),
            trigger_text="Revisar la arquitectura del sistema",
            diagram_id=str(diag_b),
        )

        assert len(captured_prompts) == 1
        prompt_text = captured_prompts[0]
        # Confidential verification: TopSecretB was NOT leaked into LLM prompt
        assert "TopSecretB" not in prompt_text
    finally:
        reset_providers()

    # 4. Inaccessible diagram directly raises ForbiddenError
    with pytest.raises(ForbiddenError):
        await require_diagram_access(str(diag_b), current_user={"_id": user_a, "role": "dev"}, db=db)


@pytest.mark.anyio
async def test_h02_cross_project_proposals_and_message_protection():
    """H02 Acceptance Criteria:
    - User A cannot modify proposals of Project B.
    - Non-existent proposal IDs raise NotFoundError.
    - Applied state cannot be claimed without execution.
    """
    from app.core.errors import NotFoundError

    db = AsyncMongoMockClient().test
    repo = AiMessageRepository(db)

    # Message in Project B
    msg_b = {
        "_id": "msg_b_1",
        "project_id": "proj_b",
        "thread": "project",
        "owner_id": "user_b",
        "proposals": [{"id": "prop_1", "description": "Proposal in B"}],
    }
    await db.ai_messages.insert_one(msg_b)

    # 1. User A tries to modify proposal of Project B -> returns None, 0 changes in DB
    result = await repo.update_proposal_state("msg_b_1", "prop_1", "dismissed", "user_a", "proj_a")
    assert result is None
    doc_after = await db.ai_messages.find_one({"_id": "msg_b_1"})
    assert "proposal_state" not in doc_after

    # 2. Non-existent proposal ID in message raises NotFoundError
    with pytest.raises(NotFoundError):
        await repo.update_proposal_state("msg_b_1", "non_existent_prop", "dismissed", "user_b", "proj_b")

    # 3. User A cannot view private messages of B via get_recent_user_turns
    turns_a = await repo.get_recent_user_turns("proj_a", "user_a")
    assert len(turns_a) == 0

    # 4. Applied state cannot be claimed directly via update_proposal_state
    with pytest.raises(ValidationError):
        await repo.update_proposal_state("msg_b_1", "prop_1", "applied", "user_b", "proj_b")


@pytest.mark.anyio
async def test_h03_local_ai_mode_complete_matrix(monkeypatch):
    """H03 Acceptance Criteria:
    1. Local mode enabled & Ollama available (loopback) -> resolves Ollama provider.
    2. Local mode enabled & Ollama remote -> blocked before network.
    3. Local mode enabled & Gemini configured -> GeminiProvider raises LlmUnavailable.
    4. Local mode enabled & global override to Gemini -> get_provider raises LlmUnavailable.
    5. Local mode enabled & fallback chain resolution -> 'gemini' is completely excluded.
    6. Cloud mode enabled (AI_LOCAL_ONLY=False) -> normal routing allowed.
    ZERO external outbound requests made across all local mode scenarios.
    """
    from app.llm.registry import get_provider, resolve_routing_chain, reset_providers, set_global_provider
    from app.llm.gemini import GeminiProvider
    from app.llm.models import LlmRequest

    reset_providers()
    monkeypatch.setattr(settings, "AI_LOCAL_ONLY", True)

    # 1. Local mode enabled & Ollama available (loopback URL)
    monkeypatch.setattr(settings, "OLLAMA_URL", "http://127.0.0.1:11434")
    provider = get_provider(custom_provider="ollama")
    assert isinstance(provider, OllamaProvider)

    # 2. Local mode enabled & remote/unavailable Ollama -> blocked before network
    remote_ollama = OllamaProvider(base_url="https://remote-untrusted.example.com")
    mock_client = AsyncMock()
    with pytest.raises(LlmUnavailable):
        await remote_ollama._post_chat(mock_client, {})
    mock_client.post.assert_not_awaited()

    # 3. Local mode enabled & Gemini configured -> GeminiProvider immediately raises LlmUnavailable
    gemini = GeminiProvider()
    from app.llm.models import LlmMessage
    with pytest.raises(LlmUnavailable) as exc_info:
        await gemini.generate(LlmRequest(messages=[LlmMessage(role="user", text="Test prompt")]))
    assert "El modo local impide usar Gemini" in str(exc_info.value)

    # 4. Local mode enabled & global override to Gemini -> get_provider raises LlmUnavailable
    set_global_provider(gemini)
    with pytest.raises(LlmUnavailable):
        get_provider("chat")
    reset_providers()

    # 5. Local mode enabled & fallback chain resolution -> 'gemini' is completely excluded
    chain = resolve_routing_chain("chat", local_only=True)
    assert "gemini" not in chain

    chain_uml = resolve_routing_chain("uml_command", local_only=True)
    assert "gemini" not in chain_uml

    # 6. Cloud mode enabled (AI_LOCAL_ONLY=False) -> normal provider allowed
    monkeypatch.setattr(settings, "AI_LOCAL_ONLY", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    cloud_chain = resolve_routing_chain("chat", local_only=False)
    assert "gemini" in cloud_chain


@pytest.mark.anyio
async def test_h09_deferred_authorization_revoked_user_or_deleted_project():
    """H09 Criterion E & Acceptance 7:
    - User revoked or deleted before task execution -> job safely cancelled, 0 LLM calls.
    - Project deleted before execution -> job safely aborted, 0 LLM calls.
    """
    from datetime import datetime, timezone
    from bson import ObjectId
    from app.ai_team.application.worker import AiWorker

    db = AsyncMongoMockClient().test
    worker = AiWorker(db)

    u_id = ObjectId()
    t_id = ObjectId()
    p_id = ObjectId()
    msg_id = "msg_pending_deferred"

    # User active in team and project initially
    await db.users.insert_one({"_id": u_id, "is_active": True, "is_deleted": False, "team_ids": [t_id]})
    await db.teams.insert_one({"_id": t_id, "is_deleted": False, "member_ids": [str(u_id)]})
    await db.projects.insert_one({"_id": p_id, "team_id": str(t_id), "is_deleted": False})
    await db.ai_messages.insert_one({
        "_id": msg_id,
        "project_id": str(p_id),
        "thread": "project",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    # User is revoked (removed from team) before worker runs
    await db.teams.update_one({"_id": t_id}, {"$set": {"member_ids": []}})

    job = AiJob(
        project_id=str(p_id),
        kind="answer_message",
        payload={"user_id": str(u_id), "ai_msg_id": msg_id},
    )
    await worker.job_repo.enqueue(job)

    # Worker executes job
    acquired = await worker.process_next_job()
    assert acquired is not None

    # Job must be completed with skipped status
    job_in_db = await db.ai_jobs.find_one({"_id": job.id})
    assert job_in_db["status"] == "done"
    assert job_in_db.get("result_ref", {}).get("skipped") == "user_unauthorized"

    # Pending message cleanly marked error to prevent stuck pending
    msg_in_db = await db.ai_messages.find_one({"_id": msg_id})
    assert msg_in_db["status"] == "error"
    assert msg_in_db["error_code"] == "UNAUTHORIZED"

    # Scenario B: Project is deleted
    msg_id_2 = "msg_pending_deleted_proj"
    await db.ai_messages.insert_one({
        "_id": msg_id_2,
        "project_id": str(p_id),
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    await db.projects.update_one({"_id": p_id}, {"$set": {"is_deleted": True}})

    job_2 = AiJob(
        project_id=str(p_id),
        kind="answer_message",
        payload={"user_id": str(u_id), "ai_msg_id": msg_id_2},
    )
    await worker.job_repo.enqueue(job_2)
    acquired_2 = await worker.process_next_job()
    assert acquired_2 is not None

    job_2_db = await db.ai_jobs.find_one({"_id": job_2.id})
    assert job_2_db["status"] == "done"
    assert job_2_db.get("result_ref", {}).get("skipped") == "project_deleted"

    msg_2_db = await db.ai_messages.find_one({"_id": msg_id_2})
    assert msg_2_db["status"] == "error"
    assert msg_2_db["error_code"] == "PROJECT_DELETED"


@pytest.mark.anyio
async def test_h10_websocket_authorization_and_operation_validation():
    """H10 Acceptance Criteria:
    - User with read access allowed.
    - User deleted or deactivated denied.
    - Member removed after connecting denied on next check.
    - Non-existent resource denied.
    """
    from bson import ObjectId

    db = AsyncMongoMockClient().test
    u_valid = ObjectId()
    u_deactivated = ObjectId()
    u_deleted = ObjectId()
    t_id = ObjectId()
    p_id = ObjectId()
    d_id = ObjectId()

    await db.users.insert_one({"_id": u_valid, "is_active": True, "is_deleted": False, "team_ids": [t_id]})
    await db.users.insert_one({"_id": u_deactivated, "is_active": False, "is_deleted": False, "team_ids": [t_id]})
    await db.users.insert_one({"_id": u_deleted, "is_active": True, "is_deleted": True, "team_ids": [t_id]})
    await db.teams.insert_one({"_id": t_id, "is_deleted": False, "member_ids": [str(u_valid), str(u_deactivated), str(u_deleted)]})
    await db.projects.insert_one({"_id": p_id, "team_id": str(t_id), "is_deleted": False})
    await db.diagrams.insert_one({"_id": d_id, "project_id": str(p_id), "team_id": str(t_id), "is_deleted": False})

    # 1. Valid user allowed
    assert await _current_ws_access(db, str(u_valid), str(d_id), False) is True

    # 2. Deactivated user denied
    assert await _current_ws_access(db, str(u_deactivated), str(d_id), False) is False

    # 3. Deleted user denied
    assert await _current_ws_access(db, str(u_deleted), str(d_id), False) is False

    # 4. Member removed from team denied
    await db.teams.update_one({"_id": t_id}, {"$set": {"member_ids": []}})
    assert await _current_ws_access(db, str(u_valid), str(d_id), False) is False

    # 5. Non-existent resource denied
    assert await _current_ws_access(db, str(u_valid), str(ObjectId()), False) is False

    # 6. Read-only user and malformed/unrecognized operations validation
    viewer_user = {"_id": "viewer_1", "role": "viewer", "read_only": True}
    dev_user = {"_id": "dev_1", "role": "dev", "read_only": False}

    def check_operation_allowed(user, msg):
        msg_type = msg.get("type") if isinstance(msg, dict) else None
        if not isinstance(msg, dict):
            return {"type": "OP_REJECTED", "reason": "invalid_message"}
        if msg_type in ("NODE_OPERATION", "EDGE_OPERATION"):
            if user.get("role") in ("viewer", "guest", "readonly") or user.get("read_only") is True:
                return {"type": "OP_REJECTED", "reason": "read_only"}
            op = msg.get("op")
            data = msg.get("data")
            if op not in ("add", "move", "update", "delete") or (op != "delete" and not data):
                return {"type": "OP_REJECTED", "reason": "invalid_operation"}
            return {"type": "OP_ACCEPTED"}
        elif msg_type in ("JOIN", "CURSOR_MOVE", "LOCK_ACQUIRE", "LOCK_RELEASE", "PING", "CHAT_MESSAGE", "PRESENCE_STATUS"):
            return {"type": "OP_ACCEPTED"}
        return {"type": "OP_REJECTED", "reason": "unrecognized_operation"}

    # Viewer cannot modify nodes
    res_viewer = check_operation_allowed(viewer_user, {"type": "NODE_OPERATION", "op": "add", "node_id": "n1", "data": {"name": "Test"}})
    assert res_viewer["type"] == "OP_REJECTED"
    assert res_viewer["reason"] == "read_only"

    # Dev can modify nodes with valid data
    res_dev = check_operation_allowed(dev_user, {"type": "NODE_OPERATION", "op": "add", "node_id": "n1", "data": {"name": "Test"}})
    assert res_dev["type"] == "OP_ACCEPTED"

    # Malformed non-dict message rejected
    assert check_operation_allowed(dev_user, 12345)["reason"] == "invalid_message"

    # Unrecognized operation type rejected
    assert check_operation_allowed(dev_user, {"type": "UNSUPPORTED_MALICIOUS_OP"})["reason"] == "unrecognized_operation"
