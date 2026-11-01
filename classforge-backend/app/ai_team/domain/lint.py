"""
Deterministic UML Linter for ClassForge.

Pure functions that validate structural, semantic, and stylistic UML rules
without calling an LLM. Findings are delivered as verified facts to AI roles.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field

from app.ai_team.domain.diagram_model import Diagram, Node, Edge


Severity = Literal["info", "warn", "critical"]


class Finding(BaseModel):
    rule: str
    severity: Severity
    element_ids: List[str] = Field(default_factory=list)
    message_es: str
    fix_hint: str


# ── Multiplicity Parsing Helpers ──────────────────────────────────────────────

def _is_many(mult: Optional[str]) -> bool:
    if not mult:
        return False
    clean = mult.strip().lower()
    return clean in ("*", "n", "m", "0..*", "1..*", "0..n", "1..n") or clean.endswith("..*")


def _validate_multiplicity_bounds(mult: Optional[str]) -> Optional[str]:
    """Returns an error message if multiplicity has inverted bounds (e.g. '2..1') or invalid syntax."""
    if not mult:
        return None
    clean = mult.strip()
    if clean in ("*", "0", "1", "0..1", "1..1", "0..*", "1..*", "N", "M"):
        return None

    # Check range "lower..upper"
    m = re.match(r"^(\d+)\.\.(\d+|\*)$", clean)
    if m:
        low = int(m.group(1))
        upper_str = m.group(2)
        if upper_str != "*":
            high = int(upper_str)
            if low > high:
                return f"Límite inferior ({low}) mayor que el superior ({high})"
        return None

    # Check standalone integer
    if clean.isdigit():
        return None

    # Unknown or malformed pattern
    if ".." in clean:
        return f"Formato de rango no válido: '{clean}'"
    return None


def _to_pascal_case_suggestion(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name)
    parts = cleaned.replace("_", " ").split()
    return "".join(p.capitalize() for p in parts) or "Clase"


def _to_camel_case_suggestion(name: str) -> str:
    pascal = _to_pascal_case_suggestion(name)
    if not pascal:
        return "atributo"
    return pascal[0].lower() + pascal[1:]


# ── Cycle Detection ───────────────────────────────────────────────────────────

def _detect_inheritance_cycles(diagram: Diagram) -> List[List[str]]:
    """Detects all cycles in the inheritance graph (source -> target)."""
    adj: Dict[str, List[str]] = {}
    for edge in diagram.edges:
        if edge.type == "inheritance":
            adj.setdefault(edge.source, []).append(edge.target)

    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: List[str] = []

    def dfs(curr: str):
        visited.add(curr)
        rec_stack.append(curr)

        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Cycle found from neighbor to curr
                cycle_start_idx = rec_stack.index(neighbor)
                cycle_path = rec_stack[cycle_start_idx:] + [neighbor]
                cycles.append(cycle_path)

        rec_stack.pop()

    for node in diagram.nodes:
        if node.id not in visited and node.id in adj:
            dfs(node.id)

    return cycles


# ── Main Linter ───────────────────────────────────────────────────────────────

def lint(diagram: Diagram, god_class_threshold: int = 15) -> List[Finding]:
    """Runs all pure deterministic rules against a Diagram and returns findings."""
    findings: List[Finding] = []

    # 1. Duplicate class names
    name_to_ids: Dict[str, List[str]] = {}
    for node in diagram.nodes:
        if node.type in ("class", "abstract", "interface", "enum"):
            norm = node.name.strip().lower()
            name_to_ids.setdefault(norm, []).append(node.id)

    for norm_name, ids in name_to_ids.items():
        if len(ids) > 1:
            names_display = diagram.get_node_name(ids[0])
            findings.append(Finding(
                rule="duplicate-class-name",
                severity="critical",
                element_ids=ids,
                message_es=f"Existe más de un clasificador con el nombre '{names_display}'.",
                fix_hint="Renombra o unifica las clases duplicadas para evitar colisiones en el código generado.",
            ))

    # 2. Per-node rules
    for node in diagram.nodes:
        # Rule: class-not-pascal-case
        if node.type in ("class", "abstract", "interface", "enum"):
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                findings.append(Finding(
                    rule="class-not-pascal-case",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"El nombre '{node.name}' de la clase no sigue la convención PascalCase.",
                    fix_hint=f"Renombra a PascalCase iniciando con mayúscula (ej. '{_to_pascal_case_suggestion(node.name)}').",
                ))

        # Rule: class-no-attributes
        if node.type in ("class", "abstract"):
            if len(node.attributes) == 0:
                findings.append(Finding(
                    rule="class-no-attributes",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"La clase '{node.name}' no tiene atributos definidos.",
                    fix_hint="Define atributos para modelar el estado de la entidad o evalúa si debe ser interfaz.",
                ))

        # Rule: missing-primary-key (for standard classes)
        if node.type in ("class", "abstract"):
            stereotype = (node.stereotype or "").lower()
            if stereotype not in ("value_object", "embedded", "utility"):
                has_pk = any(
                    a.name.lower() in ("id", "uuid", "pk")
                    or a.name.lower().endswith("id")
                    or a.name.lower().endswith("_id")
                    for a in node.attributes
                )
                if not has_pk and len(node.attributes) > 0:
                    findings.append(Finding(
                        rule="missing-primary-key",
                        severity="warn",
                        element_ids=[node.id],
                        message_es=f"La entidad '{node.name}' no posee un atributo identificador ('id').",
                        fix_hint="Añade un atributo 'id: Long' o 'id: UUID' para facilitar la persistencia ORM.",
                    ))

        # Rule: interface-has-instance-attributes
        if node.type == "interface":
            if len(node.attributes) > 0:
                findings.append(Finding(
                    rule="interface-has-instance-attributes",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"La interfaz '{node.name}' define atributos de instancia.",
                    fix_hint="Las interfaces UML no deben alojar estado de instancia; traslada los atributos a las clases implementadoras.",
                ))

        # Rule: enum-empty
        if node.type == "enum":
            has_values = bool(node.enum_values or node.attributes)
            if not has_values:
                findings.append(Finding(
                    rule="enum-empty",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"La enumeración '{node.name}' no tiene valores ni literales definidos.",
                    fix_hint="Agrega constantes a la enumeración para representar sus posibles estados.",
                ))

        # Rule: god-class
        if node.type in ("class", "abstract"):
            total_members = len(node.attributes) + len(node.methods)
            if total_members > god_class_threshold:
                findings.append(Finding(
                    rule="god-class",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"Clase Dios detectada: '{node.name}' tiene {total_members} miembros (> {god_class_threshold}), violando SRP.",
                    fix_hint="Aplica el principio de responsabilidad única (SRP) descomponiendo la clase en módulos especializados.",
                ))

        # Rule: attribute-not-camel-case
        for attr in node.attributes:
            if not re.match(r"^[a-z][a-zA-Z0-9]*$", attr.name):
                findings.append(Finding(
                    rule="attribute-not-camel-case",
                    severity="info",
                    element_ids=[node.id],
                    message_es=f"El atributo '{attr.name}' en '{node.name}' no sigue la convención camelCase.",
                    fix_hint=f"Renombra a camelCase iniciando con minúscula (ej. '{_to_camel_case_suggestion(attr.name)}').",
                ))

        # Rule: method-no-return-type
        for meth in node.methods:
            if not meth.return_type or not meth.return_type.strip():
                findings.append(Finding(
                    rule="method-no-return-type",
                    severity="info",
                    element_ids=[node.id],
                    message_es=f"El método '{meth.name}()' en '{node.name}' no especifica tipo de retorno.",
                    fix_hint="Especifica el tipo de retorno explícito (ej. 'void', 'Boolean', 'String').",
                ))

    # 3. Orphan node check
    if len(diagram.nodes) > 1:
        connected_ids: Set[str] = set()
        for edge in diagram.edges:
            connected_ids.add(edge.source)
            connected_ids.add(edge.target)

        for node in diagram.nodes:
            if node.type in ("class", "abstract", "interface", "enum") and node.id not in connected_ids:
                findings.append(Finding(
                    rule="orphan-node",
                    severity="warn",
                    element_ids=[node.id],
                    message_es=f"El clasificador '{node.name}' está huérfano (sin relaciones con otros clasificadores).",
                    fix_hint="Conecta esta clase con relaciones UML apropiadas o elimínala si no forma parte del modelo.",
                ))

    # 4. Inheritance cycles
    cycles = _detect_inheritance_cycles(diagram)
    for cycle in cycles:
        names = [diagram.get_node_name(nid) for nid in cycle]
        chain = " -> ".join(names)
        findings.append(Finding(
            rule="inheritance-cycle",
            severity="critical",
            element_ids=list(set(cycle)),
            message_es=f"Se detectó un ciclo de herencia circular: {chain}.",
            fix_hint="Elimina la herencia circular; una clase no puede heredar directa o indirectamente de sí misma.",
        ))

    # 5. Multiple class inheritance
    class_inheritance_targets: Dict[str, List[str]] = {}
    for edge in diagram.edges:
        if edge.type == "inheritance":
            src_node = diagram.get_node(edge.source)
            tgt_node = diagram.get_node(edge.target)
            # Only check if both are classes (or abstract), not interface realization
            if src_node and src_node.type in ("class", "abstract"):
                if not tgt_node or tgt_node.type in ("class", "abstract"):
                    class_inheritance_targets.setdefault(edge.source, []).append(edge.target)

    for src_id, targets in class_inheritance_targets.items():
        if len(targets) > 1:
            child_name = diagram.get_node_name(src_id)
            parent_names = [diagram.get_node_name(t) for t in targets]
            findings.append(Finding(
                rule="multiple-class-inheritance",
                severity="critical",
                element_ids=[src_id] + targets,
                message_es=f"La clase '{child_name}' hereda de múltiples clases ({', '.join(parent_names)}).",
                fix_hint="Java y Python con SQLAlchemy no soportan herencia múltiple directa de entidades. Usa composición o interfaces.",
            ))

    # 6. Edge rules (N-a-N, invalid multiplicity, duplicate relations)
    seen_edges: Set[str] = set()

    for edge in diagram.edges:
        src_name = diagram.get_node_name(edge.source)
        tgt_name = diagram.get_node_name(edge.target)

        # Rule: duplicate-relation
        edge_key = f"{edge.source}->{edge.target}:{edge.type}"
        if edge_key in seen_edges:
            findings.append(Finding(
                rule="duplicate-relation",
                severity="warn",
                element_ids=[edge.id, edge.source, edge.target],
                message_es=f"Relación duplicada de tipo '{edge.type}' entre '{src_name}' y '{tgt_name}'.",
                fix_hint="Elimina la relación redundante para mantener el grafo simplificado y limpio.",
            ))
        else:
            seen_edges.add(edge_key)

        # Rule: many-to-many-direct
        if edge.type in ("association", "aggregation"):
            if _is_many(edge.source_multiplicity) and _is_many(edge.target_multiplicity):
                findings.append(Finding(
                    rule="many-to-many-direct",
                    severity="warn",
                    element_ids=[edge.id, edge.source, edge.target],
                    message_es=f"Asociación directa N-a-N entre '{src_name}' y '{tgt_name}' sin clase de asociación intermedia.",
                    fix_hint=f"Descompón la relación creando una clase de asociación intermedia (ej. '{src_name}{tgt_name}') con relaciones 1..*.",
                ))

        # Rule: invalid-multiplicity
        for mult_val, endpoint in [(edge.source_multiplicity, "origen"), (edge.target_multiplicity, "destino")]:
            err = _validate_multiplicity_bounds(mult_val)
            if err:
                findings.append(Finding(
                    rule="invalid-multiplicity",
                    severity="critical",
                    element_ids=[edge.id],
                    message_es=f"Multiplicidad {endpoint} '{mult_val}' inválida entre '{src_name}' y '{tgt_name}': {err}.",
                    fix_hint="Corrige la multiplicidad asegurando un formato UML estándar como '1', '0..1', '1..*' o '0..*'.",
                ))

    return findings


# Alias for backward and forward compatibility
lint_diagram = lint
