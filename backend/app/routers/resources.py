"""M02 — Platform resource inventory (FDD §2.2.3: M02-3, M02-4)."""
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
from app.core.ids import PREFIX_RESOURCE, new_id
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import encrypt_secret
from app.database import get_db
from app.models.tenancy import Resource, ResourceBinding, ResourceCredential
from app.schemas.response import ApiResponse, PageData
from app.schemas.tenancy import (
    ResourceCreate,
    ResourceCredentialIn,
    ResourceOut,
    ResourcePatch,
)
from app.services.audit import emit_audit
from app.services.probes import probe_logical_resource

router = APIRouter(tags=["M02 Tenant & Resource"])

DB = Annotated[AsyncSession, Depends(get_db)]

_DESCRIPTOR_BRANCH = {
    ("compute", "physical"): "compute_physical",
    ("compute", "logical"): "compute_logical",
    ("storage", "physical"): "storage_physical",
    ("storage", "logical"): "storage_logical",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validated_descriptor(body_descriptor, resource_class: str, form: str) -> dict:
    """Exactly one branch present, matching class x form (M02-3)."""
    expected = _DESCRIPTOR_BRANCH[(resource_class, form)]
    raw = body_descriptor.model_dump(exclude_none=True)
    present = list(raw.keys())
    if present != [expected]:
        raise validation_error(
            f"Descriptor must contain exactly the '{expected}' branch for "
            f"{resource_class}/{form}.",
            details=[{"present": present, "expected": [expected]}],
        )
    return raw


def _credential_secret(credential: ResourceCredentialIn | None) -> str | None:
    if credential is None:
        return None
    parts = {
        k: v
        for k, v in credential.model_dump().items()
        if v
    }
    if not parts:
        return None
    import json

    return json.dumps(parts, sort_keys=True)


def _resource_out(resource: Resource, bindings_count: int | None = None) -> ResourceOut:
    return ResourceOut(
        resource_id=resource.resource_id,
        name=resource.name,
        resource_class=resource.resource_class,
        form=resource.form,
        descriptor=resource.descriptor,
        credential_ref=resource.credential_ref,
        health=resource.health,
        last_probe_at=resource.last_probe_at,
        status=resource.status,
        labels=resource.labels,
        version=resource.version,
        created_at=resource.created_at,
        created_by=resource.created_by,
        decommissioned_at=resource.decommissioned_at,
        bindings_count=bindings_count,
    )


async def _resource_or_404(db: AsyncSession, resource_id: str) -> Resource:
    resource = await db.get(Resource, resource_id)
    if resource is None:
        raise not_found("Resource not found.")
    return resource


@router.post(
    "/api/v1/admin/resources",
    operation_id="m02_register_resource",
    status_code=201,
    response_model=ApiResponse[ResourceOut],
)
async def register_resource(
    body: ResourceCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[ResourceOut]:
    """Registers an inventory descriptor of externally provisioned equipment;
    provisions nothing (DA-20)."""
    await authorize(db, ctx, "infra.resource:create", "platform", None)
    payload = body.model_dump(exclude={"credential"})  # secrets never in idempotency store
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m02_register_resource", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[ResourceOut].model_validate(replay["body"])

    exists = (
        await db.execute(select(Resource.resource_id).where(Resource.name == body.name))
    ).scalar_one_or_none()
    if exists:
        raise DomainError("E_CONFLICT", "A resource with this name already exists.")

    descriptor = _validated_descriptor(body.descriptor, body.resource_class, body.form)
    secret = _credential_secret(body.credential)
    credential_ref: str | None = None
    health: str | None = None
    resource_id = new_id(PREFIX_RESOURCE)

    if body.form == "logical":
        if secret is None:
            raise validation_error("Logical resources require a credential.")
        credential_ref = f"vault://resources/{resource_id}"
        reachable = await probe_logical_resource(descriptor)
        if not reachable:
            raise DomainError(
                "E_TNT_CREDENTIAL_INVALID",
                "Endpoint or credential rejected. The platform brokers existing services; "
                "verify the service is provisioned and reachable (it is not created by the platform).",
            )
        health = "reachable"

    resource = Resource(
        resource_id=resource_id,
        name=body.name,
        resource_class=body.resource_class,
        form=body.form,
        descriptor=descriptor,
        credential_ref=credential_ref,
        health=health if body.form == "logical" else None,
        last_probe_at=_now() if body.form == "logical" else None,
        status="active",
        labels=body.labels,
        version=1,
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(resource)
    if secret is not None:
        db.add(
            ResourceCredential(
                resource_id=resource_id,
                secret_encrypted=encrypt_secret(secret),
                updated_at=_now(),
            )
        )
    await emit_audit(
        db,
        action="infra.resource.registered",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="resource",
        subject_id=resource_id,
        source_module="M02",
        after_summary={
            "name": body.name,
            "resource_class": body.resource_class,
            "form": body.form,
        },
    )
    envelope = ApiResponse(data=_resource_out(resource, 0))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m02_register_resource",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    return envelope


@router.get(
    "/api/v1/admin/resources",
    operation_id="m02_list_resources",
    response_model=ApiResponse[PageData[ResourceOut]],
)
async def list_resources(
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    resource_class: str | None = Query(None),
    form: str | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None, max_length=120),
) -> ApiResponse[PageData[ResourceOut]]:
    await authorize(db, ctx, "infra.resource:read", "platform", None)
    stmt = select(Resource).order_by(Resource.created_at.desc())
    if resource_class:
        stmt = stmt.where(Resource.resource_class == resource_class)
    if form:
        stmt = stmt.where(Resource.form == form)
    if status:
        stmt = stmt.where(Resource.status == status)
    if q:
        stmt = stmt.where(Resource.name.ilike(f"%{q.strip()}%"))
    rows, next_token, total = await paginate(db, stmt, page)

    counts: dict[str, int] = {}
    if rows:
        counts = dict(
            (
                await db.execute(
                    select(ResourceBinding.resource_id, func.count())
                    .where(
                        ResourceBinding.resource_id.in_([r.resource_id for r in rows]),
                        ResourceBinding.status == "active",
                    )
                    .group_by(ResourceBinding.resource_id)
                )
            ).all()
        )
    items = [_resource_out(r, counts.get(r.resource_id, 0)) for r in rows]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.get(
    "/api/v1/admin/resources/{resource_id}",
    operation_id="m02_get_resource",
    response_model=ApiResponse[ResourceOut],
)
async def get_resource(
    resource_id: str, ctx: CurrentSession, db: DB, response: Response
) -> ApiResponse[ResourceOut]:
    await authorize(db, ctx, "infra.resource:read", "platform", None)
    resource = await _resource_or_404(db, resource_id)
    count = (
        await db.execute(
            select(func.count())
            .select_from(ResourceBinding)
            .where(
                ResourceBinding.resource_id == resource_id, ResourceBinding.status == "active"
            )
        )
    ).scalar_one()
    set_etag(response, resource.version)
    return ApiResponse(data=_resource_out(resource, count))


@router.patch(
    "/api/v1/admin/resources/{resource_id}",
    operation_id="m02_update_resource",
    response_model=ApiResponse[ResourceOut],
)
async def update_resource(
    resource_id: str,
    body: ResourcePatch,
    request: Request,
    ctx: CurrentSession,
    db: DB,
    response: Response,
) -> ApiResponse[ResourceOut]:
    await authorize(db, ctx, "infra.resource:update", "platform", None)
    resource = await _resource_or_404(db, resource_id)
    require_if_match(request, resource.version)
    if resource.status != "active":
        raise DomainError("E_STATE_INVALID", "Decommissioned resources are immutable.")

    if body.descriptor is not None:
        # class/form immutable; the branch must still match.
        resource.descriptor = _validated_descriptor(
            body.descriptor, resource.resource_class, resource.form
        )
    if body.labels is not None:
        if len(body.labels) > 20:
            raise validation_error("At most 20 label pairs.")
        resource.labels = body.labels
    if body.credential is not None:
        secret = _credential_secret(body.credential)
        if secret is None:
            raise validation_error("Credential rotation requires a non-empty secret.")
        if resource.form != "logical":
            raise validation_error("Only logical resources carry credentials.")
        existing = await db.get(ResourceCredential, resource_id)
        if existing is None:
            db.add(
                ResourceCredential(
                    resource_id=resource_id,
                    secret_encrypted=encrypt_secret(secret),
                    updated_at=_now(),
                )
            )
        else:
            existing.secret_encrypted = encrypt_secret(secret)
            existing.updated_at = _now()

    resource.version += 1
    resource.updated_at = _now()
    resource.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="infra.resource.updated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="resource",
        subject_id=resource_id,
        source_module="M02",
    )
    await db.commit()
    set_etag(response, resource.version)
    return ApiResponse(data=_resource_out(resource))


@router.post(
    "/api/v1/admin/resources/{resource_id}:decommission",
    operation_id="m02_decommission_resource",
    response_model=ApiResponse[ResourceOut],
)
async def decommission_resource(
    resource_id: str, ctx: CurrentSession, db: DB
) -> ApiResponse[ResourceOut]:
    await authorize(db, ctx, "infra.resource:admin", "platform", None)
    resource = await _resource_or_404(db, resource_id)
    if resource.status == "decommissioned":
        return ApiResponse(data=_resource_out(resource))  # idempotent

    blockers = (
        await db.execute(
            select(ResourceBinding.binding_id).where(
                ResourceBinding.resource_id == resource_id, ResourceBinding.status == "active"
            )
        )
    ).scalars().all()
    if blockers:
        raise DomainError(
            "E_TNT_RESOURCE_IN_USE",
            "Release these bindings first.",
            details=[{"binding_ids": list(blockers)}],
        )
    resource.status = "decommissioned"
    resource.decommissioned_at = _now()
    resource.version += 1
    await emit_audit(
        db,
        action="infra.resource.decommissioned",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="resource",
        subject_id=resource_id,
        source_module="M02",
    )
    await db.commit()
    return ApiResponse(data=_resource_out(resource))
