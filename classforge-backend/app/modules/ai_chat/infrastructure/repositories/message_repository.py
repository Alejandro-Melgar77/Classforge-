"""
Repository for the ai_messages collection.
Scalable model with cursor-based pagination and personal/project thread semantics.
"""
from __future__ import annotations
import logging
import base64
import json
import binascii
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.modules.ai_chat.domain.models import AiMessage

logger = logging.getLogger(__name__)

def _encode_cursor(doc: dict) -> str:
    payload = [doc['created_at'].isoformat(), str(doc['_id']), isinstance(doc['_id'], ObjectId)]
    return 'v2:' + base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

def _apply_cursor(query: dict, value: str, operator: str) -> dict:
    try:
        if not value.startswith('v2:'):
            return {'$and': [query, {'created_at': {operator: datetime.fromisoformat(value)}}]}
        encoded = value[3:]
        dt, ident, is_object_id = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        if not isinstance(ident, str) or not isinstance(is_object_id, bool):
            raise ValueError('invalid cursor')
        dt = datetime.fromisoformat(dt)
        ident = ObjectId(ident) if is_object_id else ident
        return {'$and': [query, {'$or': [
            {'created_at': {operator: dt}}, {'created_at': dt, '_id': {operator: ident}}
        ]}]}
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise ValidationError('Cursor de historial inválido') from exc


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
        project_id: str,
    ) -> Optional[dict]:
        """Sets status ('applied' | 'dismissed') for a specific proposal inside a message."""
        try:
            message = await self.find_by_id(message_id)
            if not message or str(message.get("project_id")) != str(project_id):
                return None
            if message.get("thread") == "personal" and str(message.get("owner_id")) != str(user_id):
                return None

            # Writing proposal_state for an id that does not exist used to answer
            # 200 with a phantom audit entry.
            proposals = message.get("proposals") or []
            proposal_ids = {
                str(p.get("id"))
                for p in proposals
                if isinstance(p, dict) and p.get("id") is not None
            }
            if str(proposal_id) not in proposal_ids:
                raise NotFoundError(f"Propuesta {proposal_id} no encontrada en el mensaje")
            if status not in ("dismissed", "rejected", "approved"):
                raise ValidationError("La aplicación de propuestas requiere una modificación confirmada del diagrama mediante el endpoint /apply")

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
            query["project_id"] = str(project_id)
            query["$and"] = [
                {"$or": [{"thread": {"$ne": "personal"}}, {"owner_id": str(user_id)}]},
                {"proposals.id": proposal_id},
            ]

            msg_doc = await self.col.find_one(query)
            update_fields: Dict[str, Any] = {field_key: state_record, "updated_at": now}
            if msg_doc and "proposals" in msg_doc:
                updated_proposals = []
                for p in msg_doc.get("proposals", []):
                    if isinstance(p, dict) and str(p.get("id")) == str(proposal_id):
                        p_copy = dict(p)
                        p_copy["state"] = state_record
                        updated_proposals.append(p_copy)
                    else:
                        updated_proposals.append(p)
                update_fields["proposals"] = updated_proposals

            result = await self.col.update_one(
                query,
                {"$set": update_fields}
            )
            if not result.matched_count:
                return None
            return await self.find_by_id(message_id)
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"[AiMsgRepo] update_proposal_state error: {e}")
            return None

    async def publish_message(
        self,
        message_id: str,
        user_id: str,
        project_id: str,
    ) -> Optional[dict]:
        """Publishes a personal thread message to the project team/group (sets visibility='team')."""
        try:
            message = await self.find_by_id(message_id)
            if not message or str(message.get("project_id")) != str(project_id):
                return None
            if str(message.get("owner_id")) != str(user_id) and str(message.get("author_id")) != str(user_id):
                raise ForbiddenError("Solo el propietario del mensaje puede publicarlo al equipo")

            now = datetime.now(timezone.utc)
            query = {"_id": message_id}
            if ObjectId.is_valid(message_id):
                query = {"$or": [{"_id": message_id}, {"_id": ObjectId(message_id)}]}
            await self.col.update_one(
                query,
                {"$set": {"visibility": "team", "thread": "project", "updated_at": now}}
            )
            return await self.find_by_id(message_id)
        except (NotFoundError, ForbiddenError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"[AiMsgRepo] publish_message error: {e}")
            return None

    async def get_history(
        self,
        project_id: str,
        user_id: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 50,
        member: Optional[str] = None,
        role: Optional[str] = None,
        order: str = "asc",
    ) -> Tuple[List[dict], int, Optional[str]]:
        """Cursor-paginated query of project messages (group history).
        
        Enforces visibility rules: only messages directed to the project/team,
        explicitly published messages, or messages owned by the requesting user
        are returned. Private personal messages belonging to other users are excluded.
        
        Returns:
            (messages, total_matching, next_cursor)

        ``order="desc"`` returns the newest messages first; ``"asc"`` returns the
        oldest. Callers that need "the most recent window" (e.g. the digest) must
        use ``desc``.
        """
        limit = max(1, min(limit, 100))
        query: Dict[str, Any] = {"project_id": str(project_id)}

        # Visibility filter: team-level messages + current user's personal messages
        if user_id:
            query["$or"] = [
                {"visibility": {"$ne": "private"}},
                {"owner_id": str(user_id)},
            ]

        if member:
            member_filter = [
                {"owner_id": str(member)},
                {"author_id": str(member)},
            ]
            if "$or" in query:
                query = {"$and": [query, {"$or": member_filter}]}
            else:
                query["$or"] = member_filter

        if role:
            query["ai_role"] = role

        if before and after:
            raise ValidationError('No se pueden combinar before y after')
        total = await self.col.count_documents(query)
        if before or after:
            query = _apply_cursor(query, before or after, '$lt' if before else '$gt')
        sort_dir = -1 if before else (1 if after else (-1 if order == 'desc' else 1))
        cursor = self.col.find(query).sort([('created_at', sort_dir), ('_id', sort_dir)]).limit(limit)
        docs = await cursor.to_list(length=limit)

        if before:
            docs.reverse()

        next_cursor = _encode_cursor(docs[0] if before else docs[-1]) if docs else None
        return [_doc_to_dict(d) for d in docs], total, next_cursor

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

        if before and after:
            raise ValidationError('No se pueden combinar before y after')
        sort_dir = -1 if before else 1

        total = await self.col.count_documents(query)

        if before or after:
            query = _apply_cursor(query, before or after, '$lt' if before else '$gt')
        cursor = self.col.find(query).sort([('created_at', sort_dir), ('_id', sort_dir)]).limit(limit)
        docs = await cursor.to_list(length=limit)

        if before:
            docs.reverse()

        next_cursor = _encode_cursor(docs[0] if before else docs[-1]) if docs else None
        return [_doc_to_dict(d) for d in docs], total, next_cursor

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
