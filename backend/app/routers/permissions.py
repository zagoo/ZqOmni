"""M03-3 — Atomic permission catalog (read-only; seeded by migration)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSession
from app.core.pagination import PageParams, page_params, paginate
from app.database import get_db
from app.models.iam import Permission
from app.schemas.iam import PermissionOut
from app.schemas.response import ApiResponse, PageData

router = APIRouter(tags=["M03 User, Role & Permission"])


@router.get(
    "/api/v1/permissions",
    operation_id="m03_list_permissions",
    response_model=ApiResponse[PageData[PermissionOut]],
)
async def list_permissions(
    ctx: CurrentSession,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[PageParams, Depends(page_params)],
    domain: str | None = Query(None),
    resource: str | None = Query(None),
    action: str | None = Query(None),
    q: str | None = Query(None, max_length=120),
) -> ApiResponse[PageData[PermissionOut]]:
    # Readable by any authenticated user (BR-13 catalog transparency).
    stmt = select(Permission).order_by(Permission.key.asc())
    if domain:
        stmt = stmt.where(Permission.domain == domain)
    if resource:
        stmt = stmt.where(Permission.resource == resource)
    if action:
        stmt = stmt.where(Permission.action == action)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Permission.key.ilike(like) | Permission.description.ilike(like))
    rows, next_token, total = await paginate(db, stmt, page)
    items = [
        PermissionOut(
            key=p.key,
            domain=p.domain,
            resource=p.resource,
            action=p.action,
            description=p.description,
            owning_module=p.owning_module,
            scope_levels=list(p.scope_levels),
            service_only=p.service_only,
        )
        for p in rows
    ]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))
