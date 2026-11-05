"""
Intelligent UML Normalization Engine for ClassForge (AI-NORM-01).

Provides:
- Non-destructive diagnosis of structural, stylistic, and semantic inconsistencies
- Generation of typed, reviewable Phase 2 operations (update_node, update_attribute, update_edge)
- Preservation of all unaffected elements and semantic meaning.
"""
from __future__ import annotations
import copy
import re
from typing import Any, Dict, List, Optional, Set, Tuple


TYPE_NORMALIZATION_MAP: Dict[str, str] = {
    "str": "String",
    "string": "String",
    "text": "String",
    "varchar": "String",
    "int": "Integer",
    "integer": "Integer",
    "number": "Integer",
    "long": "Long",
    "bigint": "Long",
    "bool": "Boolean",
    "boolean": "Boolean",
    "float": "Double",
    "double": "Double",
    "decimal": "Double",
    "real": "Double",
    "date": "Date",
    "datetime": "Date",
    "timestamp": "Date",
    "time": "Date",
    "list": "List",
    "array": "List",
    "map": "Map",
    "dict": "Map",
    "uuid": "UUID",
    "void": "void",
}


def _to_pascal_case(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name).strip()
    if not cleaned:
        return "Clase"
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    parts = spaced.replace("_", " ").split()
    return "".join(p.capitalize() for p in parts) or "Clase"


def _to_camel_case(name: str) -> str:
    pascal = _to_pascal_case(name)
    if not pascal:
        return "item"
    return pascal[0].lower() + pascal[1:]


def _normalize_multiplicity(mult: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Returns (normalized_multiplicity, issue_description)."""
    if not mult:
        return None, None
    clean = mult.strip()
    if clean in ("*", "n", "N"):
        return "0..*", f"Multiplicidad '{clean}' normalizada al estándar UML '0..*'"
    if clean in ("m", "M"):
        return "1..*", f"Multiplicidad '{clean}' normalizada al estándar UML '1..*'"

    m = re.match(r"^(\d+)\.\.(\d+|\*)$", clean)
    if m:
        low = int(m.group(1))
        upper_str = m.group(2)
        if upper_str != "*":
            high = int(upper_str)
            if low > high:
                # Inverted range e.g. 2..1 -> 1..2
                return f"{high}..{low}", f"Rango invertido '{clean}' corregido a '{high}..{low}'"
    return None, None


def diagnose_normalization(graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyzes graph_data and returns a list of normalization findings.
    Each finding includes rule, severity, element_id, current_value, suggested_value, description.
    """
    if not isinstance(graph_data, dict):
        return []

    findings: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = graph_data.get("nodes", [])
    edges: List[Dict[str, Any]] = graph_data.get("edges", [])

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", ""))
        data = node.get("data") if isinstance(node.get("data"), dict) else node
        name = str(data.get("name", "")).strip()

        # 1. Class PascalCase naming
        if name and not re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
            suggested = _to_pascal_case(name)
            findings.append({
                "rule": "class-naming",
                "severity": "warn",
                "element_id": node_id,
                "element_type": "node",
                "current_value": name,
                "suggested_value": suggested,
                "description": f"El nombre de la clase '{name}' debe seguir la convención PascalCase.",
            })

        # 2. Attributes analysis
        raw_attrs = data.get("attributes", [])
        if isinstance(raw_attrs, list):
            seen_attr_names: Set[str] = set()
            for attr in raw_attrs:
                if not isinstance(attr, dict):
                    continue
                attr_id = str(attr.get("id", attr.get("name", "")))
                attr_name = str(attr.get("name", "")).strip()
                attr_type = str(attr.get("type", "")).strip()

                # Duplicate attribute
                norm_attr_name = attr_name.lower()
                if norm_attr_name in seen_attr_names:
                    findings.append({
                        "rule": "duplicate-attribute",
                        "severity": "warn",
                        "element_id": node_id,
                        "member_id": attr_id,
                        "element_type": "attribute",
                        "current_value": attr_name,
                        "suggested_value": f"{attr_name}Alt",
                        "description": f"Atributo duplicado '{attr_name}' en la clase '{name}'.",
                    })
                else:
                    seen_attr_names.add(norm_attr_name)

                # Attribute camelCase naming
                if attr_name and not re.match(r"^[a-z][a-zA-Z0-9]*$", attr_name):
                    suggested_attr = _to_camel_case(attr_name)
                    findings.append({
                        "rule": "member-naming",
                        "severity": "info",
                        "element_id": node_id,
                        "member_id": attr_id,
                        "element_type": "attribute",
                        "current_value": attr_name,
                        "suggested_value": suggested_attr,
                        "description": f"El atributo '{attr_name}' en '{name}' debe seguir la convención camelCase.",
                    })

                # Type normalization
                lower_type = attr_type.lower()
                if lower_type in TYPE_NORMALIZATION_MAP and TYPE_NORMALIZATION_MAP[lower_type] != attr_type:
                    canon_type = TYPE_NORMALIZATION_MAP[lower_type]
                    findings.append({
                        "rule": "type-normalization",
                        "severity": "info",
                        "element_id": node_id,
                        "member_id": attr_id,
                        "element_type": "attribute",
                        "current_value": attr_type,
                        "suggested_value": canon_type,
                        "description": f"Tipo '{attr_type}' normalizado al estándar '{canon_type}'.",
                    })

        # 3. Methods analysis
        raw_methods = data.get("methods", [])
        if isinstance(raw_methods, list):
            seen_methods: Set[str] = set()
            for meth in raw_methods:
                if not isinstance(meth, dict):
                    continue
                meth_id = str(meth.get("id", meth.get("name", "")))
                meth_name = str(meth.get("name", "")).strip()

                norm_meth_key = f"{meth_name.lower()}:{str(meth.get('params', '')).strip().lower()}"
                if norm_meth_key in seen_methods:
                    findings.append({
                        "rule": "duplicate-method",
                        "severity": "warn",
                        "element_id": node_id,
                        "member_id": meth_id,
                        "element_type": "method",
                        "current_value": meth_name,
                        "suggested_value": f"{meth_name}Alt",
                        "description": f"Método duplicado '{meth_name}' en la clase '{name}'.",
                    })
                else:
                    seen_methods.add(norm_meth_key)

                # Method camelCase naming
                if meth_name and not re.match(r"^[a-z][a-zA-Z0-9]*$", meth_name):
                    suggested_m = _to_camel_case(meth_name)
                    findings.append({
                        "rule": "member-naming",
                        "severity": "info",
                        "element_id": node_id,
                        "member_id": meth_id,
                        "element_type": "method",
                        "current_value": meth_name,
                        "suggested_value": suggested_m,
                        "description": f"El método '{meth_name}()' en '{name}' debe seguir la convención camelCase.",
                    })

    # 4. Edges analysis (multiplicities)
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        edge_id = str(edge.get("id", ""))
        edge_data = edge.get("data") if isinstance(edge.get("data"), dict) else edge

        src_mult = str(edge_data.get("sourceMultiplicity") or edge.get("source_multiplicity") or "")
        tgt_mult = str(edge_data.get("targetMultiplicity") or edge.get("target_multiplicity") or "")

        norm_s, desc_s = _normalize_multiplicity(src_mult)
        if norm_s:
            findings.append({
                "rule": "multiplicity-normalization",
                "severity": "warn",
                "element_id": edge_id,
                "element_type": "edge",
                "endpoint": "source",
                "current_value": src_mult,
                "suggested_value": norm_s,
                "description": desc_s,
            })

        norm_t, desc_t = _normalize_multiplicity(tgt_mult)
        if norm_t:
            findings.append({
                "rule": "multiplicity-normalization",
                "severity": "warn",
                "element_id": edge_id,
                "element_type": "edge",
                "endpoint": "target",
                "current_value": tgt_mult,
                "suggested_value": norm_t,
                "description": desc_t,
            })

    return findings


def build_normalization_operations(
    graph_data: Dict[str, Any],
    rules: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates a list of typed Phase 2 operations to apply all suggested normalizations.
    """
    findings = diagnose_normalization(graph_data)
    if rules:
        rule_set = set(rules)
        findings = [f for f in findings if f["rule"] in rule_set]

    operations: List[Dict[str, Any]] = []

    # Map findings by node/edge
    node_patches: Dict[str, Dict[str, Any]] = {}
    attr_patches: Dict[Tuple[str, str], Dict[str, Any]] = {}
    edge_patches: Dict[str, Dict[str, Any]] = {}

    for f in findings:
        rule = f["rule"]
        elem_id = f["element_id"]
        elem_type = f.get("element_type")

        if rule == "class-naming" and elem_type == "node":
            node_patches.setdefault(elem_id, {}).setdefault("data", {})["name"] = f["suggested_value"]

        elif rule == "member-naming" and elem_type == "attribute":
            attr_patches.setdefault((elem_id, f["member_id"]), {})["name"] = f["suggested_value"]

        elif rule == "type-normalization" and elem_type == "attribute":
            attr_patches.setdefault((elem_id, f["member_id"]), {})["type"] = f["suggested_value"]

        elif rule == "multiplicity-normalization" and elem_type == "edge":
            field_name = "sourceMultiplicity" if f.get("endpoint") == "source" else "targetMultiplicity"
            edge_patches.setdefault(elem_id, {}).setdefault("data", {})[field_name] = f["suggested_value"]

    # Generate update_node operations
    for node_id, patch in sorted(node_patches.items()):
        operations.append({
            "type": "update_node",
            "id": node_id,
            "patch": patch,
        })

    # Generate update_attribute operations
    for (node_id, member_id), patch in sorted(attr_patches.items()):
        operations.append({
            "type": "update_attribute",
            "id": node_id,
            "member_id": member_id,
            "patch": patch,
        })

    # Generate update_edge operations
    for edge_id, patch in sorted(edge_patches.items()):
        operations.append({
            "type": "update_edge",
            "id": edge_id,
            "patch": patch,
        })

    return operations
