"""Audit, notification and idempotency regressions (audit A17, A18, M4)."""
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.core.database import db_instance
from app.modules.diagrams.service import DiagramService
from app.modules.diagrams.schemas import CreateDiagram
from app.modules.notifications.service import NotificationService

OWNER_ID = ObjectId("507f1f77bcf86cd799439091")
MEMBER_ID = ObjectId("507f1f77bcf86cd799439092")
PROJECT_ID = ObjectId("607f1f77bcf86cd799439093")


def _owner():
    return {
        "_id": OWNER_ID,
        "id": str(OWNER_ID),
        "name": "Owner",
        "email": "owner@example.com",
        "role": "scrum_master",
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    }


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("diagrams", "diagram_versions", "audit_logs", "notifications",
                       "projects", "teams", "users"):
        await db_instance.db[collection].delete_many({})
    yield


async def test_audit_log_uses_the_canonical_schema():
    """A17: every audit entry must carry created_at/resource/resource_id."""
    await db_instance.db["projects"].insert_one({
        "_id": PROJECT_ID,
        "name": "P",
        "owner_id": OWNER_ID,
        "type": "personal",
        "is_deleted": False,
    })

    service = DiagramService(db_instance.db)
    diagram = await service.create_diagram(
        CreateDiagram(name="D", project_id=str(PROJECT_ID)), _owner()
    )

    entry = await db_instance.db["audit_logs"].find_one({"action": "CREATE_DIAGRAM"})
    assert entry is not None
    assert entry["created_at"] is not None
    assert entry["resource"] == "diagrams"
    assert entry["resource_id"] == str(diagram["_id"])

    # The dashboard sorts and reads these fields.
    assert "timestamp" not in entry


async def test_notify_project_members_reaches_the_owner():
    """A18: fan-out used a non-existent `created_by` field and missed the owner."""
    await db_instance.db["projects"].insert_one({
        "_id": PROJECT_ID,
        "name": "P",
        "owner_id": OWNER_ID,
        "type": "personal",
        "is_deleted": False,
    })

    service = NotificationService(db_instance.db)
    created = await service.notify_project_members(
        project_id=str(PROJECT_ID),
        title="Cambio",
        message="Se actualizó el proyecto",
        type="project_update",
    )

    assert created >= 1
    stored = await db_instance.db["notifications"].find_one({"user_id": OWNER_ID})
    assert stored is not None
    assert stored["title"] == "Cambio"


async def test_participant_assignment_notifies_and_audits():
    now = datetime.now(timezone.utc)
    diagram_id = ObjectId()
    await db_instance.db["diagrams"].insert_one({
        "_id": diagram_id,
        "name": "Modelo",
        "created_by": OWNER_ID,
        "member_ids": [],
        "team_id": None,
        "project_id": None,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    })

    service = DiagramService(db_instance.db)
    await service.update_diagram_participants(str(diagram_id), [str(MEMBER_ID)], _owner())

    notification = await db_instance.db["notifications"].find_one({"user_id": MEMBER_ID})
    assert notification is not None
    assert notification["type"] == "diagram_assignment"

    audit = await db_instance.db["audit_logs"].find_one({"action": "UPDATE_PARTICIPANTS"})
    assert audit is not None
    assert audit["metadata"]["added"] == [str(MEMBER_ID)]


async def test_mark_as_read_is_idempotent():
    """M4: a second mark-as-read used to answer 404."""
    notif_id = ObjectId()
    await db_instance.db["notifications"].insert_one({
        "_id": notif_id,
        "user_id": OWNER_ID,
        "title": "T",
        "message": "M",
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    })

    service = NotificationService(db_instance.db)
    assert await service.mark_as_read(str(notif_id), str(OWNER_ID)) is True
    assert await service.mark_as_read(str(notif_id), str(OWNER_ID)) is True


async def test_folder_rename_is_idempotent():
    """M4: renaming a folder to its current name used to answer 404."""
    folder_id = ObjectId()
    now = datetime.now(timezone.utc)
    await db_instance.db["folders"].insert_one({
        "_id": folder_id,
        "name": "Igual",
        "owner_id": OWNER_ID,
        "team_id": None,
        "project_id": None,
        "type": "personal",
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    })

    from app.modules.folders.schemas import FolderUpdate
    from app.modules.folders.service import FolderService

    service = FolderService(db_instance.db)
    renamed = await service.rename_folder(str(folder_id), FolderUpdate(name="Igual"))
    assert renamed["name"] == "Igual"
