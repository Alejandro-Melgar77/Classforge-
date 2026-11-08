from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    Query,
    Header,
    Response,
    Path as FPath,
)

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.authz import require_project_member
from app.core.errors import ValidationError
from app.modules.auth.schemas import StandardResponse
from app.modules.project_reviews.schemas import (
    ProjectReviewCreateRequest,
    LocalAiChatRequest,
    LocalAiChatResponse,
)
from app.modules.project_reviews.service import ProjectReviewService
from app.modules.project_reviews.rubric import list_available_rubrics, get_rubric

# Project-scoped router: /api/v1/projects/{project_id}/reviews
router = APIRouter()

# Global project-reviews router: /api/v1/project-reviews
global_router = APIRouter()

# Project-scoped local-ai router: /api/v1/projects/{project_id}/local-ai
local_ai_router = APIRouter()


def get_review_service(db=Depends(get_db)) -> ProjectReviewService:
    return ProjectReviewService(db)


# ── Global Endpoints (Rubrics Catalog) ────────────────────────────────────────

@global_router.get("/rubrics", response_model=StandardResponse)
async def get_rubrics():
    """Returns all available evaluation rubrics and their criteria definitions."""
    rubrics = list_available_rubrics()
    return StandardResponse(
        success=True,
        message="Rúbricas disponibles recuperadas",
        data=[r.model_dump() for r in rubrics],
    )


@global_router.get("/rubrics/{rubric_code}", response_model=StandardResponse)
async def get_single_rubric(rubric_code: str = FPath(...)):
    """Returns details for a specific evaluation rubric."""
    rubric = get_rubric(rubric_code)
    return StandardResponse(
        success=True,
        message="Rúbrica técnica recuperada",
        data=rubric.model_dump(),
    )


# ── Project Scoped Review Endpoints ───────────────────────────────────────────

@router.post("/upload", response_model=StandardResponse)
async def upload_project_document(
    project_id: str = FPath(..., description="ID del proyecto"),
    file: UploadFile = File(..., description="Archivo PDF de documentación del proyecto"),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Uploads and analyzes a PDF project specification or thesis document."""
    if not file.filename.lower().endswith(".pdf"):
        raise ValidationError("El archivo debe tener extensión .pdf")

    content = await file.read()
    doc_res = await service.upload_document(
        project_id=project_id,
        filename=file.filename,
        content=content,
        current_user=current_user,
    )
    return StandardResponse(
        success=True,
        message="Documento procesado y registrado correctamente",
        data=doc_res.model_dump(),
    )


@router.post("", response_model=StandardResponse, include_in_schema=False)
@router.post("/", response_model=StandardResponse)
async def create_project_review(
    project_id: str = FPath(...),
    request: ProjectReviewCreateRequest = ...,
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Runs a formal local AI evaluation of an uploaded project document."""
    review = await service.create_and_run_review(
        project_id=project_id,
        request=request,
        current_user=current_user,
    )
    return StandardResponse(
        success=True,
        message="Evaluación técnica completada exitosamente",
        data=review.model_dump(),
    )


@local_ai_router.post("/evaluate-and-chat", response_model=StandardResponse)
@router.post("/local-ai/evaluate-and-chat", response_model=StandardResponse)
async def evaluate_and_chat_local_ai(
    project_id: str = FPath(...),
    request: LocalAiChatRequest = ...,
    x_local_ai_url: Optional[str] = Header(None, alias="X-Local-AI-Url"),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """
    Evaluates live project UML 2.5+ diagrams and chats with Local AI (classforge-local-1.7b)
    without requiring or generating any PDF files.
    """
    result = await service.evaluate_and_chat_local_ai(
        project_id=project_id,
        request=request,
        current_user=current_user,
        tunnel_url=x_local_ai_url,
    )
    return StandardResponse(
        success=True,
        message="Evaluación e interacción completadas exitosamente",
        data={
            "verdict": result["verdict"].value if hasattr(result["verdict"], "value") else str(result["verdict"]),
            "total_score": result["total_score"],
            "passing_score": result["passing_score"],
            "summary": result["summary"],
            "criteria_scores": [c.model_dump() for c in result["criteria_scores"]],
            "technical_specification": result["technical_specification"].model_dump() if result["technical_specification"] else None,
            "required_improvements": result["required_improvements"],
            "assistant_message": result["assistant_message"],
            "evaluated_by_model": result["evaluated_by_model"],
            "latency_ms": result["latency_ms"],
            "diagram_id": result.get("diagram_id"),
            "diagram_name": result.get("diagram_name"),
        },
    )


@router.get("", response_model=StandardResponse, include_in_schema=False)
@router.get("/", response_model=StandardResponse)
async def list_project_reviews(
    project_id: str = FPath(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Lists all previous evaluations for this project ordered by review number descending."""
    items, total = await service.list_reviews(project_id=project_id, page=page, limit=limit)
    return StandardResponse(
        success=True,
        message="Evaluaciones recuperadas",
        data={
            "items": [i.model_dump() for i in items],
            "total": total,
            "page": page,
            "limit": limit,
        },
    )


@router.get("/{review_id}", response_model=StandardResponse)
async def get_project_review_detail(
    project_id: str = FPath(...),
    review_id: str = FPath(...),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Retrieves full details, scores, findings and recommendations of a review."""
    review = await service.get_review(project_id=project_id, review_id=review_id)
    return StandardResponse(
        success=True,
        message="Detalle de evaluación técnica recuperado",
        data=review.model_dump(),
    )


@router.post("/{review_id}/cancel", response_model=StandardResponse)
async def cancel_project_review(
    project_id: str = FPath(...),
    review_id: str = FPath(...),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Cancels an in-progress or queued evaluation."""
    review = await service.cancel_review(project_id=project_id, review_id=review_id)
    return StandardResponse(
        success=True,
        message="Evaluación cancelada exitosamente",
        data=review.model_dump(),
    )


@router.get("/{review_id}/report.pdf")
async def download_review_report_pdf(
    project_id: str = FPath(...),
    review_id: str = FPath(...),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Generates and downloads the official evaluation report in PDF format."""
    pdf_bytes = await service.download_report_pdf(project_id=project_id, review_id=review_id)
    filename = f"dictamen_evaluacion_{project_id}_{review_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get("/{review_id}/specification.pdf")
async def download_review_specification_pdf(
    project_id: str = FPath(...),
    review_id: str = FPath(...),
    project=Depends(require_project_member),
    current_user=Depends(get_current_user),
    service: ProjectReviewService = Depends(get_review_service),
):
    """Generates and downloads the Technical Specification document in PDF format."""
    pdf_bytes = await service.download_specification_pdf(project_id=project_id, review_id=review_id)
    filename = f"pliego_especificaciones_{project_id}_{review_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )
