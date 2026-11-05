from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
import logging
from app.core.errors import ConflictError
from app.modules.diagrams.validation import validate_graph

logger = logging.getLogger(__name__)

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
        data["thumbnail_url"] = None
        validate_graph(data["graph_data"])
        data.setdefault('_id', ObjectId())
        now = data["created_at"]
        data['_pending_snapshot'] = {
                "diagram_id": data['_id'],
                "version": 1,
                "graph_data": data["graph_data"],
                "saved_by": data.get("created_by"),
                "saved_at": now,
                "created_at": now,
                "comment": "Creación inicial",
        }
        result = await self.collection.insert_one(data)
        try:
            await self._flush_snapshot(str(result.inserted_id), data)
        except Exception:
            logger.exception("Snapshot inicial pendiente de materializar para %s", result.inserted_id)
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
            "xmi_data": 0,
            "_pending_snapshot": 0
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

    async def save_graph(self, diagram_id: str, graph_data: Dict[str, Any], saved_by: str, comment: Optional[str], base_version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Persist a new graph state and snapshot it as the next version.

        Invariant: ``diagram.version`` equals the highest snapshot version and
        both hold the same ``graph_data``. Previously the snapshot stored the
        *previous* state and the diagram was bumped to ``N+1``, so the current
        state was never reachable from the history.
        """
        validate_graph(graph_data)
        diagram = await self.get_by_id(diagram_id)
        if not diagram:
            return None
        await self._flush_snapshot(diagram_id, diagram)

        now = datetime.now(timezone.utc)
        current_version = int(diagram.get("version", 1) or 1)
        if base_version is not None and base_version != current_version:
            raise ConflictError("El diagrama cambió. Recarga la versión actual antes de guardar.")
        new_version = max(current_version + 1, 1)

        saved_by_oid = ObjectId(saved_by) if ObjectId.is_valid(str(saved_by)) else str(saved_by)
        version_entry = {
            "diagram_id": ObjectId(diagram_id),
            "version": new_version,
            "graph_data": graph_data,
            "saved_by": saved_by_oid,
            "saved_at": now,
            "created_at": now,
            "comment": comment
        }
        # Commit graph + recovery record in ONE atomic document update. Compare
        # the graph too: legacy WS operations do not yet advance the version.
        result = await self.collection.update_one(
            {"_id": ObjectId(diagram_id), "is_deleted": False,
             "version": diagram.get("version", {"$exists": False}),
             "graph_data": diagram.get("graph_data", {"$exists": False})},
            {"$set": {"graph_data": graph_data, "version": new_version,
                      "updated_at": now, "_pending_snapshot": version_entry}}
        )
        if not result.matched_count:
            raise ConflictError("Otro participante modificó el diagrama durante el guardado.")
        committed = {**diagram, "graph_data": graph_data, "version": new_version, "updated_at": now}
        committed.pop('_pending_snapshot', None)
        try:
            await self._flush_snapshot(diagram_id, {"_pending_snapshot": version_entry})
        except Exception:
            # The committed snapshot remains recoverable in the diagram.
            logger.exception("Snapshot pendiente de materializar para %s", diagram_id)
            return committed

        return committed

    async def _flush_snapshot(self, diagram_id: str, diagram: dict) -> None:
        snapshot = diagram.get('_pending_snapshot')
        if not snapshot:
            return
        await self.versions_collection.update_one(
            {'diagram_id': ObjectId(diagram_id), 'version': snapshot['version']},
            {'$setOnInsert': snapshot}, upsert=True,
        )
        stored = await self.versions_collection.find_one(
            {'diagram_id': ObjectId(diagram_id), 'version': snapshot['version']})
        if not stored or stored.get('graph_data') != snapshot.get('graph_data'):
            raise ConflictError('El historial existente no coincide con la revisión confirmada')
        await self.collection.update_one(
            {'_id': ObjectId(diagram_id), '_pending_snapshot.version': snapshot['version']},
            {'$unset': {'_pending_snapshot': ''}},
        )

    async def soft_delete(self, diagram_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(diagram_id)},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def list_history(self, diagram_id: str) -> List[Dict[str, Any]]:
        diagram = await self.get_by_id(diagram_id)
        if diagram:
            await self._flush_snapshot(diagram_id, diagram)
        cursor = self.versions_collection.find(
            {"diagram_id": ObjectId(diagram_id)},
            {"graph_data": 0}
        ).sort("version", -1)
        versions = await cursor.to_list(length=100)
        # Preserve legacy embedded history until an explicitly verified migration.
        seen = {v.get('version') for v in versions}
        for entry in (diagram or {}).get('history', []):
            if entry.get('version') not in seen:
                versions.append({k: v for k, v in entry.items() if k != 'graph_data'})
        for v in versions:
            if "saved_at" not in v and "created_at" in v:
                v["saved_at"] = v["created_at"]
        return sorted(versions, key=lambda v: v.get('version', 0), reverse=True)

    async def get_history_entry(self, diagram_id: str, version: int) -> Optional[Dict[str, Any]]:
        diagram = await self.get_by_id(diagram_id)
        if diagram and diagram.get('_pending_snapshot', {}).get('version') == version:
            return diagram['_pending_snapshot']
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
