import json
import logging
import re
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings
from app.modules.ai.schemas import (
    UMLCommandResponse,
    UMLClassCommand,
    UMLAttribute,
    UMLMethod,
    UMLRelationCommand
)
from app.modules.ai.heuristic_engine import parse_heuristic

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def build_uml_system_instruction() -> str:
    return """Eres un Arquitecto de Software Principal y Especialista de Nivel Experto en Modelado Formal UML 2.5+.
Tu tarea es interpretar solicitudes en lenguaje natural (español o inglés) y generar diagramas de clases UML completos, profesionales, coherentes y exhaustivos.

DEBES PRODUCIR ÚNICAMENTE UN OBJETO JSON VÁLIDO (sin bloques de código markdown, sin ```json, sin texto adicional) con la siguiente estructura exacta:

{
  "action": "generate_system",
  "classes": [
    {
      "name": "NombreClaseEnPascalCase",
      "stereotype": null, // o "abstract" | "interface" | "enum" si aplica
      "attributes": [
        {
          "name": "nombreAtributoEnCamelCase",
          "type": "Long", // Long, String, Integer, Double, BigDecimal, Boolean, LocalDate, Date, etc.
          "visibility": "+" // "+" (público), "-" (privado), "#" (protegido), "~" (paquete)
        }
      ],
      "methods": [
        {
          "name": "nombreMetodo",
          "params": "param1: Tipo, param2: Tipo",
          "return_type": "TipoRetorno", // void, Long, Boolean, String, List<Tipo>, etc.
          "visibility": "+"
        }
      ]
    }
  ],
  "relations": [
    {
      "source": "ClaseOrigen",
      "target": "ClaseDestino",
      "type": "association", // "association" | "inheritance" | "composition" | "aggregation" | "dependency" | "realization"
      "sourceMultiplicity": "1", // "1", "0..1", "1..*", "*", "0..*", "1..1", etc.
      "targetMultiplicity": "1..*", // cardinalidad en el extremo destino
      "label": "verboOAccion" // e.g. "realiza", "contiene", "pertenece a", "hereda de"
    }
  ],
  "deleted_elements": [],
  "explanation": "Resumen claro y conciso en español de la arquitectura y entidades generadas."
}

REGLAS ARQUITECTÓNICAS CRÍTICAS:
1. DETECCIÓN COMPLETA DE ENTIDADES: Detecta todas las clases principales, clases asociativas, catálogos y entidades derivadas necesarias para que el sistema funcione de forma realista.
2. ATRIBUTOS REALISTAS: Cada clase debe incluir su clave primaria (ej: id: Long) y los atributos esenciales del dominio con tipos Java/UML estándar precisos y visibilidad (por defecto '+' o '-').
3. MÉTODOS OPERACIONALES: Incluye operaciones de negocio coherentes (ej: registrar, calcularTotal, cambiarEstado, validar).
4. RELACIONES Y CARDINALIDADES EXACTAS:
   - "inheritance": Generalización o subtipo (ej: CuentaAhorro hereda de CuentaBancaria, Administrador hereda de Usuario). En herencia las multiplicidades pueden ser vacías.
   - "composition": Relación de ciclo de vida fuerte donde la parte no existe sin el todo (ej: Pedido 1 a 1..* DetallePedido, Factura 1 a 1..* ItemFactura).
   - "aggregation": Relación todo-parte débil (ej: Departamento 1 a 1..* Empleado, Curso 1 a 0..* Estudiante).
   - "association": Conexión directa estándar entre entidades con multiplicidades explícitas (ej: Cliente 1 realiza 0..* Pedidos).
   - "dependency": Uso temporal o llamada a servicio.
   - "realization": Implementación de interfaz.
5. CONEXIONES VÁLIDAS: 'source' y 'target' en cada relación DEBEN coincidir exactamente con los nombres de las clases definidas en el array 'classes'.
"""

def sanitize_json_string(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r'^```(?:json)?\s*', '', clean)
        clean = re.sub(r'\s*```$', '', clean)
    return clean.strip()

def parse_gemini_json_to_command(data: Dict[str, Any]) -> UMLCommandResponse:
    action = data.get("action", "generate_system")
    raw_classes = data.get("classes", [])
    raw_relations = data.get("relations", [])
    raw_deleted = data.get("deleted_elements", [])
    explanation = data.get("explanation", "Diagrama generado exitosamente con IA Gemini.")

    classes: List[UMLClassCommand] = []
    for cls in raw_classes:
        name = str(cls.get("name", "Clase")).strip()
        name = re.sub(r'[^a-zA-Z0-9_]', '', name) or "Clase"
        
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
                
        classes.append(UMLClassCommand(
            name=name,
            attributes=attrs,
            methods=methods,
            stereotype=cls.get("stereotype") or None
        ))

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
        
        relations.append(UMLRelationCommand(
            source=src,
            target=tgt,
            type=rel_type,
            label=label,
            source_multiplicity=str(src_mult) if src_mult else None,
            target_multiplicity=str(tgt_mult) if tgt_mult else None
        ))

    return UMLCommandResponse(
        action=action,
        classes=classes,
        relations=relations,
        deleted_elements=raw_deleted,
        explanation=explanation,
        source="gemini_ai"
    )

async def generate_uml_with_gemini(
    prompt: str,
    diagram_context: Optional[dict] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Optional[UMLCommandResponse]:
    """
    Sends the user prompt and optional diagram context to Google Gemini API
    and returns a structured UMLCommandResponse.
    Uses candidate model fallback (gemini-3.7-flash -> gemini-3.8-flash -> gemini-3.5-flash -> gemini-flash-latest).
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        logger.warning("[GeminiService] GEMINI_API_KEY no configurada. Saltando a heurística.")
        return None

    target_model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.7-flash") or "gemini-3.7-flash"
    
    # Priority candidate list with modern models
    candidate_models = [target_model]
    defaults = [
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-2.5-pro",
        "gemini-pro-latest"
    ]
    for d in defaults:
        if d not in candidate_models:
            candidate_models.append(d)

    # Build prompt context
    context_str = ""
    if diagram_context and isinstance(diagram_context, dict):
        existing_nodes = diagram_context.get("nodes") or diagram_context.get("classes") or []
        if existing_nodes:
            context_str = f"\n\nCONTEXTO DEL DIAGRAMA ACTUAL EN EL LIENZO:\nClases existentes: {json.dumps(existing_nodes, ensure_ascii=False)}"

    full_user_content = f"SOLICITUD DEL USUARIO:\n{prompt}{context_str}\n\nGenera el diagrama UML estructurado en JSON respetando todas las reglas."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": build_uml_system_instruction()},
                    {"text": full_user_content}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    last_error = None
    for candidate in candidate_models:
        url = f"{GEMINI_API_BASE}/{candidate}:generateContent?key={key}"
        try:
            logger.info(f"[GeminiService] Invocando modelo {candidate}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    res_json = res.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "")
                            clean_json = sanitize_json_string(raw_text)
                            parsed_dict = json.loads(clean_json)
                            cmd_response = parse_gemini_json_to_command(parsed_dict)
                            logger.info(f"[GeminiService] Éxito con {candidate}: {len(cmd_response.classes)} clases, {len(cmd_response.relations)} relaciones.")
                            return cmd_response
                else:
                    logger.warning(f"[GeminiService] Modelo {candidate} retornó código HTTP {res.status_code}: {res.text[:150]}")
                    last_error = f"HTTP {res.status_code}"
        except Exception as e:
            logger.warning(f"[GeminiService] Excepción llamando a {candidate}: {e}")
            last_error = str(e)

    logger.warning(f"[GeminiService] Todos los modelos Gemini fallaron ({last_error}). Aplicando fallback heurístico.")
    return None
