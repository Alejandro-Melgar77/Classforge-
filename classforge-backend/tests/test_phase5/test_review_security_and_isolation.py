import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.core.errors import NotFoundError, ConflictError
from app.modules.project_reviews.service import ProjectReviewService
from app.modules.project_reviews.schemas import ProjectReviewCreateRequest
from app.modules.project_reviews.domain.models import ReviewStatus, VerdictType
from tests.test_phase5.test_pdf_upload_and_extraction import create_sample_pdf


@pytest.mark.anyio
async def test_project_isolation_documents_and_reviews():
    """Confirms documents and reviews in Project A cannot be accessed from Project B."""
    db = AsyncMongoMockClient().test_db
    service = ProjectReviewService(db)

    proj_a = str(ObjectId())
    proj_b = str(ObjectId())
    user_a = {"id": str(ObjectId()), "role": "developer"}

    # Seed projects
    await db.projects.insert_one({"_id": ObjectId(proj_a), "name": "Project A", "is_deleted": False})
    await db.projects.insert_one({"_id": ObjectId(proj_b), "name": "Project B", "is_deleted": False})

    # Upload document to Project A
    pdf_bytes = create_sample_pdf([
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\nProyecto A con suficiente texto.",
        "ESPECIFICACIÓN DE REQUISITOS\nRF-01 autenticación y roles de usuario.",
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\nArquitectura en capas y modelo de dominio.",
    ])
    doc_res = await service.upload_document(proj_a, "doc_a.pdf", pdf_bytes, user_a)
    doc_id = doc_res.id

    # Verify document is NOT accessible in Project B
    doc_in_b = await service.repo.get_document_by_id(doc_id, project_id=proj_b)
    assert doc_in_b is None

    # Run review in Project A
    rev_res = await service.create_and_run_review(
        project_id=proj_a,
        request=ProjectReviewCreateRequest(document_id=doc_id),
        current_user=user_a,
    )
    review_id = rev_res.id

    # Attempting to fetch review from Project B must fail with NotFoundError
    with pytest.raises(NotFoundError, match="no encontrada"):
        await service.get_review(project_id=proj_b, review_id=review_id)


@pytest.mark.anyio
async def test_sequential_review_numbering():
    """Validates strictly sequential review numbering (1, 2, 3...) per project."""
    db = AsyncMongoMockClient().test_db
    service = ProjectReviewService(db)

    proj_1 = str(ObjectId())
    proj_2 = str(ObjectId())
    user = {"id": str(ObjectId()), "role": "developer"}

    pdf_bytes = create_sample_pdf([
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\nProyecto base para numeración.",
        "ESPECIFICACIÓN DE REQUISITOS\nRF-01 gestión de entidades.",
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\nDiseño de clases.",
    ])

    doc_1 = await service.upload_document(proj_1, "spec1.pdf", pdf_bytes, user)
    doc_2 = await service.upload_document(proj_2, "spec2.pdf", pdf_bytes, user)

    # 3 reviews in Project 1
    r1 = await service.create_and_run_review(proj_1, ProjectReviewCreateRequest(document_id=doc_1.id), user)
    r2 = await service.create_and_run_review(proj_1, ProjectReviewCreateRequest(document_id=doc_1.id), user)
    r3 = await service.create_and_run_review(proj_1, ProjectReviewCreateRequest(document_id=doc_1.id), user)

    assert r1.review_number == 1
    assert r2.review_number == 2
    assert r3.review_number == 3

    # Review in Project 2 must start at 1
    r_p2 = await service.create_and_run_review(proj_2, ProjectReviewCreateRequest(document_id=doc_2.id), user)
    assert r_p2.review_number == 1


@pytest.mark.anyio
async def test_audit_logging_and_cancellation():
    """Verifies audit trail persistence and prevents cancellation of completed reviews."""
    db = AsyncMongoMockClient().test_db
    service = ProjectReviewService(db)

    proj_id = str(ObjectId())
    user_id = str(ObjectId())
    user = {"id": user_id, "role": "developer"}

    pdf_bytes = create_sample_pdf([
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\nSistema de auditoría de revisiones.",
        "ESPECIFICACIÓN DE REQUISITOS\nRF-01 registro inmutable de auditoría.",
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\nDiagrama de clases y arquitectura limpia.",
    ])
    doc = await service.upload_document(proj_id, "audit.pdf", pdf_bytes, user)

    review = await service.create_and_run_review(
        project_id=proj_id,
        request=ProjectReviewCreateRequest(document_id=doc.id),
        current_user=user,
    )

    # Check audit log in database
    audit_entry = await db.audit_logs.find_one({"review_id": review.id})
    assert audit_entry is not None
    assert audit_entry["action"] == "PROJECT_REVIEW_EVALUATED"
    assert audit_entry["user_id"] == user_id
    assert audit_entry["project_id"] == proj_id
    assert "verdict" in audit_entry["details"]

    # Attempting to cancel a completed review raises ConflictError
    assert review.status == ReviewStatus.COMPLETED
    with pytest.raises(ConflictError, match="No se puede cancelar"):
        await service.cancel_review(proj_id, review.id)
