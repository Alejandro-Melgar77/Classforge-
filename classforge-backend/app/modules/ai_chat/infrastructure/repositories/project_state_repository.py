"""
Repository for the ai_project_state collection.
Manages shared, audited project AI state (participative mode, role autonomies, project digest).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId

from app.ai_team.domain.roles import ROLES_REGISTRY

logger = logging.getLogger(__name__)


def _doc_to_dict(doc: dict) -> dict:
    if not doc:
        return {}
    res = dict(doc)
    if "_id" in res:
        res["id"] = str(res.pop("_id"))
    if "project_id" in res:
        res["project_id"] = str(res["project_id"])
    return res


def _build_default_state(project_id: str) -> dict:
    now = datetime.now(timezone.utc)
    roles = [
        {
            "role_id": role_id,
            "enabled": True,
            "autonomy": "suggest",
        }
        for role_id in ROLES_REGISTRY.keys()
    ]
    return {
        "project_id": str(project_id),
        "participative": {
            "enabled": False,
            "updated_by": None,
            "updated_at": None,
        },
        "roles": roles,
        "digest": {
            "text": "",
            "tokens": 0,
            "covers_until": None,
            "updated_at": None,
        },
        "local_only": False,
        "updated_at": now,
    }


class AiProjectStateRepository:
    """Manages the ai_project_state collection."""

    def __init__(self, db):
        self.db = db
        self.col = db["ai_project_state"]

    async def get_or_create(self, project_id: str) -> dict:
        """Retrieves project state or initializes it with default values."""
        pid_str = str(project_id)
        doc = await self.col.find_one({"project_id": pid_str})
        if not doc and ObjectId.is_valid(pid_str):
            doc = await self.col.find_one({"project_id": ObjectId(pid_str)})

        if not doc:
            default_doc = _build_default_state(pid_str)
            try:
                await self.col.insert_one(default_doc)
                return _doc_to_dict(default_doc)
            except Exception as e:
                logger.warning(f"[AiProjectStateRepo] Race condition inserting default state: {e}")
                doc = await self.col.find_one({"project_id": pid_str})
                return _doc_to_dict(doc) if doc else default_doc

        return _doc_to_dict(doc)

    async def update_participative(self, project_id: str, enabled: bool, user_id: str) -> dict:
        """Updates the participative flag and records user audit info."""
        await self.get_or_create(project_id)
        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "participative.enabled": bool(enabled),
                "participative.updated_by": str(user_id),
                "participative.updated_at": now,
                "updated_at": now,
            }
        }
        await self.col.update_one({"project_id": str(project_id)}, update)
        return await self.get_or_create(project_id)

    async def update_local_only(self, project_id: str, local_only: bool, user_id: str) -> dict:
        """Updates the local_only privacy flag."""
        await self.get_or_create(project_id)
        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "local_only": bool(local_only),
                "updated_by": str(user_id),
                "updated_at": now,
            }
        }
        await self.col.update_one({"project_id": str(project_id)}, update)
        return await self.get_or_create(project_id)

    async def update_roles(self, project_id: str, roles: List[Dict[str, Any]], user_id: str) -> dict:
        """Updates the role configurations (enabled and autonomy) for the project."""
        current = await self.get_or_create(project_id)
        now = datetime.now(timezone.utc)

        current_roles_map = {r["role_id"]: r for r in current.get("roles", [])}
        for r in roles:
            r_id = r.get("role_id")
            if r_id in ROLES_REGISTRY:
                existing = current_roles_map.get(r_id, {"role_id": r_id, "enabled": True, "autonomy": "suggest"})
                if "enabled" in r:
                    existing["enabled"] = bool(r["enabled"])
                if "autonomy" in r and r["autonomy"] in ("off", "suggest", "apply"):
                    existing["autonomy"] = r["autonomy"]
                current_roles_map[r_id] = existing

        updated_roles_list = list(current_roles_map.values())
        update = {
            "$set": {
                "roles": updated_roles_list,
                "updated_at": now,
            }
        }
        await self.col.update_one({"project_id": str(project_id)}, update)
        return await self.get_or_create(project_id)

    async def update_digest(
        self,
        project_id: str,
        text: str,
        tokens: int,
        covers_until: Optional[datetime] = None,
    ) -> dict:
        """Updates the shared project memory digest."""
        await self.get_or_create(project_id)
        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "digest.text": text,
                "digest.tokens": int(tokens),
                "digest.covers_until": covers_until or now,
                "digest.updated_at": now,
                "updated_at": now,
            }
        }
        await self.col.update_one({"project_id": str(project_id)}, update)
        return await self.get_or_create(project_id)
