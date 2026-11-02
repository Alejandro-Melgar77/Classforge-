"""Diagram versioning and XMI fidelity regression tests (audit C6, C7, A6)."""
import asyncio

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.modules.diagrams.repository import DiagramRepository
from app.modules.diagrams.service import DiagramService
from app.main import app

USER_ID = ObjectId("507f1f77bcf86cd799439051")
DIAGRAM_ID = ObjectId("507f1f77bcf86cd799439052")


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
async def _clean():
    for collection in ("diagrams", "diagram_versions", "users", "audit_logs"):
        await db_instance.db[collection].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


def _graph(nodes):
    return {"nodes": nodes, "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1.0}}


async def _seed_diagram(repo):
    created = await repo.create({
        "name": "D",
        "description": "",
        "created_by": USER_ID,
        "graph_data": _graph([{"id": "n1", "type": "class", "data": {"name": "Uno"}}]),
        "folder_id": None,
    })
    return created


async def test_create_seeds_initial_version_and_saves_append_current_state():
    """C7: the current diagram state must always be reachable from history."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    initial = await repo.get_history_entry(diagram_id, 1)
    assert initial is not None
    assert initial["graph_data"]["nodes"][0]["data"]["name"] == "Uno"

    new_graph = _graph([{"id": "n1", "type": "class", "data": {"name": "Uno"}},
                        {"id": "n2", "type": "class", "data": {"name": "Dos"}}])
    updated = await repo.save_graph(diagram_id, new_graph, str(USER_ID), "dos clases")

    assert updated["version"] == 2
    assert updated["graph_data"] == new_graph

    snapshot = await repo.get_history_entry(diagram_id, 2)
    assert snapshot["graph_data"] == new_graph
    assert snapshot["comment"] == "dos clases"


async def test_restore_creates_a_new_version_with_the_old_content():
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])
    await repo.save_graph(diagram_id, _graph([{"id": "n9", "type": "class", "data": {"name": "Nueve"}}]), str(USER_ID), "v2")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/diagrams/{diagram_id}/history/1/restore")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["version"] == 3
    assert body["graph_data"]["nodes"][0]["data"]["name"] == "Uno"

    restored = await repo.get_history_entry(diagram_id, 3)
    assert restored["graph_data"]["nodes"][0]["data"]["name"] == "Uno"


async def test_xmi_export_preserves_kind_geometry_and_multiplicity():
    """A6: shapes must map to UML types, geometry and multiplicities survive."""
    service = DiagramService(db_instance.db)
    graph = {
        "nodes": [
            {"id": "n1", "shape": "classNode", "x": 10, "y": 20, "width": 240, "height": 160,
             "data": {"name": "Usuario", "attributes": [], "methods": []}},
            {"id": "n2", "shape": "interfaceNode", "x": 300, "y": 20,
             "data": {"name": "Auditable", "attributes": [], "methods": []}},
            {"id": "n3", "shape": "enumNode", "x": 600, "y": 20,
             "data": {"name": "Estado", "attributes": [], "methods": []}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n3", "type": "association",
             "data": {"sourceMultiplicity": "1", "targetMultiplicity": "0..*"}},
            {"id": "e2", "source": "n1", "target": "n2", "type": "realization"},
        ],
    }

    xmi = await service.generate_xmi({"name": "Doc", "graph_data": graph, "_id": "x"})

    assert 'uml:Interface' in xmi
    assert 'uml:Enumeration' in xmi
    assert 'x="10"' in xmi and 'y="20"' in xmi
    assert 'width="240"' in xmi and 'height="160"' in xmi
    assert '<lowerValue' in xmi and 'value="0"' in xmi
    assert '<upperValue' in xmi and 'value="*"' in xmi
    assert 'memberEnd="e1_src e1_tgt"' in xmi

    back = service.parse_xmi(xmi)
    kinds = {n["data"]["name"]: n["type"] for n in back["nodes"]}
    assert kinds["Auditable"] == "interface"
    assert kinds["Estado"] == "enum"
    edge = next(e for e in back["edges"] if e["type"] == "association")
    assert edge["source_multiplicity"] == "1"
    assert edge["target_multiplicity"] == "0..*"


async def test_xmi_import_rejects_malformed_file_without_touching_diagram():
    """C6: invalid XML used to wipe the diagram and answer 200."""
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])
    before = await repo.get_by_id(diagram_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{diagram_id}/import/xmi",
            files={"file": ("broken.xmi", b"<not-xml", "application/xml")},
        )

    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"

    after = await repo.get_by_id(diagram_id)
    assert after["graph_data"] == before["graph_data"]
    assert after["version"] == before["version"]


async def test_xmi_import_rejects_document_without_elements():
    repo = DiagramRepository(db_instance.db)
    created = await _seed_diagram(repo)
    diagram_id = str(created["_id"])

    empty_xmi = (
        b'<?xml version="1.0"?>'
        b'<xmi:XMI xmlns:xmi="http://www.omg.org/spec/XMI/20131001" '
        b'xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">'
        b'<uml:Model xmi:id="M1" name="Empty"/></xmi:XMI>'
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{diagram_id}/import/xmi",
            files={"file": ("empty.xmi", empty_xmi, "application/xml")},
        )

    assert res.status_code == 400
