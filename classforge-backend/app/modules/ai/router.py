from fastapi import APIRouter, Depends, HTTPException
import httpx
from datetime import datetime
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.ai.schemas import PromptRequest, UMLCommandResponse, ImagePromptRequest
from app.modules.ai.service import process_prompt
from app.modules.ai.vision_service import generate_diagram_from_image
from app.core.config import settings
import base64

router = APIRouter()

@router.post("/generate", response_model=StandardResponse)
async def generate_uml(request: PromptRequest, current_user = Depends(get_current_user)):
    try:
        result = await process_prompt(
            prompt=request.prompt,
            diagram_context=request.diagram_context,
            api_key=request.api_key,
            model=request.model
        )
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

@router.post("/generate-from-image", response_model=StandardResponse)
async def generate_from_image(request: ImagePromptRequest, current_user = Depends(get_current_user)):
    try:
        raw_b64 = request.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(raw_b64)
        result = await generate_diagram_from_image(
            image_bytes=image_bytes,
            mime_type=request.mime_type or "image/jpeg",
            api_key=request.api_key,
            model=request.model
        )
        return StandardResponse(
            success=True,
            data=result,
            message="Diagrama generado exitosamente a partir de la imagen mediante Gemini Vision"
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            data=None,
            message=f"Error analizando imagen: {str(e)}"
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
