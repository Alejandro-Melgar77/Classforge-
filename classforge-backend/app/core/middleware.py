import ipaddress
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

logger = logging.getLogger(__name__)


def _socket_host(request: Request) -> str:
    """Returns the peer address of the TCP connection, if available."""
    if request.client and request.client.host:
        return request.client.host
    return ""


def _is_trusted_proxy(request: Request) -> bool:
    """True only when the direct peer is one of the configured trusted proxies.

    Proxy headers are attacker-controlled unless the hop that produced them is
    trusted; otherwise every client can spoof X-Forwarded-For and bypass limits.
    """
    configured = settings.trusted_proxies_list
    if not configured:
        return False

    host = _socket_host(request)
    if not host:
        return False

    try:
        peer = ipaddress.ip_address(host)
    except ValueError:
        return False

    for raw_network in configured:
        try:
            if peer in ipaddress.ip_network(raw_network, strict=False):
                return True
        except ValueError:
            logger.warning("TRUSTED_PROXIES contiene un CIDR inválido: %r", raw_network)
    return False


def get_rate_limit_key(request: Request) -> str:
    """Derives a rate limiting key based on authenticated user or verified client IP.
    
    In environments behind reverse proxies (Render, Cloudflare, etc.),
    reads proxy headers (X-Forwarded-For, CF-Connecting-IP, X-Real-IP).
    """
    # 1. Authenticated user ID in state
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # 2. Extract subject from JWT Authorization header if available
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            from jose import jwt
            from app.core.config import settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass

    # 3. Proxy headers — only honoured when the direct peer is a trusted proxy
    if _is_trusted_proxy(request):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return f"ip:{cf_ip.strip()}"

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return f"ip:{real_ip.strip()}"

    socket_host = _socket_host(request)
    if socket_host:
        return f"ip:{socket_host}"

    return "ip:127.0.0.1"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom exception handler for rate-limit breaches returning uniform JSON."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Demasiadas solicitudes. Por favor intente más tarde.",
            "code": "RATE_LIMITED"
        }
    )


limiter = Limiter(key_func=get_rate_limit_key)
