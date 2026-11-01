"""
Domain models for AI Chat in ClassForge.

Clean Architecture Domain Layer:
- AiMessage: Scalable independent message document with personal/project thread semantics.
- AiProjectState: Shared, audited project state for participative AI, role autonomy, and digest.
- ProposalState: Tracking applied/dismissed state for structured proposals.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.ai_team.application.prompt_builder import ProposalItem

# TODO(decisión): No hay mensajes privados. Según CONTEXTO §8:
# 'Chat' = mi hilo personal con la IA (thread="personal", owner_id=user_id).
# 'Historial' = unión de todos los hilos personales + el hilo 'project' (publicaciones de la IA:
# revisiones, resultados de tareas, resúmenes), visible a todos los miembros del proyecto.
# Si en el futuro se solicitan mensajes o hilos privados entre usuarios, se deberá definir
# una política de aislamiento criptográfico o ACL específica en base de datos.


class ProposalStateRecord(BaseModel):
    """Audit record for a proposal's applied or dismissed status."""
    status: Literal["applied", "dismissed"]
    by: str  # user_id
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AiMessage(BaseModel):
    """Domain model representing a single message in the scalable ai_messages collection."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    thread: Literal["personal", "project"] = "personal"
    owner_id: Optional[str] = None  # user_id (only populated when thread == "personal")
    author_type: Literal["user", "ai"]
    author_id: Optional[str] = None  # user_id or None for AI
    author_name: str  # Snapshot of name at message time
    author_role_label: str = "dev"
    ai_role: Optional[str] = None  # "architect" | "qa" | "tech_lead" | "mentor" | "dba" etc.
    content: str
    content_format: Literal["markdown"] = "markdown"
    proposals: List[ProposalItem] = Field(default_factory=list)
    proposal_state: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    mentions: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None  # message_id being replied to
    client_id: Optional[str] = None  # Client idempotency key
    trigger: Optional[str] = None  # "explicit" | "mention" | "participative" | "task"
    status: Literal["ok", "pending", "error"] = "ok"
    error_code: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class ParticipativeConfig(BaseModel):
    """Configuration for autonomous participative AI intervention."""
    enabled: bool = False
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class RoleAutonomyConfig(BaseModel):
    """Configuration of an individual AI role within a project."""
    role_id: str
    enabled: bool = True
    autonomy: Literal["off", "suggest", "apply"] = "suggest"


class ProjectDigestState(BaseModel):
    """Shared executive summary / project memory (<= 1500 tokens)."""
    text: str = ""
    tokens: int = 0
    covers_until: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AiProjectState(BaseModel):
    """Domain model representing the shared, audited state of a project's AI team."""
    project_id: str
    participative: ParticipativeConfig = Field(default_factory=ParticipativeConfig)
    roles: List[RoleAutonomyConfig] = Field(default_factory=list)
    digest: ProjectDigestState = Field(default_factory=ProjectDigestState)
    updated_at: Optional[datetime] = None
