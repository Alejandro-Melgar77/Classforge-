"""
Repository for tracking the lifecycle of AI findings in MongoDB (P5 Bloque C).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.ai_team.domain.lint import Finding
from app.ai_team.domain.findings import AiFinding, compute_finding_fingerprint

logger = logging.getLogger(__name__)


class AiFindingsRepository:
    """Manages the ai_findings collection and life-cycle transitions."""

    def __init__(self, db, clock: Optional[Callable[[], datetime]] = None):
        self.db = db
        self.col = db["ai_findings"]
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return self._clock()

    async def sync_linter_findings(
        self,
        project_id: str,
        diagram_id: str,
        findings: List[Finding],
        role_id: str = "qa",
        message_id: Optional[str] = None,
    ) -> Tuple[List[AiFinding], List[AiFinding]]:
        """Synchronizes deterministic linter output with persistent ai_findings.
        
        Transitions:
        - New finding detected -> insert with status 'open'
        - Previously open finding still present -> update 'last_seen'
        - Previously open/acknowledged finding NO LONGER detected -> transition to 'resolved'
        
        Returns:
            Tuple of (newly_opened_findings, newly_resolved_findings)
        """
        now = self._now()
        current_fingerprints: Dict[str, Finding] = {}
        for f in findings:
            fp = compute_finding_fingerprint(f.rule, f.element_ids)
            current_fingerprints[fp] = f

        # Retrieve currently open or acknowledged findings for this diagram
        cursor = self.col.find({
            "project_id": project_id,
            "diagram_id": diagram_id,
            "status": {"$in": ["open", "acknowledged"]},
        })
        existing_docs = await cursor.to_list(length=200)
        existing_by_fp = {doc["fingerprint"]: doc for doc in existing_docs}

        newly_opened: List[AiFinding] = []
        newly_resolved: List[AiFinding] = []

        # 1. Update or create current findings
        for fp, f in current_fingerprints.items():
            if fp in existing_by_fp:
                # Existing finding: touch last_seen
                await self.col.update_one(
                    {"_id": existing_by_fp[fp]["_id"]},
                    {"$set": {"last_seen": now}},
                )
            else:
                # Brand new finding
                new_finding = AiFinding(
                    project_id=project_id,
                    diagram_id=diagram_id,
                    fingerprint=fp,
                    rule=f.rule,
                    role_id=role_id,
                    severity=f.severity,
                    element_ids=f.element_ids,
                    status="open",
                    first_seen=now,
                    last_seen=now,
                    message_id=message_id,
                )
                await self.col.insert_one(new_finding.to_mongo())
                newly_opened.append(new_finding)

        # 2. Check for resolved findings (was open/acknowledged, but not detected in this run)
        for fp, doc in existing_by_fp.items():
            if fp not in current_fingerprints:
                await self.col.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "status": "resolved",
                            "resolved_at": now,
                            "updated_at": now,
                        }
                    },
                )
                doc["status"] = "resolved"
                doc["resolved_at"] = now
                newly_resolved.append(AiFinding.from_mongo(doc))

        return newly_opened, newly_resolved

    async def acknowledge_finding(self, finding_id: str, user_id: str) -> bool:
        """Transitions a finding to 'acknowledged' by a team member."""
        now = self._now()
        res = await self.col.update_one(
            {"_id": finding_id, "status": "open"},
            {
                "$set": {
                    "status": "acknowledged",
                    "acknowledged_by": user_id,
                    "updated_at": now,
                }
            },
        )
        return res.modified_count > 0

    async def dismiss_finding(self, finding_id: str, user_id: str) -> bool:
        """Transitions a finding to 'dismissed' by a team member."""
        now = self._now()
        res = await self.col.update_one(
            {"_id": finding_id, "status": {"$in": ["open", "acknowledged"]}},
            {
                "$set": {
                    "status": "dismissed",
                    "dismissed_by": user_id,
                    "updated_at": now,
                }
            },
        )
        return res.modified_count > 0

    async def list_findings(
        self,
        project_id: str,
        diagram_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[AiFinding]:
        """Lists findings filtered by project, diagram, and status."""
        q: Dict[str, Any] = {"project_id": project_id}
        if diagram_id:
            q["diagram_id"] = diagram_id
        if status:
            q["status"] = status

        cursor = self.col.find(q).sort("last_seen", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [AiFinding.from_mongo(d) for d in docs]

    async def get_by_id(self, finding_id: str) -> Optional[AiFinding]:
        """Gets a finding by its ID."""
        doc = await self.col.find_one({"_id": finding_id})
        return AiFinding.from_mongo(doc) if doc else None
