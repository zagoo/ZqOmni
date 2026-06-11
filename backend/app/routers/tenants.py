"""M02 — Tenant administration, lifecycle, resource bindings, tenant self
view (FDD §2.2.3: M02-1, M02-2, M02-5, M02-6, M02-7)."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
from app.core.errors import DomainError, not_found, state_invalid, validation_error
from app.core.ids import PREFIX_BINDING, PREFIX_TENANT, new_id
from app.core.pagination import PageParams, page_params, paginate
from app.database import get_db
from app.models.tenancy import Project, Resource, ResourceBinding, Tenant
from app.schemas.response import ApiResponse, PageData
from app.schemas.tenancy import (
    BindingCreate,
    BindingOut,
    BindingPublicOut,
    SuspendRequest,
    TenantCreate,
    TenantOut,
    TenantPatch,
    TenantPublicOut,
)
from app.services import authz
from app.services.audit import emit_audit
from app.services.probes import probe_logical_resource

router = APIRouter(tags=["M02 Tenant & Resource"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _tenant_or_404(db: AsyncSession, tenant_id: str) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise not_found("Tenant not found.")
    return tenant


async def _counts_for_tenants(db: AsyncSession, tenant_ids: list[str]) -> dict[str, tuple[int, int]]:
    """projects/bindings counts via GROUP BY (DB-layer aggregation)."""
    if not tenant_ids:
        return {}
    projects = dict(
        (
            await db.execute(
                select(Project.tenant_id, func.count())
                .where(Project.tenant_id.in_(tenant_ids))
                .group_by(Project.tenant_id)
            )
        ).all()
    )
    bindings = dict(
        (
            await db.execute(
                select(ResourceBinding.tenant_id, func.count())
                .where(
                    ResourceBinding.tenant_id.in_(tenant_ids),
                    ResourceBinding.status == "active",
                )
                .group_by(ResourceBinding.tenant_id)
            )
        ).all()
    )
    return {tid: (projects.get(tid, 0), bindings.get(tid, 0)) for tid in tenant_ids}


def _tenant_out(tenant: Tenant, counts: tuple[int, int] | None = None) -> TenantOut:
    return TenantOut(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        display_name=tenant.display_name,
        description=tenant.description,
        status=tenant.status,
        suspend_reason=tenant.suspend_reason,
        settings=tenant.settings,
        namespace_ref=tenant.namespace_ref,
        version=tenant.version,
        created_at=tenant.created_at,
        created_by=tenant.created_by,
        suspended_at=tenant.suspended_at,
        archived_at=tenant.archived_at,
        projects_count=counts[0] if counts else None,
        bindings_count=counts[1] if counts else None,
    )


# ---------------------------------------------------------------------------
# M02-1 Create / list tenants
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/admin/tenants",
    operation_id="m02_create_tenant",
    status_code=201,
    response_model=ApiResponse[TenantOut],
)
async def create_tenant(
    body: TenantCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[TenantOut]:
    await authorize(db, ctx, "tenancy.tenant:create", "platform", None)
    payload = body.model_dump()
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m02_create_tenant", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[TenantOut].model_validate(replay["body"])

    exists = (
        await db.execute(select(Tenant.tenant_id).where(Tenant.name == body.name))
    ).scalar_one_or_none()
    if exists:
        raise DomainError("E_CONFLICT", "A tenant with this name already exists.")

    tenant = Tenant(
        tenant_id=new_id(PREFIX_TENANT),
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        status="active",
        settings=body.settings.model_dump(),
        namespace_ref=f"tnt-{body.name}",
        version=1,
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(tenant)
    await emit_audit(
        db,
        action="tenant.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="tenant",
        subject_id=tenant.tenant_id,
        source_module="M02",
        tenant_id=tenant.tenant_id,
        after_summary={"name": tenant.name, "display_name": tenant.display_name},
    )
    envelope = ApiResponse(data=_tenant_out(tenant, (0, 0)))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m02_create_tenant",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    return envelope


@router.get(
    "/api/v1/admin/tenants",
    operation_id="m02_list_tenants",
    response_model=ApiResponse[PageData[TenantOut]],
)
async def list_tenants(
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, max_length=120),
    status: Annotated[list[str] | None, Query()] = None,
    sort: str = Query("-created_at"),
) -> ApiResponse[PageData[TenantOut]]:
    await authorize(db, ctx, "tenancy.tenant:read", "platform", None)
    stmt = select(Tenant)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Tenant.name.ilike(like) | Tenant.display_name.ilike(like))
    if status:
        stmt = stmt.where(Tenant.status.in_(status))
    order_col = Tenant.created_at if sort.lstrip("-") == "created_at" else Tenant.name
    stmt = stmt.order_by(order_col.desc() if sort.startswith("-") else order_col.asc())
    rows, next_token, total = await paginate(db, stmt, page)
    counts = await _counts_for_tenants(db, [t.tenant_id for t in rows])
    items = [_tenant_out(t, counts.get(t.tenant_id)) for t in rows]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


# ---------------------------------------------------------------------------
# M02-2 Tenant detail / update / lifecycle
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/admin/tenants/{tenant_id}",
    operation_id="m02_get_tenant",
    response_model=ApiResponse[TenantOut],
)
async def get_tenant(
    tenant_id: str, ctx: CurrentSession, db: DB, response: Response
) -> ApiResponse[TenantOut]:
    await authorize(db, ctx, "tenancy.tenant:read", "platform", None)
    tenant = await _tenant_or_404(db, tenant_id)
    counts = await _counts_for_tenants(db, [tenant_id])
    set_etag(response, tenant.version)
    return ApiResponse(data=_tenant_out(tenant, counts.get(tenant_id)))


@router.patch(
    "/api/v1/admin/tenants/{tenant_id}",
    operation_id="m02_update_tenant",
    response_model=ApiResponse[TenantOut],
)
async def update_tenant(
    tenant_id: str,
    body: TenantPatch,
    request: Request,
    ctx: CurrentSession,
    db: DB,
    response: Response,
) -> ApiResponse[TenantOut]:
    tenant = await _tenant_or_404(db, tenant_id)
    # PA (platform grant) retains lifecycle control even while the tenant is
    # suspended; the tenant-scope path covers TA's own-tenant display edits
    # and is naturally denied when the tenant is suspended (M03-10 step 2).
    platform_grant = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.tenant:update",
        scope_type="platform", scope_id=None,
    )
    if not platform_grant.allowed:
        await authorize(db, ctx, "tenancy.tenant:update", "tenant", tenant_id)
    require_if_match(request, tenant.version)

    before = {"display_name": tenant.display_name, "status": tenant.status}

    if body.status is not None:
        # Guarded archive: only suspended -> archived (M02-2).
        if tenant.status != "suspended":
            raise state_invalid(
                f"Action not allowed from status {tenant.status}.",
                allowed_transitions=["suspended->archived"],
            )
        open_projects = (
            await db.execute(
                select(func.count())
                .select_from(Project)
                .where(Project.tenant_id == tenant_id, Project.status != "archived")
            )
        ).scalar_one()
        if open_projects:
            raise DomainError(
                "E_TNT_TENANT_NOT_EMPTY",
                "Archive all projects before archiving the tenant.",
            )
        live_bindings = (
            await db.execute(
                select(func.count())
                .select_from(ResourceBinding)
                .where(ResourceBinding.tenant_id == tenant_id, ResourceBinding.status == "active")
            )
        ).scalar_one()
        if live_bindings:
            raise DomainError(
                "E_TNT_RESOURCE_IN_USE", "Release all resource bindings before archiving."
            )
        tenant.status = "archived"
        tenant.archived_at = _now()

    if body.settings is not None:
        # Settings changes are platform-admin scope (TA may edit display fields only).
        await authorize(db, ctx, "tenancy.tenant:update", "platform", None)
        tenant.settings = body.settings.model_dump()
    if body.display_name is not None:
        tenant.display_name = body.display_name
    if body.description is not None:
        tenant.description = body.description

    tenant.version += 1
    tenant.updated_at = _now()
    tenant.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="tenant.archived" if body.status else "tenant.updated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="tenant",
        subject_id=tenant_id,
        source_module="M02",
        tenant_id=tenant_id,
        before_summary=before,
        after_summary={"display_name": tenant.display_name, "status": tenant.status},
    )
    await db.commit()
    if body.status:
        authz.invalidate_scope(tenant_id)
    set_etag(response, tenant.version)
    counts = await _counts_for_tenants(db, [tenant_id])
    return ApiResponse(data=_tenant_out(tenant, counts.get(tenant_id)))


async def _tenant_lifecycle(
    db: AsyncSession,
    ctx,
    tenant_id: str,
    target: Literal["suspended", "active"],
    reason: str | None,
) -> Tenant:
    await authorize(db, ctx, "tenancy.tenant:admin", "platform", None)
    tenant = await _tenant_or_404(db, tenant_id)
    if tenant.status == target:
        return tenant  # idempotent lifecycle verb (FDD M02-2)
    source = "active" if target == "suspended" else "suspended"
    if tenant.status != source:
        raise state_invalid(
            f"Action not allowed from status {tenant.status}.",
            allowed_transitions=[f"{source}->{target}"],
        )
    before = {"status": tenant.status}
    tenant.status = target
    tenant.suspend_reason = reason if target == "suspended" else None
    tenant.suspended_at = _now() if target == "suspended" else tenant.suspended_at
    tenant.version += 1
    tenant.updated_at = _now()
    tenant.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="tenant.suspended" if target == "suspended" else "tenant.reactivated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="tenant",
        subject_id=tenant_id,
        source_module="M02",
        tenant_id=tenant_id,
        before_summary=before,
        after_summary={"status": tenant.status},
        reason=reason,
    )
    await db.commit()
    authz.invalidate_scope(tenant_id)  # all checks in the tenant now deny/allow
    return tenant


@router.post(
    "/api/v1/admin/tenants/{tenant_id}:suspend",
    operation_id="m02_suspend_tenant",
    response_model=ApiResponse[TenantOut],
)
async def suspend_tenant(
    tenant_id: str, body: SuspendRequest, ctx: CurrentSession, db: DB
) -> ApiResponse[TenantOut]:
    tenant = await _tenant_lifecycle(db, ctx, tenant_id, "suspended", body.reason)
    return ApiResponse(data=_tenant_out(tenant))


@router.post(
    "/api/v1/admin/tenants/{tenant_id}:reactivate",
    operation_id="m02_reactivate_tenant",
    response_model=ApiResponse[TenantOut],
)
async def reactivate_tenant(
    tenant_id: str, ctx: CurrentSession, db: DB
) -> ApiResponse[TenantOut]:
    tenant = await _tenant_lifecycle(db, ctx, tenant_id, "active", None)
    return ApiResponse(data=_tenant_out(tenant))


# ---------------------------------------------------------------------------
# M02-5 / M02-6 Resource bindings (admin)
# ---------------------------------------------------------------------------


def _binding_out(binding: ResourceBinding, resource: Resource) -> BindingOut:
    return BindingOut(
        binding_id=binding.binding_id,
        tenant_id=binding.tenant_id,
        resource_id=binding.resource_id,
        resource_name=resource.name,
        resource_class=resource.resource_class,
        form=resource.form,
        binding_mode=binding.binding_mode,
        status=binding.status,
        purpose=binding.purpose,
        config=binding.config,
        bound_by=binding.bound_by,
        bound_at=binding.bound_at,
        released_at=binding.released_at,
        released_by=binding.released_by,
        version=binding.version,
    )


def _compute_binding_config(tenant: Tenant, resource: Resource, mode: str) -> dict:
    """Server-computed isolation config (M02-5 step 5; client cannot set it)."""
    kind = (resource.resource_class, resource.form)
    if kind == ("compute", "physical"):
        return {
            "taint": f"tenant={tenant.tenant_id}:NoSchedule",
            "node_label": f"tenant={tenant.tenant_id}",
            "toleration_injection": True,
        }
    if kind == ("compute", "logical"):
        node = resource.descriptor.get("compute_logical", {})
        return {
            "endpoint_ref": node.get("endpoint_url"),
            "credential_ref": resource.credential_ref,
            "capacity_view": node.get("capacity", {}),
        }
    if kind == ("storage", "physical"):
        node = resource.descriptor.get("storage_physical", {})
        return {
            "export_path": node.get("export_path"),
            "mount_subdir": tenant.tenant_id,
        }
    node = resource.descriptor.get("storage_logical", {})
    bucket = node.get("bucket", "")
    if mode == "shared":
        return {
            "prefix": f"{bucket}/tenants/{tenant.tenant_id}/",
            "credential_vending": "short_lived_tenant_scoped",
        }
    return {"bucket": bucket, "dedicated": True, "credential_vending": "short_lived_tenant_scoped"}


def _validate_binding_mode(tenant: Tenant, resource: Resource, mode: str) -> None:
    kind = (resource.resource_class, resource.form)
    if kind == ("compute", "logical") and mode != "exclusive":
        raise validation_error(
            "Logical compute services are tenant-dedicated; binding_mode must be exclusive."
        )
    if kind == ("storage", "logical") and mode == "exclusive":
        if tenant.settings.get("storage_isolation") != "dedicated_bucket":
            raise validation_error(
                "Exclusive logical-storage bindings require the dedicated_bucket isolation tier."
            )


@router.post(
    "/api/v1/admin/tenants/{tenant_id}/resource-bindings",
    operation_id="m02_create_resource_binding",
    status_code=201,
    response_model=ApiResponse[BindingOut],
)
async def create_resource_binding(
    tenant_id: str,
    body: BindingCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[BindingOut]:
    await authorize(db, ctx, "tenancy.resource_binding:create", "platform", None)
    payload = {"tenant_id": tenant_id, **body.model_dump()}
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m02_create_resource_binding", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[BindingOut].model_validate(replay["body"])

    tenant = await _tenant_or_404(db, tenant_id)
    if tenant.status == "suspended":
        raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
    if tenant.status == "archived":
        raise state_invalid("Tenant is archived.", allowed_transitions=[])

    resource = await db.get(Resource, body.resource_id)
    if resource is None or resource.status != "active":
        raise validation_error("Resource not found or not active.")
    _validate_binding_mode(tenant, resource, body.binding_mode)

    # Conflict checks (the partial unique indexes are the concurrency backstop).
    live = (
        await db.execute(
            select(ResourceBinding).where(
                ResourceBinding.resource_id == body.resource_id,
                ResourceBinding.status == "active",
            )
        )
    ).scalars().all()
    for other in live:
        if other.tenant_id == tenant_id:
            raise DomainError("E_CONFLICT", "This resource is already bound to this tenant.")
        if other.binding_mode == "exclusive" or body.binding_mode == "exclusive":
            raise DomainError(
                "E_TNT_BINDING_CONFLICT",
                "This resource is exclusively bound to another tenant."
                if other.binding_mode == "exclusive"
                else "Resource already has active bindings; exclusive bind not possible.",
            )

    if resource.form == "logical":
        # Re-probe at bind (M02-5).
        if not await probe_logical_resource(resource.descriptor):
            raise DomainError(
                "E_TNT_CREDENTIAL_INVALID",
                "Endpoint or credential rejected. The platform brokers existing services; "
                "verify the service is provisioned and reachable.",
            )

    binding = ResourceBinding(
        binding_id=new_id(PREFIX_BINDING),
        tenant_id=tenant_id,
        resource_id=body.resource_id,
        binding_mode=body.binding_mode,
        config=_compute_binding_config(tenant, resource, body.binding_mode),
        purpose=body.purpose,
        status="active",
        bound_at=_now(),
        bound_by=ctx.user_id,
        version=1,
    )
    db.add(binding)
    await emit_audit(
        db,
        action="tenant.resource_binding.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="resource_binding",
        subject_id=binding.binding_id,
        source_module="M02",
        tenant_id=tenant_id,
        after_summary={
            "resource_id": body.resource_id,
            "binding_mode": body.binding_mode,
            "resource_class": resource.resource_class,
            "form": resource.form,
        },
    )
    envelope = ApiResponse(data=_binding_out(binding, resource))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m02_create_resource_binding",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise DomainError(
            "E_TNT_BINDING_CONFLICT", "Concurrent binding conflict; reload and retry."
        ) from None
    return envelope


@router.get(
    "/api/v1/admin/tenants/{tenant_id}/resource-bindings",
    operation_id="m02_list_resource_bindings",
    response_model=ApiResponse[PageData[BindingOut]],
)
async def list_resource_bindings(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    resource_class: str | None = Query(None),
    form: str | None = Query(None),
    status: str | None = Query(None),
) -> ApiResponse[PageData[BindingOut]]:
    await authorize(db, ctx, "tenancy.resource_binding:create", "platform", None)
    await _tenant_or_404(db, tenant_id)
    stmt = (
        select(ResourceBinding, Resource)
        .join(Resource, Resource.resource_id == ResourceBinding.resource_id)
        .where(ResourceBinding.tenant_id == tenant_id)
        .order_by(ResourceBinding.bound_at.desc())
    )
    if resource_class:
        stmt = stmt.where(Resource.resource_class == resource_class)
    if form:
        stmt = stmt.where(Resource.form == form)
    if status:
        stmt = stmt.where(ResourceBinding.status == status)

    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).all()
    items = [_binding_out(b, r) for b, r in rows]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.delete(
    "/api/v1/admin/tenants/{tenant_id}/resource-bindings/{binding_id}",
    operation_id="m02_release_resource_binding",
    status_code=204,
)
async def release_resource_binding(
    tenant_id: str, binding_id: str, ctx: CurrentSession, db: DB
) -> Response:
    await authorize(db, ctx, "tenancy.resource_binding:delete", "platform", None)
    binding = await db.get(ResourceBinding, binding_id)
    if binding is None or binding.tenant_id != tenant_id:
        raise not_found("Binding not found.")
    if binding.status == "released":
        return Response(status_code=204)  # idempotent

    # Guard: no project declares this binding as default storage (M02-6;
    # workflow runs cannot exist in this scope-locked build — M16 is a stub).
    dependent = (
        await db.execute(
            select(Project.project_id).where(
                Project.default_storage_binding_id == binding_id,
                Project.status == "active",
            )
        )
    ).scalars().all()
    if dependent:
        raise DomainError(
            "E_TNT_RESOURCE_IN_USE",
            "Active workloads or stored data still reference this binding. Drain before release.",
            details=[{"project_ids": list(dependent)}],
        )
    binding.status = "released"
    binding.released_at = _now()
    binding.released_by = ctx.user_id
    binding.version += 1
    await emit_audit(
        db,
        action="tenant.resource_binding.released",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="resource_binding",
        subject_id=binding_id,
        source_module="M02",
        tenant_id=tenant_id,
    )
    await db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# M02-7 Tenant self view + bindings (TA/RD read, sanitized)
# ---------------------------------------------------------------------------


async def _authorize_tenant_read_or_404(db: AsyncSession, ctx, tenant_id: str) -> Tenant:
    """Cross-tenant non-disclosure: deny -> 404 (FDD M02-7)."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise not_found("Tenant not found.")
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.tenant:read",
        scope_type="tenant", scope_id=tenant_id,
    )
    if not decision.allowed:
        if decision.reason == "tenant_suspended":
            raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
        raise not_found("Tenant not found.")
    return tenant


@router.get(
    "/api/v1/tenants/{tenant_id}",
    operation_id="m02_get_tenant_self",
    response_model=ApiResponse[TenantPublicOut],
)
async def get_tenant_self(tenant_id: str, ctx: CurrentSession, db: DB) -> ApiResponse[TenantPublicOut]:
    tenant = await _authorize_tenant_read_or_404(db, ctx, tenant_id)
    return ApiResponse(
        data=TenantPublicOut(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            status=tenant.status,
            settings={"storage_isolation": tenant.settings.get("storage_isolation")},
            version=tenant.version,
            created_at=tenant.created_at,
        )
    )


def _capacity_view(resource: Resource) -> dict:
    d = resource.descriptor
    if resource.resource_class == "compute" and resource.form == "physical":
        node = d.get("compute_physical", {})
        return {k: node.get(k) for k in ("gpu_model", "gpu_count", "cpu_cores", "memory_gib")}
    if resource.resource_class == "compute" and resource.form == "logical":
        return dict(d.get("compute_logical", {}).get("capacity", {}))
    if resource.resource_class == "storage" and resource.form == "physical":
        return {"capacity_gib": d.get("storage_physical", {}).get("capacity_gib")}
    return {"capacity_gib": d.get("storage_logical", {}).get("capacity_gib")}


@router.get(
    "/api/v1/tenants/{tenant_id}/resource-bindings",
    operation_id="m02_list_tenant_bindings_self",
    response_model=ApiResponse[PageData[BindingPublicOut]],
)
async def list_tenant_bindings_self(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
) -> ApiResponse[PageData[BindingPublicOut]]:
    await _authorize_tenant_read_or_404(db, ctx, tenant_id)
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.resource_binding:read",
        scope_type="tenant", scope_id=tenant_id,
    )
    if not decision.allowed:
        raise not_found("Tenant not found.")
    stmt = (
        select(ResourceBinding, Resource)
        .join(Resource, Resource.resource_id == ResourceBinding.resource_id)
        .where(ResourceBinding.tenant_id == tenant_id, ResourceBinding.status == "active")
        .order_by(ResourceBinding.bound_at.desc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).all()
    items = [
        BindingPublicOut(
            binding_id=b.binding_id,
            resource_name=r.name,
            resource_class=r.resource_class,
            form=r.form,
            binding_mode=b.binding_mode,
            status=b.status,
            capacity_view=_capacity_view(r),
            health=r.health,
            bound_at=b.bound_at,
        )
        for b, r in rows
    ]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))
