"""Folder authorization regression tests (audit C3 — IDOR)."""
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.main import app

OWNER_ID = ObjectId("507f1f77bcf86cd799439021")
INTRUDER_ID = ObjectId("507f1f77bcf86cd799439022")
FOLDER_ID = ObjectId("507f1f77bcf86cd799439023")


def _user(oid, role="dev", team_ids=None):
    return {
        "_id": oid,
        "id": str(oid),
        "name": str(oid),
        "email": f"{oid}@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": team_ids or [],
    }


def _override(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
async def _clean():
    for collection in ("folders", "users", "teams", "projects"):
        await db_instance.db[collection].delete_many({})
    yield
    app.dependency_overrides.clear()


async def _seed_folder():
    now = datetime.now(timezone.utc)
    await db_instance.db["folders"].insert_one({
        "_id": FOLDER_ID,
        "name": "Privada",
        "owner_id": OWNER_ID,
        "team_id": None,
        "project_id": None,
        "parent_folder_id": None,
        "type": "personal",
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    })


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.parametrize("method", ["get", "put", "delete"])
async def test_intruder_cannot_touch_foreign_folder(method):
    """C3: folders owned by someone else must be invisible to other users."""
    await _seed_folder()
    _override(_user(INTRUDER_ID))

    async with await _client() as ac:
        kwargs = {"json": {"name": "hackeada"}} if method == "put" else {}
        res = await getattr(ac, method)(f"/api/v1/folders/{FOLDER_ID}", **kwargs)

    assert res.status_code == 403
    stored = await db_instance.db["folders"].find_one({"_id": FOLDER_ID})
    assert stored["name"] == "Privada"
    assert stored["is_deleted"] is False


async def test_owner_can_read_and_rename():
    await _seed_folder()
    _override(_user(OWNER_ID))

    async with await _client() as ac:
        read = await ac.get(f"/api/v1/folders/{FOLDER_ID}")
        renamed = await ac.put(f"/api/v1/folders/{FOLDER_ID}", json={"name": "Renombrada"})

    assert read.status_code == 200
    assert renamed.status_code == 200
    stored = await db_instance.db["folders"].find_one({"_id": FOLDER_ID})
    assert stored["name"] == "Renombrada"


async def test_team_member_can_access_team_folder():
    team_id = ObjectId("607f1f77bcf86cd799439024")
    await db_instance.db["teams"].insert_one({
        "_id": team_id,
        "name": "T",
        "member_ids": [INTRUDER_ID],
        "scrum_master_id": OWNER_ID,
        "is_deleted": False,
    })
    await _seed_folder()
    await db_instance.db["folders"].update_one(
        {"_id": FOLDER_ID}, {"$set": {"team_id": team_id, "type": "team"}}
    )
    _override(_user(INTRUDER_ID, team_ids=[str(team_id)]))

    async with await _client() as ac:
        res = await ac.get(f"/api/v1/folders/{FOLDER_ID}")

    assert res.status_code == 200


async def test_missing_folder_returns_404():
    _override(_user(INTRUDER_ID))
    async with await _client() as ac:
        res = await ac.get(f"/api/v1/folders/{ObjectId()}")
    assert res.status_code == 404
