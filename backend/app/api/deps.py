"""Request-scoped dependencies: session context (FDD §1.4.2), permission
guard (M03-10 binding), optimistic concurrency (§1.4.4), idempotency,
internal service-plane guard."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, Header, Request, Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.errors import DomainError, permission_denied
from app.core.security import decode_access_token
from app.database import get_db
from app.models.auth import Session as AuthSession
from app.models.iam import IdempotencyKey, User
from app.services import authz
from app.services.authz import ScopeType

SESSION_COOKIE = "zq_session"

# Introspection cache (FDD M01-7: TTL 60 s, explicit delete on revoke/switch).
introspection_cache = TTLCache(ttl_s=get_settings().introspection_cache_ttl_s)


@dataclass
class SessionContext:
    """Trusted per-request identity (replaces the FDD gateway headers
    X-User-Id / X-Session-Id / X-Active-Tenant-Id)."""

    user_id: str
    session_id: str
    active_tenant_id: str | None
    user_status: str


def _unauthenticated() -> DomainError:
    return DomainError("E_UNAUTHENTICATED", "Your session has expired. Sign in again.")


async def introspect_session(db: AsyncSession, session_id: str) -> SessionContext | None:
    """Shared introspection core (M01-7 processing): status + both expiries,
    lazy expiry marking, sliding idle window persisted at most once / 60 s."""
    cached = introspection_cache.get(session_id)
    if cached is not None:
        return cached

    session = await db.get(AuthSession, session_id)
    if session is None or session.status != "active":
        return None
    now = datetime.now(timezone.utc)
    if session.absolute_expires_at <= now or session.idle_expires_at <= now:
        session.status = "expired"
        await db.commit()
        return None

    user = await db.get(User, session.user_id)
    if user is None or user.status != "active":
        return None

    settings = get_settings()
    # Slide idle expiry; bound write amplification to one persist per 60 s.
    if (
        session.last_seen_at is None
        or (now - session.last_seen_at).total_seconds() >= 60
    ):
        await db.execute(
            update(AuthSession)
            .where(AuthSession.session_id == session_id, AuthSession.status == "active")
            .values(
                idle_expires_at=now + timedelta(seconds=settings.session_idle_ttl_s),
                last_seen_at=now,
            )
        )
        await db.commit()

    ctx = SessionContext(
        user_id=session.user_id,
        session_id=session.session_id,
        active_tenant_id=session.active_tenant_id,
        user_status=user.status,
    )
    introspection_cache.set(session_id, ctx)
    return ctx


def purge_session_cache(session_id: str) -> None:
    introspection_cache.delete(session_id)


async def get_current_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> SessionContext:
    """Access-JWT bearer auth backed by the session store (dual-token system:
    the JWT is the short-lived access credential; the session row remains the
    revocation authority with the FDD 60 s staleness bound)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthenticated()
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    if payload is None:
        raise _unauthenticated()
    ctx = await introspect_session(db, payload["sid"])
    if ctx is None or ctx.user_id != payload["sub"]:
        raise _unauthenticated()
    return ctx


CurrentSession = Annotated[SessionContext, Depends(get_current_session)]


async def authorize(
    db: AsyncSession,
    ctx: SessionContext,
    permission_key: str,
    scope_type: ScopeType,
    scope_id: str | None,
) -> None:
    """Per-handler authz check (FDD §1.4.2: every handler checks before
    business logic). Raises the mapped shared error codes."""
    decision = await authz.check_permission(
        db,
        user_id=ctx.user_id,
        permission_key=permission_key,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    if decision.allowed:
        return
    if decision.reason == "tenant_suspended":
        raise DomainError("E_TENANT_SUSPENDED", "This tenant is suspended.")
    raise permission_denied()


# --- Optimistic concurrency (FDD §1.4.4) ---


def etag_of(version: int) -> str:
    return f'"{version}"'


def set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = etag_of(version)


def require_if_match(request: Request, current_version: int) -> None:
    header = request.headers.get("If-Match")
    if header is None:
        raise DomainError(
            "E_PRECONDITION_REQUIRED", "If-Match header required for this operation."
        )
    if header.strip() not in (etag_of(current_version), "*"):
        raise DomainError(
            "E_PRECONDITION_FAILED",
            "This resource changed since you loaded it. Reload and retry.",
        )


# --- Idempotency (FDD §1.4.4: 24 h retention, replay detection) ---


def _payload_hash(body: Any) -> bytes:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).digest()


async def check_idempotency(
    db: AsyncSession,
    *,
    key: str | None,
    endpoint: str,
    payload: Any,
) -> dict[str, Any] | None:
    """Returns the stored response envelope on replay; None on first call."""
    if key is None:
        return None
    row = await db.get(IdempotencyKey, (key, endpoint))
    if row is None:
        return None
    if row.created_at < datetime.now(timezone.utc) - timedelta(hours=24):
        await db.delete(row)
        await db.flush()
        return None
    if row.payload_hash != _payload_hash(payload):
        raise DomainError(
            "E_IDEMPOTENCY_CONFLICT",
            "Idempotency-Key was already used with a different payload.",
        )
    return {"status": row.response_status, "body": row.response_body}


async def store_idempotency(
    db: AsyncSession,
    *,
    key: str | None,
    endpoint: str,
    payload: Any,
    response_status: int,
    response_body: dict[str, Any],
) -> None:
    if key is None:
        return
    db.add(
        IdempotencyKey(
            key=key,
            endpoint=endpoint,
            payload_hash=_payload_hash(payload),
            response_status=response_status,
            response_body=response_body,
            created_at=datetime.now(timezone.utc),
        )
    )


IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


# --- Internal service plane (stands in for mTLS service identity, §1.4.2) ---


async def require_service_identity(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> str:
    if x_internal_token != get_settings().internal_service_token:
        raise _unauthenticated()
    return "svc-internal"
