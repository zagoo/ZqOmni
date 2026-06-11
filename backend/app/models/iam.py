"""M03 persistence (FDD §2.3.4, schemas `iam` and `audit`)."""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    text,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

user_status = Enum(
    "invited", "active", "deactivated", name="user_status", native_enum=False, length=16
)
role_type = Enum("builtin", "custom", name="role_type", native_enum=False, length=16)
role_scope_type = Enum("platform", "tenant", name="role_scope_type", native_enum=False, length=16)
binding_scope_type = Enum(
    "platform", "tenant", "project", name="binding_scope_type", native_enum=False, length=16
)
binding_origin = Enum(
    "direct", "project_membership", name="binding_origin", native_enum=False, length=24
)
review_status = Enum(
    "generating", "ready", "failed", name="review_status", native_enum=False, length=16
)
actor_type = Enum("user", "service", name="actor_type", native_enum=False, length=16)
audit_decision = Enum("allow", "deny", "n/a", name="audit_decision", native_enum=False, length=8)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_status_created", "status", "created_at"),
        {"schema": "iam"},
    )

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # stored lowercased
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(user_status, nullable=False, default="invited")
    deactivate_reason: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column()
    last_used_tenant_id: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        Index("ix_permissions_domain", "domain", "resource", "action"),
        {"schema": "iam"},
    )

    key: Mapped[str] = mapped_column(Text, primary_key=True)  # {domain}.{resource}:{action}
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owning_module: Mapped[str] = mapped_column(Text, nullable=False)
    scope_levels: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    service_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        # name unique per scope among non-deleted roles
        Index(
            "uq_roles_name_per_scope",
            "scope_type",
            "scope_tenant_id",
            "name",
            unique=True,
            postgresql_where=(text("deleted_at IS NULL")),
        ),
        {"schema": "iam"},
    )

    role_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role_type: Mapped[str] = mapped_column(role_type, nullable=False, default="custom")
    scope_type: Mapped[str] = mapped_column(role_scope_type, nullable=False)
    scope_tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenancy.tenants.tenant_id"))
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
    updated_by: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column()
    deleted_by: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = ({"schema": "iam"},)

    role_id: Mapped[str] = mapped_column(ForeignKey("iam.roles.role_id"), primary_key=True)
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("iam.permissions.key"), primary_key=True
    )


class RoleBinding(Base):
    __tablename__ = "role_bindings"
    __table_args__ = (
        Index(
            "uq_role_bindings_unique_live",
            "user_id",
            "role_id",
            "scope_type",
            "scope_id",
            unique=True,
            postgresql_where=(text("deleted_at IS NULL")),
        ),
        Index(
            "ix_role_bindings_user_live",
            "user_id",
            postgresql_where=(text("deleted_at IS NULL")),
        ),
        Index("ix_role_bindings_scope", "scope_type", "scope_id"),
        Index("ix_role_bindings_role", "role_id"),
        {"schema": "iam"},
    )

    binding_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("iam.users.user_id"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("iam.roles.role_id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(binding_scope_type, nullable=False)
    # NULL for platform scope; '' is never used. Checked against tenancy by service logic.
    scope_id: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(binding_origin, nullable=False, default="direct")
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column()
    deleted_by: Mapped[str | None] = mapped_column(Text)


class PersonaTemplate(Base):
    __tablename__ = "persona_templates"
    __table_args__ = ({"schema": "iam"},)

    template_key: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    default_builtin_role: Mapped[str] = mapped_column(ForeignKey("iam.roles.role_id"), nullable=False)
    permission_keys: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    platform_scoped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AccessReview(Base):
    __tablename__ = "access_reviews"
    __table_args__ = (
        Index("ix_access_reviews_tenant", "tenant_id", "created_at"),
        {"schema": "iam"},
    )

    review_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenancy.tenants.tenant_id"), nullable=False)
    review_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(review_status, nullable=False, default="generating")
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    requested_by: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()


class AccessReviewEntry(Base):
    __tablename__ = "access_review_entries"
    __table_args__ = (
        Index("ix_access_review_entries_review", "review_id", "entry_no"),
        {"schema": "iam"},
    )

    review_id: Mapped[str] = mapped_column(
        ForeignKey("iam.access_reviews.review_id"), primary_key=True
    )
    entry_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    grant: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    last_access_at: Mapped[datetime | None] = mapped_column()
    anomalies: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)


class AuditEvent(Base):
    """Append-only audit store (FDD §2.3.4 `audit.events`).

    Declared with native monthly range partitioning on occurred_at; the
    initial migration creates the partitioned table plus a DEFAULT partition.
    """

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_audit_events_tenant_time", "tenant_id", "occurred_at", "event_id"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_actor", "actor_id"),
        Index("ix_audit_events_subject", "subject_type", "subject_id"),
        {"schema": "audit", "postgresql_partition_by": "RANGE (occurred_at)"},
    )

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(actor_type, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(Text)
    project_id: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(audit_decision, nullable=False, default="n/a")
    reason: Mapped[str | None] = mapped_column(Text)
    before_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source_module: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(Text)
    chain_hash: Mapped[bytes | None] = mapped_column(LargeBinary)


class IdempotencyKey(Base):
    """FDD §1.4.4: Idempotency-Key on state-creating POSTs, retained 24 h."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        Index("ix_idempotency_created", "created_at"),
        {"schema": "platform"},
    )

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    payload_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
