"""
AiChatService: Orchestrates AI chat interactions with role-based personas.
Builds project context, calls Gemini, saves messages, and manages tasks.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.modules.ai_chat.context_builder import ProjectContextBuilder
from app.modules.ai_chat.repository import AiConversationRepository, AiTaskRepository
from app.modules.ai_chat.schemas import (
    AiMessage,
    AiRoleChatRequest,
    AiRoleChatResponse,
    AiTask,
    AiTaskCreate,
)
from app.modules.ai.role_prompts import build_role_system_prompt, get_role_config

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_CHAT_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
]


class AiChatService:
    """Handles AI role-based chat and task execution for ClassForge projects."""

    def __init__(self, db):
        self.db = db
        self.conv_repo = AiConversationRepository(db)
        self.task_repo = AiTaskRepository(db)
        self.context_builder = ProjectContextBuilder()

    async def send_message_with_role(
        self,
        request: AiRoleChatRequest,
        user_id: str,
        username: str,
        user_role: str = "dev",
    ) -> AiRoleChatResponse:
        """Processes a user message with an active AI role persona.
        
        1. Saves the user's message.
        2. Builds full project context.
        3. Calls Gemini with the role's system prompt + context.
        4. Saves and returns the AI response.
        """
        # 1. Save user message
        user_msg = AiMessage(
            author_type="user",
            author_id=user_id,
            author_name=username,
            author_role_label=user_role,
            content=request.message,
            timestamp=datetime.utcnow(),
            visible_to_all=True,
        )
        await self.conv_repo.append_message(request.project_id, user_msg)

        # 2. Build project context
        project_context = await self.context_builder.build(
            self.db,
            request.project_id,
            diagram_id=request.diagram_id,
        )

        # 3. Build system prompt for role
        system_prompt = build_role_system_prompt(request.ai_role, project_context)
        role_config = get_role_config(request.ai_role)

        # 4. Call Gemini
        ai_content = await self._call_gemini_with_role(
            user_message=request.message,
            system_prompt=system_prompt,
            temperature=role_config.get("temperature", 0.3),
        )

        # 5. Detect if response contains diagram changes
        has_changes, changes_json = self._detect_diagram_changes(ai_content)

        # 6. Save AI response
        ai_msg = AiMessage(
            author_type="ai",
            author_name=f"{role_config['emoji']} {role_config['label']}",
            author_role_label=f"{request.ai_role}_ai",
            ai_role=request.ai_role,
            content=ai_content,
            timestamp=datetime.utcnow(),
            visible_to_all=True,
            has_diagram_changes=has_changes,
        )
        await self.conv_repo.append_message(request.project_id, ai_msg)

        return AiRoleChatResponse(
            ai_message=ai_msg,
            has_diagram_changes=has_changes,
            diagram_changes_json=changes_json,
            role_label=role_config["label"],
            role_emoji=role_config["emoji"],
        )

    async def execute_task(self, task_id: str, project_id: str) -> AiTask:
        """Executes a pending AI task and returns the updated task."""
        task_doc = await self.task_repo.get_by_id(task_id)
        if not task_doc:
            raise ValueError(f"Task {task_id} not found")

        await self.task_repo.update_status(task_id, "in_progress")

        try:
            project_context = await self.context_builder.build(
                self.db,
                project_id,
                diagram_id=str(task_doc.get("diagram_id", "")) or None,
            )
            system_prompt = build_role_system_prompt(task_doc["ai_role"], project_context)
            task_prompt = (
                f"TAREA ASIGNADA: {task_doc['title']}\n\n"
                f"DESCRIPCIÓN: {task_doc['description']}\n\n"
                "Por favor, completa esta tarea de forma autónoma y presenta tus resultados."
            )
            result = await self._call_gemini_with_role(task_prompt, system_prompt, temperature=0.2)
            await self.task_repo.update_status(task_id, "completed", result)

            # Post result as AI message in the group chat
            role_config = get_role_config(task_doc["ai_role"])
            task_result_msg = AiMessage(
                author_type="ai",
                author_name=f"{role_config['emoji']} {role_config['label']}",
                author_role_label=f"{task_doc['ai_role']}_ai",
                ai_role=task_doc["ai_role"],
                content=f"✅ **Tarea completada:** {task_doc['title']}\n\n{result}",
                timestamp=datetime.utcnow(),
                visible_to_all=True,
            )
            await self.conv_repo.append_message(project_id, task_result_msg)

        except Exception as e:
            logger.error(f"[AiChatService] Task execution failed: {e}")
            await self.task_repo.update_status(task_id, "failed", str(e))

        updated = await self.task_repo.get_by_id(task_id)
        return self._doc_to_task(updated) if updated else AiTask(
            project_id=project_id, ai_role=task_doc["ai_role"],
            title=task_doc["title"], description=task_doc["description"],
            status="failed",
        )

    async def _call_gemini_with_role(
        self, user_message: str, system_prompt: str, temperature: float = 0.3
    ) -> str:
        """Calls Gemini API with a role system prompt and returns the text response."""
        key = getattr(settings, "GEMINI_API_KEY", None)
        if not key:
            return (
                "⚠️ La IA no está configurada (falta GEMINI_API_KEY). "
                "Configura la clave en el panel de ajustes."
            )

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }

        last_error = "Unknown error"
        for model in GEMINI_CHAT_MODELS:
            url = f"{GEMINI_API_BASE}/{model}:generateContent?key={key}"
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "")
                    else:
                        last_error = f"HTTP {res.status_code}"
                        logger.warning(f"[AiChatService] {model} returned {res.status_code}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[AiChatService] Exception calling {model}: {e}")

        return f"⚠️ No se pudo conectar con la IA en este momento ({last_error}). Intenta de nuevo."

    def _detect_diagram_changes(self, content: str) -> tuple[bool, Optional[dict]]:
        """Tries to detect if the AI response contains UML JSON changes."""
        if not content:
            return False, None
        indicators = ['"action"', '"classes"', '"relations"', "generate_system", "add_class"]
        if not any(ind in content for ind in indicators):
            return False, None
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                parsed = json.loads(json_str)
                if "classes" in parsed or "action" in parsed:
                    return True, parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return False, None

    def _doc_to_task(self, doc: dict) -> AiTask:
        return AiTask(
            id=str(doc.get("_id", "")),
            project_id=str(doc.get("project_id", "")),
            diagram_id=str(doc.get("diagram_id", "")) if doc.get("diagram_id") else None,
            assigned_by=str(doc.get("assigned_by", "")) if doc.get("assigned_by") else None,
            ai_role=doc.get("ai_role", "architect"),
            title=doc.get("title", ""),
            description=doc.get("description", ""),
            status=doc.get("status", "pending"),
            result=doc.get("result"),
            created_at=doc.get("created_at"),
            completed_at=doc.get("completed_at"),
        )
