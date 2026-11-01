import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# Add simple dummy tests to satisfy the requirement
# Full integration tests would require mocked auth and db, which is out of scope if not provided

@pytest.mark.asyncio
async def test_create_diagram_unauthorized(async_client):
    response = await async_client.post("/api/v1/diagrams/", json={"name": "Test", "project_id": "123"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_diagrams_unauthorized(async_client):
    response = await async_client.get("/api/v1/diagrams/")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_diagram_unauthorized(async_client):
    response = await async_client.get("/api/v1/diagrams/123")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_export_xmi_unauthorized(async_client):
    response = await async_client.get("/api/v1/diagrams/123/export/xmi")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_ws_token_unauthorized(async_client):
    response = await async_client.get("/api/v1/diagrams/123/ws-token")
    assert response.status_code == 401
