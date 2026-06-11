"""M01 — Platform Login & Session Management (FDD §2.1.3, endpoints M01-1..7
plus the ARCHITECTURE §2.6 silent-refresh endpoint)."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    SESSION_COOKIE,
    CurrentSession,
    authorize,
    introspection_cache,
    purge_session_cache,
    require_service_identity,
)
from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.errors import DomainError, not_found
from app.core.security import hash_session_token, issue_access_token
from app.database import get_db
from app.models.auth import Session as AuthSession
from app.models.iam import Role, RoleBinding, User
from app.models.tenancy import Project, ProjectMember, Tenant
from app.schemas.auth import (
    CurrentSessionResponse,
    IntrospectRequest,
    IntrospectResponse,
    LoginCodeAccepted,
    LoginCodeRequest,
    PermissionSummary,
    PermissionSummaryScope,
    ProjectMembershipInfo,
    RevokeAllResponse,
    SessionCreated,
    SessionCreateRequest,
    SessionInfo,
    SessionRefreshed,
    SessionRefreshRequest,
    SessionUser,
    SwitchTenantRequest,
    SwitchTenantResponse,
    TenantMembershipInfo,
)
from app.schemas.response import ApiResponse
from app.services import authz, login as login_service
from app.services.audit import emit_audit
from app.services.catalog import UI_CAPABILITY_PROBE_KEYS
from app.services.mailer import send_login_code_safe

router = APIRouter(tags=["M01 Login & Session"])

# M01-3 response cache (FDD: cached 30 s per session).
_current_session_cache = TTLCache(ttl_s=30)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_absolute_ttl_s,
        httponly=True,
        secure=settings.environment == "prod",
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post(
    "/api/v1/auth/login-codes",
    operation_id="m01_request_login_code",
    status_code=202,
    response_model=ApiResponse[LoginCodeAccepted],
)
async def request_login_code(
    body: LoginCodeRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[LoginCodeAccepted]:
    """Anonymous. Always 202 with an identical body (anti-enumeration)."""
    login_service.enforce_ip_throttle(_client_ip(request))
    code = await login_service.issue_login_code(db, email=body.email, client_ip=_client_ip(request))
    if code is not None:
        # Post-commit delivery (outbox->SVC-14 equivalent); failures only logged.
        await send_login_code_safe(body.email, code)
    return ApiResponse(data=LoginCodeAccepted(resend_available_in_s=get_settings().resend_cooldown_s))


@router.post(
    "/api/v1/auth/sessions",
    operation_id="m01_create_session",
    status_code=201,
    response_model=ApiResponse[SessionCreated],
)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SessionCreated]:
    """M01-2: verify email+code, create session (dual-token response)."""
    await login_service.enforce_verify_backoff(db, body.email)
    session, token, user = await login_service.verify_code_and_create_session(
        db,
        email=body.email,
        code=body.code,
        user_agent=(body.client.user_agent if body.client else None) or request.headers.get("user-agent"),
        device_label=body.client.device_label if body.client else None,
    )
    access_token, access_expires_at = issue_access_token(
        user_id=user.user_id, session_id=session.session_id
    )
    _set_session_cookie(response, token)
    return ApiResponse(
        data=SessionCreated(
            session_token=token,
            access_token=access_token,
            access_expires_at=access_expires_at,
            session_id=session.session_id,
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
            user=SessionUser(
                user_id=user.user_id,
                display_name=user.display_name,
                email=user.email,
                status=user.status,
            ),
            active_tenant_id=session.active_tenant_id,
            tenant_selection_required=session.active_tenant_id is None,
        )
    )


@router.post(
    "/api/v1/auth/sessions/refresh",
    operation_id="m01_refresh_access_token",
    response_model=ApiResponse[SessionRefreshed],
)
async def refresh_access_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: SessionRefreshRequest | None = None,
) -> ApiResponse[SessionRefreshed]:
    """Silent-refresh endpoint (ARCHITECTURE §2.6): exchanges the long-lived
    opaque session token (httpOnly cookie) for a fresh short-lived access JWT.
    Applies the M01-7 introspection rules: status + both expiries, sliding idle."""
    token = (body.session_token if body else None) or request.cookies.get(SESSION_COOKIE)
    if not token:
        raise DomainError("E_UNAUTHENTICATED", "No session credential present.")
    session = (
        await db.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(token))
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if session is None or session.status != "active":
        raise DomainError("E_UNAUTHENTICATED", "Your session has expired. Sign in again.")
    if session.absolute_expires_at <= now or session.idle_expires_at <= now:
        session.status = "expired"
        await db.commit()
        purge_session_cache(session.session_id)
        raise DomainError("E_UNAUTHENTICATED", "Your session has expired. Sign in again.")

    settings = get_settings()
    session.idle_expires_at = now + timedelta(seconds=settings.session_idle_ttl_s)
    session.last_seen_at = now
    await db.commit()

    access_token, access_expires_at = issue_access_token(
        user_id=session.user_id, session_id=session.session_id
    )
    return ApiResponse(
        data=SessionRefreshed(
            access_token=access_token,
            access_expires_at=access_expires_at,
            session_id=session.session_id,
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
        )
    )


@router.get(
    "/api/v1/auth/sessions/current",
    operation_id="m01_current_session",
    response_model=ApiResponse[CurrentSessionResponse],
)
async def current_session(
    ctx: CurrentSession,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CurrentSessionResponse]:
    """M01-3: user, tenants, roles, effective permission summary."""
    cached = _current_session_cache.get(ctx.session_id)
    if cached is not None:
        return ApiResponse(data=cached)

    session = await db.get(AuthSession, ctx.session_id)
    user = await db.get(User, ctx.user_id)
    if session is None or user is None:
        raise DomainError("E_UNAUTHENTICATED", "Your session has expired. Sign in again.")

    tenant_ids = await login_service.assigned_tenant_ids(db, user.user_id)
    tenants: list[TenantMembershipInfo] = []
    if tenant_ids:
        tenant_rows = (
            (await db.execute(select(Tenant).where(Tenant.tenant_id.in_(tenant_ids)))).scalars().all()
        )
        binding_rows = (
            await db.execute(
                select(RoleBinding, Role.role_id)
                .join(Role, Role.role_id == RoleBinding.role_id)
                .where(RoleBinding.user_id == user.user_id, RoleBinding.deleted_at.is_(None))
            )
        ).all()
        membership_rows = (
            await db.execute(
                select(ProjectMember, Project)
                .join(Project, Project.project_id == ProjectMember.project_id)
                .where(ProjectMember.user_id == user.user_id, Project.status == "active")
            )
        ).all()
        for tenant in sorted(tenant_rows, key=lambda t: t.name):
            roles: set[str] = set()
            for binding, role_id in binding_rows:
                if binding.scope_type == "platform":
                    roles.add(role_id)
                elif binding.scope_type == "tenant" and binding.scope_id == tenant.tenant_id:
                    roles.add(role_id)
            projects: list[ProjectMembershipInfo] = []
            for member, project in membership_rows:
                if project.tenant_id == tenant.tenant_id:
                    projects.append(
                        ProjectMembershipInfo(
                            project_id=project.project_id,
                            name=project.name,
                            persona_templates=list(member.persona_templates),
                        )
                    )
            tenants.append(
                TenantMembershipInfo(
                    tenant_id=tenant.tenant_id,
                    name=tenant.display_name,
                    status=tenant.status,
                    roles=sorted(roles),
                    projects=projects,
                )
            )

    permission_summary: PermissionSummary | None = None
    if session.active_tenant_id:
        allowed: list[str] = []
        for key in UI_CAPABILITY_PROBE_KEYS:
            decision = await authz.check_permission(
                db,
                user_id=user.user_id,
                permission_key=key,
                scope_type="tenant",
                scope_id=session.active_tenant_id,
            )
            if decision.allowed:
                allowed.append(key)
        permission_summary = PermissionSummary(
            scope=PermissionSummaryScope(type="tenant", id=session.active_tenant_id),
            allowed_keys=allowed,
        )
    else:
        # Platform-scope probe still useful for PA/OE without tenant context.
        allowed = []
        for key in UI_CAPABILITY_PROBE_KEYS:
            decision = await authz.check_permission(
                db,
                user_id=user.user_id,
                permission_key=key,
                scope_type="platform",
                scope_id=None,
            )
            if decision.allowed:
                allowed.append(key)
        permission_summary = PermissionSummary(
            scope=PermissionSummaryScope(type="platform", id=None), allowed_keys=allowed
        )

    payload = CurrentSessionResponse(
        session=SessionInfo(
            session_id=session.session_id,
            created_at=session.created_at,
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
        ),
        user=SessionUser(
            user_id=user.user_id,
            display_name=user.display_name,
            email=user.email,
            status=user.status,
        ),
        active_tenant_id=session.active_tenant_id,
        tenants=tenants,
        permission_summary=permission_summary,
    )
    _current_session_cache.set(ctx.session_id, payload)
    return ApiResponse(data=payload)


@router.put(
    "/api/v1/auth/sessions/current/active-tenant",
    operation_id="m01_switch_active_tenant",
    response_model=ApiResponse[SwitchTenantResponse],
)
async def switch_active_tenant(
    body: SwitchTenantRequest,
    ctx: CurrentSession,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SwitchTenantResponse]:
    """M01-4: validate tenant active + user assigned, re-anchor context."""
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None or tenant.status == "archived":
        raise not_found("Tenant not found.")
    if tenant.status == "suspended":
        raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
    assigned = await login_service.assigned_tenant_ids(db, ctx.user_id)
    if tenant.tenant_id not in assigned:
        raise DomainError(
            "E_AUTH_TENANT_NOT_ASSIGNED", "You no longer have access to this tenant."
        )
    session = await db.get(AuthSession, ctx.session_id)
    assert session is not None
    session.active_tenant_id = tenant.tenant_id
    user = await db.get(User, ctx.user_id)
    if user is not None:
        user.last_used_tenant_id = tenant.tenant_id
    await emit_audit(
        db,
        action="auth.session.tenant_switched",
        actor_type="user",
        actor_id=ctx.user_id,
        subject_type="session",
        subject_id=ctx.session_id,
        source_module="M01",
        tenant_id=tenant.tenant_id,
    )
    await db.commit()
    purge_session_cache(ctx.session_id)
    _current_session_cache.delete(ctx.session_id)
    return ApiResponse(data=SwitchTenantResponse(active_tenant_id=tenant.tenant_id))


@router.delete(
    "/api/v1/auth/sessions/current",
    operation_id="m01_logout",
    status_code=204,
)
async def logout(
    ctx: CurrentSession,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """M01-5: revoke own session; idempotent 204."""
    session = await db.get(AuthSession, ctx.session_id)
    if session is not None and session.status == "active":
        session.status = "revoked"
        session.revoked_reason = "logout"
        session.revoked_at = datetime.now(timezone.utc)
        await emit_audit(
            db,
            action="auth.session.revoked",
            actor_type="user",
            actor_id=ctx.user_id,
            subject_type="session",
            subject_id=ctx.session_id,
            source_module="M01",
        )
        await db.commit()
    purge_session_cache(ctx.session_id)
    _current_session_cache.delete(ctx.session_id)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/api/v1/auth")
    return response


@router.delete(
    "/api/v1/admin/users/{user_id}/sessions",
    operation_id="m01_admin_revoke_user_sessions",
    response_model=ApiResponse[RevokeAllResponse],
)
async def admin_revoke_user_sessions(
    user_id: str,
    ctx: CurrentSession,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[RevokeAllResponse]:
    """M01-6: PA-only revoke-all (permission `iam.user_session:delete`)."""
    await authorize(db, ctx, "iam.user_session:delete", "platform", None)
    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User not found.")
    sessions = (
        await db.execute(
            select(AuthSession.session_id).where(
                AuthSession.user_id == user_id, AuthSession.status == "active"
            )
        )
    ).scalars().all()
    count = await login_service.revoke_all_sessions(
        db, user_id=user_id, reason="admin_revoke", actor_type="user", actor_id=ctx.user_id
    )
    await db.commit()
    for sid in sessions:
        purge_session_cache(sid)
        _current_session_cache.delete(sid)
    return ApiResponse(data=RevokeAllResponse(revoked_count=count))


@router.post(
    "/internal/v1/auth/introspect",
    operation_id="m01_introspect_session",
    response_model=IntrospectResponse,
    include_in_schema=False,
)
async def introspect(
    body: IntrospectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _svc: Annotated[str, Depends(require_service_identity)],
) -> IntrospectResponse:
    """M01-7 (i): service-plane introspection of an opaque session token.
    Always HTTP 200; `active=false` carries the reason."""
    session = (
        await db.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(body.session_token))
        )
    ).scalar_one_or_none()
    if session is None:
        return IntrospectResponse(active=False, reason="unknown")
    now = datetime.now(timezone.utc)
    if session.status == "revoked":
        return IntrospectResponse(active=False, reason="revoked")
    if session.status == "expired" or session.absolute_expires_at <= now or session.idle_expires_at <= now:
        if session.status == "active":
            session.status = "expired"
            await db.commit()
        return IntrospectResponse(active=False, reason="expired")
    user = await db.get(User, session.user_id)
    if user is None or user.status != "active":
        return IntrospectResponse(active=False, reason="revoked")
    settings = get_settings()
    if session.last_seen_at is None or (now - session.last_seen_at).total_seconds() >= 60:
        session.idle_expires_at = now + timedelta(seconds=settings.session_idle_ttl_s)
        session.last_seen_at = now
        await db.commit()
    return IntrospectResponse(
        active=True,
        user_id=session.user_id,
        session_id=session.session_id,
        active_tenant_id=session.active_tenant_id,
        user_status=user.status,
        idle_expires_at=session.idle_expires_at,
        absolute_expires_at=session.absolute_expires_at,
    )


def purge_caches_for_session(session_id: str) -> None:
    """Hook for cross-module cascades (M03 deactivation)."""
    purge_session_cache(session_id)
    _current_session_cache.delete(session_id)
    introspection_cache.delete(session_id)
