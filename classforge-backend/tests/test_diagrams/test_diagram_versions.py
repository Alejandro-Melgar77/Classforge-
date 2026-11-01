# -*- coding: utf-8 -*-
"""
Pruebas de la arquitectura de versiones desacopladas de diagramas (P9 Bloque B):
1. Desacoplamiento de historial hacia colección diagram_versions.
2. Limpieza del array embebido 'history' en documentos de diagramas.
3. Endpoints /history y /history/{version}.
4. Script de migración idempotente y rollback.
5. Verificación de proyecciones en listado de diagramas.
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import db_instance
from app.modules.diagrams.repository import DiagramRepository
from app.modules.diagrams.service import DiagramService
from scripts.migrate_diagram_versions import (
    migrate_diagram_versions,
    rollback_diagram_versions,
    verify_versions,
)


@pytest.fixture
def repo():
    return DiagramRepository(db_instance.db)


@pytest.fixture
def service():
    return DiagramService(db_instance.db)


@pytest.mark.asyncio
async def test_save_graph_creates_version_in_diagram_versions(repo):
    db = db_instance.db
    # Create a diagram
    user_id = ObjectId()
    diagram_doc = {
        "name": "Diagrama de Prueba",
        "description": "Prueba de versiones desacopladas",
        "project_id": ObjectId(),
        "created_by": user_id,
        "is_deleted": False,
        "status": "draft",
        "version": 1,
        "graph_data": {"nodes": [{"id": "n1"}], "edges": []},
    }
    inserted = await repo.collection.insert_one(diagram_doc)
    diagram_id = str(inserted.inserted_id)

    # Save graph (first update)
    new_graph = {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": [{"source": "n1", "target": "n2"}]}
    updated = await repo.save_graph(diagram_id, new_graph, str(user_id), "Agregado nodo n2")

    assert updated["version"] == 2
    assert updated["graph_data"] == new_graph
    assert "history" not in updated or not updated["history"]

    # Verify document in diagram_versions collection
    version_doc = await repo.versions_collection.find_one({
        "diagram_id": ObjectId(diagram_id),
        "version": 1
    })
    assert version_doc is not None
    assert version_doc["comment"] == "Agregado nodo n2"
    assert version_doc["graph_data"] == {"nodes": [{"id": "n1"}], "edges": []}


@pytest.mark.asyncio
async def test_list_and_get_history_entry(repo):
    user_id = ObjectId()
    diagram_doc = {
        "name": "Diagrama Iterativo",
        "project_id": ObjectId(),
        "created_by": user_id,
        "is_deleted": False,
        "version": 1,
        "graph_data": {"v": 1},
    }
    inserted = await repo.collection.insert_one(diagram_doc)
    diagram_id = str(inserted.inserted_id)

    # Save multiple versions
    await repo.save_graph(diagram_id, {"v": 2}, str(user_id), "Versión 2")
    await repo.save_graph(diagram_id, {"v": 3}, str(user_id), "Versión 3")

    # List history
    history = await repo.list_history(diagram_id)
    assert len(history) == 2
    # Verify descending version order
    assert history[0]["version"] == 2
    assert history[1]["version"] == 1
    # graph_data should NOT be present in list_history projection
    assert "graph_data" not in history[0]

    # Get single history entry (must include graph_data)
    entry_v1 = await repo.get_history_entry(diagram_id, 1)
    assert entry_v1 is not None
    assert entry_v1["version"] == 1
    assert entry_v1["graph_data"] == {"v": 1}
    assert entry_v1["comment"] == "Versión 2"


@pytest.mark.asyncio
async def test_migration_script_idempotent_and_rollback():
    db = db_instance.db
    user_id = ObjectId()

    # Seed legacy diagram with embedded history
    legacy_doc = {
        "name": "Legacy Diagram",
        "project_id": ObjectId(),
        "created_by": user_id,
        "is_deleted": False,
        "version": 3,
        "graph_data": {"nodes": ["final"]},
        "history": [
            {
                "version": 1,
                "graph_data": {"nodes": ["initial"]},
                "saved_by": user_id,
                "saved_at": datetime.now(timezone.utc),
                "comment": "Inicio",
            },
            {
                "version": 2,
                "graph_data": {"nodes": ["mid"]},
                "saved_by": user_id,
                "saved_at": datetime.now(timezone.utc),
                "comment": "Mitad",
            }
        ]
    }
    res = await db["diagrams"].insert_one(legacy_doc)
    diag_id = res.inserted_id

    # 1. Run migration forward
    summary = await migrate_diagram_versions(db)
    assert summary["total_diagrams"] >= 1
    assert summary["saved_bytes"] > 0
    assert summary["savings_percentage"] > 0

    # Verify diagram document has no embedded history
    migrated_doc = await db["diagrams"].find_one({"_id": diag_id})
    assert "history" not in migrated_doc

    # Verify entries exist in diagram_versions
    v1 = await db["diagram_versions"].find_one({"diagram_id": diag_id, "version": 1})
    assert v1 is not None
    assert v1["comment"] == "Inicio"

    # 2. Test Idempotence: running migration again produces 0 errors and handles empty history cleanly
    summary2 = await migrate_diagram_versions(db)
    assert summary2["total_diagrams"] == 0

    # 3. Test Rollback
    await rollback_diagram_versions(db)
    rolled_back_doc = await db["diagrams"].find_one({"_id": diag_id})
    assert "history" in rolled_back_doc
    assert len(rolled_back_doc["history"]) == 2

    # 4. Migrate again to leave clean state
    await migrate_diagram_versions(db)
    is_clean = await verify_versions(db)
    assert is_clean is True


@pytest.mark.asyncio
async def test_list_diagrams_does_not_project_graph_data(repo):
    user_id = ObjectId()
    diagram_doc = {
        "name": "Diagrama Pesado",
        "project_id": ObjectId(),
        "created_by": user_id,
        "is_deleted": False,
        "graph_data": {"huge_payload": "X" * 10000},
        "history": [{"v": 1}],
        "xmi_data": "<xml>huge</xml>",
    }
    await repo.collection.insert_one(diagram_doc)

    items = await repo.list_diagrams({"created_by": user_id})
    assert len(items) >= 1
    item = items[0]
    # Check that heavy fields were stripped by projection
    assert "graph_data" not in item
    assert "history" not in item
    assert "xmi_data" not in item
    assert "name" in item
