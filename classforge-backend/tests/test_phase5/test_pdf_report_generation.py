from datetime import datetime, timezone
import pypdf
import io

from app.modules.project_reviews.domain.models import (
    ReviewStatus,
    VerdictType,
    RecommendationPriority,
)
from app.modules.project_reviews.schemas import (
    ProjectReviewResponse,
    CriterionScore,
    Recommendation,
    TechnicalSpecification,
    ComponentSpec,
    EndpointSpec,
    DataModelEntity,
)
from app.modules.project_reviews.pdf_generator import (
    generate_review_report_pdf,
    generate_specification_pdf,
)


def test_generate_review_report_pdf():
    """Generates an evaluation report and confirms ReportLab outputs valid PDF bytes."""
    review = ProjectReviewResponse(
        id="507f1f77bcf86cd799439011",
        project_id="507f1f77bcf86cd799439012",
        review_number=1,
        document_id="507f1f77bcf86cd799439013",
        document_filename="especificacion_arquitectura.pdf",
        rubric_code="CF-SE-2026.1",
        rubric_version="2026.1",
        status=ReviewStatus.COMPLETED,
        verdict=VerdictType.APROBADO,
        total_score=85.5,
        passing_score=70.0,
        summary="El proyecto presenta una arquitectura de microservicios robusta y trazable.",
        criteria_scores=[
            CriterionScore(
                criterion_code="definicion_problema_alcance",
                name="Definición del Problema y Alcance",
                weight=15.0,
                score=85.0,
                weighted_score=12.75,
                strengths=["Objetivos medibles bien definidos."],
                weaknesses=[],
                observations="Formulación clara del alcance.",
                citations=[1],
                evidence_quotes=['"Objetivo general del sistema" [Pág. 1]'],
            ),
            CriterionScore(
                criterion_code="especificacion_requisitos",
                name="Especificación de Requisitos",
                weight=20.0,
                score=80.0,
                weighted_score=16.0,
                strengths=["Requisitos funcionales numerados."],
                weaknesses=["Falta mayor detalle en RNF de seguridad."],
                observations="Adecuada cobertura de casos de uso.",
                citations=[2, 3],
                evidence_quotes=['"RF-01 Autenticación de usuarios" [Pág. 2]'],
            ),
        ],
        recommendations=[
            Recommendation(
                priority=RecommendationPriority.MEDIUM,
                criterion_code="especificacion_requisitos",
                title="Completar especificación de RNF",
                description="Detallar límites de latencia y disponibilidad.",
                action_plan="Incorporar métricas SLA en la sección de requisitos no funcionales.",
            )
        ],
        created_at=datetime.now(timezone.utc),
        created_by="507f1f77bcf86cd799439014",
    )

    pdf_bytes = generate_review_report_pdf(review, "ClassForge Microservices")

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # Parse with pypdf to verify structural validity and page count
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    first_page_text = reader.pages[0].extract_text()
    assert "Dictamen de Evaluación" in first_page_text or "ClassForge" in first_page_text
    assert "APROBADO" in first_page_text


def test_generate_specification_pdf():
    """Generates technical specification PDF and verifies valid PDF bytes."""
    spec = TechnicalSpecification(
        title="Pliego de Especificaciones Técnicas del Sistema",
        overview="Documento formal de diseño para el despliegue del sistema.",
        functional_scope=["Gestión de identidades", "Procesamiento de pagos en línea"],
        system_architecture="Arquitectura Hexagonal con microservicios en FastAPI y persistencia PostgreSQL.",
        components=[
            ComponentSpec(
                name="API Gateway",
                role="Enrutamiento y autenticación perimetral",
                technology="FastAPI / Nginx",
                description="Punto único de entrada para clientes móviles y web.",
            )
        ],
        api_endpoints=[
            EndpointSpec(
                method="POST",
                path="/api/v1/orders",
                description="Crea una orden de compra",
                request_body="{'items': [...]}",
                response_body="{'order_id': '...'}",
            )
        ],
        data_model=[
            DataModelEntity(
                name="Orden",
                attributes=["id: UUID", "total: Decimal", "created_at: DateTime"],
                relationships=["Pertenece a Usuario", "Contiene LineaItem"],
            )
        ],
        non_functional_requirements=["Latencia < 200 ms", "Disponibilidad 99.9%"],
        deployment_and_security=["Despliegue contenerizado Docker", "Autenticación JWT con RS256"],
    )

    pdf_bytes = generate_specification_pdf(spec, "Logística 2026", review_number=1)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    content = "\n".join(p.extract_text() for p in reader.pages)
    assert "Pliego de Especificaciones Técnicas" in content
    assert "API Gateway" in content
    assert "/api/v1/orders" in content
