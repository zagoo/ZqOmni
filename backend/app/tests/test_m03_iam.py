"""M03 — users, roles, bindings, authz, audit, access reviews (FDD §2.3).

Encodes least-privilege invariants: anti-escalation, last-admin guards,
built-in immutability, deactivation inertness, audit append-only chain,
review anomaly detection.
"""
import asyncio

from sqlalchemy import select

from app.database import get_session_factory
from app.models.iam import AuditEvent
from app.tests.conftest import (
    ADMIN_EMAIL,
    bind_role,
    create_tenant,
    login,
    preregister,
)


async def test_preregistration_and_duplicate(admin):
    user_id = await preregister(admin, "jane.doe@zqomni.dev", "Jane Doe")
    assert user_id.startswith("usr-")
    dup = await admin.post(
        "/api/v1/admin/users", json={"email": "jane.doe@zqomni.dev", "display_name": "Jane"}
    )
    assert dup.status_code == 409
    assert dup.json()["data"]["error_code"] == "E_IAM_EMAIL_EXISTS"
    # Case-insensitivity through lowercasing at the boundary.
    dup2 = await admin.post(
        "/api/v1/admin/users", json={"email": "Jane.Doe@zqomni.dev", "display_name": "Jane"}
    )
    assert dup2.status_code == 409


async def test_deactivation_cascade_and_reactivation(admin, client, mailbox):
    user_id = await preregister(admin, "leaver@zqomni.dev", "Leaver")
    await bind_role(admin, user_id, "builtin:ops_engineer", "platform", None)
    leaver = await login(client, mailbox, "leaver@zqomni.dev")

    r = await admin.post(
        f"/api/v1/admin/users/{user_id}:deactivate", json={"reason": "left the company"}
    )
    assert r.status_code == 200 and r.json()["data"]["status"] == "deactivated"

    # Cascade: sessions revoked immediately.
    assert (await leaver.get("/api/v1/auth/sessions/current")).status_code == 401
    # Login codes silently absorbed for deactivated users (202, no mail).
    mailbox.codes.clear()
    r = await client.post("/api/v1/auth/login-codes", json={"email": "leaver@zqomni.dev"})
    assert r.status_code == 202 and "leaver@zqomni.dev" not in mailbox.codes
    # Bindings kept but inert: authz denies with user_inactive.
    check = await client.post(
        "/internal/v1/authz/check",
        json={
            "user_id": user_id, "permission_key": "infra.resource:read",
            "scope": {"type": "platform", "id": None},
        },
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    assert check.json()["decision"] == "deny" and check.json()["reason"] == "user_inactive"

    # Reactivation restores prior access (binding still there).
    r = await admin.post(f"/api/v1/admin/users/{user_id}:reactivate")
    assert r.json()["data"]["status"] == "active"  # had logged in before
    check = await client.post(
        "/internal/v1/authz/check",
        json={
            "user_id": user_id, "permission_key": "infra.resource:read",
            "scope": {"type": "platform", "id": None},
        },
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    assert check.json()["decision"] == "allow"


async def test_last_platform_admin_guard(admin):
    r = await admin.post(
        f"/api/v1/admin/users/{admin.user_id}:deactivate", json={"reason": "self destruction"}
    )
    assert r.status_code == 409
    assert r.json()["data"]["error_code"] == "E_IAM_LAST_PLATFORM_ADMIN"

    bindings = await admin.get("/api/v1/role-bindings", params={"user_id": admin.user_id})
    pa_binding = bindings.json()["data"]["items"][0]
    r = await admin.delete(f"/api/v1/role-bindings/{pa_binding['binding_id']}")
    assert r.status_code == 409
    assert r.json()["data"]["error_code"] == "E_IAM_LAST_PLATFORM_ADMIN"


async def test_permission_catalog_browse(admin):
    r = await admin.get("/api/v1/permissions", params={"domain": "tenancy", "page_size": 500})
    items = r.json()["data"]["items"]
    assert any(p["key"] == "tenancy.tenant:create" for p in items)
    assert all(p["domain"] == "tenancy" for p in items)
    full = await admin.get("/api/v1/permissions", params={"page_size": 500})
    assert full.json()["data"]["total_size"] >= 100  # full atomic catalog seeded


async def test_custom_roles_composition_and_anti_escalation(admin, client, mailbox):
    tenant = await create_tenant(admin, "role-co")
    tid = tenant["tenant_id"]
    ta_id = await preregister(admin, "roleta@zqomni.dev", "Role TA")
    await bind_role(admin, ta_id, "builtin:tenant_admin", "tenant", tid)
    ta = await login(client, mailbox, "roleta@zqomni.dev")
    await ta.put("/api/v1/auth/sessions/current/active-tenant", json={"tenant_id": tid})

    unknown = await ta.post(
        f"/api/v1/tenants/{tid}/roles",
        json={"name": "ghost-role", "permission_keys": ["data.notreal:read"]},
    )
    assert unknown.status_code == 422
    assert unknown.json()["data"]["error_code"] == "E_IAM_UNKNOWN_PERMISSION"

    # TA cannot grant platform-admin-only keys (outside own effective set).
    escalate = await ta.post(
        f"/api/v1/tenants/{tid}/roles",
        json={"name": "sneaky", "permission_keys": ["infra.resource:create"]},
    )
    assert escalate.status_code == 403
    assert "infra.resource:create" in str(escalate.json()["data"]["details"])

    ok = await ta.post(
        f"/api/v1/tenants/{tid}/roles",
        json={
            "name": "annotation-vendor-lead",
            "description": "Vendor leads",
            "permission_keys": ["label.annotation_task:read", "label.qa_review:execute"],
        },
    )
    assert ok.status_code == 201, ok.text
    role = ok.json()["data"]

    dup = await ta.post(
        f"/api/v1/tenants/{tid}/roles",
        json={"name": "annotation-vendor-lead", "permission_keys": ["label.qa_review:read"]},
    )
    assert dup.status_code == 409

    # Built-ins are immutable and undeletable.
    builtin_patch = await admin.patch(
        "/api/v1/roles/builtin:rd_engineer",
        json={"description": "nope"},
        headers={"If-Match": '"1"'},
    )
    assert builtin_patch.status_code == 409
    assert builtin_patch.json()["data"]["error_code"] == "E_IAM_BUILTIN_IMMUTABLE"

    # Recompose, then delete; delete blocked while bound.
    member_id = await preregister(admin, "vendor@zqomni.dev", "Vendor")
    binding_id = await bind_role(admin, member_id, role["role_id"], "tenant", tid)
    blocked = await ta.delete(f"/api/v1/roles/{role['role_id']}")
    assert blocked.status_code == 409
    assert blocked.json()["data"]["error_code"] == "E_IAM_ROLE_IN_USE"

    recomposed = await ta.patch(
        f"/api/v1/roles/{role['role_id']}",
        json={"permission_keys": ["label.annotation_task:read"]},
        headers={"If-Match": '"1"'},
    )
    assert recomposed.status_code == 200
    assert recomposed.json()["data"]["permission_keys"] == ["label.annotation_task:read"]

    # Recomposition reflected immediately in decisions (cache invalidated).
    check = await client.post(
        "/internal/v1/authz/check",
        json={
            "user_id": member_id, "permission_key": "label.qa_review:execute",
            "scope": {"type": "tenant", "id": tid},
        },
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    assert check.json()["decision"] == "deny"

    await admin.delete(f"/api/v1/role-bindings/{binding_id}")
    gone = await ta.delete(f"/api/v1/roles/{role['role_id']}")
    assert gone.status_code == 204


async def test_role_binding_placement_and_scope_rules(admin):
    tenant = await create_tenant(admin, "place-co")
    tid = tenant["tenant_id"]
    user_id = await preregister(admin, "placee@zqomni.dev", "Placee")

    # Built-in placement: TA cannot be bound at platform scope.
    r = await admin.post(
        "/api/v1/role-bindings",
        json={"user_id": user_id, "role_id": "builtin:tenant_admin",
              "scope": {"type": "platform", "id": None}},
    )
    assert r.status_code == 422

    # Scope id type mismatch.
    r = await admin.post(
        "/api/v1/role-bindings",
        json={"user_id": user_id, "role_id": "builtin:rd_engineer",
              "scope": {"type": "tenant", "id": "prj-WRONG"}},
    )
    assert r.status_code == 422
    assert r.json()["data"]["error_code"] == "E_IAM_SCOPE_MISMATCH"

    binding_id = await bind_role(admin, user_id, "builtin:rd_engineer", "tenant", tid)
    dup = await admin.post(
        "/api/v1/role-bindings",
        json={"user_id": user_id, "role_id": "builtin:rd_engineer",
              "scope": {"type": "tenant", "id": tid}},
    )
    assert dup.status_code == 409

    # Last-TA guard.
    ta_id = await preregister(admin, "lastta@zqomni.dev", "Last TA")
    ta_binding = await bind_role(admin, ta_id, "builtin:tenant_admin", "tenant", tid)
    r = await admin.delete(f"/api/v1/role-bindings/{ta_binding}")
    assert r.status_code == 409
    assert r.json()["data"]["error_code"] == "E_IAM_LAST_TENANT_ADMIN"

    r = await admin.delete(f"/api/v1/role-bindings/{binding_id}")
    assert r.status_code == 204
    again = await admin.delete(f"/api/v1/role-bindings/{binding_id}")
    assert again.status_code == 204  # idempotent


async def test_effective_permissions_provenance(admin, client, mailbox):
    tenant = await create_tenant(admin, "prov-co")
    tid = tenant["tenant_id"]
    user_id = await preregister(admin, "prov@zqomni.dev", "Prov")
    await bind_role(admin, user_id, "builtin:rd_engineer", "tenant", tid)

    eff = await admin.get(
        f"/api/v1/users/{user_id}/effective-permissions",
        params={"scope_type": "tenant", "scope_id": tid},
    )
    data = eff.json()["data"]
    keys = {e["key"]: e["via"] for e in data["allowed"]}
    assert "tenancy.tenant:read" in keys  # RD usage key at tenant binding
    assert keys["tenancy.tenant:read"][0]["role"] == "builtin:rd_engineer"
    # Business keys are NOT granted by tenant-scope RD bindings ("within
    # assigned projects" boundary).
    assert "mlops.training_plan:create" not in keys
    assert data["user_status"] == "invited"
    assert "user_inactive" in data["denied_reasons"]

    # Self-query allowed without extra permission; other-user query denied.
    rd = None
    other = await preregister(admin, "nosey@zqomni.dev", "Nosey")
    await bind_role(admin, other, "builtin:rd_engineer", "tenant", tid)
    nosey = await login(client, mailbox, "nosey@zqomni.dev")
    self_q = await nosey.get(
        f"/api/v1/users/{other}/effective-permissions",
        params={"scope_type": "tenant", "scope_id": tid},
    )
    assert self_q.status_code == 200
    other_q = await nosey.get(
        f"/api/v1/users/{user_id}/effective-permissions",
        params={"scope_type": "tenant", "scope_id": tid},
    )
    assert other_q.status_code == 403


async def test_audit_query_windows_filters_and_keyset(admin):
    tenant = await create_tenant(admin, "audit-co")
    tid = tenant["tenant_id"]
    for i in range(3):
        await preregister(admin, f"bulk{i}@zqomni.dev", f"Bulk {i}")

    too_wide = await admin.get(
        "/api/v1/admin/audit-events",
        params={"occurred_after": "2020-01-01T00:00:00Z", "occurred_before": "2026-01-01T00:00:00Z"},
    )
    assert too_wide.status_code == 422

    tenant_events = await admin.get(f"/api/v1/tenants/{tid}/audit-events")
    actions = [e["action"] for e in tenant_events.json()["data"]["items"]]
    assert "tenant.created" in actions
    assert all(e["scope"]["tenant_id"] == tid for e in tenant_events.json()["data"]["items"])

    page1 = await admin.get("/api/v1/admin/audit-events", params={"page_size": 2})
    body1 = page1.json()["data"]
    assert len(body1["items"]) == 2 and body1["next_page_token"]
    page2 = await admin.get(
        "/api/v1/admin/audit-events",
        params={"page_size": 2, "page_token": body1["next_page_token"]},
    )
    ids1 = {e["event_id"] for e in body1["items"]}
    ids2 = {e["event_id"] for e in page2.json()["data"]["items"]}
    assert ids1.isdisjoint(ids2)  # keyset advances, no overlap

    prefix = await admin.get("/api/v1/admin/audit-events", params={"action": "iam.user."})
    assert all(
        e["action"].startswith("iam.user.") for e in prefix.json()["data"]["items"]
    )


async def test_audit_chain_hash_appends(admin):
    await create_tenant(admin, "chain-co")
    async with get_session_factory()() as db:
        rows = (
            (await db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at))).scalars().all()
        )
        assert rows and all(r.chain_hash for r in rows)


async def test_oe_audit_domain_filter(admin, client, mailbox):
    oe_id = await preregister(admin, "oe@zqomni.dev", "Ops Eng")
    await bind_role(admin, oe_id, "builtin:ops_engineer", "platform", None)
    oe = await login(client, mailbox, "oe@zqomni.dev")
    await create_tenant(admin, "filter-co")  # emits tenant.* + iam.* events

    r = await oe.get("/api/v1/admin/audit-events")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert items, "OE should see infrastructure-domain events"
    assert all(
        e["action"].split(".", 1)[0] in ("infra", "tenancy", "tenant", "ops", "workflow")
        for e in items
    )

    pa_view = await admin.get("/api/v1/admin/audit-events")
    pa_domains = {e["action"].split(".", 1)[0] for e in pa_view.json()["data"]["items"]}
    assert "iam" in pa_domains  # PA is unfiltered


async def test_access_review_generation(admin, client, mailbox):
    tenant = await create_tenant(admin, "review-co")
    tid = tenant["tenant_id"]
    ghost_id = await preregister(admin, "ghost@zqomni.dev", "Ghost")
    await bind_role(admin, ghost_id, "builtin:rd_engineer", "tenant", tid)
    await admin.post(
        f"/api/v1/admin/users/{ghost_id}:deactivate", json={"reason": "left the org"}
    )

    r = await admin.post(
        f"/api/v1/tenants/{tid}/access-reviews", json={"review_type": "combined"}
    )
    assert r.status_code == 201
    review = r.json()["data"]
    assert review["status"] == "generating"

    for _ in range(40):  # async generator
        await asyncio.sleep(0.05)
        detail = (await admin.get(f"/api/v1/access-reviews/{review['review_id']}")).json()["data"]
        if detail["status"] != "generating":
            break
    assert detail["status"] == "ready", detail
    assert detail["summary"]["anomalies"] >= 1

    entries = await admin.get(f"/api/v1/access-reviews/{review['review_id']}/entries")
    flat = entries.json()["data"]["items"]
    ghost_entries = [e for e in flat if e["user_id"] == ghost_id]
    assert ghost_entries
    assert "deactivated_user_with_binding" in ghost_entries[0]["anomalies"]


async def test_authz_batch_check(admin, client):
    r = await client.post(
        "/internal/v1/authz/batch-check",
        json={
            "checks": [
                {"user_id": admin.user_id, "permission_key": "tenancy.tenant:create",
                 "scope": {"type": "platform", "id": None}},
                {"user_id": "usr-NOBODY", "permission_key": "tenancy.tenant:create",
                 "scope": {"type": "platform", "id": None}},
            ]
        },
        headers={"X-Internal-Token": "dev-internal-service-token"},
    )
    results = r.json()["results"]
    assert results[0]["decision"] == "allow"
    assert results[0]["matched"]["role_id"] == "builtin:platform_admin"
    assert results[1]["decision"] == "deny" and results[1]["reason"] == "user_inactive"
