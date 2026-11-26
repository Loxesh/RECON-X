
"""Transactional human review and approval service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.governance.approval_workflow import (
    ApprovalWorkflowError,
    request_fingerprint,
    validate_decision,
)
from app.governance.audit_logger import AuditLogger
from app.governance.audit_repository import AuditChainError, AuditRepository
from app.models.enums import ApprovalDecision


class ReviewService:
    """Manage tenant-scoped human approval decisions."""

    TERMINAL_STATUSES = {
        ApprovalDecision.APPROVE: "APPROVED",
        ApprovalDecision.REJECT: "REJECTED",
    }

    def __init__(self, database, org_id: str):
        if not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("A valid organisation ID is required.")

        self.database = database
        self.org_id = org_id.strip()
        self.exceptions = database["exceptions"]
        self.approvals = database["approvals"]
        self.audit_logger = AuditLogger(
            AuditRepository(database, self.org_id)
        )

    @staticmethod
    def _serialize(document: dict) -> dict:
        result = dict(document)
        if "_id" in result:
            result["id"] = str(result.pop("_id"))
        return result

    def list_queue(self, *, skip: int = 0, limit: int = 50) -> list[dict]:
        if skip < 0 or limit < 1 or limit > 100:
            raise HTTPException(422, "Invalid pagination values.")

        cursor = (
            self.exceptions.find(
                {
                    "org_id": self.org_id,
                    "review_required": True,
                },
                {"org_id": 0},
            )
            .sort("created_at", 1)
            .skip(skip)
            .limit(limit)
        )

        return [self._serialize(item) for item in cursor]

    def get_review(self, exception_id: str) -> dict:
        if not ObjectId.is_valid(exception_id):
            raise HTTPException(404, "Review not found.")

        document = self.exceptions.find_one(
            {
                "_id": ObjectId(exception_id),
                "org_id": self.org_id,
            },
            {"org_id": 0},
        )

        if document is None:
            raise HTTPException(404, "Review not found.")

        return self._serialize(document)

    def decide(
        self,
        *,
        exception_id: str,
        decision: ApprovalDecision,
        reviewer_id: str,
        reviewer_roles: list[str],
        idempotency_key: str,
        comment: str | None,
        after: dict[str, Any] | None,
        correlation_id: str,
    ) -> dict:
        if not ObjectId.is_valid(exception_id):
            raise HTTPException(404, "Review not found.")

        if (
            not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
            or len(idempotency_key) > 128
        ):
            raise HTTPException(422, "Invalid idempotency key.")

        try:
            validate_decision(decision, comment, after)
        except ApprovalWorkflowError as exc:
            raise HTTPException(422, str(exc)) from None

        fingerprint = request_fingerprint(
            exception_id=exception_id,
            decision=decision,
            comment=comment,
            after=after,
        )

        exception_oid = ObjectId(exception_id)
        now = datetime.now(timezone.utc)

        reviewer_role = next(
            (
                role
                for role in reviewer_roles
                if role in {"org_admin", "finance_analyst"}
            ),
            None,
        )

        if reviewer_role is None:
            raise HTTPException(403, "Reviewer permission is required.")

        def transaction(session):
            existing = self.approvals.find_one(
                {
                    "org_id": self.org_id,
                    "exception_id": exception_id,
                    "idempotency_key": idempotency_key,
                },
                session=session,
            )

            if existing is not None:
                if existing.get("request_fingerprint") != fingerprint:
                    raise HTTPException(
                        409,
                        "Idempotency key was already used for another request.",
                    )

                result = self._serialize(existing)
                result["replayed"] = True
                return result

            exception = self.exceptions.find_one(
                {
                    "_id": exception_oid,
                    "org_id": self.org_id,
                    "review_required": True,
                    "status": "OPEN",
                },
                session=session,
            )

            if exception is None:
                raise HTTPException(
                    409,
                    "Review is no longer available for a decision.",
                )

            status_before = exception.get("status", "OPEN")
            review_required_before = exception.get("review_required", True)

            if decision == ApprovalDecision.MODIFY:
                status_after = status_before
                review_required_after = True
            else:
                status_after = self.TERMINAL_STATUSES[decision]
                review_required_after = False

            before = {
                "status": status_before,
                "review_required": review_required_before,
            }
            after_snapshot = after or {}

            update_fields = {
                "review_required": review_required_after,
                "updated_at": now,
            }

            update_operations: dict[str, Any] = {
                "$set": update_fields,
            }

            if status_after != status_before:
                update_operations["$set"]["status"] = status_after
                update_operations["$push"] = {
                    "status_history": {
                        "status": status_after,
                        "changed_by": reviewer_id,
                        "changed_at": now,
                        "comment": comment,
                    }
                }

            update = self.exceptions.update_one(
                {
                    "_id": exception_oid,
                    "org_id": self.org_id,
                    "status": "OPEN",
                    "review_required": True,
                },
                update_operations,
                session=session,
            )

            if update.modified_count != 1:
                raise HTTPException(
                    409,
                    "Another reviewer has already decided this item.",
                )

            approval = {
                "org_id": self.org_id,
                "job_id": str(exception["job_id"]),
                "exception_id": exception_id,
                "decision": decision.value,
                "reviewer_id": reviewer_id,
                "reviewer_role": reviewer_role,
                "comment": comment,
                "before": before,
                "after": after_snapshot,
                "idempotency_key": idempotency_key,
                "request_fingerprint": fingerprint,
                "decided_at": now,
                "policy_snapshot": {
                    "exception_status_before": status_before,
                    "exception_status_after": status_after,
                    "review_required_before": review_required_before,
                    "review_required_after": review_required_after,
                },
                "created_at": now,
                "updated_at": now,
                "schema_version": 1,
            }

            inserted = self.approvals.insert_one(
                approval,
                session=session,
            )
            approval["_id"] = inserted.inserted_id

            self.audit_logger.log(
                event_type="HUMAN_REVIEW_DECISION",
                actor={
                    "actor_id": reviewer_id,
                    "actor_type": "USER",
                },
                resource={
                    "resource_type": "EXCEPTION",
                    "resource_id": exception_id,
                },
                action=decision.value.upper(),
                outcome="SUCCESS",
                correlation_id=correlation_id,
                details={
                    "approval_id": str(inserted.inserted_id),
                    "reviewer_role": reviewer_role,
                    "comment_present": comment is not None,
                    "idempotency_key": idempotency_key,
                    "exception_status_before": status_before,
                    "exception_status_after": status_after,
                    "review_required_after": review_required_after,
                    "proposal_present": decision == ApprovalDecision.MODIFY,
                },
                timestamp=now,
                session=session,
            )

            return self._serialize(approval)

        try:
            with self.database.client.start_session() as session:
                return session.with_transaction(transaction)

        except HTTPException:
            raise

        except DuplicateKeyError:
            raise HTTPException(
                409,
                "A conflicting review decision already exists.",
            ) from None

        except (AuditChainError, PyMongoError):
            raise HTTPException(
                503,
                "The review decision could not be committed.",
            ) from None
