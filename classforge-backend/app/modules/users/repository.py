from bson import ObjectId
from datetime import datetime

class UserRepository:
    def __init__(self, db):
        self.collection = db["users"]
        self.audit = db["audit_logs"]

    async def get_by_email(self, email: str):
        return await self.collection.find_one({"email": email, "is_deleted": False})

    async def get_by_id(self, user_id: str):
        return await self.collection.find_one({"_id": ObjectId(user_id), "is_deleted": False})

    async def create(self, user_data: dict):
        now = datetime.utcnow()
        user_data.update({
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "is_deleted": False,
            "deleted_at": None,
            "last_activity": now
        })
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)

    async def update(self, user_id: str, data: dict):
        data["updated_at"] = datetime.utcnow()
        await self.collection.update_one({"_id": ObjectId(user_id)}, {"$set": data})

    async def soft_delete(self, user_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow()}}
        )

    async def get_all(self):
        cursor = self.collection.find({"is_deleted": False})
        return await cursor.to_list(length=100)

    async def update_last_activity(self, user_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_activity": datetime.utcnow()}}
        )

    async def log_audit(self, user_id: str, action: str, resource: str, resource_id: str = None, metadata: dict = None, ip: str = None):
        await self.audit.insert_one({
            "user_id": ObjectId(user_id) if user_id else None,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip,
            "created_at": datetime.utcnow()
        })

    async def get_audit_logs(self, user_id: str):
        cursor = self.audit.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        return await cursor.to_list(length=100)
