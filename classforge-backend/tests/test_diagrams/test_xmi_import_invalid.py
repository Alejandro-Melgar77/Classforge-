"""Regression tests for C6 and A36: XMI import validation and payload limits."""
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app
from app.modules.diagrams.repository import DiagramRepository

USER_ID = ObjectId("507f1f77bcf86cd799439061")


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


@pytest.fixture(autouse=True)
async def _setup():
    for collection in ("diagrams", "diagram_versions", "users", "audit_logs"):
        await db_instance.db[collection].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


async def _seed_diagram(repo):
    return await repo.create({
        "name": "Original Diagram",
        "description": "desc",
        "created_by": USER_ID,
        "graph_data": {
            "nodes": [{"id": "n1", "type": "class", "data": {"name": "Initial"}}],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1.0},
        },
        "folder_id": None,
    })


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_xmi_import_broken_xml_returns_400_and_leaves_diagram_untouched():
    """C6: Broken XML must return 400 and preserve the existing diagram graph and version."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])
    before = await repo.get_by_id(diagram_id)

    async with await _client() as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{diagram_id}/import/xmi",
            files={"file": ("corrupt.xmi", b"<xmi:XMI><unclosed-tag>", "application/xml")},
        )

    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"

    after = await repo.get_by_id(diagram_id)
    assert after["graph_data"] == before["graph_data"]
    assert after["version"] == before["version"]


async def test_xmi_import_empty_graph_returns_400():
    """C6: An XMI file that parses to no classes/relationships must be rejected with 400."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    empty_xmi = (
        b'<?xml version="1.0"?>'
        b'<xmi:XMI xmlns:xmi="http://www.omg.org/spec/XMI/20131001" '
        b'xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">'
        b'<uml:Model xmi:id="M1" name="Empty"/></xmi:XMI>'
    )

    async with await _client() as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{diagram_id}/import/xmi",
            files={"file": ("empty.xmi", empty_xmi, "application/xml")},
        )

    assert res.status_code == 400


async def test_xmi_import_oversized_file_returns_413():
    """A36 / C6: Files exceeding the 10 MB limit must return 413 without loading fully into memory."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    # 10 MB + 1024 bytes
    oversized_data = b"A" * (10 * 1024 * 1024 + 1024)

    async with await _client() as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{diagram_id}/import/xmi",
            files={"file": ("huge.xmi", oversized_data, "application/xml")},
        )

    assert res.status_code == 413
