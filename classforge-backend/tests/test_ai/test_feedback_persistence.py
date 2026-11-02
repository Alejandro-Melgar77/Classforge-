"""Persistence regression tests for POST /api/v1/ai/feedback (audit C4).

The endpoint used to answer 200/success while importing a non-existent ``db``
symbol inside a silent ``except``, so nothing was ever stored.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app

USER_ID = "507f1f77bcf86cd799439041"


@pytest.fixture(autouse=True)
async def _clean():
    if db_instance.db is not None:
        await db_instance.db["ai_feedback"].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: {
        "_id": USER_ID,
        "id": USER_ID,
        "name": "Feedback Tester",
        "role": "dev",
        "email": "fb@example.com",
    }
    yield
    app.dependency_overrides.clear()


def _payload(**overrides):
    payload = {
        "prompt": "crear clase Factura con numero:string",
        "corrected_command": {
            "action": "create_class",
            "classes": [
                {
                    "name": "Factura",
                    "attributes": [{"name": "numero", "type": "String", "visibility": "+"}],
                    "methods": [],
                }
            ],
            "relations": [],
            "deleted_elements": [],
            "explanation": "Factura creada",
            "source": "local",
        },
        "allow_feedback": True,
        "comment": "revisar tipo",
    }
    payload.update(overrides)
    return payload


async def test_feedback_is_actually_persisted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/ai/feedback", json=_payload())

    assert res.status_code == 200
    assert res.json()["success"] is True

    stored = await db_instance.db["ai_feedback"].find_one({"status": "pending_review"})
    assert stored is not None
    assert stored["corrected_command"]["classes"][0]["name"] == "Factura"
    assert stored["created_at"] is not None


async def test_feedback_anonymizes_email_and_ip():
    payload = _payload(
        prompt="contacto usuario@empresa.com desde 192.168.1.10",
        comment="escribir a soporte@test.com",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/ai/feedback", json=payload)

    assert res.status_code == 200
    stored = await db_instance.db["ai_feedback"].find_one({"status": "pending_review"})
    assert "usuario@empresa.com" not in stored["prompt"]
    assert "192.168.1.10" not in stored["prompt"]
    assert "[EMAIL]" in stored["prompt"]
    assert "soporte@test.com" not in (stored.get("comment") or "")
