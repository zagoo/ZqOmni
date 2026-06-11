"""M02-10 -> M03 materialization (FDD: `tenant.project.member_upserted/removed`
consumer; in-monolith it runs inside the same transaction — same idempotent
outcome, instant propagation).

The tenancy.project_members row is the source of truth for membership; the
materialized `rbn-` rows (origin=project_membership) are its authorization
materialization: one binding per distinct default built-in role among the
assigned templates, at project scope.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import PREFIX_ROLE_BINDING, new_id
from app.models.iam import PersonaTemplate, RoleBinding
from app.services import authz


async def materialize_membership_bindings(
    db: AsyncSession, *, project_id: str, user_id: str, persona_templates: list[str]
) -> None:
    templates = (
        await db.execute(
            select(PersonaTemplate).where(PersonaTemplate.template_key.in_(persona_templates))
        )
    ).scalars().all()
    wanted_roles = {t.default_builtin_role for t in templates}

    existing = (
        await db.execute(
            select(RoleBinding).where(
                RoleBinding.user_id == user_id,
                RoleBinding.scope_type == "project",
                RoleBinding.scope_id == project_id,
                RoleBinding.origin == "project_membership",
                RoleBinding.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    existing_roles = {b.role_id for b in existing}

    now = datetime.now(timezone.utc)
    for role_id in wanted_roles - existing_roles:
        db.add(
            RoleBinding(
                binding_id=new_id(PREFIX_ROLE_BINDING),
                user_id=user_id,
                role_id=role_id,
                scope_type="project",
                scope_id=project_id,
                origin="project_membership",
                created_at=now,
                created_by="system:project_membership",
            )
        )
    for binding in existing:
        if binding.role_id not in wanted_roles:
            binding.deleted_at = now
            binding.deleted_by = "system:project_membership"

    authz.invalidate_user(user_id)


async def remove_membership_bindings(db: AsyncSession, *, project_id: str, user_id: str) -> None:
    existing = (
        await db.execute(
            select(RoleBinding).where(
                RoleBinding.user_id == user_id,
                RoleBinding.scope_type == "project",
                RoleBinding.scope_id == project_id,
                RoleBinding.origin == "project_membership",
                RoleBinding.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for binding in existing:
        binding.deleted_at = now
        binding.deleted_by = "system:project_membership"
    authz.invalidate_user(user_id)
