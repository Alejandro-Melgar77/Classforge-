from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]
    
    # Create indexes for new collections
    await db_instance.db["teams"].create_index("scrum_master_id")
    await db_instance.db["teams"].create_index("member_ids")
    await db_instance.db["projects"].create_index("team_id")
    await db_instance.db["projects"].create_index("owner_id")
    await db_instance.db["projects"].create_index("status")
    await db_instance.db["folders"].create_index("owner_id")
    await db_instance.db["folders"].create_index("project_id")
    await db_instance.db["diagrams"].create_index("project_id")
    await db_instance.db["diagrams"].create_index("team_id")
    await db_instance.db["diagrams"].create_index("created_by")
    await db_instance.db["diagrams"].create_index("status")
    await db_instance.db["ws_tokens"].create_index("token", unique=True)
    await db_instance.db["ws_tokens"].create_index("expires_at", expireAfterSeconds=0)

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()

def get_db():
    return db_instance.db
