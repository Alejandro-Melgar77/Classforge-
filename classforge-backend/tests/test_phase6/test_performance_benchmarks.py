import time
import numpy as np
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.modules.project_reviews.evaluator import ProjectEvaluator
from app.modules.project_reviews.pdf_extractor import ExtractedDocument, PageContent
from app.modules.project_reviews.pdf_generator import generate_review_report_pdf
from app.modules.project_reviews.domain.models import ReviewStatus, VerdictType
from app.modules.project_reviews.schemas import ProjectReviewResponse, CriterionScore
from app.modules.diagrams.repository import DiagramRepository


@pytest.mark.anyio
async def test_benchmark_rubric_evaluation_latency():
    """Benchmark the deterministic rubric evaluation pipeline (PERF-01)."""
    evaluator = ProjectEvaluator()

    realistic_spec = (
        "1. DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
        "El sistema ClassForge 2.0 busca automatizar y colaborar en el diseño de arquitectura de software UML.\n"
        "2. ESPECIFICACIÓN DE REQUISITOS DEL SOFTWARE (SRS)\n"
        "RF-01: Autenticación con JWT y control de acceso basado en roles RBAC (admin, scrum_master, dev).\n"
        "RF-02: Colaboración en tiempo real con WebSockets y bloqueo de elementos concurrentes.\n"
        "RF-03: Generación de código Spring Boot y prompts de frontend estructurados.\n"
        "3. ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
        "Diagrama de clases con User, Project, Diagram, Session, AuditLog, y relaciones 1..* y 0..1.\n"
        "4. DETALLE DE CLASES, MÉTODOS Y RESPONSABILIDADES\n"
        "Clase AuthService: login(), logout(), refreshToken(). DiagramService: create_diagram(), save_graph().\n"
        "5. MODELADO DE DATOS Y PERSISTENCIA\n"
        "Base de datos MongoDB utilizando colecciones users, projects, diagrams, sessions, y audit_logs.\n"
    )

    doc = ExtractedDocument(
        page_count=2,
        total_word_count=180,
        has_sufficient_text=True,
        pages=[
            PageContent(page_number=1, text=realistic_spec[:300], word_count=50),
            PageContent(page_number=2, text=realistic_spec[300:], word_count=130),
        ],
        detected_sections=[
            "definicion_problema_alcance",
            "requisitos_funcionales",
            "arquitectura_diagrama_clases",
            "detalle_clases_metodos",
            "modelo_datos_persistencia"
        ],
        section_pages={"definicion_problema_alcance": [1], "requisitos_funcionales": [1]},
        full_text=realistic_spec
    )

    latencies_ms = []
    # Warm-up
    _ = await evaluator.evaluate_document(doc)

    # 15 iterations
    for _ in range(15):
        t0 = time.perf_counter()
        res = await evaluator.evaluate_document(doc)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))

    print(f"\n[PERF] Rubric Evaluation -> p50: {p50:.2f}ms, p95: {p95:.2f}ms")
    assert res is not None
    assert p50 < 100.0, f"Rubric evaluation p50 too high: {p50:.2f}ms"
    assert p95 < 250.0, f"Rubric evaluation p95 too high: {p95:.2f}ms"


@pytest.mark.anyio
async def test_benchmark_pdf_report_generation():
    """Benchmark PDF report rendering generation performance (PERF-01)."""
    now = datetime.now(timezone.utc)
    review = ProjectReviewResponse(
        id="507f1f77bcf86cd799439011",
        project_id="507f1f77bcf86cd799439012",
        review_number=1,
        document_id="507f1f77bcf86cd799439013",
        document_filename="bench_spec.pdf",
        rubric_code="CF-SE-2026.1",
        rubric_version="2026.1",
        status=ReviewStatus.COMPLETED,
        verdict=VerdictType.APROBADO,
        total_score=85.0,
        passing_score=70.0,
        summary="Arquitectura sólida y verificada para producción.",
        criteria_scores=[
            CriterionScore(
                criterion_code="definicion_problema_alcance",
                name="Definición del Problema",
                weight=15.0,
                score=85.0,
                weighted_score=12.75,
                strengths=["Bien definido"],
                weaknesses=[],
                observations="OK",
                citations=[1]
            )
        ],
        strengths=["Completo"],
        weaknesses=[],
        recommendations=[],
        evaluated_by="evaluator_local",
        evaluated_at=now,
        created_at=now,
        created_by="user-benchmark"
    )

    latencies_ms = []
    for _ in range(5):
        t0 = time.perf_counter()
        pdf_bytes = generate_review_report_pdf(review, project_name="ClassForge Test Proj")
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    avg_latency = float(np.mean(latencies_ms))
    print(f"\n[PERF] PDF Report Generation -> Avg: {avg_latency:.2f}ms (size: {len(pdf_bytes)} bytes)")
    assert len(pdf_bytes) > 1000
    assert avg_latency < 500.0, f"PDF report generation too slow: {avg_latency:.2f}ms"


@pytest.mark.anyio
async def test_benchmark_diagram_save_latency():
    """Benchmark diagram repository save_graph latency and versioning (PERF-01)."""
    db = AsyncMongoMockClient().test_db
    repo = DiagramRepository(db)

    diag_id = str(ObjectId())
    user_id = str(ObjectId())

    await db.diagrams.insert_one({
        "_id": ObjectId(diag_id),
        "name": "Performance Benchmark Diagram",
        "version": 1,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False
    })

    latencies_ms = []
    current_ver = 1

    for i in range(1, 21):
        graph = {
            "nodes": [{"id": f"Class_{j}", "type": "class"} for j in range(i + 5)],
            "edges": []
        }
        t0 = time.perf_counter()
        saved = await repo.save_graph(
            diagram_id=diag_id,
            graph_data=graph,
            saved_by=user_id,
            comment=f"Iteration {i}",
            base_version=current_ver
        )
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)
        current_ver = saved["version"]

    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))

    print(f"\n[PERF] Diagram save_graph -> p50: {p50:.2f}ms, p95: {p95:.2f}ms, final version: {current_ver}")
    assert current_ver == 21
    assert p50 < 50.0, f"Diagram save p50 too high: {p50:.2f}ms"
