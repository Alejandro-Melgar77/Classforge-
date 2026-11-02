"""Vision output contract tests (audit C5, A28).

Vision used to emit ``{"shape": "class-node", "cells": [...]}``; the diagram
endpoint persisted it verbatim, so the canvas (which reads ``nodes``/``edges``
and X6-registered shapes) rendered an empty diagram.
"""
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import app.modules.ai.vision_service as vision_service
from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app

USER_ID = ObjectId("507f1f77bcf86cd799439061")
DIAGRAM_ID = ObjectId("507f1f77bcf86cd799439062")

SEMANTICS = {
    "classes": [
        {"name": "Usuario", "attributes": [{"name": "id", "type": "Long"}],
         "methods": [{"name": "login", "returnType": "Boolean"}], "isInterface": False},
        {"name": "Auditable", "attributes": [], "methods": [], "isInterface": True},
    ],
    "relationships": [
        {"source": "Usuario", "target": "Auditable", "type": "realization",
         "sourceMultiplicity": "1", "targetMultiplicity": "1"},
    ],
    "summary": "ok",
}


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
    for collection in ("diagrams", "diagram_versions", "users", "notifications"):
        await db_instance.db[collection].delete_many({})
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield
    app.dependency_overrides.clear()


def test_convert_semantics_emits_canonical_graph():
    graph = vision_service.convert_semantics_to_graph_data(SEMANTICS)

    assert "nodes" in graph and "edges" in graph
    assert "cells" not in graph
    assert len(graph["nodes"]) == 2

    by_name = {n["data"]["name"]: n for n in graph["nodes"]}
    assert by_name["Usuario"]["type"] == "class"
    assert by_name["Usuario"]["shape"] == "uml-class"
    assert by_name["Auditable"]["type"] == "interface"
    assert by_name["Auditable"]["shape"] == "uml-interface"

    usuario = by_name["Usuario"]
    assert usuario["position"]["x"] >= 0 and usuario["position"]["y"] >= 0
    assert usuario["size"]["width"] == 240
    assert usuario["data"]["attributes"][0]["name"] == "id"
    assert usuario["data"]["methods"][0]["return_type"] == "Boolean"

    edge = graph["edges"][0]
    assert edge["type"] == "realization"
    assert edge["data"]["sourceMultiplicity"] == "1"


async def test_from_image_endpoint_persists_renderable_graph(monkeypatch):
    now = None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    await db_instance.db["diagrams"].insert_one({
        "_id": DIAGRAM_ID,
        "name": "Escaneado",
        "created_by": USER_ID,
        "member_ids": [],
        "team_id": None,
        "project_id": None,
        "graph_data": {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1.0}},
        "is_deleted": False,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    })

    async def fake_vision(image_bytes, mime_type="image/jpeg", api_key=None, model=None):
        return {
            "graph_data": vision_service.convert_semantics_to_graph_data(SEMANTICS),
            "semantics": SEMANTICS,
            "summary": "ok",
            "total_classes": 2,
            "total_relationships": 1,
            "model_used": "fake",
        }

    monkeypatch.setattr(vision_service, "generate_diagram_from_image", fake_vision)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/diagrams/{DIAGRAM_ID}/from-image",
            json={"image_base64": "aGVsbG8=", "mime_type": "image/png"},
        )

    assert res.status_code == 200, res.text

    stored = await db_instance.db["diagrams"].find_one({"_id": DIAGRAM_ID})
    graph = stored["graph_data"]
    assert len(graph["nodes"]) == 2
    assert {n["shape"] for n in graph["nodes"]} == {"uml-class", "uml-interface"}
    assert all(n["id"] for n in graph["nodes"])
