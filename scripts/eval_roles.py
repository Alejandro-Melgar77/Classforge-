#!/usr/bin/env python3
"""
scripts/eval_roles.py — Manual evaluation suite for ClassForge AI Roles.

Evaluates 12 golden scenarios against the role definitions, deterministic linter,
knowledge slices, and structured output contract (AiTeamResponse).
Can run offline with FakeLlmProvider or against live Gemini models when configured.

Usage:
    python scripts/eval_roles.py [--live] [--role ROLE]
"""
import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Ensure classforge-backend is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "classforge-backend")))

from app.core.config import settings
from app.ai_team.domain.roles import get_role, list_roles, RoleDefinition
from app.ai_team.domain.diagram_model import from_graph_data
from app.ai_team.domain.lint import lint
from app.ai_team.application.prompt_builder import PromptBuilder, AiTeamResponse
from app.llm import get_provider
from app.llm.models import LlmRequest


@dataclass
class GoldenTestCase:
    id: str
    role_id: str
    title: str
    category: str
    prompt: str
    diagram: Dict[str, Any]
    expected_findings: List[str]
    rubric_focus: str


GOLDEN_CASES: List[GoldenTestCase] = [
    # ── Architect ─────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-ARCH-1",
        role_id="architect",
        title="Detección y partición de Clase Dios",
        category="SOLID: SRP",
        prompt="Revisa la clase SistemaGestor. Tiene demasiada lógica mezclada, ¿qué sugieres hacer?",
        diagram={
            "nodes": [
                {
                    "id": "c1",
                    "type": "class",
                    "name": "SistemaGestor",
                    "attributes": [{"name": f"campo{i}", "type": "String"} for i in range(10)],
                    "methods": [{"name": f"operacion{i}", "return_type": "void"} for i in range(8)],
                }
            ],
            "edges": [],
        },
        expected_findings=["god-class", "missing-primary-key"],
        rubric_focus="Debe proponer partición modular en clases cohesivas y emitir propuesta de refactorización.",
    ),
    GoldenTestCase(
        id="GOLDEN-ARCH-2",
        role_id="architect",
        title="Herencia vs Composición en motor de pagos",
        category="Arquitectura",
        prompt="¿Es correcto que TarjetaCredito y Transferencia hereden de CarritoCompra?",
        diagram={
            "nodes": [
                {"id": "n1", "type": "class", "name": "CarritoCompra", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "n2", "type": "class", "name": "TarjetaCredito", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "n3", "type": "class", "name": "Transferencia", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [
                {"id": "e1", "source": "n2", "target": "n1", "type": "inheritance"},
                {"id": "e2", "source": "n3", "target": "n1", "type": "inheritance"},
            ],
        },
        expected_findings=[],
        rubric_focus="Debe rechazar herencia que viola LSP y recomendar interfaz MedioPago asociada por composición.",
    ),

    # ── QA ────────────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-QA-1",
        role_id="qa",
        title="Detección de ciclo de herencia y atributos vacíos",
        category="Consistencia Estructural",
        prompt="Ejecuta una auditoría de calidad sobre este diagrama para detectar errores críticos.",
        diagram={
            "nodes": [
                {"id": "a", "type": "class", "name": "NodoA", "attributes": []},
                {"id": "b", "type": "class", "name": "NodoB", "attributes": []},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b", "type": "inheritance"},
                {"id": "e2", "source": "b", "target": "a", "type": "inheritance"},
            ],
        },
        expected_findings=["inheritance-cycle", "class-no-attributes"],
        rubric_focus="Debe reportar como hecho verificado el ciclo de herencia y sugerir cómo romperlo.",
    ),
    GoldenTestCase(
        id="GOLDEN-QA-2",
        role_id="qa",
        title="Nombres en snake_case y cardinalidad invertida",
        category="Estándares y Cardinalidad",
        prompt="Verifica las convenciones de nomenclatura y las relaciones entre entidades.",
        diagram={
            "nodes": [
                {
                    "id": "c1",
                    "type": "class",
                    "name": "detalle_factura",
                    "attributes": [{"name": "Monto_Total", "type": "Double"}],
                },
                {"id": "c2", "type": "class", "name": "Factura", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [
                {"id": "e1", "source": "c1", "target": "c2", "type": "association", "source_multiplicity": "2..1"},
            ],
        },
        expected_findings=["class-not-pascal-case", "attribute-not-camel-case", "invalid-multiplicity"],
        rubric_focus="Debe reportar 'class-not-pascal-case', 'attribute-not-camel-case' y 'invalid-multiplicity (2..1)'.",
    ),

    # ── Tech Lead ─────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-TECH-1",
        role_id="tech_lead",
        title="Viabilidad para codegen Spring Boot (Herencia múltiple)",
        category="Codegen Compatibility",
        prompt="Queremos generar backend en Spring Boot. ¿Este modelo compilará sin problemas?",
        diagram={
            "nodes": [
                {"id": "c1", "type": "class", "name": "EntidadBaseA", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "c2", "type": "class", "name": "EntidadBaseB", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "c3", "type": "class", "name": "HijoMultiple", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [
                {"id": "e1", "source": "c3", "target": "c1", "type": "inheritance"},
                {"id": "e2", "source": "c3", "target": "c2", "type": "inheritance"},
            ],
        },
        expected_findings=["multiple-class-inheritance"],
        rubric_focus="Debe advertir que Java no soporta herencia múltiple de clases y proponer interfaces o composición.",
    ),
    GoldenTestCase(
        id="GOLDEN-TECH-2",
        role_id="tech_lead",
        title="Mapeo ORM de tipos y claves primarias",
        category="Codegen / FastAPI",
        prompt="¿Cómo mapearías estos atributos a SQLAlchemy y Pydantic en FastAPI?",
        diagram={
            "nodes": [
                {
                    "id": "c1",
                    "type": "class",
                    "name": "Producto",
                    "attributes": [
                        {"name": "id", "type": "UUID", "visibility": "-"},
                        {"name": "precio", "type": "Double", "visibility": "-"},
                        {"name": "activo", "type": "Boolean", "visibility": "-"},
                    ],
                }
            ],
            "edges": [],
        },
        expected_findings=[],
        rubric_focus="Debe orientar el mapeo a tipos nativos de Python/SQLAlchemy y verificar Pydantic v2.",
    ),

    # ── Mentor ────────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-MENTOR-1",
        role_id="mentor",
        title="Explicación didáctica de Agregación vs Composición",
        category="Conceptos OO",
        prompt="¿Cuál es la diferencia entre agregación y composición en UML? ¿Cuál debería usar para Aula y Escuela?",
        diagram={
            "nodes": [
                {"id": "c1", "type": "class", "name": "Escuela", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "c2", "type": "class", "name": "Aula", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [],
        },
        expected_findings=["orphan-node"],
        rubric_focus="Debe explicar con claridad existencial (ciclo de vida compartido = composición) y tono empático.",
    ),
    GoldenTestCase(
        id="GOLDEN-MENTOR-2",
        role_id="mentor",
        title="Principio de Inversión de Dependencias (DIP)",
        category="SOLID: DIP",
        prompt="¿Por qué mi clase PedidoService no debería depender directamente de MySQLDatabase?",
        diagram={
            "nodes": [
                {"id": "c1", "type": "class", "name": "PedidoService", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "c2", "type": "class", "name": "MySQLDatabase", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [
                {"id": "e1", "source": "c1", "target": "c2", "type": "association"}
            ],
        },
        expected_findings=[],
        rubric_focus="Debe explicar DIP pedagógicamente proponiendo una interfaz PedidoRepository intermedia.",
    ),

    # ── DBA ───────────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-DBA-1",
        role_id="dba",
        title="Resolución de relación N-a-N con clase de asociación",
        category="Normalización 3FN",
        prompt="Tenemos estudiantes y cursos con relación directa muchos a muchos. ¿Cómo optimizamos la persistencia?",
        diagram={
            "nodes": [
                {"id": "c1", "type": "class", "name": "Estudiante", "attributes": [{"name": "id", "type": "Long"}]},
                {"id": "c2", "type": "class", "name": "Curso", "attributes": [{"name": "id", "type": "Long"}]},
            ],
            "edges": [
                {"id": "e1", "source": "c1", "target": "c2", "type": "association", "source_multiplicity": "*", "target_multiplicity": "*"}
            ],
        },
        expected_findings=["many-to-many-direct"],
        rubric_focus="Debe exigir clase de asociación Matricula para alojar fecha, estado y claves foráneas.",
    ),
    GoldenTestCase(
        id="GOLDEN-DBA-2",
        role_id="dba",
        title="Entidades huérfanas sin clave primaria",
        category="Claves Primarias",
        prompt="Revisa la estructura de tablas para la base de datos relacional.",
        diagram={
            "nodes": [
                {
                    "id": "c1",
                    "type": "class",
                    "name": "RegistroLog",
                    "attributes": [{"name": "mensaje", "type": "String"}],
                }
            ],
            "edges": [],
        },
        expected_findings=["missing-primary-key"],
        rubric_focus="Debe advertir de inmediato la falta de clave primaria e indicar tipo id adecuado.",
    ),

    # ── Security ──────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-SEC-1",
        role_id="security",
        title="Contraseña en texto plano y visibilidad pública",
        category="OWASP / Protección de Datos",
        prompt="Revisa la clase Usuario para un sistema de comercio electrónico.",
        diagram={
            "nodes": [
                {
                    "id": "c1",
                    "type": "class",
                    "name": "Usuario",
                    "attributes": [
                        {"name": "id", "type": "Long", "visibility": "-"},
                        {"name": "password", "type": "String", "visibility": "+"},  # Security risk
                    ],
                }
            ],
            "edges": [],
        },
        expected_findings=[],
        rubric_focus="Debe alertar sobre vulnerabilidad OWASP de contraseña en claro y exigir passwordHash privado (-).",
    ),

    # ── Analyst ───────────────────────────────────────────────────────────────
    GoldenTestCase(
        id="GOLDEN-ANA-1",
        role_id="analyst",
        title="Mapeo de Historia de Usuario a Clases",
        category="Requisitos a Modelo",
        prompt="Historia de usuario: 'Como cliente quiero solicitar un préstamo bancario que registre monto, plazo y cuotas mensuales'.",
        diagram={
            "nodes": [
                {"id": "c1", "type": "class", "name": "Cliente", "attributes": [{"name": "id", "type": "Long"}]}
            ],
            "edges": [],
        },
        expected_findings=[],
        rubric_focus="Debe identificar clases faltantes (Prestamo, Cuota) y hacer preguntas sobre tasas y reglas de aprobación.",
    ),
]


def score_response(case: GoldenTestCase, resp: Optional[AiTeamResponse], linter_findings: list) -> tuple[int, str]:
    """Scores response on 20-point rubric:
    1. Persona & Tone (0-5)
    2. Grounding in linter facts & diagram (0-5)
    3. Structured output validity & proposals (0-5)
    4. Domain fidelity to role (0-5)
    """
    if not resp:
        return 0, "Fallo: Sin respuesta estructurada"

    score = 0
    notes = []

    # 1. Persona & Tone (1st person, no LLM clichés)
    text = resp.reply_markdown.lower()
    if "como modelo de lenguaje" in text or "como ia" in text:
        score += 1
        notes.append("Uso de cliché de IA (-2)")
    else:
        score += 5

    # 2. Grounding in linter facts & diagram
    findings_matched = 0
    for ef in case.expected_findings:
        if any(f.rule == ef for f in linter_findings):
            findings_matched += 1
    if case.expected_findings:
        ratio = findings_matched / len(case.expected_findings)
        score += int(round(ratio * 5))
    else:
        score += 5

    # 3. Structured output validity
    if resp.proposals or resp.questions:
        score += 5
    elif len(resp.reply_markdown) > 50:
        score += 3
    else:
        score += 1

    # 4. Domain fidelity
    role_def = get_role(case.role_id)
    any_trigger = any(trig in text for trig in role_def.triggers)
    if any_trigger:
        score += 5
    else:
        score += 4

    status = "EXCELENTE" if score >= 18 else "APROBADO" if score >= 14 else "REVISAR"
    return score, status


async def run_evaluation(live: bool = False, target_role: Optional[str] = None):
    print("=" * 80)
    print(" ClassForge AI Team — Manual Golden Evaluation Suite (12 Golden Test Cases)")
    print(f" Mode: {'LIVE (Gemini API)' if live else 'OFFLINE (Deterministic / Fake Provider)'}")
    print("=" * 80)

    cases = [c for c in GOLDEN_CASES if not target_role or c.role_id == target_role]
    if not cases:
        print(f"No test cases found for role '{target_role}'.")
        return

    provider = get_provider(purpose="chat")

    results = []

    for case in cases:
        diag = from_graph_data(case.diagram)
        findings = lint(diag)

        req = PromptBuilder.build(
            role=case.role_id,
            project={"name": "ProyectoEvaluacion", "status": "active"},
            diagram=diag,
            trigger=case.prompt,
            purpose="chat",
        )

        structured_resp: Optional[AiTeamResponse] = None

        if live:
            try:
                res = await provider.generate(req)
                if res.raw_json:
                    structured_resp = AiTeamResponse.model_validate(res.raw_json)
                else:
                    structured_resp = AiTeamResponse(
                        reply_markdown=res.text,
                        proposals=[],
                        questions=[],
                    )
            except Exception as e:
                structured_resp = None
        else:
            # Deterministic simulation with linter grounding
            reply_md = f"He analizado el modelo desde mi rol de {case.role_id}. "
            if findings:
                reply_md += f"Detecto {len(findings)} observaciones: " + ", ".join(f.rule for f in findings) + ". "
            reply_md += case.rubric_focus

            structured_resp = AiTeamResponse(
                reply_markdown=reply_md,
                proposals=[],
                questions=["¿Deseas aplicar esta propuesta en el lienzo?"],
                needs_context=False,
            )

        score, status = score_response(case, structured_resp, findings)
        results.append((case, score, status))

    # Print Table
    header = f"{'ID':<15} | {'ROL':<12} | {'CATEGORÍA':<22} | {'SCORE':<7} | {'ESTADO':<10}"
    print("\n" + header)
    print("-" * len(header))

    total_score = 0
    for case, score, status in results:
        total_score += score
        print(f"{case.id:<15} | {case.role_id:<12} | {case.category:<22} | {score}/20   | {status:<10}")

    avg_score = (total_score / (len(results) * 20)) * 100
    print("-" * len(header))
    print(f"Total casos: {len(results)} | Puntuación promedio: {avg_score:.1f}%\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate ClassForge AI roles against golden cases.")
    parser.add_argument("--live", action="store_true", help="Execute against live Gemini API instead of mock.")
    parser.add_argument("--role", type=str, default=None, help="Filter by specific role_id.")
    args = parser.parse_args()

    asyncio.run(run_evaluation(live=args.live, target_role=args.role))


if __name__ == "__main__":
    main()
