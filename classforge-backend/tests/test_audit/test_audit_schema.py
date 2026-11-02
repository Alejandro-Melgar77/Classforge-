"""Regression test for A17: Audit log canonical schema and dashboard stats."""
from datetime import datetime, timezone
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app
from app.modules.diagrams.schemas import CreateDiagram
from app.modules.diagrams.service import DiagramService

USER_ID = ObjectId("507f1f77bcf86cd799439091")
PROJECT_ID = ObjectId("607f1f77bcf86cd799439093")


def _user(role="admin"):
    return {
        "_id": USER_ID,
        "id": str(USER_ID),
        "name": "Admin User",
        "email": "admin@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("audit_logs", "diagrams", "projects", "users"):
        await db_instance.db[collection].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_audit_logs_have_created_at_and_dashboard_not_null():
    """A17: All audit_log records have created_at and the dashboard endpoint returns non-null recent_activity."""
    await db_instance.db["projects"].insert_one({
        "_id": PROJECT_ID,
        "name": "Audit Test Project",
        "owner_id": USER_ID,
        "type": "personal",
        "is_deleted": False,
    })

    service = DiagramService(db_instance.db)
    diagram = await service.create_diagram(
        CreateDiagram(name="Diagram for Audit", project_id=str(PROJECT_ID)),
        _user()
    )

    entry = await db_instance.db["audit_logs"].find_one({"action": "CREATE_DIAGRAM"})
    assert entry is not None
    assert "created_at" in entry
    assert entry["created_at"] is not None
    assert "timestamp" not in entry
    assert entry["resource"] == "diagrams"
    assert entry["resource_id"] == str(diagram["_id"])

    # Test dashboard endpoint
    async with await _client() as ac:
        res = await ac.get("/api/v1/dashboard/stats")

    assert res.status_code == 200
    data = res.json()["data"]
    assert "recent_activity" in data
    activities = data["recent_activity"]
    assert len(activities) >= 1
    for act in activities:
        assert act.get("created_at") is not None
        assert act.get("action") is not None
