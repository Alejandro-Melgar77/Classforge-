"""Canonical error-contract regression tests (audit A1, A2, A3, A21)."""
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import app.modules.ai.router as ai_router
import app.modules.codegen.gemini_generator as gemini_generator
from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app, permission_error_handler

ADMIN_ID = ObjectId("507f1f77bcf86cd799439031")
DEV_ID = ObjectId("507f1f77bcf86cd799439032")
DIAGRAM_ID = ObjectId("507f1f77bcf86cd799439033")


def _user(oid, role):
    return {
        "_id": oid,
        "id": str(oid),
        "name": "U",
        "email": f"{oid}@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }


def _override(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("diagrams", "projects", "teams", "users", "audit_logs"):
        await db_instance.db[collection].delete_many({})
    yield
    app.dependency_overrides.clear()


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_project_team_validation_returns_400_not_500():
    """A2: projects/service.py raised HTTPException without importing it."""
    _override(_user(ADMIN_ID, "admin"))

    async with await _client() as ac:
        res = await ac.post(
            "/api/v1/projects/",
            json={"name": "Equipo", "description": "d", "type": "team"},
        )

    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


async def test_participant_management_by_dev_returns_403_not_500():
    """A1: native PermissionError must surface as 403."""
    now = datetime.now(timezone.utc)
    await db_instance.db["diagrams"].insert_one({
        "_id": DIAGRAM_ID,
        "name": "D",
        "created_by": ADMIN_ID,
        "member_ids": [DEV_ID],
        "team_id": None,
        "project_id": None,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    })
    _override(_user(DEV_ID, "dev"))

    async with await _client() as ac:
        res = await ac.put(
            f"/api/v1/diagrams/{DIAGRAM_ID}/participants",
            json={"member_ids": []},
        )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


async def test_permission_error_handler_is_canonical():
    class _Req:
        class state:  # noqa: N801 - tiny stub
            request_id = "test"

    response = await permission_error_handler(_Req(), PermissionError("denegado"))
    assert response.status_code == 403
    assert b'"code":"FORBIDDEN"' in response.body


async def test_ai_generate_failure_returns_502(monkeypatch):
    """A3: /ai/generate used to answer HTTP 200 with success:false."""
    _override(_user(DEV_ID, "dev"))

    async def boom(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(ai_router, "process_prompt", boom)

    async with await _client() as ac:
        res = await ac.post("/api/v1/ai/generate", json={"prompt": "crear clase A"})

    assert res.status_code == 502
    assert res.json()["code"] == "EXTERNAL_SERVICE_ERROR"


async def test_codegen_fallback_does_not_leak_exception(monkeypatch):
    """A21: the fallback must not echo str(exc) to the client."""
    _override(_user(DEV_ID, "dev"))

    def boom(*args, **kwargs):
        raise RuntimeError("sensitive upstream detail")

    monkeypatch.setattr(gemini_generator, "get_provider", boom)

    result = await gemini_generator.generate_backend_with_gemini(
        graph_data={"nodes": [], "edges": []},
        target_backend="spring_boot",
    )

    assert result["engine_used"] == "deterministic"
    assert "sensitive upstream detail" not in result["summary"]
    assert "sensitive upstream detail" not in str(result["engine_used"])
