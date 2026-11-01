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
    await db_instance.db["users"].create_index("email", unique=True)
    await db_instance.db["sessions"].create_index("refresh_token_hash", unique=True)
    await db_instance.db["sessions"].create_index("expires_at", expireAfterSeconds=0)
    await db_instance.db["teams"].create_index("scrum_master_id")
    await db_instance.db["teams"].create_index("member_ids")
    await db_instance.db["projects"].create_index("team_id")
    await db_instance.db["projects"].create_index("owner_id")
    await db_instance.db["projects"].create_index("status")
    await db_instance.db["folders"].create_index("owner_id")
    await db_instance.db["folders"].create_index("project_id")
    await db_instance.db["diagrams"].create_index("project_id")
    await db_instance.db["diagrams"].create_index([("project_id", 1), ("is_deleted", 1)])
    await db_instance.db["diagrams"].create_index("member_ids")
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
    # Indexes for AI chat collections (P4 scalable model)
    await db_instance.db["ai_messages"].create_index([("project_id", 1), ("created_at", -1)])
    await db_instance.db["ai_messages"].create_index(
        [("project_id", 1), ("thread", 1), ("owner_id", 1), ("created_at", -1)]
    )
    await db_instance.db["ai_messages"].create_index(
        [("project_id", 1), ("client_id", 1)],
        unique=True,
        partialFilterExpression={"client_id": {"$type": "string"}},
    )
    await db_instance.db["ai_project_state"].create_index("project_id", unique=True)
    await db_instance.db["ai_conversations"].create_index("project_id", unique=True)
    await db_instance.db["ai_conversations"].create_index([("updated_at", -1)])
    await db_instance.db["ai_tasks"].create_index("project_id")
    await db_instance.db["ai_tasks"].create_index("status")
    await db_instance.db["ai_tasks"].create_index([("created_at", -1)])
    # Indexes for AI usage (P2)
    await db_instance.db["ai_usage"].create_index([("project_id", 1), ("created_at", -1)])
    await db_instance.db["ai_usage"].create_index([("user_id", 1), ("created_at", -1)])
    # Index for project ws_tokens
    await db_instance.db["ws_tokens"].create_index("project_id")
    # Indexes for AI background jobs (P5 Bloque A)
    await db_instance.db["ai_jobs"].create_index([("status", 1), ("run_after", 1)])
    await db_instance.db["ai_jobs"].create_index([("project_id", 1), ("status", 1)])
    await db_instance.db["ai_jobs"].create_index([("lease_until", 1)])
    await db_instance.db["ai_jobs"].create_index([("created_at", -1)])
    await db_instance.db["ai_jobs"].create_index(
        "dedupe_key",
        partialFilterExpression={"dedupe_key": {"$type": "string"}},
    )
    # Indexes for AI findings lifecycle (P5 Bloque C)
    await db_instance.db["ai_findings"].create_index([("project_id", 1), ("diagram_id", 1), ("status", 1)])
    await db_instance.db["ai_findings"].create_index([("diagram_id", 1), ("fingerprint", 1)])
    await db_instance.db["ai_findings"].create_index([("project_id", 1), ("last_seen", -1)])

    # Indexes for diagram_versions collection (P9 Bloque B)
    await db_instance.db["diagram_versions"].create_index([("diagram_id", 1), ("version", -1)], unique=True)
    await db_instance.db["diagram_versions"].create_index([("diagram_id", 1), ("created_at", -1)])
    await db_instance.db["diagram_versions"].create_index([("created_at", -1)])

    # Query performance compound indexes for listings (P9 Bloque B)
    await db_instance.db["diagrams"].create_index([("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["diagrams"].create_index([("project_id", 1), ("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["diagrams"].create_index([("team_id", 1), ("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["diagrams"].create_index([("created_by", 1), ("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["diagrams"].create_index([("member_ids", 1), ("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["projects"].create_index([("is_deleted", 1), ("created_at", -1)])
    await db_instance.db["projects"].create_index([("owner_id", 1), ("is_deleted", 1)])
    await db_instance.db["projects"].create_index([("team_id", 1), ("is_deleted", 1)])


async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()

def get_db():
    return db_instance.db
