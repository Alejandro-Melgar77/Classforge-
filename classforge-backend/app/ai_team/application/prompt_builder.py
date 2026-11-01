"""
PromptBuilder: Assembles deterministic, role-specialized prompts with structured output contracts.

Maintains byte-identical static prefixes (role persona + output contract + knowledge base)
to maximize Gemini implicit prompt caching hits (>= 4,096 tokens), and enriches dynamic
context with resolved diagram summaries, deterministic linter findings, and clean conversation turns.
Never leaks raw exception strings (str(e)) into LLM prompts.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from app.core.config import settings
from app.llm.models import LlmMessage, LlmRequest
from app.modules.ai.schemas import UMLCommandResponse
from app.ai_team.domain.diagram_model import Diagram, from_graph_data
from app.ai_team.domain.lint import Finding, lint
from app.ai_team.domain.roles import RoleDefinition, get_role, build_role_persona_prompt
from app.ai_team.application.diagram_summary import summarize_diagram
from app.ai_team.infrastructure.knowledge_loader import knowledge_loader, estimate_tokens
from app.ai_team.infrastructure.retrieval import bm25_retriever

logger = logging.getLogger(__name__)


# ── Structured Output Contract ────────────────────────────────────────────────

class ProposalItem(BaseModel):
    id: str = Field(..., description="Identificador único de la propuesta (ej. 'prop-1')")
    kind: Literal["uml_command", "task", "note"] = Field(
        ..., description="Tipo de propuesta: 'uml_command' (cambio en diagrama), 'task' (tarea a ejecutar) o 'note' (observación técnica)"
    )
    title: str = Field(..., description="Título descriptivo y conciso de la propuesta")
    rationale: str = Field(..., description="Justificación técnica o arquitectural")
    severity: Literal["info", "warn", "critical"] = Field(
        default="info", description="Nivel de impacto o criticidad"
    )
    command: Optional[UMLCommandResponse] = Field(
        default=None, description="Comando UML ejecutable cuando kind == 'uml_command'"
    )
    target_element_ids: List[str] = Field(
        default_factory=list, description="IDs o nombres de elementos afectados"
    )


class AiTeamResponse(BaseModel):
    reply_markdown: str = Field(
        ..., description="Respuesta conversacional en primera persona, concisa, colegial y fundamentada en Markdown"
    )
    proposals: List[ProposalItem] = Field(
        default_factory=list, description="Lista de propuestas estructuradas para el equipo"
    )
    questions: List[str] = Field(
        default_factory=list, description="Preguntas concretas para clarificar requisitos o ambigüedades"
    )
    needs_context: bool = Field(
        default=False, description="True si falta información esencial para emitir un juicio definitivo"
    )


AI_TEAM_RESPONSE_SCHEMA: Dict[str, Any] = AiTeamResponse.model_json_schema()


# ── Prompt Builder ────────────────────────────────────────────────────────────

class PromptBuilder:
    """Builds full LLM requests adhering to role personas, knowledge slices, and budgets."""

    @staticmethod
    def get_context_budget() -> int:
        """Returns the configured token budget, prioritizing AI_CONTEXT_BUDGET_TOKENS."""
        return getattr(settings, "AI_CONTEXT_BUDGET_TOKENS", None) or getattr(settings, "AI_CONTEXT_MAX_TOKENS", 8000)

    @classmethod
    def build_static_prefix(
        cls,
        role: RoleDefinition,
        team_members: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Assembles the static, byte-identical prefix for the given role.
        
        Order:
        1. Role persona definition (tone, tools, checklist, anti-patterns).
        2. Curated domain knowledge slice for the role.
        """
        persona = build_role_persona_prompt(role, team_members)
        knowledge_slice = knowledge_loader.get_slice_for_role(role.id, max_budget_tokens=6000)

        parts = [
            f"=== PERFIL Y ROL DEL ASISTENTE ===\n{persona}",
            f"=== BASE DE CONOCIMIENTO TÉCNICO DE CLASSFORGE ===\n{knowledge_slice}",
        ]
        return "\n\n".join(parts)

    @classmethod
    def build_dynamic_context(
        cls,
        project: Optional[Dict[str, Any]] = None,
        diagram: Optional[Union[Diagram, Dict[str, Any]]] = None,
        digest: Optional[str] = None,
        recently_touched_ids: Optional[List[str]] = None,
        god_class_threshold: int = 15,
        diagram_budget_tokens: int = 2500,
    ) -> str:
        """Assembles dynamic project state, resolved diagram summary, and linter findings.
        
        Never throws unhandled errors or exposes str(e) tracebacks in prompt text.
        """
        parts: List[str] = []

        # 1. Project Digest / Overview
        proj_parts: List[str] = []
        if project and isinstance(project, dict):
            p_name = project.get("name") or "Sin nombre"
            p_desc = project.get("description") or "Sin descripción"
            p_status = project.get("status") or "in_progress"
            proj_parts.append(f"Proyecto: {p_name} | Estado: {p_status}\nDescripción: {p_desc}")

        if digest:
            proj_parts.append(f"Resumen Ejecutivo del Proyecto:\n{digest}")

        if proj_parts:
            parts.append("=== CONTEXTO DEL PROYECTO ===\n" + "\n\n".join(proj_parts))

        # 2. Canonical Diagram & Deterministic Linter Findings
        diag_model: Optional[Diagram] = None
        if isinstance(diagram, Diagram):
            diag_model = diagram
        elif isinstance(diagram, dict):
            try:
                diag_model = from_graph_data(diagram)
            except Exception as e:
                logger.warning(f"[PromptBuilder] Error parsing diagram dict: {e}")
                diag_model = Diagram()

        if diag_model and diag_model.nodes:
            # Run deterministic linter
            findings: List[Finding] = []
            try:
                findings = lint(diag_model, god_class_threshold=god_class_threshold)
            except Exception as e:
                logger.warning(f"[PromptBuilder] Linter error: {e}")

            summary_text = summarize_diagram(
                diagram=diag_model,
                budget_tokens=diagram_budget_tokens,
                recently_touched_ids=recently_touched_ids,
                findings=findings,
            )
            parts.append("=== ESTADO ACTUAL DEL DIAGRAMA UML ===\n" + summary_text)
        else:
            parts.append("=== ESTADO DEL DIAGRAMA UML ===\nDiagrama vacío o sin clasificadores registrados.")

        return "\n\n".join(parts)

    @classmethod
    def sanitize_history(
        cls,
        turns: Optional[List[Union[LlmMessage, Dict[str, Any]]]],
        max_history_turns: int = 10,
    ) -> List[LlmMessage]:
        """Normalizes and ensures strictly alternating valid conversation turns."""
        if not turns:
            return []

        normalized: List[LlmMessage] = []
        for t in turns:
            if isinstance(t, LlmMessage):
                text = t.text.strip()
                if text:
                    normalized.append(LlmMessage(role=t.role, text=text))
            elif isinstance(t, dict):
                role = "model" if t.get("author_type") == "ai" or t.get("role") in ("model", "assistant") else "user"
                content = str(t.get("content") or t.get("text") or "").strip()
                if content:
                    normalized.append(LlmMessage(role=role, text=content))

        # Keep last N turns
        recent = normalized[-max_history_turns:] if len(normalized) > max_history_turns else normalized

        # Enforce valid alternating sequence (merge consecutive same-role messages)
        merged: List[LlmMessage] = []
        for msg in recent:
            if merged and merged[-1].role == msg.role:
                merged[-1] = LlmMessage(role=msg.role, text=f"{merged[-1].text}\n\n{msg.text}")
            else:
                merged.append(msg)

        return merged

    @classmethod
    def build(
        cls,
        role: Union[RoleDefinition, str],
        project: Optional[Dict[str, Any]] = None,
        diagram: Optional[Union[Diagram, Dict[str, Any]]] = None,
        digest: Optional[str] = None,
        turns: Optional[List[Union[LlmMessage, Dict[str, Any]]]] = None,
        trigger: str = "",
        team_members: Optional[List[Dict[str, Any]]] = None,
        recently_touched_ids: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        purpose: str = "chat",
        profile: Literal["standard", "local"] = "standard",
    ) -> LlmRequest:
        """Assembles the complete LlmRequest for LLM structured output.
        
        Profiles:
        - "standard": Gemini 3.8 Flash (cache-friendly prefix >= 4096 tokens, full knowledge slice).
        - "local": Local small models (1-3B Q4 class, strict budget <= 2000 tokens, BM25 retrieval).
        """
        role_def = get_role(role) if isinstance(role, str) else role

        if profile == "local":
            # Lightweight RAG profile with BM25 retrieval (bounded <= 2000 tokens)
            retrieved_knowledge = bm25_retriever.retrieve_context_text(query=trigger, max_tokens=500)
            compact_persona = (
                f"Eres {role_def.name} ({role_def.label_es}) en ClassForge.\n"
                f"Misión: {role_def.description_es}\n"
                f"Tono: {role_def.tone}. Responde de forma concisa y fundamentada."
            )
            static_prefix = (
                f"=== ROL Y PERFIL ===\n{compact_persona}\n\n"
                f"=== CONOCIMIENTO RELEVANTE RECUPERADO (BM25) ===\n{retrieved_knowledge}"
            )
            dynamic_context = cls.build_dynamic_context(
                project=project,
                diagram=diagram,
                digest=digest,
                recently_touched_ids=recently_touched_ids,
                diagram_budget_tokens=500,
            )
            sanitized_history = cls.sanitize_history(turns, max_history_turns=4)
        else:
            # Standard cache-friendly prefix for cloud models (Gemini)
            static_prefix = cls.build_static_prefix(role_def, team_members=team_members)
            dynamic_context = cls.build_dynamic_context(
                project=project,
                diagram=diagram,
                digest=digest,
                recently_touched_ids=recently_touched_ids,
            )
            sanitized_history = cls.sanitize_history(turns)

        full_system = f"{static_prefix}\n\n{dynamic_context}"

        # Append latest trigger user message
        clean_trigger = trigger.strip() or "Por favor, analiza el estado actual del diagrama y comparte tu evaluación."
        final_messages = list(sanitized_history)
        if not final_messages or final_messages[-1].role != "user":
            final_messages.append(LlmMessage(role="user", text=clean_trigger))
        else:
            final_messages[-1] = LlmMessage(
                role="user",
                text=f"{final_messages[-1].text}\n\n{clean_trigger}"
            )

        from pydantic import SecretStr

        proj_id = str(project.get("_id") or project.get("id") or "") if project else None

        return LlmRequest(
            system=full_system,
            messages=final_messages,
            temperature=0.1 if profile == "local" else role_def.temperature,
            json_schema=AI_TEAM_RESPONSE_SCHEMA,
            thinking=None if profile == "local" else role_def.thinking,
            purpose=purpose,
            project_id=proj_id,
            api_key=SecretStr(api_key) if api_key else None,
            model=model,
            max_output_tokens=1024 if profile == "local" else None,
        )

    @classmethod
    def build_local_uml_prompt(
        cls,
        prompt: str,
        diagram_context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        purpose: str = "task",
    ) -> LlmRequest:
        """
        Builds a compact, narrow prompt for local 1-3B models specifically for
        'natural language -> UML command JSON' (context budget <= 2000 tokens).
        Uses BM25 retrieval over 20_comandos_uml.md for relevant schema examples.
        """
        retrieved_examples = bm25_retriever.retrieve_context_text(
            query=f"comando uml json {prompt}",
            max_tokens=600,
        )

        system_instruction = (
            "Eres un Asistente Experto en Generación de Diagramas UML en formato JSON para ClassForge.\n"
            "Tu ÚNICA tarea es convertir la solicitud del usuario en un comando UML JSON válido.\n\n"
            "FORMATO REQUERIDO (responde ÚNICAMENTE un objeto JSON válido, sin explicaciones ni markdown):\n"
            "{\n"
            '  "action": "generate_system" | "create_class" | "create_relation" | "add_attribute" | "add_method",\n'
            '  "classes": [\n'
            '    {\n'
            '      "name": "NombreClase",\n'
            '      "attributes": [{"name": "id", "type": "Long", "visibility": "-"}],\n'
            '      "methods": [{"name": "metodo", "params": "", "return_type": "void", "visibility": "+"}]\n'
            '    }\n'
            '  ],\n'
            '  "relations": [\n'
            '    {\n'
            '      "source": "ClaseA",\n'
            '      "target": "ClaseB",\n'
            '      "type": "association" | "inheritance" | "composition" | "aggregation",\n'
            '      "sourceMultiplicity": "1",\n'
            '      "targetMultiplicity": "1..*",\n'
            '      "label": ""\n'
            '    }\n'
            '  ],\n'
            '  "deleted_elements": [],\n'
            '  "explanation": "Resumen breve de clases y relaciones."\n'
            "}\n\n"
            "REGLAS:\n"
            "1. Todas las clases llevan atributo 'id: Long' excepto si el usuario dice 'sin id'.\n"
            "2. En 'composition', 'source' es la clase contenedor (rombo lleno) y 'target' la parte.\n"
            "3. En 'inheritance', 'source' es la subclase (hija) y 'target' la superclase (padre).\n"
            "4. Responde ÚNICAMENTE el JSON válido.\n"
        )
        if retrieved_examples:
            system_instruction += f"\nEJEMPLOS Y GUÍA RECUPERADOS (BM25):\n{retrieved_examples}\n"

        context_str = ""
        if diagram_context and isinstance(diagram_context, dict):
            nodes = diagram_context.get("nodes") or diagram_context.get("classes") or []
            if nodes:
                # Include compact list of existing class names
                names = [str(n.get("name") if isinstance(n, dict) else n) for n in nodes[:15]]
                context_str = f"\nContexto del lienzo (clases existentes): {', '.join(names)}"

        user_content = f"Solicitud: {prompt}{context_str}\nGenera el comando UML JSON correspondiente."

        from app.modules.ai.gemini_service import UML_JSON_SCHEMA

        return LlmRequest(
            system=system_instruction,
            messages=[LlmMessage(role="user", text=user_content)],
            temperature=0.1,
            json_schema=UML_JSON_SCHEMA,
            purpose=purpose,
            model=model,
            max_output_tokens=1500,
        )
