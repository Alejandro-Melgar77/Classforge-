import pytest
from datetime import datetime, timezone
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.modules.diagrams.repository import DiagramRepository
from app.modules.project_reviews.evaluator import ProjectEvaluator
from app.modules.project_reviews.pdf_extractor import ExtractedDocument, PageContent
from app.modules.project_reviews.pdf_generator import generate_review_report_pdf
from app.modules.project_reviews.domain.models import ReviewStatus, VerdictType
from app.modules.project_reviews.schemas import ProjectReviewResponse, CriterionScore
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.frontend_prompt_generator import generate_frontend_meta_prompt


@pytest.mark.anyio
async def test_end_to_end_project_modeling_and_evaluation_flow():
    """Validates complete end-to-end flow: modeling -> codegen -> pdf evaluation (QA-01 to QA-05)."""
    db = AsyncMongoMockClient().test_db
    repo = DiagramRepository(db)

    user_id = str(ObjectId())
    project_id = str(ObjectId())
    diag_id = str(ObjectId())

    # Step 1: User & Project context
    await db.users.insert_one({
        "_id": ObjectId(user_id),
        "name": "Integration Tester",
        "email": "tester@classforge.io",
        "role": "scrum_master",
        "is_active": True
    })

    await db.projects.insert_one({
        "_id": ObjectId(project_id),
        "name": "Enterprise Logistics Platform",
        "owner_id": user_id,
        "is_deleted": False
    })

    # Step 2: Create UML Diagram in repository with proper node types
    graph_data = {
        "nodes": [
            {
                "id": "c1",
                "type": "class",
                "data": {
                    "name": "Customer",
                    "attributes": ["- id: Long", "- email: String"],
                    "methods": ["+ register(): void"]
                }
            },
            {
                "id": "c2",
                "type": "class",
                "data": {
                    "name": "Shipment",
                    "attributes": ["- trackingNumber: String", "- status: String"],
                    "methods": ["+ updateStatus(status: String): void"]
                }
            }
        ],
        "edges": [
            {
                "id": "e1",
                "source": "c1",
                "target": "c2",
                "data": {"type": "association", "sourceMultiplicity": "1", "targetMultiplicity": "0..*"}
            }
        ]
    }

    await db.diagrams.insert_one({
        "_id": ObjectId(diag_id),
        "project_id": project_id,
        "name": "Core Domain Model",
        "version": 1,
        "graph_data": graph_data,
        "created_by": user_id,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc)
    })

    # Step 3: Codegen verification (Spring Boot & Frontend prompt)
    spring_files = generate_spring_boot_project(graph_data, package_name="com.classforge.logistics")
    assert spring_files is not None
    assert any("Customer.java" in path or "Customer" in content for path, content in spring_files.items())

    frontend_prompt = generate_frontend_meta_prompt(
        graph_data=graph_data,
        target_framework="React + Tailwind CSS"
    )
    assert "Customer" in frontend_prompt
    assert "React" in frontend_prompt

    # Step 4: AI Project Evaluation
    spec_text = (
        "[Página 1]\n"
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
        "Planteamiento del problema: necesidad de automatizar logística vehicular y envíos. "
        "Objetivo general: construir plataforma tolerante a fallos Enterprise Logistics. "
        "Alcance del proyecto: gestión de rutas, telemetría y geocercas.\n\n"
        "[Página 2]\n"
        "ESPECIFICACIÓN DE REQUISITOS\n"
        "RF-01: Registro de clientes y envíos de paquetes.\n"
        "RF-02: Transmisión de coordenadas GPS y trazabilidad en tiempo real.\n"
        "RF-03: Alerta automática por retraso en entrega.\n"
        "RNF-01: Disponibilidad 99.9% anual. RNF-02: Latencia < 200 ms.\n"
        "Casos de uso: CU-01 Registrar Envio, CU-02 Notificar Estado.\n\n"
        "[Página 3]\n"
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
        "Arquitectura multicapa Clean Architecture.\n"
        "class Customer { +id: Long, +email: String, +register(): void }\n"
        "class Shipment { +trackingNumber: String, +status: String, +updateStatus(): void }\n"
        "Relaciones: Customer 1 -- 0..* Shipment (asociación y composición).\n\n"
        "[Página 4]\n"
        "MODELO DE PERSISTENCIA Y BASE DE DATOS\n"
        "Base de datos PostgreSQL con tablas relacionales customers, shipments.\n"
        "Claves foráneas con integridad referencial e índices B-Tree.\n\n"
        "[Página 5]\n"
        "PLAN DE PRUEBAS Y ASEGURAMIENTO DE CALIDAD\n"
        "Plan de pruebas con pytest para lógica de negocio y pruebas unitarias de cálculo de rutas.\n"
        "Casos de prueba para validación de entregas.\n\n"
        "[Página 6]\n"
        "SEGURIDAD Y GESTIÓN DE RIESGOS\n"
        "Autenticación con JWT, cifrado TLS 1.3 y control de acceso basado en roles (RBAC).\n"
        "Matriz de riesgos técnicos para pérdida de conectividad."
    )

    pages = [
        PageContent(page_number=i + 1, text=block.strip(), word_count=len(block.split()))
        for i, block in enumerate(spec_text.split("[Página "))
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
            "modelo_persistencia",
            "plan_pruebas_calidad",
            "seguridad_riesgos",
        ],
        section_pages={
            "definicion_problema_alcance": [1],
            "especificacion_requisitos": [2],
            "arquitectura_diagrama_uml": [3],
            "modelo_persistencia": [4],
            "plan_pruebas_calidad": [5],
            "seguridad_riesgos": [6],
        },
        full_text=spec_text
    )

    evaluator = ProjectEvaluator()
    eval_result = await evaluator.evaluate_document(doc)
    assert eval_result is not None
    assert eval_result["total_score"] >= 70.0
    assert eval_result["verdict"].value == "APROBADO"

    # Step 5: Generate evaluation PDF report
    now = datetime.now(timezone.utc)
    review_resp = ProjectReviewResponse(
        id=str(ObjectId()),
        project_id=project_id,
        review_number=1,
        document_id=str(ObjectId()),
        document_filename="logistics_spec.pdf",
        rubric_code="CF-SE-2026.1",
        rubric_version="2026.1",
        status=ReviewStatus.COMPLETED,
        verdict=eval_result["verdict"],
        total_score=eval_result["total_score"],
        passing_score=70.0,
        summary=eval_result["summary"],
        criteria_scores=eval_result["criteria_scores"],
        strengths=[s for c in eval_result["criteria_scores"] for s in c.strengths],
        weaknesses=[w for c in eval_result["criteria_scores"] for w in c.weaknesses],
        recommendations=eval_result["recommendations"],
        evaluated_by="evaluator_local",
        evaluated_at=now,
        created_at=now,
        created_by=user_id
    )

    pdf_bytes = generate_review_report_pdf(review_resp, project_name="Enterprise Logistics Platform")
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
