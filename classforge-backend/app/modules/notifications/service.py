from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db):
        self.db = db
        self.collection = db["notifications"]

    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        type: str = "info",
        project_id: Optional[str] = None,
        diagram_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """Crea una notificación individual para un usuario."""
        doc = {
            "user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
            "title": title,
            "message": message,
            "type": type,
            "project_id": ObjectId(project_id) if project_id and ObjectId.is_valid(project_id) else project_id,
            "diagram_id": ObjectId(diagram_id) if diagram_id and ObjectId.is_valid(diagram_id) else diagram_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
            "meta": meta or {}
        }
        res = await self.collection.insert_one(doc)
        return str(res.inserted_id)

    async def notify_project_members(
        self,
        project_id: str,
        title: str,
        message: str,
        type: str = "project_update",
        diagram_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notifica a todos los miembros del equipo y colaboradores vinculados al proyecto."""
        try:
            p_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            project = await self.db["projects"].find_one({"_id": p_oid})
            if not project:
                return 0

            recipient_ids = set()
            
            # 1. Creador del proyecto
            if "created_by" in project and project["created_by"]:
                recipient_ids.add(str(project["created_by"]))
            
            # 2. Miembros del equipo asignado
            team_id = project.get("team_id")
            if team_id:
                t_oid = ObjectId(team_id) if ObjectId.is_valid(team_id) else team_id
                team = await self.db["teams"].find_one({"_id": t_oid})
                if team and "member_ids" in team:
                    for mid in team["member_ids"]:
                        recipient_ids.add(str(mid))
                # También el Scrum Master / Lead del equipo
                if team and "lead_id" in team and team["lead_id"]:
                    recipient_ids.add(str(team["lead_id"]))

            # 3. Colaboradores de los diagramas del proyecto
            if diagram_id:
                d_oid = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
                diagram = await self.db["diagrams"].find_one({"_id": d_oid})
                if diagram and "member_ids" in diagram:
                    for mid in diagram["member_ids"]:
                        recipient_ids.add(str(mid))

            # 4. Todos los administradores del sistema
            admins = await self.db["users"].find({"role": "admin", "is_active": True}).to_list(length=100)
            for adm in admins:
                recipient_ids.add(str(adm["_id"]))

            created_count = 0
            for uid in recipient_ids:
                await self.create_notification(
                    user_id=uid,
                    title=title,
                    message=message,
                    type=type,
                    project_id=str(project_id),
                    diagram_id=str(diagram_id) if diagram_id else None,
                    meta=meta
                )
                created_count += 1

            return created_count
        except Exception as e:
            logger.error(f"Error notifying project members: {e}")
            return 0

    async def list_notifications(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 30,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """Obtiene las notificaciones del usuario con paginación y conteo de no leídas."""
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        filter_q = {"$or": [{"user_id": u_oid}, {"user_id": str(user_id)}]}
        
        unread_count = await self.collection.count_documents({
            **filter_q,
            "is_read": False
        })

        if unread_only:
            filter_q["is_read"] = False

        total = await self.collection.count_documents(filter_q)
        skip = (page - 1) * limit
        cursor = self.collection.find(filter_q).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)

        return {
            "items": items,
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "limit": limit
        }

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Marca una notificación como leída."""
        n_oid = ObjectId(notification_id) if ObjectId.is_valid(notification_id) else notification_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        res = await self.collection.update_one(
            {"_id": n_oid, "$or": [{"user_id": u_oid}, {"user_id": str(user_id)}]},
            {"$set": {"is_read": True}}
        )
        return res.modified_count > 0

    async def mark_all_as_read(self, user_id: str) -> int:
        """Marca todas las notificaciones del usuario como leídas."""
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        res = await self.collection.update_many(
            {"$or": [{"user_id": u_oid}, {"user_id": str(user_id)}], "is_read": False},
            {"$set": {"is_read": True}}
        )
        return res.modified_count

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Elimina una notificación."""
        n_oid = ObjectId(notification_id) if ObjectId.is_valid(notification_id) else notification_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        res = await self.collection.delete_one(
            {"_id": n_oid, "$or": [{"user_id": u_oid}, {"user_id": str(user_id)}]}
        )
        return res.deleted_count > 0
