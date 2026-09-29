from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, HTTPException
from typing import Optional, List
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.auth.schemas import StandardResponse
from app.modules.diagrams.schemas import (
    CreateDiagram, UpdateDiagram, SaveGraph, 
    DiagramResponse, DiagramResponseFull, HistoryEntry, WsTokenResponse,
    UpdateParticipants, DiagramParticipantsResponse
)
from app.modules.diagrams.service import DiagramService
from bson.errors import InvalidId

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
    try:
        diagram = await service.create_diagram(data, current_user)
        return StandardResponse(success=True, message="Diagram created", data=DiagramResponse.from_mongo(diagram).model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_diagrams(
    project_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    diagrams = await service.list_diagrams(current_user, project_id, team_id, status, page, limit)
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
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        return StandardResponse(success=True, message="Diagram retrieved", data=DiagramResponseFull.from_mongo(diagram).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

@router.put("/{diagram_id}", response_model=StandardResponse)
async def update_diagram(
    diagram_id: str,
    data: UpdateDiagram,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.update_diagram(diagram_id, data, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        return StandardResponse(success=True, message="Diagram updated", data=DiagramResponse.from_mongo(diagram).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{diagram_id}/participants", response_model=StandardResponse)
async def get_diagram_participants(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        data = await service.get_diagram_participants(diagram_id, current_user)
        return StandardResponse(success=True, message="Participants retrieved", data=DiagramParticipantsResponse(**data).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{diagram_id}/participants", response_model=StandardResponse)
async def update_diagram_participants(
    diagram_id: str,
    data: UpdateParticipants,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        updated = await service.update_diagram_participants(diagram_id, data.member_ids, current_user)
        return StandardResponse(success=True, message="Participants updated", data=DiagramParticipantsResponse(**updated).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{diagram_id}", response_model=StandardResponse)
async def delete_diagram(
    diagram_id: str,
    current_user = Depends(require_role(["admin"])),
    service: DiagramService = Depends(get_diagram_service)
):
    success = await service.delete_diagram(diagram_id, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return StandardResponse(success=True, message="Diagram deleted", data=None)

@router.put("/{diagram_id}/graph", response_model=StandardResponse)
async def save_graph(
    diagram_id: str,
    data: SaveGraph,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.save_graph(diagram_id, data, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        return StandardResponse(success=True, message="Graph saved", data=DiagramResponseFull.from_mongo(diagram).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{diagram_id}/history", response_model=StandardResponse)
async def list_history(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        history = [HistoryEntry.from_mongo(h).model_dump() for h in diagram.get("history", [])]
        return StandardResponse(success=True, message="History retrieved", data=history)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{diagram_id}/history/{version}", response_model=StandardResponse)
async def get_history_version(
    diagram_id: str,
    version: int,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        entry = await service.repository.get_history_entry(diagram_id, version)
        if not entry:
            raise HTTPException(status_code=404, detail="Version not found")
        # We need to check access to the diagram first
        await service.get_diagram(diagram_id, current_user)
        from app.modules.diagrams.schemas import HistoryEntryFull
        return StandardResponse(success=True, message="History version retrieved", data=HistoryEntryFull.from_mongo(entry).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{diagram_id}/export/xmi")
async def export_xmi(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        xmi_str = await service.generate_xmi(diagram)
        return Response(content=xmi_str, media_type="application/xml")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{diagram_id}/export/json", response_model=StandardResponse)
async def export_json(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        return StandardResponse(success=True, message="JSON exported", data=diagram.get("graph_data", {}))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.post("/{diagram_id}/import/xmi", response_model=StandardResponse)
async def import_xmi(
    diagram_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
            
        content = await file.read()
        xmi_str = content.decode("utf-8")
        graph_data = service.parse_xmi(xmi_str)
        
        save_data = SaveGraph(graph_data=graph_data, comment="Imported from XMI")
        updated = await service.save_graph(diagram_id, save_data, current_user)
        
        return StandardResponse(success=True, message="XMI imported successfully", data=DiagramResponseFull.from_mongo(updated).model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse XMI: {str(e)}")

@router.get("/{diagram_id}/ws-token", response_model=StandardResponse)
async def get_ws_token(
    diagram_id: str,
    current_user = Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service)
):
    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        token_data = await service.generate_ws_token(diagram_id, str(current_user["_id"]))
        return StandardResponse(
            success=True, 
            message="Token generated", 
            data=WsTokenResponse(**token_data).model_dump()
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/{diagram_id}/from-image", response_model=StandardResponse)
async def generate_diagram_from_image_endpoint(
    diagram_id: str,
    request_data: dict,
    current_user=Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service),
    db=Depends(get_db)
):
    import base64
    from app.modules.ai.vision_service import generate_diagram_from_image
    from app.modules.notifications.service import NotificationService

    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagrama no encontrado")

        raw_b64 = request_data.get("image_base64", "")
        if not raw_b64:
            raise HTTPException(status_code=400, detail="image_base64 es requerido")

        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(raw_b64)
        mime_type = request_data.get("mime_type", "image/jpeg")
        api_key = request_data.get("api_key")
        model = request_data.get("model")

        vision_result = await generate_diagram_from_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            api_key=api_key,
            model=model
        )

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
    except PermissionError:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{diagram_id}/ai-prompt", response_model=StandardResponse)
async def apply_ai_prompt_to_diagram(
    diagram_id: str,
    request_data: dict,
    current_user=Depends(get_current_user),
    service: DiagramService = Depends(get_diagram_service),
    db=Depends(get_db)
):
    from app.modules.ai.service import process_prompt
    from app.modules.notifications.service import NotificationService

    try:
        diagram = await service.get_diagram(diagram_id, current_user)
        if not diagram:
            raise HTTPException(status_code=404, detail="Diagrama no encontrado")

        prompt = request_data.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="El prompt es requerido")

        current_graph = diagram.get("graph_data", {"cells": []})
        ai_res = await process_prompt(prompt, current_graph)

        # Aplicar operaciones al grafo
        # ai_res contiene clases, relaciones, etc.
        # Guardar en historial
        save_data = SaveGraph(
            graph_data=current_graph,  # El frontend o la llamada integra los cambios
            comment=f"IA Prompt: {prompt[:40]}"
        )
        
        # Notificar a los miembros del proyecto
        proj_id = str(diagram.get("project_id", ""))
        if proj_id:
            notif_service = NotificationService(db)
            await notif_service.notify_project_members(
                project_id=proj_id,
                title="🎤 Actualización por Voz / IA",
                message=f"{current_user.get('name', 'Un usuario')} ejecutó comando IA: '{prompt}' en '{diagram.get('name')}'.",
                type="ai_update",
                diagram_id=diagram_id,
                actor_id=str(current_user["_id"])
            )

        return StandardResponse(
            success=True,
            message="Prompt procesado exitosamente por la IA",
            data=ai_res.model_dump()
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

