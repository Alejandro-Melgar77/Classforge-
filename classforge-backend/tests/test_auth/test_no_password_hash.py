import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_current_user, get_user_repository
from bson import ObjectId


class MockUserRepo:
    def __init__(self, sample_user):
        self.sample_user = sample_user

    async def get_by_id(self, user_id):
        return dict(self.sample_user)

    async def get_all(self):
        return [dict(self.sample_user)]

    async def update(self, user_id, update_fields):
        self.sample_user.update(update_fields)

    async def log_audit(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_no_password_hash_in_auth_and_users_responses():
    sample_user = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "name": "Security Test User",
        "email": "security@classforge.dev",
        "role": "admin",
        "avatar_url": "https://example.com/avatar.png",
        "team_ids": ["607f1f77bcf86cd799439022"],
        "is_active": True,
        "password_hash": "super_secret_argon2_or_bcrypt_hash_that_must_never_leak",
    }

    mock_repo = MockUserRepo(sample_user)

    async def mock_get_current_user():
        return dict(sample_user)

    def mock_get_user_repository():
        return mock_repo

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_user_repository] = mock_get_user_repository

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. GET /api/v1/auth/me
            res_me = await ac.get("/api/v1/auth/me")
            assert res_me.status_code == 200
            assert "password_hash" not in res_me.text
            data_me = res_me.json()["data"]
            assert data_me["id"] == str(sample_user["_id"])
            assert data_me["email"] == "security@classforge.dev"
            assert "password_hash" not in data_me

            # 2. PUT /api/v1/auth/profile
            res_profile = await ac.put("/api/v1/auth/profile", json={"name": "New Name"})
            assert res_profile.status_code == 200
            assert "password_hash" not in res_profile.text
            data_profile = res_profile.json()["data"]
            assert "password_hash" not in data_profile

            # 3. GET /api/v1/users/{user_id}
            res_user = await ac.get(f"/api/v1/users/{str(sample_user['_id'])}")
            assert res_user.status_code == 200
            assert "password_hash" not in res_user.text
            data_user = res_user.json()["data"]
            assert "password_hash" not in data_user

            # 4. GET /api/v1/users/
            res_list = await ac.get("/api/v1/users/")
            assert res_list.status_code == 200
            assert "password_hash" not in res_list.text
            for u in res_list.json()["data"]:
                assert "password_hash" not in u
    finally:
        app.dependency_overrides.clear()
