from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId


class SessionRepository:
    """Repository handling persistence and revocation of refresh token sessions."""

    def __init__(self, db: Any) -> None:
        self.collection = db["sessions"]

    async def create_session(
        self,
        user_id: str,
        refresh_token_hash: str,
        device_info: str,
        ip_address: str,
        expires_at: datetime
    ) -> str:
        """Create a new active session record for a user device."""
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": ObjectId(user_id),
            "refresh_token_hash": refresh_token_hash,
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": now,
            "expires_at": expires_at,
            "last_used": now,
            "is_active": True
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def get_active_session_by_hash(self, refresh_token_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve an active session by its hashed refresh token."""
        return await self.collection.find_one({
            "refresh_token_hash": refresh_token_hash,
            "is_active": True
        })

    async def invalidate_session(self, session_id: str) -> None:
        """Deactivate a single session by its ObjectId string."""
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"is_active": False}}
        )

    async def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Deactivate all active sessions belonging to the specified user."""
        await self.collection.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"is_active": False}}
        )

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all currently active sessions for a user."""
        cursor = self.collection.find({"user_id": ObjectId(user_id), "is_active": True})
        return await cursor.to_list(length=100)

