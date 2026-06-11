"""M01 — login codes, sessions, throttles, revocation (FDD §2.1).

These tests encode the normative WHY: anti-enumeration uniformity, single-use
codes, attempt ceilings, session lifecycle authority, and the dual-token
refresh contract — not just endpoint plumbing.
"""
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, update

from app.database import get_session_factory
from app.main import app
from app.models.auth import LoginCode, Session as AuthSession
from app.api import deps
from app.tests.conftest import ADMIN_EMAIL, Actor, bind_role, create_tenant, login, preregister


async def test_login_flow_first_login_activates_user(client, mailbox):
    """BP-M1: invited -> active on first successful login; session carries
    identity; M01-3 exposes permission summary for UI gating."""
    actor = await login(client, mailbox, ADMIN_EMAIL)
    r = await actor.get("/api/v1/auth/sessions/current")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["user"]["status"] == "active"  # invited -> active happened
    assert data["user"]["email"] == ADMIN_EMAIL
    assert "iam.user:create" in data["permission_summary"]["allowed_keys"]  # PA probe


async def test_login_code_request_is_enumeration_safe(client, mailbox):
    """Unknown and known emails MUST be indistinguishable (202, same body)."""
    r_known = await client.post("/api/v1/auth/login-codes", json={"email": ADMIN_EMAIL})
    r_unknown = await client.post(
        "/api/v1/auth/login-codes", json={"email": "ghost@nowhere.dev"}
    )
    assert r_known.status_code == r_unknown.status_code == 202
    assert r_known.json()["data"]["message"] == r_unknown.json()["data"]["message"]
    assert "ghost@nowhere.dev" not in mailbox.codes  # silently absorbed


async def test_verify_unknown_email_uniform_error(client, mailbox):
    r = await client.post(
        "/api/v1/auth/sessions", json={"email": "ghost@nowhere.dev", "code": "12345678"}
    )
    assert r.status_code == 401
    assert r.json()["data"]["error_code"] == "E_AUTH_CODE_INVALID"


async def test_code_is_single_use(client, mailbox):
    actor = await login(client, mailbox, ADMIN_EMAIL)
    code = mailbox.codes[ADMIN_EMAIL]
    replay = await client.post(
        "/api/v1/auth/sessions", json={"email": ADMIN_EMAIL, "code": code}
    )
    assert replay.status_code == 401  # consumed codes fail closed
    assert replay.json()["data"]["error_code"] == "E_AUTH_CODE_INVALID"


async def test_new_code_supersedes_previous(client, mailbox):
    await client.post("/api/v1/auth/login-codes", json={"email": ADMIN_EMAIL})
    first = mailbox.codes[ADMIN_EMAIL]
    await client.post("/api/v1/auth/login-codes", json={"email": ADMIN_EMAIL})
    second = mailbox.codes[ADMIN_EMAIL]
    r1 = await client.post(
        "/api/v1/auth/sessions", json={"email": ADMIN_EMAIL, "code": first}
    )
    assert r1.status_code == 401  # superseded
    r2 = await client.post(
        "/api/v1/auth/sessions", json={"email": ADMIN_EMAIL, "code": second}
    )
    assert r2.status_code == 201


async def test_five_wrong_attempts_exhaust_code(client, mailbox):
    """T3: 5 attempts then the code expires even if later guessed right."""
    await client.post("/api/v1/auth/login-codes", json={"email": ADMIN_EMAIL})
    real = mailbox.codes[ADMIN_EMAIL]
    wrong = "00000000" if real != "00000000" else "00000001"
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/sessions", json={"email": ADMIN_EMAIL, "code": wrong}
        )
        assert r.status_code in (401, 429)
    async with get_session_factory()() as db:
        row = (
            await db.execute(select(LoginCode).order_by(LoginCode.created_at.desc()).limit(1))
        ).scalar_one()
        assert row.status == "expired"
        assert row.expire_reason == "attempts_exhausted"


async def test_verify_backoff_rate_limits(client, mailbox):
    """T4: after 5 consecutive failures the email enters exponential backoff."""
    await client.post("/api/v1/auth/login-codes", json={"email": ADMIN_EMAIL})
    real = mailbox.codes[ADMIN_EMAIL]
    wrong = "00000000" if real != "00000000" else "00000001"
    last = None
    for _ in range(6):
        last = await client.post(
            "/api/v1/auth/sessions", json={"email": ADMIN_EMAIL, "code": wrong}
        )
    assert last is not None and last.status_code == 429
    assert last.json()["data"]["error_code"] == "E_RATE_LIMITED"
    assert "Retry-After" in last.headers


async def test_ip_throttle_t1(mailbox):
    """T1: 10 code requests per IP per hour, enumeration-independent."""
    transport = httpx.ASGITransport(app=app, client=("198.51.100.77", 999))
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        for i in range(10):
            r = await c.post(
                "/api/v1/auth/login-codes", json={"email": f"any{i}@nowhere.dev"}
            )
            assert r.status_code == 202
        r = await c.post("/api/v1/auth/login-codes", json={"email": "any@nowhere.dev"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers


async def test_session_idle_expiry_enforced(client, mailbox):
    actor = await login(client, mailbox, ADMIN_EMAIL)
    async with get_session_factory()() as db:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.session_id == actor.session_id)
            .values(idle_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()
    deps.introspection_cache.delete(actor.session_id)  # explicit purge path
    r = await actor.get("/api/v1/auth/sessions/current")
    assert r.status_code == 401
    assert r.json()["data"]["error_code"] == "E_UNAUTHENTICATED"


async def test_refresh_issues_new_access_token(client, mailbox):
    actor = await login(client, mailbox, ADMIN_EMAIL)
    r = await client.post(
        "/api/v1/auth/sessions/refresh", json={"session_token": actor.session_token}
    )
    assert r.status_code == 200
    new_access = r.json()["data"]["access_token"]
    r2 = await client.get(
        "/api/v1/auth/sessions/current", headers={"Authorization": f"Bearer {new_access}"}
    )
    assert r2.status_code == 200

    bad = await client.post(
        "/api/v1/auth/sessions/refresh", json={"session_token": "garbage"}
    )
    assert bad.status_code == 401


async def test_logout_revokes_session(client, mailbox):
    actor = await login(client, mailbox, ADMIN_EMAIL)
    r = await actor.delete("/api/v1/auth/sessions/current")
    assert r.status_code == 204
    r = await actor.get("/api/v1/auth/sessions/current")
    assert r.status_code == 401
    # Refresh with the revoked session token must also fail (revocation
    # authority is the session row, not the JWT).
    r = await client.post(
        "/api/v1/auth/sessions/refresh", json={"session_token": actor.session_token}
    )
    assert r.status_code == 401


async def test_tenant_switch_requires_assignment(client, mailbox, admin):
    """M01-4: login never grants scope — switching needs a binding in the
    target tenant (FDD §0.5.3)."""
    tenant = await create_tenant(admin, "acme-robotics")
    r = await admin.put(
        "/api/v1/auth/sessions/current/active-tenant", json={"tenant_id": tenant["tenant_id"]}
    )
    assert r.status_code == 403
    assert r.json()["data"]["error_code"] == "E_AUTH_TENANT_NOT_ASSIGNED"

    await bind_role(admin, admin.user_id, "builtin:tenant_admin", "tenant", tenant["tenant_id"])
    r = await admin.put(
        "/api/v1/auth/sessions/current/active-tenant", json={"tenant_id": tenant["tenant_id"]}
    )
    assert r.status_code == 200
    assert r.json()["data"]["active_tenant_id"] == tenant["tenant_id"]

    current = (await admin.get("/api/v1/auth/sessions/current")).json()["data"]
    assert current["active_tenant_id"] == tenant["tenant_id"]
    assert current["tenants"][0]["tenant_id"] == tenant["tenant_id"]

    missing = await admin.put(
        "/api/v1/auth/sessions/current/active-tenant", json={"tenant_id": "tnt-NOPE"}
    )
    assert missing.status_code == 404


async def test_admin_revoke_all_sessions(client, mailbox, admin):
    user_id = await preregister(admin, "victim@zqomni.dev", "Victim")
    await bind_role(admin, user_id, "builtin:ops_engineer", "platform", None)
    victim = await login(client, mailbox, "victim@zqomni.dev")

    r = await admin.delete(f"/api/v1/admin/users/{user_id}/sessions")
    assert r.status_code == 200
    assert r.json()["data"]["revoked_count"] == 1
    r = await victim.get("/api/v1/auth/sessions/current")
    assert r.status_code == 401

    # Non-PA caller lacks iam.user_session:delete.
    victim2 = await login(client, mailbox, "victim@zqomni.dev")
    r = await victim2.delete(f"/api/v1/admin/users/{admin.user_id}/sessions")
    assert r.status_code == 403
    assert r.json()["data"]["error_code"] == "E_PERMISSION_DENIED"

    r = await admin.delete("/api/v1/admin/users/usr-MISSING/sessions")
    assert r.status_code == 404


async def test_internal_introspection_requires_service_identity(client, mailbox):
    actor = await login(client, mailbox, ADMIN_EMAIL)
    r = await client.post(
        "/internal/v1/auth/introspect", json={"session_token": actor.session_token}
    )
    assert r.status_code == 401  # no service token
    r = await client.post(
        "/internal/v1/auth/introspect",
        json={"session_token": actor.session_token},
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True and body["user_id"] == actor.user_id
    r = await client.post(
        "/internal/v1/auth/introspect",
        json={"session_token": "unknown-token"},
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    assert r.json() == {
        "active": False, "reason": "unknown", "user_id": None, "session_id": None,
        "active_tenant_id": None, "user_status": None, "idle_expires_at": None,
        "absolute_expires_at": None,
    }
