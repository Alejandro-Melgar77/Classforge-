"""
Context assembly for AI Chat, prioritizing memory components according to token budget.
Priority order when trimming: digest > diagrama > turnos propios > novedades.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings
from app.llm.models import LlmMessage, LlmRequest
from app.ai_team.domain.roles import RoleDefinition
from app.ai_team.infrastructure.knowledge_loader import estimate_tokens
from app.ai_team.application.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


def format_other_members_activity(messages: List[Dict[str, Any]], max_lines: int = 10) -> str:
    """Formats recent actions/requests by other teammates into a compact bullet list (<= 10 lines)."""
    if not messages:
        return ""

    lines: List[str] = []
    for m in messages:
        if len(lines) >= max_lines:
            break
        author = m.get("author_name") or "Compañero"
        role_label = m.get("author_role_label") or "dev"
        content = (m.get("content") or "").strip().replace("\n", " ")
        if content:
            short_content = content[:120] + "..." if len(content) > 120 else content
            lines.append(f"- **{author}** ({role_label}): \"{short_content}\"")

    if not lines:
        return ""

    return "=== NOVEDADES Y PETICIONES RECIENTES DE OTROS INTEGRANTES ===\n" + "\n".join(lines)


def assemble_chat_request(
    role: RoleDefinition,
    project: Optional[Dict[str, Any]],
    diagram: Optional[Union[Dict[str, Any], Any]],
    user_id: str,
    trigger: str,
    team_members: Optional[List[Dict[str, Any]]] = None,
    digest_text: str = "",
    user_turns: Optional[List[Dict[str, Any]]] = None,
    other_activity: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    recently_touched_ids: Optional[List[str]] = None,
) -> LlmRequest:
    """Assembles an LlmRequest adhering strictly to priority trimming:
    digest > diagrama > turnos propios > novedades.
    """
    total_budget = getattr(settings, "AI_CONTEXT_BUDGET_TOKENS", 8000)

    # 1. Start with full budget parameters
    max_novedades_lines = 10
    user_turn_count = 10
    diagram_budget = 2500

    novedades_str = format_other_members_activity(other_activity or [], max_lines=max_novedades_lines)
    recent_user_turns = (user_turns or [])[-user_turn_count:]

    # Combine digest and novedades into project overview
    combined_digest = digest_text
    if novedades_str:
        combined_digest = f"{digest_text}\n\n{novedades_str}" if digest_text else novedades_str

    # Build test dynamic context to measure token footprint
    static_prefix = PromptBuilder.build_static_prefix(role, team_members=team_members)
    static_tokens = estimate_tokens(static_prefix)
    avail_dynamic = max(1000, total_budget - static_tokens)

    dynamic_context = PromptBuilder.build_dynamic_context(
        project=project,
        diagram=diagram,
        digest=combined_digest,
        recently_touched_ids=recently_touched_ids,
        diagram_budget_tokens=diagram_budget,
    )
    history_turns = PromptBuilder.sanitize_history(recent_user_turns, max_history_turns=user_turn_count)
    history_tokens = sum(estimate_tokens(m.text) for m in history_turns)
    total_estimated = static_tokens + estimate_tokens(dynamic_context) + history_tokens + estimate_tokens(trigger)

    # Priority Trimming: If exceeding total budget:
    # 1st to trim: novedades
    if total_estimated > total_budget and novedades_str:
        logger.debug("[ChatContext] Budget exceeded; trimming 'novedades'")
        combined_digest = digest_text  # Remove novedades completely
        dynamic_context = PromptBuilder.build_dynamic_context(
            project=project,
            diagram=diagram,
            digest=combined_digest,
            recently_touched_ids=recently_touched_ids,
            diagram_budget_tokens=diagram_budget,
        )
        total_estimated = static_tokens + estimate_tokens(dynamic_context) + history_tokens + estimate_tokens(trigger)

    # 2nd to trim: turnos propios
    if total_estimated > total_budget and user_turn_count > 3:
        logger.debug("[ChatContext] Budget still exceeded; trimming 'turnos propios'")
        user_turn_count = 4
        history_turns = PromptBuilder.sanitize_history(recent_user_turns, max_history_turns=user_turn_count)
        history_tokens = sum(estimate_tokens(m.text) for m in history_turns)
        total_estimated = static_tokens + estimate_tokens(dynamic_context) + history_tokens + estimate_tokens(trigger)

    # 3rd to trim: diagrama
    if total_estimated > total_budget:
        logger.debug("[ChatContext] Budget still exceeded; compacting 'diagrama'")
        diagram_budget = 1200
        dynamic_context = PromptBuilder.build_dynamic_context(
            project=project,
            diagram=diagram,
            digest=combined_digest,
            recently_touched_ids=recently_touched_ids,
            diagram_budget_tokens=diagram_budget,
        )

    # Assemble final LlmRequest using PromptBuilder
    req = PromptBuilder.build(
        role=role,
        project=project,
        diagram=diagram,
        digest=combined_digest,
        turns=history_turns,
        trigger=trigger,
        team_members=team_members,
        recently_touched_ids=recently_touched_ids,
        api_key=api_key,
        model=model,
        purpose="chat",
    )
    req.user_id = user_id
    return req
