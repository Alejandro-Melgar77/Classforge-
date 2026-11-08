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
    LocalAiChatRequest,
    LocalAiChatResponse,
)
from app.ai_team.domain.diagram_model import from_graph_data, Diagram
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

    async def evaluate_and_chat_local_ai(
        self,
        project_id: str,
        request: LocalAiChatRequest,
        current_user: Dict[str, Any],
        tunnel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs local AI evaluation and interactive conversation on project UML diagrams.
        Zero PDF dependency: directly pulls live UML 2.5+ models from MongoDB.
        """
        user_id = str(current_user.get("_id") or current_user.get("id"))
        effective_tunnel_url = request.tunnel_url or tunnel_url

        # 1. Fetch project info
        pid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        project = await self.db["projects"].find_one({"_id": pid})
        project_name = project.get("name", "Proyecto ClassForge") if project else "Proyecto ClassForge"

        # 2. Fetch target diagram(s)
        diagram_doc = None
        if request.diagram_id:
            did = ObjectId(request.diagram_id) if ObjectId.is_valid(request.diagram_id) else request.diagram_id
            diagram_doc = await self.db["diagrams"].find_one({
                "_id": did,
                "project_id": {"$in": [pid, str(project_id)]},
                "is_deleted": {"$ne": True},
            })

        if not diagram_doc:
            # Fallback: get first or all diagrams of project
            cursor = self.db["diagrams"].find({
                "project_id": {"$in": [pid, str(project_id)]},
                "is_deleted": {"$ne": True},
            }).sort("updated_at", -1)
            diagrams_list = await cursor.to_list(length=10)
            if diagrams_list:
                diagram_doc = diagrams_list[0]

        # 3. Build canonical Diagram
        if diagram_doc:
            raw_content = diagram_doc.get("content") or diagram_doc.get("graph_data") or {}
            canonical_diagram = from_graph_data(raw_content)
            canonical_diagram.id = str(diagram_doc["_id"])
            canonical_diagram.name = diagram_doc.get("name", "Diagrama Principal")
        else:
            canonical_diagram = Diagram(name=f"Diagrama de {project_name}")

        # 4. Run evaluation with evaluator
        evaluator = ProjectEvaluator()
        history_dicts = [{"role": m.role, "content": m.content} for m in request.session_history]
        result = await evaluator.evaluate_uml_diagram(
            diagram=canonical_diagram,
            user_message=request.message,
            session_history=history_dicts,
            tunnel_url=effective_tunnel_url,
            project_name=project_name,
        )

        # 5. Persist review into database if this is an evaluation request
        try:
            review_oid = ObjectId()
            review_number = await self.repo.get_next_review_number(project_id)
            review_doc = {
                "_id": review_oid,
                "project_id": str(project_id),
                "review_number": review_number,
                "document_id": canonical_diagram.id or "uml-live-diagram",
                "document_filename": f"UML: {canonical_diagram.name}",
                "rubric_code": evaluator.rubric.code,
                "rubric_version": evaluator.rubric.version,
                "status": ReviewStatus.COMPLETED.value,
                "verdict": result["verdict"].value,
                "total_score": result["total_score"],
                "passing_score": evaluator.rubric.passing_score,
                "summary": result["summary"],
                "criteria_scores": [c.model_dump() for c in result["criteria_scores"]],
                "recommendations": [
                    {
                        "priority": "HIGH",
                        "criterion_code": "arquitectura_diagrama_uml",
                        "title": imp,
                        "description": imp,
                        "action_plan": f"Actualizar el lienzo UML para corregir: {imp}",
                    }
                    for imp in result["required_improvements"]
                ],
                "technical_specification": result["technical_specification"].model_dump() if result["technical_specification"] else None,
                "evaluated_by_model": result["evaluated_by_model"],
                "created_by": user_id,
            }
            await self.repo.create_review(review_doc)
        except Exception as e:
            logger.warning(f"[ProjectReviewService] No se pudo persistir registro en project_reviews ({e})")

        return result
