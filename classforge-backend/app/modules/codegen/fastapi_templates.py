# -*- coding: utf-8 -*-
"""
Plantillas de código para la generación de Backend FastAPI (Python 3.11+)
con Clean Architecture, Pydantic v2, SQLAlchemy Async, soporte para despliegue en Render,
Cloud Bridge hacia ClassForge y endpoints de Asistente de Voz.
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
from pydantic_settings import BaseSettings

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

    class Config:
        case_sensitive = True
        env_file = ".env"

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

MODEL_PY = """# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class {class_name}(Base):
    __tablename__ = "{table_name}"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
{fields}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
"""

SCHEMA_PY = """# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class {class_name}Base(BaseModel):
{base_fields}

class {class_name}Create({class_name}Base):
    pass

class {class_name}Update(BaseModel):
{update_fields}

class {class_name}Response({class_name}Base):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
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
    cloud_url = settings.CLASSFORGE_CLOUD_URL
    if not cloud_url:
        return {"status": "disconnected", "message": "CLASSFORGE_CLOUD_URL no configurada"}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{cloud_url}/health")
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "cloud_url": cloud_url,
                    "response": resp.json()
                }
            return {
                "status": "degraded",
                "cloud_url": cloud_url,
                "status_code": resp.status_code
            }
    except Exception as e:
        return {
            "status": "offline_fallback",
            "cloud_url": cloud_url,
            "error": str(e),
            "mode": "Operando de forma local autónoma"
        }

@router.post("/voice-relay")
async def relay_voice_command(payload: dict):
    \"\"\"Reenvía un comando de voz recibido desde la App Móvil/Web hacia el backend central FastAPI para procesamiento NLU con Gemini.\"\"\"
    cloud_url = settings.CLASSFORGE_CLOUD_URL
    if not cloud_url:
        raise HTTPException(status_code=503, detail="Cloud Bridge no disponible")
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{cloud_url}/api/v1/ai/generate",
                json=payload,
                headers={"Authorization": f"Bearer {settings.CLASSFORGE_API_KEY}"}
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error comunicando con el servicio de IA en la nube: {str(e)}"
        )
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
    PYTHONUNBUFFERED=1 \\
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
"""

RENDER_YAML = """services:
  - type: web
    name: {project_slug}-fastapi
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.8
      - key: DATABASE_URL
        value: sqlite+aiosqlite:///./app.db
      - key: CLASSFORGE_CLOUD_URL
        value: https://classforge-backend.onrender.com
"""

FASTAPI_README_MD = """# {project_name} - FastAPI Backend

Backend RESTful asíncrono de alto rendimiento generado automáticamente por **ClassForge**.

---

## 🚀 Inicio Rápido Local

### 1. Requisitos
- Python 3.10 o superior
- Pip y Entorno Virtual

### 2. Ejecutar con 1 Clic
- **Windows:** Ejecuta el archivo `run.bat`
- **Linux/Mac:** Ejecuta `./run.sh`

### 3. Ejecución Manual por Terminal
```bash
# Crear y activar entorno virtual
python -m venv venv
# Windows:
.\\venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor en modo desarrollo
uvicorn app.main:app --reload --port 8000
```

---

## 📖 Documentación Interactiva (Swagger / OpenAPI)
Una vez iniciado, abre en tu navegador:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🌐 Endpoints REST Generados
{endpoints_list}

---

## ☁️ Despliegue en 1 Clic en Render
Este repositorio incluye `render.yaml` y `Dockerfile` listos para desplegar:
1. Sube este proyecto a tu repositorio de GitHub.
2. En [Render.com](https://render.com), haz clic en **New +** ➔ **Blueprint**.
3. Selecciona tu repositorio y Render configurará el servicio automáticamente.
"""

RUN_BAT = """@echo off
echo ========================================================
echo Iniciando {project_name} FastAPI Backend...
echo ========================================================

if not exist venv (
    echo Creando entorno virtual Python...
    python -m venv venv
)

call venv\\Scripts\\activate

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Servidor iniciando en: http://localhost:8000/docs
echo Presiona Ctrl+C para detener.
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
"""

RUN_SH = """#!/usr/bin/env bash
echo "Iniciando {project_name} FastAPI Backend..."

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "Servidor disponible en: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
