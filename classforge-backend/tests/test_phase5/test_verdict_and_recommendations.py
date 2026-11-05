import pytest
from app.modules.project_reviews.domain.models import VerdictType, RecommendationPriority
from app.modules.project_reviews.rubric import evaluate_verdict
from app.modules.project_reviews.evaluator import ProjectEvaluator
from app.modules.project_reviews.pdf_extractor import ExtractedDocument, PageContent


def test_evaluate_verdict_threshold_logic():
    """Validates boundary conditions of verdict computation."""
    # 70.0 is passing
    v1, msg1 = evaluate_verdict(
        total_score=70.0,
        criteria_scores={"arquitectura_diagrama_uml": 70.0, "especificacion_requisitos": 70.0},
        has_sufficient_text=True,
        detected_sections_count=5,
    )
    assert v1 == VerdictType.APROBADO
    assert "cumple satisfactoriamente" in msg1

    # 69.9 is rejected
    v2, msg2 = evaluate_verdict(
        total_score=69.9,
        criteria_scores={"arquitectura_diagrama_uml": 65.0, "especificacion_requisitos": 70.0},
        has_sufficient_text=True,
        detected_sections_count=5,
    )
    assert v2 == VerdictType.RECHAZADO
    assert "no alcanza el umbral" in msg2

    # Insufficient text is always INFORMACION_INSUFICIENTE
    v3, msg3 = evaluate_verdict(
        total_score=95.0,
        criteria_scores={},
        has_sufficient_text=False,
        detected_sections_count=0,
    )
    assert v3 == VerdictType.INFORMACION_INSUFICIENTE
    assert "menos de 50 palabras" in msg3


@pytest.mark.asyncio
async def test_high_quality_project_approved_with_technical_specification():
    """Confirms high-quality project is APROBADO and produces complete TechnicalSpecification."""
    doc_text = (
        "[Página 1]\n"
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
        "Planteamiento del problema: necesidad de automatizar logística vehicular. "
        "Objetivo general: construir plataforma tolerante a fallos. "
        "Alcance del proyecto: gestión de rutas, telemetría y geocercas.\n\n"
        "[Página 2]\n"
        "ESPECIFICACIÓN DE REQUISITOS\n"
        "RF-01: Registro de unidades de transporte.\n"
        "RF-02: Transmisión de coordenadas GPS en tiempo real.\n"
        "RF-03: Alerta automática por exceso de velocidad.\n"
        "RNF-01: Disponibilidad 99.9% anual. RNF-02: Latencia < 200 ms.\n"
        "Casos de uso: CU-01 Registrar Vehiculo, CU-02 Notificar Alerta.\n\n"
        "[Página 3]\n"
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
        "Arquitectura multicapa Clean Architecture.\n"
        "class Vehiculo { +placa: String, +capacidad: Double }\n"
        "class DispositivoGPS { +imei: String, +enviar(): Void }\n"
        "Relaciones: Vehiculo 1 -- 1 DispositivoGPS (agregación y composición).\n\n"
        "[Página 4]\n"
        "MODELO DE PERSISTENCIA Y BASE DE DATOS\n"
        "Base de datos PostgreSQL con tablas relacionales vehiculos, dispositivos, alertas.\n"
        "Claves foráneas con integridad referencial e índices B-Tree.\n\n"
        "[Página 5]\n"
        "PLAN DE PRUEBAS Y ASEGURAMIENTO DE CALIDAD\n"
        "Plan de pruebas con pytest para lógica de negocio y pruebas unitarias de cálculo de distancias.\n"
        "Casos de prueba para validación de geocercas.\n\n"
        "[Página 6]\n"
        "SEGURIDAD Y GESTIÓN DE RIESGOS\n"
        "Autenticación con JWT, cifrado TLS 1.3 y control de acceso basado en roles (RBAC).\n"
        "Matriz de riesgos técnicos para pérdida de señal celular."
    )

    pages = [
        PageContent(page_number=i + 1, text=block.strip(), word_count=len(block.split()))
        for i, block in enumerate(doc_text.split("[Página "))
        if block.strip()
    ]
    doc = ExtractedDocument(
        page_count=6,
        total_word_count=sum(p.word_count for p in pages),
        has_sufficient_text=True,
        pages=pages,
        detected_sections=[
            "definicion_problema_alcance",
            "especificacion_requisitos",
            "arquitectura_diagrama_uml",
            "modelo_persistencia_datos",
            "plan_pruebas_qa",
            "seguridad_riesgos",
        ],
        section_pages={
            "definicion_problema_alcance": [1],
            "especificacion_requisitos": [2],
            "arquitectura_diagrama_uml": [3],
            "modelo_persistencia_datos": [4],
            "plan_pruebas_qa": [5],
            "seguridad_riesgos": [6],
        },
        full_text=doc_text,
    )

    evaluator = ProjectEvaluator()
    res = await evaluator.evaluate_document(doc)

    assert res["verdict"] == VerdictType.APROBADO
    assert res["total_score"] >= 70.0
    assert res["technical_specification"] is not None
    spec = res["technical_specification"]
    assert len(spec.components) > 0
    assert len(spec.api_endpoints) > 0
    assert len(spec.data_model) > 0


@pytest.mark.asyncio
async def test_weak_project_rejected_with_actionable_recommendations():
    """Confirms incomplete project with sections is RECHAZADO and produces prioritized recommendations."""
    doc_text = (
        "[Página 1]\n"
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
        "Proyecto de catálogo de libros. No tenemos claros los objetivos.\n\n"
        "[Página 2]\n"
        "ESPECIFICACIÓN DE REQUISITOS\n"
        "RF-01 ver libros. No hay requisitos no funcionales ni casos de uso.\n\n"
        "[Página 3]\n"
        "No hay diagrama de clases UML ni arquitectura. Persistencia en archivo plano."
    )
    pages = [
        PageContent(page_number=1, text="DEFINICIÓN DEL PROBLEMA Y ALCANCE. Proyecto catálogo.", word_count=30),
        PageContent(page_number=2, text="ESPECIFICACIÓN DE REQUISITOS. RF-01 ver libros.", word_count=30),
        PageContent(page_number=3, text="Sin UML ni arquitectura de capas.", word_count=20),
    ]
    doc = ExtractedDocument(
        page_count=3,
        total_word_count=80,
        has_sufficient_text=True,
        pages=pages,
        detected_sections=["definicion_problema_alcance", "especificacion_requisitos"],
        section_pages={"definicion_problema_alcance": [1], "especificacion_requisitos": [2]},
        full_text=doc_text,
    )

    evaluator = ProjectEvaluator()
    res = await evaluator.evaluate_document(doc)

    assert res["verdict"] == VerdictType.RECHAZADO
    assert res["total_score"] < 70.0
    assert res["technical_specification"] is None
    assert len(res["recommendations"]) > 0

    # Ensure recommendations are prioritized
    priorities = [r.priority for r in res["recommendations"]]
    assert RecommendationPriority.HIGH in priorities
