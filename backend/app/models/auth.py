"""M01 persistence (FDD §2.1.4, schema `auth`)."""
from datetime import datetime

from sqlalchemy import (
    text,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

login_code_status = Enum(
    "issued", "consumed", "expired", name="login_code_status", native_enum=False, length=16
)
login_code_expire_reason = Enum(
    "ttl",
    "superseded",
    "attempts_exhausted",
    "user_deactivated",
    name="login_code_expire_reason",
    native_enum=False,
    length=24,
)
session_status = Enum(
    "active", "expired", "revoked", name="session_status", native_enum=False, length=16
)
session_revoked_reason = Enum(
    "logout",
    "admin_revoke",
    "user_deactivated",
    name="session_revoked_reason",
    native_enum=False,
    length=24,
)


class LoginCode(Base):
    __tablename__ = "login_codes"
    __table_args__ = (
        CheckConstraint("attempt_count <= 5", name="attempt_count_max"),
        # FDD: at most one live code per user.
        Index(
            "uq_login_codes_one_issued_per_user",
            "user_id",
            unique=True,
            postgresql_where=(text("status = 'issued'")),
        ),
        Index("ix_login_codes_status_expires", "status", "expires_at"),
        {"schema": "auth"},
    )

    code_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("iam.users.user_id"), nullable=False, index=True
    )
    code_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(login_code_status, nullable=False, default="issued")
    expire_reason: Mapped[str | None] = mapped_column(login_code_expire_reason)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    request_ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index(
            "ix_sessions_active_expiry",
            "idle_expires_at",
            postgresql_where=(text("status = 'active'")),
        ),
        {"schema": "auth"},
    )

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("iam.users.user_id"), nullable=False, index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(session_status, nullable=False, default="active")
    revoked_reason: Mapped[str | None] = mapped_column(session_revoked_reason)
    active_tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenancy.tenants.tenant_id"))
    client_user_agent: Mapped[str | None] = mapped_column(Text)
    client_device_label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()


class LoginThrottle(Base):
    """Per-email verification backoff (T4) — durable fallback per FDD §2.1.4."""

    __tablename__ = "login_throttle"
    __table_args__ = ({"schema": "auth"},)

    email_hash: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    consecutive_failures: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    backoff_until: Mapped[datetime | None] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
