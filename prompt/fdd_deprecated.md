# Functional Design Document: Humanoid Robotics Physical AI Data & Compute Infrastructure Platform

## 0. Domain Concept & Requirements Knowledge Base

### 0.1 Domain Knowledge Base

The platform is a Humanoid Robotics Physical AI Data & Compute Infrastructure Platform. Its governing business loop is:

`collection campaign -> raw recording -> intake validation -> alignment -> canonical episode/trajectory -> segmentation -> annotation/pre-annotation/QA -> dataset snapshot -> scenario/synthetic expansion -> training plan -> training run -> model candidate -> evaluation suite/report -> release candidate -> failure record -> remediation work request -> new data/simulation/annotation/training work`.

Core business entities: Tenant, Project, User, Role, Permission, Collection Campaign, Raw Recording, Ingest Manifest, Validation Report, Quality Finding, Alignment Policy, Episode, Trajectory Step, Segment, Scenario Tag, Annotation Project, Pre-Annotation, Annotation Set, Dataset Snapshot, Data Cohort, Scenario, Simulation Run, Synthetic Data Batch, Training Plan, Training Run, Model Candidate, Evaluation Suite, Evaluation Report, Release Candidate, Failure Record, Workflow Template, Work Request, Workflow Run, Physical Compute Resource, Logical Compute Service Resource, Physical Storage Resource, Logical Storage Service Resource, Workbench Session, Audit Event.

Mandatory platform-management additions from the transformation prompt are in scope and treated as explicit design constraints:

- Platform Login: one-time random code sent to pre-registered corporate email.
- Tenant Configuration: tenant isolation for compute/storage and business resources; tenant binds physical and logical compute/storage resources; projects exist under tenants.
- User Role Configuration: built-in roles Platform Administrator, Tenant Administrator, Operations Engineer, and R&D Engineer; permissions are modular atomic units.

User-added Analytics & Mining scope is in scope as an explicit product update:

- Hybrid Scalar-Vector Retrieval.
- Data Visualization for multimodal robot data.
- Tag/Attribute-based Distribution.
- High-dimensional Vector Clustering-based Distribution using projection/clustering methods such as t-SNE, UMAP, and HDBSCAN.

### 0.2 Research Findings & External References

Authoritative reference patterns applied to the design:

- NIST SP 800-63B and OWASP Authentication guidance for one-time-code login throttling, replay prevention, and secure authentication events.
- Kubernetes Multi-Tenancy and ResourceQuota patterns for tenant-level resource isolation and quota concepts.
- Ray/KubeRay patterns for logical compute services independent from physical compute inventory.
- ROS 2 bag, RLDS, and Open X-Embodiment patterns for raw robot recordings and canonical episode/trajectory representation.
- OpenLineage object model for dataset/job/run lineage across transformations, training, and evaluation.
- SageMaker Ground Truth, Label Studio, and NVIDIA TAO references for pre-annotation with human review and QA.
- NVIDIA Isaac Sim, Isaac Lab, Replicator, Cosmos, and OpenUSD references for governed simulation and synthetic data generation.
- MLflow Tracking/Model Registry and Kubeflow artifact patterns for training runs, model versions, metrics, artifacts, and lifecycle metadata.
- NIST AI RMF for evidence-based model/release governance.
- Apache Airflow/Kubeflow Pipelines for task graph workflows, dependencies, run history, retries, and output artifacts.
- CloudEvents/OpenTelemetry for event envelopes, structured logs, traces, and observability.
- OpenSearch/Elasticsearch vector retrieval references for scalar-filtered vector search and hybrid retrieval.
- UMAP, t-SNE, and HDBSCAN references for high-dimensional embedding inspection and clustering.
- Foxglove, Rerun, ROS message_filters, and Open3D references for synchronized multimodal robot data review and point-cloud/timeline visualization.


## 1. Executive Summary & Module Map

This FDD defines the implementation-ready functional design for the Humanoid Robotics Physical AI Data & Compute Infrastructure Platform. The module map below is the validated decomposition baseline used by all module, interface, data, permission, logging, backend service, and validation sections.

### 1.1 Final Module Map

| ID | Module | Primary ownership boundary |
|---|---|---|
| M01 | Platform Login | Identity verification and session lifecycle only. |
| M02 | Platform Management - Tenant Configuration | Tenant/project boundaries and tenant-bound compute/storage resources. |
| M03 | Platform Management - User Role Configuration | User pre-registration, roles, atomic permissions, role assignments, authorization decisions. |
| M04 | Data Collection Campaign Management | Campaign purpose, robot/task/environment context, coverage goals, restrictions, lifecycle. |
| M05 | Raw Data Ingestion & Intake Validation | Immutable raw recording registration, manifest import, validation reports, quality state, quarantine. |
| M06 | Alignment, Episode Normalization & Segmentation | Alignment policy, canonical episodes/trajectories, segments, scenario/action tags. |
| M07 | Annotation, Pre-Annotation & QA | Annotation projects, tasks, machine suggestions, human review, QA, adjudication, annotation versions. |
| M08 | Data Catalog & Dataset Governance | Catalog assets, scalar discovery, reusable cohorts, immutable dataset snapshots, dataset cards, usage restrictions. |
| M09 | Analytics & Mining | Hybrid scalar-vector retrieval, multimodal analytics visualization, distribution computation, embedding projection/clustering, coverage-gap findings. |
| M10 | Scenario Catalog & Simulation Run Management | Scenario versions, scenario collections, simulation runs, output classification, real-to-sim links. |
| M11 | Synthetic Data Generation, Validation & Use Control | Synthetic generation requests, generated batches, validation reports, use controls, composition policies, deprecation. |
| M12 | Training Plan & Training Run Tracking | Training plans, approvals, training runs, metrics, artifacts, lineage to datasets and code/build refs. |
| M13 | Model Registry & Model Documentation | Model candidates, lifecycle status, model cards, baseline/challenger links, model lineage. |
| M14 | Evaluation Suite, Report & Failure Analysis | Evaluation suites, evaluation runs/reports, failure records, regression sets, remediation links. |
| M15 | Release Candidate & Artifact Governance | Release candidates, artifact packages, evidence checks, approvals, known limitations, no OTA execution. |
| M16 | Workflow Orchestration & Work Requests | Workflow templates, work requests, approvals, workflow runs, queue/status/retry history. |
| M17 | Compute & Storage Operations | Physical/logical compute/storage inventory, quota, utilization, priority, cost attribution. |
| M18 | Integrated Physical AI Workbench | Synchronized multimodal inspection and review surface; does not own source assets. |
| M19 | Reporting, Audit & Access Review | Dashboards, audit search/export, access-review reports, operational and governance reporting. |

### 1.2 Boundary Resolution

- M01 authenticates identity; M03 authorizes actions.
- M02 owns tenant/project/resource boundaries; M03 decides whether a user can act within those boundaries.
- M08 governs catalog and dataset snapshots; M09 computes retrieval, mining, analytics, distributions, projections, clusters, and coverage-gap findings.
- M09 computes visualization datasets; M18 renders synchronized review experiences and captures decisions/comments.
- M16 orchestrates workflows; business modules own the resulting business records.
- M17 owns capacity and quota; it does not own datasets, models, scenarios, or release decisions.


## 2. Module Designs



### 2.0 Shared API, Data, Permission, and Logging Conventions

#### Standard API Envelope

All successful JSON responses use:

```json
{
  "data": {},
  "meta": {
    "trace_id": "trc_...",
    "request_id": "req_...",
    "version": "resource-version-or-etag"
  }
}
```

All error responses use:

```json
{
  "error": {
    "error_code": "DOMAIN_SPECIFIC_CODE",
    "message": "Human-readable message",
    "field_errors": [{"field": "field_name", "message": "Reason"}],
    "retryable": false,
    "trace_id": "trc_..."
  }
}
```

Common status codes: `200`, `201`, `202`, `204`, `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, `503`.

All create, submit, launch, publish, approve, rerun, and export APIs accept `Idempotency-Key`. All mutable `PATCH`, approve, publish, deprecate, and status-transition APIs require `If-Match` or body field `version`.

#### Standard Scope Fields

Tenant-scoped business APIs include `tenant_id`. Project-scoped APIs include `tenant_id` and `project_id`. Platform-scoped APIs are restricted to Platform Administrator or Operations Engineer as specified.

#### Standard Log Format

```json
{
  "timestamp": "2026-06-10T00:00:00Z",
  "level": "INFO",
  "trace_id": "trc_...",
  "tenant_id": "ten_...",
  "project_id": "prj_...",
  "user_id": "usr_...",
  "module_id": "Mxx",
  "action": "resource.action",
  "resource_type": "DatasetSnapshot",
  "resource_id": "ds_...",
  "payload_summary": {},
  "result": "success|failure|blocked",
  "error_code": null,
  "latency_ms": 123
}
```

Sensitive data rules: never log one-time codes, session tokens, API keys, signed URLs, raw source credentials, artifact credentials, private storage paths, or full PII. Corporate email is logged as `r***@company.com` outside audit storage.

#### Built-in Role Permission Legend

Actions: C = Create, R = Read, U = Update, D = Delete/Archive/Deprecate, E = Execute/Launch/Submit, A = Admin/Approve/Override.

| Role | Baseline |
|---|---|
| Platform Administrator | Full platform-wide C/R/U/D/E/A. |
| Tenant Administrator | Full C/R/U/D/E/A inside assigned tenant. |
| Operations Engineer | C/R/U/D/E/A for compute, storage, workflow operations, and operational reports; R only for business context needed to operate jobs. |
| R&D Engineer | C/R/U/E for business resources inside assigned projects; R/use for tenant-bound compute/storage; no release approval by default. |

### M01 - Platform Login

#### Functional Design

Purpose: authenticate pre-registered corporate users with a one-time random code sent to corporate email. M01 does not own authorization, role assignment, tenant membership, or project membership; it only proves identity and creates sessions.

Primary functions:
- Request login code for a corporate email.
- Verify one-time code and create session.
- Return current authenticated user context.
- Logout and revoke session.
- Enforce expiry, replay prevention, attempt limits, throttling, and generic error messages.

UI/UX logic:
- Screen 1 field `corporate_email`: input type `email`, placeholder `name@company.com`, required, lowercased and trimmed on blur, real-time email-format validation, submit validation against M03 pre-registration.
- Screen 2 field `one_time_code`: input type `text`, length 6 to 10 by policy, paste-friendly, placeholder `Enter code`, no auto-correct, submit-only validation for expiry and match.
- Buttons: `Send code`, `Verify`, `Resend code`, `Logout`.
- Loading: disable submit and show inline spinner.
- Empty state: not applicable.
- Error states: generic `The email or code is invalid or expired`; `Too many attempts, try later`; `Network error, retry`.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/auth/email-code-requests` | Body `{corporate_email, client_context:{ip_hash, user_agent_hash}}` | Normalize email; call M03 user lookup; always return generic result; if active/pre-registered, create `EmailCodeChallenge`; send `auth.email_code.requested`; increment rate counters. | `202 {challenge_id, expires_in_seconds, resend_after_seconds}`. Errors: `AUTH_RATE_LIMITED`, `AUTH_EMAIL_DELIVERY_UNAVAILABLE`. | Idempotent by email plus time bucket. Concurrent requests invalidate previous unused challenge unless policy permits multiple active challenges. |
| `POST /api/v1/auth/sessions` | Body `{challenge_id, corporate_email, one_time_code}` | Check challenge exists, not expired, not consumed, attempts remaining; constant-time compare code hash; create `Session`; mark challenge consumed; load M03 role context. | `201 {session_id, user:{user_id,email_masked,display_name}, tenant_contexts:[...]}`. Errors: `AUTH_INVALID_CODE`, `AUTH_EXPIRED_CODE`, `AUTH_CHALLENGE_CONSUMED`, `AUTH_RATE_LIMITED`. | Challenge consume is transactional with session creation. Duplicate success returns existing session only within idempotency window. |
| `GET /api/v1/auth/me` | Header session token | Validate session; refresh last_seen; fetch M03 effective roles and M02 tenant/project memberships. | `200 {user, tenants, projects, roles, permissions_digest}`. Errors: `AUTH_SESSION_EXPIRED`. | Read-only; session refresh uses optimistic timestamp update. |
| `POST /api/v1/auth/logout` | Header session token | Revoke current session; emit audit event. | `204`. Errors: `AUTH_SESSION_NOT_FOUND` treated as success. | Idempotent by session ID. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `EmailCodeChallenge` | `challenge_id PK`, `user_id`, `corporate_email_hash`, `code_hash`, `expires_at`, `attempt_count`, `max_attempts`, `consumed_at`, `created_ip_hash`, `created_user_agent_hash`, `status` enum `active/expired/consumed/locked` | References M03 `UserIdentity`. |
| `Session` | `session_id PK`, `user_id`, `issued_at`, `expires_at`, `last_seen_at`, `revoked_at`, `auth_method=email_code`, `permissions_digest_at_login` | References M03 user and role assignment digest. |
| `LoginAttempt` | `attempt_id PK`, `email_hash`, `challenge_id`, `result`, `reason`, `ip_hash`, `created_at` | Used for throttling and audit. |

Storage: relational database for sessions and attempts; low-latency cache for active challenge and rate counters. Retention: challenge data expires quickly; login audit retained under security policy. Cache invalidation occurs on challenge consumption, expiry, and logout.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Unauthenticated pre-registered user | Code request | Own challenge status only | No | No | Verify code | No |
| Platform Administrator | No direct auth bypass | Audit only | Revoke sessions | Revoke sessions | No | Session admin via security policy |
| Tenant Administrator | No | Own tenant active-session view if delegated | No | No | No | No |
| Operations Engineer | No | Operational health only | No | No | No | No |
| R&D Engineer | Own login | Own session | Own logout | Own logout | Own login | No |

Credential scoping: session token maps to `user_id`; API credentials are not created in M01.

#### Logging Design

DEBUG: suppressed in production except challenge lifecycle counters without PII. INFO: code requested, session created, logout. WARN: throttling, expired challenge, invalid attempt. ERROR: mail delivery failure, session store failure. FATAL: global challenge validation unavailable. Logs ship to centralized observability; audit copies go to M19 immutable audit store.

### M02 - Platform Management - Tenant Configuration

#### Functional Design

Purpose: create tenant and project boundaries and bind compute/storage resources to tenants. M02 owns isolation configuration, not user authorization decisions.

Primary functions:
- Create, update, suspend, archive tenants.
- Create and update projects under tenants.
- Bind/unbind physical compute resources and logical compute services.
- Bind/unbind physical storage resources and logical storage services.
- View tenant isolation status and resource-binding health.

UI/UX logic:
- Tenant form fields: `tenant_name` string required max 128, `tenant_code` string required unique uppercase/slug, `owner_user_id` required active user, `status` enum, `description`, `default_retention_policy_ref`.
- Project form fields: `project_name`, `project_code`, `steward_user_id`, `cost_center`, `business_domain`, `retention_policy_ref`.
- Binding form fields: `resource_type` enum, `resource_id`, `binding_scope` enum `tenant/project`, `allowed_project_ids`, `quota_policy_id`, `priority_policy_id`, `usage_purpose`, `version`.
- Validation: tenant/project code uniqueness on submit; resource existence and health through M17; authorization through M03.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/tenants` | Body `{tenant_name, tenant_code, owner_user_id, description, default_retention_policy_ref}` | Authorize platform admin; validate code uniqueness; create tenant in `active` or `provisioning`; emit audit. | `201 {tenant_id, tenant_code, status, version}`. Errors `TENANT_CODE_EXISTS`, `USER_NOT_ACTIVE`. | Idempotency key required; unique code constraint. |
| `PATCH /api/v1/tenants/{tenant_id}` | Path `tenant_id`; body `{tenant_name?, owner_user_id?, status?, description?, version}` | Authorize; validate legal status transition; update tenant; invalidate scope caches in M03. | `200 {tenant_id,status,version}`. Errors `TENANT_INVALID_TRANSITION`, `VERSION_CONFLICT`. | `If-Match` required. |
| `POST /api/v1/tenants/{tenant_id}/projects` | Body `{project_name, project_code, steward_user_id, cost_center, retention_policy_ref}` | Authorize tenant admin; validate tenant active; create project; emit `project.created`. | `201 {project_id, project_code, status, version}`. | Idempotent by tenant plus project_code. |
| `POST /api/v1/tenants/{tenant_id}/compute-bindings` | Body `{resource_binding_type:physical_compute|logical_compute_service, resource_id, allowed_project_ids, quota_policy_id, priority_policy_id, version?}` | Authorize; verify resource exists in M17; ensure not conflicting with exclusive binding; create binding; notify M17. | `201 {binding_id,status,effective_scope}`. Errors `RESOURCE_NOT_FOUND`, `RESOURCE_BINDING_CONFLICT`. | Idempotent by tenant/resource/type. |
| `POST /api/v1/tenants/{tenant_id}/storage-bindings` | Body `{resource_binding_type:physical_storage|logical_storage_service, resource_id, allowed_project_ids, quota_policy_id, retention_policy_ref}` | Same as compute binding, with storage-specific retention and access policy checks. | `201 {binding_id,status,effective_scope}`. | Idempotent by tenant/resource/type. |
| `GET /api/v1/tenants/{tenant_id}/isolation-status` | Query `{include_resources:boolean}` | Authorize read; aggregate project list, bindings, health from M17, authorization digest from M03. | `200 {tenant_id,status,projects,compute_bindings,storage_bindings,isolation_findings}`. | Read-only snapshot. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `Tenant` | `tenant_id PK`, `tenant_code unique`, `tenant_name`, `owner_user_id`, `status`, `description`, `default_retention_policy_ref`, `created_at`, `updated_at`, `version` | Parent of `Project`; referenced by all tenant-scoped assets. |
| `Project` | `project_id PK`, `tenant_id`, `project_code unique within tenant`, `project_name`, `steward_user_id`, `cost_center`, `status`, `retention_policy_ref`, `version` | Child of tenant; scope for business assets. |
| `TenantResourceBinding` | `binding_id PK`, `tenant_id`, `project_id nullable`, `resource_type`, `resource_id`, `binding_mode shared/exclusive`, `quota_policy_id`, `priority_policy_id`, `status`, `version` | References M17 physical/logical resources. |
| `IsolationStatusSnapshot` | `snapshot_id`, `tenant_id`, `computed_at`, `resource_findings`, `policy_findings`, `status` | Derived view. |

Storage: relational database with tenant/project indexes; cache isolation status with invalidation on binding/resource/role changes. Archive policy retains tenant/project records for audit.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | Tenant/project/binding | All | All | Archive all | Binding validation | All |
| Tenant Administrator | Project, scoped binding requests | Own tenant | Own tenant projects | Archive own projects | Binding request | Tenant admin |
| Operations Engineer | Resource binding if delegated | Tenant/resource context | Binding health metadata | No business archive | Resource validation | Compute/storage binding ops |
| R&D Engineer | No | Assigned tenant/project | No | No | No | No |

Credential scoping: tenant/project API keys, if later created, must bind to tenant/project and atomic permissions from M03.

#### Logging Design

Audit: tenant create/update/archive, project create/archive, resource binding/unbinding, isolation policy change. WARN: conflicting binding, inactive resource, suspended tenant. ERROR: resource registry unavailable. FATAL: tenant isolation policy store unavailable.

### M03 - Platform Management - User Role Configuration

#### Functional Design

Purpose: pre-register users, manage roles and atomic permissions, assign roles to tenant/project/resource scopes, and evaluate authorization. M03 is the authorization source of truth.

Primary functions:
- Pre-register corporate email users.
- Activate/deactivate user identities.
- Maintain built-in and custom roles.
- Maintain atomic permission catalog.
- Assign roles to organization, tenant, project, resource, and individual scopes.
- Evaluate authorization for all APIs and workflow actions.

UI/UX logic:
- User form: `corporate_email` required corporate domain, `display_name`, `employment_status`, `default_tenant_id`, `manager_user_id`.
- Role form: `role_name`, `role_type` enum `built_in/custom`, `description`, `permissions[]`, `assignable_scopes[]`.
- Assignment form: `user_id`, `role_id`, `scope_type`, `scope_id`, `expires_at`, `justification`.
- Validation: prevent editing built-in role semantics except permission extension through explicit custom overlay; prevent privilege escalation by tenant admins.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/users` | Body `{corporate_email, display_name, employment_status, default_tenant_id}` | Authorize user admin; normalize email; enforce corporate domain; create `UserIdentity` in pre-registered/active state; emit audit. | `201 {user_id, corporate_email_masked, status, version}`. Errors `USER_EMAIL_EXISTS`, `INVALID_CORPORATE_DOMAIN`. | Idempotent by normalized email. |
| `PATCH /api/v1/users/{user_id}` | Body `{display_name?, employment_status?, status?, default_tenant_id?, version}` | Authorize; validate status transition; revoke sessions if disabled; invalidate auth cache. | `200 {user_id,status,version}`. | `If-Match` required. |
| `GET /api/v1/permissions` | Query `{module_id?, resource_type?, action?}` | Authorize read; return atomic permission catalog. | `200 {permissions:[{permission_id,module_id,resource_type,action,scope_levels}]}`. | Read-only. |
| `POST /api/v1/roles` | Body `{role_name, description, permissions:[permission_id], assignable_scopes}` | Authorize; validate permissions exist; prevent duplicate role name; create custom role. | `201 {role_id, role_name, version}`. | Idempotent by role_name within tenant/global scope. |
| `POST /api/v1/role-assignments` | Body `{user_id, role_id, scope_type, scope_id, expires_at, justification}` | Authorize assigner; validate scope from M02; detect privilege escalation; create assignment; invalidate cache. | `201 {assignment_id,effective_permissions_digest}`. Errors `ROLE_SCOPE_INVALID`, `PRIVILEGE_ESCALATION_BLOCKED`. | Idempotent by user/role/scope/active interval. |
| `POST /api/v1/authorization/evaluate` | Body `{user_id, action, resource_type, resource_id, tenant_id?, project_id?, context}` | Resolve active role assignments; load resource scope; evaluate atomic permission; include policy blockers such as restricted data. | `200 {allowed, denial_reasons, matched_permissions, decision_id}`. | Read-only; decision logged for sensitive denials. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `UserIdentity` | `user_id PK`, `corporate_email unique`, `display_name`, `employment_status`, `status`, `default_tenant_id`, `created_at`, `version` | Referenced by M01 sessions and all ownership fields. |
| `Permission` | `permission_id PK`, `module_id`, `resource_type`, `action`, `scope_levels`, `description`, `is_sensitive` | Many-to-many with roles. |
| `Role` | `role_id PK`, `role_name`, `role_type`, `tenant_id nullable`, `is_builtin`, `description`, `version` | Has permissions; assigned to users. |
| `RolePermission` | `role_id`, `permission_id`, `condition_json` | Atomic permission composition. |
| `RoleAssignment` | `assignment_id PK`, `user_id`, `role_id`, `scope_type`, `scope_id`, `expires_at`, `status`, `justification`, `version` | Defines effective access. |
| `AuthorizationDecisionLog` | `decision_id`, `user_id`, `action`, `resource_type`, `resource_id`, `allowed`, `denial_reasons`, `created_at` | Audit/debug for sensitive access. |

Storage: relational database; authorization cache by user plus tenant/project digest. Cache invalidated on user, role, assignment, tenant, project, or resource policy changes.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | Users/roles/assignments | All | All | Deactivate all | Evaluate | All |
| Tenant Administrator | Tenant users/assignments | Own tenant | Own tenant assignments | Deactivate tenant access | Evaluate own tenant | Tenant roles except platform/global |
| Operations Engineer | No default | Own identity and operational principals | No | No | Evaluate own access | No |
| R&D Engineer | No | Own identity/permissions | No | No | Evaluate own access | No |

Credential scoping: any non-user credential must map to a service principal with role assignments and expiration.

#### Logging Design

Audit all user pre-registration, deactivation, role creation/update, permission composition, role assignment, assignment expiration, and sensitive authorization denial. WARN on attempted privilege escalation. ERROR on policy evaluation store failure. FATAL if authorization service cannot answer decisions platform-wide.

### M04 - Data Collection Campaign Management

#### Functional Design

Purpose: register and manage collection campaigns so raw recordings have explicit business purpose, owner, robot/task/environment context, coverage goals, and usage restrictions.

Primary functions:
- Create campaign before or after data capture.
- Capture robot/embodiment, sensor modalities, environment, operator role, date range, responsible team.
- Capture privacy, consent, safety-relevance, licensing, and usage restrictions.
- Define target coverage goals.
- Manage campaign statuses: `planned`, `collecting`, `ingesting`, `validating`, `published`, `suspended`, `archived`.

UI/UX logic:
- Campaign form fields: `purpose`, `task_scope`, `robot_embodiment`, `sensor_modalities[]`, `environment`, `operator_role`, `collection_date_range`, `responsible_team`, `restriction_tags[]`, `coverage_goals[]`.
- Real-time validation: required fields, date range order, modality enum, tag enum.
- Submit validation: project permission, restriction policy owner, duplicate campaign name in project.
- Status UI shows only legal next states and requires reason for `suspended` or `archived`.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/campaigns` | Body `{tenant_id, project_id, name, purpose, task_scope, robot_embodiment, sensor_modalities, environment, operator_role, date_range, responsible_team, restriction_tags}` | Authorize `campaign.create`; validate project active; persist campaign in `planned`; emit audit for restriction tags. | `201 {campaign_id,status,version}`. Errors `CAMPAIGN_DUPLICATE`, `PROJECT_INACTIVE`. | Idempotent by project plus name plus date range. |
| `GET /api/v1/campaigns` | Query `{tenant_id, project_id?, status?, robot?, task?, owner?, date_from?, date_to?}` | Authorize list; apply tenant/project visibility; return paged campaigns. | `200 {items:[CampaignSummary], page}`. | Read-only. |
| `PATCH /api/v1/campaigns/{campaign_id}` | Body mutable metadata plus `version` | Authorize update; reject edits if archived except allowed description notes; update metadata; emit `campaign.updated`. | `200 {campaign_id,version}`. Errors `VERSION_CONFLICT`, `CAMPAIGN_ARCHIVED`. | `If-Match` required. |
| `POST /api/v1/campaigns/{campaign_id}/coverage-goals` | Body `{goals:[{dimension, target_value, target_count?, priority, acceptance_note}]}` | Authorize; validate dimensions such as task, environment, object, operator instruction, failure mode; replace or append as requested. | `201 {coverage_goal_ids, campaign_version}`. | Idempotent by client goal IDs. |
| `POST /api/v1/campaigns/{campaign_id}/status-transitions` | Body `{target_status, reason, version}` | Authorize; validate legal transition; if archiving, ensure no active ingestion unless override; persist history. | `200 {campaign_id,status,version}`. Errors `CAMPAIGN_INVALID_STATUS_TRANSITION`. | Transactional status update. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `CollectionCampaign` | `campaign_id PK`, `tenant_id`, `project_id`, `name`, `purpose`, `task_scope`, `robot_embodiment`, `environment`, `operator_role`, `date_from`, `date_to`, `responsible_team`, `status`, `owner_user_id`, `version` | Parent context for raw recordings and reports. |
| `CampaignModality` | `campaign_id`, `modality_type`, `required_flag`, `sensor_notes` | Drives manifest validation in M05. |
| `CampaignRestrictionTag` | `campaign_id`, `tag_type`, `tag_value`, `policy_ref`, `created_by` | Feeds M08 policy checks. |
| `CoverageGoal` | `goal_id`, `campaign_id`, `dimension`, `target_value`, `target_count`, `priority`, `status` | Used by M09 distribution analysis and M10 scenario expansion. |
| `CampaignStatusHistory` | `history_id`, `campaign_id`, `from_status`, `to_status`, `reason`, `changed_by`, `changed_at` | Audit trail. |

Storage: relational database; search index receives campaign summaries for catalog filters. Retention follows campaign/dataset retention policy.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Archive | Status transition | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Archive own tenant | Status transition | Approve restricted tags |
| Operations Engineer | No | Workflow context | No | No | No | No |
| R&D Engineer | Assigned projects | Assigned projects | Own/assigned campaigns | No | Status transition if owner | No |

#### Logging Design

INFO campaign created/updated/status changed. WARN suspended campaign, invalid transition attempt. ERROR persistence or policy validation failure. Audit restriction tag changes, status transitions, and archive actions.

### M05 - Raw Data Ingestion & Intake Validation

#### Functional Design

Purpose: ingest raw humanoid robot recordings as immutable source assets, preserve source metadata, validate intake quality, and quarantine/reject suspect recordings.

Primary functions:
- Create ingest manifests for expected files/streams/modalities.
- Submit batch import or active capture import requests.
- Register immutable `RawRecording` records.
- Preserve timestamps, source IDs, robot IDs, sensor IDs, and capture session metadata.
- Create validation reports identifying missing modalities, unreadable files, duplicates, incomplete metadata, and timestamp gaps.
- Classify quality status: `accepted`, `accepted_with_warnings`, `quarantined`, `rejected`, `requires_manual_review`.

UI/UX logic:
- Manifest wizard fields: `campaign_id`, `source_type`, `expected_modalities[]`, `expected_files[]`, `stream_descriptors[]`, `source_uri`, `credential_ref`, `robot_id`, `sensor_suite_id`.
- Import screen shows per-file and per-recording progress, checksum status, accepted/quarantined/rejected counts.
- Validation report renders finding severity, affected modality/file/time range, recommended remediation.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/ingest-manifests` | Body `{tenant_id, project_id, campaign_id, source_type, expected_modalities, expected_files, stream_descriptors, robot_id, sensor_suite_id}` | Authorize; validate campaign active; validate modalities against campaign; create manifest. | `201 {manifest_id,status,version}`. | Idempotent by campaign plus manifest external ID. |
| `POST /api/v1/raw-recordings/import-requests` | Body `{tenant_id, project_id, manifest_id, source_uri, credential_ref, import_mode:batch|active_capture, requested_quality_rules}` | Authorize execute; validate source credential reference without exposing secret; create import work request; enqueue S03. | `202 {import_request_id, workflow_run_id, status}`. Errors `MANIFEST_NOT_FOUND`, `SOURCE_UNREACHABLE_PRECHECK_FAILED`. | Idempotency key required; duplicate source checksum blocked. |
| `GET /api/v1/raw-recordings/{recording_id}` | Path `recording_id`; query `{include_modalities, include_validation}` | Authorize restricted-data read; load recording metadata and optional validation summary. | `200 {recording}`. Errors `RECORDING_NOT_FOUND`, `RESTRICTED_DATA_DENIED`. | Read-only. |
| `POST /api/v1/raw-recordings/{recording_id}/quarantine` | Body `{reason, quarantine_category, version}` | Authorize; verify recording not already dataset-member unless override; set quality status `quarantined`; block downstream selection. | `200 {recording_id, quality_status, version}`. | Transactional; version required. |
| `POST /api/v1/validation-runs` | Body `{tenant_id, project_id, recording_ids[], quality_rule_set_ref}` | Authorize execute; ensure recordings imported; create validation run; enqueue S04. | `202 {validation_run_id,status}`. | Idempotent by recording set plus rule set plus key. |
| `GET /api/v1/validation-reports/{report_id}` | Path `report_id` | Authorize read; return findings and resulting quality state. | `200 {report_id, recording_id, status, findings[]}`. | Read-only. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `IngestManifest` | `manifest_id`, `tenant_id`, `project_id`, `campaign_id`, `source_type`, `expected_files_json`, `expected_modalities_json`, `robot_id`, `sensor_suite_id`, `status`, `version` | Belongs to campaign. |
| `RawRecording` | `recording_id`, `tenant_id`, `project_id`, `campaign_id`, `source_external_id`, `capture_session_id`, `robot_id`, `sensor_suite_id`, `source_start_time`, `source_end_time`, `immutable_storage_uri_ref`, `checksum`, `quality_status`, `restriction_tags`, `version` | Root lineage asset for episodes. |
| `RawRecordingModality` | `modality_id`, `recording_id`, `modality_type`, `sensor_id`, `topic_or_stream_name`, `time_basis`, `file_ref`, `sample_count`, `status` | Child of recording. |
| `ValidationRun` | `validation_run_id`, `recording_ids`, `rule_set_ref`, `status`, `started_at`, `ended_at` | Produces reports. |
| `ValidationReport` | `report_id`, `recording_id`, `validation_run_id`, `quality_status`, `summary`, `created_at`, `approved_by nullable` | Child of recording. |
| `QualityFinding` | `finding_id`, `report_id`, `severity`, `finding_type`, `affected_modality`, `time_range`, `message`, `recommended_action` | Searchable metadata. |

Storage: immutable object storage for raw bytes; relational metadata; search index for quality findings; lineage graph root nodes emitted to M08/M19. Raw assets are never overwritten; corrections create new derived records or status changes.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | Status/metadata | Quarantine/archive | Import/validate | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Quarantine | Import/validate | Approve quarantine release |
| Operations Engineer | Manifests for ops | Technical metadata | Job state only | No | Run ops workflows | Retry/operate |
| R&D Engineer | Assigned projects | Allowed recordings | Metadata if owner | No | Import/validate | No |

#### Logging Design

Audit raw recording accepted, quarantined, rejected, restricted accessed, validation approved. INFO import/validation lifecycle. WARN missing modality, duplicate, timestamp gap, quarantine. ERROR source read/storage failure. FATAL immutable storage unavailable.

### M06 - Alignment, Episode Normalization & Segmentation

#### Functional Design

Purpose: preserve source timing and calibration assumptions, align multimodal streams to task-specific tolerances, normalize accepted recordings into canonical episodes/trajectories, and segment long recordings into usable units.

Primary functions:
- Define alignment policies by robot, sensor suite, modality, and task family.
- Run alignment jobs and flag records outside tolerance.
- Preserve spatial calibration and coordinate-frame metadata references.
- Create canonical episodes/trajectories with observations, robot state, actions/commands, language/task instructions, environment context, annotations, and outcomes when available.
- Create manual or assisted segments with source time ranges.
- Manage scenario/action tag versions.

UI/UX logic:
- Alignment policy UI fields: `policy_name`, `robot_embodiment`, `sensor_suite_id`, `task_family`, `modality_tolerances`, `required_calibration_refs`.
- Episode list filters by recording, campaign, quality, alignment status, task, tag, outcome.
- Segmentation editor validates time ranges against recording duration and prevents overlapping segments only when taxonomy requires exclusivity.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/alignment-policies` | Body `{tenant_id, project_id, name, robot_embodiment, sensor_suite_id, task_family, modality_tolerances, calibration_requirements}` | Authorize; validate tolerance units; create policy version. | `201 {alignment_policy_id, version}`. | Idempotent by name/version. |
| `POST /api/v1/alignment-runs` | Body `{tenant_id, project_id, recording_ids[], alignment_policy_id, output_episode_schema_ref}` | Authorize; verify recordings accepted or warnings allowed; create run; enqueue S05. | `202 {alignment_run_id,status}`. Errors `RECORDING_NOT_ACCEPTED`, `POLICY_NOT_FOUND`. | One active run per recording/policy unless override. |
| `GET /api/v1/episodes` | Query `{tenant_id, project_id, campaign_id?, recording_id?, task?, tag?, quality_status?, page}` | Authorize; search episode metadata. | `200 {items:[EpisodeSummary], page}`. | Read-only. |
| `GET /api/v1/episodes/{episode_id}` | Query `{include_steps?, include_lineage?, include_annotations?}` | Authorize; load episode metadata and optional payload refs. | `200 {episode}`. | Read-only. |
| `POST /api/v1/recordings/{recording_id}/segments` | Body `{segment_type, start_time, end_time, labels, tags, source:manual|assisted, notes}` | Authorize; validate time range; create segment and tag links; emit lineage. | `201 {segment_id, version}`. | Idempotent by client segment UUID. |
| `POST /api/v1/episodes/{episode_id}/segmentation-suggestion-requests` | Body `{taxonomy_ref, suggestion_scope:{start_time?,end_time?,modalities?}, generator_ref?, priority?}` | Authorize execute; verify episode readable and not archived; validate taxonomy/tag version; enqueue S06 for assisted segmentation. | `202 {segmentation_suggestion_request_id,status}`. Errors `EPISODE_NOT_FOUND`, `TAXONOMY_NOT_APPROVED`. | Idempotency key required; one active request per episode/taxonomy/scope unless override. |
| `PATCH /api/v1/segments/{segment_id}` | Body `{start_time?, end_time?, labels?, tags?, notes?, version}` | Authorize; validate update does not break published dataset lineage; if used by immutable dataset, create new segment version. | `200 {segment_id, version}`. | `If-Match` required; immutable references force new version. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `AlignmentPolicy` | `policy_id`, `tenant_id`, `project_id`, `name`, `robot_embodiment`, `sensor_suite_id`, `task_family`, `modality_tolerances_json`, `calibration_requirements_json`, `status`, `version` | Used by runs. |
| `AlignmentRun` | `run_id`, `policy_id`, `recording_ids`, `status`, `started_at`, `ended_at`, `failure_reason` | Produces episodes. |
| `Episode` | `episode_id`, `recording_id`, `tenant_id`, `project_id`, `time_range`, `task`, `outcome`, `quality_status`, `alignment_status`, `episode_payload_ref`, `lineage_root_id`, `version` | Derived from raw recording. |
| `TrajectoryStep` | `episode_id`, `step_index`, `timestamp`, `observation_refs`, `robot_state_ref`, `action_ref`, `instruction_ref`, `environment_context_ref` | Stored as columnar/object payload for scale. |
| `Segment` | `segment_id`, `episode_id`, `recording_id`, `segment_type`, `time_range`, `label_path`, `tags`, `source`, `status`, `version` | Used by annotation/evaluation/mining. |
| `ScenarioTagVersion` | `tag_version_id`, `taxonomy_name`, `tag_key`, `tag_value`, `parent_tag_id`, `status`, `approved_by` | Maintains reproducibility. |

Storage: relational metadata; columnar/object payloads for trajectory steps; lineage graph updates; search index for tags and segments. Published dataset references freeze episode/segment versions.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Deprecate | Align | Override |
| Tenant Administrator | Own tenant policies | Own tenant | Own tenant | Deprecate | Align | Approve taxonomy |
| Operations Engineer | No | Run status | No | No | Operate jobs | Retry failed jobs |
| R&D Engineer | Segments/policies in project | Project | Own project | No | Alignment run | No |

#### Logging Design

Audit alignment policy changes, episode creation, segment version changes, taxonomy/tag approval. WARN tolerance violation and unalignable record. ERROR missing calibration or payload write failure. FATAL episode store unavailable.

### M07 - Annotation, Pre-Annotation & QA

#### Functional Design

Purpose: manage annotation projects, machine-generated pre-annotations, human review, QA sampling, overlap review, adjudication, approval, and versioned annotation sets.

Primary functions:
- Create annotation projects over cohorts, episodes, or dataset snapshots.
- Define instructions, label schema, allowed labels, review policy, and acceptance criteria.
- Generate pre-annotations with generator identity and quality signal.
- Allow annotators to accept/edit/reject/comment.
- Perform QA sampling, overlap review, adjudication, and approval/rejection.
- Track annotation throughput, rework, rejection, and quality reports.

UI/UX logic:
- Project fields: `source_scope`, `source_ids`, `instructions`, `label_schema`, `review_policy`, `sampling_policy`, `acceptance_criteria`, `assignees`, `reviewers`.
- Annotation task UI opens M18 workbench with task context; toolbar actions bind to annotation update API.
- QA UI displays sampled items, disagreement, adjudication decision, reviewer comment, approval gate.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/annotation-projects` | Body `{tenant_id, project_id, source_type, source_ids, instructions, label_schema, review_policy, acceptance_criteria, assignees, reviewers}` | Authorize; validate source assets readable; validate label schema; create project and initial tasks. | `201 {annotation_project_id,status,task_count,version}`. | Idempotent by project/client ID. |
| `POST /api/v1/annotation-tasks` | Body `{annotation_project_id, asset_ids, assignee_user_ids, priority}` | Authorize; create tasks; prevent duplicate active task unless overlap review enabled. | `201 {task_ids}`. | Idempotent by project/asset/assignee. |
| `POST /api/v1/preannotations/generation-requests` | Body `{annotation_project_id, task_ids?, generator_ref, generation_parameters}` | Authorize execute; validate generator allowed by policy; enqueue S07. | `202 {generation_request_id,status}`. | Idempotency key required. |
| `PATCH /api/v1/annotations/{annotation_id}` | Body `{label_payload, review_status, comment?, version}` | Authorize assigned annotator/reviewer; validate label schema; save new annotation version if previous approved/used. | `200 {annotation_id,status,version}`. Errors `LABEL_SCHEMA_INVALID`, `TASK_LOCKED`. | Optimistic lock and task lease. |
| `POST /api/v1/annotation-sets/{set_id}/qa-reviews` | Body `{sampling_policy_ref, reviewer_user_ids, review_notes}` | Authorize QA; create QA review tasks; compute sample set via S08. | `202 {qa_review_id,status}`. | Idempotent by set/policy. |
| `POST /api/v1/annotation-sets/{set_id}/approval-decisions` | Body `{decision:approved|rejected|requires_rework, acceptance_metrics, reviewer_comment, version}` | Authorize approval; verify QA complete; set annotation-set status; emit audit. | `200 {annotation_set_id,status,version}`. | Version required; approved sets immutable except superseding version. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `AnnotationProject` | `annotation_project_id`, `tenant_id`, `project_id`, `source_type`, `instructions`, `label_schema_ref`, `review_policy_ref`, `status`, `owner_user_id`, `version` | Owns tasks and sets. |
| `AnnotationTask` | `task_id`, `annotation_project_id`, `asset_type`, `asset_id`, `assignee_user_id`, `status`, `priority`, `lock_owner`, `lock_expires_at` | Work item for annotator. |
| `PreAnnotation` | `preannotation_id`, `task_id`, `generator_ref`, `generated_at`, `confidence`, `quality_signal`, `label_payload`, `review_status` | Candidate labels. |
| `Annotation` | `annotation_id`, `task_id`, `author_user_id`, `label_payload`, `status`, `source_preannotation_id`, `comment`, `version` | Human-reviewed label. |
| `AnnotationSet` | `set_id`, `annotation_project_id`, `asset_membership_manifest_ref`, `label_version`, `approval_status`, `qa_metrics`, `version` | Versioned label release. |
| `QAReview` | `qa_review_id`, `set_id`, `sampling_policy_ref`, `reviewer_user_id`, `decision`, `findings`, `status` | Approval prerequisite. |

Storage: relational metadata and JSON/document store for label payloads; immutable manifests for approved annotation sets; search index for label/tag discovery. Cache invalidated on label-schema changes.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Archive | Preannotate | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Archive | Preannotate | Approve policies |
| Operations Engineer | No | Job status | No | No | Operate worker | No business approval |
| R&D Engineer | Projects/tasks | Assigned/project | Assigned annotations | No | Preannotation if allowed | QA only if granted |

#### Logging Design

Audit label schema change, annotation set approval/rejection, expert review routing, QA adjudication. INFO task assignment/submission. WARN high rejection/rework, schema mismatch. ERROR generator failure or task lock conflict.

### M08 - Data Catalog & Dataset Governance

#### Functional Design

Purpose: provide governed catalog discovery and immutable dataset snapshot publication. M08 owns catalog asset records, scalar search, cohorts, dataset snapshots, dataset cards, policy checks, and deprecation.

Primary functions:
- Catalog raw recordings, episodes, annotations, dataset snapshots, synthetic assets, and evaluation datasets.
- Scalar search by campaign, task, robot, environment, object, modality, status, owner, dataset membership, restriction, scenario tag, failure category, action label, evaluation outcome.
- Create reusable data cohorts.
- Publish immutable dataset snapshots with asset membership, version, owner, purpose, quality status, annotation status, lineage, publication time, composition, restrictions, and dataset card.
- Enforce usage restrictions at workflow selection time.
- Deprecate snapshots and link replacements.

UI/UX logic:
- Catalog search page: left filter panel, result table, asset detail drawer, cohort/save action, policy indicator.
- Dataset publish wizard: select cohort/assets, validate quality/annotation/synthetic composition, fill dataset card, run policy check, submit publish.
- Error states: `Restricted assets hidden`, `Dataset contains unapproved assets`, `Synthetic composition policy missing`.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `GET /api/v1/assets/search` | Query `{tenant_id, project_id?, asset_types[], filters, sort, page}` | Authorize visible scopes; apply scalar filters; exclude restricted assets without permission; return summaries and facets. | `200 {items, facets, page}`. | Read-only; search snapshot timestamp included. |
| `POST /api/v1/data-cohorts` | Body `{tenant_id, project_id, name, source_query?, asset_ids?, purpose, visibility}` | Authorize; materialize asset list or saved query; validate asset readability. | `201 {cohort_id, asset_count, version}`. | Idempotent by client cohort ID. |
| `POST /api/v1/dataset-snapshots` | Body `{tenant_id, project_id, dataset_name, source_cohort_id, purpose, owner_user_id, dataset_card, composition_policy_ref}` | Authorize create; validate cohort; create draft snapshot. | `201 {snapshot_id,status:draft,version}`. | Idempotent by dataset_name/version_label. |
| `GET /api/v1/dataset-snapshots/{snapshot_id}` | Query `{include_membership?, include_lineage?, include_card?}` | Authorize; return snapshot and optional immutable manifest refs. | `200 {dataset_snapshot}`. | Read-only. |
| `POST /api/v1/dataset-snapshots/{snapshot_id}/publish` | Body `{version_label, approval_ref?, version}` | Authorize publish; run policy checks; freeze membership manifest; set status `published`; emit lineage/audit. | `200 {snapshot_id,status:published,manifest_ref}`. Errors `DATASET_POLICY_VIOLATION`, `ASSET_NOT_APPROVED`. | Version required; publish is single transition. |
| `POST /api/v1/dataset-snapshots/{snapshot_id}/deprecate` | Body `{reason, replacement_snapshot_id?, version}` | Authorize; verify replacement if supplied; mark deprecated; retain lineage. | `200 {snapshot_id,status:deprecated}`. | Idempotent if same reason/replacement. |
| `POST /api/v1/dataset-policy-checks` | Body `{tenant_id, project_id, dataset_snapshot_ids, intended_use, workflow_type, model_or_release_context?}` | Evaluate restrictions, approval status, synthetic validation, retention, license/privacy tags. | `200 {allowed, blockers[], warnings[]}`. | Read-only; decision logged if restricted. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `CatalogAsset` | `asset_id`, `tenant_id`, `project_id`, `asset_type`, `source_module`, `source_resource_id`, `quality_status`, `annotation_status`, `synthetic_flag`, `restriction_tags`, `lineage_refs`, `status`, `indexed_at` | Projection of assets from source modules. |
| `DataCohort` | `cohort_id`, `tenant_id`, `project_id`, `name`, `source_query`, `asset_manifest_ref`, `purpose`, `visibility`, `owner_user_id`, `version` | Input to dataset, annotation, analytics. |
| `DatasetSnapshot` | `snapshot_id`, `tenant_id`, `project_id`, `dataset_name`, `version_label`, `status`, `owner_user_id`, `purpose`, `quality_status`, `annotation_status`, `composition_summary`, `publication_time`, `version` | Immutable dataset release. |
| `DatasetMembership` | `snapshot_id`, `asset_id`, `asset_version`, `weight`, `role:train|eval|holdout|reference` | Frozen on publish. |
| `DatasetCard` | `snapshot_id`, `intended_use`, `collection_method`, `known_gaps`, `quality_limitations`, `approval_status`, `restriction_summary` | Human-readable governance doc. |
| `UsageRestriction` | `restriction_id`, `resource_type`, `resource_id`, `tag_type`, `policy_ref`, `allowed_uses`, `blocked_uses`, `retention_status` | Policy enforcement. |

Storage: relational source of truth for datasets/cohorts; search index for catalog assets; object storage for immutable membership manifests and dataset cards; lineage graph for asset-to-dataset relations.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Deprecate | Policy check | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Deprecate | Policy check | Approve restricted datasets |
| Operations Engineer | No | Operational context only | No | No | No | No |
| R&D Engineer | Cohorts/drafts | Project visible assets | Drafts owned | No | Policy check | No approval unless granted |

#### Logging Design

Audit restricted asset access, cohort creation from restricted search, dataset publish, deprecation, dataset policy check denial, dataset card approval. INFO indexing and search. WARN overused/deprecated/restricted selected. ERROR policy engine or manifest write failure.

### M09 - Analytics & Mining

#### Functional Design

Purpose: provide advanced discovery and inspection capabilities across governed robot data assets without owning the underlying assets. M09 owns hybrid scalar-vector retrieval, analytical visualization datasets, tag/attribute distributions, embedding projections, clustering outputs, and coverage-gap findings.

Primary functions:
- Hybrid scalar-vector retrieval combining metadata filters with vector similarity.
- Save search result sets to data cohorts.
- Register, rebuild, and inspect vector indexes.
- Visualize multimodal robot data: trajectories, sensor heatmaps, temporal sequences, embedding scatterplots, cluster overlays.
- Compute tag/attribute-based distributions.
- Compute high-dimensional vector distribution via t-SNE/UMAP projection and HDBSCAN clustering.
- Create coverage-gap findings and convert them into work-request drafts.

UI/UX logic:
- Hybrid search fields: `asset_types[]`, `scalar_filters`, `query_text`, `seed_asset_id`, `embedding_vector_ref`, `vector_index_id`, `top_k`, `similarity_threshold`, `ranking_strategy`, `include_fields[]`.
- Distribution UI fields: `source_scope`, `source_id`, `group_by[]`, `metrics[]`, `breakdowns[]`, `time_window`, `real_synthetic_split`.
- Projection/clustering fields: `algorithm`, `source_cohort_id`, `vector_index_id`, `sample_strategy`, `random_seed`, `parameters`.
- Visualization output states: interactive scatterplot, cluster table, distribution chart, trajectory overlay, heatmap tile, temporal sequence view; all allow drill-down to M18 if user can read the source asset.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/analytics/hybrid-search` | Body `{tenant_id, project_id?, asset_types, scalar_filters, query_text?, seed_asset_id?, vector_index_id, top_k, similarity_threshold?, ranking_strategy}` | Authorize readable scopes; validate vector index; embed query text or load seed vector; apply scalar filters during candidate retrieval; compute score components; persist result summary. | `200 {result_id, items:[{asset_id, score, scalar_match, vector_score, highlights}], facets}`. Errors `VECTOR_INDEX_NOT_READY`, `ASSET_SCOPE_DENIED`. | Read computation; optional persisted result id. |
| `POST /api/v1/analytics/search-results/{result_id}/cohorts` | Body `{cohort_name, project_id, selected_asset_ids?, purpose}` | Authorize cohort create; verify selected IDs are subset of result and readable; call M08 cohort creation. | `201 {cohort_id, asset_count}`. | Idempotent by result/cohort_name. |
| `POST /api/v1/analytics/vector-indexes` | Body `{tenant_id, project_id?, name, asset_types, embedding_model_ref, vector_dimension, distance_metric, scalar_filter_fields, refresh_policy}` | Authorize analytics admin; validate fields exist in catalog; create index metadata; optionally enqueue build. | `201 {vector_index_id,status,version}`. | Unique index name per scope. |
| `POST /api/v1/analytics/vector-indexes/{index_id}/rebuild` | Body `{source_scope, source_id?, rebuild_mode:full|incremental, version}` | Authorize; lock index; enqueue S11; mark `rebuilding`. | `202 {index_id,status:rebuilding}`. | One active rebuild per index. |
| `POST /api/v1/analytics/visualization-views` | Body `{tenant_id, project_id, view_type:trajectory|heatmap|temporal_sequence|embedding_scatter|cluster_overlay, source_scope, source_id, parameters}` | Authorize source read; create view job; enqueue S14 if materialization needed. | `202 {view_id,status}`. | Idempotent by client view ID. |
| `GET /api/v1/analytics/visualization-views/{view_id}/data` | Query `{window?, level_of_detail?, format?}` | Authorize view/source read; return materialized data or `202` if still processing. | `200 {view_type,data,legend,source_refs}` or `202 {status}`. | Read-only; supports cache ETag. |
| `POST /api/v1/analytics/distribution-jobs` | Body `{tenant_id, project_id, source_scope, source_id, group_by, metrics, breakdowns, filters}` | Authorize; validate fields; enqueue S12. | `202 {distribution_job_id,status}`. | Idempotent by source plus field set plus key. |
| `GET /api/v1/analytics/distributions/{distribution_id}` | Query `{include_examples?}` | Authorize; return bins, counts, ratios, missing values, outliers, linked findings. | `200 {distribution_id, profile, findings}`. | Read-only. |
| `POST /api/v1/analytics/projection-jobs` | Body `{tenant_id, project_id, source_cohort_id, vector_index_id, algorithm:tSNE|UMAP, parameters, sample_strategy, random_seed}` | Authorize; validate cohort readable and algorithm params; enqueue S13. | `202 {projection_run_id,status}`. | One active projection per cohort/index/algorithm unless new seed/version. |
| `POST /api/v1/analytics/clustering-jobs` | Body `{tenant_id, project_id, source_cohort_id, vector_index_id, algorithm:HDBSCAN, parameters, link_projection_run_id?}` | Authorize; validate min cluster size etc.; enqueue S13. | `202 {cluster_run_id,status}`. | Idempotent by cohort/index/params. |
| `GET /api/v1/analytics/cluster-runs/{cluster_run_id}` | Query `{include_points?, include_examples?, include_gap_candidates?}` | Authorize; return cluster labels, noise points, metrics, representative assets, linked failures/tags. | `200 {cluster_run_id, clusters, noise_summary, coverage_gap_candidates}`. | Read-only. |
| `POST /api/v1/analytics/coverage-gap-findings` | Body `{tenant_id, project_id, source_type, source_id, finding_type, description, evidence_refs, severity, recommended_action}` | Authorize finding create; validate evidence refs; create governed finding. | `201 {finding_id,status,version}`. | Idempotent by source/evidence hash. |
| `POST /api/v1/analytics/coverage-gap-findings/{finding_id}/work-request-drafts` | Body `{target_workflow_type, objective, priority, suggested_inputs}` | Authorize; convert finding to M16 draft work request; do not auto-launch. | `201 {work_request_id,status:draft}`. | Idempotent by finding/workflow type. |
| `POST /api/v1/analytics/coverage-gap-findings/{finding_id}/scenario-drafts` | Body `{scenario_purpose, task, environment?, robot_embodiment?, objects?, suggested_variations?, owner_user_id}` | Authorize scenario draft creation; load finding evidence; create M10 scenario draft linked to the coverage-gap finding as a source reference. | `201 {scenario_id,status:draft,source_finding_id}`. Errors `FINDING_NOT_FOUND`, `FINDING_SCOPE_DENIED`. | Idempotent by finding/scenario_purpose/task hash. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `VectorIndex` | `index_id`, `tenant_id`, `project_id nullable`, `name`, `asset_types`, `embedding_model_ref`, `vector_dimension`, `distance_metric`, `scalar_filter_fields`, `refresh_policy`, `status`, `freshness_watermark`, `version` | Contains embeddings for M08 catalog assets. |
| `EmbeddingRecord` | `embedding_id`, `index_id`, `asset_id`, `asset_version`, `segment_id nullable`, `embedding_ref`, `embedding_hash`, `created_by_job_id`, `model_ref`, `created_at` | Links vector to source asset. |
| `HybridSearchResult` | `result_id`, `user_id`, `query_json`, `ranking_strategy`, `result_manifest_ref`, `created_at`, `expires_at` | Can become M08 cohort. |
| `VisualizationView` | `view_id`, `view_type`, `source_scope`, `source_id`, `parameters_json`, `materialized_data_ref`, `status`, `created_by` | Feeds UI and M18. |
| `DistributionProfile` | `distribution_id`, `source_scope`, `source_id`, `group_by`, `metrics_json`, `bins_json`, `missing_summary`, `created_at` | Drives coverage reporting. |
| `ProjectionRun` | `projection_run_id`, `algorithm`, `parameters_json`, `random_seed`, `source_cohort_id`, `vector_index_id`, `coordinates_ref`, `status` | Optional input to cluster views. |
| `ClusterRun` | `cluster_run_id`, `algorithm`, `parameters_json`, `source_cohort_id`, `vector_index_id`, `cluster_labels_ref`, `cluster_metrics`, `noise_summary`, `status` | Generates coverage gaps. |
| `CoverageGapFinding` | `finding_id`, `finding_type`, `source_type`, `source_id`, `severity`, `description`, `evidence_refs`, `recommended_action`, `status`, `owner_user_id` | Can draft M16 work request or M10 scenario request. |

Storage: vector database/search engine for embeddings plus scalar filters; relational metadata for jobs/views/findings; object storage for large coordinates, labels, and visualization tiles; warehouse/columnar store for distributions.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Delete/rebuild | All analytics | Override |
| Tenant Administrator | Own tenant indexes/findings | Own tenant | Own tenant | Archive | Run analytics | Approve index rebuild |
| Operations Engineer | No business finding | Job health only | Job priority only | No | Operate jobs | No business admin |
| R&D Engineer | Findings/views/jobs in project | Readable assets only | Own views/findings | Archive own views | Search/distribution/projection | No |

#### Logging Design

Audit hybrid search over restricted assets, vector index creation/rebuild, coverage-gap finding creation, result-to-cohort conversion. INFO analytics job lifecycle. WARN sampled projections, stale index, low cluster confidence, hidden restricted results. ERROR vector store failure, projection job failure. FATAL analytics index service unavailable for all tenants.

### M10 - Scenario Catalog & Simulation Run Management

#### Functional Design

Purpose: manage governed simulation scenarios and simulation runs linked to tasks, environments, objects, robot embodiments, failures, coverage gaps, and evaluation/training purposes.

Primary functions:
- Create and version scenarios with owner, purpose, validation status, source inspiration, and limitations.
- Group scenarios into scenario collections.
- Link scenarios to real episodes, failure records, and coverage-gap findings.
- Submit simulation runs from approved scenarios.
- Record scenario version, robot embodiment, task goal, variation plan, run owner, and output type.
- Classify simulation outputs and capture invalid-run reasons.

UI/UX logic:
- Scenario form fields: `task`, `environment`, `robot_embodiment`, `objects[]`, `variation_plan`, `intended_purpose`, `source_refs`, `known_limitations`, `validation_status`.
- Run form fields: `scenario_id`, `scenario_version`, `model_candidate_id?`, `variation_parameters`, `intended_output_type`, `priority`, `service_class`.
- Output classification UI requires choosing `synthetic_data`, `evaluation_evidence`, `scenario_diagnostics`, or `discarded`.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/scenarios` | Body `{tenant_id, project_id, task, environment, robot_embodiment, objects, variation_plan, intended_purpose, source_refs, known_limitations}` | Authorize; validate source refs from M08/M09/M14; create scenario version 1; status draft. | `201 {scenario_id,version,status}`. | Idempotent by project/client ID. |
| `PATCH /api/v1/scenarios/{scenario_id}` | Body scenario fields plus `version` | Authorize; if approved/validated, create new scenario version; else update draft. | `200 {scenario_id,current_version,status}`. | Version required. |
| `POST /api/v1/scenario-collections` | Body `{tenant_id, project_id, name, purpose, scenario_version_refs, release_plan_ref?}` | Authorize; validate scenario versions visible and compatible with purpose. | `201 {scenario_collection_id,scenario_count}`. | Idempotent by name. |
| `POST /api/v1/simulation-runs` | Body `{tenant_id, project_id, scenario_version_ref, model_candidate_id?, task_goal, variation_parameters, intended_output_type, priority}` | Authorize execute; verify scenario approved if policy requires; quota check M17; create run; enqueue S15. | `202 {simulation_run_id,status,workflow_run_id}`. Errors `SCENARIO_NOT_APPROVED`, `QUOTA_BLOCKED`. | Idempotency key required. |
| `GET /api/v1/simulation-runs/{run_id}` | Query `{include_outputs?, include_failures?}` | Authorize; return run status, outputs, failure reasons. | `200 {simulation_run}`. | Read-only. |
| `POST /api/v1/simulation-runs/{run_id}/rerun` | Body `{reason, parameter_overrides?, version}` | Authorize; clone context; create new run linked to prior run. | `202 {simulation_run_id,parent_run_id,status}`. | Idempotent by parent run plus key. |
| `POST /api/v1/simulation-runs/{run_id}/output-classifications` | Body `{output_id, classification, reason, version}` | Authorize; verify output exists; register classified output in M08/M11/M14 as applicable. | `200 {output_id,classification,registered_asset_ref}`. | Version required. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `Scenario` | `scenario_id`, `tenant_id`, `project_id`, `scenario_key`, `owner_user_id`, `status`, `current_version` | Parent of versions. |
| `ScenarioVersion` | `scenario_version_id`, `scenario_id`, `version_label`, `task`, `environment`, `robot_embodiment`, `objects_json`, `variation_plan_json`, `intended_purpose`, `source_refs`, `known_limitations`, `validation_status` | Used by runs and collections. |
| `ScenarioCollection` | `collection_id`, `tenant_id`, `project_id`, `name`, `purpose`, `scenario_version_refs`, `release_plan_ref`, `status` | Evaluation/training grouping. |
| `SimulationRun` | `run_id`, `scenario_version_id`, `model_candidate_id nullable`, `task_goal`, `variation_parameters`, `intended_output_type`, `status`, `owner_user_id`, `failure_reason` | Produces outputs. |
| `SimulationOutput` | `output_id`, `run_id`, `output_type`, `artifact_ref`, `classification`, `validation_status`, `registered_asset_ref` | Feeds M11/M14/M08. |

Storage: relational scenario/run metadata; object storage for outputs; catalog index receives outputs after classification.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Deprecate | Run/rerun | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Deprecate | Run/rerun | Approve scenario validation |
| Operations Engineer | No | Run health | Run priority only | No | Operate run | Retry failed dispatch |
| R&D Engineer | Project scenarios | Project | Own drafts | No | Submit runs | No |

#### Logging Design

Audit scenario validation, source links to failures/gaps, simulation run submission, output classification, rerun. WARN invalid-run reason and simulation artifact. ERROR backend dispatch failure. FATAL simulation dispatcher unavailable.

### M11 - Synthetic Data Generation, Validation & Use Control

#### Functional Design

Purpose: govern synthetic and augmented data generation so synthetic data is created only from approved scenarios, approved generation requests, or approved source datasets, with provenance, validation, use controls, and deprecation.

Primary functions:
- Create synthetic generation requests tied to a coverage gap or evaluation objective.
- Record source scenario, source data, generator identity, generation settings, and intended use.
- Mark every output as synthetic.
- Create validation reports with intended use, known limitations, failure modes, and suitability.
- Approve use for `training`, `evaluation`, or `exploration_only`.
- Manage synthetic-to-real composition policies for mixed datasets.
- Deprecate unrealistic, biased, mislabeled, or harmful synthetic batches.

UI/UX logic:
- Generation request fields: `source_scenario_id`, `source_dataset_snapshot_id?`, `coverage_gap_finding_id?`, `target_objective`, `generator_ref`, `variation_categories`, `output_modalities`, `intended_use`, `requested_volume`, `validation_policy_ref`.
- Validation report fields: `quality_summary`, `known_limitations`, `failure_modes`, `suitability`, `reviewer_comment`.
- Approval action requires explicit selected use and reviewer comment.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/synthetic-generation-requests` | Body `{tenant_id, project_id, source_scenario_id?, source_dataset_snapshot_id?, coverage_gap_finding_id?, target_objective, generator_ref, generation_settings, intended_use, requested_volume}` | Authorize; verify approved scenario/source dataset; verify objective/gap exists; create request; quota check; enqueue S16. | `202 {generation_request_id,status,workflow_run_id}`. Errors `SOURCE_NOT_APPROVED`, `SYNTHETIC_USE_NOT_ALLOWED`. | Idempotency key required. |
| `GET /api/v1/synthetic-batches/{batch_id}` | Query `{include_validation?, include_lineage?}` | Authorize; load batch metadata, provenance, validation status, use controls. | `200 {synthetic_batch}`. | Read-only. |
| `POST /api/v1/synthetic-batches/{batch_id}/validation-runs` | Body `{validation_policy_ref, intended_use, requested_checks?, reviewer_user_id?}` | Authorize execute; verify batch exists and is not deprecated; create validation run; enqueue S17. | `202 {synthetic_validation_run_id,status}`. Errors `SYNTHETIC_BATCH_DEPRECATED`, `VALIDATION_POLICY_NOT_FOUND`. | Idempotency key required; one active validation per batch/policy/intended_use. |
| `POST /api/v1/synthetic-batches/{batch_id}/validation-reports` | Body `{validation_policy_ref, findings, intended_use_assessment, known_limitations, failure_modes, reviewer_user_id?}` | Authorize; validate batch exists; create immutable validation report; set batch validation status. | `201 {validation_report_id,batch_status}`. | Idempotent by batch/policy/version. |
| `POST /api/v1/synthetic-batches/{batch_id}/approval-decisions` | Body `{decision:approved|rejected|exploration_only, allowed_uses, reviewer_comment, version}` | Authorize data owner/governance; require validation report; update use control. | `200 {batch_id,validation_status,allowed_uses}`. Errors `VALIDATION_REQUIRED`. | Version required. |
| `POST /api/v1/synthetic-batches/{batch_id}/deprecate` | Body `{reason, affected_downstream_assets?, replacement_batch_id?, version}` | Authorize; mark deprecated; emit catalog and lineage event; downstream policy checks warn/block future use. | `200 {batch_id,status:deprecated}`. | Idempotent if same reason. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `SyntheticGenerationRequest` | `request_id`, `tenant_id`, `project_id`, `source_scenario_id`, `source_dataset_snapshot_id`, `coverage_gap_finding_id`, `target_objective`, `generator_ref`, `settings_json`, `intended_use`, `requested_volume`, `status` | Creates batches. |
| `SyntheticDataBatch` | `batch_id`, `request_id`, `synthetic_flag=true`, `source_refs`, `artifact_manifest_ref`, `generated_label_refs`, `generation_settings_hash`, `validation_status`, `allowed_uses`, `status`, `version` | Cataloged in M08. |
| `SyntheticValidationReport` | `report_id`, `batch_id`, `validation_policy_ref`, `quality_summary`, `known_limitations`, `failure_modes`, `suitability`, `created_by`, `created_at` | Required before approved use. |
| `SyntheticUsePolicy` | `policy_id`, `batch_id`, `allowed_uses`, `composition_limits`, `requires_human_review`, `status` | Enforced by M08/M12/M14. |
| `SyntheticDeprecation` | `deprecation_id`, `batch_id`, `reason`, `replacement_batch_id`, `created_by`, `created_at` | Lineage record. |

Storage: relational metadata, immutable generated artifact manifests in object storage, catalog/search projection in M08, lineage graph links to source scenario/data/generator.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Deprecate | Generate/validate | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Deprecate | Generate/validate | Approve allowed uses |
| Operations Engineer | No | Job health | No | No | Operate generation | No business approval |
| R&D Engineer | Requests in project | Project allowed | Own draft request | No | Generate if approved | No |

#### Logging Design

Audit generation request, batch creation, synthetic approval, allowed-use change, deprecation, mixed-dataset composition policy changes. WARN validation unsuitable, synthetic artifact detected, harmful batch. ERROR generator failure. FATAL generator registry unavailable.

### M12 - Training Plan & Training Run Tracking

#### Functional Design

Purpose: plan, approve, launch, track, and compare governed Physical AI model training runs with immutable dataset bindings and full lineage.

Primary functions:
- Create training plans with capability, model family, embodiment, task scope, objective, dataset snapshots, evaluation suite, owner, cost center, priority.
- Validate dataset usage restrictions before launch.
- Request approvals for restricted datasets or high-cost compute.
- Launch training workflows.
- Track training run status, metrics, artifacts, failure reason, reusable context, lineage.
- Compare runs across dataset versions, model candidates, and evaluation results.

UI/UX logic:
- Training plan fields: `target_capability`, `model_family`, `robot_embodiment`, `task_scope`, `training_objective`, `dataset_snapshot_ids`, `evaluation_suite_id`, `owner_user_id`, `cost_center`, `priority`, `approval_policy_ref`.
- Launch button first displays dataset policy check and quota check results; blocked launch shows exact blockers.
- Run page shows inputs, task graph, metrics stream, artifact list, failure reason, rerun context.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/training-plans` | Body `{tenant_id, project_id, target_capability, model_family, robot_embodiment, task_scope, training_objective, dataset_snapshot_ids, evaluation_suite_id, owner_user_id, cost_center, priority}` | Authorize; verify dataset snapshots immutable; run initial policy check; create plan draft/pending approval. | `201 {training_plan_id,status,policy_check_summary,version}`. | Idempotent by client plan ID. |
| `POST /api/v1/training-plans/{plan_id}/approval-requests` | Body `{approval_reason, requested_compute_class, restricted_dataset_justification, version}` | Authorize; compute required approvers; create approval work items in M16. | `202 {approval_request_id,status,required_approvers}`. | One active approval request per plan/version. |
| `POST /api/v1/training-plans/{plan_id}/launch` | Body `{workflow_template_id, launch_parameters, version}` | Authorize; verify approvals complete; run M08 policy check and M17 quota check; create training run; enqueue S18. | `202 {training_run_id,workflow_run_id,status}`. Errors `DATASET_POLICY_BLOCKED`, `APPROVAL_REQUIRED`, `QUOTA_BLOCKED`. | Idempotency key required. |
| `GET /api/v1/training-runs/{run_id}` | Query `{include_metrics?, include_artifacts?, include_lineage?}` | Authorize; load run, metrics, artifacts, lineage. | `200 {training_run}`. | Read-only. |
| `PATCH /api/v1/training-runs/{run_id}/status` | Body `{status, failure_reason?, reusable_context?, version}` | Worker/operator only; validate state transition; persist terminal reason; emit lineage event. | `200 {run_id,status,version}`. | Version required; terminal states immutable except annotation fields. |
| `POST /api/v1/training-runs/{run_id}/metrics` | Body `{metrics:[{name,value,step,timestamp,metadata}]}` | Validate run active; batch insert metrics; update summaries. | `202 {accepted_count}`. | Idempotent by metric name/step/source. |
| `POST /api/v1/training-runs/{run_id}/artifacts` | Body `{artifact_type, artifact_ref, checksum, metadata, produced_at}` | Validate run; register artifact; if model artifact, notify M13 registration. | `201 {artifact_id}`. | Idempotent by checksum/run/type. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `TrainingPlan` | `plan_id`, `tenant_id`, `project_id`, `target_capability`, `model_family`, `robot_embodiment`, `task_scope`, `objective`, `evaluation_suite_id`, `owner_user_id`, `cost_center`, `priority`, `approval_status`, `version` | Parent of runs. |
| `TrainingPlanDatasetBinding` | `plan_id`, `dataset_snapshot_id`, `dataset_version`, `composition_type`, `intended_role`, `policy_check_result_id` | Immutable input binding. |
| `TrainingRun` | `run_id`, `plan_id`, `workflow_run_id`, `status`, `started_at`, `ended_at`, `failure_reason`, `reusable_context`, `resource_summary`, `version` | Produces artifacts and model candidate. |
| `TrainingMetric` | `metric_id`, `run_id`, `name`, `value`, `step`, `timestamp`, `metadata_json` | For comparison. |
| `TrainingArtifact` | `artifact_id`, `run_id`, `artifact_type`, `artifact_ref`, `checksum`, `metadata_json`, `status` | Feeds M13/M15. |
| `TrainingRunLineage` | `lineage_id`, `run_id`, `dataset_snapshot_ids`, `code_ref`, `parameter_hash`, `artifact_ids`, `created_at` | Release traceability. |

Storage: relational metadata; time-series/columnar metric storage; object/model artifact storage; lineage graph events. Failed runs retain reusable context.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Cancel/archive | Launch | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Cancel/archive | Launch | Approve high-cost/restricted |
| Operations Engineer | No plan changes | Run/job context | Operational status only | Cancel jobs if delegated | Operate workflow | Retry job |
| R&D Engineer | Plans in project | Project | Own draft plans | Cancel own draft | Launch if approved | No approval |

#### Logging Design

Audit plan creation, approval request, launch, dataset policy blocks, artifact registration, terminal status. INFO metrics/artifact ingestion. WARN quota or restricted-data blocker. ERROR training dispatch or artifact write failure.

### M13 - Model Registry & Model Documentation

#### Functional Design

Purpose: register model candidates as governed assets with unique versions, lifecycle states, lineage, model cards, reviewers, baselines, and deprecation history.

Primary functions:
- Register model candidate from training run/artifact.
- Maintain lifecycle states: `registered`, `evaluating`, `rejected`, `approved_for_limited_trial`, `release_candidate`, `released`, `deprecated`, `archived`.
- Store lineage to training run, dataset snapshots, code/build reference, evaluation reports, artifact package.
- Maintain model card with intended use, task scope, robot embodiment, known limitations, evaluation coverage.
- Link baseline/challenger relationships.
- Prevent release-candidate creation unless required lineage and evaluation evidence exist.

UI/UX logic:
- Registration form fields: `training_run_id`, `artifact_id`, `model_family`, `version_label`, `intended_use`, `limitations`, `owner_user_id`.
- Lifecycle UI shows only allowed next states and required evidence blockers.
- Model card editor requires intended use, robot embodiment, task scope, limitations, evaluation coverage before governance review.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/model-candidates` | Body `{tenant_id, project_id, training_run_id, artifact_id, model_family, version_label, owner_user_id, intended_use}` | Authorize; verify training run complete and artifact exists; create model candidate; attach lineage. | `201 {model_candidate_id,lifecycle_status,version}`. Errors `TRAINING_RUN_NOT_COMPLETE`, `ARTIFACT_NOT_FOUND`. | Idempotent by artifact checksum/version_label. |
| `GET /api/v1/model-candidates/{model_candidate_id}` | Query `{include_lineage?, include_model_card?, include_evaluations?}` | Authorize sensitive artifact read; return registry record. | `200 {model_candidate}`. | Read-only. |
| `PATCH /api/v1/model-candidates/{model_candidate_id}/lifecycle` | Body `{target_status, reason, evidence_refs?, version}` | Authorize transition; validate required evidence; persist status history; notify M14/M15 as needed. | `200 {model_candidate_id,lifecycle_status,version}`. Errors `MODEL_INVALID_TRANSITION`, `MODEL_EVIDENCE_MISSING`. | Version required. |
| `PUT /api/v1/model-candidates/{model_candidate_id}/model-card` | Body `{intended_use, task_scope, robot_embodiment, known_limitations, evaluation_coverage, owner_notes, version}` | Authorize; validate required fields; create new card version. | `200 {model_card_id,version}`. | Version required; card history retained. |
| `POST /api/v1/model-candidates/{model_candidate_id}/baseline-links` | Body `{baseline_model_candidate_id, relationship:baseline|challenger|supersedes, reason, version}` | Authorize; validate both model candidates same tenant/project or allowed cross-project; create link. | `201 {baseline_link_id}`. | Idempotent by model candidate/baseline/relationship. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `ModelCandidate` | `model_candidate_id`, `tenant_id`, `project_id`, `model_family`, `version_label`, `training_run_id`, `primary_artifact_id`, `owner_user_id`, `lifecycle_status`, `evaluation_readiness_status`, `version` | Feeds evaluation/release. |
| `ModelLifecycleHistory` | `history_id`, `model_candidate_id`, `from_status`, `to_status`, `reason`, `evidence_refs`, `changed_by`, `changed_at` | Audit. |
| `ModelCard` | `model_card_id`, `model_candidate_id`, `card_version`, `intended_use`, `task_scope`, `robot_embodiment`, `known_limitations`, `evaluation_coverage`, `approval_status` | Required for release. |
| `ModelLineage` | `lineage_id`, `model_candidate_id`, `training_run_id`, `dataset_snapshot_ids`, `code_ref`, `artifact_ids`, `evaluation_report_ids` | End-to-end traceability. |
| `BaselineLink` | `link_id`, `model_candidate_id`, `related_model_candidate_id`, `relationship`, `reason`, `created_by` | Evaluation comparison. |

Storage: relational registry; artifact refs in model artifact store; lineage graph. Model records archived, not deleted, except under exceptional admin policy.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Archive | Lifecycle | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Archive | Lifecycle | Approve lifecycle |
| Operations Engineer | No | Artifact/job metadata | No | No | No | No |
| R&D Engineer | Project models | Project | Own model card | No | Submit to evaluation | No approval |

#### Logging Design

Audit registration, lifecycle transition, model-card update, baseline link, deprecation. WARN missing evidence for transition. ERROR artifact/lineage registry failure.

### M14 - Evaluation Suite, Report & Failure Analysis

#### Functional Design

Purpose: define governed evaluation suites, execute evaluation runs, produce immutable evaluation reports, compare model candidates, and turn failures into remediation work.

Primary functions:
- Define evaluation suites with datasets, scenarios, metrics, baselines, and acceptance criteria.
- Distinguish offline dataset evaluation, simulation evaluation, and real-world trial evidence records.
- Execute evaluation runs.
- Produce reports comparing candidates against baselines and thresholds.
- Break results down by task, environment, object class, robot state, action phase, failure category, real/synthetic source.
- Create failure records, clusters, remediation work requests, and regression sets.

UI/UX logic:
- Suite fields: `scope`, `dataset_snapshot_ids`, `scenario_collection_ids`, `metrics`, `baselines`, `acceptance_criteria`.
- Report view shows pass/fail, metric breakdown, baseline comparison, failure table, workbench open action.
- Failure triage UI fields: `failure_category`, `severity`, `owner`, `recommended_action`, `linked_asset_refs`.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/evaluation-suites` | Body `{tenant_id, project_id, name, scope, dataset_snapshot_ids, scenario_collection_ids, metrics, baselines, acceptance_criteria}` | Authorize; validate immutable datasets and approved scenarios; create suite version. | `201 {evaluation_suite_id,version,status}`. | Idempotent by name/version. |
| `POST /api/v1/evaluation-runs` | Body `{tenant_id, project_id, evaluation_suite_id, model_candidate_ids, baseline_model_candidate_ids, run_mode}` | Authorize execute; verify candidate readiness; quota/policy checks; enqueue S20. | `202 {evaluation_run_id,status,workflow_run_id}`. Errors `MODEL_NOT_READY`, `EVALUATION_INPUT_BLOCKED`. | Idempotency key required. |
| `POST /api/v1/evaluation-reports` | Body `{evaluation_run_id, model_candidate_id, metric_results, failure_refs, baseline_comparison, report_summary}` | Worker creates draft; validate run complete; attach failures and metrics. | `201 {evaluation_report_id,status:draft}`. | Idempotent by run/model. |
| `POST /api/v1/evaluation-reports/{report_id}/approve` | Body `{decision:approved|rejected|superseded, reviewer_comment, version}` | Authorize; verify report complete; approved report becomes immutable; update model evaluation status. | `200 {report_id,status}`. | Version required; approved immutable. |
| `POST /api/v1/failure-records` | Body `{tenant_id, project_id, source, affected_model_candidate_id?, affected_dataset_id?, task, environment, failure_category, severity, owner_user_id, evidence_refs}` | Authorize; create failure; enqueue clustering S21. | `201 {failure_id,status:open}`. | Idempotent by source/evidence hash. |
| `POST /api/v1/failure-records/{failure_id}/remediation-work-requests` | Body `{target_workflow_type, objective, suggested_inputs, priority}` | Authorize; create M16 draft or submitted work request depending permissions. | `201 {work_request_id,status}`. | Idempotent by failure/workflow type. |
| `POST /api/v1/regression-sets` | Body `{tenant_id, project_id, name, failure_ids, dataset_snapshot_ids?, scenario_ids?, purpose}` | Authorize; validate failure refs; create regression set. | `201 {regression_set_id,item_count}`. | Idempotent by name. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `EvaluationSuite` | `suite_id`, `tenant_id`, `project_id`, `name`, `scope`, `version_label`, `dataset_snapshot_ids`, `scenario_collection_ids`, `metrics_json`, `acceptance_criteria_json`, `status` | Input to runs. |
| `EvaluationRun` | `run_id`, `suite_id`, `model_candidate_ids`, `baseline_model_candidate_ids`, `run_mode`, `status`, `started_at`, `ended_at`, `workflow_run_id` | Produces reports. |
| `EvaluationReport` | `report_id`, `run_id`, `model_candidate_id`, `status`, `metric_summary`, `baseline_comparison`, `breakdowns_ref`, `failure_refs`, `approved_at`, `version` | Immutable after approval. |
| `EvaluationMetricResult` | `metric_id`, `report_id`, `metric_name`, `value`, `threshold`, `pass_flag`, `breakdown_dimensions` | Report detail. |
| `FailureRecord` | `failure_id`, `source`, `affected_model_candidate_id`, `affected_dataset_id`, `task`, `environment`, `failure_category`, `severity`, `owner_user_id`, `status`, `evidence_refs` | Closed-loop asset. |
| `RegressionSet` | `regression_set_id`, `failure_ids`, `dataset_snapshot_ids`, `scenario_ids`, `purpose`, `status` | Used in future evaluations. |

Storage: relational metadata; immutable report artifacts in object storage; metrics in warehouse; failure evidence refs in catalog/workbench.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Supersede/archive | Run | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Supersede | Run | Approve release-critical reports |
| Operations Engineer | No | Run/job status | Operational status only | No | Operate jobs | Retry |
| R&D Engineer | Suites/failures in project | Project | Own failures/drafts | No | Run if allowed | Report approval only if granted |

#### Logging Design

Audit suite creation, evaluation run launch, report approval, failure severity/status change, remediation work request, regression set creation. WARN evaluation regression, threshold failure, missing evidence. ERROR run/report persistence failure.

### M15 - Release Candidate & Artifact Governance

#### Functional Design

Purpose: assemble release candidates from approved or conditionally approved model candidates and govern evidence, artifact packages, compatibility notes, limitations, approvals, and remediation. The module does not execute OTA delivery or robot fleet updates.

Primary functions:
- Assemble release candidate with model artifact, model card, dataset lineage, evaluation evidence, target robot/deployment class, compatibility notes, known limitations, rollback reference.
- Run evidence checks.
- Record artifact packaging and optimization metadata.
- Approve, reject, conditionally approve, or mark remediation required.
- Require reevaluation or reviewer acknowledgement on significant changes.

UI/UX logic:
- Release draft fields: `model_candidate_id`, `target_deployment_class`, `artifact_package_refs`, `evaluation_report_ids`, `known_limitations`, `compatibility_notes`, `rollback_reference`, `approvers`.
- Evidence checklist displays required/optional evidence and blockers.
- Approval decision requires decision, comment, limitations acknowledgement, and version.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/release-candidates` | Body `{tenant_id, project_id, model_candidate_id, target_deployment_class, evaluation_report_ids, known_limitations, compatibility_notes, rollback_reference}` | Authorize; verify model state; create draft release candidate; start evidence check. | `201 {release_candidate_id,status:draft,version}`. | Idempotent by model/target/version. |
| `GET /api/v1/release-candidates/{release_id}` | Query `{include_evidence?, include_decisions?}` | Authorize sensitive artifact/evidence read. | `200 {release_candidate}`. | Read-only. |
| `POST /api/v1/release-candidates/{release_id}/evidence-check` | Body `{version}` | Authorize; enqueue S22; verify lineage/evidence/model card/package/limitations. | `202 {evidence_check_id,status}`. | One active check per release version. |
| `POST /api/v1/release-candidates/{release_id}/approval-decisions` | Body `{decision:approved|rejected|conditional_approval|remediation_required, reviewer_comment, acknowledged_limitations, conditions?, version}` | Authorize approver; verify evidence check passed or record override; update status and model lifecycle. | `200 {release_id,status,decision_id}`. Errors `EVIDENCE_CHECK_BLOCKED`. | Version required; decision audit immutable. |
| `POST /api/v1/release-candidates/{release_id}/artifact-packages` | Body `{package_type, artifact_refs, optimization_steps, compatibility_notes, checksum}` | Authorize; register package metadata; changing package marks evidence stale. | `201 {artifact_package_id,release_status}`. | Idempotent by checksum/package type. |
| `PATCH /api/v1/release-candidates/{release_id}/status` | Body `{target_status, reason, version}` | Authorize; validate lifecycle transition; require reevaluation acknowledgement for material changes. | `200 {release_id,status,version}`. | Version required. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `ReleaseCandidate` | `release_id`, `tenant_id`, `project_id`, `model_candidate_id`, `target_deployment_class`, `status`, `owner_user_id`, `known_limitations`, `rollback_reference`, `version` | Tied to model and evidence. |
| `ArtifactPackage` | `package_id`, `release_id`, `package_type`, `artifact_refs`, `optimization_steps_json`, `checksum`, `compatibility_notes`, `created_at` | No OTA execution. |
| `ReleaseEvidenceChecklist` | `checklist_id`, `release_id`, `required_items_json`, `passed_items`, `blockers`, `warnings`, `status` | Required for decision. |
| `ReleaseApprovalDecision` | `decision_id`, `release_id`, `decision`, `reviewer_user_id`, `comment`, `conditions`, `created_at` | Immutable audit. |
| `ReleaseLimitation` | `limitation_id`, `release_id`, `description`, `severity`, `acknowledged_by`, `status` | Review artifact. |

Storage: relational governance records; package metadata and evidence manifests in object storage; audit immutable.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Archive | Evidence check | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant | Archive | Evidence check | Approve if policy grants |
| Operations Engineer | Packaging job status | Package metadata | Operational package metadata | No | Operate packaging workflow | No release decision |
| R&D Engineer | Drafts | Project releases | Own drafts | No | Submit evidence check | No approval |

#### Logging Design

Audit release candidate creation, evidence check, artifact package registration, approval decision, status change, limitation acknowledgement. WARN missing evidence, stale evidence, significant change. ERROR evidence registry or artifact package failure.

### M16 - Workflow Orchestration & Work Requests

#### Functional Design

Purpose: coordinate data, annotation, simulation, synthetic generation, training, evaluation, packaging, and reporting workflows using versioned templates, work requests, approvals, run history, retries, and queue visibility.

Primary functions:
- Create versioned workflow templates with task dependencies and expected outputs.
- Create work requests with requester, project, objective, inputs, priority, expected output, approval status.
- Enforce approval requirements for restricted data, high-cost compute, release-critical evaluation, release packaging.
- Start, pause, cancel, rerun, and inspect workflow runs.
- Register workflow outputs as governed assets in owning modules.
- Show queues by project, workflow type, priority, and status.

UI/UX logic:
- Work request fields: `workflow_type`, `objective`, `input_refs`, `priority`, `service_class`, `expected_outputs`, `required_approvals`, `cost_center`.
- Workflow run detail shows DAG, task states, retries, failure stage/category, affected inputs, recommended next action.
- Queue page filters by project, type, priority, service class, status.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/workflow-templates` | Body `{tenant_id?, name, workflow_type, version_label, task_graph, input_schema, output_schema, approval_rules}` | Authorize template admin; validate DAG acyclic and output types map to modules. | `201 {workflow_template_id,version,status}`. | Unique name/version. |
| `POST /api/v1/work-requests` | Body `{tenant_id, project_id, workflow_type, objective, input_refs, priority, service_class, expected_outputs, approval_context}` | Authorize; evaluate approval requirements; create draft/pending/approved request. | `201 {work_request_id,status,required_approvals}`. | Idempotent by client request ID. |
| `POST /api/v1/work-requests/{request_id}/approval-decisions` | Body `{decision, reviewer_comment, version}` | Authorize approver; persist decision; if all approved, mark request executable. | `200 {request_id,status}`. | Version required. |
| `POST /api/v1/workflow-runs` | Body `{work_request_id?, workflow_template_id, input_parameters, priority_override?}` | Authorize execute; validate approvals and quota; enqueue S23. | `202 {workflow_run_id,status}`. | Idempotency key required. |
| `GET /api/v1/workflow-runs/{run_id}` | Query `{include_tasks?, include_logs?, include_outputs?}` | Authorize; return run graph, tasks, retries, outputs, failure reason. | `200 {workflow_run}`. | Read-only. |
| `POST /api/v1/workflow-runs/{run_id}/pause` | Body `{reason, version}` | Authorize operations; request cooperative pause. | `202 {run_id,status:pausing}`. | Idempotent while pausing/paused. |
| `POST /api/v1/workflow-runs/{run_id}/cancel` | Body `{reason, version}` | Authorize; request cancellation; terminal canceled after workers checkpoint. | `202 {run_id,status:canceling}`. | Idempotent while canceling/canceled. |
| `POST /api/v1/workflow-runs/{run_id}/rerun` | Body `{scope:failed_tasks|all, parameter_overrides?, reason}` | Authorize; clone run context; create new run linked to parent. | `202 {workflow_run_id,parent_run_id}`. | Idempotency key required. |
| `GET /api/v1/workflow-queues` | Query `{tenant_id, project_id?, workflow_type?, priority?, status?}` | Authorize; aggregate queued/running/backlog by filters. | `200 {queues, summary}`. | Read-only. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `WorkflowTemplate` | `template_id`, `name`, `workflow_type`, `version_label`, `task_graph_json`, `input_schema`, `output_schema`, `approval_rules`, `status` | Used by runs. |
| `WorkRequest` | `request_id`, `tenant_id`, `project_id`, `requester_user_id`, `workflow_type`, `objective`, `input_refs`, `priority`, `service_class`, `approval_status`, `status`, `version` | Can launch run. |
| `ApprovalDecision` | `decision_id`, `request_id`, `reviewer_user_id`, `decision`, `comment`, `created_at` | Governance. |
| `WorkflowRun` | `run_id`, `template_id`, `work_request_id`, `status`, `started_at`, `ended_at`, `inputs_ref`, `outputs_ref`, `failure_reason`, `retry_count`, `version` | Executes tasks. |
| `WorkflowTaskRun` | `task_run_id`, `run_id`, `task_key`, `status`, `attempt`, `started_at`, `ended_at`, `failure_stage`, `affected_inputs`, `recommended_next_action` | Operational unit. |
| `WorkflowOutputRegistration` | `registration_id`, `run_id`, `task_run_id`, `output_type`, `owning_module_id`, `resource_id`, `status` | Connects to business modules. |

Storage: relational run state; durable event log; object storage for large inputs/outputs; observability store for task logs.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Cancel/archive | Run/rerun | Override |
| Tenant Administrator | Own tenant | Own tenant | Priority/status | Cancel | Run/rerun | Approve |
| Operations Engineer | Templates if delegated | All operational | Operational state | Cancel | Pause/rerun/retry | Operational admin |
| R&D Engineer | Work requests | Project runs | Own drafts | Cancel own pending | Launch allowed workflows | No approval unless granted |

#### Logging Design

Audit work request creation, approval, workflow launch, pause, cancel, rerun, output registration. INFO task lifecycle. WARN retry, blocked approval, quota warning. ERROR task/run failure. FATAL orchestrator unavailable.

### M17 - Compute & Storage Operations

#### Functional Design

Purpose: manage shared compute/storage inventory, quotas, utilization, priority, health, and cost/resource attribution. It distinguishes physical resources from logical service resources.

Primary functions:
- Register physical compute resources such as GPU machines.
- Register logical compute services such as Ray cluster instances.
- Register physical storage resources.
- Register logical storage services.
- Define quotas and warning thresholds.
- Check quota before workflows.
- Monitor utilization by workload class and cost center.
- Adjust job priority by authorized users.

UI/UX logic:
- Resource forms: `resource_name`, `resource_type`, `capacity`, `labels`, `health_endpoint_ref`, `credential_ref`, `location`, `owner_team`, `status`.
- Quota form: `tenant_id`, `project_id?`, `resource_class`, `hard_limit`, `soft_limit`, `warning_threshold`, `escalation_policy`.
- Utilization dashboard filters workload class, tenant, project, model, campaign, workflow, date range.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/resources/physical-compute` | Body `{name, resource_class, capacity, labels, health_endpoint_ref, credential_ref, status}` | Authorize ops; validate unique resource; store credential ref only; register health monitor. | `201 {resource_id,status,version}`. | Idempotent by resource name/provider ID. |
| `POST /api/v1/resources/logical-compute-services` | Body `{name, service_type, backing_resource_ids, endpoint_ref, capacity, labels, status}` | Authorize; validate backing resources; create logical service. | `201 {logical_service_id,status,version}`. | Idempotent by service name. |
| `POST /api/v1/resources/physical-storage` | Body `{name, storage_class, capacity, endpoint_ref, credential_ref, retention_capabilities, status}` | Authorize; register storage resource. | `201 {storage_resource_id,status}`. | Idempotent by provider ID. |
| `POST /api/v1/resources/logical-storage-services` | Body `{name, service_type, backing_storage_ids, endpoint_ref, quota_capabilities, status}` | Authorize; validate backing storage. | `201 {logical_storage_service_id,status}`. | Idempotent by name. |
| `GET /api/v1/resources/utilization` | Query `{tenant_id?, project_id?, resource_id?, workload_class?, date_from, date_to}` | Authorize; aggregate S24 samples and cost attribution. | `200 {utilization_summary, time_series}`. | Read-only. |
| `POST /api/v1/quotas` | Body `{tenant_id, project_id?, resource_class, soft_limit, hard_limit, warning_threshold, escalation_policy, version?}` | Authorize; validate tenant/project; create/update quota policy. | `201/200 {quota_policy_id,version}`. | Unique by scope/resource_class; version on update. |
| `POST /api/v1/quota-checks` | Body `{tenant_id, project_id, workflow_type, requested_resources, priority, cost_center}` | Compute current allocation, pending queue, requested resources, policy; return allow/block/escalate. | `200 {allowed, decision, blockers, warnings, required_approval}`. | Read-only decision logged. |
| `PATCH /api/v1/jobs/{job_id}/priority` | Body `{priority, reason, version}` | Authorize priority update; validate service class; notify workflow scheduler. | `200 {job_id,priority,version}`. | Version required. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `PhysicalComputeResource` | `resource_id`, `name`, `resource_class`, `capacity_json`, `labels`, `health_status`, `credential_ref`, `status`, `version` | Bound to tenants by M02. |
| `LogicalComputeService` | `service_id`, `service_type`, `backing_resource_ids`, `endpoint_ref`, `capacity_json`, `health_status`, `status`, `version` | Bound to tenants by M02. |
| `PhysicalStorageResource` | `storage_id`, `storage_class`, `capacity`, `endpoint_ref`, `credential_ref`, `retention_capabilities`, `health_status` | Bound to tenants by M02. |
| `LogicalStorageService` | `service_id`, `service_type`, `backing_storage_ids`, `endpoint_ref`, `quota_capabilities`, `health_status` | Bound to tenants by M02. |
| `QuotaPolicy` | `quota_policy_id`, `tenant_id`, `project_id nullable`, `resource_class`, `soft_limit`, `hard_limit`, `warning_threshold`, `escalation_policy`, `version` | Used by M16. |
| `UtilizationSample` | `sample_id`, `resource_id`, `tenant_id`, `project_id`, `workflow_run_id`, `workload_class`, `usage_metrics`, `sampled_at` | Aggregated reporting. |
| `CostAttributionRecord` | `record_id`, `tenant_id`, `project_id`, `campaign_id`, `model_candidate_id`, `workflow_run_id`, `cost_center`, `usage_summary`, `period` | Reporting. |

Storage: relational inventory/quota; time-series store for utilization; warehouse for attribution. Credentials stored only in secret manager references.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Retire | Quota check | Override |
| Tenant Administrator | Quota requests | Own allocation | Own quota request metadata | No | Quota check | Tenant quota approval if delegated |
| Operations Engineer | Resources/quotas | All operational | Resources/priority | Retire resources | Operate | Ops admin |
| R&D Engineer | No | Project available capacity | No | No | Quota check for own workflow | No |

#### Logging Design

Audit resource registration, resource retirement, quota create/update, priority change, quota override. WARN quota warning/breach, degraded resource. ERROR resource health poll failure, utilization ingest failure. FATAL quota service unavailable.

### M18 - Integrated Physical AI Workbench

#### Functional Design

Purpose: provide synchronized 4D review and analysis across video, point clouds/spatial data, robot state, action records, annotations, predictions, simulation outputs, evaluation outcomes, comments, failure tags, review decisions, saved views, and cohorts. M18 is not the source of truth for underlying assets.

Primary functions:
- Open raw recordings, aligned episodes, annotation tasks, simulation outputs, evaluation failures, and model comparison cases.
- Render synchronized timeline where data exists.
- Display asset status, source type, quality status, annotation status, synthetic/real indicator, model version, evaluation context.
- Create comments, issue links, failure tags, review decisions.
- Compare model candidates side by side on same episode/scenario.
- Save views or cohorts for dataset creation, simulation requests, or regression sets.

UI/UX logic:
- Session launcher fields: `context_type`, `asset_id`, `task_id?`, `model_candidate_ids?`, `time_range?`, `view_template`.
- Panels: video, point cloud/spatial, robot state, action stream, annotations, predictions, evaluation outcomes, comments, decision drawer.
- Missing modalities render explicit unavailable state, not blank panels.
- Review decisions validate module-specific permission before submit.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `POST /api/v1/workbench/sessions` | Body `{tenant_id, project_id, context_type, asset_id, task_id?, model_candidate_ids?, time_range?, view_template?}` | Authorize source read; create session; request timeline manifest S26. | `201 {workbench_session_id,status,timeline_status}`. | Idempotent by user/context/time range if key supplied. |
| `GET /api/v1/workbench/assets/{asset_id}/timeline` | Query `{context_type, time_range?, include_annotations?, include_predictions?, include_evaluation?}` | Authorize; return manifest if ready or trigger materialization. | `200 {timeline_manifest}` or `202 {status}`. | Cache by asset/version/context. |
| `GET /api/v1/workbench/assets/{asset_id}/frames` | Query `{modality, start_time, end_time, level_of_detail}` | Authorize; stream frame/window refs, not raw credentials. | `200 {frames, modality_status}`. | Read-only; supports range caching. |
| `POST /api/v1/workbench/comments` | Body `{session_id, asset_id, time_range?, body, linked_issue_ref?}` | Authorize comment create; sanitize; persist; emit audit if linked to status/decision. | `201 {comment_id}`. | Idempotent by client comment ID. |
| `POST /api/v1/workbench/failure-tags` | Body `{session_id, asset_id, time_range?, failure_category, severity?, note?, evidence_refs?}` | Authorize source read and failure-tag create; persist workbench failure tag; when `severity` or policy requires triage, create or update an M14 `FailureRecord` draft linked to the same evidence. | `201 {failure_tag_id, failure_record_id?, status}`. Errors `FAILURE_TAG_SCOPE_DENIED`, `FAILURE_CATEGORY_INVALID`. | Idempotent by asset/time_range/category/evidence hash. |
| `POST /api/v1/workbench/review-decisions` | Body `{session_id, context_type, target_resource_id, decision, reason, evidence_refs}` | Authorize module-specific decision; route to owning module if status-affecting; persist local review record. | `201 {review_decision_id, routed_resource_ref}`. | Idempotent by target/decision/evidence hash. |
| `POST /api/v1/workbench/saved-views` | Body `{session_id, name, layout_json, time_range, filters, visibility}` | Authorize; create reusable view. | `201 {saved_view_id}`. | Idempotent by name/user/session. |
| `POST /api/v1/workbench/cohorts` | Body `{session_id, source_selection, cohort_name, purpose}` | Authorize M08 cohort create; validate selected assets readable. | `201 {cohort_id}`. | Idempotent by selection hash/cohort name. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `WorkbenchSession` | `session_id`, `tenant_id`, `project_id`, `user_id`, `context_type`, `asset_id`, `task_id`, `model_candidate_ids`, `time_range`, `status` | Temporary review context. |
| `TimelineManifest` | `manifest_id`, `asset_id`, `asset_version`, `modalities`, `time_basis`, `coordinate_frame_refs`, `annotation_refs`, `prediction_refs`, `evaluation_refs`, `status` | Generated by S26/S14. |
| `FrameWindow` | `window_id`, `manifest_id`, `modality`, `start_time`, `end_time`, `data_ref`, `level_of_detail` | Playback unit. |
| `WorkbenchComment` | `comment_id`, `session_id`, `asset_id`, `time_range`, `body_sanitized`, `linked_issue_ref`, `created_by` | Review artifact. |
| `WorkbenchFailureTag` | `failure_tag_id`, `session_id`, `asset_id`, `time_range`, `failure_category`, `severity`, `note_sanitized`, `evidence_refs`, `failure_record_id nullable`, `created_by` | Lightweight visual failure marker; may route to M14 `FailureRecord`. |
| `ReviewDecision` | `decision_id`, `session_id`, `target_resource_type`, `target_resource_id`, `decision`, `reason`, `evidence_refs`, `routed_module_id` | May update owning module. |
| `SavedView` | `saved_view_id`, `session_id`, `name`, `layout_json`, `filters`, `visibility`, `owner_user_id` | Reusable view. |

Storage: relational review metadata; object storage for manifests/tiles; no ownership of source payloads.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | All | All | All | Delete review artifacts | Open/review | Override |
| Tenant Administrator | Own tenant | Own tenant | Own tenant review artifacts | Archive | Open/review | Approve if owning module permits |
| Operations Engineer | Operational comments | Job context | Operational comments | No | Open ops views | No business review |
| R&D Engineer | Comments/views/cohorts | Readable assets | Own comments/views | Archive own views | Open sessions | Review if assigned |

#### Logging Design

Audit review decisions, failure tags, saved cohorts, restricted asset open. INFO session open/close and timeline generated. WARN missing modality, partial manifest, denied review decision. ERROR frame decode or manifest materialization failure.

### M19 - Reporting, Audit & Access Review

#### Functional Design

Purpose: provide dashboards, audit search/export, access review, and operational/governance reporting across data, simulation, model, release, workflow, compute, and restricted access.

Primary functions:
- Data ingestion status by campaign/project/modality/quality.
- Dataset inventory and coverage.
- Annotation throughput/QA/rework reports.
- Scenario coverage and validation status.
- Training run inventory.
- Model comparison and release readiness dashboards.
- Closed-loop failure dashboard.
- Compute utilization, queue, quota, cost attribution, workflow failure trends.
- Restricted dataset/sensitive artifact/release decision audit and access review.

UI/UX logic:
- Dashboard filters: `tenant_id`, `project_id`, `campaign_id`, `robot`, `task`, `model_family`, `release_plan`, `date_range`, `status`, `owner`.
- Audit search fields: `actor_user_id`, `resource_type`, `resource_id`, `action`, `time_range`, `result`, `sensitive_only`.
- Export requires `justification`, `scope`, `date_range`, `approver` for restricted data.

#### Interface Design

| Interface | Request | Internal processing logic | Response and errors | Idempotency/concurrency |
|---|---|---|---|---|
| `GET /api/v1/dashboards/data-ingestion` | Query filters | Authorize; aggregate M04/M05 quality and campaign data. | `200 {summary, breakdowns, trends}`. | Read-only snapshot. |
| `GET /api/v1/dashboards/dataset-coverage` | Query filters | Aggregate M08/M09 distributions and coverage findings. | `200 {coverage_by_task, gaps, composition}`. | Read-only. |
| `GET /api/v1/dashboards/model-comparison` | Query `{tenant_id, project_id, evaluation_suite_id?, model_candidate_ids?}` | Aggregate M12/M13/M14 metrics and baseline links. | `200 {model_candidates, metric_matrix, regressions}`. | Read-only. |
| `GET /api/v1/dashboards/release-readiness` | Query filters | Aggregate M15 evidence checks, blockers, limitations, approval state. | `200 {release_candidates, blockers, missing_evidence}`. | Read-only. |
| `GET /api/v1/dashboards/compute-utilization` | Query filters | Aggregate M16/M17 utilization, queue, quota, failures. | `200 {utilization, queues, quota, cost_attribution}`. | Read-only. |
| `GET /api/v1/audit-events` | Query `{tenant_id, project_id?, actor_user_id?, action?, resource_type?, resource_id?, time_range, page}` | Authorize audit read; apply restricted audit policy; return paged events. | `200 {items,page}`. | Read-only. |
| `POST /api/v1/audit-export-requests` | Body `{tenant_id, project_id?, scope, time_range, filters, justification, format}` | Authorize/export policy; create export request; enqueue S28; may require approval. | `202 {export_request_id,status}`. | Idempotent by requester/scope/time/filter hash. |
| `GET /api/v1/access-review-reports` | Query `{tenant_id, project_id?, resource_type?, resource_id?, time_range}` | Authorize; compute users/roles/access events for restricted resources. | `200 {reports, findings}`. | Read-only; snapshot timestamp returned. |

#### Data Design

| Model | Attributes and constraints | Relationships |
|---|---|---|
| `AuditEvent` | `audit_event_id`, `tenant_id`, `project_id`, `actor_user_id`, `module_id`, `action`, `resource_type`, `resource_id`, `result`, `payload_summary`, `sensitive_flag`, `created_at` | Immutable event log. |
| `DashboardSnapshot` | `snapshot_id`, `dashboard_type`, `tenant_id`, `project_id`, `filters_hash`, `data_ref`, `computed_at`, `freshness_status` | Cached dashboard. |
| `ReportDefinition` | `report_definition_id`, `name`, `report_type`, `filters_schema`, `required_permissions` | Template. |
| `ReportRun` | `report_run_id`, `definition_id`, `requested_by`, `filters_json`, `status`, `output_ref`, `created_at` | Export/report output. |
| `AuditExportRequest` | `export_request_id`, `scope`, `time_range`, `justification`, `approval_status`, `status`, `output_ref` | Governed export. |
| `AccessReviewReport` | `report_id`, `resource_type`, `resource_id`, `review_period`, `subjects`, `findings`, `status` | Governance review. |

Storage: immutable audit log, search index for audit queries, warehouse for dashboards, object storage for exports. Audit export outputs expire per retention policy.

#### Permission Design

| Role | C | R | U | D | E | A |
|---|---:|---:|---:|---:|---:|---:|
| Platform Administrator | Report/export | All | Report definitions | Archive reports | Export | Approve all |
| Tenant Administrator | Tenant reports | Own tenant | Tenant definitions | Archive tenant reports | Export tenant audit | Approve tenant exports |
| Operations Engineer | Operational reports | Ops dashboards/audit | Ops report notes | No | Export ops reports | No restricted approval |
| R&D Engineer | No default exports | Project dashboards | No | No | No | No |

#### Logging Design

Audit audit search on sensitive resources, export request, export approval, access review completion. INFO dashboard/report generation. WARN stale dashboard, export pending approval, access anomaly. ERROR report generation/export failure. FATAL audit log write path unavailable.

## 3. Backend Service Designs



### Shared Background Service Standards

#### Event Envelope

All events use the following envelope. Queue/topic technology is intentionally not prescribed by the FRD; the schema is transport-neutral.

```json
{
  "id": "evt_...",
  "type": "domain.event.name",
  "source": "module-or-service-name",
  "specversion": "1.0",
  "time": "2026-06-10T00:00:00Z",
  "subject": "resource-type/resource-id",
  "trace_id": "trc_...",
  "tenant_id": "ten_...",
  "project_id": "prj_...",
  "actor_user_id": "usr_...",
  "idempotency_key": "idem_...",
  "data": {}
}
```

#### Worker State Machine

Default worker state machine:

`received -> validated -> leased -> running -> checkpointed -> completed`

Failure branches:

- `received -> rejected`: invalid schema, permission/policy violation, unsupported input.
- `running -> retry_wait`: retryable infrastructure or dependency failure.
- `retry_wait -> running`: retry budget remains.
- `retry_wait -> dead_lettered`: retry budget exhausted.
- `running -> blocked`: business prerequisite not met, such as approval missing or dataset policy violation.
- `running -> canceled`: cooperative cancellation requested by M16.

#### Common Failure Recovery

- Durable lease is acquired before work starts.
- Acknowledgement occurs only after terminal status is persisted.
- Retry uses exponential backoff with jitter.
- Deduplication key is event ID plus business request ID.
- Dead-letter event contains masked input summary, failure stage, failure category, retry count, and operator recommendation.
- Status updates are written to the owning module record, not only to worker logs.

#### High Availability Baseline

Every service exposes health checks: liveness, readiness, dependency readiness, queue lag, and active lease count. Every service supports graceful shutdown: stop pulling messages, finish or checkpoint active work, release leases, and mark interrupted work retryable.

### S01 - Email Code Delivery Worker

**Purpose:** Deliver M01 one-time login codes after corporate email pre-registration is confirmed.

**Input:** `auth.email_code.requested`

```json
{
  "challenge_id": "chg_...",
  "user_id": "usr_...",
  "corporate_email_masked": "r***@company.com",
  "delivery_channel": "corporate_email",
  "expires_at": "timestamp"
}
```

**Output:** `auth.email_code.sent`, `auth.email_code.delivery_failed`.

**Processing logic:**
1. Validate event schema and challenge status.
2. Confirm user is active through M03 read model.
3. Render email template without logging code.
4. Send through corporate mail connector.
5. Persist delivery status and provider message ID.
6. Emit success/failure audit event.

**Concurrency:** bounded worker pool by provider send quota; partition by email hash to prevent resend races.

**HA:** circuit breaker for mail provider; retry transient provider errors; DLQ after retry exhaustion; fallback marks challenge as delivery failed.

### S02 - Authorization Cache Invalidation Consumer

**Purpose:** Keep M03 authorization caches consistent after user, role, permission, tenant, or project changes.

**Input:** `permission.assignment.changed`, `role.updated`, `user.status.changed`, `tenant.updated`, `project.updated`.

**Output:** `authorization.cache.invalidated`.

**Processing logic:**
1. Resolve affected user IDs, role IDs, tenant IDs, and project IDs.
2. Compute affected cache keys.
3. Invalidate user permission digest and scope digest.
4. Emit invalidation completion event with affected counts.
5. If invalidation fails, force short TTL mode for affected key prefix.

**Concurrency:** partition by `user_id` and `tenant_id`; debounce repeated changes within a short window.

**HA:** idempotent invalidation; replayable event stream; degraded mode uses low TTL; DLQ triggers security/ops alert.

### S03 - Raw Recording Import Worker

**Purpose:** Execute M05 batch imports and active-capture imports into immutable raw recording storage.

**Input:** `raw_recording.import.requested`

```json
{
  "import_request_id": "imp_...",
  "manifest_id": "man_...",
  "source_uri_ref": "secret-or-storage-ref",
  "import_mode": "batch",
  "expected_modalities": ["video", "joint_state"]
}
```

**Output:** `raw_recording.imported`, `raw_recording.import_failed`, `raw_recording.partial_import_quarantined`.

**Processing logic:**
1. Load M05 ingest manifest and M04 campaign.
2. Verify tenant/project access and campaign status.
3. Resolve source credentials through secret reference.
4. Enumerate files/streams and compare with manifest.
5. Copy bytes to immutable object storage.
6. Compute checksums and basic file metadata.
7. Register `RawRecording` and `RawRecordingModality`.
8. Emit import result and optionally trigger S04 validation.

**Concurrency:** file-level parallelism with per-import bounded pool; chunked resumable copy; one metadata commit lock per source recording.

**HA:** checkpoint per file/stream; retry storage/network errors; partial imports are quarantined; DLQ masks source refs and includes remediation recommendation.

### S04 - Intake Validation Worker

**Purpose:** Produce M05 validation reports and quality status.

**Input:** `validation.run.requested`

**Output:** `validation.report.created`, `raw_recording.quality_status.changed`, `validation.run.failed`.

**Processing logic:**
1. Load `ValidationRun`, raw recording metadata, manifest, and quality rules.
2. Run rule groups: modality completeness, file readability, duplicate checksum, metadata completeness, timestamp gap, restriction tag presence.
3. Create `QualityFinding` records with severity and affected modality/time range.
4. Derive quality status using rule severity policy.
5. Persist `ValidationReport`.
6. Update `RawRecording.quality_status`.
7. Emit remediation work-request suggestion for missing metadata/corruption/privacy review/recollection.

**Concurrency:** partition by recording ID; rule groups run in parallel; report write transaction serializes per recording.

**HA:** technical read failures retry; business-quality failures do not retry; DLQ after repeated storage/catalog failures.

### S05 - Alignment and Episode Builder Worker

**Purpose:** Create M06 canonical episodes/trajectories from accepted raw recordings.

**Input:** `alignment.run.requested`

**Output:** `episode.created`, `alignment.run.completed`, `alignment.tolerance_violation.detected`, `alignment.run.failed`.

**Processing logic:**
1. Load alignment policy and accepted recordings.
2. Resolve source timing, calibration, coordinate-frame metadata.
3. Align modality streams by policy tolerances.
4. Mark unalignable spans and tolerance violations.
5. Build canonical episode payloads with observations, states, actions, instructions, context, and outcome placeholders.
6. Persist `Episode`, `TrajectoryStep`, and raw-to-derived lineage.
7. Emit catalog indexing event.

**Concurrency:** one active alignment lease per recording/policy version; chunk processing by time windows; large payload streaming.

**HA:** checkpoint per time window; retry transient storage reads; circuit breaker for calibration metadata service; failed run retains reusable context.

### S06 - Segmentation Suggestion Worker

**Purpose:** Generate assisted segment suggestions for M06 without making final human decisions.

**Input:** `segmentation.suggestion.requested`

**Output:** `segmentation.suggestions.created`, `segmentation.suggestion.failed`.

**Processing logic:**
1. Load episode timeline and available modalities.
2. Validate requested segment taxonomy and tag version.
3. Run configured suggestion model or heuristic.
4. Create suggested `Segment` records with source `assisted`, confidence, generator metadata.
5. Notify task owners for human review.

**Concurrency:** GPU/model queue is quota-aware; partition by episode ID; batch small episodes.

**HA:** partial suggestions allowed; model endpoint circuit breaker; unsupported modality/schema failures are terminal with clear finding.

### S07 - Pre-Annotation Generation Worker

**Purpose:** Create M07 machine-generated pre-annotations for annotation tasks.

**Input:** `preannotation.generation.requested`

**Output:** `preannotation.created`, `preannotation.generation_failed`.

**Processing logic:**
1. Load annotation project, label schema, and selected tasks.
2. Validate generator is approved for label type and data sensitivity.
3. Fetch task assets through permission-scoped access.
4. Invoke generator.
5. Normalize output to project label schema.
6. Store `PreAnnotation` with generator identity, confidence, quality signal, review status `pending_review`.
7. Never mark output as human-approved unless explicit low-risk policy allows direct acceptance.

**Concurrency:** partition by annotation project; bounded GPU/inference worker pool; backpressure from generator capacity.

**HA:** retry transient endpoint failures; if generator unavailable, tasks remain manual; DLQ on schema incompatibility.

### S08 - Annotation QA Sampling Worker

**Purpose:** Create QA review tasks and annotation quality metrics for M07.

**Input:** `annotation.submitted`, `qa.sampling.scheduled`, `annotation_set.qa_requested`.

**Output:** `qa.review_tasks.created`, `annotation.quality_metrics.updated`.

**Processing logic:**
1. Load project QA policy and annotation set.
2. Compute deterministic sample using policy version and seed.
3. Select overlap-review items and ambiguous/high-value items.
4. Create QA review tasks.
5. Compute throughput, rework rate, rejection rate, agreement, and unresolved queue metrics.
6. Update annotation project dashboard facts.

**Concurrency:** partition by annotation project; metric aggregation batched.

**HA:** deterministic sampling makes retries safe; database conflicts retry; DLQ alerts QA lead.

### S09 - Catalog Indexing and Lineage Consumer

**Purpose:** Maintain M08 catalog search projections and lineage graph projections.

**Input:** `asset.created`, `asset.updated`, `asset.deprecated`, `dataset.snapshot.published`, `synthetic.batch.created`, `model.candidate.registered`, `evaluation.report.approved`.

**Output:** `catalog.index.updated`, `lineage.projection.updated`, `catalog.index.failed`.

**Processing logic:**
1. Validate asset event and source module ownership.
2. Fetch latest source record.
3. Normalize metadata into `CatalogAsset`.
4. Update scalar search index and facets.
5. Update lineage graph edges.
6. Mark superseded/deprecated assets as non-default in search.

**Concurrency:** partition by asset ID; bulk index updates; debounce noisy metadata events.

**HA:** replay from durable event log; full index rebuild supported; DLQ for invalid event schema or missing source record after retry.

### S10 - Dataset Snapshot Publisher

**Purpose:** Publish M08 immutable dataset snapshots.

**Input:** `dataset.snapshot.publish_requested`

**Output:** `dataset.snapshot.published`, `dataset.snapshot.publish_blocked`, `dataset.snapshot.publish_failed`.

**Processing logic:**
1. Lock draft dataset snapshot.
2. Resolve cohort membership to concrete asset versions.
3. Run M08 policy checks for quality, annotation, restrictions, synthetic validation, retention, and license/privacy tags.
4. Generate immutable membership manifest.
5. Freeze dataset card version.
6. Persist status `published`.
7. Emit catalog and lineage events.

**Concurrency:** one publish lock per dataset logical name/version; streaming membership resolution for large cohorts.

**HA:** two-phase state `publishing -> published`; idempotent retry reuses manifest hash; blocked publish records precise blockers.

### S11 - Vector Embedding and Index Worker

**Purpose:** Build and refresh M09 vector indexes for hybrid scalar-vector retrieval.

**Input:** `analytics.vector_index.rebuild_requested`, `asset.embedding.requested`.

**Output:** `analytics.embedding.created`, `analytics.vector_index.ready`, `analytics.vector_index.degraded`, `analytics.vector_index.failed`.

**Processing logic:**
1. Load `VectorIndex` configuration.
2. Resolve eligible assets from M08 by asset type and scalar filters.
3. Verify user/request scope can read assets at job creation time.
4. Compute or import embeddings using `embedding_model_ref`.
5. Validate vector dimension and distance metric.
6. Store `EmbeddingRecord` and bulk upsert vectors.
7. Update index freshness watermark and status.

**Concurrency:** partition by index ID and asset type; GPU/inference pool controlled by M17 quota; vector-store bulk writes.

**HA:** checkpoint by asset batch; retry model/vector-store transients; dimension mismatch is terminal; partial index marked degraded with missing count.

### S12 - Analytics Distribution Worker

**Purpose:** Compute M09 tag/attribute distributions and structured coverage summaries.

**Input:** `analytics.distribution.requested`.

**Output:** `analytics.distribution.created`, `analytics.coverage_gap.detected`, `analytics.distribution.failed`.

**Processing logic:**
1. Load distribution job and source cohort/dataset/query.
2. Verify source assets are readable.
3. Query warehouse/catalog for requested group-by fields.
4. Compute counts, ratios, missing values, outliers, and real/synthetic splits.
5. Compare coverage against campaign goals or evaluation requirements where supplied.
6. Store `DistributionProfile`.
7. Create candidate `CoverageGapFinding` if underrepresented dimensions are detected.

**Concurrency:** partition by source cohort and grouping fields; columnar scans and aggregate cache.

**HA:** checkpoint aggregate partitions; retry warehouse failures; invalid grouping fields are terminal validation errors.

### S13 - Projection and Clustering Worker

**Purpose:** Run M09 high-dimensional embedding projection and clustering jobs.

**Input:** `analytics.projection.requested`, `analytics.clustering.requested`.

**Output:** `analytics.projection.completed`, `analytics.cluster_run.completed`, `analytics.coverage_gap.detected`, `analytics.projection_or_cluster_failed`.

**Processing logic:**
1. Load source cohort and vector index.
2. Resolve embedding records and verify dimensions.
3. Apply sampling strategy with recorded random seed.
4. For projection, run t-SNE or UMAP and persist coordinates.
5. For clustering, run HDBSCAN or configured clustering algorithm and persist labels/noise points.
6. Compute cluster statistics: size, dominant tags, failure density, synthetic/real mix, missing modalities.
7. Generate coverage-gap candidates for sparse/empty/failure-heavy clusters.

**Concurrency:** heavy jobs are scheduled by tenant quota; one active heavy job per cohort/index unless explicitly allowed; input arrays chunked and memory-guarded.

**HA:** infrastructure failures retry; algorithm parameter errors terminal; reproducibility metadata always stored; DLQ includes sample size and parameter hash.

### S14 - Visualization Materialization Worker

**Purpose:** Materialize M09 analytics visualization views and selected M18 workbench-ready data products.

**Input:** `analytics.visualization_view.requested`, `workbench.timeline.requested`.

**Output:** `analytics.visualization_view.ready`, `workbench.timeline_manifest.ready`, `visualization.materialization.partial`, `visualization.materialization.failed`.

**Processing logic:**
1. Load view/session request.
2. Resolve source assets and modality availability.
3. Generate required data product: trajectory overlay, sensor heatmap tile, temporal sequence, embedding scatter tile, cluster overlay, or timeline manifest.
4. Store materialized data refs with access scope.
5. Mark missing optional modalities as partial, not failed.

**Concurrency:** partition by asset ID and time range; tile/window-level parallelism; cache by asset version and parameters.

**HA:** partial manifests supported; retry decode/storage transient failures; unsupported modality format terminal with UI-readable reason.

### S15 - Simulation Run Dispatcher

**Purpose:** Dispatch and monitor M10 simulation runs.

**Input:** `simulation.run.requested`, `simulation.run.rerun_requested`.

**Output:** `simulation.run.started`, `simulation.run.completed`, `simulation.run.failed`, `simulation.output.created`.

**Processing logic:**
1. Load simulation run record and scenario version.
2. Verify scenario approval/validation according to purpose.
3. Run quota and resource availability check through M17.
4. Allocate logical compute service.
5. Submit simulation job to configured backend.
6. Monitor status and heartbeat.
7. Register outputs and classify failures/artifacts.
8. Emit synthetic/evaluation/catalog events depending output classification.

**Concurrency:** tenant/project queues by priority and service class; backpressure from compute availability.

**HA:** submission failures retry before remote job starts; running job failures become business failure records; stale heartbeat triggers recovery or failed status.

### S16 - Synthetic Generation Worker

**Purpose:** Execute M11 governed synthetic generation and augmentation requests.

**Input:** `synthetic.generation.requested`.

**Output:** `synthetic.batch.created`, `synthetic.generation_failed`.

**Processing logic:**
1. Load generation request and validate approved scenario/source dataset.
2. Verify target coverage gap or evaluation objective.
3. Resolve generator configuration and resource quota.
4. Execute generation in shards.
5. Mark all outputs synthetic.
6. Register generated labels/ground truth if present.
7. Persist `SyntheticDataBatch`, generation settings hash, source links, and initial validation status.

**Concurrency:** generator-specific worker pools; GPU/resource-aware scheduling; output-volume guardrails.

**HA:** checkpoint per generated shard; retry transient generator/storage failures; invalid generator config terminal; DLQ includes generator ref and settings hash only.

### S17 - Synthetic Validation Worker

**Purpose:** Validate M11 synthetic batches and route approval decisions.

**Input:** `synthetic.validation.requested`, `synthetic.batch.created`.

**Output:** `synthetic.validation_report.created`, `synthetic.validation_blocked`, `synthetic.validation_failed`.

**Processing logic:**
1. Load batch, validation policy, intended use.
2. Run modality completeness and label availability checks.
3. Evaluate known limitations and generator failure modes.
4. Compare output suitability to intended use: training/evaluation/exploration.
5. Write validation report.
6. If policy requires human review, create approval task.

**Concurrency:** batch shards validated in parallel; final report transaction serializes per batch/policy.

**HA:** validator infrastructure failures retry; unsuitable data is a terminal business result, not an infrastructure failure.

### S18 - Training Run Dispatcher

**Purpose:** Launch and monitor M12 training runs.

**Input:** `training.launch.requested`.

**Output:** `training.run.started`, `training.metric.logged`, `training.artifact.created`, `training.run.completed`, `training.run.failed`.

**Processing logic:**
1. Load training plan and requested workflow template.
2. Verify approvals, immutable dataset snapshots, M08 usage policies, synthetic validation, and M17 quota.
3. Allocate compute/logical service.
4. Submit training job.
5. Stream status, metrics, and artifacts.
6. Persist terminal run state and reusable context on failure/cancel.
7. Notify S19 for model registration readiness when model artifact exists.

**Concurrency:** priority queue by service class; per-run metric batching; resource leases prevent over-allocation.

**HA:** retry submission before remote job starts; heartbeat monitor for stale jobs; checkpoint run context; DLQ for orchestration integration failure.

### S19 - Model Registration and Lineage Consumer

**Purpose:** Create or update M13 model candidate registration readiness after training artifacts are produced.

**Input:** `training.run.completed`, `training.artifact.created`.

**Output:** `model.candidate.registration_ready`, `model.lineage.updated`, `model.registration_blocked`.

**Processing logic:**
1. Load training run, dataset bindings, code/build refs, and artifact list.
2. Verify required model artifact and metadata are present.
3. Create draft model candidate if auto-registration policy allows; otherwise create readiness record.
4. Attach lineage edges from datasets -> training run -> artifacts -> model candidate.
5. Notify model owner for model card completion.

**Concurrency:** partition by training run ID; idempotent artifact association by checksum.

**HA:** retry registry conflicts; missing required artifact after timeout becomes blocked status with owner notification.

### S20 - Evaluation Run Dispatcher

**Purpose:** Execute M14 offline and simulation-based evaluation runs.

**Input:** `evaluation.run.requested`.

**Output:** `evaluation.run.started`, `evaluation.metric.logged`, `evaluation.failure.detected`, `evaluation.report.drafted`, `evaluation.run.failed`.

**Processing logic:**
1. Load evaluation suite, model candidates, baselines, datasets, scenarios, metrics.
2. Validate candidate readiness, dataset policy, scenario approval, and quota.
3. Fan out evaluation tasks by suite component.
4. Collect metrics and failure events.
5. Create draft evaluation report.
6. Request M18 visualization materialization for selected failures.

**Concurrency:** fan-out by dataset/scenario shard; release-critical evaluation lock per model/suite version; metric writes batched.

**HA:** retry technical task failures; preserve partial metrics; suite/candidate mismatch terminal.

### S21 - Failure Clustering and Remediation Worker

**Purpose:** Group M14 failures and draft closed-loop remediation actions.

**Input:** `failure.record.created`, `failure.clustering.scheduled`.

**Output:** `failure.cluster.updated`, `remediation.work_request_draft.created`, `failure.clustering_failed`.

**Processing logic:**
1. Load new and open failures for project/model/suite.
2. Group by task, object, environment, action phase, robot state, scenario, model output, and embedding cluster when available from M09.
3. Update failure clusters and severity summaries.
4. Recommend action: data mining, collection, annotation correction, simulation expansion, evaluation update, retraining.
5. Draft M16 remediation work requests for owner review.

**Concurrency:** partition by project and model/suite; incremental updates for new failures.

**HA:** deterministic clustering window; metadata read failures retry; schema drift terminal to DLQ.

### S22 - Release Evidence Check Worker

**Purpose:** Verify M15 release-candidate evidence completeness.

**Input:** `release.evidence_check.requested`.

**Output:** `release.evidence_check.completed`, `release.evidence_check.blocked`, `release.evidence_check_failed`.

**Processing logic:**
1. Load release candidate.
2. Verify model candidate lifecycle status and model card completeness.
3. Verify dataset lineage and immutable dataset snapshots.
4. Verify approved evaluation reports and acceptance thresholds.
5. Verify artifact package, target deployment class, compatibility notes, known limitations, rollback ref if required.
6. Detect unresolved blockers/failures.
7. Write `ReleaseEvidenceChecklist`.

**Concurrency:** partition by release candidate ID; parallel registry reads.

**HA:** registry timeout retry; stale or missing evidence yields blocked result; repeated registry failure DLQ.

### S23 - Workflow Orchestrator

**Purpose:** Execute M16 workflow runs and task graphs.

**Input:** `workflow.run.requested`, `workflow.run.pause_requested`, `workflow.run.cancel_requested`, `workflow.run.rerun_requested`.

**Output:** `workflow.run.started`, `workflow.task.started`, `workflow.task.completed`, `workflow.task.failed`, `workflow.run.completed`, `workflow.run.failed`, `workflow.run.canceled`.

**Processing logic:**
1. Load template version and work request.
2. Validate approvals, input schema, output schema, dataset policies, and quota.
3. Expand DAG and create task runs.
4. Schedule ready tasks based on dependencies.
5. Dispatch domain-specific events to owning workers.
6. Track task completions, retries, pauses, cancellations.
7. Register outputs through owning modules.
8. Persist workflow terminal state.

**Concurrency:** leader-elected scheduler; tenant/project queues; task leases; backpressure from M17 quota and downstream service health.

**HA:** task leases expire and can be reclaimed; scheduler failover via leader election; cancellation is cooperative; invalid template expansion DLQ.

### S24 - Quota and Utilization Aggregator

**Purpose:** Maintain M17 utilization, quota, and cost attribution.

**Input:** `resource.utilization.sampled`, `workflow.task.started`, `workflow.task.completed`, `quota.policy.updated`.

**Output:** `utilization.summary.updated`, `quota.warning.triggered`, `quota.breach.triggered`.

**Processing logic:**
1. Consume resource samples and workflow/job events.
2. Normalize usage to resource class and workload class.
3. Attribute usage to tenant, project, campaign, model, workflow, and cost center.
4. Evaluate soft/hard quotas.
5. Emit warning/breach/escalation events.
6. Update dashboard aggregates.

**Concurrency:** stream processing partitioned by tenant/resource/time window.

**HA:** replayable event stream; local buffering at collectors; malformed samples DLQ.

### S25 - Resource Health Monitor

**Purpose:** Monitor M17 physical and logical compute/storage health.

**Input:** `resource.health.poll_tick`, provider health events.

**Output:** `resource.health.changed`, `tenant.resource_binding.degraded`, `resource.health_monitor_failed`.

**Processing logic:**
1. Load active resources and health endpoint refs.
2. Poll or consume provider health signals.
3. Update resource health status.
4. Detect degraded tenant bindings.
5. Notify M16 scheduler to avoid unhealthy resources.
6. Emit operator alerts.

**Concurrency:** bounded poller pools by provider/resource type; staggered schedules.

**HA:** redundant monitors with leader election per resource group; provider circuit breaker; failed status writes retry.

### S26 - Workbench Timeline Materializer

**Purpose:** Build M18 synchronized timelines, manifests, and frame windows.

**Input:** `workbench.timeline.requested`.

**Output:** `workbench.timeline_manifest.ready`, `workbench.timeline_manifest.partial`, `workbench.timeline_manifest.failed`.

**Processing logic:**
1. Load workbench session and source asset metadata.
2. Resolve modalities, timestamps, coordinate-frame refs, annotations, predictions, evaluation context.
3. Align timeline to available source timing and policy assumptions.
4. Generate modality availability map.
5. Create frame windows and data refs.
6. Persist `TimelineManifest`.
7. Mark optional missing modalities as partial.

**Concurrency:** partition by asset/session; cache by asset version and context version.

**HA:** partial manifests allowed; retry decode/storage failures; unsupported schema terminal with UI-visible error.

### S27 - Audit Event Collector

**Purpose:** Collect, validate, store, and index M19 audit events.

**Input:** `audit.event.recorded`.

**Output:** `audit.event.indexed`, `audit.event.rejected`.

**Processing logic:**
1. Validate required audit fields.
2. Enrich with tenant/project/user context when allowed.
3. Write immutable audit log.
4. Update audit search index.
5. Flag malformed/missing fields.

**Concurrency:** append-only partition by tenant/time; bulk indexer.

**HA:** immutable log write precedes search index update; search index can replay from log; malformed sensitive events trigger alert and DLQ.

### S28 - Dashboard and Report Aggregator

**Purpose:** Build M19 dashboard snapshots and scheduled/exported reports.

**Input:** `dashboard.snapshot.scheduled`, `report.run.requested`, `audit.export.requested`.

**Output:** `dashboard.snapshot.updated`, `report.run.completed`, `report.run.failed`.

**Processing logic:**
1. Load report definition and requester permissions.
2. Query module read models, warehouse facts, audit index, and utilization aggregates.
3. Apply filters and restricted-data masking.
4. Generate dashboard snapshot or report artifact.
5. Store output ref and freshness metadata.
6. Notify requester.

**Concurrency:** partition by tenant/report type; cache common aggregates; enforce export size limits.

**HA:** retry warehouse/query failures; partial dashboards show stale markers; invalid report definition DLQ.

### Service Traceability Matrix

| Service | Primary modules served | Key produced records |
|---|---|---|
| S01 | M01 | Email delivery status, login audit |
| S02 | M02, M03 | Authorization cache invalidation |
| S03 | M05 | RawRecording, RawRecordingModality |
| S04 | M05 | ValidationReport, QualityFinding |
| S05 | M06 | Episode, TrajectoryStep, lineage |
| S06 | M06 | Suggested Segment |
| S07 | M07 | PreAnnotation |
| S08 | M07 | QAReview, quality metrics |
| S09 | M08 | CatalogAsset projection, lineage projection |
| S10 | M08 | Published DatasetSnapshot |
| S11 | M09 | VectorIndex, EmbeddingRecord |
| S12 | M09 | DistributionProfile, CoverageGapFinding |
| S13 | M09 | ProjectionRun, ClusterRun, CoverageGapFinding |
| S14 | M09, M18 | VisualizationView data, TimelineManifest |
| S15 | M10 | SimulationRun status, SimulationOutput |
| S16 | M11 | SyntheticDataBatch |
| S17 | M11 | SyntheticValidationReport |
| S18 | M12 | TrainingRun status, metrics, artifacts |
| S19 | M13 | Model lineage, registration readiness |
| S20 | M14 | EvaluationReport draft, FailureRecord |
| S21 | M14, M16 | FailureCluster, remediation work-request draft |
| S22 | M15 | ReleaseEvidenceChecklist |
| S23 | M16 | WorkflowRun, WorkflowTaskRun |
| S24 | M17, M19 | UtilizationSample, CostAttributionRecord |
| S25 | M17 | Resource health state |
| S26 | M18 | TimelineManifest, FrameWindow |
| S27 | M19 | AuditEvent |
| S28 | M19 | DashboardSnapshot, ReportRun |

### HTTP-to-Service Trigger Matrix

This matrix closes the causal contract between module HTTP interfaces and backend services. Interfaces not listed here are synchronous CRUD/read operations, or they emit ordinary audit/catalog events handled by S09/S27.

| HTTP interface or domain event source | Emitted event | Consuming service | Expected business result |
|---|---|---|---|
| `POST /api/v1/auth/email-code-requests` | `auth.email_code.requested` | S01 | Email delivery status and active login challenge. |
| M02 tenant/project/resource-binding mutation | `tenant.updated`, `project.updated` | S02 | Authorization scope cache invalidated. |
| M03 user/role/assignment mutation | `user.status.changed`, `role.updated`, `permission.assignment.changed` | S02 | Authorization cache invalidated. |
| `POST /api/v1/raw-recordings/import-requests` | `raw_recording.import.requested` | S03 | Immutable `RawRecording` and modality records. |
| `POST /api/v1/validation-runs` | `validation.run.requested` | S04 | `ValidationReport`, `QualityFinding`, quality status. |
| `POST /api/v1/alignment-runs` | `alignment.run.requested` | S05 | Canonical `Episode`, `TrajectoryStep`, lineage. |
| `POST /api/v1/episodes/{episode_id}/segmentation-suggestion-requests` | `segmentation.suggestion.requested` | S06 | Suggested `Segment` records with generator provenance. |
| `POST /api/v1/preannotations/generation-requests` | `preannotation.generation.requested` | S07 | `PreAnnotation` records awaiting human review. |
| `POST /api/v1/annotation-sets/{set_id}/qa-reviews` and annotation submissions | `annotation_set.qa_requested`, `annotation.submitted` | S08 | `QAReview` tasks and annotation quality metrics. |
| Asset lifecycle changes from M05-M15 | `asset.created`, `asset.updated`, `asset.deprecated` | S09 | `CatalogAsset` search projection and lineage projection. |
| `POST /api/v1/dataset-snapshots/{snapshot_id}/publish` | `dataset.snapshot.publish_requested` | S10 | Published immutable `DatasetSnapshot`. |
| `POST /api/v1/analytics/vector-indexes/{index_id}/rebuild` | `analytics.vector_index.rebuild_requested` | S11 | Fresh or degraded `VectorIndex` with `EmbeddingRecord`s. |
| `POST /api/v1/analytics/distribution-jobs` | `analytics.distribution.requested` | S12 | `DistributionProfile` and optional `CoverageGapFinding`. |
| `POST /api/v1/analytics/projection-jobs` | `analytics.projection.requested` | S13 | `ProjectionRun` with persisted coordinates. |
| `POST /api/v1/analytics/clustering-jobs` | `analytics.clustering.requested` | S13 | `ClusterRun` with labels/noise summary and optional gaps. |
| `POST /api/v1/analytics/visualization-views` | `analytics.visualization_view.requested` | S14 | Materialized visualization data. |
| `POST /api/v1/workbench/sessions` and timeline request | `workbench.timeline.requested` | S14/S26 | Timeline manifest or visualization-ready material. |
| `POST /api/v1/simulation-runs` | `simulation.run.requested` | S15 | `SimulationRun` status and outputs. |
| `POST /api/v1/simulation-runs/{run_id}/rerun` | `simulation.run.rerun_requested` | S15 | New linked simulation run. |
| `POST /api/v1/synthetic-generation-requests` | `synthetic.generation.requested` | S16 | `SyntheticDataBatch` with provenance. |
| `POST /api/v1/synthetic-batches/{batch_id}/validation-runs` | `synthetic.validation.requested` | S17 | `SyntheticValidationReport` or validation blocker. |
| `POST /api/v1/training-plans/{plan_id}/launch` | `training.launch.requested` | S18 | `TrainingRun`, metrics, artifacts, terminal status. |
| Training run/artifact completion | `training.run.completed`, `training.artifact.created` | S19 | Model registration readiness and lineage. |
| `POST /api/v1/evaluation-runs` | `evaluation.run.requested` | S20 | Draft `EvaluationReport`, metrics, failures. |
| `POST /api/v1/failure-records` and scheduled clustering | `failure.record.created`, `failure.clustering.scheduled` | S21 | Failure clusters and remediation drafts. |
| `POST /api/v1/release-candidates/{release_id}/evidence-check` | `release.evidence_check.requested` | S22 | `ReleaseEvidenceChecklist`. |
| `POST /api/v1/workflow-runs` | `workflow.run.requested` | S23 | `WorkflowRun` and `WorkflowTaskRun` execution. |
| Workflow pause/cancel/rerun interfaces | `workflow.run.pause_requested`, `workflow.run.cancel_requested`, `workflow.run.rerun_requested` | S23 | Cooperative state transition or cloned run. |
| Resource/job utilization events | `resource.utilization.sampled`, `workflow.task.started`, `workflow.task.completed` | S24 | Utilization, quota, and cost attribution aggregates. |
| Resource health schedule/provider events | `resource.health.poll_tick` and provider health events | S25 | Resource health status and degraded binding alerts. |
| M18 timeline requests | `workbench.timeline.requested` | S26 | `TimelineManifest` and `FrameWindow`. |
| Critical actions from all modules | `audit.event.recorded` | S27 | Immutable `AuditEvent` and searchable audit index. |
| Dashboard/report/export requests | `dashboard.snapshot.scheduled`, `report.run.requested`, `audit.export.requested` | S28 | `DashboardSnapshot`, `ReportRun`, export artifact. |

## 4. Validation Report


### 0. Validation Boundary

Agent E validation was performed only against the generated FDD artifacts:

- Domain Concept & Requirements Knowledge Base
- Executive Summary & Module Map
- Module Designs
- Backend Service Designs

The original FRD was not reread during Agent E validation. The validation target was the generated FDD content only, as required by the FRD-to-FDD transformation protocol.

### 1. Validation Method

Agent E checked the generated FDD for:

1. Completeness: every module has functional design, interface design, data design, permission design, and logging design; every backend service has purpose, input/output service interface, business processing logic, concurrency, and HA/failure recovery.
2. Interface-to-data consistency: interface request/response fields map to module data models or cross-module source records.
3. Interface-to-service continuity: async HTTP operations emit events consumed by backend services.
4. Data model lifecycle coverage: major records have create/read/update/execute/publish/deprecate or service-owned lifecycle paths.
5. Permission alignment: UI/API mutation capabilities have authorization ownership and role boundaries.
6. Logging/audit coverage: critical data, annotation, model, evaluation, release, access, workflow, and resource actions are auditable.
7. Naming consistency: business terms and identifiers are consistently used across modules.

### 2. Mechanical Coverage Check

| Check | Result |
|---|---:|
| Modules present | 19 |
| Backend services present | 28 |
| HTTP interfaces defined | 132 |
| Modules with Functional Design section | 19 / 19 |
| Modules with Interface Design section | 19 / 19 |
| Modules with Data Design section | 19 / 19 |
| Modules with Permission Design section | 19 / 19 |
| Modules with Logging Design section | 19 / 19 |
| HTTP-to-service trigger matrix present | Yes |

### 3. Initial Validation Findings and Fixes

| ID | Severity | Finding | Impact | Fix applied | Status |
|---|---|---|---|---|---|
| VE-001 | Critical | M18 claimed support for failure tags, but the module design did not define a failure-tag interface or data model. | Workbench could not fulfill its stated review/failure-triage function. | Added `POST /api/v1/workbench/failure-tags` and `WorkbenchFailureTag`; linked severe tags to M14 `FailureRecord` drafts. | Fixed |
| VE-002 | Critical | S06 Segmentation Suggestion Worker existed, but no module interface triggered `segmentation.suggestion.requested`. | Assisted segmentation was orphaned from the HTTP/API layer. | Added `POST /api/v1/episodes/{episode_id}/segmentation-suggestion-requests`; mapped it to S06 in backend services. | Fixed |
| VE-003 | Critical | S17 Synthetic Validation Worker existed, but the module design only allowed manual validation-report creation and lacked an async validation-run trigger. | Synthetic validation service was not causally reachable from the module API. | Added `POST /api/v1/synthetic-batches/{batch_id}/validation-runs`; mapped it to S17. | Fixed |
| VE-004 | Major | Backend services were individually defined, but the FDD lacked a full HTTP-to-service trigger matrix. | Async causality was implicit and harder to verify. | Added `HTTP-to-Service Trigger Matrix` covering key async interfaces/events from M01-M19 to S01-S28. | Fixed |
| VE-005 | Major | M09 `CoverageGapFinding` stated it could feed M10 scenario requests, but only work-request draft conversion was defined. | Analytics-to-simulation closed-loop path was under-specified. | Added `POST /api/v1/analytics/coverage-gap-findings/{finding_id}/scenario-drafts`. | Fixed |
| VE-006 | Major | M13 used `model_id` in several places while surrounding modules used `model_candidate_id`. | Naming inconsistency could break evaluation/release contracts. | Replaced M13 path/body/model fields with `model_candidate_id`; also aligned failure, cost attribution, evaluation, and dashboard fields. | Fixed |

### 4. Re-Validation Results

#### 4.1 Completeness

Pass. Every module M01-M19 contains the required module-design subsections:

- Functional Design
- Interface Design
- Data Design
- Permission Design
- Logging Design

Every backend service S01-S28 includes:

- Purpose
- Input event or queue topic
- Output event or destination
- Business processing logic
- Concurrency model
- High availability / failure recovery handling

#### 4.2 Orphan Interface and Orphan Service Check

Pass. No critical orphan service remains.

Key repaired async chains:

| Chain | Verified path |
|---|---|
| Login email code | M01 `email-code-requests` -> `auth.email_code.requested` -> S01 |
| Raw import | M05 `raw-recordings/import-requests` -> `raw_recording.import.requested` -> S03 |
| Validation | M05 `validation-runs` -> `validation.run.requested` -> S04 |
| Alignment | M06 `alignment-runs` -> `alignment.run.requested` -> S05 |
| Assisted segmentation | M06 `segmentation-suggestion-requests` -> `segmentation.suggestion.requested` -> S06 |
| Pre-annotation | M07 `preannotations/generation-requests` -> `preannotation.generation.requested` -> S07 |
| Dataset publication | M08 `dataset-snapshots/{id}/publish` -> `dataset.snapshot.publish_requested` -> S10 |
| Vector indexing | M09 `vector-indexes/{id}/rebuild` -> `analytics.vector_index.rebuild_requested` -> S11 |
| Distribution mining | M09 `distribution-jobs` -> `analytics.distribution.requested` -> S12 |
| Projection/clustering | M09 projection/clustering jobs -> S13 |
| Simulation | M10 `simulation-runs` -> `simulation.run.requested` -> S15 |
| Synthetic generation | M11 `synthetic-generation-requests` -> `synthetic.generation.requested` -> S16 |
| Synthetic validation | M11 `synthetic-batches/{id}/validation-runs` -> `synthetic.validation.requested` -> S17 |
| Training | M12 `training-plans/{id}/launch` -> `training.launch.requested` -> S18 |
| Evaluation | M14 `evaluation-runs` -> `evaluation.run.requested` -> S20 |
| Release evidence | M15 `release-candidates/{id}/evidence-check` -> `release.evidence_check.requested` -> S22 |
| Workflow orchestration | M16 workflow run lifecycle APIs -> S23 |
| Workbench timeline | M18 workbench session/timeline request -> S26 |
| Audit | Critical actions -> `audit.event.recorded` -> S27 |
| Reporting/export | M19 dashboard/report/export requests -> S28 |

#### 4.3 Data Model and CRUD/Lifecycle Coverage

Pass. Core data models have lifecycle paths:

| Data model group | Lifecycle coverage |
|---|---|
| Identity/session | M01/M03 create, update, revoke, evaluate |
| Tenant/project/resource binding | M02 create/update/archive/bind, M17 resource registration |
| Campaign/raw recording/validation | M04 campaign CRUD/status, M05 import/validation/quarantine |
| Episode/segment/tags | M06 alignment, episode read, segment create/update, suggestion requests |
| Annotation/pre-annotation/QA | M07 project/task/preannotation/annotation/QA/approval |
| Catalog/cohort/dataset | M08 search/cohort/create/publish/deprecate/policy-check |
| Analytics/mining | M09 search/index/rebuild/views/distributions/projections/clusters/findings |
| Scenario/simulation | M10 scenario/version/collection/run/rerun/output classification |
| Synthetic data | M11 request/batch/validation/approval/deprecation |
| Training/model/evaluation/release | M12-M15 plan/run/artifact/model card/evaluation report/failure/release decision |
| Workflow/compute/reporting | M16-M19 template/request/run/quota/resource/health/audit/report |

#### 4.4 Logical Consistency

Pass after fixes.

Important consistency checks:

- M01 authenticates only; M03 authorizes.
- M02 owns tenant/project/resource boundaries; M03 owns permission decisions.
- M08 owns catalog and dataset governance; M09 owns analytics/mining outputs.
- M09 computes visualization datasets; M18 renders synchronized review sessions.
- M16 orchestrates workflows; owning business modules register final business records.
- M17 manages capacity and quotas only; it does not mutate business assets.
- M15 explicitly governs release artifacts and does not perform OTA execution.

#### 4.5 Causal Continuity

Pass. The generated FDD now provides direct handoff paths for all major end-to-end loops:

1. Campaign -> Raw Recording -> Validation -> Alignment -> Episode -> Annotation -> Dataset Snapshot.
2. Coverage Gap -> Scenario Draft -> Simulation Run -> Synthetic Batch -> Synthetic Validation -> Dataset Snapshot.
3. Dataset Snapshot -> Training Plan -> Training Run -> Model Candidate -> Evaluation Report.
4. Evaluation Failure -> Failure Record -> Failure Cluster -> Remediation Work Request.
5. Model Candidate + Evidence -> Release Candidate -> Evidence Check -> Approval Decision.
6. Workbench Review -> Comment/Failure Tag/Review Decision -> Owning module record or M14 failure record.
7. Workflow Run -> Task Execution -> Output Registration -> Owning module asset.

#### 4.6 Permission Alignment

Pass. Permission design follows the required built-in role boundaries:

- Platform Administrator: unrestricted by default.
- Tenant Administrator: unrestricted within assigned tenant by default.
- Operations Engineer: compute/storage/workflow operations by default, business-resource mutation blocked unless delegated.
- R&D Engineer: project-scoped business work and tenant-bound compute/storage usage.

Every module has a role-permission matrix. Sensitive actions such as dataset publication, synthetic approval, training launch, evaluation approval, release decision, quota override, restricted audit export, and role assignment are explicitly gated.

#### 4.7 Logging and Audit Alignment

Pass. All modules define log levels and audit-worthy actions. S27 provides centralized immutable audit collection. Sensitive-data masking rules are globally specified and reinforced in services handling credentials, sessions, raw source references, synthetic generation, artifact packages, and audit exports.

#### 4.8 Naming Consistency

Pass after fixes.

The model lifecycle now consistently uses:

- `ModelCandidate`
- `model_candidate_id`
- `baseline_model_candidate_id`
- `model_candidate_ids`

No residual `model_id`, `affected_model_id`, `baseline_model_id`, or `model_ids` remains in the module and backend service designs.

### 5. Final Agent E Result

| Category | Result |
|---|---|
| Critical issues remaining | 0 |
| Major issues remaining | 0 |
| Minor issues remaining | 0 |
| Advisory notes | 1 |

Advisory: Module interfaces use compact JSON-object schema notation inside the interface tables rather than full OpenAPI YAML. The interface contracts are logically complete and implementation-ready; this is an FDD-level representation, not a validation blocker.

### 6. Final Validation Status

**PASS - zero unresolved critical, major, or minor validation findings.**
