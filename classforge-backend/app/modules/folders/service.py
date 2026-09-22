from fastapi import HTTPException
from app.modules.folders.repository import FolderRepository
from app.modules.teams.repository import TeamRepository
from app.modules.folders.schemas import FolderCreate, FolderUpdate
from bson import ObjectId

class FolderService:
    def __init__(self, db):
        self.repo = FolderRepository(db)
        self.team_repo = TeamRepository(db)

    async def create_folder(self, data: FolderCreate, current_user: dict):
        user_id = str(current_user["_id"])
        
        if data.type == "team" and not data.team_id:
            raise HTTPException(status_code=400, detail="team_id is required for team folders")
        if data.type == "project" and not data.project_id:
            raise HTTPException(status_code=400, detail="project_id is required for project folders")
            
        folder = await self.repo.create(data.model_dump(), user_id)
        return folder

    async def get_folders(self, current_user: dict):
        user_id = str(current_user["_id"])
        role = current_user.get("role")
        
        # Get team ids user belongs to
        user_teams = await self.team_repo.get_all(role, user_id) if role != "admin" else []
        team_ids = [str(t["_id"]) for t in user_teams]
        if role == "admin":
            all_teams = await self.team_repo.collection.find({"is_deleted": False}).to_list(length=1000)
            team_ids = [str(t["_id"]) for t in all_teams]
            
        folders = await self.repo.get_by_owner_and_teams(user_id, team_ids)
        return folders

    async def build_tree(self, folders: list) -> list:
        folder_dict = {str(f["_id"]): {**f, "_id": str(f["_id"]), "children": []} for f in folders}
        tree = []
        for f_id, f in folder_dict.items():
            parent_id = str(f.get("parent_folder_id")) if f.get("parent_folder_id") else None
            if parent_id and parent_id in folder_dict:
                folder_dict[parent_id]["children"].append(f)
            else:
                tree.append(f)
        return tree

    async def get_folder(self, folder_id: str):
        folder = await self.repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        children = await self.repo.get_children(folder_id)
        return {"folder": folder, "children": children}

    async def rename_folder(self, folder_id: str, data: FolderUpdate):
        success = await self.repo.update(folder_id, data.name)
        if not success:
            raise HTTPException(status_code=404, detail="Folder not found")
        return await self.repo.get_by_id(folder_id)

    async def delete_folder(self, folder_id: str):
        success = await self.repo.soft_delete(folder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Folder not found")
        return True
