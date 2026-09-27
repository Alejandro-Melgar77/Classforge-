from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.folders.schemas import FolderCreate, FolderUpdate, FolderResponse
from app.modules.folders.service import FolderService

router = APIRouter()

def get_folder_service(db = Depends(get_db)):
    return FolderService(db)

@router.post("", response_model=StandardResponse, include_in_schema=False)
@router.post("/", response_model=StandardResponse)
async def create_folder(
    data: FolderCreate,
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    folder = await service.create_folder(data, current_user)
    return StandardResponse(success=True, message="Folder created", data=FolderResponse.from_mongo(folder))

@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_folders(
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    folders = await service.get_folders(current_user)
    return StandardResponse(success=True, message="Folders retrieved", data=[FolderResponse.from_mongo(f) for f in folders])

@router.get("/tree", response_model=StandardResponse)
async def get_folder_tree(
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    folders = await service.get_folders(current_user)
    tree = await service.build_tree(folders)
    
    # Simple recursive formatter to reuse from_mongo structure
    def format_node(node):
        formatted = FolderResponse.from_mongo(node).model_dump()
        formatted["children"] = [format_node(c) for c in node["children"]]
        return formatted

    return StandardResponse(success=True, message="Folder tree retrieved", data=[format_node(n) for n in tree])

@router.get("/{folder_id}", response_model=StandardResponse)
async def get_folder(
    folder_id: str,
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    result = await service.get_folder(folder_id)
    data = {
        "folder": FolderResponse.from_mongo(result["folder"]),
        "children": [FolderResponse.from_mongo(c) for c in result["children"]]
    }
    return StandardResponse(success=True, message="Folder retrieved", data=data)

@router.put("/{folder_id}", response_model=StandardResponse)
async def rename_folder(
    folder_id: str,
    data: FolderUpdate,
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    folder = await service.rename_folder(folder_id, data)
    return StandardResponse(success=True, message="Folder renamed", data=FolderResponse.from_mongo(folder))

@router.delete("/{folder_id}", response_model=StandardResponse)
async def delete_folder(
    folder_id: str,
    current_user = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    await service.delete_folder(folder_id)
    return StandardResponse(success=True, message="Folder deleted", data=None)
