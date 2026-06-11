"""Atomic permission catalog, built-in role boundaries, persona templates.

Code-defined per FDD §2.3 ("catalog content is code-defined via migration at
deploy; built-in roles are code-defined, immutable, versioned with the
platform release"). The Alembic initial revision seeds these rows; the authz
service evaluates built-in boundaries from the structures below.

Scope lock: only M01/M02/M03 contribute *implemented* permission keys. Keys of
out-of-scope modules appear solely as catalog metadata because (a) the ten
§0.2.4 persona templates reference them and (b) the role composer must list
them; no business logic exists behind them.
"""
from dataclasses import dataclass, field

PLATFORM = "platform"
TENANT = "tenant"
PROJECT = "project"

ALL_SCOPES = [PLATFORM, TENANT, PROJECT]
PT = [PLATFORM, TENANT]
P_ONLY = [PLATFORM]

# Built-in role ids (FDD §2.3.4 stable ids).
ROLE_PA = "builtin:platform_admin"
ROLE_TA = "builtin:tenant_admin"
ROLE_OE = "builtin:ops_engineer"
ROLE_RD = "builtin:rd_engineer"

BUILTIN_ROLES: dict[str, dict] = {
    ROLE_PA: {"name": "Platform Administrator", "description": "Unrestricted platform-wide."},
    ROLE_TA: {
        "name": "Tenant Administrator",
        "description": "Unrestricted within assigned tenant(s), excluding platform-admin-only keys.",
    },
    ROLE_OE: {
        "name": "Operations Engineer",
        "description": "Management permissions over all compute/storage resources platform-wide; no business-resource permissions.",
    },
    ROLE_RD: {
        "name": "R&D Engineer",
        "description": "Usage permissions on tenant compute/storage plus business-resource permissions within assigned projects.",
    },
}

# FDD M03-6 built-in placement rules.
BUILTIN_PLACEMENT: dict[str, set[str]] = {
    ROLE_PA: {PLATFORM},
    ROLE_TA: {TENANT},
    ROLE_OE: {PLATFORM},
    ROLE_RD: {TENANT, PROJECT},
}


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    description: str
    owning_module: str
    scope_levels: list[str] = field(default_factory=lambda: ALL_SCOPES)
    service_only: bool = False

    @property
    def domain(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def resource(self) -> str:
        return self.key.split(".", 1)[1].split(":", 1)[0]

    @property
    def action(self) -> str:
        return self.key.split(":", 1)[1]


def _e(key: str, description: str, module: str, scopes: list[str], service_only: bool = False) -> CatalogEntry:
    return CatalogEntry(key, description, module, scopes, service_only)


# ---------------------------------------------------------------------------
# Implemented keys (M01/M02/M03 §2.x.5)
# ---------------------------------------------------------------------------

M01_KEYS = [
    _e("iam.user_session:delete", "Revoke all sessions of a user (M01-6).", "M01", P_ONLY),
    _e("iam.session_introspect:execute", "Gateway session introspection (M01-7).", "M01", P_ONLY, True),
]

M02_KEYS = [
    _e("tenancy.tenant:create", "Create tenants.", "M02", P_ONLY),
    _e("tenancy.tenant:read", "Read tenant profile.", "M02", PT),
    _e("tenancy.tenant:update", "Update tenant display fields/settings.", "M02", PT),
    _e("tenancy.tenant:admin", "Tenant lifecycle: suspend/reactivate/archive.", "M02", P_ONLY),
    _e("infra.resource:create", "Register inventory resources.", "M02", P_ONLY),
    _e("infra.resource:read", "Read inventory resources.", "M02", P_ONLY),
    _e("infra.resource:update", "Update inventory resources.", "M02", P_ONLY),
    _e("infra.resource:admin", "Decommission inventory resources.", "M02", P_ONLY),
    _e("tenancy.resource_binding:create", "Bind resources to tenants.", "M02", P_ONLY),
    _e("tenancy.resource_binding:read", "Read tenant resource bindings.", "M02", PT),
    _e("tenancy.resource_binding:delete", "Release tenant resource bindings.", "M02", P_ONLY),
    _e("tenancy.project:create", "Create projects in a tenant.", "M02", PT),
    _e("tenancy.project:read", "Read projects.", "M02", ALL_SCOPES),
    _e("tenancy.project:update", "Update project fields.", "M02", PT),
    _e("tenancy.project:admin", "Archive projects.", "M02", PT),
    _e("tenancy.project_member:read", "List project members.", "M02", ALL_SCOPES),
    _e("tenancy.project_member:update", "Upsert project members (persona templates).", "M02", PT),
    _e("tenancy.project_member:delete", "Remove project members.", "M02", PT),
]

M03_KEYS = [
    _e("iam.user:create", "Pre-register corporate emails.", "M03", P_ONLY),
    _e("iam.user:read", "Read user accounts.", "M03", PT),
    _e("iam.user:update", "Update user profile fields.", "M03", P_ONLY),
    _e("iam.user:admin", "User lifecycle deactivate/reactivate.", "M03", P_ONLY),
    _e("iam.permission:read", "Browse the atomic permission catalog.", "M03", ALL_SCOPES),
    _e("iam.role:create", "Compose custom roles.", "M03", PT),
    _e("iam.role:read", "Read roles.", "M03", ALL_SCOPES),
    _e("iam.role:update", "Recompose custom roles.", "M03", PT),
    _e("iam.role:delete", "Delete custom roles.", "M03", PT),
    _e("iam.role_binding:create", "Bind users to roles at a scope.", "M03", ALL_SCOPES),
    _e("iam.role_binding:read", "Read role bindings / effective permissions.", "M03", ALL_SCOPES),
    _e("iam.role_binding:delete", "Remove role bindings.", "M03", ALL_SCOPES),
    _e("audit.event:read", "Query the audit event store.", "M03", PT),
    _e("audit.event:create", "Append audit events (service plane, M03-11).", "M03", P_ONLY, True),
    _e("iam.access_review:create", "Generate access reviews (RPT-11).", "M03", PT),
    _e("iam.access_review:read", "Read access reviews.", "M03", PT),
    _e("iam.authz:execute", "Authorization decision point (service plane, M03-10).", "M03", P_ONLY, True),
]

# ---------------------------------------------------------------------------
# Catalog-only keys for out-of-scope modules (metadata: persona templates and
# the role composer reference them; no endpoint enforces them yet).
# ---------------------------------------------------------------------------

_BUSINESS: list[tuple[str, str, str]] = [
    # (key, description, owning module)
    ("data.campaign:create", "Create collection campaigns.", "M04"),
    ("data.campaign:read", "Read collection campaigns.", "M04"),
    ("data.campaign:update", "Update collection campaigns.", "M04"),
    ("data.ingest:create", "Open ingest manifests/sessions.", "M05"),
    ("data.ingest:read", "Read ingest sessions and recordings.", "M05"),
    ("data.ingest:update", "Update ingest sessions.", "M05"),
    ("data.ingest:execute", "Run ingest operations.", "M05"),
    ("data.quality:read", "Read quality reports/rules.", "M05"),
    ("data.quality:update", "Set quality statuses.", "M05"),
    ("data.quality:execute", "Run quality validation.", "M05"),
    ("data.alignment:create", "Create alignment policies/jobs.", "M06"),
    ("data.alignment:read", "Read episodes and alignment results.", "M06"),
    ("data.alignment:execute", "Run alignment/segmentation jobs.", "M06"),
    ("data.taxonomy:create", "Propose/manage taxonomies.", "M06"),
    ("data.snapshot:read", "Read dataset snapshots.", "M08"),
    ("data.snapshot:approve", "Publish/approve dataset snapshots.", "M08"),
    ("data.lineage:read", "Read lineage graphs.", "M06"),
    ("label.annotation_project:create", "Create annotation projects.", "M07"),
    ("label.annotation_project:read", "Read annotation projects.", "M07"),
    ("label.annotation_project:update", "Update annotation projects.", "M07"),
    ("label.annotation_project:admin", "Administer annotation projects.", "M07"),
    ("label.annotation_task:read", "Read annotation tasks.", "M07"),
    ("label.annotation_task:update", "Edit annotation tasks.", "M07"),
    ("label.annotation_task:execute", "Claim/submit annotation tasks.", "M07"),
    ("label.preannotation:read", "View pre-annotations.", "M07"),
    ("label.preannotation:execute", "Review pre-annotations.", "M07"),
    ("label.qa_review:create", "Create QA samples.", "M07"),
    ("label.qa_review:read", "Read QA reviews.", "M07"),
    ("label.qa_review:execute", "Perform QA reviews.", "M07"),
    ("label.qa_review:approve", "Adjudicate QA reviews.", "M07"),
    ("sim.scenario:create", "Create scenarios.", "M09"),
    ("sim.scenario:read", "Read scenarios.", "M09"),
    ("sim.scenario:update", "Update scenarios.", "M09"),
    ("sim.simulation_run:create", "Submit simulation runs.", "M10"),
    ("sim.simulation_run:read", "Read simulation runs.", "M10"),
    ("sim.simulation_run:execute", "Control simulation runs.", "M10"),
    ("sim.synthetic_batch:create", "Create synthetic batches.", "M10"),
    ("sim.synthetic_batch:read", "Read synthetic batches.", "M10"),
    ("sim.synthetic_batch:update", "Update synthetic validation status.", "M10"),
    ("sim.validation:execute", "Submit synthetic validation evidence.", "M10"),
    ("mlops.training_plan:create", "Create training plans.", "M11"),
    ("mlops.training_plan:read", "Read training plans.", "M11"),
    ("mlops.training_plan:update", "Update training plans.", "M11"),
    ("mlops.training_run:create", "Launch training runs.", "M11"),
    ("mlops.training_run:read", "Read training runs.", "M11"),
    ("mlops.training_run:execute", "Control training runs.", "M11"),
    ("mlops.model_candidate:create", "Register model candidates.", "M12"),
    ("mlops.model_candidate:read", "Read model candidates.", "M12"),
    ("mlops.evaluation_suite:create", "Create evaluation suites.", "M13"),
    ("mlops.evaluation_suite:read", "Read evaluation suites.", "M13"),
    ("mlops.evaluation_suite:update", "Update evaluation suites.", "M13"),
    ("mlops.evaluation_run:create", "Launch evaluation runs.", "M13"),
    ("mlops.evaluation_run:read", "Read evaluation runs.", "M13"),
    ("mlops.evaluation_run:execute", "Control evaluation runs.", "M13"),
    ("mlops.evaluation_report:approve", "Approve evaluation reports.", "M13"),
    ("release.candidate:create", "Assemble release candidates.", "M14"),
    ("release.candidate:read", "Read release candidates.", "M14"),
    ("failure.record:create", "Create failure records.", "M15"),
    ("failure.record:read", "Read failure records.", "M15"),
    ("failure.record:update", "Triage failure records.", "M15"),
    ("analytics.coverage:read", "Read coverage summaries.", "M18"),
    ("analytics.report:read", "Read analytics reports.", "M18"),
    ("analytics.milestone:read", "Read milestone reports.", "M18"),
    ("analytics.search:execute", "Run hybrid search.", "M18"),
    ("workbench.session:create", "Open 4D workbench sessions.", "M19"),
    ("workbench.session:read", "Read workbench sessions.", "M19"),
    ("orchestration.workflow:create", "Launch workflow runs.", "M16"),
    ("orchestration.workflow:read", "Read workflow runs.", "M16"),
    ("orchestration.approval:approve", "Decide approvals.", "M16"),
]

_OPS: list[tuple[str, str, str]] = [
    ("workflow.ops:execute", "Operate workflow runs (pause/resume/reprioritize).", "M16"),
    ("workflow.ops:admin", "Administer workflow operations.", "M16"),
    ("ops.quota:read", "Read quota policies/utilization.", "M17"),
    ("ops.quota:update", "Edit quota policies.", "M17"),
    ("ops.queue:read", "View queues.", "M17"),
    ("ops.incident:create", "Create incident annotations.", "M17"),
    ("ops.incident:read", "Read incidents.", "M17"),
    ("ops.incident:update", "Update incidents.", "M17"),
]

BUSINESS_DOMAIN_KEYS = [_e(k, d, m, ALL_SCOPES) for k, d, m in _BUSINESS]
OPS_DOMAIN_KEYS = [_e(k, d, m, PT) for k, d, m in _OPS]

CATALOG: list[CatalogEntry] = M01_KEYS + M02_KEYS + M03_KEYS + BUSINESS_DOMAIN_KEYS + OPS_DOMAIN_KEYS
CATALOG_BY_KEY: dict[str, CatalogEntry] = {e.key: e for e in CATALOG}

SERVICE_ONLY_KEYS = {e.key for e in CATALOG if e.service_only}
HUMAN_KEYS = {e.key for e in CATALOG if not e.service_only}

# ---------------------------------------------------------------------------
# Built-in role boundaries (FDD §2.3.1, normative table)
# ---------------------------------------------------------------------------

# Business domains carved out of OE per mandate.
BUSINESS_DOMAINS = {
    "data", "label", "sim", "mlops", "release", "failure", "analytics", "workbench", "orchestration",
}
# Infrastructure domains granted to OE platform-wide.
OE_DOMAINS = {"infra", "ops", "workflow"}
OE_EXTRA_KEYS = {
    "tenancy.resource_binding:create",
    "tenancy.resource_binding:read",
    "tenancy.resource_binding:delete",
    "tenancy.tenant:read",
    "iam.permission:read",
    "iam.role:read",
    "audit.event:read",  # M03-8 server-enforces the infra/tenancy/ops domain filter
}

# Platform-admin-only keys excluded from the TA boundary (FDD: tenant CRUD,
# resource inventory, user pre-registration, platform roles, session revoke).
TA_EXCLUDED_KEYS = {
    "tenancy.tenant:create",
    "tenancy.tenant:admin",
    "infra.resource:create",
    "infra.resource:read",
    "infra.resource:update",
    "infra.resource:admin",
    "tenancy.resource_binding:create",
    "tenancy.resource_binding:delete",
    "iam.user:create",
    "iam.user:update",
    "iam.user:admin",
    "iam.user_session:delete",
}

# RD usage-level keys, valid wherever the RD binding sits (tenant or project).
RD_USAGE_KEYS = {
    "tenancy.tenant:read",
    "tenancy.resource_binding:read",
    "tenancy.project:read",
    "tenancy.project_member:read",
    "iam.permission:read",
    "iam.role:read",
}


def builtin_allows(role_id: str, permission_key: str, binding_scope_type: str) -> bool:
    """Expand a built-in role's boundary for one key (M03-10 step 4).

    `binding_scope_type` is the scope the matched binding is attached at —
    RD grants business-domain keys only through project-scoped bindings
    ("within assigned projects"), while its usage keys apply from tenant
    bindings too.
    """
    if permission_key in SERVICE_ONLY_KEYS:
        return False
    domain = permission_key.split(".", 1)[0]
    if role_id == ROLE_PA:
        return True
    if role_id == ROLE_TA:
        return permission_key not in TA_EXCLUDED_KEYS
    if role_id == ROLE_OE:
        return domain in OE_DOMAINS or permission_key in OE_EXTRA_KEYS
    if role_id == ROLE_RD:
        if permission_key in RD_USAGE_KEYS:
            return True
        if domain in BUSINESS_DOMAINS:
            return binding_scope_type == PROJECT
        return False
    return False


def expand_builtin_keys(role_id: str, binding_scope_type: str) -> set[str]:
    return {k for k in HUMAN_KEYS if builtin_allows(role_id, k, binding_scope_type)}


# ---------------------------------------------------------------------------
# Persona permission-set templates (FDD §0.2.4, DA-01; ten seeded rows)
# ---------------------------------------------------------------------------

PERSONA_TEMPLATES: list[dict] = [
    {
        "template_key": "persona.data_collection_lead",
        "display_name": "Data Collection Lead",
        "description": "Plans campaigns and tracks coverage.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "data.campaign:create", "data.campaign:update", "data.campaign:read",
            "data.ingest:execute", "analytics.coverage:read",
        ],
    },
    {
        "template_key": "persona.robotics_data_engineer",
        "display_name": "Robotics Data Engineer",
        "description": "Runs ingestion, quality, alignment, and snapshot publication.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "data.ingest:create", "data.ingest:read", "data.ingest:update", "data.ingest:execute",
            "data.quality:read", "data.quality:update", "data.quality:execute",
            "data.alignment:create", "data.alignment:read", "data.alignment:execute",
            "data.snapshot:approve", "data.lineage:read",
        ],
    },
    {
        "template_key": "persona.annotator",
        "display_name": "Annotator",
        "description": "Works annotation tasks and reviews pre-annotations.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "label.annotation_task:read", "label.annotation_task:execute",
            "label.preannotation:read", "label.preannotation:execute",
        ],
    },
    {
        "template_key": "persona.annotation_qa_lead",
        "display_name": "Annotation QA Lead",
        "description": "Owns annotation projects, QA sampling, and taxonomy proposals.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "label.annotation_project:create", "label.annotation_project:read",
            "label.annotation_project:update", "label.annotation_project:admin",
            "label.qa_review:create", "label.qa_review:read", "label.qa_review:execute",
            "label.qa_review:approve", "data.taxonomy:create",
        ],
    },
    {
        "template_key": "persona.simulation_engineer",
        "display_name": "Simulation Engineer",
        "description": "Builds scenarios and runs simulation/synthetic pipelines.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "sim.scenario:create", "sim.scenario:read", "sim.scenario:update",
            "sim.simulation_run:create", "sim.simulation_run:read", "sim.simulation_run:execute",
            "sim.synthetic_batch:create", "sim.synthetic_batch:read", "sim.synthetic_batch:update",
            "sim.validation:execute",
        ],
    },
    {
        "template_key": "persona.model_engineer",
        "display_name": "Model Engineer",
        "description": "Owns training plans/runs, model registration, release assembly.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "mlops.training_plan:create", "mlops.training_plan:read", "mlops.training_plan:update",
            "mlops.training_run:create", "mlops.training_run:read", "mlops.training_run:execute",
            "mlops.model_candidate:create", "release.candidate:create",
        ],
    },
    {
        "template_key": "persona.evaluation_lead",
        "display_name": "Evaluation Lead",
        "description": "Owns evaluation suites/runs/reports and failure triage.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "mlops.evaluation_suite:create", "mlops.evaluation_suite:read",
            "mlops.evaluation_suite:update", "mlops.evaluation_run:create",
            "mlops.evaluation_run:read", "mlops.evaluation_run:execute",
            "mlops.evaluation_report:approve", "failure.record:update",
        ],
    },
    {
        "template_key": "persona.platform_operator",
        "display_name": "Platform Operator",
        "description": "Operates workflows, quotas, queues, and incidents platform-wide.",
        "default_builtin_role": ROLE_OE,
        "platform_scoped": True,
        "permission_keys": [
            "workflow.ops:execute", "workflow.ops:admin", "ops.quota:read", "ops.quota:update",
            "ops.queue:read", "ops.incident:create", "ops.incident:read", "ops.incident:update",
        ],
    },
    {
        "template_key": "persona.governance_approver",
        "display_name": "Governance / Release Approver",
        "description": "Decides approvals; reads audit and access reviews.",
        "default_builtin_role": ROLE_TA,
        "platform_scoped": False,
        "permission_keys": [
            "orchestration.approval:approve", "audit.event:read", "iam.access_review:read",
        ],
    },
    {
        "template_key": "persona.program_manager",
        "display_name": "Product / Program Manager",
        "description": "Read-mostly reporting and coverage visibility.",
        "default_builtin_role": ROLE_RD,
        "platform_scoped": False,
        "permission_keys": [
            "analytics.report:read", "analytics.coverage:read", "analytics.milestone:read",
        ],
    },
]

PERSONA_TEMPLATE_KEYS = {t["template_key"] for t in PERSONA_TEMPLATES}

# M02-10 validation: templates compatible with a user's built-in role default.
# persona.platform_operator is OE/platform-scoped and not assignable to projects.
PROJECT_ASSIGNABLE_TEMPLATES = {
    t["template_key"] for t in PERSONA_TEMPLATES if not t["platform_scoped"]
}

# M01-3 capability probe set: keys the UI needs to toggle navigation/actions.
UI_CAPABILITY_PROBE_KEYS = [
    "tenancy.tenant:create",
    "tenancy.tenant:read",
    "tenancy.tenant:update",
    "tenancy.tenant:admin",
    "infra.resource:read",
    "infra.resource:create",
    "tenancy.resource_binding:read",
    "tenancy.resource_binding:create",
    "tenancy.project:create",
    "tenancy.project:read",
    "tenancy.project_member:update",
    "iam.user:create",
    "iam.user:read",
    "iam.user:admin",
    "iam.permission:read",
    "iam.role:create",
    "iam.role:read",
    "iam.role_binding:create",
    "iam.role_binding:read",
    "audit.event:read",
    "iam.access_review:create",
    "iam.access_review:read",
    "iam.user_session:delete",
]
