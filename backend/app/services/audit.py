"""Audit event emission (M03-11 semantics, in-transaction).

FDD routes module audit events through outboxes + SVC-13 into M03. In this
monolith every module shares M03's process and database, so events are
appended directly inside the caller's transaction — the same at-least-once
guarantee with strictly stronger ordering (M03 itself writes in-transaction
per FDD §2.3.6 "no self-shipping loop").

Append-only with a per-tenant hash chain:
chain_hash = SHA-256(prev_chain_hash || canonical_event)  (BR-14 tamper evidence)
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import PREFIX_AUDIT_EVENT, new_id
from app.models.iam import AuditEvent


def _canonical(event: dict[str, Any]) -> bytes:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), default=str).encode()


async def _prev_chain_hash(db: AsyncSession, tenant_id: str | None) -> bytes:
    stmt = (
        select(AuditEvent.chain_hash)
        .where(AuditEvent.tenant_id.is_(None) if tenant_id is None else AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc())
        .limit(1)
    )
    prev = (await db.execute(stmt)).scalar_one_or_none()
    return prev or b""


async def emit_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_type: str,
    actor_id: str,
    subject_type: str,
    subject_id: str,
    source_module: str,
    tenant_id: str | None = None,
    project_id: str | None = None,
    decision: str = "n/a",
    reason: str | None = None,
    before_summary: dict[str, Any] | None = None,
    after_summary: dict[str, Any] | None = None,
    trace_id: str | None = None,
    event_id: str | None = None,
    occurred_at: datetime | None = None,
) -> AuditEvent:
    """Append one audit event; idempotent by event_id (duplicates skipped)."""
    event_id = event_id or new_id(PREFIX_AUDIT_EVENT)
    occurred_at = occurred_at or datetime.now(timezone.utc)

    existing = await db.get(AuditEvent, (event_id, occurred_at))
    if existing is not None:
        return existing

    payload = {
        "event_id": event_id,
        "occurred_at": occurred_at,
        "action": action,
        "actor": {"type": actor_type, "id": actor_id},
        "subject": {"type": subject_type, "id": subject_id},
        "scope": {"tenant_id": tenant_id, "project_id": project_id},
        "decision": decision,
        "reason": reason,
        "before_summary": before_summary,
        "after_summary": after_summary,
        "source_module": source_module,
    }
    prev = await _prev_chain_hash(db, tenant_id)
    chain_hash = hashlib.sha256(prev + _canonical(payload)).digest()

    event = AuditEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        recorded_at=datetime.now(timezone.utc),
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        tenant_id=tenant_id,
        project_id=project_id,
        decision=decision,
        reason=reason,
        before_summary=before_summary,
        after_summary=after_summary,
        source_module=source_module,
        trace_id=trace_id,
        chain_hash=chain_hash,
    )
    db.add(event)
    return event
