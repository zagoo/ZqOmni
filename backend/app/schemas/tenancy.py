"""M02 wire schemas (FDD §2.2.3)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{2,38}$"


class TenantSettings(BaseModel):
    storage_isolation: Literal["prefix_per_tenant", "dedicated_bucket"] = "prefix_per_tenant"


class TenantCreate(BaseModel):
    name: str = Field(pattern=SLUG_PATTERN)
    display_name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    settings: TenantSettings = Field(default_factory=TenantSettings)

    @field_validator("display_name", "description")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class TenantPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    settings: TenantSettings | None = None
    # Accepted ONLY for the guarded suspended->archived transition (M02-2).
    status: Literal["archived"] | None = None


class SuspendRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


class TenantOut(BaseModel):
    tenant_id: str
    name: str
    display_name: str
    description: str | None
    status: str
    suspend_reason: str | None
    settings: dict[str, Any]
    namespace_ref: str
    version: int
    created_at: datetime
    created_by: str | None
    suspended_at: datetime | None
    archived_at: datetime | None
    projects_count: int | None = None
    bindings_count: int | None = None


class TenantPublicOut(BaseModel):
    """Sanitized self-view (M02-7): no namespace/internal descriptors."""

    tenant_id: str
    name: str
    display_name: str
    description: str | None
    status: str
    settings: dict[str, Any]
    version: int
    created_at: datetime


# --- Resources ---

ResourceClass = Literal["compute", "storage"]
ResourceForm = Literal["physical", "logical"]


class ComputePhysicalDescriptor(BaseModel):
    hostname: str = Field(max_length=253)
    gpu_model: str = Field(max_length=64)
    gpu_count: int = Field(ge=1, le=16)
    cpu_cores: int = Field(ge=1)
    memory_gib: int = Field(ge=1)
    node_labels: dict[str, str] = Field(default_factory=dict)


class LogicalCapacity(BaseModel):
    gpu_count: int = Field(default=0, ge=0)
    cpu_cores: int = Field(default=0, ge=0)
    memory_gib: int = Field(default=0, ge=0)
    max_workers: int = Field(default=0, ge=0)


class ComputeLogicalDescriptor(BaseModel):
    service_type: Literal["ray_cluster", "other_registered"] = "ray_cluster"
    endpoint_url: str = Field(max_length=512)
    version: str | None = Field(default=None, max_length=32)
    capacity: LogicalCapacity = Field(default_factory=LogicalCapacity)


class StoragePhysicalDescriptor(BaseModel):
    volume_ref: str = Field(max_length=128)
    filesystem: str = Field(max_length=32)
    capacity_gib: int = Field(ge=1)
    export_path: str = Field(max_length=512)


class StorageLogicalDescriptor(BaseModel):
    service_type: Literal["object_storage", "other_registered"] = "object_storage"
    endpoint_url: str = Field(max_length=512)
    bucket: str = Field(max_length=128)
    region: str | None = Field(default=None, max_length=64)
    capacity_gib: int | None = Field(default=None, ge=1)


class ResourceDescriptor(BaseModel):
    """Exactly one branch present, matching class x form (M02-3)."""

    compute_physical: ComputePhysicalDescriptor | None = None
    compute_logical: ComputeLogicalDescriptor | None = None
    storage_physical: StoragePhysicalDescriptor | None = None
    storage_logical: StorageLogicalDescriptor | None = None


class ResourceCredentialIn(BaseModel):
    access_key_id: str | None = Field(default=None, max_length=256)
    secret: str | None = Field(default=None, max_length=1024)
    token: str | None = Field(default=None, max_length=2048)


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    resource_class: ResourceClass
    form: ResourceForm
    descriptor: ResourceDescriptor
    credential: ResourceCredentialIn | None = None
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("labels")
    @classmethod
    def labels_max(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > 20:
            raise ValueError("at most 20 label pairs")
        return v


class ResourcePatch(BaseModel):
    descriptor: ResourceDescriptor | None = None
    credential: ResourceCredentialIn | None = None
    labels: dict[str, str] | None = None


class ResourceOut(BaseModel):
    resource_id: str
    name: str
    resource_class: str
    form: str
    descriptor: dict[str, Any]
    credential_ref: str | None  # opaque vault marker, PA/OE only
    health: str | None
    last_probe_at: datetime | None
    status: str
    labels: dict[str, Any]
    version: int
    created_at: datetime
    created_by: str | None
    decommissioned_at: datetime | None
    bindings_count: int | None = None


# --- Bindings ---


class BindingCreate(BaseModel):
    resource_id: str
    binding_mode: Literal["exclusive", "shared"]
    purpose: str | None = Field(default=None, max_length=200)


class BindingOut(BaseModel):
    binding_id: str
    tenant_id: str
    resource_id: str
    resource_name: str | None = None
    resource_class: str
    form: str
    binding_mode: str
    status: str
    purpose: str | None
    config: dict[str, Any]
    bound_by: str | None
    bound_at: datetime
    released_at: datetime | None
    released_by: str | None
    version: int


class BindingPublicOut(BaseModel):
    """Sanitized binding view for TA/RD (M02-7): kind, name, mode, capacity
    view, status, health — no credentials, vault paths, or raw endpoints."""

    binding_id: str
    resource_name: str
    resource_class: str
    form: str
    binding_mode: str
    status: str
    capacity_view: dict[str, Any]
    health: str | None
    bound_at: datetime


# --- Projects ---


class ProjectCreate(BaseModel):
    name: str = Field(pattern=SLUG_PATTERN)
    display_name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    owner_user_id: str
    default_storage_binding_id: str | None = None


class ProjectPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    owner_user_id: str | None = None
    default_storage_binding_id: str | None = None


class ProjectOut(BaseModel):
    project_id: str
    tenant_id: str
    name: str
    display_name: str
    description: str | None
    status: str
    owner_user_id: str
    default_storage_binding_id: str | None
    version: int
    created_at: datetime
    created_by: str | None
    archived_at: datetime | None
    members_count: int | None = None


# --- Members ---


class MemberPut(BaseModel):
    persona_templates: list[str] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)


class MemberOut(BaseModel):
    user_id: str
    display_name: str
    email: str | None = None
    user_status: str
    persona_templates: list[str]
    note: str | None
    added_by: str | None
    added_at: datetime
