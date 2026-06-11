"""Internal service plane (FDD /internal/v1; mTLS stood in by the service
token guard): M03-10 authz check/batch-check, M03-11 audit ingestion.
M01-7 introspection lives in routers/auth.py."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_service_identity
from app.core.config import get_settings
from app.database import get_db
from app.models.iam import AuditEvent
from app.schemas.iam import (
    AuditIngestRejection,
    AuditIngestRequest,
    AuditIngestResponse,
    AuthzBatchCheckRequest,
    AuthzBatchCheckResponse,
    AuthzCheckRequest,
    AuthzCheckResponse,
    AuthzMatched,
)
from app.services import authz
from app.services.audit import emit_audit

router = APIRouter(include_in_schema=False)

DB = Annotated[AsyncSession, Depends(get_db)]
SVC = Annotated[str, Depends(require_service_identity)]


async def _run_check(db: AsyncSession, check: AuthzCheckRequest) -> AuthzCheckResponse:
    decision = await authz.check_permission(
        db,
        user_id=check.user_id,
        permission_key=check.permission_key,
        scope_type=check.scope.type,
        scope_id=check.scope.id,
    )
    return AuthzCheckResponse(
        decision=decision.decision,
        reason=decision.reason,
        matched=AuthzMatched(**decision.matched) if decision.matched else None,
        ttl_s=get_settings().introspection_cache_ttl_s,
        evaluated_at=datetime.now(timezone.utc),
    )


@router.post("/internal/v1/authz/check", operation_id="m03_authz_check")
async def authz_check(body: AuthzCheckRequest, db: DB, _svc: SVC) -> AuthzCheckResponse:
    return await _run_check(db, body)


@router.post("/internal/v1/authz/batch-check", operation_id="m03_authz_batch_check")
async def authz_batch_check(
    body: AuthzBatchCheckRequest, db: DB, _svc: SVC
) -> AuthzBatchCheckResponse:
    results = [await _run_check(db, check) for check in body.checks]  # order-preserved
    return AuthzBatchCheckResponse(results=results)


@router.post(
    "/internal/v1/audit-events", operation_id="m03_ingest_audit_events", status_code=202
)
async def ingest_audit_events(
    body: AuditIngestRequest, db: DB, _svc: SVC
) -> AuditIngestResponse:
    """M03-11: per-event accept/reject, idempotent by event_id, append-only."""
    accepted = 0
    duplicates = 0
    rejected: list[AuditIngestRejection] = []
    for index, event in enumerate(body.events):
        try:
            before = await db.get(AuditEvent, (event.event_id, event.occurred_at))
            if before is not None:
                duplicates += 1
                continue
            await emit_audit(
                db,
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                action=event.action,
                actor_type=event.actor.type,
                actor_id=event.actor.id,
                subject_type=event.subject.type,
                subject_id=event.subject.id,
                tenant_id=event.scope.tenant_id,
                project_id=event.scope.project_id,
                decision=event.decision,
                reason=event.reason,
                before_summary=event.before_summary,
                after_summary=event.after_summary,
                source_module=event.source_module,
                trace_id=event.trace_id,
            )
            accepted += 1
        except Exception as exc:
            rejected.append(
                AuditIngestRejection(index=index, code="E_VALIDATION", message=str(exc)[:200])
            )
    await db.commit()
    return AuditIngestResponse(accepted=accepted, duplicates=duplicates, rejected=rejected)
