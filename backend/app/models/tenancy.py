"""M02 persistence (FDD §2.2.4, schema `tenancy`)."""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    text,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

tenant_status = Enum(
    "active", "suspended", "archived", name="tenant_status", native_enum=False, length=16
)
resource_class = Enum("compute", "storage", name="resource_class", native_enum=False, length=16)
resource_form = Enum("physical", "logical", name="resource_form", native_enum=False, length=16)
resource_status = Enum(
    "active", "decommissioned", name="resource_status", native_enum=False, length=20
)
resource_health = Enum(
    "unprobed", "reachable", "unreachable", name="resource_health", native_enum=False, length=16
)
binding_mode = Enum("exclusive", "shared", name="binding_mode", native_enum=False, length=16)
binding_status = Enum("active", "released", name="binding_status", native_enum=False, length=16)
project_status = Enum("active", "archived", name="project_status", native_enum=False, length=16)


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_status_created", "status", "created_at"),
        {"schema": "tenancy"},
    )

    tenant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(tenant_status, nullable=False, default="active")
    suspend_reason: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    namespace_ref: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)
    suspended_at: Mapped[datetime | None] = mapped_column()
    archived_at: Mapped[datetime | None] = mapped_column()


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        Index("ix_resources_kind_status", "resource_class", "form", "status", "created_at"),
        {"schema": "tenancy"},
    )

    resource_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    resource_class: Mapped[str] = mapped_column(resource_class, nullable=False)
    form: Mapped[str] = mapped_column(resource_form, nullable=False)
    descriptor: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(Text)
    health: Mapped[str | None] = mapped_column(resource_health)
    last_probe_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(resource_status, nullable=False, default="active")
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)
    decommissioned_at: Mapped[datetime | None] = mapped_column()


class ResourceCredential(Base):
    """Local encrypted store standing in for the platform vault (FDD: secrets
    never live in `tenancy.resources`; only `credential_ref` does)."""

    __tablename__ = "resource_credentials"
    __table_args__ = ({"schema": "tenancy"},)

    resource_id: Mapped[str] = mapped_column(
        ForeignKey("tenancy.resources.resource_id"), primary_key=True
    )
    secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class ResourceBinding(Base):
    __tablename__ = "resource_bindings"
    __table_args__ = (
        # FDD M02-5: duplicate (tenant,resource) active binding -> E_CONFLICT.
        Index(
            "uq_bindings_tenant_resource_active",
            "tenant_id",
            "resource_id",
            unique=True,
            postgresql_where=(text("status = 'active'")),
        ),
        # FDD M02-5: one exclusive active binding per resource.
        Index(
            "uq_bindings_exclusive_resource",
            "resource_id",
            unique=True,
            postgresql_where=(text("binding_mode = 'exclusive' AND status = 'active'")),
        ),
        Index("ix_bindings_tenant_status", "tenant_id", "status", "bound_at"),
        {"schema": "tenancy"},
    )

    binding_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenancy.tenants.tenant_id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("tenancy.resources.resource_id"), nullable=False
    )
    binding_mode: Mapped[str] = mapped_column(binding_mode, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    purpose: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(binding_status, nullable=False, default="active")
    bound_at: Mapped[datetime] = mapped_column(nullable=False)
    bound_by: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[datetime | None] = mapped_column()
    released_by: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name"),
        Index("ix_projects_tenant_status", "tenant_id", "status", "created_at"),
        Index("ix_projects_owner", "owner_user_id"),
        {"schema": "tenancy"},
    )

    project_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenancy.tenants.tenant_id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("iam.users.user_id"), nullable=False)
    default_storage_binding_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenancy.resource_bindings.binding_id")
    )
    status: Mapped[str] = mapped_column(project_status, nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column()
    archived_by: Mapped[str | None] = mapped_column(Text)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        CheckConstraint(
            "array_length(persona_templates, 1) >= 1", name="persona_templates_nonempty"
        ),
        Index("ix_project_members_user", "user_id"),
        {"schema": "tenancy"},
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("tenancy.projects.project_id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("iam.users.user_id"), primary_key=True)
    persona_templates: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(nullable=False)
    added_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)
