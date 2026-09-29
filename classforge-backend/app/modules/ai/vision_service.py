import base64
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def build_vision_system_prompt() -> str:
    return """You are a senior Software Architect and UML specialist.
Analyze the provided image of a UML class diagram (whiteboard photo, sketch, scanned diagram, or digital screenshot).
Carefully detect all classes, interfaces, attributes, types, methods, and relationships.

You MUST output ONLY a valid raw JSON object (NO markdown backticks, NO ```json, NO explanation) matching this exact schema:
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
- "association" (standard arrow or line)
- "inheritance" (generalization / triangle arrow pointing to parent)
- "composition" (solid diamond)
- "aggregation" (hollow diamond)
- "dependency" (dashed arrow)
- "realization" (dashed line with triangle)
"""


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
        class_name = re.sub(r'[^a-zA-Z0-9_]', '', class_name) or f"Class{idx+1}"
        
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
                clean_attrs.append({
                    "name": a.get("name", "attr"),
                    "type": a.get("type", "String"),
                    "visibility": a.get("visibility", "+"),
                    "isNullable": a.get("isNullable", False)
                })
            elif isinstance(a, str):
                clean_attrs.append({
                    "name": a.replace("+", "").replace("-", "").replace("#", "").strip(),
                    "type": "String",
                    "visibility": "+",
                    "isNullable": False
                })

        # Normalize methods
        raw_methods = cls.get("methods", [])
        clean_methods = []
        for m in raw_methods:
            if isinstance(m, dict):
                clean_methods.append({
                    "name": m.get("name", "method"),
                    "returnType": m.get("returnType", "void"),
                    "visibility": m.get("visibility", "+"),
                    "parameters": m.get("parameters", "")
                })
            elif isinstance(m, str):
                clean_methods.append({
                    "name": m.replace("+", "").replace("-", "").replace("#", "").strip(),
                    "returnType": "void",
                    "visibility": "+",
                    "parameters": ""
                })

        node_cell = {
            "id": node_id,
            "shape": "class-node",
            "position": {"x": pos_x, "y": pos_y},
            "size": {"width": node_width, "height": max(node_min_height, 60 + len(clean_attrs) * 20 + len(clean_methods) * 20)},
            "data": {
                "name": class_name,
                "attributes": clean_attrs,
                "methods": clean_methods,
                "isInterface": cls.get("isInterface", False)
            }
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
                    "label": label_text
                }
            }
            cells.append(edge_cell)

    return {"cells": cells}


async def generate_diagram_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends an image of a UML diagram to Google Gemini Vision API and returns ClassForge graph_data.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        raise ValueError("GEMINI_API_KEY no configurada en el backend")

    target_model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
    candidate_models = [target_model]
    for m in ["gemini-3.8-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]:
        if m not in candidate_models:
            candidate_models.append(m)

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": build_vision_system_prompt()},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json"
        }
    }

    last_error = None
    for cand in candidate_models:
        url = f"{GEMINI_API_BASE}/{cand}:generateContent?key={key}"
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    resp_json = response.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        clean_json = raw_text.strip()
                        if clean_json.startswith("```"):
                            clean_json = re.sub(r'^```(?:json)?\s*', '', clean_json)
                            clean_json = re.sub(r'\s*```$', '', clean_json)

                        semantics = json.loads(clean_json)
                        graph_data = convert_semantics_to_graph_data(semantics)
                        return {
                            "graph_data": graph_data,
                            "semantics": semantics,
                            "summary": semantics.get("summary", "Diagrama generado a partir de la imagen"),
                            "total_classes": len(semantics.get("classes", [])),
                            "total_relationships": len(semantics.get("relationships", [])),
                            "model_used": cand
                        }
                else:
                    logger.warning(f"Gemini model {cand} returned status {response.status_code}: {response.text}")
                    last_error = f"Gemini error {response.status_code}: {response.text}"
        except Exception as e:
            logger.warning(f"Error calling Gemini model {cand}: {e}")
            last_error = str(e)

    raise RuntimeError(f"No se pudo procesar la imagen con Gemini Vision: {last_error}")
