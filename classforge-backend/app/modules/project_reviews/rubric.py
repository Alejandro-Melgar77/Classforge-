from typing import Dict, List, Optional, Tuple
from app.modules.project_reviews.domain.models import (
    VerdictType,
    RubricCriterionDefinition,
    RubricDefinition,
)

STANDARD_RUBRIC_CODE = "CF-SE-2026.1"
STANDARD_RUBRIC_VERSION = "2026.1"

STANDARD_CRITERIA: List[RubricCriterionDefinition] = [
    RubricCriterionDefinition(
        code="definicion_problema_alcance",
        name="Definición del Problema y Alcance",
        weight=15.0,
        description="Claridad y rigor en la formulación del problema, justificación, objetivos del sistema y delimitación del alcance.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Identificación clara de la problemática o necesidad de negocio",
            "Objetivo general y objetivos específicos medibles",
            "Límites y alcance explícito del producto de software",
        ],
    ),
    RubricCriterionDefinition(
        code="especificacion_requisitos",
        name="Especificación de Requisitos",
        weight=20.0,
        description="Completitud y precisión de los requisitos funcionales (RF) y no funcionales (RNF), trazabilidad y reglas de negocio.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Lista numerada y estructurada de Requisitos Funcionales (RF)",
            "Especificación de Requisitos No Funcionales (rendimiento, disponibilidad, seguridad)",
            "Casos de uso o historias de usuario con criterios de aceptación",
        ],
    ),
    RubricCriterionDefinition(
        code="arquitectura_diagrama_uml",
        name="Arquitectura y Diagrama de Clases UML",
        weight=25.0,
        description="Estructura arquitectónica, calidad y formalidad del diagrama de clases UML 2.5+, patrones de diseño y acoplamiento.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Identificación clara de capas o arquitectura (MVC, Hexagonal, Clean, etc.)",
            "Diagrama de clases UML con atributos tipados, visibilidad y métodos",
            "Relaciones UML correctas: asociación, agregación, composición, herencia e interfaces",
            "Bajo acoplamiento y alta cohesión entre componentes",
        ],
    ),
    RubricCriterionDefinition(
        code="modelo_persistencia_datos",
        name="Modelo de Persistencia y Base de Datos",
        weight=15.0,
        description="Diseño del modelo de datos, normalización/esquema, consistencia con el diagrama de clases y persistencia.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Esquema relacional o de colecciones NoSQL bien definido",
            "Definición de claves primarias, foráneas o índices",
            "Coherencia directa con las entidades del diagrama de clases UML",
        ],
    ),
    RubricCriterionDefinition(
        code="plan_pruebas_qa",
        name="Plan de Pruebas y Aseguramiento de Calidad",
        weight=15.0,
        description="Estrategia de aseguramiento de calidad (QA), diseño de casos de prueba unitarios, integración y criterios de aceptación.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Estrategia de pruebas definida (unitarias, integración, carga)",
            "Casos de prueba con entradas, pasos y resultados esperados",
            "Métricas de cobertura y criterios de calidad de código",
        ],
    ),
    RubricCriterionDefinition(
        code="seguridad_riesgos",
        name="Seguridad y Gestión de Riesgos",
        weight=10.0,
        description="Identificación de riesgos técnicos y operativos, modelos de autenticación/autorización y mitigación de vulnerabilidades.",
        min_passing_score=40.0,
        evaluation_hints=[
            "Mecanismos de autenticación (JWT, OAuth) y autorización RBAC",
            "Matriz de riesgos técnicos, operativos o de seguridad con planes de mitigación",
            "Protección de datos sensibles y control de accesos",
        ],
    ),
]

RUBRIC_REGISTRY: Dict[str, RubricDefinition] = {
    STANDARD_RUBRIC_CODE: RubricDefinition(
        code=STANDARD_RUBRIC_CODE,
        version=STANDARD_RUBRIC_VERSION,
        name="Rúbrica Estándar de Evaluación de Proyectos de Software ClassForge",
        description="Rúbrica técnica para evaluar proyectos de ingeniería de software documental, arquitectura UML y calidad de diseño.",
        passing_score=70.0,
        criteria=STANDARD_CRITERIA,
    )
}


def get_rubric(code: Optional[str] = None) -> RubricDefinition:
    """Returns the rubric definition for the requested code or the default standard rubric."""
    rubric_code = code or STANDARD_RUBRIC_CODE
    if rubric_code not in RUBRIC_REGISTRY:
        return RUBRIC_REGISTRY[STANDARD_RUBRIC_CODE]
    return RUBRIC_REGISTRY[rubric_code]


def list_available_rubrics() -> List[RubricDefinition]:
    """Returns all registered rubric models."""
    return list(RUBRIC_REGISTRY.values())


def evaluate_verdict(
    total_score: float,
    criteria_scores: Dict[str, float],
    has_sufficient_text: bool,
    detected_sections_count: int,
    passing_score: float = 70.0,
) -> Tuple[VerdictType, str]:
    """
    Computes final review verdict and summary explanation based on:
    - Text sufficiency
    - Presence of critical project sections
    - Total weighted score against passing threshold
    - Critical criteria minimum passing scores
    """
    if not has_sufficient_text:
        return (
            VerdictType.INFORMACION_INSUFICIENTE,
            "El documento analizado contiene menos de 50 palabras extraíbles o corresponde a un PDF escaneado sin capa de texto OCR legible. No es posible realizar una evaluación técnica confiable.",
        )

    if detected_sections_count < 2 and total_score < 40.0:
        return (
            VerdictType.INFORMACION_INSUFICIENTE,
            f"El documento carece de las secciones fundamentales mínimas para un proyecto de software formal (solo se identificaron {detected_sections_count} de 6 secciones). Se requiere mayor documentación técnica.",
        )

    # Check critical disqualifiers (Architecture & Requirements cannot fail completely)
    arch_score = criteria_scores.get("arquitectura_diagrama_uml", 0.0)
    req_score = criteria_scores.get("especificacion_requisitos", 0.0)

    if arch_score < 30.0 and req_score < 30.0:
        return (
            VerdictType.RECHAZADO,
            f"El proyecto fue rechazado debido a deficiencias críticas simultáneas en la Especificación de Requisitos ({req_score:.1f}/100) y la Arquitectura / Diagrama UML ({arch_score:.1f}/100).",
        )

    if total_score >= passing_score:
        return (
            VerdictType.APROBADO,
            f"El proyecto cumple satisfactoriamente con los criterios de calidad técnica de la rúbrica ({total_score:.1f}/100, umbral: {passing_score:.1f}/100). Se ha generado el pliego de especificaciones técnicas.",
        )
    else:
        return (
            VerdictType.RECHAZADO,
            f"El proyecto no alcanza el umbral de aprobación requerido ({total_score:.1f}/100 vs mínimo de {passing_score:.1f}/100). Consulte las recomendaciones prioritarias para subsanar los hallazgos.",
        )
