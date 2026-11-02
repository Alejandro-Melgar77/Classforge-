"""Regression test for A18: Notification fan-out reaches project owner_id."""
import pytest
from bson import ObjectId

from app.core.database import db_instance
from app.modules.notifications.service import NotificationService

OWNER_ID = ObjectId("507f1f77bcf86cd799439095")
PROJECT_ID = ObjectId("607f1f77bcf86cd799439096")


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("notifications", "projects", "teams", "users"):
        await db_instance.db[collection].delete_many({})
    yield


async def test_notification_fanout_delivers_to_project_owner():
    """A18: Project notifications must use owner_id (not created_by) so the owner receives them."""
    await db_instance.db["projects"].insert_one({
        "_id": PROJECT_ID,
        "name": "Project Alpha",
        "owner_id": OWNER_ID,
        "type": "personal",
        "is_deleted": False,
    })

    service = NotificationService(db_instance.db)
    count = await service.notify_project_members(
        project_id=str(PROJECT_ID),
        title="Actualización del Proyecto",
        message="Se ha generado un nuevo artefacto",
        type="project_update",
    )

    assert count >= 1

    stored = await db_instance.db["notifications"].find_one({"user_id": OWNER_ID})
    assert stored is not None
    assert stored["title"] == "Actualización del Proyecto"
    assert stored["is_read"] is False
