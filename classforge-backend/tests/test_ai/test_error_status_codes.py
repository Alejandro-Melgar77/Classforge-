"""Regression test for A3: /ai/generate error status codes."""
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import app.modules.ai.router as ai_router
from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.core.errors import ExternalServiceError
from app.main import app

USER_ID = ObjectId("507f1f77bcf86cd799439041")


def _user():
    return {
        "_id": USER_ID,
        "id": str(USER_ID),
        "name": "Dev",
        "email": "dev@example.com",
        "role": "dev",
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }


@pytest.fixture(autouse=True)
async def _setup():
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_ai_generate_without_key_or_on_error_returns_502_not_200(monkeypatch):
    """A3: /ai/generate without key or failing upstream must return 502/503, never 200."""
    async def fake_fail(**kwargs):
        raise ExternalServiceError("No API key configured for provider")

    monkeypatch.setattr(ai_router, "process_prompt", fake_fail)

    async with await _client() as ac:
        res = await ac.post("/api/v1/ai/generate", json={"prompt": "crear clase A"})

    assert res.status_code in (502, 503)
    data = res.json()
    assert data["success"] is False
    assert data["code"] in ("EXTERNAL_SERVICE_ERROR", "SERVICE_UNAVAILABLE")


async def test_ai_generate_from_image_error_returns_502_not_200(monkeypatch):
    """A3: /ai/generate-from-image failing upstream must return 502/503, never 200."""
    async def fake_fail(**kwargs):
        raise ExternalServiceError("Vision provider unavailable")

    monkeypatch.setattr(ai_router, "generate_diagram_from_image", fake_fail)

    async with await _client() as ac:
        res = await ac.post(
            "/api/v1/ai/generate-from-image",
            json={"image_base64": "aGVsbG8="},
        )

    assert res.status_code in (502, 503)
    data = res.json()
    assert data["success"] is False
