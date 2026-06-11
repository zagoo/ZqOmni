"""M03 — User pre-registration & lifecycle (FDD §2.3.3: M03-1, M03-2)."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentSession,
    IdempotencyKeyHeader,
    authorize,
    check_idempotency,
    require_if_match,
    set_etag,
    store_idempotency,
)
from app.core.config import get_settings
from app.core.errors import DomainError, not_found, state_invalid, validation_error
from app.core.ids import PREFIX_USER, new_id
from app.core.pagination import PageParams, page_params, paginate
from app.database import get_db
from app.models.iam import Role, RoleBinding, User
from app.routers.auth import purge_caches_for_session
from app.schemas.iam import DeactivateRequest, UserCreate, UserOut, UserPatch
from app.schemas.response import ApiResponse, PageData
from app.services import authz
from app.services.audit import emit_audit
from app.services.catalog import ROLE_PA
from app.services.login import revoke_all_sessions

router = APIRouter(tags=["M03 User, Role & Permission"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_out(user: User, bindings_count: int | None = None) -> UserOut:
    return UserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        deactivate_reason=user.deactivate_reason,
        last_login_at=user.last_login_at,
        note=user.note,
        version=user.version,
        created_at=user.created_at,
        created_by=user.created_by,
        bindings_count=bindings_count,
    )


async def _user_or_404(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User not found.")
    return user


async def _count_other_active_platform_admins(db: AsyncSession, user_id: str) -> int:
    """Active PAs other than `user_id` (last-admin guard)."""
    stmt = (
        select(func.count(func.distinct(RoleBinding.user_id)))
        .select_from(RoleBinding)
        .join(User, User.user_id == RoleBinding.user_id)
        .where(
            RoleBinding.role_id == ROLE_PA,
            RoleBinding.scope_type == "platform",
            RoleBinding.deleted_at.is_(None),
            User.status == "active",
            RoleBinding.user_id != user_id,
        )
    )
    return (await db.execute(stmt)).scalar_one()


@router.post(
    "/api/v1/admin/users",
    operation_id="m03_preregister_user",
    status_code=201,
    response_model=ApiResponse[UserOut],
)
async def preregister_user(
    body: UserCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[UserOut]:
    """M03-1: PA pre-registers a corporate email — the M01 login prerequisite.
    No invitation email is sent (scope discipline)."""
    await authorize(db, ctx, "iam.user:create", "platform", None)
    payload = body.model_dump()
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m03_preregister_user", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[UserOut].model_validate(replay["body"])

    settings = get_settings()
    domain = body.email.rsplit("@", 1)[-1]
    if settings.allowed_email_domains and domain not in settings.allowed_email_domains:
        raise validation_error(
            f"Only corporate domains are allowed: {', '.join(settings.allowed_email_domains)}."
        )
    exists = (
        await db.execute(select(User.user_id).where(User.email == body.email))
    ).scalar_one_or_none()
    if exists:
        raise DomainError("E_IAM_EMAIL_EXISTS", "This email is already registered.")

    user = User(
        user_id=new_id(PREFIX_USER),
        email=body.email,
        display_name=body.display_name,
        status="invited",
        note=body.note,
        version=1,
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(user)
    await emit_audit(
        db,
        action="iam.user.invited",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="user",
        subject_id=user.user_id,
        source_module="M03",
        after_summary={"email": user.email, "display_name": user.display_name},
    )
    envelope = ApiResponse(data=_user_out(user, 0))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m03_preregister_user",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    return envelope


@router.get(
    "/api/v1/admin/users",
    operation_id="m03_list_users",
    response_model=ApiResponse[PageData[UserOut]],
)
async def list_users(
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, max_length=120),
    status: Annotated[list[str] | None, Query()] = None,
    sort: str = Query("-created_at"),
) -> ApiResponse[PageData[UserOut]]:
    # PA platform-wide; TA reads tenant members via scope-limited iam.user:read.
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="iam.user:read",
        scope_type="platform", scope_id=None,
    )
    tenant_member_filter: set[str] | None = None
    if not decision.allowed:
        if ctx.active_tenant_id is None:
            raise DomainError("E_PERMISSION_DENIED", "Platform administrator access required.")
        await authorize(db, ctx, "iam.user:read", "tenant", ctx.active_tenant_id)
        # Tenant members = users with bindings/memberships anchored in this tenant.
        from app.models.tenancy import Project, ProjectMember

        project_ids = (
            await db.execute(
                select(Project.project_id).where(Project.tenant_id == ctx.active_tenant_id)
            )
        ).scalars().all()
        ids: set[str] = set()
        rows = (
            await db.execute(
                select(RoleBinding.user_id).where(
                    RoleBinding.deleted_at.is_(None),
                    (
                        (RoleBinding.scope_type == "tenant")
                        & (RoleBinding.scope_id == ctx.active_tenant_id)
                    )
                    | (
                        (RoleBinding.scope_type == "project")
                        & (RoleBinding.scope_id.in_(project_ids) if project_ids else False)
                    ),
                )
            )
        ).scalars().all()
        ids.update(rows)
        if project_ids:
            member_rows = (
                await db.execute(
                    select(ProjectMember.user_id).where(ProjectMember.project_id.in_(project_ids))
                )
            ).scalars().all()
            ids.update(member_rows)
        tenant_member_filter = ids

    stmt = select(User)
    if tenant_member_filter is not None:
        if not tenant_member_filter:
            return ApiResponse(data=PageData(items=[], next_page_token=None, total_size=0))
        stmt = stmt.where(User.user_id.in_(tenant_member_filter))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(User.email.ilike(like) | User.display_name.ilike(like))
    if status:
        stmt = stmt.where(User.status.in_(status))
    order = User.created_at if sort.lstrip("-") == "created_at" else User.display_name
    stmt = stmt.order_by(order.desc() if sort.startswith("-") else order.asc())
    rows, next_token, total = await paginate(db, stmt, page)

    counts: dict[str, int] = {}
    if rows:
        counts = dict(
            (
                await db.execute(
                    select(RoleBinding.user_id, func.count())
                    .where(
                        RoleBinding.user_id.in_([u.user_id for u in rows]),
                        RoleBinding.deleted_at.is_(None),
                    )
                    .group_by(RoleBinding.user_id)
                )
            ).all()
        )
    items = [_user_out(u, counts.get(u.user_id, 0)) for u in rows]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.get(
    "/api/v1/admin/users/{user_id}",
    operation_id="m03_get_user",
    response_model=ApiResponse[UserOut],
)
async def get_user(
    user_id: str, ctx: CurrentSession, db: DB, response: Response
) -> ApiResponse[UserOut]:
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="iam.user:read",
        scope_type="platform", scope_id=None,
    )
    if not decision.allowed:
        if ctx.active_tenant_id is None:
            raise DomainError("E_PERMISSION_DENIED", "Platform administrator access required.")
        await authorize(db, ctx, "iam.user:read", "tenant", ctx.active_tenant_id)
    user = await _user_or_404(db, user_id)
    count = (
        await db.execute(
            select(func.count())
            .select_from(RoleBinding)
            .where(RoleBinding.user_id == user_id, RoleBinding.deleted_at.is_(None))
        )
    ).scalar_one()
    set_etag(response, user.version)
    return ApiResponse(data=_user_out(user, count))


@router.patch(
    "/api/v1/admin/users/{user_id}",
    operation_id="m03_update_user",
    response_model=ApiResponse[UserOut],
)
async def update_user(
    user_id: str,
    body: UserPatch,
    request: Request,
    ctx: CurrentSession,
    db: DB,
    response: Response,
) -> ApiResponse[UserOut]:
    await authorize(db, ctx, "iam.user:update", "platform", None)
    user = await _user_or_404(db, user_id)
    require_if_match(request, user.version)
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.note is not None:
        user.note = body.note
    user.version += 1
    user.updated_at = _now()
    user.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="iam.user.updated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="user",
        subject_id=user_id,
        source_module="M03",
    )
    await db.commit()
    set_etag(response, user.version)
    return ApiResponse(data=_user_out(user))


@router.post(
    "/api/v1/admin/users/{user_id}:deactivate",
    operation_id="m03_deactivate_user",
    response_model=ApiResponse[UserOut],
)
async def deactivate_user(
    user_id: str, body: DeactivateRequest, ctx: CurrentSession, db: DB
) -> ApiResponse[UserOut]:
    """M03-2: deactivate + session-revocation cascade. Bindings stay but are
    inert (denied at M03-10 step 2), so reactivation restores access intact."""
    await authorize(db, ctx, "iam.user:admin", "platform", None)
    user = await _user_or_404(db, user_id)
    if user.status == "deactivated":
        return ApiResponse(data=_user_out(user))  # idempotent
    others = await _count_other_active_platform_admins(db, user_id)
    holds_pa = (
        await db.execute(
            select(RoleBinding.binding_id).where(
                RoleBinding.user_id == user_id,
                RoleBinding.role_id == ROLE_PA,
                RoleBinding.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if holds_pa and others == 0:
        raise DomainError(
            "E_IAM_LAST_PLATFORM_ADMIN",
            "This is the last platform administrator. Assign another before deactivating.",
        )

    from app.models.auth import Session as AuthSession

    session_ids = (
        await db.execute(
            select(AuthSession.session_id).where(
                AuthSession.user_id == user_id, AuthSession.status == "active"
            )
        )
    ).scalars().all()

    user.status = "deactivated"
    user.deactivate_reason = body.reason
    user.version += 1
    user.updated_at = _now()
    user.updated_by = ctx.user_id
    await revoke_all_sessions(
        db, user_id=user_id, reason="user_deactivated", actor_type="user", actor_id=ctx.user_id
    )
    await emit_audit(
        db,
        action="iam.user.deactivated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="user",
        subject_id=user_id,
        source_module="M03",
        reason=body.reason,
    )
    await db.commit()
    for sid in session_ids:
        purge_caches_for_session(sid)
    authz.invalidate_user(user_id)
    return ApiResponse(data=_user_out(user))


@router.post(
    "/api/v1/admin/users/{user_id}:reactivate",
    operation_id="m03_reactivate_user",
    response_model=ApiResponse[UserOut],
)
async def reactivate_user(user_id: str, ctx: CurrentSession, db: DB) -> ApiResponse[UserOut]:
    await authorize(db, ctx, "iam.user:admin", "platform", None)
    user = await _user_or_404(db, user_id)
    if user.status != "deactivated":
        raise state_invalid(
            f"Action not allowed from status {user.status}.",
            allowed_transitions=["deactivated->active", "deactivated->invited"],
        )
    # Returns to `invited` when the user never logged in (FDD state machine).
    user.status = "active" if user.last_login_at is not None else "invited"
    user.deactivate_reason = None
    user.version += 1
    user.updated_at = _now()
    user.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="iam.user.reactivated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="user",
        subject_id=user_id,
        source_module="M03",
    )
    await db.commit()
    authz.invalidate_user(user_id)
    return ApiResponse(data=_user_out(user))
