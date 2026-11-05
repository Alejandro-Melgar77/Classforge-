"""
Transactional Outbox and Durable Events System for ClassForge Real-Time Collaboration (SYNC-01).
Ensures committed UML diagram operations are durably recorded and resiliently delivered.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class DiagramOutboxRepository:
    """Manages persistence, retrieval, and delivery tracking of diagram outbox events."""

    def __init__(self, db):
        self.db = db
        self.col = db["diagram_events"]

    async def record_event(
        self,
        diagram_id: str,
        project_id: Optional[str],
        revision: int,
        previous_revision: int,
        actor_id: str,
        operations: List[Dict[str, Any]],
        operation_id: Optional[str] = None,
        origin_connection_id: Optional[str] = None,
        graph_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Durably records a committed diagram operation event."""
        now = datetime.now(timezone.utc)
        event_id = uuid.uuid4().hex

        event_doc = {
            "_id": event_id,
            "event_id": event_id,
            "event_type": "diagram.operation.committed",
            "schema_version": 1,
            "project_id": str(project_id) if project_id else None,
            "diagram_id": str(diagram_id),
            "operation_id": operation_id or f"op_{uuid.uuid4().hex[:12]}",
            "actor_id": str(actor_id),
            "origin_connection_id": origin_connection_id,
            "previous_revision": previous_revision,
            "revision": revision,
            "operations": operations or [],
            "graph_data": graph_data,
            "status": "pending",
            "retry_count": 0,
            "created_at": now,
            "dispatched_at": None,
        }

        # Idempotency check: if operation_id is provided and already committed, return existing
        if operation_id:
            existing = await self.col.find_one({
                "diagram_id": str(diagram_id),
                "operation_id": operation_id,
            })
            if existing:
                logger.info(f"[Outbox] Duplicate operation {operation_id} detected for diagram {diagram_id}.")
                return existing

        await self.col.insert_one(event_doc)
        return event_doc

    async def get_events_since(
        self,
        diagram_id: str,
        known_revision: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves contiguous committed events since known_revision for client resynchronization."""
        cursor = self.col.find({
            "diagram_id": str(diagram_id),
            "revision": {"$gt": known_revision},
        }).sort("revision", 1).limit(limit)

        events = await cursor.to_list(length=limit)
        return events

    async def get_pending_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves undispatched events for delivery."""
        cursor = self.col.find({"status": "pending"}).sort("created_at", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def mark_dispatched(self, event_id: str) -> bool:
        """Marks an event as successfully dispatched."""
        now = datetime.now(timezone.utc)
        res = await self.col.update_one(
            {"_id": event_id},
            {"$set": {"status": "dispatched", "dispatched_at": now}}
        )
        return res.modified_count > 0

    async def mark_failed(self, event_id: str, error: str) -> bool:
        """Increments retry count on delivery failure."""
        res = await self.col.update_one(
            {"_id": event_id},
            {"$inc": {"retry_count": 1}, "$set": {"last_error": str(error)}}
        )
        return res.modified_count > 0


async def dispatch_outbox_events(db, limit: int = 50) -> int:
    """Processes pending outbox events and broadcasts them via ConnectionManager."""
    from app.modules.collaboration.connection_manager import manager

    repo = DiagramOutboxRepository(db)
    pending = await repo.get_pending_events(limit=limit)
    dispatched_count = 0

    for event in pending:
        diagram_id = event["diagram_id"]
        broadcast_msg = {
            "type": "DIAGRAM_COMMITTED",
            "event_id": event["event_id"],
            "diagram_id": diagram_id,
            "revision": event["revision"],
            "previous_revision": event.get("previous_revision", event["revision"] - 1),
            "operations": event.get("operations", []),
            "actor_id": event.get("actor_id"),
            "graph_data": event.get("graph_data"),
            "created_at": event["created_at"].isoformat() if hasattr(event["created_at"], "isoformat") else str(event["created_at"]),
        }

        try:
            await manager.broadcast(diagram_id, broadcast_msg)
            await repo.mark_dispatched(event["event_id"])
            dispatched_count += 1
        except Exception as exc:
            logger.warning(f"[OutboxDispatcher] Error broadcasting event {event['event_id']}: {exc}")
            await repo.mark_failed(event["event_id"], str(exc))

    return dispatched_count
