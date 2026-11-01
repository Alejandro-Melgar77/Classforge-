"""
Router and mention parsing logic for AI Chat.
Implements the 4-step decision hierarchy for AI role intervention:
1. Explicit ai_role passed by user
2. @mention in content (@arquitecto, @qa, @techlead, @mentor, @dba, @seguridad, @analista)
3. Participative mode enabled -> heuristic trigger matching (selects <= 2 roles without extra LLM call)
4. None -> message is saved without AI call
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.ai_team.domain.roles import ROLES_REGISTRY, RoleDefinition
from app.modules.ai_chat.domain.models import AiProjectState, RoleAutonomyConfig


AI_MENTION_MAP: Dict[str, str] = {
    "arquitecto": "architect",
    "architect": "architect",
    "qa": "qa",
    "calidad": "qa",
    "techlead": "tech_lead",
    "tech_lead": "tech_lead",
    "tech-lead": "tech_lead",
    "mentor": "mentor",
    "tutor": "mentor",
    "dba": "dba",
    "basededatos": "dba",
    "database": "dba",
    "seguridad": "security",
    "security": "security",
    "analista": "analyst",
    "analyst": "analyst",
}


def parse_mentions(
    text: str,
    team_members: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[str], List[str]]:
    """Extracts AI role mentions and teammate mentions from text.
    
    Returns:
        (ai_roles_mentioned, teammate_names_or_ids)
    """
    if not text:
        return [], []

    raw_mentions = re.findall(r"@([a-zA-Z0-9_\-]+)", text.lower())
    ai_roles: List[str] = []
    teammates: List[str] = []

    member_names_map = {}
    if team_members:
        for m in team_members:
            name = (m.get("name") or "").strip().lower()
            if name:
                # Map first name and full name
                first_name = name.split()[0]
                member_names_map[first_name] = str(m.get("_id") or m.get("id", name))
                member_names_map[name.replace(" ", "")] = str(m.get("_id") or m.get("id", name))

    for m in raw_mentions:
        if m in AI_MENTION_MAP:
            role = AI_MENTION_MAP[m]
            if role not in ai_roles:
                ai_roles.append(role)
        elif m in member_names_map:
            member_id = member_names_map[m]
            if member_id not in teammates:
                teammates.append(member_id)
        else:
            # Check if mention matches a known role id directly
            if m in ROLES_REGISTRY and m not in ai_roles:
                ai_roles.append(m)

    return ai_roles, teammates


def route_ai_roles(
    explicit_role: Optional[str],
    content: str,
    project_state: Optional[AiProjectState],
    team_members: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[str], str, List[str]]:
    """Determines which AI roles should respond to a user message.
    
    Order of precedence:
    1. Explicit ai_role
    2. @mención in text
    3. If participative.enabled: router chooses <= 2 enabled roles matching triggers
    4. None (only user message is saved)
    
    Returns:
        (selected_role_ids, trigger_reason, all_mentions)
    """
    ai_mentions, teammate_mentions = parse_mentions(content, team_members)
    all_mentions = [f"@{r}" for r in ai_mentions] + [f"@{t}" for t in teammate_mentions]

    # 1. Explicit role
    if explicit_role and explicit_role in ROLES_REGISTRY:
        return [explicit_role], "explicit", all_mentions

    # 2. @mention in text
    if ai_mentions:
        # Take the first mentioned AI role (or top 2 if multiple)
        return ai_mentions[:2], "mention", all_mentions

    # 3. Participative AI mode
    if project_state and project_state.participative and project_state.participative.enabled:
        # Build map of role configs
        role_configs: Dict[str, RoleAutonomyConfig] = {
            r.role_id: r for r in project_state.roles
        }

        content_lower = content.lower()
        scored_roles: List[Tuple[int, str]] = []

        for role_id, role_def in ROLES_REGISTRY.items():
            cfg = role_configs.get(role_id)
            # Must be enabled and autonomy not 'off'
            if cfg and (not cfg.enabled or cfg.autonomy == "off"):
                continue

            # Calculate trigger hits
            score = 0
            for trigger in role_def.triggers:
                trig_clean = trigger.strip().lower()
                if not trig_clean:
                    continue
                # Simple word/phrase presence check
                if trig_clean in content_lower:
                    score += 1

            if score > 0:
                scored_roles.append((score, role_id))

        if scored_roles:
            # Sort by score descending
            scored_roles.sort(key=lambda x: x[0], reverse=True)
            # Pick up to 2 top roles
            selected = [r_id for _, r_id in scored_roles[:2]]
            return selected, "participative", all_mentions

    # 4. Nothing matched -> No AI response
    return [], "none", all_mentions
