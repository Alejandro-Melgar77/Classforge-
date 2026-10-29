"""MongoDB CRUD operations for ai_conversations and ai_tasks collections."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from bson import ObjectId

from app.modules.ai_chat.schemas import AiMessage, AiTask, AiTaskCreate

logger = logging.getLogger(__name__)


class AiConversationRepository:
    """Manages the ai_conversations collection (one document per project)."""

    def __init__(self, db):
        self.col = db["ai_conversations"]

    async def get_by_project(self, project_id: str) -> Optional[dict]:
        """Retrieves the conversation document for a project."""
        try:
            return await self.col.find_one({"project_id": ObjectId(project_id)})
        except Exception as e:
            logger.error(f"[AiConvRepo] get_by_project error: {e}")
            return None

    async def append_message(self, project_id: str, message: AiMessage) -> bool:
        """Appends a message to the project's conversation document, creating it if needed."""
        try:
            msg_dict = message.model_dump()
            msg_dict["timestamp"] = message.timestamp
            now = datetime.utcnow()
            result = await self.col.update_one(
                {"project_id": ObjectId(project_id)},
                {
                    "$push": {"messages": msg_dict},
                    "$set": {"updated_at": now},
                    "$setOnInsert": {"created_at": now, "active_ai_roles": []},
                },
                upsert=True,
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"[AiConvRepo] append_message error: {e}")
            return False

    async def get_messages_for_user(
        self, project_id: str, user_id: str, limit: int = 100
    ) -> list[dict]:
        """Returns messages authored by a specific user plus all AI messages."""
        conv = await self.get_by_project(project_id)
        if not conv:
            return []
        all_msgs = conv.get("messages", [])
        filtered = [
            m for m in all_msgs
            if m.get("author_type") == "ai" or m.get("author_id") == user_id
        ]
        return filtered[-limit:]

    async def get_all_messages(self, project_id: str, limit: int = 200) -> list[dict]:
        """Returns all messages (group history) for a project."""
        conv = await self.get_by_project(project_id)
        if not conv:
            return []
        messages = conv.get("messages", [])
        return messages[-limit:]

    async def set_active_roles(self, project_id: str, roles: list[str]) -> bool:
        """Updates the list of active AI roles for a project."""
        try:
            result = await self.col.update_one(
                {"project_id": ObjectId(project_id)},
                {
                    "$set": {"active_ai_roles": roles, "updated_at": datetime.utcnow()},
                    "$setOnInsert": {"created_at": datetime.utcnow(), "messages": []},
                },
                upsert=True,
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"[AiConvRepo] set_active_roles error: {e}")
            return False

    async def get_active_roles(self, project_id: str) -> list[str]:
        """Returns the currently active AI role IDs for a project."""
        conv = await self.get_by_project(project_id)
        if not conv:
            return []
        return conv.get("active_ai_roles", [])


class AiTaskRepository:
    """Manages the ai_tasks collection."""

    def __init__(self, db):
        self.col = db["ai_tasks"]

    async def create(self, project_id: str, assigned_by: str, task_data: AiTaskCreate) -> Optional[str]:
        """Creates a new AI task and returns its inserted ID as string."""
        try:
            doc = {
                "project_id": ObjectId(project_id),
                "diagram_id": ObjectId(task_data.diagram_id) if task_data.diagram_id else None,
                "assigned_by": ObjectId(assigned_by),
                "ai_role": task_data.ai_role,
                "title": task_data.title,
                "description": task_data.description,
                "status": "pending",
                "result": None,
                "created_at": datetime.utcnow(),
                "completed_at": None,
            }
            result = await self.col.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"[AiTaskRepo] create error: {e}")
            return None

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[dict]:
        """Returns all tasks for a project ordered by creation date desc."""
        try:
            cursor = self.col.find(
                {"project_id": ObjectId(project_id)}
            ).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"[AiTaskRepo] list_by_project error: {e}")
            return []

    async def update_status(
        self, task_id: str, status: str, result: Optional[str] = None
    ) -> bool:
        """Updates a task's status and optionally its result."""
        try:
            update: dict = {"$set": {"status": status}}
            if result is not None:
                update["$set"]["result"] = result
            if status in ("completed", "failed"):
                update["$set"]["completed_at"] = datetime.utcnow()
            res = await self.col.update_one({"_id": ObjectId(task_id)}, update)
            return res.modified_count > 0
        except Exception as e:
            logger.error(f"[AiTaskRepo] update_status error: {e}")
            return False

    async def get_by_id(self, task_id: str) -> Optional[dict]:
        """Retrieves a single task by its ObjectId string."""
        try:
            return await self.col.find_one({"_id": ObjectId(task_id)})
        except Exception:
            return None
