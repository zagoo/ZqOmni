"""M03-8 — Audit query (tenant / platform routes, keyset pagination on
(occurred_at, event_id), 92-day window guard, OE domain filter, meta-audit)."""
import base64
import binascii
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSession, authorize
from app.core.config import get_settings
from app.core.errors import permission_denied, validation_error
from app.database import get_db
from app.models.iam import AuditEvent, RoleBinding
from app.schemas.iam import (
    AuditActor,
    AuditEventOut,
    AuditScopeOut,
    AuditSubject,
)
from app.schemas.response import ApiResponse, PageData
from app.services import authz
from app.services.audit import emit_audit
from app.services.catalog import ROLE_OE, ROLE_PA

router = APIRouter(tags=["M03 User, Role & Permission"])

DB = Annotated[AsyncSession, Depends(get_db)]

# M02 emits `tenant.*` / `infra.*` actions; the FDD's "infra/tenancy/ops"
# domain filter therefore covers both the tenant.* and tenancy.* prefixes.
OE_VISIBLE_DOMAINS = ("infra", "tenancy", "tenant", "ops", "workflow")


def _encode_keyset(occurred_at: datetime, event_id: str) -> str:
    raw = f"{occurred_at.isoformat()}|{event_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_keyset(token: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        ts, event_id = raw.split("|", 1)
        return datetime.fromisoformat(ts), event_id
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise validation_error("Invalid page_token.") from None


def _event_out(e: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        event_id=e.event_id,
        occurred_at=e.occurred_at,
        action=e.action,
        actor=AuditActor(type=e.actor_type, id=e.actor_id),
        subject=AuditSubject(type=e.subject_type, id=e.subject_id),
        scope=AuditScopeOut(tenant_id=e.tenant_id, project_id=e.project_id),
        decision=e.decision,
        reason=e.reason,
        before_summary=e.before_summary,
        after_summary=e.after_summary,
        source_module=e.source_module,
        trace_id=e.trace_id,
    )


async def _query_events(
    db: AsyncSession,
    *,
    tenant_id: str | None,
    occurred_after: datetime | None,
    occurred_before: datetime | None,
    action: str | None,
    actor_id: str | None,
    subject_type: str | None,
    subject_id: str | None,
    domain: str | None,
    decision: str | None,
    project_id: str | None,
    domain_allowlist: tuple[str, ...] | None,
    page_size: int,
    page_token: str | None,
) -> tuple[list[AuditEventOut], str | None]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    occurred_before = occurred_before or now
    occurred_after = occurred_after or (occurred_before - timedelta(days=1))
    if occurred_after >= occurred_before:
        raise validation_error("occurred_after must be before occurred_before.")
    if occurred_before - occurred_after > timedelta(days=settings.audit_query_max_window_days):
        raise validation_error(
            f"Narrow the time window to {settings.audit_query_max_window_days} days or less."
        )

    stmt = select(AuditEvent).where(
        AuditEvent.occurred_at >= occurred_after,
        AuditEvent.occurred_at <= occurred_before,
    )
    if tenant_id is not None:
        stmt = stmt.where(AuditEvent.tenant_id == tenant_id)
    if action:
        stmt = stmt.where(AuditEvent.action.like(f"{action}%"))
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if subject_type:
        stmt = stmt.where(AuditEvent.subject_type == subject_type)
    if subject_id:
        stmt = stmt.where(AuditEvent.subject_id == subject_id)
    if decision:
        stmt = stmt.where(AuditEvent.decision == decision)
    if project_id:
        stmt = stmt.where(AuditEvent.project_id == project_id)
    if domain:
        stmt = stmt.where(AuditEvent.action.like(f"{domain}.%"))
    if domain_allowlist is not None:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(*[AuditEvent.action.like(f"{d}.%") for d in domain_allowlist])
        )

    # Keyset pagination (occurred_at, event_id) descending.
    if page_token:
        ts, eid = _decode_keyset(page_token)
        from sqlalchemy import and_, or_

        stmt = stmt.where(
            or_(
                AuditEvent.occurred_at < ts,
                and_(AuditEvent.occurred_at == ts, AuditEvent.event_id < eid),
            )
        )
    stmt = stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc()).limit(
        page_size + 1
    )
    rows = (await db.execute(stmt)).scalars().all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_token = (
        _encode_keyset(rows[-1].occurred_at, rows[-1].event_id) if has_more and rows else None
    )
    return [_event_out(e) for e in rows], next_token


async def _meta_audit_if_restricted(
    db: AsyncSession, ctx, *, subject_id: str | None, tenant_id: str | None
) -> None:
    """The query itself is audited when filters target restricted subjects
    (meta-audit supporting RPT-11)."""
    if subject_id:
        await emit_audit(
            db,
            action="audit.query.executed",
            actor_type="user",
            actor_id=ctx.user_id,
            subject_type="audit_query",
            subject_id=subject_id,
            source_module="M03",
            tenant_id=tenant_id,
        )
        await db.commit()


@router.get(
    "/api/v1/tenants/{tenant_id}/audit-events",
    operation_id="m03_query_tenant_audit_events",
    response_model=ApiResponse[PageData[AuditEventOut]],
)
async def query_tenant_audit_events(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    occurred_after: datetime | None = Query(None),
    occurred_before: datetime | None = Query(None),
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    subject_type: str | None = Query(None),
    subject_id: str | None = Query(None),
    domain: str | None = Query(None),
    decision: str | None = Query(None),
    project_id: str | None = Query(None),
    page_size: int = Query(50, ge=1, le=500),
    page_token: str | None = Query(None),
) -> ApiResponse[PageData[AuditEventOut]]:
    await authorize(db, ctx, "audit.event:read", "tenant", tenant_id)
    items, next_token = await _query_events(
        db,
        tenant_id=tenant_id,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        action=action,
        actor_id=actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        domain=domain,
        decision=decision,
        project_id=project_id,
        domain_allowlist=None,
        page_size=page_size,
        page_token=page_token,
    )
    await _meta_audit_if_restricted(db, ctx, subject_id=subject_id, tenant_id=tenant_id)
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=None))


@router.get(
    "/api/v1/admin/audit-events",
    operation_id="m03_query_admin_audit_events",
    response_model=ApiResponse[PageData[AuditEventOut]],
)
async def query_admin_audit_events(
    ctx: CurrentSession,
    db: DB,
    occurred_after: datetime | None = Query(None),
    occurred_before: datetime | None = Query(None),
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    subject_type: str | None = Query(None),
    subject_id: str | None = Query(None),
    domain: str | None = Query(None),
    decision: str | None = Query(None),
    project_id: str | None = Query(None),
    page_size: int = Query(50, ge=1, le=500),
    page_token: str | None = Query(None),
) -> ApiResponse[PageData[AuditEventOut]]:
    decision_check = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="audit.event:read",
        scope_type="platform", scope_id=None,
    )
    if not decision_check.allowed:
        raise permission_denied()

    # OE callers receive a server-enforced infrastructure-domain filter
    # (mandate boundary); PA sees everything.
    domain_allowlist: tuple[str, ...] | None = None
    is_pa = (
        await db.execute(
            select(RoleBinding.binding_id).where(
                RoleBinding.user_id == ctx.user_id,
                RoleBinding.role_id == ROLE_PA,
                RoleBinding.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if is_pa is None:
        is_oe = (
            await db.execute(
                select(RoleBinding.binding_id).where(
                    RoleBinding.user_id == ctx.user_id,
                    RoleBinding.role_id == ROLE_OE,
                    RoleBinding.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if is_oe is not None:
            domain_allowlist = OE_VISIBLE_DOMAINS

    items, next_token = await _query_events(
        db,
        tenant_id=None,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        action=action,
        actor_id=actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        domain=domain,
        decision=decision,
        project_id=project_id,
        domain_allowlist=domain_allowlist,
        page_size=page_size,
        page_token=page_token,
    )
    await _meta_audit_if_restricted(db, ctx, subject_id=subject_id, tenant_id=None)
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=None))
