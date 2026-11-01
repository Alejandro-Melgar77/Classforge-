import os
import sys
from pathlib import Path
import logging
import pytest
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

logger = logging.getLogger(__name__)

# Respect environment variables with sensible defaults
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "classforge_test")
os.environ.setdefault("SECRET_KEY", "test")

# Synchronize settings with environment variables
settings.MONGODB_URL = os.environ["MONGODB_URL"]
settings.DATABASE_NAME = os.environ["DATABASE_NAME"]
settings.SECRET_KEY = os.environ["SECRET_KEY"]

from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, db_instance
from app.core.security import create_access_token

_mongo_checked = False
_mongo_available = False


async def check_mongo_connectivity() -> bool:
    """Check if MongoDB is reachable with a short timeout."""
    global _mongo_checked, _mongo_available
    if _mongo_checked:
        return _mongo_available

    test_client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=1000)
    try:
        await test_client.admin.command("ping")
        _mongo_available = True
    except Exception as exc:
        _mongo_available = False
        print(f"\n[AVISO] MongoDB no disponible en {settings.MONGODB_URL} ({exc}). Tests dependientes de DB fallarán o se omitirán.")
    finally:
        test_client.close()
        _mongo_checked = True

    return _mongo_available


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_db():
    is_up = await check_mongo_connectivity()
    if is_up:
        try:
            await connect_to_mongo()
        except Exception as exc:
            print(f"\n[AVISO] Error al conectar con MongoDB en {settings.MONGODB_URL}: {exc}")
        yield
        try:
            await close_mongo_connection()
        except Exception:
            pass
    else:
        from mongomock_motor import AsyncMongoMockClient
        from bson import ObjectId
        mock_client = AsyncMongoMockClient()
        db_instance.client = mock_client
        db_instance.db = mock_client[settings.DATABASE_NAME]

        # Seed default admin user matching admin_token_headers
        admin_oid = ObjectId("507f1f77bcf86cd799439011")
        await db_instance.db["users"].update_one(
            {"_id": admin_oid},
            {"$set": {
                "_id": admin_oid,
                "name": "Admin Test",
                "email": "admin@example.com",
                "role": "admin",
                "is_active": True,
                "is_deleted": False,
                "team_ids": []
            }},
            upsert=True
        )
        yield
        db_instance.client = None
        db_instance.db = None


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def async_client(client):
    yield client


@pytest.fixture
def admin_token_headers():
    token = create_access_token(subject="507f1f77bcf86cd799439011")
    return {"Authorization": f"Bearer {token}"}
