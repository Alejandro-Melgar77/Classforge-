from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

class DiagramRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["diagrams"]
        self.ws_tokens = db["ws_tokens"]
        self.versions_collection = db["diagram_versions"]

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
        
        result = await self.collection.insert_one(data)
        return await self.get_by_id(str(result.inserted_id))

    async def get_by_id(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        if not diagram_id or not ObjectId.is_valid(str(diagram_id)):
            return None
        return await self.collection.find_one({"_id": ObjectId(diagram_id), "is_deleted": False})

    async def list_diagrams(self, query: Dict[str, Any], skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        query["is_deleted"] = False
        projection = {
            "graph_data": 0,
            "history": 0,
            "xmi_data": 0
        }
        cursor = self.collection.find(query, projection).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    async def count_diagrams(self, query: Dict[str, Any]) -> int:
        q = dict(query)
        q["is_deleted"] = False
        return await self.collection.count_documents(q)

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

        now = datetime.now(timezone.utc)
        current_version = diagram.get("version", 1)
        new_version = current_version + 1

        # 1. Insert/upsert into diagram_versions collection
        saved_by_oid = ObjectId(saved_by) if ObjectId.is_valid(str(saved_by)) else str(saved_by)
        version_entry = {
            "diagram_id": ObjectId(diagram_id),
            "version": current_version,
            "graph_data": diagram.get("graph_data", {}),
            "saved_by": saved_by_oid,
            "saved_at": now,
            "created_at": now,
            "comment": comment
        }
        await self.versions_collection.update_one(
            {"diagram_id": ObjectId(diagram_id), "version": current_version},
            {"$set": version_entry},
            upsert=True
        )

        # 2. Configurable pruning / version limit (default 20 latest versions)
        old_versions = await self.versions_collection.find(
            {"diagram_id": ObjectId(diagram_id)},
            {"_id": 1}
        ).sort("version", -1).skip(20).to_list(length=100)
        if old_versions:
            old_ids = [v["_id"] for v in old_versions]
            await self.versions_collection.delete_many({"_id": {"$in": old_ids}})

        # 3. Update diagram, strip legacy embedded history array
        await self.collection.update_one(
            {"_id": ObjectId(diagram_id), "is_deleted": False},
            {
                "$set": {
                    "graph_data": graph_data,
                    "version": new_version,
                    "updated_at": now,
                    "xmi_data": None
                },
                "$unset": {
                    "history": ""
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

    async def list_history(self, diagram_id: str) -> List[Dict[str, Any]]:
        cursor = self.versions_collection.find(
            {"diagram_id": ObjectId(diagram_id)},
            {"graph_data": 0}
        ).sort("version", -1)
        versions = await cursor.to_list(length=100)
        if versions:
            for v in versions:
                if "saved_at" not in v and "created_at" in v:
                    v["saved_at"] = v["created_at"]
            return versions

        # Fallback to embedded history if not yet migrated
        diagram = await self.get_by_id(diagram_id)
        return diagram.get("history", []) if diagram else []

    async def get_history_entry(self, diagram_id: str, version: int) -> Optional[Dict[str, Any]]:
        entry = await self.versions_collection.find_one({
            "diagram_id": ObjectId(diagram_id),
            "version": version
        })
        if entry:
            if "saved_at" not in entry and "created_at" in entry:
                entry["saved_at"] = entry["created_at"]
            return entry

        # Fallback to embedded history if not yet migrated
        diagram = await self.get_by_id(diagram_id)
        if not diagram:
            return None
        for h in diagram.get("history", []):
            if h.get("version") == version:
                return h
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
