import httpx
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def notify_n8n_webhook(event_type: str, diagram_id: str, diagram_name: str, payload: dict):
    if not settings.N8N_WEBHOOK_URL:
        return
    
    data = {
        "event_type": event_type,
        "diagram_id": diagram_id,
        "diagram_name": diagram_name,
        "payload": payload
    }
    
    async def _send():
        try:
            async with httpx.AsyncClient() as client:
                await client.post(settings.N8N_WEBHOOK_URL, json=data, timeout=2.0)
        except Exception as e:
            logger.warning(f"Failed to notify N8N webhook: {str(e)}")
            pass # Never raise errors to the client
            
    asyncio.create_task(_send())
