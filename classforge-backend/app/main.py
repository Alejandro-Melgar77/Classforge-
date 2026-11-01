import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.errors import DomainError
from app.core.middleware import limiter, rate_limit_exceeded_handler, RateLimitExceeded
from app.llm.gemini import set_shared_client

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.teams.router import router as teams_router
from app.modules.projects.router import router as projects_router
from app.modules.folders.router import router as folders_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.diagrams.router import router as diagrams_router
from app.modules.collaboration.router import router as ws_router
from app.modules.ai.router import router as ai_router
from app.modules.codegen.router import router as codegen_router
from app.modules.notifications.router import router as notifications_router
from app.modules.ai_chat.router import router as ai_chat_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown lifecycle events of the FastAPI application."""
    if settings.ENVIRONMENT == "production":
        default_key = "classforge-super-secret-key-for-development-only"
        if not settings.SECRET_KEY or settings.SECRET_KEY == default_key:
            raise RuntimeError("CRITICAL: In production, SECRET_KEY must be configured and cannot be the default value.")
        if not settings.cors_origins_list:
            raise RuntimeError("CRITICAL: In production, CORS_ORIGINS must not be empty.")

    llm_client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS)
    set_shared_client(llm_client)

    await connect_to_mongo()
    from app.ai_team.application.worker import AiWorker
    worker = AiWorker(db_instance.db)
    worker.start()
    app.state.ai_worker = worker
    yield
    await worker.stop()
    await close_mongo_connection()
    await llm_client.aclose()
    set_shared_client(None)


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter

# ── Global Middleware ─────────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Assigns or propagates a unique Request ID for tracing and logging."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled exception [request_id={request_id}]: {exc}", exc_info=True)
        response = JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "code": "INTERNAL_SERVER_ERROR"
            }
        )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Exception Handlers ────────────────────────────────────────────────────────

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Handles all domain errors returning standard {success: false, message, code}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "code": exc.code
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Transforms HTTPExceptions to the standard {success: false, message, code} payload."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "code": code
        },
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors, logs with request_id, and returns safe 500 without leaking details."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception [request_id={request_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Error interno del servidor",
            "code": "INTERNAL_SERVER_ERROR"
        }
    )


# ── CORS Configuration ────────────────────────────────────────────────────────

cors_kwargs = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# Only permit regex origins in development mode (never in production)
if settings.ENVIRONMENT != "production":
    cors_kwargs["allow_origin_regex"] = r"https://(.*\.trycloudflare\.com|.*\.pages\.dev)"

app.add_middleware(CORSMiddleware, **cors_kwargs)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(teams_router, prefix=f"{settings.API_V1_STR}/teams", tags=["teams"])
app.include_router(projects_router, prefix=f"{settings.API_V1_STR}/projects", tags=["projects"])
app.include_router(folders_router, prefix=f"{settings.API_V1_STR}/folders", tags=["folders"])
app.include_router(dashboard_router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(diagrams_router, prefix=f"{settings.API_V1_STR}/diagrams", tags=["diagrams"])
app.include_router(ws_router, prefix=f"{settings.API_V1_STR}/ws", tags=["collaboration"])
app.include_router(ai_router, prefix=f"{settings.API_V1_STR}/ai", tags=["ai"])
app.include_router(codegen_router, prefix=f"{settings.API_V1_STR}/codegen", tags=["codegen"])
app.include_router(notifications_router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(ai_chat_router, prefix=f"{settings.API_V1_STR}/ai-chat", tags=["ai-chat"])


@app.get("/", tags=["health"])
def root() -> Dict[str, str]:
    """Health check endpoint to verify that the API server is operational."""
    return {"message": "ClassForge API Running"}
