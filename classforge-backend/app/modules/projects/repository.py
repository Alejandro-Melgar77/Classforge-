from bson import ObjectId
from datetime import datetime
import random
from typing import List, Optional, Tuple

class ProjectRepository:
    def __init__(self, db):
        self.collection = db["projects"]
        self.teams_collection = db["teams"]

    def _generate_color(self) -> str:
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    async def create(self, data: dict, owner_id: str) -> dict:
        doc = {
            "name": data["name"],
            "description": data["description"],
            "team_id": ObjectId(data["team_id"]) if data.get("team_id") else None,
            "owner_id": ObjectId(owner_id),
            "type": data["type"],
            "status": "in_progress",
            "color_tag": self._generate_color(),
            "tags": data.get("tags", []),
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, project_id: str) -> Optional[dict]:
        return await self.collection.find_one({"_id": ObjectId(project_id), "is_deleted": False})

    async def get_list(self, query: dict, page: int, limit: int, sort_by: str, order: int) -> Tuple[List[dict], int]:
        query["is_deleted"] = False
        cursor = self.collection.find(query).sort(sort_by, order).skip((page - 1) * limit).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.collection.count_documents(query)
        return items, total

    async def update(self, project_id: str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def soft_delete(self, project_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
