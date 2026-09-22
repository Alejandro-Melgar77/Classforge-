from fastapi import APIRouter, Depends, HTTPException
import httpx
from datetime import datetime
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.ai.schemas import PromptRequest, UMLCommandResponse
from app.modules.ai.service import process_prompt
from app.core.config import settings

router = APIRouter()

@router.post("/generate", response_model=StandardResponse)
async def generate_uml(request: PromptRequest, current_user = Depends(get_current_user)):
    try:
        result = await process_prompt(request.prompt, request.diagram_context)
        return StandardResponse(
            success=True,
            data=result.model_dump(),
            message="Prompt procesado exitosamente"
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            data=None,
            message=str(e)
        )

@router.get("/health")
async def ai_health():
    url = f"{settings.OLLAMA_URL}/api/tags"
    available = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                available = True
    except Exception:
        pass
        
    return {
        "ollama_available": available,
        "model": getattr(settings, "OLLAMA_MODEL", "tinyllama")
    }
