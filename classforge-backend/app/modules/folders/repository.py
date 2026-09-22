from bson import ObjectId
from datetime import datetime
from typing import List, Optional

class FolderRepository:
    def __init__(self, db):
        self.collection = db["folders"]

    async def create(self, data: dict, owner_id: str) -> dict:
        doc = {
            "name": data["name"],
            "owner_id": ObjectId(owner_id),
            "team_id": ObjectId(data["team_id"]) if data.get("team_id") else None,
            "project_id": ObjectId(data["project_id"]) if data.get("project_id") else None,
            "parent_folder_id": ObjectId(data["parent_folder_id"]) if data.get("parent_folder_id") else None,
            "type": data["type"],
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, folder_id: str) -> Optional[dict]:
        return await self.collection.find_one({"_id": ObjectId(folder_id), "is_deleted": False})

    async def get_by_owner_and_teams(self, owner_id: str, team_ids: List[str]) -> List[dict]:
        query = {
            "is_deleted": False,
            "$or": [
                {"owner_id": ObjectId(owner_id)},
                {"team_id": {"$in": [ObjectId(t) for t in team_ids]}}
            ]
        }
        cursor = self.collection.find(query)
        return await cursor.to_list(length=1000)

    async def get_children(self, folder_id: str) -> List[dict]:
        cursor = self.collection.find({"parent_folder_id": ObjectId(folder_id), "is_deleted": False})
        return await cursor.to_list(length=1000)

    async def update(self, folder_id: str, name: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": {"name": name, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def soft_delete(self, folder_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
