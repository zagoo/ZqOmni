"""M03-9 — Access reviews (RPT-11)."""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentSession,
    IdempotencyKeyHeader,
    authorize,
    check_idempotency,
    store_idempotency,
)
from app.core.config import get_settings
from app.core.errors import not_found
from app.core.ids import PREFIX_ACCESS_REVIEW, new_id
from app.core.pagination import PageParams, page_params, paginate
from app.database import get_db
from app.models.iam import AccessReview, AccessReviewEntry
from app.schemas.iam import (
    AccessReviewCreate,
    AccessReviewEntryOut,
    AccessReviewOut,
    AccessReviewSummary,
)
from app.schemas.response import ApiResponse, PageData
from app.services.audit import emit_audit
from app.services.reviews import generate_access_review

router = APIRouter(tags=["M03 User, Role & Permission"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _review_out(r: AccessReview) -> AccessReviewOut:
    return AccessReviewOut(
        review_id=r.review_id,
        tenant_id=r.tenant_id,
        review_type=r.review_type,
        status=r.status,
        period_start=r.period_start,
        period_end=r.period_end,
        requested_by=r.requested_by,
        created_at=r.created_at,
        completed_at=r.completed_at,
        failure_reason=r.failure_reason,
        summary=AccessReviewSummary(**r.summary) if r.summary else None,
    )


@router.post(
    "/api/v1/tenants/{tenant_id}/access-reviews",
    operation_id="m03_create_access_review",
    status_code=201,
    response_model=ApiResponse[AccessReviewOut],
)
async def create_access_review(
    tenant_id: str,
    body: AccessReviewCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[AccessReviewOut]:
    await authorize(db, ctx, "iam.access_review:create", "tenant", tenant_id)
    payload = {"tenant_id": tenant_id, **body.model_dump(mode="json")}
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m03_create_access_review", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[AccessReviewOut].model_validate(replay["body"])

    now = datetime.now(timezone.utc)
    period_end = body.period_end or now
    period_start = body.period_start or (period_end - timedelta(days=90))

    review = AccessReview(
        review_id=new_id(PREFIX_ACCESS_REVIEW),
        tenant_id=tenant_id,
        review_type=body.review_type,
        status="generating",
        period_start=period_start,
        period_end=period_end,
        requested_by=ctx.user_id,
        created_at=now,
    )
    db.add(review)
    await emit_audit(
        db,
        action="iam.access_review.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="access_review",
        subject_id=review.review_id,
        source_module="M03",
        tenant_id=tenant_id,
    )
    envelope = ApiResponse(data=_review_out(review))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m03_create_access_review",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    # Async generation job (FDD: respond immediately, generate in background).
    asyncio.get_running_loop().create_task(generate_access_review(review.review_id))
    return envelope


@router.get(
    "/api/v1/tenants/{tenant_id}/access-reviews",
    operation_id="m03_list_access_reviews",
    response_model=ApiResponse[PageData[AccessReviewOut]],
)
async def list_access_reviews(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
) -> ApiResponse[PageData[AccessReviewOut]]:
    await authorize(db, ctx, "iam.access_review:read", "tenant", tenant_id)
    stmt = (
        select(AccessReview)
        .where(AccessReview.tenant_id == tenant_id)
        .order_by(AccessReview.created_at.desc())
    )
    rows, next_token, total = await paginate(db, stmt, page)
    return ApiResponse(
        data=PageData(
            items=[_review_out(r) for r in rows], next_page_token=next_token, total_size=total
        )
    )


@router.get(
    "/api/v1/access-reviews/{review_id}",
    operation_id="m03_get_access_review",
    response_model=ApiResponse[AccessReviewOut],
)
async def get_access_review(
    review_id: str, ctx: CurrentSession, db: DB
) -> ApiResponse[AccessReviewOut]:
    review = await db.get(AccessReview, review_id)
    if review is None:
        raise not_found("Access review not found.")
    await authorize(db, ctx, "iam.access_review:read", "tenant", review.tenant_id)
    return ApiResponse(data=_review_out(review))


@router.get(
    "/api/v1/access-reviews/{review_id}/entries",
    operation_id="m03_list_access_review_entries",
    response_model=ApiResponse[PageData[AccessReviewEntryOut]],
)
async def list_access_review_entries(
    review_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
) -> ApiResponse[PageData[AccessReviewEntryOut]]:
    review = await db.get(AccessReview, review_id)
    if review is None:
        raise not_found("Access review not found.")
    await authorize(db, ctx, "iam.access_review:read", "tenant", review.tenant_id)
    stmt = (
        select(AccessReviewEntry)
        .where(AccessReviewEntry.review_id == review_id)
        .order_by(AccessReviewEntry.entry_no.asc())
    )
    rows, next_token, total = await paginate(db, stmt, page)
    items = [
        AccessReviewEntryOut(
            user_id=e.user_id,
            display_name=e.display_name,
            grant=e.grant,
            asset_class=e.asset_class,
            last_access_at=e.last_access_at,
            anomalies=list(e.anomalies),
        )
        for e in rows
    ]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))
