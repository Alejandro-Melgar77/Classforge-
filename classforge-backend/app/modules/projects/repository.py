from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId


class ProjectRepository:
    """Repository handling persistence operations for project documents in MongoDB."""

    def __init__(self, db: Any) -> None:
        self.collection = db["projects"]
        self.teams_collection = db["teams"]

    def _generate_color(self) -> str:
        """Generate a random hex color string for visual tagging."""
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    async def create(self, data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """Create a new project document with default values and timestamps."""
        now = datetime.now(timezone.utc)
        doc: Dict[str, Any] = {
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
            "created_at": now,
            "updated_at": now,
            "completed_at": None
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an active project by its ObjectId string."""
        return await self.collection.find_one({"_id": ObjectId(project_id), "is_deleted": False})

    async def get_list(
        self, query: Dict[str, Any], page: int, limit: int, sort_by: str, order: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieve a paginated list of non-deleted projects matching the query."""
        query["is_deleted"] = False
        cursor = self.collection.find(query).sort(sort_by, order).skip((page - 1) * limit).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.collection.count_documents(query)
        return items, total

    async def update(self, project_id: str, update_data: Dict[str, Any]) -> bool:
        """Update fields on an existing project document."""
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def soft_delete(self, project_id: str) -> bool:
        """Mark a project as soft-deleted with timestamps."""
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0
