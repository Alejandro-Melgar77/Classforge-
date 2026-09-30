# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import re

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.codegen.schemas import CodegenPreviewRequest, FrontendPromptRequest
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.gemini_generator import generate_backend_with_gemini
from app.modules.codegen.frontend_prompt_generator import (
    generate_frontend_meta_prompt,
    generate_frontend_meta_prompt_with_gemini
)
from app.modules.codegen.zip_service import create_project_zip
from app.modules.codegen.webhook import notify_n8n_webhook
from app.modules.diagrams.service import DiagramService

router = APIRouter()

def get_diagram_service(db = Depends(get_db)) -> DiagramService:
    return DiagramService(db)

@router.post("/{diagram_id}/preview", response_model=StandardResponse)
async def preview_code(
    diagram_id: str,
    request: CodegenPreviewRequest,
    current_user = Depends(get_current_user),
    diagram_service: DiagramService = Depends(get_diagram_service)
):
    graph_data = request.graph_data
    if not graph_data:
        diagram = await diagram_service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        graph_data = diagram.get("graph_data", {})
        diagram_name = diagram.get("name", f"Diagram-{diagram_id}")
    else:
        diagram_name = f"Preview-{diagram_id}"
        
    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for code generation")

    target_backend = request.target_backend or "spring_boot"
    engine_used = "deterministic"
    summary = None

    if request.engine == "gemini":
        result = await generate_backend_with_gemini(
            graph_data=graph_data,
            target_backend=target_backend,
            api_key=request.gemini_api_key,
            model=request.gemini_model
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
        payload={"total_files": len(files), "engine": engine_used, "backend": target_backend}
    )
    
    return StandardResponse(
        success=True,
        message=f"Code preview generated successfully for {target_backend} with {engine_used}",
        data={
            "files": files,
            "total_files": len(files),
            "target_backend": target_backend,
            "engine_used": engine_used,
            "summary": summary
        }
    )

@router.get("/{diagram_id}/download")
async def download_code(
    diagram_id: str,
    target_backend: Optional[str] = "spring_boot",
    engine: Optional[str] = "deterministic",
    model: Optional[str] = None,
    current_user = Depends(get_current_user),
    diagram_service: DiagramService = Depends(get_diagram_service)
):
    diagram = await diagram_service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
        
    graph_data = diagram.get("graph_data", {})
    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for code generation")
        
    if engine == "gemini":
        result = await generate_backend_with_gemini(
            graph_data=graph_data,
            target_backend=target_backend,
            model=model
        )
        files = result["files"]
    else:
        if target_backend == "fastapi":
            files = generate_fastapi_project(graph_data)
        else:
            files = generate_spring_boot_project(graph_data)
        
    zip_bytes = create_project_zip(files)
    
    raw_name = diagram.get("name", "diagram")
    clean_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    suffix = "fastapi-backend" if target_backend == "fastapi" else "springboot-backend"
    
    await notify_n8n_webhook(
        event_type="codegen_download",
        diagram_id=diagram_id,
        diagram_name=raw_name,
        payload={"total_files": len(files), "zip_size_bytes": len(zip_bytes), "engine": engine, "backend": target_backend}
    )
    
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}-{suffix}.zip"'}
    )


@router.post("/{diagram_id}/webhook-test")
async def test_webhook(
    diagram_id: str,
    current_user = Depends(get_current_user)
):
    await notify_n8n_webhook(
        event_type="webhook_test",
        diagram_id=diagram_id,
        diagram_name="Test Diagram",
        payload={"message": "This is a test notification from ClassForge", "user_id": str(current_user.get("_id"))}
    )
    return {"success": True, "message": "Webhook test initiated in background"}

@router.post("/{diagram_id}/frontend-prompt", response_model=StandardResponse)
async def get_frontend_prompt(
    diagram_id: str,
    request: FrontendPromptRequest,
    current_user = Depends(get_current_user),
    diagram_service: DiagramService = Depends(get_diagram_service)
):
    graph_data = request.graph_data
    if not graph_data:
        diagram = await diagram_service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        graph_data = diagram.get("graph_data", {})
        
    if not graph_data:
        raise HTTPException(status_code=400, detail="No graph data available for prompt generation")
        
    if request.engine == "gemini":
        result = await generate_frontend_meta_prompt_with_gemini(
            graph_data=graph_data,
            target_framework=request.target_framework,
            theme=request.theme,
            api_key=request.gemini_api_key,
            model=request.gemini_model
        )
        prompt = result["prompt"]
        char_count = result["character_count"]
        estimated_tokens = result["estimated_tokens"]
        engine_used = result.get("engine_used", "gemini")
    else:
        prompt = generate_frontend_meta_prompt(graph_data, request.target_framework, request.theme)
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
            "target_framework": request.target_framework,
            "theme": request.theme,
            "engine_used": engine_used
        }
    )
