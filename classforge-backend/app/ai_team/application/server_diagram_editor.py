"""
ServerDiagramEditor: Bot diagram editor for autonomous changes (P5 Bloque E).

Acts as bot user 'ai:<role>' in the diagram collaboration room:
- Acquires pessimistic locks
- Enforces limits: <= 10 operations, NEVER deletes classes without human confirmation
- Validates against canonical schema and ensures linter has no cyclic inheritance
- Persists snapshot in history: 'IA <rol>: <título>'
- Broadcasts NODE_OPERATION / EDGE_OPERATION over diagram WebSocket
- Releases all locks
"""
from __future__ import annotations
import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from app.core.config import settings
from app.ai_team.domain.diagram_model import (
    Diagram,
    Node,
    Edge,
    Attribute,
    Method,
    from_graph_data,
)
from app.ai_team.domain.lint import lint_diagram
from app.modules.ai.schemas import UMLCommandResponse
from app.modules.collaboration.connection_manager import manager
from app.modules.diagrams.repository import DiagramRepository

logger = logging.getLogger(__name__)


class ServerDiagramEditor:
    """Safely applies autonomous UML modifications to diagrams on behalf of AI roles."""

    def __init__(self, db):
        self.db = db
        self.repo = DiagramRepository(db)

    async def apply_command(
        self,
        diagram_id: str,
        role_id: str,
        command: UMLCommandResponse,
        title: str = "Mejoras de diseño",
    ) -> Tuple[bool, int, str]:
        """Applies a UMLCommandResponse to the diagram atomically.
        
        Returns:
            Tuple[success: bool, operations_count: int, message: str]
        """
        bot_user_id = f"ai:{role_id}"
        room_key = f"diagram:{diagram_id}"

        # 1. Fetch current diagram
        diagram_doc = await self.repo.get_by_id(diagram_id)
        if not diagram_doc:
            return False, 0, "Diagrama no encontrado"

        current_graph = diagram_doc.get("graph_data", {"nodes": [], "edges": []})
        canonical = from_graph_data(current_graph)

        # 2. Limit check: <= 10 operations
        total_ops = len(command.classes) + len(command.relations) + len(command.deleted_elements)
        if total_ops > settings.AI_MAX_OPERATIONS_PER_APPLY:
            return (
                False,
                0,
                f"Límite de operaciones excedido ({total_ops} > {settings.AI_MAX_OPERATIONS_PER_APPLY}). "
                "Requiere intervención humana.",
            )

        # 3. Safety check: NEVER delete classes without human approval
        if command.deleted_elements:
            for elem_id in command.deleted_elements:
                node = canonical.get_node(elem_id) or canonical.get_node_by_name(elem_id)
                if node:
                    return (
                        False,
                        0,
                        f"Operación rechazada: La IA no puede eliminar la clase '{node.name}' "
                        "de forma autónoma sin aprobación humana.",
                    )

        # 4. Simulation & Linter validation: Must not introduce circular inheritance or critical faults
        simulated_canonical = copy.deepcopy(canonical)
        simulated_success, sim_msg = self._simulate_apply(simulated_canonical, command)
        if not simulated_success:
            return False, 0, f"Error validando esquema canónico: {sim_msg}"

        sim_findings = lint_diagram(simulated_canonical)
        has_critical_error = any(f.rule in ("inheritance-cycle", "circular-inheritance") or f.severity == "critical" for f in sim_findings)
        if has_critical_error:
            return (
                False,
                0,
                "Operación rechazada: La propuesta introduce ciclos de herencia o errores críticos en el modelo.",
            )

        # 5. Acquire locks on affected elements
        locked_elements: List[str] = []
        try:
            for c_cmd in command.classes:
                existing_node = canonical.get_node_by_name(c_cmd.name)
                el_id = existing_node.id if existing_node else f"new_{c_cmd.name}"
                if manager.acquire_lock(diagram_id, bot_user_id, el_id):
                    locked_elements.append(el_id)

            for r_cmd in command.relations:
                rel_id = f"rel_{r_cmd.source}_{r_cmd.target}"
                if manager.acquire_lock(diagram_id, bot_user_id, rel_id):
                    locked_elements.append(rel_id)

            # 6. Apply changes and broadcast WS operations
            applied_ops = 0
            new_graph = simulated_canonical.to_graph_data()

            # Broadcast simulated additions/modifications to diagram room
            for n in simulated_canonical.nodes:
                orig = canonical.get_node(n.id)
                if not orig:
                    await manager.broadcast(room_key, {
                        "type": "NODE_OPERATION",
                        "op": "add",
                        "node_id": n.id,
                        "data": {
                            "type": n.type,
                            "position": n.position,
                            "size": n.size,
                            "data": {
                                "name": n.name,
                                "stereotype": n.stereotype,
                                "attributes": [a.model_dump() for a in n.attributes],
                                "methods": [m.model_dump() for m in n.methods],
                            },
                        },
                        "user_id": bot_user_id,
                    })
                    applied_ops += 1
                elif orig.model_dump() != n.model_dump():
                    await manager.broadcast(room_key, {
                        "type": "NODE_OPERATION",
                        "op": "update",
                        "node_id": n.id,
                        "data": {
                            "data": {
                                "name": n.name,
                                "stereotype": n.stereotype,
                                "attributes": [a.model_dump() for a in n.attributes],
                                "methods": [m.model_dump() for m in n.methods],
                            }
                        },
                        "user_id": bot_user_id,
                    })
                    applied_ops += 1

            for e in simulated_canonical.edges:
                orig_edge = next((x for x in canonical.edges if x.id == e.id), None)
                if not orig_edge:
                    await manager.broadcast(room_key, {
                        "type": "EDGE_OPERATION",
                        "op": "add",
                        "edge_id": e.id,
                        "data": {
                            "type": e.type,
                            "source": e.source,
                            "target": e.target,
                            "label": e.label,
                            "source_multiplicity": e.source_multiplicity,
                            "target_multiplicity": e.target_multiplicity,
                        },
                        "user_id": bot_user_id,
                    })
                    applied_ops += 1

            # 7. Persist to MongoDB with snapshot in history
            comment = f"IA {role_id.capitalize()}: {title}"
            # Use system or bot identifier as saved_by
            saved_by = "000000000000000000000000"
            await self.repo.save_graph(diagram_id, new_graph, saved_by=saved_by, comment=comment)

            # Optional AI_FOCUS event (TODO P7b / lienzo highlighting)
            focus_ids = [n.id for n in simulated_canonical.nodes if not canonical.get_node(n.id)]
            if focus_ids:
                await manager.broadcast(room_key, {
                    "type": "AI_FOCUS",
                    "element_ids": focus_ids,
                    "role": role_id,
                })

            return True, applied_ops, f"Se aplicaron {applied_ops} cambios correctamente al diagrama."

        finally:
            # 8. Release all locks
            manager.release_all_user_locks(diagram_id, bot_user_id)

    def _simulate_apply(self, diagram: Diagram, cmd: UMLCommandResponse) -> Tuple[bool, str]:
        """Mutates simulated Diagram in place based on command instructions."""
        # 1. Classes
        for c in cmd.classes:
            node = diagram.get_node_by_name(c.name)
            attrs = [
                Attribute(name=a.name, type=a.type, visibility=a.visibility)
                for a in c.attributes
            ]
            methods = [
                Method(name=m.name, params=m.params, return_type=m.return_type, visibility=m.visibility)
                for m in c.methods
            ]
            if node:
                # Merge or replace attributes
                node.attributes = attrs
                node.methods = methods
                if c.stereotype:
                    node.stereotype = c.stereotype
            else:
                new_id = f"node_{uuid.uuid4().hex[:8]}"
                diagram.nodes.append(Node(
                    id=new_id,
                    name=c.name.strip(),
                    type="class",
                    stereotype=c.stereotype,
                    attributes=attrs,
                    methods=methods,
                    position={"x": 150.0 + len(diagram.nodes) * 50, "y": 150.0},
                ))

        # 2. Relations
        for r in cmd.relations:
            src_node = diagram.get_node_by_name(r.source) or diagram.get_node(r.source)
            tgt_node = diagram.get_node_by_name(r.target) or diagram.get_node(r.target)
            if not src_node or not tgt_node:
                continue

            # Check if relation already exists between these endpoints
            existing_edge = next(
                (e for e in diagram.edges if e.source == src_node.id and e.target == tgt_node.id and e.type == r.type),
                None
            )
            if not existing_edge:
                diagram.edges.append(Edge(
                    id=f"edge_{uuid.uuid4().hex[:8]}",
                    type=r.type,
                    source=src_node.id,
                    target=tgt_node.id,
                    label=r.label,
                    source_multiplicity=r.source_multiplicity,
                    target_multiplicity=r.target_multiplicity,
                ))

        return True, "Simulation ok"
