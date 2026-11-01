"""
Backward-compatibility bridge for AI Chat repositories.
Re-exports new clean repositories while preserving legacy signatures.
"""
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository
from app.modules.ai_chat.infrastructure.repositories.project_state_repository import AiProjectStateRepository
from app.modules.ai_chat.infrastructure.repositories.task_repository import AiTaskRepository


class AiConversationRepository:
    """Legacy adapter delegating to AiMessageRepository and AiProjectStateRepository."""

    def __init__(self, db):
        self.db = db
        self.msg_repo = AiMessageRepository(db)
        self.state_repo = AiProjectStateRepository(db)
        self.col = db["ai_conversations"]

    async def get_by_project(self, project_id: str):
        # Fallback to old collection if needed
        try:
            return await self.col.find_one({"project_id": str(project_id)})
        except Exception:
            return None

    async def append_message(self, project_id: str, message) -> bool:
        try:
            from app.modules.ai_chat.domain.models import AiMessage as DomainAiMessage
            if not isinstance(message, DomainAiMessage):
                domain_msg = DomainAiMessage(
                    project_id=str(project_id),
                    thread="personal" if message.author_type == "user" else "personal",
                    owner_id=message.author_id if message.author_type == "user" else None,
                    author_type=message.author_type,
                    author_id=message.author_id,
                    author_name=message.author_name,
                    author_role_label=message.author_role_label,
                    ai_role=message.ai_role,
                    content=message.content,
                    created_at=getattr(message, "timestamp", None) or getattr(message, "created_at", None),
                    proposals=getattr(message, "proposals", []) or [],
                )
            else:
                domain_msg = message
            await self.msg_repo.create_message(domain_msg)
            return True
        except Exception:
            return False

    async def get_messages_for_user(self, project_id: str, user_id: str, limit: int = 100):
        msgs, _, _ = await self.msg_repo.get_mine_history(project_id, user_id, limit=limit)
        return msgs

    async def get_all_messages(self, project_id: str, limit: int = 200):
        msgs, _, _ = await self.msg_repo.get_history(project_id, limit=limit)
        return msgs

    async def set_active_roles(self, project_id: str, roles: list[str]) -> bool:
        roles_payload = [{"role_id": r, "enabled": True} for r in roles]
        await self.state_repo.update_roles(project_id, roles_payload, user_id="system")
        return True

    async def get_active_roles(self, project_id: str) -> list[str]:
        state = await self.state_repo.get_or_create(project_id)
        return [r["role_id"] for r in state.get("roles", []) if r.get("enabled")]


__all__ = [
    "AiConversationRepository",
    "AiMessageRepository",
    "AiProjectStateRepository",
    "AiTaskRepository",
]
