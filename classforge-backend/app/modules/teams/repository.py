from bson import ObjectId
from datetime import datetime
import random
from typing import List, Optional

class TeamRepository:
    def __init__(self, db):
        self.collection = db["teams"]

    def _generate_color(self) -> str:
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    async def create(self, team_data: dict, created_by: str) -> dict:
        raw_members = team_data.get("member_ids", []) or []
        member_oids = [ObjectId(m) for m in raw_members if ObjectId.is_valid(str(m))]
        sm_oid = ObjectId(team_data["scrum_master_id"])
        if sm_oid not in member_oids:
            member_oids.append(sm_oid)

        doc = {
            "name": team_data["name"],
            "description": team_data.get("description", ""),
            "scrum_master_id": sm_oid,
            "member_ids": member_oids,
            "avatar_color": self._generate_color(),
            "is_active": True,
            "is_deleted": False,
            "deleted_at": None,
            "created_by": ObjectId(created_by),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, team_id: str) -> Optional[dict]:
        return await self.collection.find_one({"_id": ObjectId(team_id), "is_deleted": False})

    async def get_all(self, role: str, user_id: str) -> List[dict]:
        query = {"is_deleted": False}
        if role == "scrum_master":
            query["scrum_master_id"] = ObjectId(user_id)
        elif role == "dev":
            query["member_ids"] = ObjectId(user_id)
        cursor = self.collection.find(query).sort("created_at", -1)
        return await cursor.to_list(length=1000)

    async def update(self, team_id: str, update_data: dict) -> bool:
        if "scrum_master_id" in update_data and update_data["scrum_master_id"]:
            update_data["scrum_master_id"] = ObjectId(update_data["scrum_master_id"])
            
        if "member_ids" in update_data and isinstance(update_data["member_ids"], list):
            update_data["member_ids"] = [ObjectId(m) for m in update_data["member_ids"] if ObjectId.is_valid(str(m))]
            
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def add_member(self, team_id: str, user_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(team_id)},
            {
                "$addToSet": {"member_ids": ObjectId(user_id)},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    async def remove_member(self, team_id: str, user_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(team_id)},
            {
                "$pull": {"member_ids": ObjectId(user_id)},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    async def soft_delete(self, team_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
