
"""Human review queue, evidence and decision API."""

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.deps.auth_deps import require_permission
from app.core.exceptions import get_request_id
from app.core.permissions import Permission
from app.models.enums import ApprovalDecision
from app.schemas.review import (
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewDetailResponse,
    ReviewQueueItem,
)
from app.services.review_service import ReviewService


router = APIRouter(prefix="/reviews", tags=["Human Reviews"])


def _service(request: Request, current_user: dict) -> ReviewService:
    database = getattr(request.app.state, "mongodb_database", None)

    if database is None:
        from fastapi import HTTPException

        raise HTTPException(503, "Database is unavailable.")

    org_id = current_user.get("org_id")
    if not isinstance(org_id, str) or not org_id:
        from fastapi import HTTPException

        raise HTTPException(403, "Organisation context is unavailable.")

    return ReviewService(database, org_id)


@router.get(
    "",
    response_model=list[ReviewQueueItem],
    summary="List pending human reviews",
)
def list_reviews(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(
        require_permission(Permission.REVIEWS_READ.value)
    ),
):
    return _service(request, current_user).list_queue(
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{exception_id}",
    response_model=ReviewDetailResponse,
    summary="View exception evidence for human review",
)
def get_review(
    exception_id: str,
    request: Request,
    current_user: dict = Depends(
        require_permission(Permission.REVIEWS_READ.value)
    ),
):
    return _service(request, current_user).get_review(exception_id)


@router.post(
    "/{exception_id}/decision",
    response_model=ReviewDecisionResponse,
    summary="Submit an approve, modify or reject decision",
)
def submit_review_decision(
    exception_id: str,
    payload: ReviewDecisionRequest,
    request: Request,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
    ),
    current_user: dict = Depends(
        require_permission(Permission.REVIEWS_DECIDE.value)
    ),
):
    reviewer_id = str(current_user.get("_id", ""))
    roles = current_user.get("roles", [])

    if not reviewer_id or not isinstance(roles, list):
        from fastapi import HTTPException

        raise HTTPException(403, "Reviewer identity is unavailable.")

    return _service(request, current_user).decide(
        exception_id=exception_id,
        decision=payload.decision,
        reviewer_id=reviewer_id,
        reviewer_roles=roles,
        idempotency_key=idempotency_key,
        comment=payload.comment,
        after=payload.after,
        correlation_id=get_request_id(request),
    )
