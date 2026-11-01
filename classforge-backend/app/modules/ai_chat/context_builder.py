"""
ProjectContextBuilder: Thin adapter preserving legacy signature while fixing reported issues:
- Resolves 'username' -> 'name'.
- Resolves edge node IDs into readable class names.
- Never injects raw exception tracebacks or str(e) into the AI prompt.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class ProjectContextBuilder:
    """Thin adapter for assembling project context strings safely."""

    async def build(
        self,
        db,
        project_id: str,
        diagram_id: Optional[str] = None,
        history_limit: int = 15,
    ) -> str:
        """Assembles project context without leaking internal exceptions."""
        try:
            project = await self._get_project(db, project_id)
            team = await self._get_team(db, project)
            members = await self._get_members(db, team)
            diagram = await self._get_diagram(db, diagram_id)
            history = await self._get_recent_history(db, project_id, history_limit)
            tasks = await self._get_active_tasks(db, project_id)

            return f"""=== CONTEXTO DEL PROYECTO ClassForge ===

PROYECTO: {project.get('name', 'Sin nombre')}
DESCRIPCIÓN: {project.get('description', 'Sin descripción')}
ESTADO: {project.get('status', 'in_progress')}
EQUIPO: {team.get('name', 'Sin equipo asignado') if team else 'Sin equipo asignado'}

MIEMBROS DEL EQUIPO:
{self._format_members(members)}

DIAGRAMA ACTIVO: {diagram.get('name', 'Ninguno seleccionado') if diagram else 'Ninguno seleccionado'}
ESTRUCTURA ACTUAL DEL DIAGRAMA:
{self._summarize_diagram(diagram.get('graph_data', {})) if diagram else 'Sin datos de diagrama'}

HISTORIAL RECIENTE:
{self._format_history(history)}

TAREAS ACTIVAS:
{self._format_tasks(tasks)}
================================================="""
        except Exception as e:
            logger.warning(f"[ProjectContextBuilder] Error assembling context: {e}")
            return "=== CONTEXTO DEL PROYECTO ===\nInformación del proyecto temporalmente no disponible.\n==========================="

    async def _get_project(self, db, project_id: str) -> dict:
        try:
            pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            doc = await db["projects"].find_one({"_id": pid})
            return doc or {}
        except Exception:
            return {}

    async def _get_team(self, db, project: dict) -> Optional[dict]:
        team_id = project.get("team_id")
        if not team_id:
            return None
        try:
            tid = ObjectId(team_id) if ObjectId.is_valid(team_id) else team_id
            return await db["teams"].find_one({"_id": tid})
        except Exception:
            return None

    async def _get_members(self, db, team: Optional[dict]) -> list[dict]:
        if not team:
            return []
        member_ids = team.get("member_ids", [])
        if not member_ids:
            return []
        try:
            oids = [ObjectId(m) if ObjectId.is_valid(m) else m for m in member_ids]
            cursor = db["users"].find({"_id": {"$in": oids}}, {"name": 1, "role": 1})
            return await cursor.to_list(length=50)
        except Exception:
            return []

    async def _get_diagram(self, db, diagram_id: Optional[str]) -> Optional[dict]:
        if not diagram_id:
            return None
        try:
            did = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            return await db["diagrams"].find_one({"_id": did})
        except Exception:
            return None

    async def _get_recent_history(self, db, project_id: str, limit: int) -> list[dict]:
        try:
            cursor = db["ai_messages"].find({"project_id": str(project_id)}).sort("created_at", -1).limit(limit)
            msgs = await cursor.to_list(length=limit)
            msgs.reverse()
            return msgs
        except Exception:
            return []

    async def _get_active_tasks(self, db, project_id: str) -> list[dict]:
        try:
            pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            cursor = db["ai_tasks"].find(
                {"project_id": pid, "status": {"$in": ["pending", "in_progress"]}},
                {"title": 1, "ai_role": 1, "status": 1}
            ).limit(10)
            return await cursor.to_list(length=10)
        except Exception:
            return []

    def _format_members(self, members: list[dict]) -> str:
        if not members:
            return "  (Sin miembros registrados)"
        lines = []
        for m in members:
            name = m.get("name") or "Usuario"
            role = m.get("role", "dev")
            lines.append(f"  - {name} ({role})")
        return "\n".join(lines)

    def _summarize_diagram(self, graph_data: Any) -> str:
        """Converts graph JSON to human-readable text, resolving node UUIDs to class names."""
        if not graph_data or not isinstance(graph_data, dict):
            return "  Diagrama vacío"
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        # Build ID -> Name resolution map
        id_to_name: Dict[str, str] = {}
        for node in nodes:
            nid = str(node.get("id", ""))
            data = node.get("data", {})
            name = data.get("name") or nid
            if nid:
                id_to_name[nid] = name

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
            raw_src = str(edge.get("source", "?"))
            raw_tgt = str(edge.get("target", "?"))
            src_name = id_to_name.get(raw_src, raw_src)
            tgt_name = id_to_name.get(raw_tgt, raw_tgt)

            edge_data = edge.get("data", {})
            rel_type = edge_data.get("type", edge.get("type", "association"))
            src_mult = edge_data.get("sourceMultiplicity", edge.get("source_multiplicity", ""))
            tgt_mult = edge_data.get("targetMultiplicity", edge.get("target_multiplicity", ""))
            summary.append(
                f"  RELACIÓN: {src_name} --[{rel_type}]--> {tgt_name} [{src_mult}:{tgt_mult}]"
            )

        return "\n".join(summary) if summary else "  Diagrama vacío"

    def _format_history(self, messages: list[dict]) -> str:
        if not messages:
            return "  (Sin historial previo)"
        lines = []
        for msg in messages:
            author = msg.get("author_name", "Desconocido")
            content = (msg.get("content") or "").replace("\n", " ")[:150]
            role = msg.get("ai_role", "")
            if msg.get("author_type") == "ai" and role:
                lines.append(f"  [{role.upper()}]: {content}")
            else:
                lines.append(f"  [{author}]: {content}")
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
