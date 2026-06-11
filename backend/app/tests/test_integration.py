"""Cross-module integration (scope-lock contract): M03 permissions guard M02
resources; M01 sessions propagate tenant context; suspended tenants deny;
M04-M20 remain 501 stubs."""
from app.tests.conftest import (
    bind_role,
    create_tenant,
    login,
    preregister,
)

SVC = {"X-Internal-Token": "dev-internal-service-token"}


async def test_builtin_role_boundaries_enforced_across_modules(admin, client, mailbox):
    """The mandated four-role matrix, checked end-to-end through real M02
    endpoints (BR-13: roles bound via M03 gate M02 behavior)."""
    tenant = await create_tenant(admin, "matrix-co")
    tid = tenant["tenant_id"]

    rd_id = await preregister(admin, "rd@zqomni.dev", "RD")
    await bind_role(admin, rd_id, "builtin:rd_engineer", "tenant", tid)
    oe_id = await preregister(admin, "oe2@zqomni.dev", "OE")
    await bind_role(admin, oe_id, "builtin:ops_engineer", "platform", None)
    ta_id = await preregister(admin, "ta2@zqomni.dev", "TA")
    await bind_role(admin, ta_id, "builtin:tenant_admin", "tenant", tid)

    rd = await login(client, mailbox, "rd@zqomni.dev")
    oe = await login(client, mailbox, "oe2@zqomni.dev")
    ta = await login(client, mailbox, "ta2@zqomni.dev")

    # RD: no tenant creation, no resource inventory; CAN read own tenant.
    assert (await rd.post("/api/v1/admin/tenants", json={"name": "x-co", "display_name": "X"})).status_code == 403
    assert (await rd.get("/api/v1/admin/resources")).status_code == 403
    assert (await rd.get(f"/api/v1/tenants/{tid}")).status_code == 200

    # OE: inventory platform-wide; NO business containers (projects).
    assert (await oe.get("/api/v1/admin/resources")).status_code == 200
    r = await oe.post(
        f"/api/v1/tenants/{tid}/projects",
        json={"name": "ops-proj", "display_name": "Ops", "owner_user_id": oe_id},
    )
    assert r.status_code == 403  # mandate: OE has no business-resource permissions

    # TA: projects inside own tenant; tenant lifecycle is platform-admin-only.
    r = await ta.post(
        f"/api/v1/tenants/{tid}/projects",
        json={"name": "ta-proj", "display_name": "TA Proj", "owner_user_id": ta_id},
    )
    assert r.status_code == 201, r.text
    assert (
        await ta.post(f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "ta tries suspend"})
    ).status_code == 403

    # TA cannot touch another tenant.
    other = await create_tenant(admin, "matrix-other")
    r = await ta.post(
        f"/api/v1/tenants/{other['tenant_id']}/projects",
        json={"name": "intrude", "display_name": "Nope", "owner_user_id": ta_id},
    )
    assert r.status_code == 403


async def test_session_tenant_context_propagates(admin, client, mailbox):
    """M01-2 step 5: single assigned tenant becomes the active context
    automatically; M01-3 reflects roles per tenant."""
    tenant = await create_tenant(admin, "ctx-co")
    tid = tenant["tenant_id"]
    user_id = await preregister(admin, "ctx@zqomni.dev", "Ctx")
    await bind_role(admin, user_id, "builtin:tenant_admin", "tenant", tid)

    actor = await login(client, mailbox, "ctx@zqomni.dev")
    current = (await actor.get("/api/v1/auth/sessions/current")).json()["data"]
    assert current["active_tenant_id"] == tid  # the single assigned tenant
    assert current["tenants"][0]["roles"] == ["builtin:tenant_admin"]
    assert "tenancy.project:create" in current["permission_summary"]["allowed_keys"]


async def test_suspended_tenant_denies_everything_inside(admin, client, mailbox):
    tenant = await create_tenant(admin, "suspend-co")
    tid = tenant["tenant_id"]
    ta_id = await preregister(admin, "suspendta@zqomni.dev", "TA")
    await bind_role(admin, ta_id, "builtin:tenant_admin", "tenant", tid)
    ta = await login(client, mailbox, "suspendta@zqomni.dev")

    await admin.post(f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "billing freeze"})

    r = await ta.post(
        f"/api/v1/tenants/{tid}/projects",
        json={"name": "frozen", "display_name": "Frozen", "owner_user_id": ta_id},
    )
    assert r.status_code == 403
    assert r.json()["data"]["error_code"] == "E_TENANT_SUSPENDED"
    r = await ta.get(f"/api/v1/tenants/{tid}")
    assert r.json()["data"]["error_code"] == "E_TENANT_SUSPENDED"

    # Switching INTO a suspended tenant is blocked at M01-4 too.
    r = await ta.put("/api/v1/auth/sessions/current/active-tenant", json={"tenant_id": tid})
    assert r.status_code == 403
    assert r.json()["data"]["error_code"] == "E_TENANT_SUSPENDED"


async def test_archived_project_denies_writes_allows_reads(admin, client, mailbox):
    tenant = await create_tenant(admin, "arch-proj-co")
    tid = tenant["tenant_id"]
    owner = await preregister(admin, "archowner@zqomni.dev", "Owner")
    await login(client, mailbox, "archowner@zqomni.dev")  # invited -> active
    project = (
        await admin.post(
            f"/api/v1/tenants/{tid}/projects",
            json={"name": "old-proj", "display_name": "Old", "owner_user_id": owner},
        )
    ).json()["data"]
    pid = project["project_id"]
    await admin.put(
        f"/api/v1/projects/{pid}/members/{owner}",
        json={"persona_templates": ["persona.model_engineer"]},
    )
    await admin.post(f"/api/v1/projects/{pid}:archive")

    # M03-10 step 2: archived project => deny all non-read actions.
    deny = await client.post(
        "/internal/v1/authz/check",
        json={"user_id": owner, "permission_key": "mlops.training_plan:create",
              "scope": {"type": "project", "id": pid}},
        headers=SVC,
    )
    assert deny.json()["decision"] == "deny" and deny.json()["reason"] == "scope_inactive"


async def test_out_of_scope_modules_return_501(admin):
    """Scope lock: M04-M20 surface only as 501 stubs with the standard
    envelope (code != 0, E_NOT_IMPLEMENTED)."""
    cases = [
        ("get", "/api/v1/projects/prj-X/campaigns"),                # M04
        ("post", "/api/v1/projects/prj-X/dataset-snapshots"),       # M08
        ("get", "/api/v1/scenarios/scn-1"),                         # M09
        ("post", "/api/v1/projects/prj-X/training-plans"),          # M11
        ("get", "/api/v1/model-candidates/mdl-1"),                  # M12
        ("post", "/api/v1/projects/prj-X/evaluation-runs"),         # M13
        ("get", "/api/v1/release-candidates/rls-1"),                # M14
        ("post", "/api/v1/tenants/tnt-X/workflow-templates"),       # M16
        ("get", "/api/v1/tenants/tnt-X/quota-policies"),            # M17
        ("post", "/api/v1/projects/prj-X/search/hybrid"),           # M18
        ("post", "/api/v1/projects/prj-X/workbench-sessions"),      # M19
        ("get", "/api/v1/users/me/notifications"),                  # M20
    ]
    for method, url in cases:
        r = await getattr(admin, method)(url, **({"json": {}} if method == "post" else {}))
        assert r.status_code == 501, f"{url} -> {r.status_code}"
        body = r.json()
        assert body["code"] != 0
        assert body["data"]["error_code"] == "E_NOT_IMPLEMENTED"


async def test_unauthenticated_requests_rejected(client):
    r = await client.get("/api/v1/admin/tenants")
    assert r.status_code == 401
    assert r.json()["data"]["error_code"] == "E_UNAUTHENTICATED"
    r = await client.get(
        "/api/v1/admin/tenants", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 401
