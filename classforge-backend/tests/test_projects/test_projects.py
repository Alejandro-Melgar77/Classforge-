import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_projects(async_client: AsyncClient, admin_token_headers):
    response = await async_client.get("/api/v1/projects/", headers=admin_token_headers)
    assert response.status_code == 200
    assert "data" in response.json()

@pytest.mark.asyncio
async def test_create_personal_project(async_client: AsyncClient, admin_token_headers):
    data = {
        "name": "My Personal Project",
        "description": "Just testing",
        "type": "personal",
        "tags": ["test"]
    }
    response = await async_client.post("/api/v1/projects/", json=data, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My Personal Project"
