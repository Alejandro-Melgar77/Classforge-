from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from fastapi import HTTPException

from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import ProjectCreate, ProjectStatusUpdate, ProjectUpdate
from app.modules.teams.repository import TeamRepository
from app.modules.users.repository import UserRepository

class ProjectService:
    def __init__(self, db):
        self.repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)
        self.team_repo = TeamRepository(db)

    async def create_project(self, data: ProjectCreate, current_user: dict):
        user_id = str(current_user["_id"])
        
        if data.type == "team":
            if not data.team_id:
                raise HTTPException(status_code=400, detail="team_id is required for team projects")
            team = await self.team_repo.get_by_id(data.team_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
            if current_user.get("role") not in ["admin", "scrum_master"]:
                raise HTTPException(status_code=403, detail="Only admin or scrum_master can create team projects")
            if current_user.get("role") == "scrum_master" and str(team["scrum_master_id"]) != user_id:
                raise HTTPException(status_code=403, detail="You are not the scrum master of this team")
        
        project = await self.repo.create(data.model_dump(), user_id)
        await self.user_repo.log_audit(user_id, "PROJECT_CREATED", f"Created project {project['_id']}")
        return project

    async def list_projects(self, current_user: dict, team_id: str = None, status: str = None, type: str = None, page: int = 1, limit: int = 20, sort_by: str = "created_at", order: str = "desc"):
        user_id = str(current_user["_id"])
        role = current_user.get("role")
        
        query = {}
        if team_id: query["team_id"] = ObjectId(team_id)
        if status: query["status"] = status
        if type: query["type"] = type

        if role == "dev":
            # Dev sees personal projects and projects of their teams
            user_teams = await self.team_repo.get_all("dev", user_id)
            team_ids = [t["_id"] for t in user_teams]
            query["$or"] = [
                {"team_id": {"$in": team_ids}},
                {"owner_id": ObjectId(user_id)}
            ]
        elif role == "scrum_master":
            user_teams = await self.team_repo.get_all("scrum_master", user_id)
            team_ids = [t["_id"] for t in user_teams]
            query["$or"] = [
                {"team_id": {"$in": team_ids}},
                {"owner_id": ObjectId(user_id)}
            ]
        
        sort_order = -1 if order == "desc" else 1
        items, total = await self.repo.get_list(query, page, limit, sort_by, sort_order)
        return items, total

    async def get_project(self, project_id: str, current_user: dict):
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Access control
        user_id = str(current_user["_id"])
        role = current_user.get("role")
        if role != "admin" and str(project["owner_id"]) != user_id:
            if project["team_id"]:
                team = await self.team_repo.get_by_id(str(project["team_id"]))
                if not team:
                    raise HTTPException(status_code=403, detail="Access denied")
                if role == "scrum_master" and str(team["scrum_master_id"]) != user_id:
                    raise HTTPException(status_code=403, detail="Access denied")
                if role == "dev" and ObjectId(user_id) not in team["member_ids"]:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
                
        return project

    async def update_project(self, project_id: str, data: ProjectUpdate, current_user: dict):
        project = await self.get_project(project_id, current_user)
        
        role = current_user.get("role")
        user_id = str(current_user["_id"])
        if role not in ["admin", "scrum_master"] and str(project["owner_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Permission denied to update project")
            
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        if update_dict:
            await self.repo.update(project_id, update_dict)
            await self.user_repo.log_audit(user_id, "PROJECT_UPDATED", f"Updated project {project_id}")
            
        return await self.repo.get_by_id(project_id)

    async def update_status(self, project_id: str, data: ProjectStatusUpdate, current_user: dict):
        project = await self.get_project(project_id, current_user)
        
        update_dict = {"status": data.status}
        if data.status == "completed":
            update_dict["completed_at"] = datetime.now(timezone.utc)
            
        await self.repo.update(project_id, update_dict)
        await self.user_repo.log_audit(str(current_user["_id"]), "PROJECT_STATUS_UPDATED", f"Updated status of project {project_id} to {data.status}")
        return await self.repo.get_by_id(project_id)

    async def delete_project(self, project_id: str, admin_id: str):
        success = await self.repo.soft_delete(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        await self.user_repo.log_audit(admin_id, "PROJECT_DELETED", f"Deleted project {project_id}")
        return True
