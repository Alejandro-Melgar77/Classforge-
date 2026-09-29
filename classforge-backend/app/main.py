from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.middleware import limiter, _rate_limit_exceeded_handler, RateLimitExceeded

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown lifecycle events of the FastAPI application."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/", tags=["health"])
def root() -> Dict[str, str]:
    """Health check endpoint to verify that the API server is operational."""
    return {"message": "ClassForge API Running"}

