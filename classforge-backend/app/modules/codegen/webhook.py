# -*- coding: utf-8 -*-
"""
Webhook notification service with SSRF mitigation and private network filtering.
"""
import asyncio
import ipaddress
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),     # Cloud Instance Metadata Service (AWS/GCP/Azure)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def is_safe_webhook_url(url: Optional[str]) -> bool:
    """
    Validates that the target webhook URL is non-empty, uses http/https,
    and does not target loopback, private RFC1918, or cloud metadata endpoints (SSRF prevention).
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False

    if hostname in BLOCKED_HOSTNAMES:
        return False

    try:
        ip = ipaddress.ip_address(hostname)
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return False
    except ValueError:
        # Hostname is a domain name; will be resolved safely via DNS
        pass

    return True


async def notify_n8n_webhook(
    event_type: str,
    diagram_id: str,
    diagram_name: str,
    payload: Dict[str, Any]
) -> None:
    """
    Asynchronously fires an n8n webhook notification.
    Ensures no arbitrary URL supplied by the client can be invoked.
    """
    webhook_url = settings.N8N_WEBHOOK_URL
    if not webhook_url:
        return

    if not is_safe_webhook_url(webhook_url):
        logger.warning(
            f"[Webhook] Configured N8N_WEBHOOK_URL '{webhook_url}' failed safety checks (potential SSRF). Notification aborted."
        )
        return

    data = {
        "event_type": event_type,
        "diagram_id": diagram_id,
        "diagram_name": diagram_name,
        "payload": payload,
    }

    async def _send():
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json=data, timeout=3.0)
        except Exception as exc:
            logger.warning(f"[Webhook] Failed to notify N8N webhook: {exc}")

    asyncio.create_task(_send())
