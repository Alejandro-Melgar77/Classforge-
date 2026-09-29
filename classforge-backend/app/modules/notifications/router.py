from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.notifications.schemas import NotificationResponse, NotificationsListResponse
from app.modules.notifications.service import NotificationService

router = APIRouter()


def get_notification_service(db=Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get("", response_model=StandardResponse)
@router.get("/", response_model=StandardResponse, include_in_schema=False)
async def get_my_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user=Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    user_id = str(current_user["_id"])
    result = await service.list_notifications(user_id, page=page, limit=limit, unread_only=unread_only)
    
    items = [NotificationResponse.from_mongo(doc) for doc in result["items"]]
    data = {
        "items": [i.model_dump() for i in items],
        "total": result["total"],
        "unread_count": result["unread_count"],
        "page": result["page"],
        "limit": result["limit"]
    }
    return StandardResponse(success=True, message="Notificaciones recuperadas", data=data)


@router.put("/{notification_id}/read", response_model=StandardResponse)
async def mark_read(
    notification_id: str,
    current_user=Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    user_id = str(current_user["_id"])
    ok = await service.mark_as_read(notification_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return StandardResponse(success=True, message="Notificación marcada como leída")


@router.put("/read-all", response_model=StandardResponse)
async def mark_all_read(
    current_user=Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    user_id = str(current_user["_id"])
    count = await service.mark_all_as_read(user_id)
    return StandardResponse(success=True, message=f"{count} notificaciones marcadas como leídas", data={"updated": count})


@router.delete("/{notification_id}", response_model=StandardResponse)
async def delete_notification(
    notification_id: str,
    current_user=Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    user_id = str(current_user["_id"])
    ok = await service.delete_notification(notification_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return StandardResponse(success=True, message="Notificación eliminada")
