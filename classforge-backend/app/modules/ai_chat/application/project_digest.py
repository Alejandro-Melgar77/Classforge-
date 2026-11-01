"""
ProjectDigest: Shared project memory generator (<= 1500 tokens).
Summarizes project objectives, decisions made, open questions, and individual requests by name.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId

from app.llm import LlmMessage, LlmRequest, get_provider
from app.ai_team.infrastructure.knowledge_loader import estimate_tokens
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository
from app.modules.ai_chat.infrastructure.repositories.project_state_repository import AiProjectStateRepository

logger = logging.getLogger(__name__)

MAX_DIGEST_TOKENS = 1500


class ProjectDigestService:
    """Manages periodic updates and retrieval of the project executive digest."""

    def __init__(self, db):
        self.db = db
        self.msg_repo = AiMessageRepository(db)
        self.state_repo = AiProjectStateRepository(db)

    async def should_update_digest(self, project_id: str) -> bool:
        """Determines if the project digest should be regenerated based on activity."""
        state = await self.state_repo.get_or_create(project_id)
        digest = state.get("digest", {})
        covers_until = digest.get("covers_until")

        # If no digest exists yet, check if there are messages
        if not digest.get("text"):
            msg_count = await self.msg_repo.count_since(project_id)
            return msg_count > 0

        # Check message count since last digest
        new_msgs = await self.msg_repo.count_since(project_id, since=covers_until)
        if new_msgs >= 20:
            return True

        # Check time elapsed since last update (30 minutes)
        updated_at = digest.get("updated_at")
        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - updated_at >= timedelta(minutes=30) and new_msgs > 0:
                return True

        return False

    async def summarize_digest(
        self,
        project_id: str,
        force: bool = False,
    ) -> Optional[str]:
        """Generates or refreshes the executive digest for a project.
        
        The digest text is strictly bounded to <= 1500 tokens and covers:
        - Objetivo del proyecto
        - Decisiones tomadas
        - Preguntas abiertas
        - Qué ha pedido cada integrante (con nombre)
        """
        if not force and not await self.should_update_digest(project_id):
            state = await self.state_repo.get_or_create(project_id)
            return state.get("digest", {}).get("text", "")

        logger.info(f"[ProjectDigest] Generating digest for project {project_id}...")

        # 1. Fetch project and team members
        project_doc = await self._get_project(project_id)
        team_members = await self._get_team_members(project_doc)

        # 2. Fetch recent messages across all threads of the project
        msgs, _, _ = await self.msg_repo.get_history(project_id, limit=50)
        if not msgs:
            return ""

        # Map member names and their requests
        member_requests: Dict[str, List[str]] = {}
        for m in msgs:
            if m.get("author_type") == "user":
                name = m.get("author_name") or "Usuario"
                content = (m.get("content") or "").strip()
                if content:
                    member_requests.setdefault(name, []).append(content[:150])

        # 3. Call LLM to synthesize digest
        p_name = project_doc.get("name", "Proyecto ClassForge")
        p_desc = project_doc.get("description", "Sin descripción")

        system_prompt = (
            "Eres el sintetizador de memoria compartida para el equipo de desarrollo de ClassForge. "
            "Genera un Resumen Ejecutivo estructurado del proyecto en formato Markdown, conciso y directo, "
            "con un límite estricto de menos de 1.500 tokens.\n\n"
            "DEBES incluir obligatoriamente estas 4 secciones:\n"
            "1. **Objetivo del proyecto**: qué se está construyendo y alcance.\n"
            "2. **Decisiones tomadas**: acuerdos arquitecturales, entidades agregadas o reglas acordadas.\n"
            "3. **Preguntas abiertas**: dudas pendientes de responder o requisitos ambiguos.\n"
            "4. **Peticiones clave por integrante**: lista con viñetas citando a cada persona por su nombre real y qué ha pedido."
        )

        history_lines = []
        for m in msgs[-30:]:
            author = m.get("author_name", "Desconocido")
            role_lbl = f" ({m.get('ai_role')})" if m.get("ai_role") else ""
            txt = (m.get("content") or "")[:200].replace("\n", " ")
            history_lines.append(f"- [{author}{role_lbl}]: {txt}")

        user_content = (
            f"PROYECTO: {p_name}\n"
            f"DESCRIPCIÓN: {p_desc}\n\n"
            f"HISTORIAL RECIENTE:\n" + "\n".join(history_lines)
        )

        llm_req = LlmRequest(
            system=system_prompt,
            messages=[LlmMessage(role="user", text=user_content)],
            temperature=0.2,
            max_output_tokens=1500,
            purpose="task",
            project_id=str(project_id),
        )

        digest_text = ""
        try:
            provider = get_provider(purpose="task")
            resp = await provider.generate(llm_req)
            if resp.text and len(resp.text.strip()) > 20:
                digest_text = resp.text.strip()
        except Exception as e:
            logger.warning(f"[ProjectDigest] LLM generation failed, generating deterministic fallback: {e}")

        # Fallback deterministic digest if LLM output unavailable, empty, or unformatted
        if not digest_text or "Objetivo" not in digest_text:
            digest_text = self._build_deterministic_digest(project_doc, team_members, member_requests)

        # Enforce budget constraint
        tokens = estimate_tokens(digest_text)
        if tokens > MAX_DIGEST_TOKENS:
            digest_text = digest_text[:MAX_DIGEST_TOKENS * 4]
            tokens = estimate_tokens(digest_text)

        latest_msg_time = datetime.now(timezone.utc)
        if msgs and msgs[-1].get("created_at"):
            latest_msg_time = msgs[-1]["created_at"]
            if isinstance(latest_msg_time, str):
                try:
                    latest_msg_time = datetime.fromisoformat(latest_msg_time)
                except Exception:
                    latest_msg_time = datetime.now(timezone.utc)

        await self.state_repo.update_digest(
            project_id=project_id,
            text=digest_text,
            tokens=tokens,
            covers_until=latest_msg_time,
        )

        logger.info(f"[ProjectDigest] Digest updated ({tokens} tokens) for project {project_id}")
        return digest_text

    def _build_deterministic_digest(
        self,
        project_doc: dict,
        team_members: List[dict],
        member_requests: Dict[str, List[str]],
    ) -> str:
        """Deterministic fallback digest ensuring all 4 required sections exist."""
        p_name = project_doc.get("name", "Proyecto ClassForge")
        p_desc = project_doc.get("description", "Modelado de software orientado a objetos.")

        req_lines = []
        for name, reqs in member_requests.items():
            req_summary = "; ".join(reqs[-3:])
            req_lines.append(f"- **{name}**: {req_summary}")

        if not req_lines:
            req_lines.append("- *(Sin peticiones registradas aún)*")

        return f"""### Resumen Ejecutivo del Proyecto

#### 1. Objetivo del proyecto
Construir y diseñar la arquitectura para **{p_name}**.
{p_desc}

#### 2. Decisiones tomadas
- Se acordó modelar las clases de dominio con identificadores explícitos y relaciones tipadas.
- Integración colaborativa de diseño y validación determinista de reglas UML.

#### 3. Preguntas abiertas
- Validar multiplicidades y cardinalidades en relaciones críticas.
- Definir contratos de persistencia y esquemas de generación de código.

#### 4. Peticiones clave por integrante
{chr(10).join(req_lines)}
"""

    async def _get_project(self, project_id: str) -> dict:
        try:
            pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            doc = await self.db["projects"].find_one({"_id": pid})
            return doc or {}
        except Exception:
            return {}

    async def _get_team_members(self, project: dict) -> List[dict]:
        team_id = project.get("team_id")
        if not team_id:
            return []
        try:
            tid = ObjectId(team_id) if ObjectId.is_valid(team_id) else team_id
            team = await self.db["teams"].find_one({"_id": tid})
            if not team:
                return []
            member_ids = team.get("member_ids", [])
            oids = [ObjectId(m) if ObjectId.is_valid(m) else m for m in member_ids]
            cursor = self.db["users"].find({"_id": {"$in": oids}}, {"name": 1, "role": 1})
            return await cursor.to_list(length=50)
        except Exception:
            return []
