# -*- coding: utf-8 -*-
"""
Plantillas de código para la generación de Backend FastAPI (Python 3.11+)
con Clean Architecture, Pydantic v2, SQLAlchemy Async, soporte para despliegue en Render,
Cloud Bridge hacia ClassForge, soporte para Enums, Herencia y Relaciones (1-N, N-N).
"""

MAIN_PY = """# -*- coding: utf-8 -*-
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import cloud_sync
{router_imports}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("{project_name}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando {project_name}...")
    await init_db()
    logger.info("Base de datos inicializada correctamente.")
    yield
    logger.info("Cerrando {project_name}...")

app = FastAPI(
    title="{project_name} API",
    description="Backend empresarial generado automáticamente por ClassForge. Incluye arquitectura limpia, OpenAPI/Swagger y Cloud Bridge.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de Routers
app.include_router(cloud_sync.router)
{router_includes}

@app.get("/", tags=["Health"])
async def root():
    return {{
        "app": "{project_name} API",
        "status": "online",
        "docs": "/docs",
        "cloud_connected": bool(settings.CLASSFORGE_CLOUD_URL)
    }}

@app.get("/health", tags=["Health"])
async def health_check():
    return {{"status": "healthy"}}
"""

CONFIG_PY = """# -*- coding: utf-8 -*-
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "{project_name}"
    API_V1_STR: str = "/api/v1"
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Base de datos: SQLite local o PostgreSQL en la nube (Render / Supabase)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4200",
        "http://localhost:8080",
        "http://10.0.2.2:8000",
        "*"
    ]
    
    # Enlace a la nube ClassForge
    CLASSFORGE_CLOUD_URL: str = os.getenv("CLASSFORGE_CLOUD_URL", "https://classforge-backend.onrender.com")
    CLASSFORGE_API_KEY: str = os.getenv("CLASSFORGE_API_KEY", "")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )

settings = Settings()
"""

DATABASE_PY = """# -*- coding: utf-8 -*-
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    db_url,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
"""

ENUMS_PY = """# -*- coding: utf-8 -*-
from enum import Enum

{enums_content}
"""

MODEL_PY = """# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, Date, ForeignKey, Table, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
{extra_imports}

{association_tables}
class {class_name}({base_class}):
    __tablename__ = "{table_name}"
{mapper_args}
{id_field}
{fields}
{relationship_fields}
{audit_fields}
"""

SCHEMA_PY = """# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
{extra_imports}

class {class_name}Base(BaseModel):
{base_fields}

class {class_name}Create({base_create_class}):
    pass

class {class_name}Update(BaseModel):
{update_fields}

class {class_name}Response({base_response_class}):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
"""

ROUTER_PY = """# -*- coding: utf-8 -*-
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.{model_file} import {class_name}
from app.schemas.{schema_file} import {class_name}Create, {class_name}Update, {class_name}Response

router = APIRouter(
    prefix="/api/v1/{url_path}",
    tags=["{class_name}s"]
)

@router.get("", response_model=List[{class_name}Response])
async def get_all(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select({class_name}))
    return result.scalars().all()

@router.get("/{{id}}", response_model={class_name}Response)
async def get_by_id(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select({class_name}).where({class_name}.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} con ID {{id}} no encontrado"
        )
    return item

@router.post("", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)
async def create(data: {class_name}Create, db: AsyncSession = Depends(get_db)):
    db_item = {class_name}(**data.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.put("/{{id}}", response_model={class_name}Response)
async def update(id: int, data: {class_name}Update, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select({class_name}).where({class_name}.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} con ID {{id}} no encontrado"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select({class_name}).where({class_name}.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} con ID {{id}} no encontrado"
        )
    await db.delete(item)
    await db.commit()
    return None
"""

CLOUD_SYNC_ROUTER_PY = """# -*- coding: utf-8 -*-
import httpx
from fastapi import APIRouter, HTTPException
from app.config import settings

router = APIRouter(
    prefix="/api/v1/cloud",
    tags=["Cloud Bridge & Voice Assistant"]
)

@router.get("/status")
async def check_cloud_status():
    \"\"\"Verifica la conectividad con el backend central en la nube de ClassForge.\"\"\"
    if not settings.CLASSFORGE_CLOUD_URL:
        return {"connected": False, "message": "CLASSFORGE_CLOUD_URL no configurada"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.CLASSFORGE_CLOUD_URL}/health")
            return {
                "connected": resp.status_code == 200,
                "remote_status": resp.json() if resp.status_code == 200 else None,
                "cloud_url": settings.CLASSFORGE_CLOUD_URL
            }
    except Exception as e:
        return {"connected": False, "error": str(e), "cloud_url": settings.CLASSFORGE_CLOUD_URL}
"""

REQUIREMENTS_TXT = """fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
sqlalchemy>=2.0.28
aiosqlite>=0.20.0
asyncpg>=0.29.0
httpx>=0.27.0
python-dotenv>=1.0.1
"""

DOCKERFILE = """FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    gcc \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

RENDER_YAML = """services:
  - type: web
    name: {project_slug}-backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.8
      - key: DATABASE_URL
        value: sqlite+aiosqlite:///./app.db
"""

RUN_BAT = """@echo off
echo ===================================================
echo Iniciando {project_name} Backend (FastAPI Asincrono)
echo ===================================================

if not exist venv (
    echo Creando entorno virtual Python...
    python -m venv venv
)

call venv\\Scripts\\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

RUN_SH = """#!/bin/bash
echo "==================================================="
echo "Iniciando {project_name} Backend (FastAPI Asincrono)"
echo "==================================================="

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual Python..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

FASTAPI_README_MD = """# {project_name} - Backend FastAPI Asíncrono

Backend RESTful empresarial de alto rendimiento generado automáticamente por **ClassForge**.
Implementado con **FastAPI**, **SQLAlchemy 2.0 (Async)**, **Pydantic v2** y arquitectura limpia.

## 🚀 Inicio Rápido

### En Windows:
```cmd
run.bat
```

### En Linux / macOS:
```bash
chmod +x run.sh
./run.sh
```

El servidor iniciará en: **http://localhost:8000**
- **Documentación Swagger UI:** http://localhost:8000/docs
- **Documentación ReDoc:** http://localhost:8000/redoc

## 📦 Endpoints RESTful Generados

{endpoints_list}
"""
