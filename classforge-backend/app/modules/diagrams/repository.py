from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

class DiagramRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["diagrams"]
        self.ws_tokens = db["ws_tokens"]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = data["created_at"]
        data["is_deleted"] = False
        data["deleted_at"] = None
        data["status"] = data.get("status", "draft")
        data["is_public"] = data.get("is_public", False)
        data["version"] = 1
        data["graph_data"] = data.get("graph_data", {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1.0}})
        data["xmi_data"] = None
        data["thumbnail_url"] = None
        data["history"] = []
        
        result = await self.collection.insert_one(data)
        return await self.get_by_id(str(result.inserted_id))

    async def get_by_id(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": ObjectId(diagram_id), "is_deleted": False})

    async def list_diagrams(self, query: Dict[str, Any], skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        query["is_deleted"] = False
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def update(self, diagram_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(diagram_id), "is_deleted": False},
            {"$set": update_data}
        )
        return await self.get_by_id(diagram_id)

    async def save_graph(self, diagram_id: str, graph_data: Dict[str, Any], saved_by: str, comment: Optional[str]) -> Optional[Dict[str, Any]]:
        diagram = await self.get_by_id(diagram_id)
        if not diagram:
            return None

        history_entry = {
            "version": diagram.get("version", 1),
            "graph_data": diagram.get("graph_data", {}),
            "saved_by": ObjectId(saved_by),
            "saved_at": datetime.now(timezone.utc),
            "comment": comment
        }
        
        # We need to maintain history limited to 20
        # Wait, if we just push and then slice, we can do it in an update pipeline or multiple updates.
        # Motor allows $push with $slice.
        
        new_version = diagram.get("version", 1) + 1
        
        await self.collection.update_one(
            {"_id": ObjectId(diagram_id), "is_deleted": False},
            {
                "$set": {
                    "graph_data": graph_data,
                    "version": new_version,
                    "updated_at": datetime.now(timezone.utc),
                    "xmi_data": None
                },
                "$push": {
                    "history": {
                        "$each": [history_entry],
                        "$slice": -20
                    }
                }
            }
        )
        return await self.get_by_id(diagram_id)

    async def soft_delete(self, diagram_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def save_xmi(self, diagram_id: str, xmi_content: str):
        await self.collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": {"xmi_data": xmi_content}}
        )

    async def get_history_entry(self, diagram_id: str, version: int) -> Optional[Dict[str, Any]]:
        diagram = await self.get_by_id(diagram_id)
        if not diagram:
            return None
        for entry in diagram.get("history", []):
            if entry["version"] == version:
                return entry
        return None

    async def create_ws_token(self, diagram_id: str, user_id: str, expires_at: datetime) -> str:
        token = str(uuid.uuid4())
        await self.ws_tokens.insert_one({
            "token": token,
            "diagram_id": ObjectId(diagram_id),
            "user_id": ObjectId(user_id),
            "expires_at": expires_at
        })
        return token
