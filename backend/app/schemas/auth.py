"""M01 wire schemas (FDD §2.1.3)."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginCodeRequest(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.strip().lower()


class LoginCodeAccepted(BaseModel):
    status: str = "accepted"
    message: str = "If the email is registered, a login code has been sent."
    resend_available_in_s: int = 60


class ClientInfo(BaseModel):
    user_agent: str | None = Field(default=None, max_length=256)
    device_label: str | None = Field(default=None, max_length=256)


class SessionCreateRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    code: str = Field(pattern=r"^[0-9]{8}$")
    client: ClientInfo | None = None

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.strip().lower()


class SessionUser(BaseModel):
    user_id: str
    display_name: str
    email: str
    status: str


class SessionCreated(BaseModel):
    session_token: str
    access_token: str
    access_expires_at: datetime
    session_id: str
    idle_expires_at: datetime
    absolute_expires_at: datetime
    user: SessionUser
    active_tenant_id: str | None
    tenant_selection_required: bool


class SessionRefreshRequest(BaseModel):
    # Optional body fallback; the httpOnly cookie is the primary carrier.
    session_token: str | None = None


class SessionRefreshed(BaseModel):
    access_token: str
    access_expires_at: datetime
    session_id: str
    idle_expires_at: datetime
    absolute_expires_at: datetime


class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime


class ProjectMembershipInfo(BaseModel):
    project_id: str
    name: str
    persona_templates: list[str]


class TenantMembershipInfo(BaseModel):
    tenant_id: str
    name: str
    status: str
    roles: list[str]
    projects: list[ProjectMembershipInfo]


class PermissionSummaryScope(BaseModel):
    type: str
    id: str | None


class PermissionSummary(BaseModel):
    scope: PermissionSummaryScope
    allowed_keys: list[str]


class CurrentSessionResponse(BaseModel):
    session: SessionInfo
    user: SessionUser
    active_tenant_id: str | None
    tenants: list[TenantMembershipInfo]
    permission_summary: PermissionSummary | None


class SwitchTenantRequest(BaseModel):
    tenant_id: str


class SwitchTenantResponse(BaseModel):
    active_tenant_id: str


class RevokeAllResponse(BaseModel):
    revoked_count: int


class IntrospectRequest(BaseModel):
    session_token: str


class IntrospectResponse(BaseModel):
    active: bool
    reason: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    active_tenant_id: str | None = None
    user_status: str | None = None
    idle_expires_at: datetime | None = None
    absolute_expires_at: datetime | None = None
