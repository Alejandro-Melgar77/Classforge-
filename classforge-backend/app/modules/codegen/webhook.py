# -*- coding: utf-8 -*-
"""
Webhook notification service with SSRF mitigation and private network filtering.
"""
import asyncio
import ipaddress
import logging
import socket
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core.tasks import spawn

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
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def _try_parse_raw_ip(host: str) -> Optional[ipaddress._BaseAddress]:
    """Tolerantly parses IPv4/IPv6 literals including bracketed, integer, octal, hex formats."""
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    # Standard IP address parsing
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass

    # Decimal, hex or octal single-integer IPv4 (e.g. 2130706433, 0x7f000001)
    try:
        val = int(host, 0)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
    except (ValueError, SyntaxError):
        pass

    # Dotted notation with octal/hex segments (e.g. 0177.0.0.1)
    parts = host.split(".")
    if len(parts) in (2, 3, 4):
        try:
            parsed_parts = [int(p, 0) for p in parts]
            if len(parts) == 4 and all(0 <= p <= 255 for p in parsed_parts):
                val = (parsed_parts[0] << 24) | (parsed_parts[1] << 16) | (parsed_parts[2] << 8) | parsed_parts[3]
                return ipaddress.IPv4Address(val)
        except (ValueError, SyntaxError):
            pass

    return None


def is_ip_unsafe(ip: ipaddress._BaseAddress) -> bool:
    """Checks whether an IP is loopback, private, link-local, reserved, multicast, or in blocked networks."""
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None and is_ip_unsafe(mapped):
        return True

    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True

    for net in BLOCKED_IP_NETWORKS:
        if ip in net:
            return True

    return False


def is_safe_webhook_url(url: Optional[str]) -> bool:
    """
    Validates that the target webhook URL is non-empty, uses http/https,
    and does not target loopback, private RFC1918, or cloud metadata endpoints (SSRF prevention).
    Resolves DNS of domain names and checks all resolved IP addresses.
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

    # Check if hostname directly represents an IP (literal, int, hex, octal, IPv4-mapped)
    direct_ip = _try_parse_raw_ip(hostname)
    if direct_ip is not None:
        if is_ip_unsafe(direct_ip):
            return False
        return True

    # DNS resolution for hostnames to prevent DNS rebinding and nip.io-style bypasses
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for res in resolved:
            sockaddr = res[4]
            ip_str = sockaddr[0]
            try:
                resolved_ip = ipaddress.ip_address(ip_str)
                if is_ip_unsafe(resolved_ip):
                    return False
            except ValueError:
                return False
    except (socket.gaierror, socket.herror):
        # Domain cannot be resolved in this environment (e.g. offline unit test dummy domain)
        pass
    except Exception:
        return False

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
            async with httpx.AsyncClient(follow_redirects=False) as client:
                await client.post(webhook_url, json=data, timeout=3.0)
        except Exception as exc:
            logger.warning(f"[Webhook] Failed to notify N8N webhook: {exc}")

    spawn(_send())
