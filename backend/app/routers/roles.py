"""M03 — Roles (FDD §2.3.3: M03-4 create/list, M03-5 detail/recompose/delete).

Anti-escalation (BR-13): every requested key must lie inside the grantor's own
effective set at the target scope (PA exempt).
"""
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
from app.core.errors import DomainError, not_found, validation_error
from app.core.ids import PREFIX_ROLE, new_id
from app.core.pagination import PageParams, page_params
from app.database import get_db
from app.models.iam import Permission, Role, RoleBinding, RolePermission
from app.schemas.iam import RoleCreate, RoleOut, RolePatch, RoleScope
from app.schemas.response import ApiResponse, PageData
from app.services import authz
from app.services.audit import emit_audit
from app.services.catalog import ROLE_PA, expand_builtin_keys

router = APIRouter(tags=["M03 User, Role & Permission"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _role_keys(db: AsyncSession, role_id: str) -> list[str]:
    rows = (
        await db.execute(
            select(RolePermission.permission_key).where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    return sorted(rows)


async def _bindings_count(db: AsyncSession, role_id: str) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(RoleBinding)
            .where(RoleBinding.role_id == role_id, RoleBinding.deleted_at.is_(None))
        )
    ).scalar_one()


async def _role_out(db: AsyncSession, role: Role, with_counts: bool = True) -> RoleOut:
    if role.role_type == "builtin":
        # Built-ins render their expanded unit list (read-only composer).
        keys = sorted(expand_builtin_keys(role.role_id, "project"))
    else:
        keys = await _role_keys(db, role.role_id)
    return RoleOut(
        role_id=role.role_id,
        name=role.name,
        role_type=role.role_type,
        scope=RoleScope(type=role.scope_type, id=role.scope_tenant_id),
        description=role.description,
        permission_keys=keys,
        version=role.version,
        created_at=role.created_at,
        created_by=role.created_by,
        bindings_count=(await _bindings_count(db, role.role_id)) if with_counts else None,
    )


async def _validate_keys_exist(db: AsyncSession, keys: list[str]) -> None:
    rows = (
        await db.execute(select(Permission.key).where(Permission.key.in_(keys)))
    ).scalars().all()
    known = set(rows)
    unknown = sorted(set(keys) - known)
    if unknown:
        raise DomainError(
            "E_IAM_UNKNOWN_PERMISSION",
            "Unknown permission key(s).",
            details=[{"unknown_keys": unknown}],
        )
    service_only = (
        await db.execute(
            select(Permission.key).where(Permission.key.in_(keys), Permission.service_only)
        )
    ).scalars().all()
    if service_only:
        raise validation_error(
            "Service-plane permission keys cannot be granted to human roles.",
            details=[{"service_only_keys": sorted(service_only)}],
        )


async def _enforce_anti_escalation(
    db: AsyncSession, ctx, keys: list[str], scope_type: str, scope_id: str | None
) -> None:
    """Grantor's effective set at the target scope must superset `keys` (PA exempt)."""
    pa = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="iam.role:create",
        scope_type="platform", scope_id=None, use_cache=False,
    )
    if pa.allowed and pa.matched and pa.matched.get("role_id") == ROLE_PA:
        return
    effective = await authz.effective_permission_keys(
        db, user_id=ctx.user_id, scope_type=scope_type, scope_id=scope_id
    )
    missing = sorted(set(keys) - set(effective.keys()))
    if missing:
        raise DomainError(
            "E_PERMISSION_DENIED",
            "You cannot grant permissions outside your own effective set.",
            details=[{"missing_keys": missing}],
        )


# ---------------------------------------------------------------------------
# M03-4 Create / list roles
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/tenants/{tenant_id}/roles",
    operation_id="m03_create_tenant_role",
    status_code=201,
    response_model=ApiResponse[RoleOut],
)
async def create_tenant_role(
    tenant_id: str,
    body: RoleCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[RoleOut]:
    await authorize(db, ctx, "iam.role:create", "tenant", tenant_id)
    payload = {"tenant_id": tenant_id, **body.model_dump()}
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m03_create_tenant_role", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[RoleOut].model_validate(replay["body"])

    keys = sorted(set(body.permission_keys))
    await _validate_keys_exist(db, keys)
    await _enforce_anti_escalation(db, ctx, keys, "tenant", tenant_id)

    duplicate = (
        await db.execute(
            select(Role.role_id).where(
                Role.scope_type == "tenant",
                Role.scope_tenant_id == tenant_id,
                Role.name == body.name,
                Role.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        raise DomainError("E_CONFLICT", "A role with this name already exists at this scope.")

    role = Role(
        role_id=new_id(PREFIX_ROLE),
        name=body.name,
        role_type="custom",
        scope_type="tenant",
        scope_tenant_id=tenant_id,
        description=body.description,
        version=1,
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(role)
    for key in keys:
        db.add(RolePermission(role_id=role.role_id, permission_key=key))
    await emit_audit(
        db,
        action="iam.role.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="role",
        subject_id=role.role_id,
        source_module="M03",
        tenant_id=tenant_id,
        after_summary={"name": body.name, "permission_keys": keys},
    )
    out = RoleOut(
        role_id=role.role_id,
        name=role.name,
        role_type="custom",
        scope=RoleScope(type="tenant", id=tenant_id),
        description=role.description,
        permission_keys=keys,
        version=1,
        created_at=role.created_at,
        created_by=role.created_by,
        bindings_count=0,
    )
    envelope = ApiResponse(data=out)
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m03_create_tenant_role",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    return envelope


@router.get(
    "/api/v1/tenants/{tenant_id}/roles",
    operation_id="m03_list_tenant_roles",
    response_model=ApiResponse[PageData[RoleOut]],
)
async def list_tenant_roles(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
) -> ApiResponse[PageData[RoleOut]]:
    """Built-ins (read-only) + customs visible at the tenant scope."""
    await authorize(db, ctx, "iam.role:read", "tenant", tenant_id)
    stmt = (
        select(Role)
        .where(
            Role.deleted_at.is_(None),
            (Role.role_type == "builtin")
            | ((Role.scope_type == "tenant") & (Role.scope_tenant_id == tenant_id)),
        )
        .order_by(Role.role_type.asc(), Role.name.asc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).scalars().all()
    items = [await _role_out(db, role) for role in rows]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.get(
    "/api/v1/roles",
    operation_id="m03_list_platform_roles",
    response_model=ApiResponse[PageData[RoleOut]],
)
async def list_platform_roles(
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    scope: str = Query("platform"),
) -> ApiResponse[PageData[RoleOut]]:
    await authorize(db, ctx, "iam.role:read", "platform", None)
    stmt = (
        select(Role)
        .where(Role.deleted_at.is_(None), Role.scope_type == "platform")
        .order_by(Role.role_type.asc(), Role.name.asc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).scalars().all()
    items = [await _role_out(db, role) for role in rows]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


# ---------------------------------------------------------------------------
# M03-5 Role detail / recompose / delete
# ---------------------------------------------------------------------------


async def _role_or_404(db: AsyncSession, role_id: str) -> Role:
    role = (
        await db.execute(
            select(Role).where(Role.role_id == role_id, Role.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if role is None:
        raise not_found("Role not found.")
    return role


def _role_read_scope(role: Role) -> tuple[str, str | None]:
    if role.scope_type == "tenant" and role.scope_tenant_id:
        return "tenant", role.scope_tenant_id
    return "platform", None


@router.get(
    "/api/v1/roles/{role_id}",
    operation_id="m03_get_role",
    response_model=ApiResponse[RoleOut],
)
async def get_role(
    role_id: str, ctx: CurrentSession, db: DB, response: Response
) -> ApiResponse[RoleOut]:
    role = await _role_or_404(db, role_id)
    scope_type, scope_id = _role_read_scope(role)
    await authorize(db, ctx, "iam.role:read", scope_type, scope_id)
    set_etag(response, role.version)
    return ApiResponse(data=await _role_out(db, role))


@router.patch(
    "/api/v1/roles/{role_id}",
    operation_id="m03_update_role",
    response_model=ApiResponse[RoleOut],
)
async def update_role(
    role_id: str,
    body: RolePatch,
    request: Request,
    ctx: CurrentSession,
    db: DB,
    response: Response,
) -> ApiResponse[RoleOut]:
    role = await _role_or_404(db, role_id)
    if role.role_type == "builtin":
        raise DomainError("E_IAM_BUILTIN_IMMUTABLE", "Built-in roles cannot be modified.")
    scope_type, scope_id = _role_read_scope(role)
    await authorize(db, ctx, "iam.role:update", scope_type, scope_id)
    require_if_match(request, role.version)

    if body.permission_keys is not None:
        keys = sorted(set(body.permission_keys))
        await _validate_keys_exist(db, keys)
        await _enforce_anti_escalation(db, ctx, keys, scope_type, scope_id)
        existing = (
            await db.execute(select(RolePermission).where(RolePermission.role_id == role_id))
        ).scalars().all()
        for row in existing:
            await db.delete(row)
        await db.flush()
        for key in keys:
            db.add(RolePermission(role_id=role_id, permission_key=key))
    if body.description is not None:
        role.description = body.description

    role.version += 1
    role.updated_at = _now()
    role.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="iam.role.updated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="role",
        subject_id=role_id,
        source_module="M03",
        tenant_id=role.scope_tenant_id,
    )
    await db.commit()
    # Mandated: decision-cache invalidation for every binding of this role.
    user_ids = (
        await db.execute(
            select(RoleBinding.user_id).where(
                RoleBinding.role_id == role_id, RoleBinding.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    for uid in set(user_ids):
        authz.invalidate_user(uid)
    set_etag(response, role.version)
    return ApiResponse(data=await _role_out(db, role))


@router.delete(
    "/api/v1/roles/{role_id}",
    operation_id="m03_delete_role",
    status_code=204,
)
async def delete_role(role_id: str, ctx: CurrentSession, db: DB) -> Response:
    role = (
        await db.execute(select(Role).where(Role.role_id == role_id))
    ).scalar_one_or_none()
    if role is None or role.deleted_at is not None:
        return Response(status_code=204)  # idempotent
    if role.role_type == "builtin":
        raise DomainError("E_IAM_BUILTIN_IMMUTABLE", "Built-in roles cannot be deleted.")
    scope_type, scope_id = _role_read_scope(role)
    await authorize(db, ctx, "iam.role:delete", scope_type, scope_id)
    count = await _bindings_count(db, role_id)
    if count:
        raise DomainError(
            "E_IAM_ROLE_IN_USE",
            "Role has active bindings.",
            details=[{"binding_count": count}],
        )
    role.deleted_at = _now()  # soft delete (audit reconstruction)
    role.deleted_by = ctx.user_id
    await emit_audit(
        db,
        action="iam.role.deleted",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="role",
        subject_id=role_id,
        source_module="M03",
        tenant_id=role.scope_tenant_id,
    )
    await db.commit()
    return Response(status_code=204)
