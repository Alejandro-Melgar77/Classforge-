"""
Tests for PromptBuilder, static prefix byte-identity, token budgets,
and structured output validation with FakeLlmProvider.
"""
import pytest
from app.ai_team.application.prompt_builder import (
    PromptBuilder,
    AiTeamResponse,
    ProposalItem,
    AI_TEAM_RESPONSE_SCHEMA,
)
from app.ai_team.domain.roles import list_roles, get_role, build_role_persona_prompt
from app.ai_team.infrastructure.knowledge_loader import estimate_tokens
from app.llm.fake import FakeLlmProvider
from app.llm.models import LlmMessage, LlmRequest


def test_each_role_persona_prompt_under_900_tokens():
    """Requirement: Cada prompt de rol <= 900 tokens."""
    for role in list_roles():
        prompt = build_role_persona_prompt(role)
        tokens = estimate_tokens(prompt)
        assert tokens <= 900, f"Role {role.id} persona prompt is {tokens} tokens, exceeding 900"


def test_static_prefix_byte_identical_across_calls():
    """Requirement: El prefijo estático va primero y byte-idéntico entre llamadas para beneficiarse de caché."""
    for role in list_roles():
        prefix1 = PromptBuilder.build_static_prefix(role)
        prefix2 = PromptBuilder.build_static_prefix(role)
        assert prefix1 == prefix2, f"Static prefix for {role.id} is not byte-identical across calls"


def test_prompt_builder_structure():
    """Verifies that PromptBuilder includes persona, knowledge, project context, diagram, and linter findings."""
    role = get_role("architect")
    project = {"name": "SistemaHospital", "description": "Gestión hospitalaria", "status": "active"}
    diagram = {
        "nodes": [
            {"id": "c1", "type": "class", "name": "Paciente", "attributes": [{"name": "id", "type": "Long"}]},
            {"id": "c2", "type": "class", "name": "Medico", "attributes": []},  # triggers class-no-attributes
        ],
        "edges": [
            {"id": "e1", "source": "c1", "target": "c2", "type": "association"}
        ],
    }

    req = PromptBuilder.build(
        role=role,
        project=project,
        diagram=diagram,
        trigger="¿Cómo deberíamos modelar las citas médicas?",
    )

    assert isinstance(req, LlmRequest)
    assert req.json_schema == AI_TEAM_RESPONSE_SCHEMA
    assert req.temperature == role.temperature
    assert req.thinking == role.thinking

    # Verify sections in system instruction
    assert "=== PERFIL Y ROL DEL ASISTENTE ===" in req.system
    assert "=== BASE DE CONOCIMIENTO TÉCNICO DE CLASSFORGE ===" in req.system
    assert "=== CONTEXTO DEL PROYECTO ===" in req.system
    assert "SistemaHospital" in req.system
    assert "=== ESTADO ACTUAL DEL DIAGRAMA UML ===" in req.system
    assert "HALLAZGOS DEL LINTER" in req.system
    assert "class-no-attributes" in req.system
    assert "Paciente --[association]--> Medico" in req.system

    # Verify messages
    assert len(req.messages) >= 1
    assert req.messages[-1].role == "user"
    assert "¿Cómo deberíamos modelar las citas médicas?" in req.messages[-1].text


def test_prompt_builder_never_injects_str_e_errors():
    """Requirement: Sin inyectar str(e) ni errores internos en el prompt."""
    role = get_role("qa")
    # Passing corrupted diagram dictionary that might raise exceptions during processing
    corrupted_diagram = {"nodes": "invalid_not_a_list", "edges": 12345}

    req = PromptBuilder.build(
        role=role,
        project={"name": "Test"},
        diagram=corrupted_diagram,
        trigger="Analiza el diagrama",
    )

    assert "Traceback" not in req.system
    assert "Error al cargar contexto:" not in req.system
    assert "Exception" not in req.system


def test_structured_response_model_validation():
    """Verifies that AiTeamResponse parses valid structured JSON outputs."""
    valid_payload = {
        "reply_markdown": "He analizado el modelo. Recomiendo desacoplar la relación entre Paciente y Medico creando la entidad Cita.",
        "proposals": [
            {
                "id": "prop-1",
                "kind": "uml_command",
                "title": "Crear entidad Cita",
                "rationale": "Evita acoplamiento directo y permite registrar fecha y estado",
                "severity": "warn",
                "command": {
                    "action": "add_class",
                    "classes": [
                        {
                            "name": "Cita",
                            "attributes": [
                                {"name": "id", "type": "Long", "visibility": "-"},
                                {"name": "fecha", "type": "DateTime", "visibility": "-"}
                            ],
                            "methods": []
                        }
                    ],
                    "relations": [],
                    "deleted_elements": [],
                    "explanation": "Entidad intermedia Cita",
                    "source": "backend_ai"
                },
                "target_element_ids": ["c1", "c2"]
            }
        ],
        "questions": ["¿Las citas pueden ser virtuales o solo presenciales?"],
        "needs_context": False
    }

    parsed = AiTeamResponse.model_validate(valid_payload)
    assert parsed.reply_markdown.startswith("He analizado")
    assert len(parsed.proposals) == 1
    proposal = parsed.proposals[0]
    assert proposal.kind == "uml_command"
    assert proposal.command is not None
    assert proposal.command.action == "add_class"
    assert proposal.command.classes[0].name == "Cita"
    assert len(parsed.questions) == 1
    assert parsed.needs_context is False


@pytest.mark.asyncio
async def test_fake_llm_provider_with_structured_contract():
    """Verifies integration with FakeLlmProvider returning structured responses."""
    provider = FakeLlmProvider()

    req = PromptBuilder.build(
        role="architect",
        project={"name": "Demo"},
        trigger="Propón mejoras para el diagrama",
    )

    resp = await provider.generate(req)
    assert resp.raw_json is not None or resp.text is not None
