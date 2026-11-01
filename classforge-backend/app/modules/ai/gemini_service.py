from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import SecretStr

from app.llm import LlmMessage, LlmRequest, get_provider
from app.modules.ai.schemas import (
    UMLAttribute,
    UMLClassCommand,
    UMLCommandResponse,
    UMLMethod,
    UMLRelationCommand,
)

logger = logging.getLogger(__name__)


def build_uml_system_instruction() -> str:
    return """Eres un Asistente Experto en Generación de Diagramas de Clases UML para ClassForge.
Tu función es interpretar la orden del usuario y construir un diagrama de clases limpio, directo, funcional y fiel a lo solicitado.

DEBES PRODUCIR ÚNICAMENTE UN OBJETO JSON VÁLIDO (sin markdown, sin ```json, sin texto extra) con esta estructura exacta:

{
  "action": "generate_system",
  "classes": [
    {
      "name": "NombreClase",
      "stereotype": null,
      "attributes": [
        {
          "name": "nombreAtributo",
          "type": "Long",
          "visibility": "+"
        }
      ],
      "methods": [
        {
          "name": "nombreMetodo",
          "params": "param: Tipo",
          "return_type": "void",
          "visibility": "+"
        }
      ]
    }
  ],
  "relations": [
    {
      "source": "ClaseOrigen",
      "target": "ClaseDestino",
      "type": "association",
      "sourceMultiplicity": "1",
      "targetMultiplicity": "1..*",
      "label": ""
    }
  ],
  "deleted_elements": [],
  "explanation": "Resumen breve de las clases y relaciones creadas."
}

REGLAS DE FIDELIDAD AL PROMPT:
1. OBEDIENCIA EXACTA: Si el usuario especifica nombres de clases, atributos, cardinalidades y tipos de relación, reprodúcelos con total exactitud sin inventar entidades extra innecesarias.
2. DIRECCIONALIDAD DE RELACIONES UML:
   - "composition": 'source' es la clase TODO/Contenedora (lleva el rombo lleno), 'target' es la clase PARTE.
   - "aggregation": 'source' es la clase TODO/Agrupadora (lleva el rombo hueco), 'target' es el elemento agrupado.
   - "inheritance": 'source' es la subclase (hija), 'target' es la superclase (padre).
   - "association": 'source' se asocia con 'target' con las cardinalidades pedidas.
3. COHERENCIA DE NOMBRES: Los campos 'source' y 'target' de cada relación DEBEN coincidir exactamente con los nombres en 'classes'.
4. REGLA ESTRICTA DE NO INVENTAR: NUNCA añadas clases, atributos, métodos o relaciones que el usuario NO haya mencionado explícitamente.
5. ID AUTOMÁTICO: Toda clase recibe automáticamente un atributo "id" de tipo "Long" con visibilidad "-" como primer atributo, EXCEPTO si el usuario explícitamente dijo "sin id" o ya mencionó un atributo llamado "id".
6. RESPUESTA SOLO JSON: Tu respuesta debe ser EXCLUSIVAMENTE el objeto JSON.
"""


def sanitize_json_string(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


UML_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "classes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "stereotype": {"type": "string"},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "visibility": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                    "methods": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "params": {"type": "string"},
                                "return_type": {"type": "string"},
                                "visibility": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["name", "attributes", "methods"],
            },
        },
        "relations": {
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
                "required": ["source", "target", "type"],
            },
        },
        "deleted_elements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "explanation": {"type": "string"},
    },
    "required": ["action", "classes", "relations"],
}


def parse_gemini_json_to_command(data: Dict[str, Any], source: str = "gemini") -> UMLCommandResponse:
    action = data.get("action", "generate_system")
    raw_classes = data.get("classes", [])
    raw_relations = data.get("relations", [])
    raw_deleted = data.get("deleted_elements", [])
    explanation = data.get("explanation", "Diagrama generado exitosamente con IA Gemini.")

    classes: List[UMLClassCommand] = []
    for cls in raw_classes:
        name = str(cls.get("name", "Clase")).strip()
        name = re.sub(r"[^a-zA-Z0-9_]", "", name) or "Clase"

        # Attributes
        attrs: List[UMLAttribute] = []
        for a in cls.get("attributes", []):
            if isinstance(a, dict):
                a_name = str(a.get("name", "attr")).strip()
                a_type = str(a.get("type", "String")).strip() or "String"
                a_vis = str(a.get("visibility", "+")).strip() or "+"
                attrs.append(UMLAttribute(name=a_name, type=a_type, visibility=a_vis))
            elif isinstance(a, str):
                attrs.append(UMLAttribute(name=a.strip(), type="String", visibility="+"))

        # Methods
        methods: List[UMLMethod] = []
        for m in cls.get("methods", []):
            if isinstance(m, dict):
                m_name = str(m.get("name", "metodo")).strip()
                m_params = str(m.get("params", m.get("parameters", ""))).strip()
                m_return = str(m.get("return_type", m.get("returnType", "void"))).strip() or "void"
                m_vis = str(m.get("visibility", "+")).strip() or "+"
                methods.append(UMLMethod(name=m_name, params=m_params, return_type=m_return, visibility=m_vis))
            elif isinstance(m, str):
                methods.append(UMLMethod(name=m.strip(), params="", return_type="void", visibility="+"))

        classes.append(
            UMLClassCommand(
                name=name,
                attributes=attrs,
                methods=methods,
                stereotype=cls.get("stereotype") or None,
            )
        )

    relations: List[UMLRelationCommand] = []
    for rel in raw_relations:
        src = str(rel.get("source", "")).strip()
        tgt = str(rel.get("target", "")).strip()
        if not src or not tgt:
            continue

        rel_type = str(rel.get("type", "association")).strip().lower()
        if rel_type not in ["association", "inheritance", "composition", "aggregation", "dependency", "realization"]:
            rel_type = "association"

        src_mult = rel.get("sourceMultiplicity") or rel.get("source_multiplicity") or ""
        tgt_mult = rel.get("targetMultiplicity") or rel.get("target_multiplicity") or ""
        label = rel.get("label") or ""

        relations.append(
            UMLRelationCommand(
                source=src,
                target=tgt,
                type=rel_type,
                label=label,
                source_multiplicity=str(src_mult) if src_mult else None,
                target_multiplicity=str(tgt_mult) if tgt_mult else None,
            )
        )

    return UMLCommandResponse(
        action=action,
        classes=classes,
        relations=relations,
        deleted_elements=raw_deleted,
        explanation=explanation,
        source=source,
    )


async def generate_uml_with_gemini(
    prompt: str,
    diagram_context: Optional[dict] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Optional[UMLCommandResponse]:
    """
    Sends the user prompt and optional diagram context to the LLM provider (Gemini / Fake)
    and returns a structured UMLCommandResponse.
    Falls back to None on provider errors so the heuristic engine can proceed.
    """
    provider = get_provider(purpose="task")

    # Build prompt context
    context_str = ""
    if diagram_context and isinstance(diagram_context, dict):
        existing_nodes = diagram_context.get("nodes") or diagram_context.get("classes") or []
        if existing_nodes:
            context_str = f"\n\nCONTEXTO DEL DIAGRAMA ACTUAL EN EL LIENZO:\nClases existentes: {json.dumps(existing_nodes, ensure_ascii=False)}"

    full_user_content = f"SOLICITUD DEL USUARIO:\n{prompt}{context_str}\n\nGenera el diagrama UML estructurado en JSON respetando todas las reglas."
    instruction = system_prompt or build_uml_system_instruction()

    req = LlmRequest(
        system=instruction,
        messages=[LlmMessage(role="user", text=full_user_content)],
        temperature=0.15,
        purpose="task",
        json_schema=UML_JSON_SCHEMA,
        api_key=SecretStr(api_key) if api_key else None,
        model=model,
    )

    try:
        res = await provider.generate(req)
        if res.raw_json and isinstance(res.raw_json, dict):
            parsed_dict = res.raw_json
        else:
            clean = sanitize_json_string(res.text)
            parsed_dict = json.loads(clean)

        cmd_response = parse_gemini_json_to_command(parsed_dict)
        logger.info(f"[GeminiService] Éxito con {res.model}: {len(cmd_response.classes)} clases, {len(cmd_response.relations)} relaciones.")
        return cmd_response
    except Exception as e:
        logger.warning(f"[GeminiService] Error invocando LLM ({e}). Aplicando fallback heurístico.")
        return None
