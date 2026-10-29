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
    # Performance indexes for audit_logs and notifications
    await db_instance.db["audit_logs"].create_index([("timestamp", -1)])
    await db_instance.db["audit_logs"].create_index("user_id")
    await db_instance.db["notifications"].create_index([("user_id", 1), ("is_read", 1)])
    await db_instance.db["notifications"].create_index([("created_at", -1)])
    # Indexes for AI chat collections
    await db_instance.db["ai_conversations"].create_index("project_id", unique=True)
    await db_instance.db["ai_conversations"].create_index([("updated_at", -1)])
    await db_instance.db["ai_tasks"].create_index("project_id")
    await db_instance.db["ai_tasks"].create_index("status")
    await db_instance.db["ai_tasks"].create_index([("created_at", -1)])

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()

def get_db():
    return db_instance.db
