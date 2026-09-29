from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId


class UserRepository:
    """Repository for managing users and audit logs in MongoDB."""

    def __init__(self, db: Any):
        self.collection = db["users"]
        self.audit = db["audit_logs"]

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Finds an active user by their email address."""
        return await self.collection.find_one({"email": email, "is_deleted": False})

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Finds an active user by their string ObjectId."""
        return await self.collection.find_one({"_id": ObjectId(user_id), "is_deleted": False})

    async def create(self, user_data: dict) -> str:
        """Creates a new user record with UTC timestamps."""
        now = datetime.now(timezone.utc)
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

    async def update(self, user_id: str, data: dict) -> None:
        """Updates user fields with updated_at timestamp."""
        data["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one({"_id": ObjectId(user_id)}, {"$set": data})

    async def soft_delete(self, user_id: str) -> None:
        """Soft-deletes a user setting is_deleted=True and deleted_at."""
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )

    async def get_all(self) -> List[Dict[str, Any]]:
        """Retrieves active users list."""
        cursor = self.collection.find({"is_deleted": False})
        return await cursor.to_list(length=100)

    async def update_last_activity(self, user_id: str) -> None:
        """Updates last_activity timestamp for session tracking."""
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_activity": datetime.now(timezone.utc)}}
        )

    async def log_audit(self, user_id: str, action: str, resource: str, resource_id: str = None, metadata: dict = None, ip: str = None) -> None:
        """Inserts an immutable audit log entry."""
        await self.audit.insert_one({
            "user_id": ObjectId(user_id) if user_id else None,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip,
            "created_at": datetime.now(timezone.utc)
        })

    async def get_audit_logs(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves recent audit log entries for a user."""
        cursor = self.audit.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        return await cursor.to_list(length=50)
