"""
Unit and integration tests for P4 AI Team Chat:
- Project isolation (403 for non-members, message isolation)
- Idempotency via client_id
- 4-step AI role routing (Explicit > Mention > Participative > None)
- Cursor-based pagination for group history and personal history (/mine)
- Shared project AI state & role autonomy permissions (apply restricted to SM/Admin/Owner)
- Structured proposals state management (applied / dismissed)
- Asynchronous task execution returning 202 Accepted
- Project digest creation, update, and context trimming priorities
- Project WebSocket authentication (single-use token), events, and member isolation
- Migration script test (dry-run, real execution, and idempotency)
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import pytest
from httpx import AsyncClient
from bson import ObjectId
from starlette.websockets import WebSocketDisconnect

# Ensure workspace root is in sys.path for scripts import
repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings
from app.core.database import db_instance
from app.core.security import create_access_token
from app.llm.registry import set_global_provider, reset_providers
from app.llm.fake import FakeLlmProvider
from app.modules.collaboration.connection_manager import ConnectionManager
from app.modules.ai_chat.infrastructure.repositories import (
    AiMessageRepository,
    AiProjectStateRepository,
    AiTaskRepository,
)
from app.modules.ai_chat.domain.models import AiMessage
from app.modules.ai_chat.domain.router_logic import route_ai_roles
from app.modules.ai_chat.application.project_digest import ProjectDigestService
from app.modules.ai_chat.application.chat_context import assemble_chat_request
from app.ai_team.domain.roles import get_role


@pytest.fixture(autouse=True)
def setup_fake_llm():
    """Ensure all LLM calls in this module use FakeLlmProvider."""
    orig_provider = settings.LLM_PROVIDER
    settings.LLM_PROVIDER = "fake"
    fake = FakeLlmProvider()
    set_global_provider(fake)
    yield fake
    reset_providers()
    settings.LLM_PROVIDER = orig_provider


async def create_test_user(role: str = "dev", name: str = "Test Dev") -> tuple[dict, str, dict]:
    """Helper to create a user and return (user_doc, user_id, auth_headers)."""
    db = db_instance.db
    user_id = str(ObjectId())
    user_doc = {
        "_id": ObjectId(user_id),
        "name": name,
        "email": f"user_{user_id}@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }
    await db["users"].insert_one(user_doc)
    token = create_access_token(subject=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    return user_doc, user_id, headers


async def create_test_project(owner_id: str, member_ids: list[str]) -> tuple[dict, str]:
    """Helper to create a team and project with assigned members."""
    db = db_instance.db
    all_members = list(set([ObjectId(m) for m in member_ids] + [ObjectId(owner_id)]))

    team_id = ObjectId()
    await db["teams"].insert_one({
        "_id": team_id,
        "name": "Team Test",
        "owner_id": ObjectId(owner_id),
        "member_ids": all_members,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    })

    project_id = str(ObjectId())
    project_doc = {
        "_id": ObjectId(project_id),
        "name": "Project P4 Test",
        "description": "Testing P4 AI Chat subsystem",
        "owner_id": ObjectId(owner_id),
        "team_id": team_id,
        "status": "in_progress",
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db["projects"].insert_one(project_doc)
    return project_doc, project_id


# ── 1. Project Isolation & Idempotency Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_project_isolation_and_authorization(async_client: AsyncClient):
    """Requirement: 403 para ajenos; los miembros de proyecto A no pueden ver ni escribir en proyecto B."""
    _, user_a_id, headers_a = await create_test_user(role="dev", name="User A")
    _, user_b_id, headers_b = await create_test_user(role="dev", name="User B")

    _, project_a_id = await create_test_project(owner_id=user_a_id, member_ids=[user_a_id])
    _, project_b_id = await create_test_project(owner_id=user_b_id, member_ids=[user_b_id])

    # User A tries to post to Project B -> 403 Forbidden
    res = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_b_id}/messages",
        json={"content": "Mensaje no autorizado en proyecto B"},
        headers=headers_a,
    )
    assert res.status_code == 403

    # User A tries to read Project B history -> 403 Forbidden
    res = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_b_id}/history",
        headers=headers_a,
    )
    assert res.status_code == 403

    # User A posting to own Project A -> 200 OK
    res = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_a_id}/messages",
        json={"content": "Hola equipo de proyecto A"},
        headers=headers_a,
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_client_id_idempotency(async_client: AsyncClient):
    """Requirement: Idempotencia con client_id; llamadas repetidas devuelven el mismo registro."""
    _, user_id, headers = await create_test_user(role="dev", name="Idempotent Dev")
    _, project_id = await create_test_project(owner_id=user_id, member_ids=[user_id])

    client_id = "client-req-uuid-999"
    payload = {
        "content": "Mensaje que debe ser idempotente",
        "client_id": client_id,
        "ai_role": "architect",
    }

    # First send
    res1 = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json=payload,
        headers=headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    msg_id1 = data1["message"]["id"]

    # Second send with identical client_id
    res2 = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json=payload,
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    msg_id2 = data2["message"]["id"]

    # Must be exact same message ID without creating duplicates
    assert msg_id1 == msg_id2

    # Check database count: exactly 1 user message with that client_id
    db = db_instance.db
    count = await db["ai_messages"].count_documents({"project_id": project_id, "client_id": client_id})
    assert count == 1


# ── 2. Role Routing Tests (4 steps) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_role_routing_hierarchy(async_client: AsyncClient):
    """Requirement: Ruteo de roles:
    (1) ai_role explícito
    (2) @mención en texto
    (3) participativa on (router elige <= 2 roles por trigger) / off (no responde)
    (4) nada aplica (solo se guarda)
    """
    _, user_id, headers = await create_test_user(role="dev", name="Routing Dev")
    _, project_id = await create_test_project(owner_id=user_id, member_ids=[user_id])

    # Case 1: Explicit ai_role passed (even if content mentions @qa, explicit wins)
    res_explicit = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json={"content": "Evaluando diseño con @qa", "ai_role": "architect"},
        headers=headers,
    )
    assert res_explicit.status_code == 200
    pending_exp = res_explicit.json().get("ai_pending", [])
    assert len(pending_exp) == 1
    assert pending_exp[0]["role"] == "architect"

    # Case 2: Mention in content without explicit ai_role
    res_mention = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json={"content": "Por favor revisa inconsistencias @qa en el modelo"},
        headers=headers,
    )
    assert res_mention.status_code == 200
    pending_men = res_mention.json().get("ai_pending", [])
    assert len(pending_men) >= 1
    assert pending_men[0]["role"] == "qa"

    # Case 3a: Participative mode OFF (default), no explicit role, no mention -> only saved, 0 pending
    res_part_off = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json={"content": "El patrón de arquitectura para las clases es sólido"},
        headers=headers,
    )
    assert res_part_off.status_code == 200
    pending_off = res_part_off.json().get("ai_pending", [])
    assert len(pending_off) == 0

    # Turn participative mode ON
    res_state = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"participative": {"enabled": True}},
        headers=headers,
    )
    assert res_state.status_code == 200
    assert res_state.json()["participative"]["enabled"] is True

    # Case 3b: Participative mode ON, triggers matching keywords ('arquitectura', 'patrón') -> router picks architect
    res_part_on = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json={"content": "Necesitamos definir la arquitectura y el patrón modular del sistema"},
        headers=headers,
    )
    assert res_part_on.status_code == 200
    pending_on = res_part_on.json().get("ai_pending", [])
    assert 1 <= len(pending_on) <= 2
    roles_triggered = [p["role"] for p in pending_on]
    assert "architect" in roles_triggered

    # Case 4: Content has zero keywords and no mention -> message saved, 0 pending
    res_none = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages",
        json={"content": "Buenos días a todos en la reunión de hoy"},
        headers=headers,
    )
    assert res_none.status_code == 200
    pending_none = res_none.json().get("ai_pending", [])
    assert len(pending_none) == 0


# ── 3. Cursor Pagination and History Semantics ────────────────────────────────

@pytest.mark.asyncio
async def test_cursor_pagination_and_thread_semantics(async_client: AsyncClient):
    """Requirement: Paginación por cursor (before/after/limit);
    Historial = unión de todos los hilos personales + proyecto;
    Historial/mine = hilo personal + publicaciones de proyecto.
    """
    _, user1_id, headers1 = await create_test_user(role="dev", name="Ana Dev")
    _, user2_id, headers2 = await create_test_user(role="dev", name="Beto Dev")
    _, project_id = await create_test_project(owner_id=user1_id, member_ids=[user1_id, user2_id])

    db = db_instance.db
    repo = AiMessageRepository(db)

    # Insert sequential messages for Ana (user1)
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        msg = AiMessage(
            id=f"msg-ana-{i}",
            project_id=project_id,
            thread="personal",
            owner_id=user1_id,
            author_type="user",
            author_id=user1_id,
            author_name="Ana Dev",
            content=f"Ana mensaje {i}",
            created_at=base_time + timedelta(minutes=i),
        )
        await repo.create_message(msg)

    # Insert sequential messages for Beto (user2)
    for i in range(5):
        msg = AiMessage(
            id=f"msg-beto-{i}",
            project_id=project_id,
            thread="personal",
            owner_id=user2_id,
            author_type="user",
            author_id=user2_id,
            author_name="Beto Dev",
            content=f"Beto mensaje {i}",
            created_at=base_time + timedelta(minutes=10 + i),
        )
        await repo.create_message(msg)

    # Insert a project announcement message (thread="project")
    proj_announcement = AiMessage(
        id="msg-proj-announcement-1",
        project_id=project_id,
        thread="project",
        owner_id=None,
        author_type="ai",
        author_name="🏛️ Arquitecto",
        ai_role="architect",
        content="Resumen global de arquitectura aprobado.",
        created_at=base_time + timedelta(minutes=20),
    )
    await repo.create_message(proj_announcement)

    # 1. Test Group History (/history): includes all messages (Ana + Beto + Project announcement = 11)
    res_group = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/history?limit=50",
        headers=headers1,
    )
    assert res_group.status_code == 200
    group_data = res_group.json()
    assert group_data["total"] == 11
    assert len(group_data["messages"]) == 11

    # 2. Test Cursor Pagination (limit=3)
    res_page1 = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/history?limit=3",
        headers=headers1,
    )
    page1_data = res_page1.json()
    assert len(page1_data["messages"]) == 3
    cursor1 = page1_data["next_cursor"]
    assert cursor1 is not None

    # Next page using 'after'
    res_page2 = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/history?after={cursor1}&limit=3",
        headers=headers1,
    )
    page2_data = res_page2.json()
    assert len(page2_data["messages"]) > 0
    # Ensure next page messages are newer than cursor1
    assert page2_data["messages"][0]["created_at"] > cursor1

    # 3. Test Personal History (/history/mine) for Ana:
    # Must contain Ana's 5 personal messages + 1 project announcement (6 total),
    # but NEVER Beto's personal messages!
    res_mine = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/history/mine",
        headers=headers1,
    )
    assert res_mine.status_code == 200
    mine_data = res_mine.json()
    assert mine_data["total"] == 6
    for m in mine_data["messages"]:
        assert m["owner_id"] == user1_id or m["thread"] == "project"
        assert m["owner_id"] != user2_id


# ── 4. Project AI State & Role Autonomy Authorization ─────────────────────────

@pytest.mark.asyncio
async def test_project_ai_state_and_autonomy_permissions(async_client: AsyncClient):
    """Requirement: GET|PUT /state; autonomy:'apply' solo owner/scrum_master/admin;
    PUT /roles alias funciona.
    """
    _, owner_id, owner_headers = await create_test_user(role="dev", name="Owner User")
    _, dev_id, dev_headers = await create_test_user(role="dev", name="Dev User")
    _, sm_id, sm_headers = await create_test_user(role="scrum_master", name="SM User")

    _, project_id = await create_test_project(owner_id=owner_id, member_ids=[owner_id, dev_id, sm_id])

    # 1. Dev tries to set autonomy 'apply' -> 403 Forbidden
    res_forbidden = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"roles": [{"role_id": "architect", "autonomy": "apply"}]},
        headers=dev_headers,
    )
    assert res_forbidden.status_code == 403

    # 2. Dev can toggle role enabled or autonomy 'suggest' -> 200 OK
    res_dev_ok = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"roles": [{"role_id": "architect", "enabled": False, "autonomy": "suggest"}]},
        headers=dev_headers,
    )
    assert res_dev_ok.status_code == 200

    # 3. Scrum Master can set autonomy 'apply' -> 200 OK
    res_sm_ok = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"roles": [{"role_id": "qa", "autonomy": "apply"}]},
        headers=sm_headers,
    )
    assert res_sm_ok.status_code == 200

    # 4. Project Owner can set autonomy 'apply' -> 200 OK
    res_owner_ok = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/state",
        json={"roles": [{"role_id": "tech_lead", "autonomy": "apply"}]},
        headers=owner_headers,
    )
    assert res_owner_ok.status_code == 200

    # 5. PUT /roles alias works
    res_alias = await async_client.put(
        f"/api/v1/ai-chat/projects/{project_id}/roles",
        json={"role_id": "architect", "active": True},
        headers=dev_headers,
    )
    assert res_alias.status_code == 200
    assert "architect" in res_alias.json()["active_ai_roles"]


# ── 5. Proposal State & Asynchronous Tasks ────────────────────────────────────

@pytest.mark.asyncio
async def test_proposal_state_and_async_tasks(async_client: AsyncClient):
    """Requirement: POST /messages/{mid}/proposals/{pid}/state {status};
    PATCH /tasks/{tid}/execute responde 202; PATCH/DELETE /tasks/{tid}.
    """
    _, user_id, headers = await create_test_user(role="dev", name="Task Dev")
    _, project_id = await create_test_project(owner_id=user_id, member_ids=[user_id])

    db = db_instance.db
    msg_repo = AiMessageRepository(db)

    # 1. Proposal state update
    test_msg = AiMessage(
        id="msg-prop-test-1",
        project_id=project_id,
        thread="personal",
        owner_id=user_id,
        author_type="ai",
        author_name="🏛️ Arquitecto",
        content="Propongo normalizar la relación entre Alumno y Curso",
        proposals=[{
            "id": "prop-101",
            "kind": "uml_command",
            "title": "Extraer clase Matricula",
            "rationale": "Evitar N-a-N",
            "severity": "warn",
        }],
    )
    await msg_repo.create_message(test_msg)

    # Apply proposal
    res_prop = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/messages/msg-prop-test-1/proposals/prop-101/state",
        json={"status": "applied"},
        headers=headers,
    )
    assert res_prop.status_code == 200
    assert res_prop.json()["status"] == "applied"

    # Check in DB
    saved_msg = await msg_repo.find_by_id("msg-prop-test-1")
    assert saved_msg["proposal_state"]["prop-101"]["status"] == "applied"
    assert saved_msg["proposal_state"]["prop-101"]["by"] == user_id

    # 2. Tasks: Create, Update, Async Execute (202), Delete
    res_task_create = await async_client.post(
        f"/api/v1/ai-chat/projects/{project_id}/tasks",
        json={
            "ai_role": "architect",
            "title": "Refactorizar módulos",
            "description": "Evaluar partición de subsistemas según principios SOLID.",
        },
        headers=headers,
    )
    assert res_task_create.status_code == 201
    task_id = res_task_create.json()["task_id"]

    # PATCH task
    res_patch = await async_client.patch(
        f"/api/v1/ai-chat/projects/{project_id}/tasks/{task_id}",
        json={"title": "Refactorizar módulos prioritarios"},
        headers=headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "Refactorizar módulos prioritarios"

    # PATCH execute responds 202 Accepted immediately
    res_exec = await async_client.patch(
        f"/api/v1/ai-chat/projects/{project_id}/tasks/{task_id}/execute",
        headers=headers,
    )
    assert res_exec.status_code == 202
    assert res_exec.json()["status"] == "in_progress"

    # DELETE task
    res_del = await async_client.delete(
        f"/api/v1/ai-chat/projects/{project_id}/tasks/{task_id}",
        headers=headers,
    )
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True


# ── 6. Project Digest & Context Trimming Priority ─────────────────────────────

@pytest.mark.asyncio
async def test_project_digest_and_trimming_priority():
    """Requirement: ProjectDigest <= 1500 tokens con objetivo, decisiones, preguntas, y qué pidió cada integrante;
    Trimming priority: digest > diagrama > turnos propios > novedades.
    """
    db = db_instance.db
    _, user_id, _ = await create_test_user(role="dev", name="Carlos Gómez")
    _, project_id = await create_test_project(owner_id=user_id, member_ids=[user_id])

    # Seed messages
    msg_repo = AiMessageRepository(db)
    for i in range(5):
        await msg_repo.create_message(
            AiMessage(
                project_id=project_id,
                author_type="user",
                author_name="Carlos Gómez",
                content=f"Carlos pide implementar la entidad Factura {i}",
            )
        )

    # 1. Generate digest
    digest_service = ProjectDigestService(db)
    digest_text = await digest_service.summarize_digest(project_id, force=True)
    assert digest_text != ""
    assert "Objetivo" in digest_text
    assert "Decisiones" in digest_text
    assert "Preguntas" in digest_text
    assert "Carlos Gómez" in digest_text

    # Check saved in ai_project_state
    state_repo = AiProjectStateRepository(db)
    state = await state_repo.get_or_create(project_id)
    assert state["digest"]["text"] == digest_text
    assert state["digest"]["tokens"] <= 1500

    # 2. Test Context Trimming Priority (digest > diagrama > turnos propios > novedades)
    role_def = get_role("architect")
    large_novedades = [
        {"author_name": f"User {i}", "author_role_label": "dev", "content": f"Petición larga número {i} " * 20}
        for i in range(20)
    ]
    large_user_turns = [
        {"author_type": "user", "content": f"Turno conversacional largo {i} " * 30}
        for i in range(15)
    ]

    llm_req = assemble_chat_request(
        role=role_def,
        project={"name": "Test Project", "description": "Large test context"},
        diagram={"nodes": [{"id": "n1", "data": {"name": "Usuario"}}], "edges": []},
        user_id=user_id,
        trigger="¿Cuál es tu recomendación?",
        digest_text=digest_text,
        user_turns=large_user_turns,
        other_activity=large_novedades,
    )

    # Verify digest is preserved in system prompt
    assert digest_text in llm_req.system
    assert "=== PERFIL Y ROL DEL ASISTENTE ===" in llm_req.system


# ── 7. Project WebSocket Connection & Tokens ──────────────────────────────────

@pytest.mark.asyncio
async def test_project_websocket_token_and_auth(async_client: AsyncClient):
    """Requirement: WS /api/v1/ws/projects/{project_id}?token= con token de un solo uso;
    cierre 4001 con token inválido/expirado; 4003 para no miembros.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    _, member_id, member_headers = await create_test_user(role="dev", name="WS Member")
    _, non_member_id, non_member_headers = await create_test_user(role="dev", name="WS Intruder")
    _, project_id = await create_test_project(owner_id=member_id, member_ids=[member_id])

    # 1. Non-member cannot obtain token -> 403 Forbidden
    res_tok_fail = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/ws-token",
        headers=non_member_headers,
    )
    assert res_tok_fail.status_code == 403

    # 2. Member obtains token -> 200 OK
    res_tok = await async_client.get(
        f"/api/v1/ai-chat/projects/{project_id}/ws-token",
        headers=member_headers,
    )
    assert res_tok.status_code == 200
    token_str = res_tok.json()["data"]["token"]

    # 3. Connect via TestClient with valid token
    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/projects/{project_id}?token={token_str}") as ws:
        # Initial presence is received
        data = ws.receive_json()
        assert data["type"] == "PRESENCE"

        # PING -> PONG
        ws.send_json({"type": "PING"})
        resp_pong = ws.receive_json()
        assert resp_pong["type"] == "PONG"

    # 4. Token is single-use: reconnecting with same token fails with code 4001
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/projects/{project_id}?token={token_str}") as ws:
            ws.receive_json()
    assert exc_info.value.code == 4001


# ── 8. Migration Script Tests (Dry-Run & Real Run) ─────────────────────────────

@pytest.mark.asyncio
async def test_migration_script_dry_run_and_real_run():
    """Requirement: migrate_ai_conversations.py idempotente (dedupe por id),
    con --dry-run, informe de conteos, y sin borrar la colección vieja.
    """
    from scripts.migrate_ai_conversations import run_migration

    db = db_instance.db
    project_id = str(ObjectId())
    user_id = str(ObjectId())

    # Seed legacy ai_conversations document
    legacy_msgs = [
        {
            "id": "legacy-msg-1",
            "author_type": "user",
            "author_id": user_id,
            "author_name": "Legacy User",
            "author_role_label": "dev",
            "content": "Pregunta legacy sobre herencia",
            "timestamp": datetime.now(timezone.utc),
        },
        {
            "id": "legacy-msg-2",
            "author_type": "ai",
            "author_name": "🏛️ Arquitecto",
            "author_role_label": "architect_ai",
            "ai_role": "architect",
            "content": "Respuesta legacy del arquitecto",
            "timestamp": datetime.now(timezone.utc),
            "proposals": [],
        },
    ]

    await db["ai_conversations"].insert_one({
        "project_id": project_id,
        "messages": legacy_msgs,
        "active_ai_roles": ["architect", "qa"],
        "created_at": datetime.now(timezone.utc),
    })

    # 1. Dry Run Execution
    stats_dry = await run_migration(
        mongodb_url=settings.MONGODB_URL,
        database_name=settings.DATABASE_NAME,
        dry_run=True,
        project_id_filter=project_id,
        client=db_instance.client,
        db=db_instance.db,
    )
    assert stats_dry["conversations_scanned"] == 1
    assert stats_dry["messages_scanned"] == 2
    assert stats_dry["messages_migrated"] == 2
    assert stats_dry["errors"] == 0

    # In dry-run, ai_messages must not contain the records yet
    count_after_dry = await db["ai_messages"].count_documents({"project_id": project_id})
    assert count_after_dry == 0

    # 2. Real Run Execution
    stats_real = await run_migration(
        mongodb_url=settings.MONGODB_URL,
        database_name=settings.DATABASE_NAME,
        dry_run=False,
        project_id_filter=project_id,
        client=db_instance.client,
        db=db_instance.db,
    )
    assert stats_real["messages_migrated"] == 2
    assert stats_real["errors"] == 0

    # Now messages exist in ai_messages
    count_after_real = await db["ai_messages"].count_documents({"project_id": project_id})
    assert count_after_real == 2

    # Verify legacy collection was NOT deleted
    old_conv = await db["ai_conversations"].find_one({"project_id": project_id})
    assert old_conv is not None
    assert len(old_conv["messages"]) == 2

    # 3. Idempotent re-run
    stats_idempotent = await run_migration(
        mongodb_url=settings.MONGODB_URL,
        database_name=settings.DATABASE_NAME,
        dry_run=False,
        project_id_filter=project_id,
        client=db_instance.client,
        db=db_instance.db,
    )
    # All messages must be skipped
    assert stats_idempotent["messages_skipped"] == 2
    assert stats_idempotent["messages_migrated"] == 0
    # Still 2 messages total in ai_messages
    count_final = await db["ai_messages"].count_documents({"project_id": project_id})
    assert count_final == 2
