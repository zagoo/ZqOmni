"""M03-9 access-review generation (RPT-11, FR-D5.6).

Joins role bindings + persona templates + membership against the audit store
for the period. Restricted datasets / release artifacts live in out-of-scope
modules (M08/M14 stubs), so those entry classes are structurally empty; the
review machinery itself is fully implemented over IAM grants + audit data.
Anomaly flags: deactivated_user_with_binding, dormant_grant_90d,
escalation_after_period_start.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_factory
from app.models.iam import AccessReview, AccessReviewEntry, AuditEvent, Role, RoleBinding, User
from app.models.tenancy import Project
from app.services.audit import emit_audit

logger = logging.getLogger("app.m03.reviews")


async def generate_access_review(review_id: str) -> None:
    """Async generation job (runs post-commit of the POST)."""
    async with get_session_factory()() as db:
        review = await db.get(AccessReview, review_id)
        if review is None or review.status != "generating":
            return
        try:
            entries = await _compute_entries(db, review)
            for i, entry in enumerate(entries):
                db.add(
                    AccessReviewEntry(
                        review_id=review_id,
                        entry_no=i,
                        user_id=entry["user_id"],
                        display_name=entry["display_name"],
                        grant=entry["grant"],
                        asset_class=entry["asset_class"],
                        last_access_at=entry["last_access_at"],
                        anomalies=entry["anomalies"],
                    )
                )
            review.summary = {
                "users_with_restricted_access": len(
                    {e["user_id"] for e in entries if e["asset_class"] != "iam_grant"}
                ),
                "dormant_grants": sum(
                    1 for e in entries if "dormant_grant_90d" in e["anomalies"]
                ),
                "anomalies": sum(1 for e in entries if e["anomalies"]),
            }
            review.status = "ready"
            review.completed_at = datetime.now(timezone.utc)
            await emit_audit(
                db,
                action="iam.access_review.completed",
                actor_type="service",
                actor_id="svc-access-review",
                subject_type="access_review",
                subject_id=review_id,
                source_module="M03",
                tenant_id=review.tenant_id,
            )
            await db.commit()
        except Exception as exc:  # fail loud into the review row
            logger.error("access-review generation failed", exc_info=True)
            await db.rollback()
            review = await db.get(AccessReview, review_id)
            if review is not None:
                review.status = "failed"
                review.failure_reason = str(exc)[:500]
                await db.commit()


async def _compute_entries(db: AsyncSession, review: AccessReview) -> list[dict]:
    tenant_id = review.tenant_id
    project_ids = (
        await db.execute(select(Project.project_id).where(Project.tenant_id == tenant_id))
    ).scalars().all()

    # Grants anchored in this tenant subtree (bindings at tenant or its projects).
    stmt = (
        select(RoleBinding, User, Role)
        .join(User, User.user_id == RoleBinding.user_id)
        .join(Role, Role.role_id == RoleBinding.role_id)
        .where(
            RoleBinding.deleted_at.is_(None),
            (
                (RoleBinding.scope_type == "tenant") & (RoleBinding.scope_id == tenant_id)
            )
            | (
                (RoleBinding.scope_type == "project")
                & (RoleBinding.scope_id.in_(project_ids) if project_ids else False)
            ),
        )
    )
    rows = (await db.execute(stmt)).all()

    # last_access_at per user from audit events in the period (DB-side MAX).
    last_access = dict(
        (
            await db.execute(
                select(AuditEvent.actor_id, func.max(AuditEvent.occurred_at))
                .where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.actor_type == "user",
                    AuditEvent.occurred_at >= review.period_start,
                    AuditEvent.occurred_at <= review.period_end,
                )
                .group_by(AuditEvent.actor_id)
            )
        ).all()
    )

    now = datetime.now(timezone.utc)
    entries: list[dict] = []
    for binding, user, role in rows:
        anomalies: list[str] = []
        if user.status == "deactivated":
            anomalies.append("deactivated_user_with_binding")
        user_last = last_access.get(user.user_id)
        if user_last is None and (now - binding.created_at) > timedelta(days=90):
            anomalies.append("dormant_grant_90d")
        if binding.created_at > review.period_start and binding.origin == "direct":
            anomalies.append("escalation_after_period_start")
        entries.append(
            {
                "user_id": user.user_id,
                "display_name": user.display_name,
                "grant": {
                    "via": binding.origin,
                    "role": role.name,
                    "role_id": role.role_id,
                    "scope": f"{binding.scope_type}:{binding.scope_id or 'platform'}",
                    "granted_by": binding.created_by,
                    "granted_at": binding.created_at.isoformat(),
                },
                # Restricted datasets / release artifacts come from M08/M14
                # (zero-implementation stubs) => only iam_grant entries exist.
                "asset_class": "iam_grant",
                "last_access_at": user_last,
                "anomalies": anomalies,
            }
        )
    return entries
