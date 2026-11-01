import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, HTTPException, Request, Header

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.errors import ForbiddenError, NotFoundError, ValidationError, ExternalServiceError
from app.core.middleware import limiter
from app.core.utils import validate_object_id
from app.modules.auth.schemas import StandardResponse
from app.modules.diagrams.schemas import (
    CreateDiagram, UpdateDiagram, SaveGraph, 
    DiagramResponse, DiagramResponseFull, HistoryEntry, WsTokenResponse,
    UpdateParticipants, DiagramParticipantsResponse,
    DiagramFromImageRequest, DiagramAiPromptRequest
)
from app.modules.diagrams.service import DiagramService

logger = logging.getLogger(__name__)
router = APIRouter()

def get_diagram_service(db = Depends(get_db)):
    return DiagramService(db)

@router.post("", response_model=StandardResponse, include_in_schema=False)
@router.post("/", response_model=StandardResponse)
async def create_diagram(
    data: CreateDiagram,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    diagram = await service.create_diagram(data, current_user)
    return StandardResponse(
        success=True,
        message="Diagram created",
        data=DiagramResponse.from_mongo(diagram).model_dump()
    )

@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_diagrams(
    response: Response,
    project_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    if project_id:
        validate_object_id(project_id, "project_id")
    if team_id:
        validate_object_id(team_id, "team_id")
    diagrams, total = await service.list_diagrams(current_user, project_id, team_id, status, page, limit)
    response.headers["X-Total-Count"] = str(total)
    return StandardResponse(
        success=True, 
        message="Diagrams retrieved", 
        data=[DiagramResponse.from_mongo(d).model_dump() for d in diagrams]
    )

@router.get("/{diagram_id}", response_model=StandardResponse)
async def get_diagram(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    return StandardResponse(
        success=True,
        message="Diagram retrieved",
        data=DiagramResponseFull.from_mongo(diagram).model_dump()
    )

@router.put("/{diagram_id}", response_model=StandardResponse)
async def update_diagram(
    diagram_id: str,
    data: UpdateDiagram,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.update_diagram(diagram_id, data, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    return StandardResponse(
        success=True,
        message="Diagram updated",
        data=DiagramResponse.from_mongo(diagram).model_dump()
    )

@router.get("/{diagram_id}/participants", response_model=StandardResponse)
async def get_diagram_participants(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    data = await service.get_diagram_participants(diagram_id, current_user)
    return StandardResponse(
        success=True,
        message="Participants retrieved",
        data=DiagramParticipantsResponse(**data).model_dump()
    )

@router.put("/{diagram_id}/participants", response_model=StandardResponse)
async def update_diagram_participants(
    diagram_id: str,
    data: UpdateParticipants,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    updated = await service.update_diagram_participants(diagram_id, data.member_ids, current_user)
    return StandardResponse(
        success=True,
        message="Participants updated",
        data=DiagramParticipantsResponse(**updated).model_dump()
    )

@router.delete("/{diagram_id}", response_model=StandardResponse)
async def delete_diagram(
    diagram_id: str,
    current_user = Depends(require_role(["admin"])),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    success = await service.delete_diagram(diagram_id, current_user)
    if not success:
        raise NotFoundError("Diagram not found")
    return StandardResponse(success=True, message="Diagram deleted", data=None)

@router.put("/{diagram_id}/graph", response_model=StandardResponse)
async def save_graph(
    diagram_id: str,
    data: SaveGraph,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.save_graph(diagram_id, data, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")

    if diagram.get("project_id"):
        from app.ai_team.application.triggers import TriggersManager
        import asyncio
        triggers = TriggersManager(service.db)
        asyncio.create_task(triggers.on_diagram_changed(
            project_id=str(diagram["project_id"]),
            diagram_id=diagram_id,
            origin="human",
        ))
    return StandardResponse(
        success=True,
        message="Graph saved",
        data=DiagramResponseFull.from_mongo(diagram).model_dump()
    )

@router.get("/{diagram_id}/history", response_model=StandardResponse)
async def list_history(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    history_docs = await service.repository.list_history(diagram_id)
    history = [HistoryEntry.from_mongo(h).model_dump() for h in history_docs]
    return StandardResponse(success=True, message="History retrieved", data=history)

@router.get("/{diagram_id}/history/{version}", response_model=StandardResponse)
async def get_history_version(
    diagram_id: str,
    version: int,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    entry = await service.repository.get_history_entry(diagram_id, version)
    if not entry:
        raise NotFoundError("Version not found")
    await service.get_diagram(diagram_id, current_user)
    from app.modules.diagrams.schemas import HistoryEntryFull
    return StandardResponse(
        success=True,
        message="History version retrieved",
        data=HistoryEntryFull.from_mongo(entry).model_dump()
    )

@router.post("/{diagram_id}/history/{version}/restore", response_model=StandardResponse)
async def restore_history_version(
    diagram_id: str,
    version: int,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    from datetime import datetime, timezone
    from bson import ObjectId
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")

    entry = await service.repository.get_history_entry(diagram_id, version)
    if not entry:
        raise NotFoundError(f"Versión {version} no encontrada en el historial")

    save_data = SaveGraph(
        graph_data=entry.get("graph_data", {}),
        comment=f"Restaurado a versión {version}"
    )
    updated = await service.save_graph(diagram_id, save_data, current_user)

    await service.db["audit_logs"].insert_one({
        "action": "RESTORE_VERSION",
        "diagram_id": ObjectId(diagram_id),
        "user_id": ObjectId(current_user["_id"]),
        "restored_version": version,
        "new_version": updated.get("version") if updated else None,
        "timestamp": datetime.now(timezone.utc)
    })

    return StandardResponse(
        success=True,
        message=f"Diagrama restaurado a versión {version}",
        data=DiagramResponseFull.from_mongo(updated).model_dump()
    )

@router.get("/{diagram_id}/export/xmi")
async def export_xmi(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    xmi_str = await service.generate_xmi(diagram)
    return Response(content=xmi_str, media_type="application/xml")

@router.get("/{diagram_id}/export/json", response_model=StandardResponse)
async def export_json(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    return StandardResponse(success=True, message="JSON exported", data=diagram.get("graph_data", {}))

@router.post("/{diagram_id}/import/xmi", response_model=StandardResponse)
async def import_xmi(
    diagram_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
        
    try:
        content = await file.read()
        xmi_str = content.decode("utf-8")
        graph_data = service.parse_xmi(xmi_str)
        save_data = SaveGraph(graph_data=graph_data, comment="Imported from XMI")
        updated = await service.save_graph(diagram_id, save_data, current_user)
        return StandardResponse(
            success=True,
            message="XMI imported successfully",
            data=DiagramResponseFull.from_mongo(updated).model_dump()
        )
    except (ForbiddenError, NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to parse XMI: {e}")
        raise ValidationError("Error al procesar el archivo XMI")

@router.get("/{diagram_id}/ws-token", response_model=StandardResponse)
async def get_ws_token(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagram not found")
    
    token_data = await service.generate_ws_token(diagram_id, str(current_user["_id"]))
    return StandardResponse(
        success=True, 
        message="Token generated", 
        data=WsTokenResponse(**token_data).model_dump()
    )


@router.post("/{diagram_id}/from-image", response_model=StandardResponse)
@limiter.limit("10/minute")
async def generate_diagram_from_image_endpoint(
    request: Request,
    diagram_id: str,
    request_data: DiagramFromImageRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user=Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service),
    db=Depends(get_db)
):
    import base64
    from app.modules.ai.vision_service import generate_diagram_from_image
    from app.modules.notifications.service import NotificationService

    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagrama no encontrado")

    raw_b64 = request_data.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    image_bytes = base64.b64decode(raw_b64)
    mime_type = request_data.mime_type
    if request_data.api_key:
        logger.warning("[Diagrams] Field 'api_key' in request body is deprecated; use header 'X-Gemini-Key'")
    api_key = x_gemini_key or request_data.api_key
    model = request_data.model

    try:
        vision_result = await generate_diagram_from_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            api_key=api_key,
            model=model
        )
    except Exception as e:
        logger.error(f"Error procesando imagen con IA: {e}")
        raise ExternalServiceError("Error procesando imagen con el servicio de IA")

    save_data = SaveGraph(
        graph_data=vision_result["graph_data"],
        comment=f"Generado con Gemini Vision ({vision_result.get('model_used', 'flash')})"
    )
    updated = await service.save_graph(diagram_id, save_data, current_user)

    # Notificar a los miembros del proyecto
    proj_id = str(diagram.get("project_id", ""))
    if proj_id:
        notif_service = NotificationService(db)
        await notif_service.notify_project_members(
            project_id=proj_id,
            title="📸 Diagrama Digitalizado desde Foto",
            message=f"{current_user.get('name', 'Un usuario')} escaneó una foto y actualizó el diagrama '{diagram.get('name')}'.",
            type="diagram_update",
            diagram_id=diagram_id,
            actor_id=str(current_user["_id"])
        )

    return StandardResponse(
        success=True,
        message="Diagrama generado y guardado exitosamente desde la foto",
        data={
            "diagram": DiagramResponseFull.from_mongo(updated).model_dump(),
            "summary": vision_result.get("summary", ""),
            "total_classes": vision_result.get("total_classes", 0),
            "total_relationships": vision_result.get("total_relationships", 0)
        }
    )


@router.post("/{diagram_id}/ai-prompt", response_model=StandardResponse)
@limiter.limit("15/minute")
async def apply_ai_prompt_to_diagram(
    request: Request,
    diagram_id: str,
    request_data: DiagramAiPromptRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user=Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service),
):
    from app.modules.ai.service import process_prompt

    validate_object_id(diagram_id, "diagram_id")
    diagram = await service.get_diagram(diagram_id, current_user)
    if not diagram:
        raise NotFoundError("Diagrama no encontrado")

    prompt = request_data.prompt
    current_graph = diagram.get("graph_data", {"cells": []})
    if request_data.api_key:
        logger.warning("[Diagrams] Field 'api_key' in request body is deprecated; use header 'X-Gemini-Key'")
    effective_key = x_gemini_key or request_data.api_key

    try:
        ai_res = await process_prompt(
            prompt=prompt,
            diagram_context=current_graph,
            api_key=effective_key,
            model=request_data.model,
        )
    except Exception as e:
        logger.error(f"Error procesando prompt con IA: {e}")
        raise ExternalServiceError("Error procesando prompt con el servicio de IA")

    return StandardResponse(
        success=True,
        message="Prompt procesado exitosamente por la IA",
        data=ai_res.model_dump()
    )
