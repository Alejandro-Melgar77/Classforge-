from fastapi import HTTPException, status
from bson import ObjectId
from typing import List, Dict, Any, Optional
from app.modules.teams.repository import TeamRepository
from app.modules.users.repository import UserRepository
from app.modules.teams.schemas import TeamCreate, TeamUpdate

class TeamService:
    def __init__(self, db):
        self.db = db
        self.repo = TeamRepository(db)
        self.user_repo = UserRepository(db)

    async def _enrich_team(self, team: Dict[str, Any]) -> Dict[str, Any]:
        if not team:
            return team
        
        # Enrich Scrum Master Name
        sm_id = team.get("scrum_master_id")
        if sm_id:
            sm = await self.user_repo.get_by_id(str(sm_id))
            if sm:
                team["scrum_master_name"] = sm.get("name") or sm.get("email")
                
        # Enrich Members List with details
        raw_mids = team.get("member_ids", [])
        m_oids = [mid if isinstance(mid, ObjectId) else ObjectId(str(mid)) for mid in raw_mids if ObjectId.is_valid(str(mid))]
        
        members_list = []
        if m_oids:
            users = await self.db["users"].find({"_id": {"$in": m_oids}, "is_deleted": False}).to_list(length=None)
            for u in users:
                members_list.append({
                    "id": str(u["_id"]),
                    "name": u.get("name") or u.get("email", "Usuario"),
                    "email": u.get("email", ""),
                    "role": u.get("role", "dev")
                })
        team["members"] = members_list
        return team

    async def _enrich_teams(self, teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [await self._enrich_team(t) for t in teams]

    async def create_team(self, team_data: TeamCreate, admin_id: str):
        # Validate scrum master exists
        sm = await self.user_repo.get_by_id(team_data.scrum_master_id)
        if not sm or sm.get("is_deleted"):
            raise HTTPException(status_code=400, detail="Scrum master not found")
        
        team = await self.repo.create(team_data.model_dump(), admin_id)
        await self.user_repo.log_audit(admin_id, "TEAM_CREATED", f"Created team {team['_id']}")
        return await self._enrich_team(team)

    async def get_team(self, team_id: str, current_user: dict):
        team = await self.repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Access control
        user_id = str(current_user["_id"])
        role = current_user.get("role")
        if role != "admin":
            if role == "scrum_master" and str(team["scrum_master_id"]) != user_id:
                raise HTTPException(status_code=403, detail="Not your team")
            if role == "dev" and user_id not in [str(m) for m in team.get("member_ids", [])]:
                raise HTTPException(status_code=403, detail="Not a member of this team")
                
        return await self._enrich_team(team)

    async def update_team(self, team_id: str, data: TeamUpdate, admin_id: str):
        team = await self.repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
            
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_dict:
            return team

        if "scrum_master_id" in update_dict:
            sm = await self.user_repo.get_by_id(update_dict["scrum_master_id"])
            if not sm or sm.get("is_deleted"):
                raise HTTPException(status_code=400, detail="Scrum master not found")
                
        await self.repo.update(team_id, update_dict)
        await self.user_repo.log_audit(admin_id, "TEAM_UPDATED", f"Updated team {team_id}")
        updated = await self.repo.get_by_id(team_id)
        return await self._enrich_team(updated)

    async def add_member(self, team_id: str, user_id: str, admin_id: str):
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.get("is_deleted"):
            raise HTTPException(status_code=400, detail="User not found")
            
        success = await self.repo.add_member(team_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
            
        await self.user_repo.log_audit(admin_id, "TEAM_MEMBER_ADDED", f"Added user {user_id} to team {team_id}")
        return True

    async def remove_member(self, team_id: str, user_id: str, admin_id: str):
        success = await self.repo.remove_member(team_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
            
        await self.user_repo.log_audit(admin_id, "TEAM_MEMBER_REMOVED", f"Removed user {user_id} from team {team_id}")
        return True

    async def delete_team(self, team_id: str, admin_id: str):
        success = await self.repo.soft_delete(team_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
            
        await self.user_repo.log_audit(admin_id, "TEAM_DELETED", f"Deleted team {team_id}")
        return True
