"""
Repository for durable ai_jobs collection in MongoDB (P5 Bloque A).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
from pymongo import ReturnDocument

from app.ai_team.domain.jobs import AiJob

logger = logging.getLogger(__name__)


class AiJobRepository:
    """Manages persistence and atomic operations for the ai_jobs collection."""

    def __init__(self, db, clock: Optional[Callable[[], datetime]] = None):
        self.db = db
        self.col = db["ai_jobs"]
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return self._clock()

    async def enqueue(self, job: AiJob) -> Optional[AiJob]:
        """Enqueues an AI job. If a job with the same dedupe_key is queued or running,
        returns the existing job to prevent duplicates.
        """
        now = self._now()
        if job.run_after <= job.created_at:
            job.run_after = now
            job.created_at = now

        if job.dedupe_key:
            existing = await self.col.find_one({
                "dedupe_key": job.dedupe_key,
                "status": {"$in": ["queued", "running"]},
            })
            if existing:
                logger.info(f"[AiJobRepository] Dedupe hit for key '{job.dedupe_key}', skipping enqueue.")
                return AiJob.from_mongo(existing)

        doc = job.to_mongo()
        doc["created_at"] = doc.get("created_at") or now
        doc["updated_at"] = now
        await self.col.insert_one(doc)
        return job

    async def acquire_next(
        self,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> Optional[AiJob]:
        """Atomically acquires the next executable job using find_one_and_update.
        Sets status to 'running' and assigns lease_until.
        """
        now = self._now()
        lease_until = now + timedelta(seconds=lease_seconds)

        updated_doc = await self.col.find_one_and_update(
            filter={
                "status": "queued",
                "run_after": {"$lte": now},
            },
            update={
                "$set": {
                    "status": "running",
                    "lease_until": lease_until,
                    "updated_at": now,
                    "worker_id": worker_id,
                },
                "$inc": {"attempts": 1},
            },
            sort=[("run_after", 1), ("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

        if not updated_doc:
            return None
        return AiJob.from_mongo(updated_doc)

    async def complete(self, job_id: str, result_ref: Optional[Dict[str, Any]] = None) -> bool:
        """Marks a job as done."""
        now = self._now()
        update_doc: Dict[str, Any] = {
            "status": "done",
            "updated_at": now,
            "lease_until": None,
        }
        if result_ref is not None:
            update_doc["result_ref"] = result_ref

        res = await self.col.update_one({"_id": job_id}, {"$set": update_doc})
        return res.modified_count > 0 or res.matched_count > 0

    async def fail(self, job_id: str, error: str, max_attempts: int = 3) -> bool:
        """Handles job failure with exponential backoff if attempts < max_attempts."""
        now = self._now()
        job_doc = await self.col.find_one({"_id": job_id})
        if not job_doc:
            return False

        attempts = job_doc.get("attempts", 1)
        if attempts < max_attempts:
            # Exponential backoff: 5s, 10s, 20s...
            backoff_secs = (2 ** attempts) * 5
            run_after = now + timedelta(seconds=backoff_secs)
            res = await self.col.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "queued",
                        "run_after": run_after,
                        "lease_until": None,
                        "error": str(error),
                        "updated_at": now,
                    }
                },
            )
        else:
            res = await self.col.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "lease_until": None,
                        "error": str(error),
                        "updated_at": now,
                    }
                },
            )
        return res.modified_count > 0 or res.matched_count > 0

    async def reap_expired_leases(self) -> int:
        """Recovers running jobs whose lease has expired.
        If attempts >= 3, moves to 'failed'. Otherwise re-queues them.
        """
        now = self._now()
        cursor = self.col.find({
            "status": "running",
            "lease_until": {"$lt": now},
        })
        expired_jobs = await cursor.to_list(length=100)
        reaped_count = 0

        for doc in expired_jobs:
            job_id = doc["_id"]
            attempts = doc.get("attempts", 1)
            if attempts >= doc.get("max_attempts", 3):
                await self.col.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "status": "failed",
                            "error": "Lease expiró y se alcanzó el límite de intentos",
                            "lease_until": None,
                            "updated_at": now,
                        }
                    },
                )
            else:
                await self.col.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "status": "queued",
                            "lease_until": None,
                            "run_after": now + timedelta(seconds=5),
                            "updated_at": now,
                        }
                    },
                )
            reaped_count += 1

        if reaped_count > 0:
            logger.warning(f"[AiJobRepository] Reaped {reaped_count} expired job leases.")
        return reaped_count

    async def skip_stale_jobs(self, max_age_hours: int = 24) -> int:
        """Marks queued jobs older than max_age_hours as 'skipped'."""
        now = self._now()
        stale_threshold = now - timedelta(hours=max_age_hours)
        res = await self.col.update_many(
            {
                "status": "queued",
                "created_at": {"$lt": stale_threshold},
            },
            {
                "$set": {
                    "status": "skipped",
                    "error": f"Trabajo expiró sin procesar (> {max_age_hours} h)",
                    "updated_at": now,
                }
            },
        )
        return res.modified_count

    async def cancel_project_queued_jobs(self, project_id: str, origin: Optional[str] = None) -> int:
        """Instantly cancels queued jobs for a given project (e.g. when participative AI is turned off)."""
        now = self._now()
        query: Dict[str, Any] = {
            "project_id": project_id,
            "status": "queued",
        }
        if origin:
            query["origin"] = origin

        res = await self.col.update_many(
            query,
            {
                "$set": {
                    "status": "cancelled",
                    "error": "Cancelado por cambio en la configuración de IA participativa",
                    "updated_at": now,
                }
            },
        )
        if res.modified_count > 0:
            logger.info(f"[AiJobRepository] Cancelled {res.modified_count} queued jobs for project {project_id}.")
        return res.modified_count

    async def get_by_id(self, job_id: str) -> Optional[AiJob]:
        """Retrieves a single job by id."""
        doc = await self.col.find_one({"_id": job_id})
        return AiJob.from_mongo(doc) if doc else None
