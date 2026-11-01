"""
Repository for the ai_tasks collection.
Extends existing task repository to support task update, cancellation, and deletion.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId

from app.modules.ai_chat.schemas import AiTaskCreate

logger = logging.getLogger(__name__)


class AiTaskRepository:
    """Manages the ai_tasks collection."""

    def __init__(self, db):
        self.db = db
        self.col = db["ai_tasks"]

    async def create(self, project_id: str, assigned_by: str, task_data: AiTaskCreate) -> Optional[str]:
        """Creates a new AI task and returns its inserted ID as string."""
        try:
            now = datetime.now(timezone.utc)
            created_by = task_data.created_by or assigned_by
            doc = {
                "project_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id,
                "diagram_id": ObjectId(task_data.diagram_id) if task_data.diagram_id and ObjectId.is_valid(task_data.diagram_id) else task_data.diagram_id,
                "assigned_by": ObjectId(assigned_by) if ObjectId.is_valid(assigned_by) else assigned_by,
                "created_by": created_by,
                "assignee_type": task_data.assignee_type or "ai_role",
                "assignee_id": task_data.assignee_id or task_data.ai_role,
                "ai_role": task_data.ai_role,
                "title": task_data.title,
                "description": task_data.description,
                "status": "pending",
                "attempts": 0,
                "result": None,
                "result_message_id": None,
                "created_at": now,
                "completed_at": None,
            }
            result = await self.col.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"[AiTaskRepo] create error: {e}")
            return None

    async def list_by_project(self, project_id: str, limit: int = 50) -> List[dict]:
        """Returns all tasks for a project ordered by creation date desc."""
        try:
            query = {"project_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id}
            cursor = self.col.find(query).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"[AiTaskRepo] list_by_project error: {e}")
            return []

    async def get_by_id(self, task_id: str) -> Optional[dict]:
        """Retrieves a single task by its ID."""
        try:
            query = {"_id": ObjectId(task_id) if ObjectId.is_valid(task_id) else task_id}
            return await self.col.find_one(query)
        except Exception:
            return None

    async def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        result_message_id: Optional[str] = None,
    ) -> bool:
        """Updates a task's status and optionally its result and linked message ID."""
        try:
            update: dict = {"$set": {"status": status}}
            if result is not None:
                update["$set"]["result"] = result
            if result_message_id is not None:
                update["$set"]["result_message_id"] = result_message_id
            if status in ("completed", "failed", "cancelled"):
                update["$set"]["completed_at"] = datetime.now(timezone.utc)
            query = {"_id": ObjectId(task_id) if ObjectId.is_valid(task_id) else task_id}
            res = await self.col.update_one(query, update)
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            logger.error(f"[AiTaskRepo] update_status error: {e}")
            return False

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Updates mutable fields of a task."""
        try:
            now = datetime.now(timezone.utc)
            allowed = {
                "title", "description", "ai_role", "status", "diagram_id",
                "assignee_type", "assignee_id", "created_by", "attempts", "result_message_id"
            }
            data = {k: v for k, v in updates.items() if k in allowed and v is not None}
            if not data:
                return True
            data["updated_at"] = now
            query = {"_id": ObjectId(task_id) if ObjectId.is_valid(task_id) else task_id}
            res = await self.col.update_one(query, {"$set": data})
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            logger.error(f"[AiTaskRepo] update_task error: {e}")
            return False

    async def delete_task(self, task_id: str) -> bool:
        """Deletes a task by ID."""
        try:
            query = {"_id": ObjectId(task_id) if ObjectId.is_valid(task_id) else task_id}
            res = await self.col.delete_one(query)
            return res.deleted_count > 0
        except Exception as e:
            logger.error(f"[AiTaskRepo] delete_task error: {e}")
            return False
