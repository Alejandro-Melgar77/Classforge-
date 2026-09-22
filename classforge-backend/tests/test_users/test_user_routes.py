import pytest

@pytest.mark.asyncio
async def test_get_users_unauthorized(client):
    response = await client.get("/api/v1/users/")
    assert response.status_code == 403
