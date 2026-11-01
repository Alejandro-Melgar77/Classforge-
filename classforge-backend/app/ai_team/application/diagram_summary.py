"""
DiagramSummary: Summarizes canonical UML diagrams for AI context injection.

Resolves internal UUIDs to human-readable class names, respects token budgets
(AI_CONTEXT_BUDGET_TOKENS), and prioritizes recently touched elements.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
from app.ai_team.domain.diagram_model import Diagram, Node, Edge
from app.ai_team.domain.lint import Finding
from app.ai_team.infrastructure.knowledge_loader import estimate_tokens


def format_edge_line(edge: Edge, diagram: Diagram) -> str:
    """Formats an edge with resolved class names instead of raw IDs."""
    src_name = diagram.get_node_name(edge.source)
    tgt_name = diagram.get_node_name(edge.target)
    src_m = edge.source_multiplicity or ""
    tgt_m = edge.target_multiplicity or ""
    mult_str = f" [{src_m}:{tgt_m}]" if (src_m or tgt_m) else ""
    label_str = f" (rol: '{edge.label}')" if edge.label else ""
    return f"  - {src_name} --[{edge.type}]--> {tgt_name}{mult_str}{label_str}"


def format_node_full(node: Node) -> str:
    """Detailed formatting of a class/classifier."""
    st = f" <<{node.stereotype}>>" if node.stereotype else ""
    header = f"  CLASE: {node.name}{st} (tipo: {node.type})"
    
    attrs_lines = []
    if node.attributes:
        for a in node.attributes:
            attrs_lines.append(f"    - {a.visibility} {a.name}: {a.type}")
    elif node.enum_values:
        attrs_lines.append(f"    - Valores: {', '.join(node.enum_values)}")
    else:
        attrs_lines.append("    - (Sin atributos)")

    methods_lines = []
    if node.methods:
        for m in node.methods:
            params = f"({m.params})" if m.params else "()"
            methods_lines.append(f"    - {m.visibility} {m.name}{params}: {m.return_type}")
    else:
        methods_lines.append("    - (Sin métodos)")

    return "\n".join([header, "    Atributos:", *attrs_lines, "    Métodos:", *methods_lines])


def format_node_compact(node: Node) -> str:
    """Compact single-line summary of a class for budget constraints."""
    st = f" <<{node.stereotype}>>" if node.stereotype else ""
    attrs_count = len(node.attributes) or len(node.enum_values)
    meths_count = len(node.methods)
    return f"  CLASE: {node.name}{st} ({node.type}) [{attrs_count} atributos, {meths_count} métodos]"


def summarize_diagram(
    diagram: Diagram,
    budget_tokens: int = 2000,
    recently_touched_ids: Optional[List[str]] = None,
    findings: Optional[List[Finding]] = None,
) -> str:
    """Produces a human-readable diagram summary with resolved names respecting budget_tokens.
    
    Prioritizes classes listed in recently_touched_ids and their direct neighbors.
    """
    if not diagram.nodes:
        return "Diagrama vacío (sin clases ni relaciones registradas)."

    # Determine priority IDs
    priority_ids: Set[str] = set(recently_touched_ids or [])
    if priority_ids:
        # Include direct neighbors
        for edge in diagram.edges:
            if edge.source in priority_ids:
                priority_ids.add(edge.target)
            elif edge.target in priority_ids:
                priority_ids.add(edge.source)

    # Sort nodes: priority nodes first, then alphabetical
    def node_sort_key(n: Node):
        is_priority = 0 if n.id in priority_ids else 1
        return (is_priority, n.name.lower())

    sorted_nodes = sorted(diagram.nodes, key=node_sort_key)

    # 1. First attempt: Full representation
    classes_blocks: List[str] = []
    for node in sorted_nodes:
        classes_blocks.append(format_node_full(node))

    edges_blocks: List[str] = []
    for edge in diagram.edges:
        edges_blocks.append(format_edge_line(edge, diagram))

    findings_blocks: List[str] = []
    if findings:
        for f in findings:
            target_names = [diagram.get_node_name(eid) for eid in f.element_ids]
            targets_str = f" [Elementos: {', '.join(target_names)}]" if target_names else ""
            findings_blocks.append(
                f"  - [{f.severity.upper()}] {f.rule}: {f.message_es}{targets_str} (Sugerencia: {f.fix_hint})"
            )

    full_text = _assemble_summary(classes_blocks, edges_blocks, findings_blocks)
    if estimate_tokens(full_text) <= budget_tokens:
        return full_text

    # 2. Second attempt: Keep priority classes full, compact the rest
    classes_blocks = []
    for node in sorted_nodes:
        if node.id in priority_ids or not priority_ids:
            classes_blocks.append(format_node_full(node))
        else:
            classes_blocks.append(format_node_compact(node))

    compact_text = _assemble_summary(classes_blocks, edges_blocks, findings_blocks)
    if estimate_tokens(compact_text) <= budget_tokens:
        return compact_text

    # 3. Third attempt: All classes compact
    classes_blocks = [format_node_compact(node) for node in sorted_nodes]
    minimal_text = _assemble_summary(classes_blocks, edges_blocks, findings_blocks)
    if estimate_tokens(minimal_text) <= budget_tokens:
        return minimal_text

    # 4. Strict budget truncation: trim classes until it fits
    trimmed_classes = []
    for cb in classes_blocks:
        trial = _assemble_summary(trimmed_classes + [cb], edges_blocks, findings_blocks)
        if estimate_tokens(trial) > budget_tokens:
            omitted = len(classes_blocks) - len(trimmed_classes)
            trimmed_classes.append(f"  [... {omitted} clases adicionales omitidas por límite de presupuesto ...]")
            break
        trimmed_classes.append(cb)

    return _assemble_summary(trimmed_classes, edges_blocks, findings_blocks)


def _assemble_summary(
    classes_blocks: List[str],
    edges_blocks: List[str],
    findings_blocks: List[str],
) -> str:
    sections = []
    if classes_blocks:
        sections.append("ESTRUCTURA DE CLASIFICADORES:\n" + "\n\n".join(classes_blocks))
    if edges_blocks:
        sections.append("RELACIONES:\n" + "\n".join(edges_blocks))
    else:
        sections.append("RELACIONES:\n  (Sin relaciones entre clasificadores)")
    if findings_blocks:
        sections.append("HALLAZGOS DEL LINTER (HECHOS DETERMINISTAS VERIFICADOS):\n" + "\n".join(findings_blocks))
    return "\n\n".join(sections)
