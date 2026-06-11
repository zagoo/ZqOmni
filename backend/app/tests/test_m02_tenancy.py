"""M02 — tenants, resources, bindings, projects, membership (FDD §2.2).

Encodes the binding invariants (exclusivity, tier rules, in-use guards),
lifecycle state machines, optimistic locking, and sanitized self-views.
"""
from app.tests.conftest import (
    ADMIN_EMAIL,
    bind_role,
    create_tenant,
    login,
    preregister,
)


async def _register_resource(admin, name="gpu-node-a17", rclass="compute", form="physical", **kw):
    descriptors = {
        ("compute", "physical"): {
            "compute_physical": {
                "hostname": "node-a17.dc1.local", "gpu_model": "H100", "gpu_count": 8,
                "cpu_cores": 96, "memory_gib": 1024,
            }
        },
        ("compute", "logical"): {
            "compute_logical": {
                "service_type": "ray_cluster", "endpoint_url": "https://ray.dc1.local:8265",
                "capacity": {"gpu_count": 16, "cpu_cores": 256, "memory_gib": 2048, "max_workers": 32},
            }
        },
        ("storage", "physical"): {
            "storage_physical": {
                "volume_ref": "san-vol-009", "filesystem": "xfs",
                "capacity_gib": 65536, "export_path": "/exports/robodata1",
            }
        },
        ("storage", "logical"): {
            "storage_logical": {
                "service_type": "object_storage", "endpoint_url": "https://s3.dc1.local",
                "bucket": "platform-data", "region": "dc1",
            }
        },
    }
    body = {
        "name": name,
        "resource_class": rclass,
        "form": form,
        "descriptor": descriptors[(rclass, form)],
        **kw,
    }
    if form == "logical" and "credential" not in body:
        body["credential"] = {"access_key_id": "AK", "secret": "SK"}
    r = await admin.post("/api/v1/admin/resources", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _bind(admin, tenant_id, resource_id, mode="exclusive", expect=201):
    r = await admin.post(
        f"/api/v1/admin/tenants/{tenant_id}/resource-bindings",
        json={"resource_id": resource_id, "binding_mode": mode},
    )
    assert r.status_code == expect, r.text
    return r.json()


async def test_tenant_crud_and_optimistic_locking(admin):
    tenant = await create_tenant(admin, "acme-robotics", description="Acme")
    assert tenant["namespace_ref"] == "tnt-acme-robotics"

    dup = await admin.post(
        "/api/v1/admin/tenants", json={"name": "acme-robotics", "display_name": "X"}
    )
    assert dup.status_code == 409
    assert dup.json()["data"]["error_code"] == "E_CONFLICT"

    tid = tenant["tenant_id"]
    no_etag = await admin.patch(f"/api/v1/admin/tenants/{tid}", json={"display_name": "New"})
    assert no_etag.status_code == 428  # If-Match required

    stale = await admin.patch(
        f"/api/v1/admin/tenants/{tid}", json={"display_name": "New"},
        headers={"If-Match": '"99"'},
    )
    assert stale.status_code == 412
    assert stale.json()["data"]["error_code"] == "E_PRECONDITION_FAILED"

    ok = await admin.patch(
        f"/api/v1/admin/tenants/{tid}", json={"display_name": "Acme New"},
        headers={"If-Match": '"1"'},
    )
    assert ok.status_code == 200 and ok.json()["data"]["version"] == 2

    listing = await admin.get("/api/v1/admin/tenants", params={"q": "acme"})
    assert listing.json()["data"]["total_size"] == 1


async def test_tenant_idempotency_replay(admin):
    body = {"name": "idem-tenant", "display_name": "Idem"}
    key = "11111111-2222-3333-4444-555555555555"
    first = await admin.post("/api/v1/admin/tenants", json=body, headers={"Idempotency-Key": key})
    assert first.status_code == 201
    replay = await admin.post(
        "/api/v1/admin/tenants", json=body, headers={"Idempotency-Key": key}
    )
    assert replay.status_code == 201
    assert replay.headers.get("Idempotency-Replayed") == "true"
    assert replay.json()["data"]["tenant_id"] == first.json()["data"]["tenant_id"]

    conflict = await admin.post(
        "/api/v1/admin/tenants",
        json={"name": "other-name", "display_name": "Other"},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    assert conflict.json()["data"]["error_code"] == "E_IDEMPOTENCY_CONFLICT"


async def test_tenant_lifecycle_and_archive_guards(admin, client, mailbox):
    tenant = await create_tenant(admin, "lifecycle-co")
    tid = tenant["tenant_id"]

    short = await admin.post(f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "short"})
    assert short.status_code == 422  # reason 10-500 chars

    r = await admin.post(
        f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "maintenance window"}
    )
    assert r.status_code == 200 and r.json()["data"]["status"] == "suspended"

    # Archive requires zero live bindings/projects; from suspended only.
    resource = await _register_resource(admin, "arch-node")
    reactivate = await admin.post(f"/api/v1/admin/tenants/{tid}:reactivate")
    assert reactivate.status_code == 200
    binding = (await _bind(admin, tid, resource["resource_id"]))["data"]
    await admin.post(f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "to be archived"})

    blocked = await admin.patch(
        f"/api/v1/admin/tenants/{tid}", json={"status": "archived"},
        headers={"If-Match": f'"{4}"'},
    )
    assert blocked.status_code == 409
    assert blocked.json()["data"]["error_code"] == "E_TNT_RESOURCE_IN_USE"

    await admin.delete(f"/api/v1/admin/tenants/{tid}/resource-bindings/{binding['binding_id']}")
    archived = await admin.patch(
        f"/api/v1/admin/tenants/{tid}", json={"status": "archived"},
        headers={"If-Match": f'"{4}"'},
    )
    assert archived.status_code == 200 and archived.json()["data"]["status"] == "archived"

    # Lifecycle verbs from archived are invalid transitions.
    bad = await admin.post(f"/api/v1/admin/tenants/{tid}:suspend", json={"reason": "irreversible?"})
    assert bad.status_code == 409
    assert bad.json()["data"]["error_code"] == "E_STATE_INVALID"


async def test_resource_registration_validation(admin):
    wrong_branch = await admin.post(
        "/api/v1/admin/resources",
        json={
            "name": "bad-node", "resource_class": "compute", "form": "physical",
            "descriptor": {"compute_logical": {"endpoint_url": "https://x", "service_type": "ray_cluster"}},
        },
    )
    assert wrong_branch.status_code == 422

    no_credential = await admin.post(
        "/api/v1/admin/resources",
        json={
            "name": "ray-1", "resource_class": "compute", "form": "logical",
            "descriptor": {"compute_logical": {"service_type": "ray_cluster", "endpoint_url": "https://r"}},
        },
    )
    assert no_credential.status_code == 422

    logical = await _register_resource(admin, "ray-main", "compute", "logical")
    assert logical["credential_ref"].startswith("vault://resources/")
    assert "credential" not in logical  # secret never echoed

    dup = await admin.post(
        "/api/v1/admin/resources",
        json={
            "name": "ray-main", "resource_class": "compute", "form": "logical",
            "descriptor": {"compute_logical": {"service_type": "ray_cluster", "endpoint_url": "https://r"}},
            "credential": {"secret": "x"},
        },
    )
    assert dup.status_code == 409


async def test_binding_mode_rules_and_conflicts(admin):
    t1 = await create_tenant(admin, "tenant-one")
    t2 = await create_tenant(admin, "tenant-two")
    gpu = await _register_resource(admin, "gpu-a", "compute", "physical")

    created = (await _bind(admin, t1["tenant_id"], gpu["resource_id"], "exclusive"))["data"]
    assert created["config"]["taint"] == f"tenant={t1['tenant_id']}:NoSchedule"

    conflict = await _bind(admin, t2["tenant_id"], gpu["resource_id"], "exclusive", expect=409)
    assert conflict["data"]["error_code"] == "E_TNT_BINDING_CONFLICT"

    dup = await _bind(admin, t1["tenant_id"], gpu["resource_id"], "exclusive", expect=409)
    assert dup["data"]["error_code"] in ("E_CONFLICT", "E_TNT_BINDING_CONFLICT")

    ray = await _register_resource(admin, "ray-b", "compute", "logical")
    forced = await _bind(admin, t1["tenant_id"], ray["resource_id"], "shared", expect=422)
    assert forced["data"]["error_code"] == "E_VALIDATION"  # logical compute => exclusive

    s3 = await _register_resource(admin, "s3-shared", "storage", "logical")
    shared = (await _bind(admin, t1["tenant_id"], s3["resource_id"], "shared"))["data"]
    assert shared["config"]["prefix"].endswith(f"/tenants/{t1['tenant_id']}/")

    # Exclusive logical storage requires the dedicated_bucket tier.
    s3b = await _register_resource(admin, "s3-dedicated", "storage", "logical")
    denied = await _bind(admin, t2["tenant_id"], s3b["resource_id"], "exclusive", expect=422)
    assert denied["data"]["error_code"] == "E_VALIDATION"
    t3 = await create_tenant(
        admin, "premium-co", settings={"storage_isolation": "dedicated_bucket"}
    )
    ok = await _bind(admin, t3["tenant_id"], s3b["resource_id"], "exclusive")
    assert ok["data"]["config"]["dedicated"] is True


async def test_decommission_guards(admin):
    tenant = await create_tenant(admin, "decomm-co")
    res = await _register_resource(admin, "decomm-node")
    binding = (await _bind(admin, tenant["tenant_id"], res["resource_id"]))["data"]

    blocked = await admin.post(f"/api/v1/admin/resources/{res['resource_id']}:decommission")
    assert blocked.status_code == 409
    assert blocked.json()["data"]["error_code"] == "E_TNT_RESOURCE_IN_USE"
    assert blocked.json()["data"]["details"][0]["binding_ids"] == [binding["binding_id"]]

    await admin.delete(
        f"/api/v1/admin/tenants/{tenant['tenant_id']}/resource-bindings/{binding['binding_id']}"
    )
    ok = await admin.post(f"/api/v1/admin/resources/{res['resource_id']}:decommission")
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "decommissioned"
    again = await admin.post(f"/api/v1/admin/resources/{res['resource_id']}:decommission")
    assert again.status_code == 200  # idempotent


async def test_tenant_self_view_sanitized_and_cross_tenant_404(admin, client, mailbox):
    tenant = await create_tenant(admin, "self-view-co")
    other = await create_tenant(admin, "other-co")
    ray = await _register_resource(admin, "ray-self", "compute", "logical")
    await _bind(admin, tenant["tenant_id"], ray["resource_id"], "exclusive")

    ta_id = await preregister(admin, "ta@zqomni.dev", "Tenant Admin")
    await bind_role(admin, ta_id, "builtin:tenant_admin", "tenant", tenant["tenant_id"])
    ta = await login(client, mailbox, "ta@zqomni.dev")

    self_view = await ta.get(f"/api/v1/tenants/{tenant['tenant_id']}")
    assert self_view.status_code == 200
    assert "namespace_ref" not in self_view.json()["data"]

    bindings = await ta.get(f"/api/v1/tenants/{tenant['tenant_id']}/resource-bindings")
    assert bindings.status_code == 200
    item = bindings.json()["data"]["items"][0]
    assert item["resource_name"] == "ray-self"
    assert "credential_ref" not in item and "config" not in item  # sanitized

    cross = await ta.get(f"/api/v1/tenants/{other['tenant_id']}")
    assert cross.status_code == 404  # non-disclosure, not 403


async def test_projects_and_members_flow(admin, client, mailbox):
    tenant = await create_tenant(admin, "proj-co")
    tid = tenant["tenant_id"]
    storage = await _register_resource(admin, "vol-1", "storage", "physical")
    binding = (await _bind(admin, tid, storage["resource_id"], "shared"))["data"]

    owner_id = await preregister(admin, "owner@zqomni.dev", "Owner")

    missing_storage = await admin.post(
        f"/api/v1/tenants/{tid}/projects",
        json={"name": "grasping-v2", "display_name": "Grasping", "owner_user_id": owner_id},
    )
    assert missing_storage.status_code == 422  # storage binding exists => required

    r = await admin.post(
        f"/api/v1/tenants/{tid}/projects",
        json={
            "name": "grasping-v2", "display_name": "Grasping v2",
            "owner_user_id": owner_id, "default_storage_binding_id": binding["binding_id"],
        },
    )
    assert r.status_code == 201, r.text
    project = r.json()["data"]
    pid = project["project_id"]

    dup = await admin.post(
        f"/api/v1/tenants/{tid}/projects",
        json={
            "name": "grasping-v2", "display_name": "Again",
            "owner_user_id": owner_id, "default_storage_binding_id": binding["binding_id"],
        },
    )
    assert dup.status_code == 409

    # Unbind guard: project references the binding as default storage.
    in_use = await admin.delete(
        f"/api/v1/admin/tenants/{tid}/resource-bindings/{binding['binding_id']}"
    )
    assert in_use.status_code == 409
    assert in_use.json()["data"]["error_code"] == "E_TNT_RESOURCE_IN_USE"

    # Membership: unknown template rejected; platform_operator not assignable.
    bad_template = await admin.put(
        f"/api/v1/projects/{pid}/members/{owner_id}",
        json={"persona_templates": ["persona.unknown"]},
    )
    assert bad_template.status_code == 422
    operator_template = await admin.put(
        f"/api/v1/projects/{pid}/members/{owner_id}",
        json={"persona_templates": ["persona.platform_operator"]},
    )
    assert operator_template.status_code == 422

    ok = await admin.put(
        f"/api/v1/projects/{pid}/members/{owner_id}",
        json={"persona_templates": ["persona.model_engineer", "persona.evaluation_lead"]},
    )
    assert ok.status_code == 200

    members = await admin.get(f"/api/v1/projects/{pid}/members")
    assert members.json()["data"]["total_size"] == 1

    # Materialization: RD binding at project scope, origin=project_membership.
    bindings = await admin.get(
        "/api/v1/role-bindings", params={"user_id": owner_id, "scope_type": "project"}
    )
    rows = bindings.json()["data"]["items"]
    assert len(rows) == 1
    assert rows[0]["role_id"] == "builtin:rd_engineer"
    assert rows[0]["origin"] == "project_membership"

    # Effective permissions at project include persona-template keys.
    eff = await admin.get(
        f"/api/v1/users/{owner_id}/effective-permissions",
        params={"scope_type": "project", "scope_id": pid},
    )
    keys = {e["key"] for e in eff.json()["data"]["allowed"]}
    assert "mlops.training_plan:create" in keys  # model_engineer template
    assert "mlops.evaluation_report:approve" in keys  # evaluation_lead template

    # Removing membership removes materialized bindings.
    r = await admin.delete(f"/api/v1/projects/{pid}/members/{owner_id}")
    assert r.status_code == 204
    bindings = await admin.get(
        "/api/v1/role-bindings", params={"user_id": owner_id, "scope_type": "project"}
    )
    assert bindings.json()["data"]["items"] == []

    # Archive is idempotent and freezes membership writes.
    archived = await admin.post(f"/api/v1/projects/{pid}:archive")
    assert archived.status_code == 200
    again = await admin.post(f"/api/v1/projects/{pid}:archive")
    assert again.status_code == 200
    frozen = await admin.put(
        f"/api/v1/projects/{pid}/members/{owner_id}",
        json={"persona_templates": ["persona.annotator"]},
    )
    assert frozen.status_code == 409
    assert frozen.json()["data"]["error_code"] == "E_STATE_INVALID"
