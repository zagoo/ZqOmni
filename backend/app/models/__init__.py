"""ORM models. Importing this package registers every table on Base.metadata
(required by Alembic autogeneration and test bootstrapping)."""
from app.models.base import Base
from app.models.auth import LoginCode, LoginThrottle, Session
from app.models.iam import (
    AccessReview,
    AccessReviewEntry,
    AuditEvent,
    IdempotencyKey,
    Permission,
    PersonaTemplate,
    Role,
    RoleBinding,
    RolePermission,
    User,
)
from app.models.tenancy import (
    Project,
    ProjectMember,
    Resource,
    ResourceBinding,
    ResourceCredential,
    Tenant,
)

__all__ = [
    "Base",
    "LoginCode",
    "LoginThrottle",
    "Session",
    "AccessReview",
    "AccessReviewEntry",
    "AuditEvent",
    "IdempotencyKey",
    "Permission",
    "PersonaTemplate",
    "Role",
    "RoleBinding",
    "RolePermission",
    "User",
    "Project",
    "ProjectMember",
    "Resource",
    "ResourceBinding",
    "ResourceCredential",
    "Tenant",
]
