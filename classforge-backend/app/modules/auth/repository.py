from bson import ObjectId
from datetime import datetime

class SessionRepository:
    def __init__(self, db):
        self.collection = db["sessions"]

    async def create_session(self, user_id: str, refresh_token_hash: str, device_info: str, ip_address: str, expires_at: datetime):
        doc = {
            "user_id": ObjectId(user_id),
            "refresh_token_hash": refresh_token_hash,
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used": datetime.utcnow(),
            "is_active": True
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def get_active_session_by_hash(self, refresh_token_hash: str):
        return await self.collection.find_one({
            "refresh_token_hash": refresh_token_hash,
            "is_active": True
        })

    async def invalidate_session(self, session_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"is_active": False}}
        )

    async def invalidate_all_user_sessions(self, user_id: str):
        await self.collection.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"is_active": False}}
        )

    async def get_user_sessions(self, user_id: str):
        cursor = self.collection.find({"user_id": ObjectId(user_id), "is_active": True})
        return await cursor.to_list(length=100)
