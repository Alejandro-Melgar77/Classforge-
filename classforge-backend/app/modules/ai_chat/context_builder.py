"""
ProjectContextBuilder: Assembles full project context for Gemini AI injection.
Queries MongoDB for project, team, members, diagram, and chat history.
"""
from __future__ import annotations
import logging
from typing import Any, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class ProjectContextBuilder:
    """Builds a formatted project context string for injecting into AI system prompts."""

    async def build(
        self,
        db,
        project_id: str,
        diagram_id: Optional[str] = None,
        history_limit: int = 15,
    ) -> str:
        """Assembles the full context of a ClassForge project.
        
        Args:
            db: AsyncIOMotorDatabase instance.
            project_id: The project's MongoDB ObjectId as string.
            diagram_id: Optional diagram ObjectId string to include in context.
            history_limit: How many recent AI conversation messages to include.
        
        Returns:
            A formatted multi-line string ready to be injected into a system prompt.
        """
        try:
            project = await self._get_project(db, project_id)
            team = await self._get_team(db, project)
            members = await self._get_members(db, team)
            diagram = await self._get_diagram(db, diagram_id)
            history = await self._get_recent_history(db, project_id, history_limit)
            tasks = await self._get_active_tasks(db, project_id)

            return f"""=== CONTEXTO COMPLETO DEL PROYECTO ClassForge ===

PROYECTO: {project.get('name', 'Sin nombre')}
DESCRIPCIÓN: {project.get('description', 'Sin descripción')}
ESTADO: {project.get('status', 'in_progress')}
EQUIPO: {team.get('name', 'Sin equipo asignado') if team else 'Sin equipo asignado'}

MIEMBROS DEL EQUIPO:
{self._format_members(members)}

DIAGRAMA ACTIVO: {diagram.get('name', 'Ninguno seleccionado') if diagram else 'Ninguno seleccionado'}
ESTRUCTURA ACTUAL DEL DIAGRAMA:
{self._summarize_diagram(diagram.get('graph_data', {})) if diagram else 'Sin datos de diagrama'}

HISTORIAL DE CONVERSACIONES RECIENTES CON LA IA (últimas {history_limit}):
{self._format_history(history)}

TAREAS ACTIVAS ASIGNADAS A LA IA:
{self._format_tasks(tasks)}
================================================="""
        except Exception as e:
            logger.error(f"[ContextBuilder] Error building context for project {project_id}: {e}")
            return f"=== CONTEXTO DEL PROYECTO ===\nError al cargar contexto: {e}\n==========================="

    async def _get_project(self, db, project_id: str) -> dict:
        try:
            doc = await db["projects"].find_one({"_id": ObjectId(project_id)})
            return doc or {}
        except Exception:
            return {}

    async def _get_team(self, db, project: dict) -> Optional[dict]:
        team_id = project.get("team_id")
        if not team_id:
            return None
        try:
            return await db["teams"].find_one({"_id": team_id if isinstance(team_id, ObjectId) else ObjectId(str(team_id))})
        except Exception:
            return None

    async def _get_members(self, db, team: Optional[dict]) -> list[dict]:
        if not team:
            return []
        member_ids = team.get("member_ids", [])
        if not member_ids:
            return []
        try:
            cursor = db["users"].find(
                {"_id": {"$in": [m if isinstance(m, ObjectId) else ObjectId(str(m)) for m in member_ids]}},
                {"username": 1, "email": 1, "role": 1}
            )
            return await cursor.to_list(length=50)
        except Exception:
            return []

    async def _get_diagram(self, db, diagram_id: Optional[str]) -> Optional[dict]:
        if not diagram_id:
            return None
        try:
            return await db["diagrams"].find_one({"_id": ObjectId(diagram_id)})
        except Exception:
            return None

    async def _get_recent_history(self, db, project_id: str, limit: int) -> list[dict]:
        try:
            conv = await db["ai_conversations"].find_one({"project_id": ObjectId(project_id)})
            if not conv:
                return []
            messages = conv.get("messages", [])
            return messages[-limit:] if len(messages) > limit else messages
        except Exception:
            return []

    async def _get_active_tasks(self, db, project_id: str) -> list[dict]:
        try:
            cursor = db["ai_tasks"].find(
                {"project_id": ObjectId(project_id), "status": {"$in": ["pending", "in_progress"]}},
                {"title": 1, "ai_role": 1, "status": 1, "description": 1}
            ).limit(10)
            return await cursor.to_list(length=10)
        except Exception:
            return []

    def _format_members(self, members: list[dict]) -> str:
        if not members:
            return "  (Sin miembros registrados)"
        lines = []
        for m in members:
            username = m.get("username", "Desconocido")
            role = m.get("role", "dev")
            lines.append(f"  - {username} ({role})")
        return "\n".join(lines)

    def _summarize_diagram(self, graph_data: Any) -> str:
        """Converts AntV X6 graph JSON to human-readable text for Gemini."""
        if not graph_data or not isinstance(graph_data, dict):
            return "  Diagrama vacío"
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        summary = []
        for node in nodes:
            data = node.get("data", {})
            name = data.get("name", "?")
            attrs = [
                f"{a.get('visibility', '+')} {a.get('name', '?')}: {a.get('type', '?')}"
                for a in data.get("attributes", [])
                if isinstance(a, dict)
            ]
            methods = [
                f"{m.get('visibility', '+')} {m.get('name', '?')}(): {m.get('return_type', 'void')}"
                for m in data.get("methods", [])
                if isinstance(m, dict)
            ]
            summary.append(
                f"  CLASE: {name}\n"
                f"    Atributos: {', '.join(attrs) or 'ninguno'}\n"
                f"    Métodos: {', '.join(methods) or 'ninguno'}"
            )
        for edge in edges:
            src = edge.get("source", "?")
            tgt = edge.get("target", "?")
            edge_data = edge.get("data", {})
            rel_type = edge_data.get("type", edge.get("type", "association"))
            src_mult = edge_data.get("sourceMultiplicity", "")
            tgt_mult = edge_data.get("targetMultiplicity", "")
            summary.append(
                f"  RELACIÓN: {src} --[{rel_type}]--> {tgt} "
                f"[{src_mult}:{tgt_mult}]"
            )
        return "\n".join(summary) if summary else "  Diagrama vacío"

    def _format_history(self, messages: list[dict]) -> str:
        if not messages:
            return "  (Sin historial de conversaciones)"
        lines = []
        for msg in messages:
            author = msg.get("author_name", "Desconocido")
            author_type = msg.get("author_type", "user")
            content = msg.get("content", "")
            role = msg.get("ai_role", "")
            if author_type == "ai" and role:
                lines.append(f"  [{role.upper()} IA]: {content[:200]}")
            else:
                lines.append(f"  [{author}]: {content[:200]}")
        return "\n".join(lines)

    def _format_tasks(self, tasks: list[dict]) -> str:
        if not tasks:
            return "  (Sin tareas activas)"
        lines = []
        for t in tasks:
            role = t.get("ai_role", "?")
            title = t.get("title", "Sin título")
            status = t.get("status", "?")
            lines.append(f"  [{role.upper()}] {title} — Estado: {status}")
        return "\n".join(lines)
