import re
import logging
from typing import Optional
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute
from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.ollama_client import call_ollama
from app.modules.ai.gemini_service import generate_uml_with_gemini

logger = logging.getLogger(__name__)

def generate_fallback_entities(prompt: str) -> UMLCommandResponse:
    # Deterministic single class extraction without generating random extra entities
    single_match = re.search(
        r'(?:(?:crea|agrega|anade|inserta|genera|nueva?)\w*\s+)?(?:una?\s+)?(?:clase|tabla|entidad|clse)\s+(?:con\s+(?:el\s+)?nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)',
        prompt,
        re.IGNORECASE
    )
    if single_match:
        class_name = single_match.group(1).capitalize()
        # Extract attributes if specified
        attrs_match = re.search(r'(?:con\s+atributos?|con\s+campos?|atributos?)\s+(?:de\s+nombres?|llamados?|:)?\s*(.+)', prompt, re.IGNORECASE)
        attrs = [UMLAttribute(name="id", type="Long", visibility="-")]
        if attrs_match:
            raw = attrs_match.group(1).split('.')[0]
            tokens = re.split(r'[,;\s]+(?:y\s+)?', raw)
            for t in tokens:
                clean_t = re.sub(r'[^a-zA-Z0-9_]', '', t).strip()
                if clean_t and clean_t.lower() not in ['con', 'de', 'y', 'los', 'las', 'que', 'id', 'atributos', 'campos', 'clase', 'tabla']:
                    attrs.append(UMLAttribute(name=clean_t, type="String", visibility="-"))
        return UMLCommandResponse(
            action="create_class",
            classes=[UMLClassCommand(name=class_name, attributes=attrs)],
            relations=[],
            deleted_elements=[],
            explanation=f"Clase '{class_name}' identificada a partir del texto.",
            source="offline_nlu"
        )

    return UMLCommandResponse(
        action="unknown",
        classes=[],
        relations=[],
        deleted_elements=[],
        explanation="No se pudo interpretar el comando con certeza. Prueba con: 'crear clase Producto con atributos precio, stock, codigo'",
        source="offline_nlu"
    )

async def process_prompt(
    prompt: str,
    diagram_context: Optional[dict] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> UMLCommandResponse:
    # 1. Primary Engine: Google Gemini Semantic UML Generator
    try:
        gemini_res = await generate_uml_with_gemini(
            prompt=prompt,
            diagram_context=diagram_context,
            api_key=api_key,
            model=model
        )
        if gemini_res and gemini_res.classes:
            return gemini_res
    except Exception as e:
        logger.warning(f"[AiService] Gemini prompt processing error: {e}")

    # 2. Secondary Engine: Deterministic NLU Heuristic Engine (100% Offline)
    heuristic_res = parse_heuristic(prompt)
    if heuristic_res and heuristic_res.action != "unknown":
        heuristic_res.source = "offline_nlu"
        return heuristic_res
        
    # 3. Tertiary Engine: Local Ollama (if configured and running)
    try:
        ollama_res = await call_ollama(prompt, diagram_context)
        if ollama_res and ollama_res.classes:
            return ollama_res
    except Exception:
        pass

    # 4. Final Fallback: Precise Entity Extractor (never invents spurious classes)
    return generate_fallback_entities(prompt)
