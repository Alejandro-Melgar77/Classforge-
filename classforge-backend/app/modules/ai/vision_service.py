from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import SecretStr

from app.core.errors import ValidationError
from app.llm import LlmMessage, LlmRequest, get_provider

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB hard limit


def build_vision_system_prompt() -> str:
    return """You are a senior Software Architect and UML specialist.
Analyze the provided image of a UML class diagram (whiteboard photo, sketch, scanned diagram, or digital screenshot).
Carefully detect all classes, interfaces, attributes, types, methods, and relationships.

You MUST output ONLY a valid raw JSON object matching this exact schema:
{
  "classes": [
    {
      "name": "User",
      "isInterface": false,
      "attributes": [
        {"name": "id", "type": "Long", "visibility": "+"},
        {"name": "email", "type": "String", "visibility": "-"}
      ],
      "methods": [
        {"name": "login", "returnType": "Boolean", "visibility": "+", "parameters": "email: String, pass: String"}
      ]
    }
  ],
  "relationships": [
    {
      "source": "User",
      "target": "Role",
      "type": "association",
      "sourceMultiplicity": "1",
      "targetMultiplicity": "*",
      "label": "has"
    }
  ],
  "summary": "Brief summary in Spanish describing what this diagram represents."
}

Relationship types allowed:
- "association", "inheritance", "composition", "aggregation", "dependency", "realization"
"""


VISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "classes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "isInterface": {"type": "boolean"},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "visibility": {"type": "string"},
                            },
                        },
                    },
                    "methods": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "returnType": {"type": "string"},
                                "visibility": {"type": "string"},
                                "parameters": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["name"],
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "sourceMultiplicity": {"type": "string"},
                    "targetMultiplicity": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["source", "target"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["classes", "relationships"],
}


_X6_NODE_SHAPES = {
    "class": "uml-class",
    "interface": "uml-interface",
    "abstract": "uml-abstract",
    "enum": "uml-enum",
}


def cells_to_graph_data(cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Converts X6 cells into the canonical ClassForge graph (nodes/edges).

    The canvas, the linter and the code generators all consume ``graph_data``
    with ``nodes``/``edges`` and X6-registered shapes (``uml-class`` and friends).
    Emitting ``cells`` with ``class-node`` produced diagrams the canvas could not
    render and that were persisted as an empty graph.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for cell in cells:
        data = cell.get("data") or {}

        if cell.get("shape") == "edge":
            source = cell.get("source")
            target = cell.get("target")
            if isinstance(source, dict):
                source = source.get("cell")
            if isinstance(target, dict):
                target = target.get("cell")
            if not source or not target:
                continue
            edges.append({
                "id": cell.get("id"),
                "source": source,
                "target": target,
                "type": data.get("type") or "association",
                "data": {
                    "sourceMultiplicity": data.get("sourceMultiplicity") or "",
                    "targetMultiplicity": data.get("targetMultiplicity") or "",
                    "label": data.get("label") or "",
                },
            })
            continue

        is_interface = bool(data.get("isInterface"))
        node_type = "interface" if is_interface else str(data.get("type") or "class").lower()
        if node_type not in _X6_NODE_SHAPES:
            node_type = "class"

        attributes = []
        for attr in data.get("attributes", []) or []:
            attributes.append({
                "name": attr.get("name", ""),
                "type": attr.get("type", "String"),
                "visibility": attr.get("visibility", "+"),
                "is_static": attr.get("is_static", False),
            })

        methods = []
        for method in data.get("methods", []) or []:
            raw_params = method.get("params", method.get("parameters", ""))
            if isinstance(raw_params, list):
                params = ", ".join(
                    f"{p.get('name', '')}: {p.get('type', 'String')}" if isinstance(p, dict) else str(p)
                    for p in raw_params
                )
            else:
                params = str(raw_params or "")
            methods.append({
                "name": method.get("name", ""),
                "params": params,
                "return_type": method.get("return_type") or method.get("returnType") or "void",
                "visibility": method.get("visibility", "+"),
                "is_abstract": method.get("is_abstract", False),
            })

        nodes.append({
            "id": cell.get("id"),
            "type": node_type,
            "shape": _X6_NODE_SHAPES[node_type],
            "position": cell.get("position") or {"x": 0, "y": 0},
            "size": cell.get("size") or {"width": 240, "height": 140},
            "data": {
                "name": data.get("name", "Clase"),
                "stereotype": "interface" if is_interface else None,
                "attributes": attributes,
                "methods": methods,
                "notes": None,
            },
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": 0, "y": 0, "zoom": 1.0},
    }


def convert_semantics_to_graph_data(semantics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms extracted semantic classes and relationships into AntV/X6 ClassForge cells.
    """
    cells = []
    classes = semantics.get("classes", [])
    relationships = semantics.get("relationships", [])

    class_name_to_id = {}

    # Layout positions in a grid
    cols = 3
    node_width = 240
    node_min_height = 140
    gap_x = 80
    gap_y = 100
    start_x = 100
    start_y = 100

    for idx, cls in enumerate(classes):
        class_name = cls.get("name", f"Class{idx+1}").strip()
        class_name = re.sub(r"[^a-zA-Z0-9_]", "", class_name) or f"Class{idx+1}"

        node_id = str(uuid.uuid4())
        class_name_to_id[class_name.lower()] = node_id
        class_name_to_id[class_name] = node_id

        row = idx // cols
        col = idx % cols
        pos_x = start_x + col * (node_width + gap_x)
        pos_y = start_y + row * (node_min_height + gap_y)

        # Normalize attributes
        raw_attrs = cls.get("attributes", [])
        clean_attrs = []
        for a in raw_attrs:
            if isinstance(a, dict):
                clean_attrs.append(
                    {
                        "name": a.get("name", "attr"),
                        "type": a.get("type", "String"),
                        "visibility": a.get("visibility", "+"),
                        "isNullable": a.get("isNullable", False),
                    }
                )
            elif isinstance(a, str):
                clean_attrs.append(
                    {
                        "name": a.replace("+", "").replace("-", "").replace("#", "").strip(),
                        "type": "String",
                        "visibility": "+",
                        "isNullable": False,
                    }
                )

        # Normalize methods
        raw_methods = cls.get("methods", [])
        clean_methods = []
        for m in raw_methods:
            if isinstance(m, dict):
                clean_methods.append(
                    {
                        "name": m.get("name", "method"),
                        "returnType": m.get("returnType", "void"),
                        "visibility": m.get("visibility", "+"),
                        "parameters": m.get("parameters", ""),
                    }
                )
            elif isinstance(m, str):
                clean_methods.append(
                    {
                        "name": m.replace("+", "").replace("-", "").replace("#", "").strip(),
                        "returnType": "void",
                        "visibility": "+",
                        "parameters": "",
                    }
                )

        node_cell = {
            "id": node_id,
            "shape": "class-node",
            "position": {"x": pos_x, "y": pos_y},
            "size": {"width": node_width, "height": max(node_min_height, 60 + len(clean_attrs) * 20 + len(clean_methods) * 20)},
            "data": {
                "name": class_name,
                "attributes": clean_attrs,
                "methods": clean_methods,
                "isInterface": cls.get("isInterface", False),
            },
        }
        cells.append(node_cell)

    # Process relationships
    for rel in relationships:
        source_name = str(rel.get("source", "")).strip()
        target_name = str(rel.get("target", "")).strip()

        source_id = class_name_to_id.get(source_name) or class_name_to_id.get(source_name.lower())
        target_id = class_name_to_id.get(target_name) or class_name_to_id.get(target_name.lower())

        if source_id and target_id and source_id != target_id:
            rel_type = rel.get("type", "association")
            label_text = rel.get("label") or ""
            target_mult = rel.get("targetMultiplicity") or ""
            source_mult = rel.get("sourceMultiplicity") or ""

            display_label = label_text
            if target_mult:
                display_label = f"{display_label} [{target_mult}]".strip()

            edge_cell = {
                "id": str(uuid.uuid4()),
                "shape": "edge",
                "source": {"cell": source_id},
                "target": {"cell": target_id},
                "labels": [{"attrs": {"text": {"text": display_label}}}] if display_label else [],
                "data": {
                    "type": rel_type,
                    "sourceMultiplicity": source_mult,
                    "targetMultiplicity": target_mult,
                    "label": label_text,
                },
            }
            cells.append(edge_cell)

    return cells_to_graph_data(cells)


async def generate_diagram_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends an image of a UML diagram to LLM Vision Provider (Gemini / Fake)
    and returns ClassForge graph_data.
    """
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValidationError(f"El tamaño de la imagen ({len(image_bytes)} bytes) excede el límite permitido de 8 MB")

    provider = get_provider(purpose="vision")

    req = LlmRequest(
        system=build_vision_system_prompt(),
        messages=[
            LlmMessage(
                role="user",
                text="Analiza esta imagen y extrae el diagrama UML completo con clases, atributos, métodos y relaciones.",
                image_bytes=image_bytes,
                mime_type=mime_type or "image/jpeg",
            )
        ],
        temperature=0.1,
        purpose="vision",
        json_schema=VISION_JSON_SCHEMA,
        api_key=SecretStr(api_key) if api_key else None,
        model=model,
    )

    try:
        res = await provider.generate(req)
        if res.raw_json and isinstance(res.raw_json, dict):
            semantics = res.raw_json
        else:
            cleaned = res.text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            semantics = json.loads(cleaned)

        graph_data = convert_semantics_to_graph_data(semantics)
        return {
            "graph_data": graph_data,
            "semantics": semantics,
            "summary": semantics.get("summary", "Diagrama generado a partir de la imagen"),
            "total_classes": len(semantics.get("classes", [])),
            "total_relationships": len(semantics.get("relationships", [])),
            "model_used": res.model,
        }
    except Exception as exc:
        logger.error(f"[VisionService] Error procesando imagen con LLM: {exc}")
        raise RuntimeError(f"No se pudo procesar la imagen con Gemini Vision: {exc}")
