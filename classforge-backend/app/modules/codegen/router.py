# -*- coding: utf-8 -*-
"""
Controlador de generación de código (Spring Boot y FastAPI), descarga de ZIPs,
prompts de frontend y webhooks n8n, con autorización estricta require_diagram_access
y mitigación de ataques SSRF y Zip-Slip.
"""
import io
import logging
import re
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from app.core.authz import require_diagram_access
from app.core.dependencies import get_current_user
from app.core.middleware import limiter
from app.modules.auth.schemas import StandardResponse
from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.frontend_prompt_generator import (
    generate_frontend_meta_prompt,
    generate_frontend_meta_prompt_with_gemini,
)
from app.modules.codegen.gemini_generator import generate_backend_with_gemini
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.schemas import CodegenPreviewRequest, FrontendPromptRequest
from app.modules.codegen.webhook import notify_n8n_webhook
from app.modules.codegen.zip_service import create_project_zip

router = APIRouter()


@router.post("/{diagram_id}/preview", response_model=StandardResponse)
@limiter.limit("20/minute")
async def preview_code(
    request: Request,
    diagram_id: str,
    payload: CodegenPreviewRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user = Depends(get_current_user),
    diagram: Dict[str, Any] = Depends(require_diagram_access),
):
    if payload.gemini_api_key:
        logger.warning("[Codegen] Field 'gemini_api_key' in request body is deprecated; use header 'X-Gemini-Key'")
    effective_key = x_gemini_key or payload.gemini_api_key

    graph_data = payload.graph_data or diagram.get("graph_data", {})
    diagram_name = diagram.get("name", f"Diagram-{diagram_id}")

    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for code generation")

    target_backend = payload.target_backend or "spring_boot"
    engine_used = "deterministic"
    summary = None

    if payload.engine == "gemini":
        result = await generate_backend_with_gemini(
            graph_data=graph_data,
            target_backend=target_backend,
            api_key=effective_key,
            model=payload.gemini_model,
        )
        files = result["files"]
        engine_used = result.get("engine_used", "gemini")
        summary = result.get("summary")
    else:
        if target_backend == "fastapi":
            files = generate_fastapi_project(graph_data)
        else:
            files = generate_spring_boot_project(graph_data)

    await notify_n8n_webhook(
        event_type="codegen_preview",
        diagram_id=diagram_id,
        diagram_name=diagram_name,
        payload={"total_files": len(files), "engine": engine_used, "backend": target_backend},
    )

    return StandardResponse(
        success=True,
        message=f"Code preview generated successfully for {target_backend} with {engine_used}",
        data={
            "files": files,
            "total_files": len(files),
            "target_backend": target_backend,
            "engine_used": engine_used,
            "summary": summary,
        },
    )


@router.get("/{diagram_id}/download")
@limiter.limit("20/minute")
async def download_code(
    request: Request,
    diagram_id: str,
    target_backend: Optional[str] = "spring_boot",
    engine: Optional[str] = "deterministic",
    model: Optional[str] = None,
    current_user = Depends(get_current_user),
    diagram: Dict[str, Any] = Depends(require_diagram_access),
):
    graph_data = diagram.get("graph_data", {})
    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for code generation")

    if engine == "gemini":
        result = await generate_backend_with_gemini(
            graph_data=graph_data,
            target_backend=target_backend,
            model=model,
        )
        files = result["files"]
    else:
        if target_backend == "fastapi":
            files = generate_fastapi_project(graph_data)
        else:
            files = generate_spring_boot_project(graph_data)

    zip_bytes = create_project_zip(files)

    raw_name = diagram.get("name", "diagram")
    clean_filename = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_name)
    suffix = "fastapi-backend" if target_backend == "fastapi" else "springboot-backend"

    await notify_n8n_webhook(
        event_type="codegen_download",
        diagram_id=diagram_id,
        diagram_name=raw_name,
        payload={
            "total_files": len(files),
            "zip_size_bytes": len(zip_bytes),
            "engine": engine,
            "backend": target_backend,
        },
    )

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}-{suffix}.zip"'},
    )


@router.post("/{diagram_id}/webhook-test")
@limiter.limit("5/minute")
async def test_webhook(
    request: Request,
    diagram_id: str,
    current_user = Depends(get_current_user),
    diagram: Dict[str, Any] = Depends(require_diagram_access),
):
    raw_name = diagram.get("name", "Test Diagram")
    await notify_n8n_webhook(
        event_type="webhook_test",
        diagram_id=diagram_id,
        diagram_name=raw_name,
        payload={"message": "This is a test notification from ClassForge", "user_id": str(current_user.get("_id"))},
    )
    return {"success": True, "message": "Webhook test initiated in background"}


@router.post("/{diagram_id}/frontend-prompt", response_model=StandardResponse)
@limiter.limit("20/minute")
async def get_frontend_prompt(
    request: Request,
    diagram_id: str,
    payload: FrontendPromptRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user = Depends(get_current_user),
    diagram: Dict[str, Any] = Depends(require_diagram_access),
):
    if payload.gemini_api_key:
        logger.warning("[Codegen] Field 'gemini_api_key' in request body is deprecated; use header 'X-Gemini-Key'")
    effective_key = x_gemini_key or payload.gemini_api_key

    graph_data = payload.graph_data or diagram.get("graph_data", {})
    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for prompt generation")

    if payload.engine == "gemini":
        result = await generate_frontend_meta_prompt_with_gemini(
            graph_data=graph_data,
            target_framework=payload.target_framework,
            theme=payload.theme,
            api_key=effective_key,
            model=payload.gemini_model,
        )
        prompt = result["prompt"]
        char_count = result["character_count"]
        estimated_tokens = result["estimated_tokens"]
        engine_used = result.get("engine_used", "gemini")
    else:
        prompt = generate_frontend_meta_prompt(graph_data, payload.target_framework, payload.theme)
        char_count = len(prompt)
        estimated_tokens = max(1, char_count // 4)
        engine_used = "deterministic"

    return StandardResponse(
        success=True,
        message="Frontend meta-prompt generated successfully",
        data={
            "prompt": prompt,
            "character_count": char_count,
            "estimated_tokens": estimated_tokens,
            "target_framework": payload.target_framework,
            "theme": payload.theme,
            "engine_used": engine_used,
        },
    )
