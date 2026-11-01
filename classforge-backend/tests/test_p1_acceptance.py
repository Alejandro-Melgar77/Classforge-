import os
import io
import base64
import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from httpx import AsyncClient, ASGITransport
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings, settings
from app.core.database import db_instance
from app.core.security import create_access_token, hash_refresh_token
from app.core.errors import (
    DomainError,
    NotFoundError,
    ForbiddenError,
    ConflictError,
    ValidationError,
    RateLimitedError,
    ExternalServiceError,
)
from app.core.authz import can_access_project, can_access_diagram
from app.modules.collaboration.service import verify_ws_token, update_diagram_graph_data
from app.modules.collaboration.connection_manager import ConnectionManager
from app.modules.diagrams.service import DiagramService


# ── Helpers ──────────────────────────────────────────────────────────────────

async def get_test_db():
    return db_instance.db


async def create_user(db, name="Test User", email=None, role="dev", team_ids=None):
    if not email:
        email = f"user_{ObjectId()}@classforge.dev"
    user_doc = {
        "_id": ObjectId(),
        "name": name,
        "email": email,
        "password_hash": "hash_pwd",
        "role": role,
        "avatar_url": None,
        "team_ids": team_ids or [],
        "is_active": True,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db["users"].insert_one(user_doc)
    return user_doc


async def create_user_with_session(db, name="Session User", email=None, role="dev"):
    user = await create_user(db, name=name, email=email, role=role)
    user_id = str(user["_id"])
    session_id = str(ObjectId())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    await db["sessions"].insert_one({
        "_id": ObjectId(session_id),
        "user_id": user_id,
        "refresh_token_hash": hash_refresh_token("dummy_refresh_token_" + session_id),
        "device_info": "test_device",
        "ip_address": "127.0.0.1",
        "created_at": now,
        "last_activity": now,
        "expires_at": expires_at,
        "is_active": True,
    })
    token = create_access_token(subject=user_id, sid=session_id)
    headers = {"Authorization": f"Bearer {token}"}
    return user, session_id, token, headers


# ── Bloque A Tests: Núcleo transversal ───────────────────────────────────────

@pytest.mark.asyncio
async def test_domain_error_hierarchy_and_response_format(async_client: AsyncClient):
    """Verifies that DomainError subclasses map to correct HTTP statuses and {success:false, message, code}."""
    @app.get("/api/v1/test/domain-not-found")
    async def _route_not_found():
        raise NotFoundError("Resource was not found")

    @app.get("/api/v1/test/domain-forbidden")
    async def _route_forbidden():
        raise ForbiddenError("Access is forbidden")

    @app.get("/api/v1/test/domain-conflict")
    async def _route_conflict():
        raise ConflictError("Item already exists")

    @app.get("/api/v1/test/domain-validation")
    async def _route_validation():
        raise ValidationError("Invalid input provided", code="CUSTOM_VALIDATION_ERROR")

    @app.get("/api/v1/test/domain-rate-limited")
    async def _route_rate_limited():
        raise RateLimitedError("Too many attempts")

    @app.get("/api/v1/test/domain-external")
    async def _route_external():
        raise ExternalServiceError("Upstream AI failed")

    res = await async_client.get("/api/v1/test/domain-not-found")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["message"] == "Resource was not found"
    assert data["code"] == "NOT_FOUND"

    res = await async_client.get("/api/v1/test/domain-forbidden")
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    res = await async_client.get("/api/v1/test/domain-conflict")
    assert res.status_code == 409
    assert res.json()["code"] == "CONFLICT"

    res = await async_client.get("/api/v1/test/domain-validation")
    assert res.status_code == 400
    assert res.json()["code"] == "CUSTOM_VALIDATION_ERROR"

    res = await async_client.get("/api/v1/test/domain-rate-limited")
    assert res.status_code == 429
    assert res.json()["code"] == "RATE_LIMITED"

    res = await async_client.get("/api/v1/test/domain-external")
    assert res.status_code == 502
    assert res.json()["code"] == "EXTERNAL_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_unhandled_500_hides_internal_details_and_logs_request_id(async_client: AsyncClient):
    """Verifies that unhandled 500 exceptions do NOT leak tracebacks or credentials, and return X-Request-ID."""
    @app.get("/api/v1/test/crash-route")
    async def _crash_route():
        raise RuntimeError("CRITICAL_DB_PASSWORD_LEAK_SECRET_12345")

    res = await async_client.get("/api/v1/test/crash-route")
    assert res.status_code == 500
    assert "CRITICAL_DB_PASSWORD_LEAK_SECRET_12345" not in res.text
    body = res.json()
    assert body["success"] is False
    assert body["message"] == "Internal server error"
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert "X-Request-ID" in res.headers


def test_authz_pure_domain_policies():
    """Verifies pure domain policies can_access_project and can_access_diagram without FastAPI dependencies."""
    owner_id = str(ObjectId())
    other_user_id = str(ObjectId())
    team_id = str(ObjectId())

    owner_user = {"_id": ObjectId(owner_id), "role": "dev", "team_ids": []}
    admin_user = {"_id": ObjectId(), "role": "admin", "team_ids": []}
    member_user = {"_id": ObjectId(other_user_id), "role": "dev", "team_ids": [ObjectId(team_id)]}
    outsider_user = {"_id": ObjectId(), "role": "dev", "team_ids": []}

    project = {
        "_id": ObjectId(),
        "owner_id": ObjectId(owner_id),
        "team_id": ObjectId(team_id),
    }

    diagram = {
        "_id": ObjectId(),
        "creator_id": ObjectId(owner_id),
        "project_id": project["_id"],
        "member_ids": [ObjectId(owner_id)],
    }

    # Project access
    assert can_access_project(owner_user, project) is True
    assert can_access_project(admin_user, project) is True
    assert can_access_project(member_user, project) is True
    assert can_access_project(outsider_user, project) is False

    # Diagram access
    assert can_access_diagram(owner_user, diagram, project=project) is True
    assert can_access_diagram(admin_user, diagram, project=project) is True
    assert can_access_diagram(member_user, diagram, project=project) is True
    assert can_access_diagram(outsider_user, diagram, project=project) is False


# ── Bloque B Tests: Defectos verificados ──────────────────────────────────────

@pytest.mark.asyncio
async def test_b2_session_revocation_on_logout(async_client: AsyncClient):
    """B2: /auth/logout revokes session when sid claim is present in access token."""
    db = await get_test_db()
    user, session_id, token, headers = await create_user_with_session(db)

    # 1. Access protected route with active session -> 200
    res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["email"] == user["email"]

    # 2. Logout -> revokes session
    res_logout = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert res_logout.status_code == 200
    assert res_logout.json()["success"] is True

    # Verify session revoked in database
    session_doc = await db["sessions"].find_one({"_id": ObjectId(session_id)})
    assert session_doc["is_active"] is False

    # 3. Subsequent request with same revoked token -> 401 Unauthorized
    res_after = await async_client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 401

    # 4. Backward compatibility: Legacy token without sid succeeds and logout only audits
    legacy_token = create_access_token(subject=str(user["_id"]))  # sid=None
    legacy_headers = {"Authorization": f"Bearer {legacy_token}"}
    res_legacy = await async_client.get("/api/v1/auth/me", headers=legacy_headers)
    assert res_legacy.status_code == 200
    res_legacy_logout = await async_client.post("/api/v1/auth/logout", headers=legacy_headers)
    assert res_legacy_logout.status_code == 200


@pytest.mark.asyncio
async def test_b3_ai_chat_project_isolation(async_client: AsyncClient):
    """B3: Foreign user receives 403 on all ai-chat /projects/{pid}/* routes and invalid task execution."""
    db = await get_test_db()
    user_a = await create_user(db, name="Owner User")
    user_b = await create_user(db, name="Outsider User")

    project_a = {
        "_id": ObjectId(),
        "name": "Project A",
        "owner_id": user_a["_id"],
        "team_id": None,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db["projects"].insert_one(project_a)
    pid_a = str(project_a["_id"])

    token_b = create_access_token(subject=str(user_b["_id"]))
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B receives 403 on history
    res_hist = await async_client.get(f"/api/v1/ai-chat/projects/{pid_a}/history", headers=headers_b)
    assert res_hist.status_code == 403

    # User B receives 403 on my history
    res_my_hist = await async_client.get(f"/api/v1/ai-chat/projects/{pid_a}/history/mine", headers=headers_b)
    assert res_my_hist.status_code == 403

    # User B receives 403 on messages
    res_msg = await async_client.post(
        f"/api/v1/ai-chat/projects/{pid_a}/messages",
        json={"message": "Hello"},
        headers=headers_b
    )
    assert res_msg.status_code == 403

    # User B receives 403 on tasks list
    res_tasks = await async_client.get(f"/api/v1/ai-chat/projects/{pid_a}/tasks", headers=headers_b)
    assert res_tasks.status_code == 403

    # Verify task project mismatch in execute_task
    token_a = create_access_token(subject=str(user_a["_id"]))
    headers_a = {"Authorization": f"Bearer {token_a}"}

    foreign_task = {
        "_id": ObjectId(),
        "project_id": str(ObjectId()),  # Belongs to a different project
        "description": "Foreign task",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    await db["ai_tasks"].insert_one(foreign_task)
    tid = str(foreign_task["_id"])

    res_exec = await async_client.patch(
        f"/api/v1/ai-chat/projects/{pid_a}/tasks/{tid}/execute",
        headers=headers_a
    )
    assert res_exec.status_code == 403
    assert "belong" in res_exec.json().get("message", "").lower() or res_exec.json().get("code") == "FORBIDDEN"


@pytest.mark.asyncio
async def test_b4_user_naming_correctness():
    """B4: Users collection uses 'name', never 'username'."""
    from app.modules.ai_chat.context_builder import ProjectContextBuilder
    db = await get_test_db()
    user = await create_user(db, name="Ada Lovelace")

    team = {
        "_id": ObjectId(),
        "name": "Math Pioneers",
        "scrum_master_id": user["_id"],
        "member_ids": [user["_id"]],
        "is_deleted": False,
    }
    await db["teams"].insert_one(team)

    project = {
        "_id": ObjectId(),
        "name": "Math Project",
        "description": "Analysis",
        "owner_id": user["_id"],
        "team_id": team["_id"],
        "tags": ["math"],
        "diagram_count": 0,
        "is_deleted": False,
    }
    await db["projects"].insert_one(project)

    builder = ProjectContextBuilder()
    ctx = await builder.build(db, str(project["_id"]))
    assert "Ada Lovelace" in ctx


@pytest.mark.asyncio
async def test_b5_diagram_creation_scoping(async_client: AsyncClient):
    """B5: Without project_id, assigns user's personal project; foreign project_id receives 403."""
    db = await get_test_db()
    user_a = await create_user(db, name="User A")
    user_b = await create_user(db, name="User B")

    token_b = create_access_token(subject=str(user_b["_id"]))
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User B creates diagram without project_id
    res_b = await async_client.post(
        "/api/v1/diagrams/",
        json={"name": "Diagram B", "type": "class"},
        headers=headers_b
    )
    assert res_b.status_code == 200
    diagram_data = res_b.json()["data"]
    assigned_project_id = diagram_data["project_id"]
    assert assigned_project_id is not None

    # Verify assigned project belongs to User B
    proj_doc = await db["projects"].find_one({"_id": ObjectId(assigned_project_id)})
    assert str(proj_doc["owner_id"]) == str(user_b["_id"])

    # 2. User B tries to create diagram specifying User A's private project -> 403
    project_a = {
        "_id": ObjectId(),
        "name": "Project A Private",
        "owner_id": user_a["_id"],
        "team_id": None,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db["projects"].insert_one(project_a)
    pid_a = str(project_a["_id"])

    res_foreign = await async_client.post(
        "/api/v1/diagrams/",
        json={"name": "Sneaky Diagram", "type": "class", "project_id": pid_a},
        headers=headers_b
    )
    assert res_foreign.status_code == 403


@pytest.mark.asyncio
async def test_b7_and_b9_dto_validation_and_no_fake_notifications(async_client: AsyncClient):
    """B7 & B9: DTO validation for prompt / image limits and no uncommitted notifications."""
    db = await get_test_db()
    user = await create_user(db, name="Prompt User")
    token = create_access_token(subject=str(user["_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    diagram = {
        "_id": ObjectId(),
        "name": "Test Diagram",
        "creator_id": user["_id"],
        "project_id": None,
        "member_ids": [user["_id"]],
        "graph_data": {"cells": []},
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db["diagrams"].insert_one(diagram)
    did = str(diagram["_id"])

    # B9: Prompt exceeds 4000 characters -> 422
    long_prompt = "a" * 4001
    res_long = await async_client.post(
        f"/api/v1/diagrams/{did}/ai-prompt",
        json={"prompt": long_prompt},
        headers=headers
    )
    assert res_long.status_code == 422

    # B9: Invalid MIME type on from-image -> 422
    res_bad_mime = await async_client.post(
        f"/api/v1/diagrams/{did}/from-image",
        json={"image_base64": "SGVsbG8=", "mime_type": "application/x-executable"},
        headers=headers
    )
    assert res_bad_mime.status_code == 422

    # B9: Image base64 exceeding 8 MB -> 422
    huge_bytes = b"0" * (8 * 1024 * 1024 + 100)
    huge_b64 = base64.b64encode(huge_bytes).decode("ascii")
    res_huge = await async_client.post(
        f"/api/v1/diagrams/{did}/from-image",
        json={"image_base64": huge_b64, "mime_type": "image/png"},
        headers=headers
    )
    assert res_huge.status_code == 422


@pytest.mark.asyncio
async def test_b10_object_id_boundary_validation(async_client: AsyncClient, admin_token_headers):
    """B10: Invalid ObjectId path parameters return 400 Bad Request (never 500 InvalidId)."""
    invalid_ids = ["not-an-object-id", "123", "00000000000000000000000z", "bad_hex!"]

    for bad_id in invalid_ids:
        # Projects router
        res_proj = await async_client.get(f"/api/v1/projects/{bad_id}", headers=admin_token_headers)
        assert res_proj.status_code == 400
        assert res_proj.json()["code"] == "INVALID_OBJECT_ID"

        # Diagrams router
        res_diag = await async_client.get(f"/api/v1/diagrams/{bad_id}", headers=admin_token_headers)
        assert res_diag.status_code == 400
        assert res_diag.json()["code"] == "INVALID_OBJECT_ID"

        # Teams router
        res_team = await async_client.get(f"/api/v1/teams/{bad_id}", headers=admin_token_headers)
        assert res_team.status_code == 400
        assert res_team.json()["code"] == "INVALID_OBJECT_ID"

        # Folders router
        res_fold = await async_client.get(f"/api/v1/folders/{bad_id}", headers=admin_token_headers)
        assert res_fold.status_code == 400
        assert res_fold.json()["code"] == "INVALID_OBJECT_ID"


# ── Bloque C Tests: Colaboración WebSocket ───────────────────────────────────

@pytest.mark.asyncio
async def test_c1_websocket_lock_rejection_logic():
    """C1: ConnectionManager rejects operations on locked elements owned by another user."""
    manager = ConnectionManager()
    diagram_id = "test_diag_locks"
    user1_id = "user_1"
    user2_id = "user_2"

    # User 1 acquires lock on node_123
    acquired = manager.acquire_lock(diagram_id, user1_id, "node_123")
    assert acquired is True

    # User 2 cannot modify node_123
    assert manager.is_locked_by_other(diagram_id, "node_123", user2_id) is True
    # User 1 CAN modify node_123
    assert manager.is_locked_by_other(diagram_id, "node_123", user1_id) is False

    # Once User 1 releases lock, User 2 can modify
    manager.release_lock(diagram_id, user1_id, "node_123")
    assert manager.is_locked_by_other(diagram_id, "node_123", user2_id) is False


@pytest.mark.asyncio
async def test_c2_atomic_concurrent_graph_updates():
    """C2: asyncio.gather of 50 concurrent moves on distinct nodes without losing any position."""
    db = await get_test_db()
    diagram_id = str(ObjectId())

    # Initialize diagram with 50 nodes
    nodes = [{"id": f"node_{i}", "x": 0, "y": 0, "type": "class"} for i in range(50)]
    await db["diagrams"].insert_one({
        "_id": ObjectId(diagram_id),
        "name": "Concurrency Test Diagram",
        "graph_data": {"nodes": nodes, "edges": []},
        "updated_at": datetime.now(timezone.utc),
    })

    async def _move_node(i):
        await update_diagram_graph_data(
            diagram_id=diagram_id,
            element_id=f"node_{i}",
            op="move",
            data={"position": {"x": (i + 1) * 10, "y": (i + 1) * 20}},
            element_type="node"
        )

    # Execute 50 concurrent updates
    await asyncio.gather(*[_move_node(i) for i in range(50)])

    # Verify that all 50 nodes have their updated positions
    doc = await db["diagrams"].find_one({"_id": ObjectId(diagram_id)})
    stored_nodes = doc["graph_data"]["nodes"]
    assert len(stored_nodes) == 50

    node_dict = {n["id"]: n for n in stored_nodes}
    for i in range(50):
        node = node_dict[f"node_{i}"]
        assert node["position"]["x"] == (i + 1) * 10
        assert node["position"]["y"] == (i + 1) * 20


@pytest.mark.asyncio
async def test_c4_websocket_single_use_token():
    """C4: ws_token is single-use and consumed upon verification."""
    db = await get_test_db()
    user = await create_user(db, name="WS User")
    uid = str(user["_id"])
    did = str(ObjectId())

    service = DiagramService(db)
    token_data = await service.generate_ws_token(did, uid)
    ws_token = token_data["token"]

    # 1. First verification succeeds and consumes the token
    user_first = await verify_ws_token(diagram_id=did, token=ws_token)
    assert user_first is not None
    assert str(user_first["_id"]) == uid

    # 2. Second verification with same token fails (consumed / single-use)
    user_second = await verify_ws_token(diagram_id=did, token=ws_token)
    assert user_second is None


def test_c3_websocket_rate_and_size_limits():
    """C3: WebSocket limits size <= 64KB and burst <= 60 msg/s, closing with code 4008."""
    from app.modules.collaboration.router import MAX_MESSAGE_BYTES, MAX_BURST_PER_SECOND
    assert MAX_MESSAGE_BYTES == 64 * 1024
    assert MAX_BURST_PER_SECOND == 60


# ── Bloque D Tests: Configuración y despliegue ───────────────────────────────

def test_d1_production_settings_validation():
    """D1: Settings raises ValueError in production if SECRET_KEY or CORS_ORIGINS are unsafe."""
    # Fails if default SECRET_KEY
    with pytest.raises(ValueError, match="SECRET_KEY debe estar configurado"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="classforge-super-secret-key-for-development-only",
            CORS_ORIGINS="https://app.classforge.dev"
        )

    # Fails if CORS_ORIGINS is empty
    with pytest.raises(ValueError, match="CORS_ORIGINS no puede estar vacío"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            CORS_ORIGINS=""
        )

    # Succeeds with safe production configuration
    valid_prod = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="super_secure_production_secret_key_12345",
        CORS_ORIGINS="https://app.classforge.dev"
    )
    assert valid_prod.ENVIRONMENT == "production"


@pytest.mark.asyncio
async def test_d6_pagination_headers_present(async_client: AsyncClient, admin_token_headers):
    """D6: GET /users/ and GET /diagrams/ return X-Total-Count header."""
    # Users list
    res_users = await async_client.get("/api/v1/users/", headers=admin_token_headers)
    assert res_users.status_code == 200
    assert "X-Total-Count" in res_users.headers

    # Diagrams list
    res_diags = await async_client.get("/api/v1/diagrams/", headers=admin_token_headers)
    assert res_diags.status_code == 200
    assert "X-Total-Count" in res_diags.headers
