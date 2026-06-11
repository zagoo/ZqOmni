"""Startup bootstrap (BP-M1 step 0): ensure the initial Platform
Administrator exists — without one, nobody can pass M03-1 pre-registration.
Idempotent; driven by ZQ_INITIAL_ADMIN_EMAIL."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.ids import PREFIX_ROLE_BINDING, PREFIX_USER, new_id
from app.database import get_session_factory
from app.models.iam import RoleBinding, User
from app.services.catalog import ROLE_PA

logger = logging.getLogger("app.bootstrap")


async def ensure_initial_admin() -> None:
    settings = get_settings()
    email = settings.initial_admin_email.strip().lower()
    if not email:
        return
    async with get_session_factory()() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if user is None:
            user = User(
                user_id=new_id(PREFIX_USER),
                email=email,
                display_name=settings.initial_admin_display_name,
                status="invited",
                version=1,
                created_at=now,
                created_by="system:bootstrap",
            )
            db.add(user)
            await db.flush()
            logger.info("bootstrap: created initial platform administrator user")
        binding = (
            await db.execute(
                select(RoleBinding).where(
                    RoleBinding.user_id == user.user_id,
                    RoleBinding.role_id == ROLE_PA,
                    RoleBinding.scope_type == "platform",
                    RoleBinding.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if binding is None:
            db.add(
                RoleBinding(
                    binding_id=new_id(PREFIX_ROLE_BINDING),
                    user_id=user.user_id,
                    role_id=ROLE_PA,
                    scope_type="platform",
                    scope_id=None,
                    origin="direct",
                    created_at=now,
                    created_by="system:bootstrap",
                )
            )
            logger.info("bootstrap: bound initial administrator to builtin:platform_admin")
        await db.commit()
