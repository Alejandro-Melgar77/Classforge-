"""
Canonical UML Diagram Model and Adapters for ClassForge.

Defines the single source of truth for UML diagram state and adapts
discrepant serialization formats (flat snake_case, nested camelCase data, AntV X6, and XMI 2.1).
"""
from __future__ import annotations
import hashlib
import json
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class Attribute(BaseModel):
    name: str
    type: str = "String"
    visibility: str = "+"  # "+", "-", "#", "~"


class Method(BaseModel):
    name: str
    params: str = ""
    return_type: str = "void"
    visibility: str = "+"


class Node(BaseModel):
    id: str
    name: str
    type: str = "class"  # class, interface, abstract, enum, note, package
    stereotype: Optional[str] = None
    attributes: List[Attribute] = Field(default_factory=list)
    methods: List[Method] = Field(default_factory=list)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    size: Dict[str, float] = Field(default_factory=lambda: {"width": 220.0, "height": 140.0})
    notes: Optional[str] = None
    enum_values: List[str] = Field(default_factory=list)


class Edge(BaseModel):
    id: str
    type: str = "association"  # association, inheritance, composition, aggregation, dependency, realization
    source: str
    target: str
    label: Optional[str] = None
    source_multiplicity: Optional[str] = None
    target_multiplicity: Optional[str] = None


class Diagram(BaseModel):
    id: Optional[str] = None
    name: str = "Diagrama"
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    viewport: Optional[Dict[str, Any]] = None

    def get_node(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_node_by_name(self, name: str) -> Optional[Node]:
        for n in self.nodes:
            if n.name.strip().lower() == name.strip().lower():
                return n
        return None

    def get_node_name(self, node_id: str) -> str:
        """Resolves a node ID to its human-readable class name, or returns node_id if unknown."""
        node = self.get_node(node_id)
        if node and node.name:
            return node.name
        return node_id

    def find_edges_for_node(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

    def to_graph_data(self) -> Dict[str, Any]:
        """Serializes back to canonical ClassForge GraphData format."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "position": n.position,
                    "size": n.size,
                    "data": {
                        "name": n.name,
                        "stereotype": n.stereotype,
                        "attributes": [a.model_dump() for a in n.attributes],
                        "methods": [m.model_dump() for m in n.methods],
                        "notes": n.notes,
                        "enum_values": n.enum_values,
                    },
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "type": e.type,
                    "source": e.source,
                    "target": e.target,
                    "label": e.label,
                    "source_multiplicity": e.source_multiplicity,
                    "target_multiplicity": e.target_multiplicity,
                }
                for e in self.edges
            ],
            "viewport": self.viewport or {"x": 0, "y": 0, "zoom": 1},
        }

    def compute_hash(self) -> str:
        """Computes deterministic structural hash of this diagram."""
        return compute_canonical_diagram_hash(self)


def compute_canonical_diagram_hash(diagram: Diagram) -> str:
    """Computes a deterministic SHA-256 hash of the canonical diagram structure.
    Focuses on structural elements (classes, types, attributes, methods, edges, multiplicities)
    so purely layout/viewport changes do not trigger false positive AI re-analysis.
    """
    sorted_nodes = []
    for n in sorted(diagram.nodes, key=lambda x: str(x.id)):
        attrs = sorted([f"{a.visibility}{a.name}:{a.type}" for a in n.attributes])
        methods = sorted([f"{m.visibility}{m.name}({m.params}):{m.return_type}" for m in n.methods])
        sorted_nodes.append({
            "id": str(n.id),
            "name": n.name.strip(),
            "type": n.type,
            "stereotype": n.stereotype or "",
            "attrs": attrs,
            "methods": methods,
            "enum_values": sorted(n.enum_values),
        })

    sorted_edges = []
    for e in sorted(diagram.edges, key=lambda x: str(x.id)):
        sorted_edges.append({
            "id": str(e.id),
            "type": e.type,
            "source": str(e.source),
            "target": str(e.target),
            "label": e.label or "",
            "source_mult": e.source_multiplicity or "",
            "target_mult": e.target_multiplicity or "",
        })

    canonical_obj = {
        "nodes": sorted_nodes,
        "edges": sorted_edges,
    }
    encoded = json.dumps(canonical_obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ── Adapters ──────────────────────────────────────────────────────────────────

def _normalize_cell_endpoint(val: Any) -> str:
    """Extracts node ID if endpoint is an AntV X6 cell object `{"cell": "..."}` or string."""
    if isinstance(val, dict):
        return str(val.get("cell") or val.get("id") or "")
    return str(val or "")


def from_graph_data(raw: Any) -> Diagram:
    """Adapts raw graph data dictionary into canonical Diagram.
    
    Tolerates both variants:
    1. Flat snake_case: `edge.source_multiplicity`, `edge.target_multiplicity`, `edge.type`.
    2. Nested camelCase: `edge.data.sourceMultiplicity`, `edge.data.targetMultiplicity`, `edge.data.type`.
    And nodes with `data.name`, `data.attributes` or top-level `name`, `attributes`.
    """
    if not raw or not isinstance(raw, dict):
        return Diagram()

    raw_nodes = raw.get("nodes", [])
    raw_edges = raw.get("edges", [])
    nodes: List[Node] = []
    edges: List[Edge] = []

    for item in raw_nodes:
        if not isinstance(item, dict):
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        
        node_id = str(item.get("id") or data.get("id") or uuid.uuid4())
        name = str(data.get("name") or item.get("name") or "Clase").strip()
        node_type = str(item.get("type") or data.get("type") or "class").strip()

        # Parse attributes
        raw_attrs = data.get("attributes") or item.get("attributes") or []
        attributes: List[Attribute] = []
        for a in raw_attrs:
            if isinstance(a, dict):
                attributes.append(Attribute(
                    name=str(a.get("name", "")).strip(),
                    type=str(a.get("type", "String")).strip() or "String",
                    visibility=str(a.get("visibility", "+")).strip() or "+",
                ))

        # Parse methods
        raw_methods = data.get("methods") or item.get("methods") or []
        methods: List[Method] = []
        for m in raw_methods:
            if isinstance(m, dict):
                methods.append(Method(
                    name=str(m.get("name", "")).strip(),
                    params=str(m.get("params", "")).strip(),
                    return_type=str(m.get("return_type", "void")).strip() or "void",
                    visibility=str(m.get("visibility", "+")).strip() or "+",
                ))

        # Parse position & size
        pos = item.get("position") if isinstance(item.get("position"), dict) else {"x": 0.0, "y": 0.0}
        size = item.get("size") if isinstance(item.get("size"), dict) else {"width": 220.0, "height": 140.0}

        enum_vals = data.get("enum_values") or item.get("enum_values") or []
        if isinstance(enum_vals, list):
            enum_vals = [str(v) for v in enum_vals]
        else:
            enum_vals = []

        nodes.append(Node(
            id=node_id,
            name=name,
            type=node_type,
            stereotype=data.get("stereotype") or item.get("stereotype"),
            attributes=attributes,
            methods=methods,
            position={"x": float(pos.get("x", 0.0)), "y": float(pos.get("y", 0.0))},
            size={"width": float(size.get("width", 220.0)), "height": float(size.get("height", 140.0))},
            notes=data.get("notes") or item.get("notes"),
            enum_values=enum_vals,
        ))

    for item in raw_edges:
        if not isinstance(item, dict):
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}

        edge_id = str(item.get("id") or data.get("id") or uuid.uuid4())
        source = _normalize_cell_endpoint(item.get("source") or data.get("source"))
        target = _normalize_cell_endpoint(item.get("target") or data.get("target"))

        # Tolerant extraction of edge type
        edge_type = str(
            item.get("type")
            or data.get("type")
            or data.get("relation_type")
            or "association"
        ).strip().lower()

        # Tolerant extraction of multiplicities (flat snake_case vs nested camelCase/snake_case)
        src_mult = (
            item.get("source_multiplicity")
            or data.get("sourceMultiplicity")
            or data.get("source_multiplicity")
            or None
        )
        tgt_mult = (
            item.get("target_multiplicity")
            or data.get("targetMultiplicity")
            or data.get("target_multiplicity")
            or None
        )

        label = item.get("label") or data.get("label") or None

        edges.append(Edge(
            id=edge_id,
            type=edge_type,
            source=source,
            target=target,
            label=str(label) if label else None,
            source_multiplicity=str(src_mult) if src_mult else None,
            target_multiplicity=str(tgt_mult) if tgt_mult else None,
        ))

    return Diagram(
        id=raw.get("id") or raw.get("_id"),
        name=raw.get("name") or "Diagrama",
        nodes=nodes,
        edges=edges,
        viewport=raw.get("viewport"),
    )


def from_x6_json(x6_json: Any) -> Diagram:
    """Adapts raw AntV X6 graph JSON (`cells`) into canonical Diagram."""
    if not x6_json or not isinstance(x6_json, dict):
        return Diagram()

    cells = x6_json.get("cells", [])
    raw_nodes = []
    raw_edges = []

    for cell in cells:
        if not isinstance(cell, dict):
            continue
        shape = cell.get("shape", "")
        if cell.get("source") and cell.get("target"):
            # Edge cell
            raw_edges.append(cell)
        elif shape.startswith("uml-") or "data" in cell:
            # Node cell
            raw_nodes.append(cell)

    return from_graph_data({"nodes": raw_nodes, "edges": raw_edges})


def from_xmi(xmi_str: str) -> Diagram:
    """Adapts OMG XMI 2.1 / Eclipse UML 2.5 XML string into canonical Diagram."""
    if not xmi_str or not xmi_str.strip():
        return Diagram()

    try:
        root = ET.fromstring(xmi_str)
    except Exception:
        return Diagram()

    vis_map = {'public': '+', 'private': '-', 'protected': '#', 'package': '~'}
    nodes: List[Node] = []
    edges: List[Edge] = []

    # Map packagedElements
    for pe in root.findall('.//packagedElement'):
        pe_type = pe.get('type') or pe.get('{http://www.omg.org/spec/XMI/20131001}type', '')
        node_id = pe.get('{http://www.omg.org/spec/XMI/20131001}id') or pe.get('id')
        if not node_id:
            continue

        if pe_type in ['Class', 'uml:Class', 'Interface', 'uml:Interface', 'Enumeration', 'uml:Enumeration']:
            ntype = 'class'
            if 'Interface' in pe_type:
                ntype = 'interface'
            elif 'Enumeration' in pe_type:
                ntype = 'enum'
            elif pe.get('isAbstract') == 'true':
                ntype = 'abstract'

            attrs: List[Attribute] = []
            for a in pe.findall('./ownedAttribute'):
                attrs.append(Attribute(
                    name=a.get('name', 'attr'),
                    type="String",
                    visibility=vis_map.get(a.get('visibility', 'public'), '+'),
                ))

            methods: List[Method] = []
            for op in pe.findall('./ownedOperation'):
                methods.append(Method(
                    name=op.get('name', 'method'),
                    return_type="void",
                    visibility=vis_map.get(op.get('visibility', 'public'), '+'),
                ))

            nodes.append(Node(
                id=node_id,
                name=pe.get('name', 'Clase'),
                type=ntype,
                attributes=attrs,
                methods=methods,
            ))

            # Check for generalisations
            for gen in pe.findall('./generalization'):
                general = gen.get('general')
                if general:
                    edges.append(Edge(
                        id=str(gen.get('{http://www.omg.org/spec/XMI/20131001}id') or uuid.uuid4()),
                        type="inheritance",
                        source=node_id,
                        target=general,
                    ))

        elif pe_type in ['Association', 'uml:Association']:
            ends = pe.findall('.//ownedEnd')
            if len(ends) >= 2:
                src = ends[0].get('type')
                tgt = ends[1].get('type')
                if src and tgt:
                    edges.append(Edge(
                        id=node_id,
                        type="association",
                        source=src,
                        target=tgt,
                    ))

    return Diagram(nodes=nodes, edges=edges)


def from_ws_message(msg: dict) -> Diagram:
    """Adapts collaboration WebSocket payloads into canonical Diagram."""
    if not isinstance(msg, dict):
        return Diagram()
    payload = msg.get("payload") or msg.get("graph_data") or msg
    return from_graph_data(payload)
