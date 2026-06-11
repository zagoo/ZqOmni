"""M03 wire schemas (FDD §2.3.3)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=254)
    display_name: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.strip().lower()


class UserPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class DeactivateRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


class UserOut(BaseModel):
    user_id: str
    email: str
    display_name: str
    status: str
    deactivate_reason: str | None
    last_login_at: datetime | None
    note: str | None
    version: int
    created_at: datetime
    created_by: str | None
    bindings_count: int | None = None


# --- Permission catalog ---


class PermissionOut(BaseModel):
    key: str
    domain: str
    resource: str
    action: str
    description: str
    owning_module: str
    scope_levels: list[str]
    service_only: bool


# --- Roles ---


class RoleScope(BaseModel):
    type: Literal["platform", "tenant"]
    id: str | None = None


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] = Field(min_length=1)


class RolePatch(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] | None = Field(default=None, min_length=1)


class RoleOut(BaseModel):
    role_id: str
    name: str
    role_type: str
    scope: RoleScope
    description: str | None
    permission_keys: list[str]
    version: int
    created_at: datetime | None
    created_by: str | None
    bindings_count: int | None = None


# --- Role bindings ---


class BindingScope(BaseModel):
    type: Literal["platform", "tenant", "project"]
    id: str | None = None


class RoleBindingCreate(BaseModel):
    user_id: str
    role_id: str
    scope: BindingScope


class RoleBindingOut(BaseModel):
    binding_id: str
    user_id: str
    user_display_name: str | None = None
    role_id: str
    role_name: str | None = None
    scope: BindingScope
    origin: str
    created_at: datetime
    created_by: str | None


# --- Effective permissions (M03-7) ---


class EffectiveVia(BaseModel):
    binding_id: str | None
    role: str
    scope: str


class EffectivePermission(BaseModel):
    key: str
    via: list[EffectiveVia]


class EffectivePermissionsResponse(BaseModel):
    user_id: str
    scope: BindingScope
    allowed: list[EffectivePermission]
    denied_reasons: list[str]
    user_status: str
    scope_status: str
    resolved_at: datetime


# --- Audit (M03-8) ---


class AuditActor(BaseModel):
    type: str
    id: str


class AuditSubject(BaseModel):
    type: str
    id: str


class AuditScopeOut(BaseModel):
    tenant_id: str | None
    project_id: str | None


class AuditEventOut(BaseModel):
    event_id: str
    occurred_at: datetime
    action: str
    actor: AuditActor
    subject: AuditSubject
    scope: AuditScopeOut
    decision: str
    reason: str | None
    before_summary: dict[str, Any] | None
    after_summary: dict[str, Any] | None
    source_module: str
    trace_id: str | None


# --- Access reviews (M03-9) ---


class AccessReviewCreate(BaseModel):
    review_type: Literal["restricted_datasets", "release_artifacts", "combined"]
    period_start: datetime | None = None
    period_end: datetime | None = None


class AccessReviewSummary(BaseModel):
    users_with_restricted_access: int
    dormant_grants: int
    anomalies: int


class AccessReviewEntryOut(BaseModel):
    user_id: str
    display_name: str
    grant: dict[str, Any]
    asset_class: str
    last_access_at: datetime | None
    anomalies: list[str]


class AccessReviewOut(BaseModel):
    review_id: str
    tenant_id: str
    review_type: str
    status: str
    period_start: datetime
    period_end: datetime
    requested_by: str
    created_at: datetime
    completed_at: datetime | None
    failure_reason: str | None
    summary: AccessReviewSummary | None = None


# --- Internal plane (M03-10 / M03-11) ---


class AuthzScope(BaseModel):
    type: Literal["platform", "tenant", "project"]
    id: str | None = None


class AuthzCheckRequest(BaseModel):
    user_id: str
    permission_key: str
    scope: AuthzScope
    resource_ref: str | None = None
    context: dict[str, Any] | None = None


class AuthzBatchCheckRequest(BaseModel):
    checks: list[AuthzCheckRequest] = Field(max_length=100)


class AuthzMatched(BaseModel):
    binding_id: str | None
    role_id: str
    via_scope: str


class AuthzCheckResponse(BaseModel):
    decision: Literal["allow", "deny"]
    reason: str
    matched: AuthzMatched | None = None
    ttl_s: int
    evaluated_at: datetime


class AuthzBatchCheckResponse(BaseModel):
    results: list[AuthzCheckResponse]


class AuditIngestEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    action: str
    actor: AuditActor
    subject: AuditSubject
    scope: AuditScopeOut
    decision: Literal["allow", "deny", "n/a"] = "n/a"
    reason: str | None = None
    before_summary: dict[str, Any] | None = None
    after_summary: dict[str, Any] | None = None
    source_module: str
    trace_id: str | None = None


class AuditIngestRequest(BaseModel):
    events: list[AuditIngestEvent] = Field(max_length=500)


class AuditIngestRejection(BaseModel):
    index: int
    code: str
    message: str


class AuditIngestResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: list[AuditIngestRejection]
