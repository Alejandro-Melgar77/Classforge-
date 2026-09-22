from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.auth.schemas import StandardResponse
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate, ProjectStatusUpdate, ProjectResponse
from app.modules.projects.service import ProjectService
from typing import Optional

router = APIRouter()

def get_project_service(db = Depends(get_db)):
    return ProjectService(db)

@router.post("/", response_model=StandardResponse)
async def create_project(
    data: ProjectCreate,
    current_user = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    project = await service.create_project(data, current_user)
    return StandardResponse(success=True, message="Project created", data=ProjectResponse.from_mongo(project))

@router.get("/", response_model=StandardResponse)
async def list_projects(
    team_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    current_user = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    items, total = await service.list_projects(current_user, team_id, status, type, page, limit, sort_by, order)
    return StandardResponse(success=True, message="Projects retrieved", data={
        "items": [ProjectResponse.from_mongo(i) for i in items],
        "total": total,
        "page": page,
        "limit": limit
    })

@router.get("/{project_id}", response_model=StandardResponse)
async def get_project(
    project_id: str,
    current_user = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    project = await service.get_project(project_id, current_user)
    return StandardResponse(success=True, message="Project retrieved", data=ProjectResponse.from_mongo(project))

@router.put("/{project_id}", response_model=StandardResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    project = await service.update_project(project_id, data, current_user)
    return StandardResponse(success=True, message="Project updated", data=ProjectResponse.from_mongo(project))

@router.put("/{project_id}/status", response_model=StandardResponse)
async def update_status(
    project_id: str,
    data: ProjectStatusUpdate,
    current_user = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service)
):
    project = await service.update_status(project_id, data, current_user)
    return StandardResponse(success=True, message="Status updated", data=ProjectResponse.from_mongo(project))

@router.delete("/{project_id}", response_model=StandardResponse)
async def delete_project(
    project_id: str,
    current_user = Depends(require_role(["admin"])),
    service: ProjectService = Depends(get_project_service)
):
    await service.delete_project(project_id, str(current_user["_id"]))
    return StandardResponse(success=True, message="Project deleted", data=None)
