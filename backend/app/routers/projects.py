"""M02 — Projects & membership (FDD §2.2.3: M02-8, M02-9, M02-10)."""
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
from app.core.errors import DomainError, not_found, state_invalid, validation_error
from app.core.ids import PREFIX_PROJECT, new_id
from app.core.pagination import PageParams, page_params, paginate
from app.database import get_db
from app.models.iam import User
from app.models.tenancy import Project, ProjectMember, Resource, ResourceBinding, Tenant
from app.schemas.response import ApiResponse, PageData
from app.schemas.tenancy import MemberOut, MemberPut, ProjectCreate, ProjectOut, ProjectPatch
from app.services import authz
from app.services.audit import emit_audit
from app.services.catalog import PROJECT_ASSIGNABLE_TEMPLATES
from app.services.membership import materialize_membership_bindings, remove_membership_bindings

router = APIRouter(tags=["M02 Tenant & Resource"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _project_out(project: Project, members_count: int | None = None) -> ProjectOut:
    return ProjectOut(
        project_id=project.project_id,
        tenant_id=project.tenant_id,
        name=project.name,
        display_name=project.display_name,
        description=project.description,
        status=project.status,
        owner_user_id=project.owner_user_id,
        default_storage_binding_id=project.default_storage_binding_id,
        version=project.version,
        created_at=project.created_at,
        created_by=project.created_by,
        archived_at=project.archived_at,
        members_count=members_count,
    )


async def _project_or_404(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise not_found("Project not found.")
    return project


async def _validate_storage_binding(
    db: AsyncSession, tenant_id: str, binding_id: str | None, required_if_available: bool
) -> None:
    storage_bindings = (
        await db.execute(
            select(ResourceBinding.binding_id)
            .join(Resource, Resource.resource_id == ResourceBinding.resource_id)
            .where(
                ResourceBinding.tenant_id == tenant_id,
                ResourceBinding.status == "active",
                Resource.resource_class == "storage",
            )
        )
    ).scalars().all()
    if binding_id is None:
        if required_if_available and storage_bindings:
            raise validation_error(
                "default_storage_binding_id is required when the tenant has storage bindings."
            )
        return
    if binding_id not in storage_bindings:
        raise validation_error(
            "default_storage_binding_id must reference an active storage binding of this tenant."
        )


async def _validate_owner(db: AsyncSession, owner_user_id: str) -> None:
    owner = await db.get(User, owner_user_id)
    if owner is None or owner.status == "deactivated":
        raise validation_error("Owner must be an invited or active user.")


# ---------------------------------------------------------------------------
# M02-8 Create / list projects
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/tenants/{tenant_id}/projects",
    operation_id="m02_create_project",
    status_code=201,
    response_model=ApiResponse[ProjectOut],
)
async def create_project(
    tenant_id: str,
    body: ProjectCreate,
    ctx: CurrentSession,
    db: DB,
    response: Response,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ApiResponse[ProjectOut]:
    await authorize(db, ctx, "tenancy.project:create", "tenant", tenant_id)
    payload = {"tenant_id": tenant_id, **body.model_dump()}
    replay = await check_idempotency(
        db, key=idempotency_key, endpoint="m02_create_project", payload=payload
    )
    if replay is not None:
        response.headers["Idempotency-Replayed"] = "true"
        return ApiResponse[ProjectOut].model_validate(replay["body"])

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise not_found("Tenant not found.")
    if tenant.status != "active":
        raise state_invalid(f"Tenant is {tenant.status}.", allowed_transitions=[])

    duplicate = (
        await db.execute(
            select(Project.project_id).where(
                Project.tenant_id == tenant_id, Project.name == body.name
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        raise DomainError("E_CONFLICT", "A project with this name already exists in this tenant.")

    await _validate_owner(db, body.owner_user_id)
    await _validate_storage_binding(
        db, tenant_id, body.default_storage_binding_id, required_if_available=True
    )

    project = Project(
        project_id=new_id(PREFIX_PROJECT),
        tenant_id=tenant_id,
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        owner_user_id=body.owner_user_id,
        default_storage_binding_id=body.default_storage_binding_id,
        status="active",
        version=1,
        created_at=_now(),
        created_by=ctx.user_id,
    )
    db.add(project)
    await emit_audit(
        db,
        action="tenant.project.created",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="project",
        subject_id=project.project_id,
        source_module="M02",
        tenant_id=tenant_id,
        project_id=project.project_id,
        after_summary={"name": body.name, "owner_user_id": body.owner_user_id},
    )
    envelope = ApiResponse(data=_project_out(project, 0))
    await store_idempotency(
        db,
        key=idempotency_key,
        endpoint="m02_create_project",
        payload=payload,
        response_status=201,
        response_body=envelope.model_dump(mode="json"),
    )
    await db.commit()
    return envelope


@router.get(
    "/api/v1/tenants/{tenant_id}/projects",
    operation_id="m02_list_projects",
    response_model=ApiResponse[PageData[ProjectOut]],
)
async def list_projects(
    tenant_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, max_length=120),
    status: str | None = Query(None),
    owner_id: str | None = Query(None),
) -> ApiResponse[PageData[ProjectOut]]:
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.project:read",
        scope_type="tenant", scope_id=tenant_id,
    )
    stmt = select(Project).where(Project.tenant_id == tenant_id)
    if not decision.allowed:
        # RD without tenant-wide read sees only assigned projects (scope-limited).
        assigned = (
            await db.execute(
                select(ProjectMember.project_id).where(ProjectMember.user_id == ctx.user_id)
            )
        ).scalars().all()
        if not assigned:
            if decision.reason == "tenant_suspended":
                raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
            raise not_found("Tenant not found.")
        stmt = stmt.where(Project.project_id.in_(assigned))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Project.name.ilike(like) | Project.display_name.ilike(like))
    if status:
        stmt = stmt.where(Project.status == status)
    if owner_id:
        stmt = stmt.where(Project.owner_user_id == owner_id)
    stmt = stmt.order_by(Project.created_at.desc())
    rows, next_token, total = await paginate(db, stmt, page)

    counts: dict[str, int] = {}
    if rows:
        counts = dict(
            (
                await db.execute(
                    select(ProjectMember.project_id, func.count())
                    .where(ProjectMember.project_id.in_([p.project_id for p in rows]))
                    .group_by(ProjectMember.project_id)
                )
            ).all()
        )
    items = [_project_out(p, counts.get(p.project_id, 0)) for p in rows]
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


# ---------------------------------------------------------------------------
# M02-9 Project detail / update / archive
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/projects/{project_id}",
    operation_id="m02_get_project",
    response_model=ApiResponse[ProjectOut],
)
async def get_project(
    project_id: str, ctx: CurrentSession, db: DB, response: Response
) -> ApiResponse[ProjectOut]:
    project = await _project_or_404(db, project_id)
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.project:read",
        scope_type="project", scope_id=project_id,
    )
    if not decision.allowed:
        if decision.reason == "tenant_suspended":
            raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
        raise not_found("Project not found.")
    members = (
        await db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
    ).scalar_one()
    set_etag(response, project.version)
    return ApiResponse(data=_project_out(project, members))


@router.patch(
    "/api/v1/projects/{project_id}",
    operation_id="m02_update_project",
    response_model=ApiResponse[ProjectOut],
)
async def update_project(
    project_id: str,
    body: ProjectPatch,
    request: Request,
    ctx: CurrentSession,
    db: DB,
    response: Response,
) -> ApiResponse[ProjectOut]:
    project = await _project_or_404(db, project_id)
    await authorize(db, ctx, "tenancy.project:update", "tenant", project.tenant_id)
    require_if_match(request, project.version)
    if project.status == "archived":
        raise state_invalid("This project is archived (read-only).", allowed_transitions=[])

    if body.owner_user_id is not None:
        await _validate_owner(db, body.owner_user_id)
        project.owner_user_id = body.owner_user_id
    if body.default_storage_binding_id is not None:
        await _validate_storage_binding(
            db, project.tenant_id, body.default_storage_binding_id, required_if_available=False
        )
        project.default_storage_binding_id = body.default_storage_binding_id
    if body.display_name is not None:
        project.display_name = body.display_name
    if body.description is not None:
        project.description = body.description

    project.version += 1
    project.updated_at = _now()
    project.updated_by = ctx.user_id
    await emit_audit(
        db,
        action="tenant.project.updated",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="project",
        subject_id=project_id,
        source_module="M02",
        tenant_id=project.tenant_id,
        project_id=project_id,
    )
    await db.commit()
    set_etag(response, project.version)
    return ApiResponse(data=_project_out(project))


@router.post(
    "/api/v1/projects/{project_id}:archive",
    operation_id="m02_archive_project",
    response_model=ApiResponse[ProjectOut],
)
async def archive_project(project_id: str, ctx: CurrentSession, db: DB) -> ApiResponse[ProjectOut]:
    project = await _project_or_404(db, project_id)
    await authorize(db, ctx, "tenancy.project:admin", "tenant", project.tenant_id)
    if project.status == "archived":
        return ApiResponse(data=_project_out(project))  # idempotent
    # Guard "no non-terminal workflow runs" (M16): trivially satisfied —
    # M16 is a zero-implementation stub, no runs can exist.
    project.status = "archived"
    project.archived_at = _now()
    project.archived_by = ctx.user_id
    project.version += 1
    await emit_audit(
        db,
        action="tenant.project.archived",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="project",
        subject_id=project_id,
        source_module="M02",
        tenant_id=project.tenant_id,
        project_id=project_id,
    )
    await db.commit()
    authz.invalidate_scope(project_id)  # archived => business writes deny (M03-10 step 2)
    return ApiResponse(data=_project_out(project))


# ---------------------------------------------------------------------------
# M02-10 Project membership (persona-template assignment)
# ---------------------------------------------------------------------------


@router.put(
    "/api/v1/projects/{project_id}/members/{user_id}",
    operation_id="m02_upsert_project_member",
    response_model=ApiResponse[MemberOut],
)
async def upsert_project_member(
    project_id: str,
    user_id: str,
    body: MemberPut,
    ctx: CurrentSession,
    db: DB,
) -> ApiResponse[MemberOut]:
    project = await _project_or_404(db, project_id)
    await authorize(db, ctx, "tenancy.project_member:update", "tenant", project.tenant_id)
    if project.status != "active":
        raise state_invalid("This project is archived (read-only).", allowed_transitions=[])

    user = await db.get(User, user_id)
    if user is None or user.status == "deactivated":
        raise validation_error("User must exist with status invited or active.")
    unknown = [t for t in body.persona_templates if t not in PROJECT_ASSIGNABLE_TEMPLATES]
    if unknown:
        raise validation_error(
            "Unknown or non-project-assignable persona template(s).",
            details=[{"unknown_templates": unknown}],
        )

    member = await db.get(ProjectMember, (project_id, user_id))
    if member is None:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            persona_templates=list(dict.fromkeys(body.persona_templates)),
            note=body.note,
            added_at=_now(),
            added_by=ctx.user_id,
        )
        db.add(member)
    else:
        member.persona_templates = list(dict.fromkeys(body.persona_templates))
        member.note = body.note
        member.updated_at = _now()
        member.updated_by = ctx.user_id

    # M03 materialization (FDD M02-10 step 4) — same transaction in-monolith.
    await materialize_membership_bindings(
        db, project_id=project_id, user_id=user_id, persona_templates=member.persona_templates
    )
    await emit_audit(
        db,
        action="tenant.project.member_upserted",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="project_member",
        subject_id=f"{project_id}/{user_id}",
        source_module="M02",
        tenant_id=project.tenant_id,
        project_id=project_id,
        after_summary={"persona_templates": member.persona_templates},
    )
    await db.commit()
    return ApiResponse(
        data=MemberOut(
            user_id=user_id,
            display_name=user.display_name,
            email=user.email,
            user_status=user.status,
            persona_templates=list(member.persona_templates),
            note=member.note,
            added_by=member.added_by,
            added_at=member.added_at,
        )
    )


@router.get(
    "/api/v1/projects/{project_id}/members",
    operation_id="m02_list_project_members",
    response_model=ApiResponse[PageData[MemberOut]],
)
async def list_project_members(
    project_id: str,
    ctx: CurrentSession,
    db: DB,
    page: Annotated[PageParams, Depends(page_params)],
) -> ApiResponse[PageData[MemberOut]]:
    project = await _project_or_404(db, project_id)
    decision = await authz.check_permission(
        db, user_id=ctx.user_id, permission_key="tenancy.project_member:read",
        scope_type="project", scope_id=project_id,
    )
    if not decision.allowed:
        raise not_found("Project not found.")
    stmt = (
        select(ProjectMember, User)
        .join(User, User.user_id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.added_at.asc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).all()
    items = [
        MemberOut(
            user_id=m.user_id,
            display_name=u.display_name,
            email=u.email,
            user_status=u.status,
            persona_templates=list(m.persona_templates),
            note=m.note,
            added_by=m.added_by,
            added_at=m.added_at,
        )
        for m, u in rows
    ]
    next_token = page.next_token if page.offset + len(items) < total else None
    return ApiResponse(data=PageData(items=items, next_page_token=next_token, total_size=total))


@router.delete(
    "/api/v1/projects/{project_id}/members/{user_id}",
    operation_id="m02_remove_project_member",
    status_code=204,
)
async def remove_project_member(
    project_id: str, user_id: str, ctx: CurrentSession, db: DB
) -> Response:
    project = await _project_or_404(db, project_id)
    await authorize(db, ctx, "tenancy.project_member:delete", "tenant", project.tenant_id)
    member = await db.get(ProjectMember, (project_id, user_id))
    if member is not None:
        await db.delete(member)
        await remove_membership_bindings(db, project_id=project_id, user_id=user_id)
        await emit_audit(
            db,
            action="tenant.project.member_removed",
            actor_type="user",
            actor_id=ctx.user_id,
            subject_type="project_member",
            subject_id=f"{project_id}/{user_id}",
            source_module="M02",
            tenant_id=project.tenant_id,
            project_id=project_id,
        )
        await db.commit()
    return Response(status_code=204)
