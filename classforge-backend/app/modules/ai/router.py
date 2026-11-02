import re
import logging
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
import httpx
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.errors import DomainError, ExternalServiceError
from app.core.middleware import limiter
from app.modules.auth.schemas import StandardResponse
from app.modules.ai.schemas import PromptRequest, UMLCommandResponse, ImagePromptRequest, FeedbackCorrectionRequest
from app.modules.ai.service import process_prompt
from app.modules.ai.vision_service import generate_diagram_from_image
from app.core.config import settings
import base64

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=StandardResponse)
@limiter.limit("15/minute")
async def generate_uml(
    request: Request,
    payload: PromptRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user = Depends(get_current_user),
):
    try:
        if payload.api_key:
            logger.warning("[AI] Field 'api_key' in request body is deprecated; use header 'X-Gemini-Key'")
        effective_key = x_gemini_key or payload.api_key
        result = await process_prompt(
            prompt=payload.prompt,
            diagram_context=payload.diagram_context,
            api_key=effective_key,
            model=payload.model,
            preferred_provider=payload.preferred_provider,
            local_only=payload.local_only or False,
        )
        return StandardResponse(
            success=True,
            data=result.model_dump(),
            message="Prompt procesado exitosamente"
        )
    except DomainError:
        raise
    except Exception as e:
        logger.error(f"[AI] Error generating UML from prompt: {e}")
        raise ExternalServiceError("Error al procesar el prompt con el servicio de IA")

@router.post("/generate-from-image", response_model=StandardResponse)
@limiter.limit("10/minute")
async def generate_from_image(
    request: Request,
    payload: ImagePromptRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user = Depends(get_current_user),
):
    try:
        if payload.api_key:
            logger.warning("[AI] Field 'api_key' in request body is deprecated; use header 'X-Gemini-Key'")
        effective_key = x_gemini_key or payload.api_key
        raw_b64 = payload.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(raw_b64)
        result = await generate_diagram_from_image(
            image_bytes=image_bytes,
            mime_type=payload.mime_type or "image/jpeg",
            api_key=effective_key,
            model=payload.model,
        )
        return StandardResponse(
            success=True,
            data=result,
            message="Diagrama generado exitosamente a partir de la imagen mediante Gemini Vision"
        )
    except DomainError:
        raise
    except Exception as e:
        logger.error(f"[AI] Error generating from image: {e}")
        raise ExternalServiceError("Error al procesar la imagen con el servicio de IA")


_HEALTH_CACHE: Dict[str, Any] = {"at": 0.0, "info": None}
_HEALTH_TTL_SECONDS = 30.0


@router.get("/health")
@limiter.limit("30/minute")
async def ai_health(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Reports provider/routing health.

    Requires authentication and caches the upstream probe: it used to be a public
    endpoint performing a 2-second outbound request on every call.
    """
    from app.llm.registry import get_ollama_provider

    now = time.monotonic()
    cached = _HEALTH_CACHE["info"]
    if cached is None or (now - _HEALTH_CACHE["at"]) > _HEALTH_TTL_SECONDS:
        provider = get_ollama_provider()
        cached = await provider.check_health(timeout_s=2.0)
        _HEALTH_CACHE["at"] = now
        _HEALTH_CACHE["info"] = cached

    health_info = cached
    local_ok = health_info.get("available", False)

    return {
        "provider": settings.LLM_PROVIDER,
        "models": settings.gemini_models_list,
        "has_server_key": settings.has_gemini_server_key,
        "local_available": local_ok,
        "local_model": health_info.get("model", getattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")),
        "local_latency_ms": health_info.get("latency_ms"),
        "routing": settings.routing_config,
        # Backward compatibility aliases
        "ollama_available": local_ok,
        "model": health_info.get("model", getattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")),
    }


@router.post("/feedback", response_model=StandardResponse)
async def submit_ai_feedback(
    payload: FeedbackCorrectionRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    if not payload.allow_feedback:
        raise HTTPException(
            status_code=400,
            detail="El consentimiento explícito para recolección de feedback (allow_feedback=True) es requerido."
        )

    clean_prompt = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', payload.prompt)
    clean_prompt = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', clean_prompt)
    clean_comment = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', payload.comment or "") if payload.comment else None

    from app.modules.ai.service import validate_command_with_linter
    if not validate_command_with_linter(payload.corrected_command):
        raise HTTPException(
            status_code=422,
            detail="El comando corregido contiene infracciones críticas del linter UML P3."
        )

    feedback_doc = {
        "prompt": clean_prompt,
        "corrected_command": payload.corrected_command.model_dump(),
        "project_id": payload.project_id,
        "comment": clean_comment,
        "status": "pending_review",
        "created_at": datetime.now(timezone.utc),
    }

    # A success response is only truthful if the correction was actually stored.
    if db is None:
        raise ExternalServiceError("El almacenamiento de feedback no está disponible")

    try:
        await db["ai_feedback"].insert_one(feedback_doc)
    except Exception as e:
        logger.error(f"[AI] No fue posible guardar feedback en MongoDB: {e}")
        raise ExternalServiceError("No se pudo registrar la corrección para revisión")

    return StandardResponse(
        success=True,
        data={"status": "pending_review"},
        message="Corrección registrada exitosamente para revisión humana."
    )
