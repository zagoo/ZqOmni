"""Test harness: real PostgreSQL (dockerized), schema via `alembic upgrade
head` (the migration itself is under test), truncation between tests, OTP
capture in place of SMTP."""
import asyncio
import os

# Settings must be fixed before any app import (get_settings is cached).
os.environ.setdefault(
    "ZQ_DATABASE_URL", "postgresql+asyncpg://zqomni:zqomni@localhost:55432/zqomni_test"
)
os.environ.setdefault("ZQ_SWEEPERS_ENABLED", "false")
os.environ.setdefault("ZQ_RESOURCE_PROBE_ENABLED", "false")
os.environ.setdefault("ZQ_ENVIRONMENT", "test")
os.environ.setdefault("ZQ_INITIAL_ADMIN_EMAIL", "root.admin@zqomni.dev")

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

import app.routers.auth as auth_router
from app.api import deps
from app.database import dispose_engine, get_engine, get_session_factory
from app.services import authz
from app.services import login as login_service
from app.services.bootstrap import ensure_initial_admin
from app.main import app

ADMIN_EMAIL = "root.admin@zqomni.dev"

TRUNCATE_SQL = """
TRUNCATE TABLE
  audit.events,
  auth.login_codes, auth.sessions, auth.login_throttle,
  iam.access_review_entries, iam.access_reviews,
  iam.role_bindings, iam.role_permissions,
  tenancy.project_members, tenancy.projects,
  tenancy.resource_bindings, tenancy.resource_credentials, tenancy.resources,
  platform.idempotency_keys
CASCADE
"""
# roles/permissions/persona_templates are migration-seeded and kept;
# custom roles and non-bootstrap users are wiped separately below.
CLEAN_MUTABLE_SQL = [
    "DELETE FROM iam.role_permissions",
    "DELETE FROM iam.roles WHERE role_type = 'custom'",
    "DELETE FROM iam.users",
    # Tenants last: custom roles (FK scope_tenant_id) are gone by now. A
    # TRUNCATE ... CASCADE here would wipe iam.roles incl. the built-ins.
    "DELETE FROM tenancy.tenants",
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database():
    """Create the test database and migrate it once per session."""
    import asyncpg

    admin_conn = await asyncpg.connect(
        "postgresql://zqomni:zqomni@localhost:55432/postgres"
    )
    await admin_conn.execute("DROP DATABASE IF EXISTS zqomni_test (FORCE)")
    await admin_conn.execute("CREATE DATABASE zqomni_test")
    await admin_conn.close()

    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "..", "alembic")
    )
    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield
    await dispose_engine()


def _clear_caches() -> None:
    authz.decision_cache.clear()
    deps.introspection_cache.clear()
    auth_router._current_session_cache.clear()
    login_service.ip_window.clear()
    login_service.email_window.clear()


@pytest_asyncio.fixture(autouse=True)
async def _clean_db(_database):
    async with get_session_factory()() as db:
        await db.execute(text(TRUNCATE_SQL))
        for stmt in CLEAN_MUTABLE_SQL:
            await db.execute(text(stmt))
        await db.commit()
    _clear_caches()
    await ensure_initial_admin()
    yield


class MailCapture:
    def __init__(self) -> None:
        self.codes: dict[str, str] = {}

    async def send(self, email: str, code: str) -> None:
        self.codes[email] = code


@pytest.fixture
def mailbox(monkeypatch) -> MailCapture:
    capture = MailCapture()
    monkeypatch.setattr(auth_router, "send_login_code_safe", capture.send)
    return capture


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("203.0.113.10", 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class Actor:
    """Logged-in user handle for tests."""

    def __init__(self, client: httpx.AsyncClient, email: str, payload: dict) -> None:
        self.client = client
        self.email = email
        self.user_id = payload["user"]["user_id"]
        self.session_id = payload["session_id"]
        self.access_token = payload["access_token"]
        self.session_token = payload["session_token"]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def get(self, url: str, **kw):
        return await self.client.get(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    async def post(self, url: str, **kw):
        return await self.client.post(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    async def put(self, url: str, **kw):
        return await self.client.put(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    async def patch(self, url: str, **kw):
        return await self.client.patch(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    async def delete(self, url: str, **kw):
        return await self.client.delete(url, headers={**self.headers, **kw.pop("headers", {})}, **kw)


async def login(client: httpx.AsyncClient, mailbox: MailCapture, email: str) -> Actor:
    r = await client.post("/api/v1/auth/login-codes", json={"email": email})
    assert r.status_code == 202, r.text
    code = mailbox.codes[email]
    r = await client.post("/api/v1/auth/sessions", json={"email": email, "code": code})
    assert r.status_code == 201, r.text
    return Actor(client, email, r.json()["data"])


@pytest_asyncio.fixture
async def admin(client, mailbox) -> Actor:
    """The bootstrapped Platform Administrator, logged in."""
    return await login(client, mailbox, ADMIN_EMAIL)


async def preregister(admin: Actor, email: str, display_name: str = "Test User") -> str:
    r = await admin.post(
        "/api/v1/admin/users", json={"email": email, "display_name": display_name}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["user_id"]


async def bind_role(admin: Actor, user_id: str, role_id: str, scope_type: str, scope_id):
    r = await admin.post(
        "/api/v1/role-bindings",
        json={"user_id": user_id, "role_id": role_id, "scope": {"type": scope_type, "id": scope_id}},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["binding_id"]


async def create_tenant(admin: Actor, name: str, **overrides) -> dict:
    body = {"name": name, "display_name": name.title().replace("-", " "), **overrides}
    r = await admin.post("/api/v1/admin/tenants", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]
