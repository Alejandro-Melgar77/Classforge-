import re
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute
from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.ollama_client import call_ollama

def generate_fallback_entities(prompt: str) -> UMLCommandResponse:
    # A simple fallback entity extractor
    # Just extracts words that are nouns (simplification: words longer than 3 chars starting with upper case, or just random nouns)
    words = re.findall(r'\b[A-Za-z]{4,}\b', prompt)
    # Simple stop words filter
    stop_words = {"para", "como", "este", "esta", "sistema", "aplicacion", "quiero", "necesito", "crear", "un", "una", "el", "la", "los", "las"}
    entities = [w.capitalize() for w in words if w.lower() not in stop_words]
    # Unique entities
    entities = list(dict.fromkeys(entities))
    
    classes = []
    for ent in entities[:5]: # Limit to 5 classes
        classes.append(UMLClassCommand(
            name=ent,
            attributes=[
                UMLAttribute(name="id", type="int"),
                UMLAttribute(name="nombre", type="String")
            ]
        ))
        
    return UMLCommandResponse(
        action="generate_system",
        classes=classes,
        explanation="Generado vía fallback de extracción de entidades (Ollama no disponible).",
        source="nlu_heuristic"
    )

async def process_prompt(prompt: str, diagram_context: dict = None) -> UMLCommandResponse:
    # 1. Heuristic matching
    heuristic_res = parse_heuristic(prompt)
    if heuristic_res:
        return heuristic_res
        
    # 2. Ollama
    try:
        ollama_res = await call_ollama(prompt, diagram_context)
        return ollama_res
    except Exception as e:
        # 3. Fallback
        return generate_fallback_entities(prompt)
