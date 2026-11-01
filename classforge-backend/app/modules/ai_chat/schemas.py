"""Pydantic schemas for the AI Chat module (P4 Scalable Team Chat)."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from app.ai_team.domain.roles import RoleSkin
from app.ai_team.application.prompt_builder import AiTeamResponse, ProposalItem


ROLE_PATTERN = "^(architect|qa|tech_lead|mentor|dba|security|analyst)$"


# ── Message ────────────────────────────────────────────────────────────────────

class AiMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Optional[str] = None
    thread: Literal["personal", "project"] = "personal"
    owner_id: Optional[str] = None           # user_id (personal thread only)
    author_type: Literal["user", "ai"] = "user"
    author_id: Optional[str] = None          # ObjectId as string; None for AI
    author_name: str = "Usuario"
    author_role_label: str = "dev"           # "dev" | "scrum_master" | "admin" | "architect_ai" etc.
    ai_role: Optional[str] = None            # "architect" | "qa" | "tech_lead" | "mentor" | "dba" etc.
    content: str = ""
    content_format: Literal["markdown"] = "markdown"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    visible_to_all: bool = True
    diagram_snapshot: Optional[dict] = None  # Snapshot of graph_data when message was sent
    has_diagram_changes: bool = False        # True if AI proposes UML changes
    proposals: List[ProposalItem] = Field(default_factory=list)
    proposal_state: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    mentions: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None
    client_id: Optional[str] = None
    trigger: Optional[str] = None
    status: Literal["ok", "pending", "error"] = "ok"
    error_code: Optional[str] = None
    model: Optional[str] = None
    questions: Optional[List[str]] = None
    needs_context: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def sync_timestamps(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "timestamp" in data and not data.get("created_at"):
                data["created_at"] = data["timestamp"]
            elif "created_at" in data and not data.get("timestamp"):
                data["timestamp"] = data["created_at"]
        return data


class AiMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    diagram_id: Optional[str] = None        # Active diagram context
    visible_to_all: bool = True


# ── Chat Request/Response (P4) ──────────────────────────────────────────────────

class AiRoleChatRequest(BaseModel):
    """Request body for sending a message to project AI chat.
    ai_role is optional (P4 router selects role via explicit, @mention, or participative mode).
    Accepts both 'content' and legacy 'message'.
    """
    content: Optional[str] = Field(default=None, max_length=4000)
    message: Optional[str] = Field(default=None, max_length=4000)
    ai_role: Optional[str] = Field(default=None)
    project_id: Optional[str] = None
    diagram_id: Optional[str] = None
    client_id: Optional[str] = None
    reply_to: Optional[str] = None
    api_key: Optional[str] = Field(default=None, repr=False)
    model: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_content_or_message(cls, data: Any) -> Any:
        if isinstance(data, dict):
            txt = (data.get("content") or data.get("message") or "").strip()
            if not txt:
                raise ValueError("Se requiere 'content' o 'message' con texto válido.")
            data["content"] = txt
            data["message"] = txt
        return data


class AiPendingItem(BaseModel):
    role: str
    message_id: str


class AiSendMessageResponse(BaseModel):
    """Immediate response contract: message + ai_pending background tasks."""
    message: Dict[str, Any]
    ai_pending: List[AiPendingItem] = Field(default_factory=list)
    # Backward compatibility fields
    ai_message: Optional[Dict[str, Any]] = None
    has_diagram_changes: bool = False
    diagram_changes_json: Optional[Any] = None
    role_label: Optional[str] = None
    role_emoji: Optional[str] = None
    structured_response: Optional[AiTeamResponse] = None
    proposals: List[ProposalItem] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    needs_context: bool = False


class AiRoleChatResponse(AiSendMessageResponse):
    """Backward-compatible alias for previous response model."""
    pass


class AiHistoryResponse(BaseModel):
    """Contract for group and personal chat history queries."""
    project_id: str
    messages: List[Dict[str, Any]]
    total: int
    next_cursor: Optional[str] = None


# ── Project AI State & Roles ───────────────────────────────────────────────────

class ParticipativeConfigDTO(BaseModel):
    enabled: bool = False
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class RoleAutonomyConfigDTO(BaseModel):
    role_id: str
    enabled: bool = True
    autonomy: Literal["off", "suggest", "apply"] = "suggest"


class ProjectDigestDTO(BaseModel):
    text: str = ""
    tokens: int = 0
    covers_until: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AiProjectStateResponse(BaseModel):
    project_id: str
    participative: ParticipativeConfigDTO
    roles: List[RoleAutonomyConfigDTO] = Field(default_factory=list)
    digest: ProjectDigestDTO
    local_only: bool = False
    updated_at: Optional[datetime] = None


class AiProjectStateUpdateRequest(BaseModel):
    participative: Optional[Dict[str, Any]] = None
    roles: Optional[List[Dict[str, Any]]] = None
    local_only: Optional[bool] = None


class ProposalStateUpdateRequest(BaseModel):
    status: Literal["applied", "dismissed"]


class AiRoleActivate(BaseModel):
    role_id: str = Field(..., pattern=ROLE_PATTERN)
    active: bool


class AiRoleStatus(BaseModel):
    role_id: str
    label: str
    emoji: str
    description: str
    is_active: bool
    skin: Optional[RoleSkin] = None
    triggers: List[str] = Field(default_factory=list)


# ── Tasks ───────────────────────────────────────────────────────────────────────

class AiTaskCreate(BaseModel):
    ai_role: str = Field(..., pattern=ROLE_PATTERN)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    diagram_id: Optional[str] = None
    assignee_type: Literal["ai_role", "user"] = "ai_role"
    assignee_id: Optional[str] = None
    created_by: Optional[str] = None


class AiTaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    ai_role: Optional[str] = Field(default=None, pattern=ROLE_PATTERN)
    assignee_type: Optional[Literal["ai_role", "user"]] = None
    assignee_id: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "failed", "needs_input", "cancelled"]] = None
    diagram_id: Optional[str] = None


class AiTask(BaseModel):
    id: Optional[str] = None
    project_id: str
    diagram_id: Optional[str] = None
    assigned_by: Optional[str] = None
    created_by: Optional[str] = None
    assignee_type: Literal["ai_role", "user"] = "ai_role"
    assignee_id: Optional[str] = None
    ai_role: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed", "needs_input", "cancelled"] = "pending"
    attempts: int = 0
    result: Optional[str] = None
    result_message_id: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Conversation Legacy ─────────────────────────────────────────────────────────

class AiConversation(BaseModel):
    id: Optional[str] = None
    project_id: str
    messages: list[AiMessage] = []
    active_ai_roles: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AiConversationSummary(BaseModel):
    id: str
    project_id: str
    message_count: int
    active_ai_roles: list[str]
    updated_at: Optional[datetime]


class WsTokenResponse(BaseModel):
    token: str
    expires_at: datetime
