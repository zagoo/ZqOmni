"""M03 — Role bindings & effective permissions (FDD §2.3.3: M03-6, M03-7)."""
from datetime import datetime, timezone
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
from app.core.errors import DomainError, not_found, validation_error
from app.core.ids import PREFIX_ROLE_BINDING, new_id
from app.core.pagination import PageParams, page_params
from app.database import get_db
from app.models.iam import Role, RoleBinding, RolePermission, User
from app.models.tenancy import Project, Tenant
from app.schemas.iam import (
    BindingScope,
    EffectivePermission,
    EffectivePermissionsResponse,
    EffectiveVia,
    RoleBindingCreate,
    RoleBindingOut,
)
from app.schemas.response import ApiResponse, PageData
from app.services import authz
from app.services.audit import emit_audit
from app.services.catalog import (
    BUILTIN_PLACEMENT,
    ROLE_PA,
    ROLE_TA,
    expand_builtin_keys,
)

router = APIRouter(tags=["M03 User, Role & Permission"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _binding_out(b: RoleBinding, user: User | None, role: Role | None) -> RoleBindingOut:
    return RoleBindingOut(
        binding_id=b.binding_id,
        user_id=b.user_id,
        user_display_name=user.display_name if user else None,
        role_id=b.role_id,
        role_name=role.name if role else None,
        scope=BindingScope(type=b.scope_type, id=b.scope_id),
        origin=b.origin,
        created_at=b.created_at,
        created_by=b.created_by,
    )


async def _validate_scope(db: AsyncSession, scope: BindingScope) -> None:
    """Scope exists and is not archived; id type must match scope type."""
    if scope.type == "platform":
        if scope.id is not None:
            raise DomainError("E_IAM_SCOPE_MISMATCH", "Platform scope takes no id.")
        return
    if scope.id is None:
        raise DomainError("E_IAM_SCOPE_MISMATCH", "Scope id required.")
    if scope.type == "tenant":
        if not scope.id.startswith("tnt-"):
            raise DomainError("E_IAM_SCOPE_MISMATCH", "Scope id is not a tenant id.")
        tenant = await db.get(Tenant, scope.id)
        if tenant is None:
            raise DomainError("E_IAM_SCOPE_MISMATCH", "Tenant not found.")
        if tenant.status == "archived":
            raise validation_error("Cannot bind into an archived tenant.")
        return
    if not scope.id.startswith("prj-"):
        raise DomainError("E_IAM_SCOPE_MISMATCH", "Scope id is not a project id.")
    project = await db.get(Project, scope.id)
    if project is None:
        raise DomainError("E_IAM_SCOPE_MISMATCH", "Project not found.")
    if project.status == "archived":
        raise validation_error("Cannot bind into an archived project.")


async def _validate_role_scope_compat(
    db: AsyncSession, role: Role, scope: BindingScope
) -> None:
    if role.role_type == "builtin":
        allowed = BUILTIN_PLACEMENT[role.role_id]
        if scope.type not in allowed:
            raise validation_error(
                f"Built-in role {role.role_id} is bindable only at: {', '.join(sorted(allowed))}."
            )
        return
    # Tenant custom roles bindable only within their tenant subtree.
    if role.scope_type == "tenant":
        if scope.type == "tenant":
            if scope.id != role.scope_tenant_id:
                raise DomainError(
                    "E_IAM_SCOPE_MISMATCH", "Custom role belongs to a different tenant."
                )
        elif scope.type == "project":
            project = await db.get(Project, scope.id)
            if project is None or project.tenant_id != role.scope_tenant_id:
                raise DomainError(
                    "E_IAM_SCOPE_MISMATCH", "Custom role belongs to a different tenant."
                )
        else:
            raise DomainError(
                "E_IAM_SCOPE_MISMATCH", "Tenant custom roles cannot be bound at platform scope."
            )


async def _role_unit_keys(db: AsyncSession, role: Role, scope_type: str) -> set[str]:
    if role.role_type == "builtin":
        return expand_builtin_keys(role.role_id, scope_type)
    rows = (
        await db.execute(
            select(RolePermission.permission_key).where(RolePermission.role_id == role.role_id)
        )
    ).scalars().all()
    return set(rows)


async def _is_pa(db: AsyncSession, user_id: str) -> bool:
    row = (
        await db.execute(
            select(RoleBinding.binding_id)
            .join(User, User.user_id == RoleBinding.user_id)
            .where(
                RoleBinding.user_id == user_id,
                RoleBinding.role_id == ROLE_PA,
                RoleBinding.scope_type == "platform",
                RoleBinding.deleted_at.is_(None),
                User.status == "active",
            )
        )
    ).scalar_one_or_none()
    return row is not None


@router.post(
    "/api/v1/role-bindings",
    operation_id="m03_create_role_binding",
    status_code=201,
    response_model=ApiResponse[RoleBindingOut],
)
async def create_role_binding(
    body: RoleBindingCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[RoleBindingOut]:
    # 1. Scope shape/existence first (malformed scopes are E_IAM_SCOPE_MISMATCH,
    #    not authz denials), then authz at the TARGET scope (TA only inside
    #    own tenant subtree).
    await _validate_scope(db, body.scope)
    await authorize(db, ctx, "iam.role_binding:create", body.scope.type, body.scope.id)
    payload = body.model_dump()
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m03_create_role_binding", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[RoleBindingOut].model_validate(replay["body"])

    # 2. Validations.
    user = await db.get(User, body.user_id)
    if user is None:
        raise validation_error("User not found.")  # binding deactivated users is allowed (inert)
    role = (
        await db.execute(
            select(Role).where(Role.role_id == body.role_id, Role.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if role is None:
        raise validation_error("Role not found.")
    await _validate_role_scope_compat(db, role, body.scope)

    # 3. Anti-escalation (PA exempt).
    if not await _is_pa(db, ctx.user_id):
        role_keys = await _role_unit_keys(db, role, body.scope.type)
        effective = await authz.effective_permission_keys(
            db, user_id=ctx.user_id, scope_type=body.scope.type, scope_id=body.scope.id
        )
        missing = sorted(role_keys - set(effective.keys()))
        if missing:
            raise DomainError(
                "E_PERMISSION_DENIED",
                "You cannot grant a role exceeding your own effective permissions.",
                details=[{"missing_keys": missing}],
            )

    # 4. Uniqueness among live bindings.
    duplicate = (
        await db.execute(
            select(RoleBinding.binding_id).where(
                RoleBinding.user_id == body.user_id,
                RoleBinding.role_id == body.role_id,
                RoleBinding.scope_type == body.scope.type,
                RoleBinding.scope_id.is_(None) if body.scope.id is None
                else RoleBinding.scope_id == body.scope.id,
                RoleBinding.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        raise DomainError("E_CONFLICT", "This binding already exists.")

    binding = RoleBinding(
        binding_id=new_id(PREFIX_ROLE_BINDING),
        user_id=body.user_id,
        role_id=body.role_id,
        scope_type=body.scope.type,
        scope_id=body.scope.id,
        origin="direct",
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(binding)
    await emit_audit(
        db,
        action="iam.role_binding.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="role_binding",
        subject_id=binding.binding_id,
        source_module="M03",
        tenant_id=body.scope.id if body.scope.type == "tenant" else None,
        after_summary={
            "user_id": body.user_id,
            "role_id": body.role_id,
            "scope": f"{body.scope.type}:{body.scope.id or 'platform'}",
        },
    )
    envelope = ApiResponse(data=_binding_out(binding, user, role))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m03_create_role_binding",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    authz.invalidate_user(body.user_id)
    return envelope


@router.get(
    "/api/v1/role-bindings",
    operation_id="m03_list_role_bindings",
    response_model=ApiResponse[PageData[RoleBindingOut]],
)
async def list_role_bindings(
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    user_id: str | None = Query(None),
    role_id: str | None = Query(None),
    scope_type: str | None = Query(None),
    scope_id: str | None = Query(None),
) -> ApiResponse[PageData[RoleBindingOut]]:
    platform_read = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="iam.role_binding:read",
        scope_type="platform", scope_id=None,
    )
    stmt = (
        select(RoleBinding, User, Role)
        .join(User, User.user_id == RoleBinding.user_id)
        .join(Role, Role.role_id == RoleBinding.role_id)
        .where(RoleBinding.deleted_at.is_(None))
        .order_by(RoleBinding.created_at.desc())
    )
    if not platform_read.allowed:
        tenant_read = None
        if ctx.active_tenant_id:
            tenant_read = await authz.check_permission(
                db, user_id=ctx.user_id, permission_key="iam.role_binding:read",
                scope_type="tenant", scope_id=ctx.active_tenant_id,
            )
        if tenant_read is not None and tenant_read.allowed:
            project_ids = (
                await db.execute(
                    select(Project.project_id).where(Project.tenant_id == ctx.active_tenant_id)
                )
            ).scalars().all()
            tenant_filter = (
                (RoleBinding.scope_type == "tenant")
                & (RoleBinding.scope_id == ctx.active_tenant_id)
            )
            if project_ids:
                tenant_filter = tenant_filter | (
                    (RoleBinding.scope_type == "project")
                    & (RoleBinding.scope_id.in_(project_ids))
                )
            stmt = stmt.where(tenant_filter)
        else:
            stmt = stmt.where(RoleBinding.user_id == ctx.user_id)  # self only

    if user_id:
        stmt = stmt.where(RoleBinding.user_id == user_id)
    if role_id:
        stmt = stmt.where(RoleBinding.role_id == role_id)
    if scope_type:
        stmt = stmt.where(RoleBinding.scope_type == scope_type)
    if scope_id:
        stmt = stmt.where(RoleBinding.scope_id == scope_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).all()
    items = [_binding_out(b, u, r) for b, u, r in rows]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.delete(
    "/api/v1/role-bindings/{binding_id}",
    operation_id="m03_delete_role_binding",
    status_code=204,
)
async def delete_role_binding(binding_id: str, ctx: CurrentSession, db: DB) -> Response:
    binding = (
        await db.execute(select(RoleBinding).where(RoleBinding.binding_id == binding_id))
    ).scalar_one_or_none()
    if binding is None or binding.deleted_at is not None:
        return Response(status_code=204)  # idempotent
    await authorize(db, ctx, "iam.role_binding:delete", binding.scope_type, binding.scope_id)

    if binding.origin == "project_membership":
        raise validation_error("Manage via project membership.")

    # Last-admin guards.
    if binding.role_id == ROLE_PA and binding.scope_type == "platform":
        others = (
            await db.execute(
                select(func.count(func.distinct(RoleBinding.user_id)))
                .select_from(RoleBinding)
                .join(User, User.user_id == RoleBinding.user_id)
                .where(
                    RoleBinding.role_id == ROLE_PA,
                    RoleBinding.scope_type == "platform",
                    RoleBinding.deleted_at.is_(None),
                    User.status == "active",
                    RoleBinding.binding_id != binding_id,
                )
            )
        ).scalar_one()
        if others == 0:
            raise DomainError(
                "E_IAM_LAST_PLATFORM_ADMIN",
                "This is the last platform administrator binding.",
            )
    if binding.role_id == ROLE_TA and binding.scope_type == "tenant":
        others = (
            await db.execute(
                select(func.count())
                .select_from(RoleBinding)
                .where(
                    RoleBinding.role_id == ROLE_TA,
                    RoleBinding.scope_type == "tenant",
                    RoleBinding.scope_id == binding.scope_id,
                    RoleBinding.deleted_at.is_(None),
                    RoleBinding.binding_id != binding_id,
                )
            )
        ).scalar_one()
        if others == 0:
            raise DomainError(
                "E_IAM_LAST_TENANT_ADMIN",
                "This is the last tenant administrator binding of this tenant.",
            )

    binding.deleted_at = _now()
    binding.deleted_by = ctx.user_id
    await emit_audit(
        db,
        action="iam.role_binding.deleted",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="role_binding",
        subject_id=binding_id,
        source_module="M03",
        tenant_id=binding.scope_id if binding.scope_type == "tenant" else None,
    )
    await db.commit()
    authz.invalidate_user(binding.user_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# M03-7 Effective permissions
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/users/{user_id}/effective-permissions",
    operation_id="m03_effective_permissions",
    response_model=ApiResponse[EffectivePermissionsResponse],
)
async def effective_permissions(
    user_id: str,
    ctx: CurrentSession,
    db: DB,
    scope_type: str = Query(...),
    scope_id: str | None = Query(None),
) -> ApiResponse[EffectivePermissionsResponse]:
    """Self always allowed; others require iam.role_binding:read at the scope."""
    if scope_type not in ("platform", "tenant", "project"):
        raise validation_error("scope_type must be platform|tenant|project.")
    if user_id != ctx.user_id:
        await authorize(db, ctx, "iam.role_binding:read", scope_type, scope_id)  # type: ignore[arg-type]

    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User not found.")
    try:
        chain = await authz.resolve_scope_chain(db, scope_type, scope_id)  # type: ignore[arg-type]
    except authz.ScopeNotFound:
        raise not_found("Scope not found.") from None

    scope_status = "active"
    denied_reasons: list[str] = []
    if user.status != "active":
        denied_reasons.append("user_inactive")
    if chain.tenant is not None and chain.tenant.status != "active":
        scope_status = chain.tenant.status
        denied_reasons.append("scope_inactive")
    if chain.project is not None and chain.project.status != "active":
        scope_status = chain.project.status
        denied_reasons.append("scope_inactive")

    allowed_map = await authz.effective_permission_keys(
        db, user_id=user_id, scope_type=scope_type, scope_id=scope_id  # type: ignore[arg-type]
    )
    allowed = [
        EffectivePermission(
            key=key,
            via=[EffectiveVia(**v) for v in vias],
        )
        for key, vias in sorted(allowed_map.items())
    ]
    return ApiResponse(
        data=EffectivePermissionsResponse(
            user_id=user_id,
            scope=BindingScope(type=scope_type, id=scope_id),  # type: ignore[arg-type]
            allowed=allowed,
            denied_reasons=denied_reasons,
            user_status=user.status,
            scope_status=scope_status,
            resolved_at=_now(),
        )
    )
