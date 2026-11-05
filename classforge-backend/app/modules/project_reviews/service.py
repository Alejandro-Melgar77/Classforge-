import logging
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.utils import validate_object_id
from app.modules.project_reviews.domain.models import ReviewStatus, VerdictType
from app.modules.project_reviews.schemas import (
    ReviewDocumentResponse,
    ProjectReviewCreateRequest,
    ProjectReviewResponse,
)
from app.modules.project_reviews.storage import (
    save_pdf_file,
    compute_sha256,
)
from app.modules.project_reviews.pdf_extractor import (
    extract_pdf_data,
    ExtractedDocument,
    PageContent,
)
from app.modules.project_reviews.rubric import get_rubric
from app.modules.project_reviews.evaluator import ProjectEvaluator
from app.modules.project_reviews.pdf_generator import (
    generate_review_report_pdf,
    generate_specification_pdf,
)
from app.modules.project_reviews.repository import ProjectReviewRepository

logger = logging.getLogger("classforge.project_reviews.service")


class ProjectReviewService:
    """Business service coordinating document ingestion, evaluation, and reporting."""

    def __init__(self, db: Any):
        self.db = db
        self.repo = ProjectReviewRepository(db)

    async def upload_document(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        current_user: Dict[str, Any],
    ) -> ReviewDocumentResponse:
        """Processes and stores an uploaded PDF project document."""
        user_id = str(current_user.get("_id") or current_user.get("id"))
        content_hash = compute_sha256(content)

        # Extract structured content and validate PDF
        extracted = extract_pdf_data(content)

        doc_oid = ObjectId()
        doc_id_str = str(doc_oid)

        # Save binary securely to filesystem
        save_pdf_file(project_id, doc_id_str, content)

        # Prepare document metadata for persistence
        doc_data = {
            "_id": doc_oid,
            "project_id": str(project_id),
            "filename": filename or "documento_proyecto.pdf",
            "file_size_bytes": len(content),
            "content_hash": content_hash,
            "page_count": extracted.page_count,
            "has_sufficient_text": extracted.has_sufficient_text,
            "detected_sections": extracted.detected_sections,
            "section_pages": extracted.section_pages,
            "extracted_pages": [p.model_dump() for p in extracted.pages],
            "uploaded_by": user_id,
        }

        saved_doc = await self.repo.save_document(doc_data)
        return ReviewDocumentResponse.from_mongo(saved_doc)

    async def create_and_run_review(
        self,
        project_id: str,
        request: ProjectReviewCreateRequest,
        current_user: Dict[str, Any],
    ) -> ProjectReviewResponse:
        """Initiates and executes a formal evaluation of the project document."""
        user_id = str(current_user.get("_id") or current_user.get("id"))

        # Verify document existence and project isolation
        doc = await self.repo.get_document_by_id(request.document_id, project_id=project_id)
        if not doc:
            raise NotFoundError("El documento especificado no existe o no pertenece a este proyecto")

        rubric = get_rubric(request.rubric_code)

        # Create initial review record with sequential numbering
        review_oid = ObjectId()
        review_id_str = str(review_oid)
        review_number = await self.repo.get_next_review_number(project_id)

        initial_data = {
            "_id": review_oid,
            "project_id": str(project_id),
            "review_number": review_number,
            "document_id": str(doc["_id"]),
            "document_filename": doc.get("filename", ""),
            "rubric_code": rubric.code,
            "rubric_version": rubric.version,
            "status": ReviewStatus.PROCESSING.value,
            "passing_score": rubric.passing_score,
            "created_by": user_id,
        }
        await self.repo.create_review(initial_data)

        # Reconstruct ExtractedDocument from stored page data
        raw_pages = doc.get("extracted_pages", [])
        page_objects = [PageContent(**p) for p in raw_pages]
        total_words = sum(p.word_count for p in page_objects)
        full_text = "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in page_objects)

        extracted_doc = ExtractedDocument(
            page_count=doc.get("page_count", len(page_objects)),
            total_word_count=total_words,
            has_sufficient_text=doc.get("has_sufficient_text", True),
            pages=page_objects,
            detected_sections=doc.get("detected_sections", []),
            section_pages=doc.get("section_pages", {}),
            full_text=full_text,
        )

        try:
            evaluator = ProjectEvaluator(rubric)
            eval_results = await evaluator.evaluate_document(
                extracted_doc, notes=request.evaluation_notes
            )

            completed_doc = await self.repo.complete_review(review_id_str, eval_results)

            # Record audit event
            await self.repo.record_audit_log(
                user_id=user_id,
                project_id=project_id,
                review_id=review_id_str,
                action="PROJECT_REVIEW_EVALUATED",
                details={
                    "review_number": review_number,
                    "verdict": eval_results["verdict"].value if hasattr(eval_results["verdict"], "value") else str(eval_results["verdict"]),
                    "total_score": eval_results["total_score"],
                    "document_id": str(doc["_id"]),
                },
            )

            return ProjectReviewResponse.from_mongo(completed_doc)

        except Exception as e:
            logger.error("Error durante la evaluación de la revisión %s: %s", review_id_str, e, exc_info=True)
            await self.repo.update_review_status(review_id_str, ReviewStatus.FAILED, error_message=str(e))
            failed_doc = await self.repo.get_review_by_id(review_id_str, project_id=project_id)
            return ProjectReviewResponse.from_mongo(failed_doc)

    async def get_review(
        self,
        project_id: str,
        review_id: str,
    ) -> ProjectReviewResponse:
        """Retrieves a single review record enforcing project isolation."""
        doc = await self.repo.get_review_by_id(review_id, project_id=project_id)
        if not doc:
            raise NotFoundError("Evaluación no encontrada en este proyecto")
        return ProjectReviewResponse.from_mongo(doc)

    async def list_reviews(
        self,
        project_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ProjectReviewResponse], int]:
        """Lists reviews for a project ordered chronologically."""
        skip = (page - 1) * limit
        items, total = await self.repo.list_reviews_for_project(project_id, skip=skip, limit=limit)
        return [ProjectReviewResponse.from_mongo(i) for i in items], total

    async def cancel_review(
        self,
        project_id: str,
        review_id: str,
    ) -> ProjectReviewResponse:
        """Cancels an in-progress or pending review."""
        review = await self.repo.get_review_by_id(review_id, project_id=project_id)
        if not review:
            raise NotFoundError("Evaluación no encontrada")

        current_status = review.get("status")
        if current_status in (ReviewStatus.COMPLETED.value, ReviewStatus.FAILED.value):
            raise ConflictError("No se puede cancelar una revisión que ya ha finalizado")

        await self.repo.update_review_status(review_id, ReviewStatus.CANCELLED)
        updated = await self.repo.get_review_by_id(review_id, project_id=project_id)
        return ProjectReviewResponse.from_mongo(updated)

    async def download_report_pdf(
        self,
        project_id: str,
        review_id: str,
    ) -> bytes:
        """Generates downloadable PDF report for a completed review."""
        review_resp = await self.get_review(project_id, review_id)
        if review_resp.status != ReviewStatus.COMPLETED:
            raise ValidationError("El informe PDF solo está disponible cuando la evaluación ha finalizado exitosamente")

        # Fetch project name
        proj_oid = validate_object_id(project_id, "project_id")
        project = await self.db["projects"].find_one({"_id": proj_oid})
        project_name = project.get("name", "Proyecto") if project else "Proyecto"

        return generate_review_report_pdf(review_resp, project_name)

    async def download_specification_pdf(
        self,
        project_id: str,
        review_id: str,
    ) -> bytes:
        """Generates downloadable Technical Specification PDF for an approved review."""
        review_resp = await self.get_review(project_id, review_id)
        if review_resp.status != ReviewStatus.COMPLETED:
            raise ValidationError("El pliego de especificaciones solo está disponible para evaluaciones completadas")

        if review_resp.verdict != VerdictType.APROBADO or not review_resp.technical_specification:
            raise ValidationError("El pliego de especificaciones técnicas solo está disponible para proyectos con dictamen APROBADO")

        proj_oid = validate_object_id(project_id, "project_id")
        project = await self.db["projects"].find_one({"_id": proj_oid})
        project_name = project.get("name", "Proyecto") if project else "Proyecto"

        return generate_specification_pdf(
            review_resp.technical_specification, project_name, review_resp.review_number
        )
