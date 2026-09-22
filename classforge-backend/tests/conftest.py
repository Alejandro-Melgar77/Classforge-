import pytest
import os
import asyncio
from httpx import AsyncClient
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, db_instance

os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
os.environ["DATABASE_NAME"] = "classforge_test"
os.environ["SECRET_KEY"] = "test"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
