"""Tenant-scoped historical retrieval through existing repositories."""

import asyncio
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.knowledge.schemas import (
    ResearchQuery,
    ResearchRecord,
    ResearchToolResult,
)
from app.repositories.tenant_collections import (
    ExceptionRepository,
    ReconciliationJobRepository,
)


def _id_string(value: Any) -> str:
    return str(value)


class ResearchKnowledgeService:
    """Read-only retrieval of historical tenant-owned evidence."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_prior_exceptions(
        self,
        query: ResearchQuery,
    ) -> ResearchToolResult:
        repository = ExceptionRepository(
            self._database,
            query.org_id,
        )

        documents = await asyncio.to_thread(
            repository.list,
            {"job_id": {"$ne": query.current_job_id}},
            limit=query.limit,
            sort=[("created_at", -1)],
        )

        records = []

        for document in documents:
            record_id = _id_string(document["_id"])

            records.append(
                ResearchRecord(
                    record_id=record_id,
                    record_type="EXCEPTION",
                    job_id=document.get("job_id"),
                    summary=str(document.get("summary", "Historical exception")),
                    occurred_at=document.get("created_at"),
                    citation=f"exceptions/{record_id}",
                    details={
                        "type": document.get("type"),
                        "severity": document.get("severity"),
                        "status": document.get("status"),
                        "review_required": document.get("review_required"),
                        "evidence": document.get("evidence", {}),
                    },
                )
            )

        return ResearchToolResult(records=records)

    async def list_prior_jobs(
        self,
        query: ResearchQuery,
    ) -> ResearchToolResult:
        repository = ReconciliationJobRepository(
            self._database,
            query.org_id,
        )

        filters: dict[str, Any] = {}

        if ObjectId.is_valid(query.current_job_id):
            filters["_id"] = {"$ne": ObjectId(query.current_job_id)}

        documents = await asyncio.to_thread(
            repository.list,
            filters,
            limit=query.limit,
            sort=[("created_at", -1)],
        )

        records = []

        for document in documents:
            record_id = _id_string(document["_id"])

            records.append(
                ResearchRecord(
                    record_id=record_id,
                    record_type="RECONCILIATION_JOB",
                    job_id=record_id,
                    summary=str(document.get("name", "Historical reconciliation job")),
                    occurred_at=document.get("created_at"),
                    citation=f"reconciliation_jobs/{record_id}",
                    details={
                        "status": document.get("status"),
                        "period": document.get("period", {}),
                        "stats": document.get("stats", {}),
                    },
                )
            )

        return ResearchToolResult(records=records)

    async def list_rule_history(
        self,
        query: ResearchQuery,
    ) -> ResearchToolResult:
        repository = ReconciliationJobRepository(
            self._database,
            query.org_id,
        )

        filters: dict[str, Any] = {}

        if ObjectId.is_valid(query.current_job_id):
            filters["_id"] = {"$ne": ObjectId(query.current_job_id)}

        documents = await asyncio.to_thread(
            repository.list,
            filters,
            limit=query.limit,
            sort=[("created_at", -1)],
        )

        records = []

        for document in documents:
            snapshot = document.get("rules_snapshot") or {}

            if not snapshot:
                continue

            record_id = _id_string(document["_id"])

            records.append(
                ResearchRecord(
                    record_id=record_id,
                    record_type="RULE_HISTORY",
                    job_id=record_id,
                    summary="Historical reconciliation rules snapshot",
                    occurred_at=document.get("created_at"),
                    citation=f"reconciliation_jobs/{record_id}/rules_snapshot",
                    details={"rules_snapshot": snapshot},
                )
            )

        return ResearchToolResult(records=records)