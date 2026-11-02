"""Regression test for C7: Diagram versioning semantics and history snapshots."""
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app
from app.modules.diagrams.repository import DiagramRepository

USER_ID = ObjectId("507f1f77bcf86cd799439062")


def _user():
    return {
        "_id": USER_ID,
        "id": str(USER_ID),
        "name": "Owner",
        "email": "owner@example.com",
        "role": "dev",
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }


def _graph(nodes):
    return {"nodes": nodes, "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1.0}}


@pytest.fixture(autouse=True)
async def _setup():
    for collection in ("diagrams", "diagram_versions", "users", "audit_logs"):
        await db_instance.db[collection].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


async def _seed_diagram(repo):
    return await repo.create({
        "name": "Versioning Test Diagram",
        "description": "desc",
        "created_by": USER_ID,
        "graph_data": _graph([{"id": "n1", "type": "class", "data": {"name": "InitialState"}}]),
        "folder_id": None,
    })


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_save_graph_appends_new_state_to_history():
    """C7: Saving a new graph state must store the NEW state at version N+1 in history."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    # Initial creation seeds version 1 with the initial graph
    v1_snapshot = await repo.get_history_entry(diagram_id, 1)
    assert v1_snapshot is not None
    assert v1_snapshot["graph_data"]["nodes"][0]["data"]["name"] == "InitialState"

    # Save a new state (version 2)
    new_graph = _graph([
        {"id": "n1", "type": "class", "data": {"name": "InitialState"}},
        {"id": "n2", "type": "class", "data": {"name": "SecondClass"}},
    ])
    updated = await repo.save_graph(diagram_id, new_graph, str(USER_ID), "Added second class")

    assert updated["version"] == 2
    assert updated["graph_data"] == new_graph

    # History entry at version 2 must hold the NEW state, not the old one
    v2_snapshot = await repo.get_history_entry(diagram_id, 2)
    assert v2_snapshot is not None
    assert v2_snapshot["version"] == 2
    assert len(v2_snapshot["graph_data"]["nodes"]) == 2
    assert v2_snapshot["graph_data"]["nodes"][1]["data"]["name"] == "SecondClass"
    assert v2_snapshot["comment"] == "Added second class"


async def test_restore_version_restores_intended_state():
    """C7: Restoring a previous version restores that snapshot's exact content as a new version."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    # Save version 2
    v2_graph = _graph([{"id": "n9", "type": "class", "data": {"name": "Replaced"}}])
    await repo.save_graph(diagram_id, v2_graph, str(USER_ID), "v2 replace")

    # Restore version 1
    async with await _client() as ac:
        res = await ac.post(f"/api/v1/diagrams/{diagram_id}/history/1/restore")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["version"] == 3
    assert body["graph_data"]["nodes"][0]["data"]["name"] == "InitialState"

    # And check database snapshot for version 3
    restored_entry = await repo.get_history_entry(diagram_id, 3)
    assert restored_entry["version"] == 3
    assert restored_entry["graph_data"]["nodes"][0]["data"]["name"] == "InitialState"
