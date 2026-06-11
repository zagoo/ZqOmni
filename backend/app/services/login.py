"""M01 business logic: code issuance, verification, session lifecycle
(FDD §2.1.2/§2.1.3 normative policies)."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import SlidingWindowCounter
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.ids import PREFIX_LOGIN_CODE, PREFIX_SESSION, new_id
from app.core.security import (
    generate_login_code,
    generate_session_token,
    hash_identifier,
    hash_login_code,
    hash_session_token,
    new_code_salt,
    verify_login_code,
)
from app.models.auth import LoginCode, LoginThrottle, Session
from app.models.iam import RoleBinding, User
from app.models.tenancy import ProjectMember, Tenant
from app.services.audit import emit_audit

logger = logging.getLogger("app.m01")

# T1/T2 sliding windows (process-local; see core/cache.py note).
ip_window = SlidingWindowCounter()
email_window = SlidingWindowCounter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def mask_email(email: str) -> str:
    return f"{email[:1]}***@{email.split('@')[-1]}" if "@" in email else "***"


class RateLimited(DomainError):
    def __init__(self, retry_after_s: int) -> None:
        super().__init__(
            "E_RATE_LIMITED",
            "Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after_s)},
        )


def enforce_ip_throttle(client_ip: str) -> None:
    """T1: 10 requests / IP / hour — applied before user lookup, identical for
    registered and unregistered emails (enumeration-safe)."""
    settings = get_settings()
    if ip_window.hit_and_count(client_ip, 3600) > settings.throttle_ip_per_hour:
        raise RateLimited(retry_after_s=300)


def email_issue_allowed(email: str) -> bool:
    """T2: silent per-email limits (3/15 min, 10/24 h). Never surfaces as an
    error — the 202 body stays identical (anti-enumeration oracle)."""
    settings = get_settings()
    c15 = email_window.hit_and_count(("15m", email), 900)
    c24 = email_window.hit_and_count(("24h", email), 86400)
    return c15 <= settings.throttle_email_per_15m and c24 <= settings.throttle_email_per_24h


async def issue_login_code(db: AsyncSession, *, email: str, client_ip: str) -> str | None:
    """M01-1 steps 3-8. Returns the plaintext code when mail should be sent,
    None when the request is silently absorbed. Always commits the same way
    so response timing stays uniform."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user is None or user.status == "deactivated":
        # Timing-uniformity dummy HMAC + WARN with masked email; still 202.
        hash_login_code("00000000", new_code_salt())
        logger.warning("login-code requested for unknown/deactivated email %s", mask_email(email))
        return None

    if not email_issue_allowed(email):
        return None

    now = _now()
    # Supersede all outstanding codes (at most one live code per email).
    await db.execute(
        update(LoginCode)
        .where(LoginCode.user_id == user.user_id, LoginCode.status == "issued")
        .values(status="expired", expire_reason="superseded")
    )
    code = generate_login_code()
    salt = new_code_salt()
    settings = get_settings()
    db.add(
        LoginCode(
            code_id=new_id(PREFIX_LOGIN_CODE),
            user_id=user.user_id,
            code_hash=hash_login_code(code, salt),
            salt=salt,
            status="issued",
            attempt_count=0,
            expires_at=now + timedelta(seconds=settings.login_code_ttl_s),
            created_at=now,
            request_ip_hash=hash_identifier(client_ip),
        )
    )
    await emit_audit(
        db,
        action="auth.login_code.requested",
        actor_type="user",
        actor_id="anonymous",
        subject_type="user",
        subject_id=user.user_id,
        source_module="M01",
    )
    await db.commit()
    return code


async def _backoff_row(db: AsyncSession, email: str) -> LoginThrottle | None:
    return await db.get(LoginThrottle, hash_identifier(email))


async def enforce_verify_backoff(db: AsyncSession, email: str) -> None:
    """T4: exponential backoff after 5 consecutive failures (30 s x 2^n, cap 15 min)."""
    row = await _backoff_row(db, email)
    if row is not None and row.backoff_until is not None and row.backoff_until > _now():
        raise RateLimited(retry_after_s=int((row.backoff_until - _now()).total_seconds()) + 1)


async def record_verify_failure(db: AsyncSession, email: str) -> None:
    settings = get_settings()
    key = hash_identifier(email)
    row = await db.get(LoginThrottle, key)
    if row is None:
        row = LoginThrottle(email_hash=key, consecutive_failures=0, updated_at=_now())
        db.add(row)
    row.consecutive_failures += 1
    row.updated_at = _now()
    if row.consecutive_failures >= settings.verify_backoff_threshold:
        exponent = row.consecutive_failures - settings.verify_backoff_threshold
        delay = min(
            settings.verify_backoff_base_s * (2**exponent), settings.verify_backoff_cap_s
        )
        row.backoff_until = _now() + timedelta(seconds=delay)


async def reset_verify_backoff(db: AsyncSession, email: str) -> None:
    row = await _backoff_row(db, email)
    if row is not None:
        row.consecutive_failures = 0
        row.backoff_until = None
        row.updated_at = _now()


def invalid_code_error() -> DomainError:
    # One uniform error for wrong/expired/consumed/unknown (anti-enumeration).
    return DomainError("E_AUTH_CODE_INVALID", "This code is invalid or has expired. Request a new code.")


async def verify_code_and_create_session(
    db: AsyncSession,
    *,
    email: str,
    code: str,
    user_agent: str | None,
    device_label: str | None,
) -> tuple[Session, str, User]:
    """M01-2 steps 3-6 in one transaction. Returns (session, opaque token, user)."""
    settings = get_settings()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    code_row: LoginCode | None = None
    if user is not None and user.status != "deactivated":
        code_row = (
            await db.execute(
                select(LoginCode)
                .where(LoginCode.user_id == user.user_id, LoginCode.status == "issued")
                .with_for_update()
            )
        ).scalar_one_or_none()

    now = _now()
    valid = (
        code_row is not None
        and code_row.expires_at > now
        and verify_login_code(code, code_row.salt, code_row.code_hash)
    )
    if code_row is None or user is None:
        # Constant-time-ish dummy compare even when no row exists.
        verify_login_code(code, new_code_salt(), b"\x00" * 32)

    if not valid:
        if code_row is not None:
            code_row.attempt_count += 1
            if code_row.expires_at <= now:
                code_row.status = "expired"
                code_row.expire_reason = "ttl"
            elif code_row.attempt_count >= settings.login_code_max_attempts:
                code_row.status = "expired"
                code_row.expire_reason = "attempts_exhausted"
        await record_verify_failure(db, email)
        if user is not None:
            await emit_audit(
                db,
                action="auth.login.failed",
                actor_type="user",
                actor_id="anonymous",
                subject_type="user",
                subject_id=user.user_id,
                source_module="M01",
                decision="deny",
                reason="code_invalid",
                after_summary={"attempt_no": code_row.attempt_count if code_row else None},
            )
        await db.commit()
        raise invalid_code_error()

    assert code_row is not None and user is not None
    code_row.status = "consumed"
    code_row.consumed_at = now

    active_tenant_id = await _resolve_initial_tenant(db, user)
    token = generate_session_token()
    session = Session(
        session_id=new_id(PREFIX_SESSION),
        user_id=user.user_id,
        token_hash=hash_session_token(token),
        status="active",
        active_tenant_id=active_tenant_id,
        client_user_agent=user_agent,
        client_device_label=device_label,
        created_at=now,
        idle_expires_at=now + timedelta(seconds=settings.session_idle_ttl_s),
        absolute_expires_at=now + timedelta(seconds=settings.session_absolute_ttl_s),
        last_seen_at=now,
    )
    db.add(session)

    first_login = user.status == "invited"
    if first_login:
        # `auth.user.first_login` consumer (M03): invited -> active.
        user.status = "active"
        await emit_audit(
            db,
            action="iam.user.activated",
            actor_type="user",
            actor_id=user.user_id,
            subject_type="user",
            subject_id=user.user_id,
            source_module="M03",
        )
    user.last_login_at = now

    await emit_audit(
        db,
        action="auth.login.succeeded",
        actor_type="user",
        actor_id=user.user_id,
        subject_type="session",
        subject_id=session.session_id,
        source_module="M01",
        tenant_id=active_tenant_id,
    )
    await reset_verify_backoff(db, email)
    await db.commit()
    return session, token, user


async def _resolve_initial_tenant(db: AsyncSession, user: User) -> str | None:
    """active_tenant_id = last-used tenant if still assigned, else the single
    assigned tenant, else NULL (M01-2 step 5)."""
    assigned = await assigned_tenant_ids(db, user.user_id)
    if user.last_used_tenant_id and user.last_used_tenant_id in assigned:
        return user.last_used_tenant_id
    if len(assigned) == 1:
        return next(iter(assigned))
    return None


async def assigned_tenant_ids(db: AsyncSession, user_id: str) -> set[str]:
    """Tenants where the user holds >=1 role binding (tenant or project scope)
    or a project membership — non-archived tenants only."""
    tenant_ids: set[str] = set()

    rows = (
        await db.execute(
            select(RoleBinding.scope_type, RoleBinding.scope_id).where(
                RoleBinding.user_id == user_id, RoleBinding.deleted_at.is_(None)
            )
        )
    ).all()
    project_ids = {sid for stype, sid in rows if stype == "project" and sid}
    tenant_ids.update(sid for stype, sid in rows if stype == "tenant" and sid)

    member_projects = (
        await db.execute(select(ProjectMember.project_id).where(ProjectMember.user_id == user_id))
    ).scalars().all()
    project_ids.update(member_projects)

    if project_ids:
        from app.models.tenancy import Project

        rows = (
            await db.execute(
                select(Project.tenant_id).where(Project.project_id.in_(project_ids))
            )
        ).scalars().all()
        tenant_ids.update(rows)

    if not tenant_ids:
        return set()
    live = (
        await db.execute(
            select(Tenant.tenant_id).where(
                Tenant.tenant_id.in_(tenant_ids), Tenant.status != "archived"
            )
        )
    ).scalars().all()
    return set(live)


async def revoke_all_sessions(
    db: AsyncSession, *, user_id: str, reason: str, actor_type: str, actor_id: str
) -> int:
    """M01-6 core; also invoked by the M03 deactivation cascade."""
    result = await db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.status == "active")
        .values(status="revoked", revoked_reason=reason, revoked_at=_now())
    )
    count = result.rowcount or 0
    await db.execute(
        update(LoginCode)
        .where(LoginCode.user_id == user_id, LoginCode.status == "issued")
        .values(status="expired", expire_reason="user_deactivated")
    )
    await emit_audit(
        db,
        action="auth.session.revoked_all",
        actor_type=actor_type,
        actor_id=actor_id,
        subject_type="user",
        subject_id=user_id,
        source_module="M01",
        after_summary={"revoked_count": count},
    )
    return count


async def count_sessions(db: AsyncSession, user_id: str, status: str = "active") -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Session)
            .where(Session.user_id == user_id, Session.status == status)
        )
    ).scalar_one()
