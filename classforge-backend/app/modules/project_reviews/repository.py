from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.core.utils import validate_object_id
from app.modules.project_reviews.domain.models import ReviewStatus


class ProjectReviewRepository:
    """Repository handling persistence for project review documents, runs, and audit logs."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.documents_col = db["review_documents"]
        self.reviews_col = db["project_reviews"]
        self.audit_col = db["audit_logs"]

    # ── Document Persistence ──────────────────────────────────────────────────

    async def save_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves extracted metadata and text structure of an uploaded PDF."""
        doc = dict(data)
        doc.setdefault("_id", ObjectId())
        doc["uploaded_at"] = doc.get("uploaded_at") or datetime.now(timezone.utc)
        await self.documents_col.insert_one(doc)
        return doc

    async def get_document_by_id(
        self, document_id: str, project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Finds document by ID, enforcing project isolation when project_id is provided."""
        doc_oid = validate_object_id(document_id, "document_id")
        query: Dict[str, Any] = {"_id": doc_oid}
        if project_id:
            query["project_id"] = str(project_id)
        return await self.documents_col.find_one(query)

    async def get_document_by_hash(self, content_hash: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Finds existing document with identical content hash within the same project."""
        return await self.documents_col.find_one(
            {"project_id": str(project_id), "content_hash": content_hash}
        )

    async def list_documents_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Lists all uploaded review documents for a given project."""
        cursor = self.documents_col.find({"project_id": str(project_id)}).sort("uploaded_at", -1)
        return await cursor.to_list(length=100)

    # ── Review Persistence ────────────────────────────────────────────────────

    async def get_next_review_number(self, project_id: str) -> int:
        """Determines the next sequential review number (1, 2, 3...) for a project."""
        latest = await self.reviews_col.find_one(
            {"project_id": str(project_id)},
            sort=[("review_number", -1)],
        )
        if latest and "review_number" in latest:
            return int(latest["review_number"]) + 1
        return 1

    async def create_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new evaluation record with sequential numbering."""
        review_data = dict(data)
        review_data.setdefault("_id", ObjectId())
        project_id = str(review_data["project_id"])

        if "review_number" not in review_data:
            review_data["review_number"] = await self.get_next_review_number(project_id)

        now = datetime.now(timezone.utc)
        review_data["created_at"] = review_data.get("created_at") or now
        review_data["status"] = review_data.get("status", ReviewStatus.PENDING.value)

        await self.reviews_col.insert_one(review_data)
        return review_data

    async def get_review_by_id(
        self, review_id: str, project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Finds a review by ID, enforcing project isolation when project_id is provided."""
        rev_oid = validate_object_id(review_id, "review_id")
        query: Dict[str, Any] = {"_id": rev_oid}
        if project_id:
            query["project_id"] = str(project_id)
        return await self.reviews_col.find_one(query)

    async def list_reviews_for_project(
        self, project_id: str, skip: int = 0, limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Returns paginated list of reviews for a project ordered chronologically descending."""
        query = {"project_id": str(project_id)}
        total = await self.reviews_col.count_documents(query)
        cursor = self.reviews_col.find(query).sort("review_number", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        return items, total

    async def update_review_status(
        self,
        review_id: str,
        status: ReviewStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Updates review status."""
        rev_oid = validate_object_id(review_id, "review_id")
        update_fields: Dict[str, Any] = {"status": status.value}
        if error_message is not None:
            update_fields["error_message"] = error_message
        if status in (ReviewStatus.COMPLETED, ReviewStatus.FAILED, ReviewStatus.CANCELLED):
            update_fields["completed_at"] = datetime.now(timezone.utc)

        result = await self.reviews_col.update_one({"_id": rev_oid}, {"$set": update_fields})
        return result.modified_count > 0

    async def complete_review(
        self, review_id: str, results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Persists final evaluation scores, findings, recommendations, and specs."""
        rev_oid = validate_object_id(review_id, "review_id")
        now = datetime.now(timezone.utc)

        update_fields: Dict[str, Any] = {
            "status": ReviewStatus.COMPLETED.value,
            "verdict": results["verdict"].value if hasattr(results["verdict"], "value") else str(results["verdict"]),
            "total_score": results["total_score"],
            "passing_score": results["passing_score"],
            "summary": results["summary"],
            "criteria_scores": [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in results.get("criteria_scores", [])
            ],
            "recommendations": [
                r.model_dump() if hasattr(r, "model_dump") else r
                for r in results.get("recommendations", [])
            ],
            "technical_specification": (
                results["technical_specification"].model_dump()
                if hasattr(results.get("technical_specification"), "model_dump")
                else results.get("technical_specification")
            ),
            "evaluated_by_model": results.get("evaluated_by_model"),
            "completed_at": now,
        }

        updated = await self.reviews_col.find_one_and_update(
            {"_id": rev_oid},
            {"$set": update_fields},
            return_document=True,
        )
        return updated

    async def record_audit_log(
        self,
        user_id: str,
        project_id: str,
        review_id: str,
        action: str,
        details: Dict[str, Any],
    ) -> None:
        """Records an immutable audit event in audit_logs collection."""
        log_entry = {
            "user_id": str(user_id),
            "project_id": str(project_id),
            "review_id": str(review_id),
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        }
        await self.audit_col.insert_one(log_entry)
