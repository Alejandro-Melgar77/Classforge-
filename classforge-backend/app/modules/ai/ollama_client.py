import httpx
import json
from app.core.config import settings
from app.modules.ai.schemas import UMLCommandResponse

async def call_ollama(prompt: str, diagram_context: dict = None) -> UMLCommandResponse:
    url = f"{settings.OLLAMA_URL}/api/generate"
    
    system_prompt = (
        "You are a UML assistant. Your task is to process user commands and output "
        "a JSON object conforming strictly to this schema:\n"
        "{\n"
        "  \"action\": \"create_class | add_attribute | add_method | create_relation | delete_element | generate_system\",\n"
        "  \"classes\": [{ \"name\": \"str\", \"attributes\": [{ \"name\": \"str\", \"type\": \"str\", \"visibility\": \"str\" }], \"methods\": [{ \"name\": \"str\", \"params\": \"str\", \"return_type\": \"str\", \"visibility\": \"str\" }], \"stereotype\": \"str\" }],\n"
        "  \"relations\": [{ \"source\": \"str\", \"target\": \"str\", \"type\": \"inheritance | composition | aggregation | association | dependency\", \"label\": \"str\" }],\n"
        "  \"deleted_elements\": [\"str\"],\n"
        "  \"explanation\": \"str\",\n"
        "  \"source\": \"ollama_tinyllama\"\n"
        "}\n"
        "Do not output markdown block quotes, do not include extra text. ONLY raw valid JSON."
    )
    
    if diagram_context:
        user_prompt = f"Context: {json.dumps(diagram_context)}\nUser prompt: {prompt}"
    else:
        user_prompt = f"User prompt: {prompt}"
        
    payload = {
        "model": getattr(settings, "OLLAMA_MODEL", "tinyllama"),
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json"
    }

    try:
        async with httpx.AsyncClient(timeout=4.5) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "{}")
            
            # parse the JSON
            result_dict = json.loads(response_text)
            result_dict["source"] = "ollama_tinyllama"
            return UMLCommandResponse(**result_dict)
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")
