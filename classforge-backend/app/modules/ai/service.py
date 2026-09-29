import re
import logging
from typing import Optional
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute
from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.ollama_client import call_ollama
from app.modules.ai.gemini_service import generate_uml_with_gemini

logger = logging.getLogger(__name__)

def generate_fallback_entities(prompt: str) -> UMLCommandResponse:
    words = re.findall(r'\b[A-Za-z]{4,}\b', prompt)
    stop_words = {"para", "como", "este", "esta", "sistema", "aplicacion", "quiero", "necesito", "crear", "un", "una", "el", "la", "los", "las"}
    entities = [w.capitalize() for w in words if w.lower() not in stop_words]
    entities = list(dict.fromkeys(entities))
    
    classes = []
    for ent in entities[:6]:
        classes.append(UMLClassCommand(
            name=ent,
            attributes=[
                UMLAttribute(name="id", type="Long", visibility="+"),
                UMLAttribute(name="nombre", type="String", visibility="+")
            ],
            methods=[]
        ))
        
    return UMLCommandResponse(
        action="generate_system",
        classes=classes,
        relations=[],
        deleted_elements=[],
        explanation="Generado vía extracción rápida de entidades.",
        source="offline_nlu"
    )

async def process_prompt(
    prompt: str,
    diagram_context: Optional[dict] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> UMLCommandResponse:
    # 1. Primary Engine: Google Gemini 3.7 Flash Semantic UML Generator
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

    # 4. Final Fallback: Entity Extractor
    return generate_fallback_entities(prompt)

