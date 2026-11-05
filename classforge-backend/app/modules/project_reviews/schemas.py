from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.modules.project_reviews.domain.models import (
    VerdictType,
    ReviewStatus,
    RecommendationPriority,
    RubricCriterionDefinition,
    RubricDefinition,
)


class CriterionScore(BaseModel):
    criterion_code: str
    name: str
    weight: float
    score: float
    weighted_score: float
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    observations: str = ""
    citations: List[int] = Field(default_factory=list)
    evidence_quotes: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    priority: RecommendationPriority
    criterion_code: str
    title: str
    description: str
    action_plan: str


class ComponentSpec(BaseModel):
    name: str
    role: str
    technology: str = ""
    description: str = ""


class EndpointSpec(BaseModel):
    method: str
    path: str
    description: str
    request_body: Optional[str] = None
    response_body: Optional[str] = None


class DataModelEntity(BaseModel):
    name: str
    attributes: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)


class TechnicalSpecification(BaseModel):
    title: str
    overview: str
    functional_scope: List[str] = Field(default_factory=list)
    system_architecture: str
    components: List[ComponentSpec] = Field(default_factory=list)
    api_endpoints: List[EndpointSpec] = Field(default_factory=list)
    data_model: List[DataModelEntity] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    deployment_and_security: List[str] = Field(default_factory=list)


class ReviewDocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size_bytes: int
    content_hash: str
    page_count: int
    has_sufficient_text: bool
    detected_sections: List[str] = Field(default_factory=list)
    uploaded_by: str
    uploaded_at: datetime

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "ReviewDocumentResponse":
        if not doc:
            return None
        return cls(
            id=str(doc.get("_id")),
            project_id=str(doc.get("project_id")),
            filename=doc.get("filename", ""),
            file_size_bytes=int(doc.get("file_size_bytes", 0)),
            content_hash=doc.get("content_hash", ""),
            page_count=int(doc.get("page_count", 0)),
            has_sufficient_text=bool(doc.get("has_sufficient_text", False)),
            detected_sections=doc.get("detected_sections", []),
            uploaded_by=str(doc.get("uploaded_by")),
            uploaded_at=doc.get("uploaded_at") or datetime.utcnow(),
        )


class ProjectReviewCreateRequest(BaseModel):
    document_id: str
    rubric_code: str = "CF-SE-2026.1"
    evaluation_notes: Optional[str] = None


class ProjectReviewResponse(BaseModel):
    id: str
    project_id: str
    review_number: int
    document_id: str
    document_filename: str
    rubric_code: str
    rubric_version: str
    status: ReviewStatus
    verdict: Optional[VerdictType] = None
    total_score: Optional[float] = None
    passing_score: float = 70.0
    summary: Optional[str] = None
    criteria_scores: List[CriterionScore] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    technical_specification: Optional[TechnicalSpecification] = None
    evaluated_by_model: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    created_by: str

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "ProjectReviewResponse":
        if not doc:
            return None

        # Build CriterionScore list safely
        raw_criteria = doc.get("criteria_scores", [])
        criteria_scores = []
        if isinstance(raw_criteria, list):
            for c in raw_criteria:
                if isinstance(c, dict):
                    criteria_scores.append(CriterionScore(**c))
                elif isinstance(c, CriterionScore):
                    criteria_scores.append(c)
        elif isinstance(raw_criteria, dict):
            for k, v in raw_criteria.items():
                if isinstance(v, dict):
                    criteria_scores.append(CriterionScore(**v))

        # Build Recommendations list safely
        raw_recs = doc.get("recommendations", [])
        recommendations = []
        for r in raw_recs:
            if isinstance(r, dict):
                recommendations.append(Recommendation(**r))
            elif isinstance(r, Recommendation):
                recommendations.append(r)

        # Build TechnicalSpecification safely
        tech_spec = None
        raw_spec = doc.get("technical_specification")
        if raw_spec and isinstance(raw_spec, dict):
            tech_spec = TechnicalSpecification(**raw_spec)

        return cls(
            id=str(doc.get("_id")),
            project_id=str(doc.get("project_id")),
            review_number=int(doc.get("review_number", 1)),
            document_id=str(doc.get("document_id")),
            document_filename=doc.get("document_filename", ""),
            rubric_code=doc.get("rubric_code", "CF-SE-2026.1"),
            rubric_version=doc.get("rubric_version", "2026.1"),
            status=ReviewStatus(doc.get("status", ReviewStatus.PENDING)),
            verdict=VerdictType(doc.get("verdict")) if doc.get("verdict") else None,
            total_score=float(doc["total_score"]) if doc.get("total_score") is not None else None,
            passing_score=float(doc.get("passing_score", 70.0)),
            summary=doc.get("summary"),
            criteria_scores=criteria_scores,
            recommendations=recommendations,
            technical_specification=tech_spec,
            evaluated_by_model=doc.get("evaluated_by_model"),
            error_message=doc.get("error_message"),
            created_at=doc.get("created_at") or datetime.utcnow(),
            completed_at=doc.get("completed_at"),
            created_by=str(doc.get("created_by")),
        )
