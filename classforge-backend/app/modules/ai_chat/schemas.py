"""Pydantic schemas for the AI Chat module."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ── Message ────────────────────────────────────────────────────────────────────

class AiMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author_type: Literal["user", "ai"]
    author_id: Optional[str] = None          # ObjectId as string; None for AI
    author_name: str
    author_role_label: str = "dev"           # "dev" | "scrum_master" | "admin" | "architect_ai" etc.
    ai_role: Optional[str] = None            # "architect" | "qa" | "tech_lead" | "mentor"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    visible_to_all: bool = True
    diagram_snapshot: Optional[dict] = None  # Snapshot of graph_data when message was sent
    has_diagram_changes: bool = False        # True if AI proposes UML changes


class AiMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    diagram_id: Optional[str] = None        # Active diagram context
    visible_to_all: bool = True


# ── Conversation ────────────────────────────────────────────────────────────────

class AiConversation(BaseModel):
    id: Optional[str] = None
    project_id: str
    messages: list[AiMessage] = []
    active_ai_roles: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AiConversationSummary(BaseModel):
    """Lightweight summary for listing conversations."""
    id: str
    project_id: str
    message_count: int
    active_ai_roles: list[str]
    updated_at: Optional[datetime]


# ── Role Management ─────────────────────────────────────────────────────────────

class AiRoleActivate(BaseModel):
    role_id: str = Field(..., pattern="^(architect|qa|tech_lead|mentor)$")
    active: bool


class AiRoleStatus(BaseModel):
    role_id: str
    label: str
    emoji: str
    description: str
    is_active: bool


# ── Tasks ───────────────────────────────────────────────────────────────────────

class AiTaskCreate(BaseModel):
    ai_role: str = Field(..., pattern="^(architect|qa|tech_lead|mentor)$")
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    diagram_id: Optional[str] = None


class AiTask(BaseModel):
    id: Optional[str] = None
    project_id: str
    diagram_id: Optional[str] = None
    assigned_by: Optional[str] = None
    ai_role: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Chat Request/Response ───────────────────────────────────────────────────────

class AiRoleChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    ai_role: str = Field(..., pattern="^(architect|qa|tech_lead|mentor)$")
    project_id: str
    diagram_id: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class AiRoleChatResponse(BaseModel):
    ai_message: AiMessage
    has_diagram_changes: bool = False
    diagram_changes_json: Optional[Any] = None  # UMLCommandResponse compatible JSON
    role_label: str
    role_emoji: str
