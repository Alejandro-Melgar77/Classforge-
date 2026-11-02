"""RBAC and identity-hardening regression tests (audit C2, A7, A9, A10, A11)."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import db_instance
from app.core.dependencies import get_current_user
from app.core.security import hash_refresh_token
from app.main import app

DEV_ID = ObjectId("507f1f77bcf86cd799439012")
OTHER_ID = ObjectId("507f1f77bcf86cd799439013")
TEAM_ID = ObjectId("607f1f77bcf86cd799439014")


def _dev(role="dev", team_ids=None):
    return {
        "_id": DEV_ID,
        "id": str(DEV_ID),
        "name": "Dev",
        "email": "dev@example.com",
        "role": role,
        "is_active": True,
        "is_deleted": False,
        "team_ids": team_ids or [],
    }


def _override(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
async def _clean():
    db = db_instance.db
    for collection in ("users", "teams", "sessions", "audit_logs"):
        await db[collection].delete_many({})
    yield
    app.dependency_overrides.clear()


async def _seed_user(doc):
    await db_instance.db["users"].insert_one(doc)


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_dev_cannot_promote_self_to_admin():
    """C2: PUT /users/{id} must reject privileged fields for non-admins."""
    await _seed_user(_dev())
    _override(_dev())

    async with await _client() as ac:
        res = await ac.put(f"/api/v1/users/{DEV_ID}", json={"role": "admin"})

    assert res.status_code == 403
    stored = await db_instance.db["users"].find_one({"_id": DEV_ID})
    assert stored["role"] == "dev"


async def test_dev_cannot_toggle_own_active_flag_or_email():
    await _seed_user(_dev())
    _override(_dev())

    async with await _client() as ac:
        inactive = await ac.put(f"/api/v1/users/{DEV_ID}", json={"is_active": False})
        email = await ac.put(f"/api/v1/users/{DEV_ID}", json={"email": "other@example.com"})

    assert inactive.status_code == 403
    assert email.status_code == 403


async def test_dev_can_update_own_name():
    await _seed_user(_dev())
    _override(_dev())

    async with await _client() as ac:
        res = await ac.put(f"/api/v1/users/{DEV_ID}", json={"name": "Nuevo Nombre"})

    assert res.status_code == 200
    stored = await db_instance.db["users"].find_one({"_id": DEV_ID})
    assert stored["name"] == "Nuevo Nombre"


async def test_admin_can_change_role_and_invalid_role_rejected():
    await _seed_user(_dev())
    await _seed_user({**_dev(), "_id": OTHER_ID, "email": "other@example.com"})
    _override(_dev(role="admin"))

    async with await _client() as ac:
        ok = await ac.put(f"/api/v1/users/{OTHER_ID}", json={"role": "scrum_master"})
        # admin may not invent roles
        bad = await ac.put(f"/api/v1/users/{OTHER_ID}", json={"role": "superuser"})

    assert ok.status_code == 200
    assert bad.status_code in (400, 422)


async def test_user_listing_is_admin_only():
    """A7: the full user table must not be readable by a dev."""
    await _seed_user(_dev())
    _override(_dev())

    async with await _client() as ac:
        as_dev = await ac.get("/api/v1/users/")

    assert as_dev.status_code == 403

    _override(_dev(role="admin"))
    async with await _client() as ac:
        as_admin = await ac.get("/api/v1/users/")

    assert as_admin.status_code == 200


async def test_user_directory_is_scoped_to_shared_teams():
    await db_instance.db["teams"].insert_one({
        "_id": TEAM_ID,
        "name": "Team",
        "member_ids": [DEV_ID, OTHER_ID],
        "scrum_master_id": OTHER_ID,
        "is_deleted": False,
    })
    outsider = ObjectId("507f1f77bcf86cd799439099")
    await _seed_user(_dev(team_ids=[str(TEAM_ID)]))
    await _seed_user({**_dev(), "_id": OTHER_ID, "email": "other@example.com"})
    await _seed_user({**_dev(), "_id": outsider, "email": "out@example.com"})
    _override(_dev(team_ids=[str(TEAM_ID)]))

    async with await _client() as ac:
        res = await ac.get("/api/v1/users/directory")

    assert res.status_code == 200
    ids = {row["id"] for row in res.json()["data"]}
    assert str(DEV_ID) in ids
    assert str(OTHER_ID) in ids
    assert str(outsider) not in ids
    assert all(set(row) == {"id", "name", "role"} for row in res.json()["data"])


async def test_sessions_never_expose_refresh_token_hash():
    """A9: /auth/sessions must return a public projection."""
    await _seed_user(_dev())
    await db_instance.db["sessions"].insert_one({
        "_id": ObjectId(),
        "user_id": DEV_ID,
        "refresh_token_hash": "deadbeef" * 8,
        "device_info": "pytest",
        "ip_address": "127.0.0.1",
        "is_active": True,
        "created_at": None,
        "last_used": None,
        "expires_at": None,
    })
    _override(_dev())

    async with await _client() as ac:
        res = await ac.get("/api/v1/auth/sessions")

    assert res.status_code == 200
    assert "refresh_token_hash" not in res.text
    assert "deadbeef" not in res.text


@pytest.mark.parametrize("role", ["dev", "admin"])
async def test_refresh_rejects_disabled_user(role):
    """A10: a disabled/deleted account must not be able to refresh tokens."""
    user = {**_dev(role=role), "is_active": False}
    await _seed_user(user)
    raw = "refresh-token-abc"
    await db_instance.db["sessions"].insert_one({
        "_id": ObjectId(),
        "user_id": DEV_ID,
        "refresh_token_hash": hash_refresh_token(raw),
        "device_info": "pytest",
        "ip_address": "127.0.0.1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_used": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })

    async with await _client() as ac:
        res = await ac.post("/api/v1/auth/refresh", json={"refresh_token": raw})

    assert res.status_code == 401


async def test_register_rejects_weak_password():
    """A11: password policy is enforced at the API boundary."""
    async with await _client() as ac:
        res = await ac.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "1234", "name": "Weak"},
        )
    assert res.status_code == 422
