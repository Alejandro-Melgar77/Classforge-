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
