from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.auth.schemas import StandardResponse
from app.modules.teams.schemas import TeamCreate, TeamUpdate, AddMemberRequest, TeamResponse
from app.modules.teams.service import TeamService

router = APIRouter()

def get_team_service(db = Depends(get_db)):
    return TeamService(db)

@router.post("", response_model=StandardResponse, include_in_schema=False)
@router.post("/", response_model=StandardResponse)
async def create_team(
    data: TeamCreate,
    current_user = Depends(require_role(["admin"])),
    service: TeamService = Depends(get_team_service)
):
    team = await service.create_team(data, str(current_user["_id"]))
    return StandardResponse(success=True, message="Team created successfully", data=TeamResponse.from_mongo(team))

@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_teams(
    current_user = Depends(get_current_user),
    service: TeamService = Depends(get_team_service)
):
    role = current_user.get("role")
    user_id = str(current_user["_id"])
    teams = await service.repo.get_all(role, user_id)
    enriched = await service._enrich_teams(teams)
    return StandardResponse(success=True, message="Teams retrieved", data=[TeamResponse.from_mongo(t).model_dump() for t in enriched])

@router.get("/{team_id}", response_model=StandardResponse)
async def get_team(
    team_id: str,
    current_user = Depends(get_current_user),
    service: TeamService = Depends(get_team_service)
):
    team = await service.get_team(team_id, current_user)
    return StandardResponse(success=True, message="Team retrieved", data=TeamResponse.from_mongo(team))

@router.put("/{team_id}", response_model=StandardResponse)
async def update_team(
    team_id: str,
    data: TeamUpdate,
    current_user = Depends(require_role(["admin"])),
    service: TeamService = Depends(get_team_service)
):
    team = await service.update_team(team_id, data, str(current_user["_id"]))
    return StandardResponse(success=True, message="Team updated successfully", data=TeamResponse.from_mongo(team))

@router.post("/{team_id}/members", response_model=StandardResponse)
async def add_member(
    team_id: str,
    data: AddMemberRequest,
    current_user = Depends(require_role(["admin"])),
    service: TeamService = Depends(get_team_service)
):
    await service.add_member(team_id, data.user_id, str(current_user["_id"]))
    return StandardResponse(success=True, message="Member added successfully", data=None)

@router.delete("/{team_id}/members/{user_id}", response_model=StandardResponse)
async def remove_member(
    team_id: str,
    user_id: str,
    current_user = Depends(require_role(["admin"])),
    service: TeamService = Depends(get_team_service)
):
    await service.remove_member(team_id, user_id, str(current_user["_id"]))
    return StandardResponse(success=True, message="Member removed successfully", data=None)

@router.delete("/{team_id}", response_model=StandardResponse)
async def delete_team(
    team_id: str,
    current_user = Depends(require_role(["admin"])),
    service: TeamService = Depends(get_team_service)
):
    await service.delete_team(team_id, str(current_user["_id"]))
    return StandardResponse(success=True, message="Team deleted successfully", data=None)
