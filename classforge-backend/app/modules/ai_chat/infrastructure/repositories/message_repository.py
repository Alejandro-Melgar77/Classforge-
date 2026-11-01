"""
Repository for the ai_messages collection.
Scalable model with cursor-based pagination and personal/project thread semantics.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from app.modules.ai_chat.domain.models import AiMessage

logger = logging.getLogger(__name__)


def _serialize_id(val: Any) -> str:
    return str(val) if val is not None else ""


def _doc_to_dict(doc: dict) -> dict:
    """Normalizes MongoDB document representation for client consumption."""
    if not doc:
        return {}
    res = dict(doc)
    if "_id" in res:
        res["id"] = str(res.pop("_id"))
    elif "id" in res:
        res["id"] = str(res["id"])
    if "project_id" in res:
        res["project_id"] = str(res["project_id"])
    if "author_id" in res and res["author_id"]:
        res["author_id"] = str(res["author_id"])
    if "owner_id" in res and res["owner_id"]:
        res["owner_id"] = str(res["owner_id"])
    return res


class AiMessageRepository:
    """Manages the scalable ai_messages collection."""

    def __init__(self, db):
        self.db = db
        self.col = db["ai_messages"]

    async def create_message(self, message: AiMessage) -> dict:
        """Inserts a new message document into ai_messages."""
        doc = message.model_dump()
        # Ensure project_id is stored consistently
        doc["project_id"] = str(message.project_id)
        if message.owner_id:
            doc["owner_id"] = str(message.owner_id)
        if message.author_id:
            doc["author_id"] = str(message.author_id)
        if not doc.get("created_at"):
            doc["created_at"] = datetime.now(timezone.utc)

        # Store using custom uuid id as _id or keep uuid in id and auto ObjectId in _id
        # Having _id as a string or ObjectId: Let's store doc with _id = message.id (uuid)
        # or use message.id as id and let Mongo have _id.
        # To be clean and compatible with ObjectId & string queries:
        if "id" in doc and doc["id"]:
            doc["_id"] = doc["id"]

        await self.col.insert_one(doc)
        return _doc_to_dict(doc)

    async def find_by_client_id(self, project_id: str, client_id: str) -> Optional[dict]:
        """Finds an existing message by project_id and client_id (idempotency)."""
        if not client_id:
            return None
        doc = await self.col.find_one({
            "project_id": str(project_id),
            "client_id": client_id,
        })
        return _doc_to_dict(doc) if doc else None

    async def find_by_id(self, message_id: str) -> Optional[dict]:
        """Finds a single message by string ID or ObjectId."""
        try:
            doc = await self.col.find_one({"_id": message_id})
            if not doc and ObjectId.is_valid(message_id):
                doc = await self.col.find_one({"_id": ObjectId(message_id)})
            return _doc_to_dict(doc) if doc else None
        except Exception as e:
            logger.error(f"[AiMsgRepo] find_by_id error: {e}")
            return None

    async def find_pending_ai_for_user_message(self, reply_to_id: str) -> List[dict]:
        """Finds AI responses generated for a given user message."""
        cursor = self.col.find({"reply_to": str(reply_to_id)})
        docs = await cursor.to_list(length=10)
        return [_doc_to_dict(d) for d in docs]

    async def update_ai_response(
        self,
        message_id: str,
        content: str,
        proposals: Optional[List[Any]] = None,
        status: str = "ok",
        model: Optional[str] = None,
        error_code: Optional[str] = None,
        questions: Optional[List[str]] = None,
        needs_context: bool = False,
        diagram_snapshot: Optional[dict] = None,
    ) -> bool:
        """Updates a pending AI message with generated content, structured proposals, and status."""
        try:
            now = datetime.now(timezone.utc)
            update_data: Dict[str, Any] = {
                "content": content,
                "status": status,
                "updated_at": now,
            }
            if proposals is not None:
                # Store proposals serialized cleanly
                serialized_props = []
                for p in proposals:
                    if hasattr(p, "model_dump"):
                        serialized_props.append(p.model_dump())
                    elif isinstance(p, dict):
                        serialized_props.append(p)
                update_data["proposals"] = serialized_props
                update_data["has_diagram_changes"] = any(
                    p.get("kind") == "uml_command" for p in serialized_props
                )
            if model:
                update_data["model"] = model
            if error_code is not None:
                update_data["error_code"] = error_code
            if questions is not None:
                update_data["questions"] = questions
            update_data["needs_context"] = needs_context
            if diagram_snapshot is not None:
                update_data["diagram_snapshot"] = diagram_snapshot

            query = {"_id": message_id}
            if ObjectId.is_valid(message_id):
                query = {"$or": [{"_id": message_id}, {"_id": ObjectId(message_id)}]}

            res = await self.col.update_one(query, {"$set": update_data})
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            logger.error(f"[AiMsgRepo] update_ai_response error: {e}")
            return False

    async def update_proposal_state(
        self,
        message_id: str,
        proposal_id: str,
        status: str,
        user_id: str,
    ) -> Optional[dict]:
        """Sets status ('applied' | 'dismissed') for a specific proposal inside a message."""
        try:
            now = datetime.now(timezone.utc)
            state_record = {
                "status": status,
                "by": str(user_id),
                "at": now,
            }
            field_key = f"proposal_state.{proposal_id}"
            query = {"_id": message_id}
            if ObjectId.is_valid(message_id):
                query = {"$or": [{"_id": message_id}, {"_id": ObjectId(message_id)}]}

            await self.col.update_one(
                query,
                {"$set": {field_key: state_record, "updated_at": now}}
            )
            return await self.find_by_id(message_id)
        except Exception as e:
            logger.error(f"[AiMsgRepo] update_proposal_state error: {e}")
            return None

    async def get_history(
        self,
        project_id: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 50,
        member: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Tuple[List[dict], int, Optional[str]]:
        """Cursor-paginated query of all project messages (group history).
        
        Returns:
            (messages, total_matching, next_cursor)
        """
        limit = max(1, min(limit, 100))
        query: Dict[str, Any] = {"project_id": str(project_id)}

        if member:
            query["$or"] = [
                {"owner_id": str(member)},
                {"author_id": str(member)},
            ]

        if role:
            query["ai_role"] = role

        sort_dir = 1
        if before:
            try:
                dt_before = datetime.fromisoformat(before) if isinstance(before, str) else before
                query["created_at"] = {"$lt": dt_before}
            except Exception:
                pass
            sort_dir = -1
        elif after:
            try:
                dt_after = datetime.fromisoformat(after) if isinstance(after, str) else after
                query["created_at"] = {"$gt": dt_after}
            except Exception:
                pass
            sort_dir = 1

        total = await self.col.count_documents({"project_id": str(project_id)})

        cursor = self.col.find(query).sort("created_at", sort_dir).limit(limit)
        docs = await cursor.to_list(length=limit)

        if before:
            docs.reverse()

        serialized = [_doc_to_dict(d) for d in docs]
        next_cursor = None
        if serialized:
            last_dt = serialized[-1].get("created_at")
            if isinstance(last_dt, datetime):
                next_cursor = last_dt.isoformat()
            elif isinstance(last_dt, str):
                next_cursor = last_dt

        return serialized, total, next_cursor

    async def get_mine_history(
        self,
        project_id: str,
        user_id: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[dict], int, Optional[str]]:
        """Cursor-paginated query of user's personal thread + project-level AI announcements."""
        limit = max(1, min(limit, 100))
        query: Dict[str, Any] = {
            "project_id": str(project_id),
            "$or": [
                {"thread": "personal", "owner_id": str(user_id)},
                {"thread": "project"},
            ],
        }

        sort_dir = 1
        if before:
            try:
                dt_before = datetime.fromisoformat(before) if isinstance(before, str) else before
                query["created_at"] = {"$lt": dt_before}
            except Exception:
                pass
            sort_dir = -1
        elif after:
            try:
                dt_after = datetime.fromisoformat(after) if isinstance(after, str) else after
                query["created_at"] = {"$gt": dt_after}
            except Exception:
                pass
            sort_dir = 1

        total = await self.col.count_documents({
            "project_id": str(project_id),
            "$or": [
                {"thread": "personal", "owner_id": str(user_id)},
                {"thread": "project"},
            ],
        })

        cursor = self.col.find(query).sort("created_at", sort_dir).limit(limit)
        docs = await cursor.to_list(length=limit)

        if before:
            docs.reverse()

        serialized = [_doc_to_dict(d) for d in docs]
        next_cursor = None
        if serialized:
            last_dt = serialized[-1].get("created_at")
            if isinstance(last_dt, datetime):
                next_cursor = last_dt.isoformat()
            elif isinstance(last_dt, str):
                next_cursor = last_dt

        return serialized, total, next_cursor

    async def get_recent_user_turns(
        self,
        project_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Retrieves the recent alternating messages in a user's personal thread for prompt assembly."""
        query = {
            "project_id": str(project_id),
            "thread": "personal",
            "owner_id": str(user_id),
            "status": "ok",
        }
        cursor = self.col.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        docs.reverse()
        return [_doc_to_dict(d) for d in docs]

    async def get_recent_team_activity(
        self,
        project_id: str,
        exclude_user_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Retrieves recent user messages from other team members for 'Novedades de otros'."""
        query = {
            "project_id": str(project_id),
            "author_type": "user",
            "owner_id": {"$ne": str(exclude_user_id)},
        }
        cursor = self.col.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        docs.reverse()
        return [_doc_to_dict(d) for d in docs]

    async def count_since(self, project_id: str, since: Optional[datetime] = None) -> int:
        """Counts how many messages have been created in a project since a specific timestamp."""
        query: Dict[str, Any] = {"project_id": str(project_id)}
        if since:
            query["created_at"] = {"$gt": since}
        return await self.col.count_documents(query)
