"""Batch jobs (FDD §2.1.4 / §2.2.4): code-sweeper (1 min), session-sweeper
(5 min), binding-health-probe (hourly), idempotency purge (hourly).

Run as asyncio loops inside the app process (monolith equivalent of the FDD's
scheduled jobs); disabled via settings.sweepers_enabled for tests.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from app.core.config import get_settings
from app.database import get_session_factory
from app.models.auth import LoginCode, Session
from app.models.iam import IdempotencyKey
from app.models.tenancy import Resource
from app.services.probes import probe_logical_resource

logger = logging.getLogger("app.sweepers")

_tasks: list[asyncio.Task] = []


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def sweep_login_codes() -> None:
    async with get_session_factory()() as db:
        await db.execute(
            update(LoginCode)
            .where(LoginCode.status == "issued", LoginCode.expires_at <= _now())
            .values(status="expired", expire_reason="ttl")
        )
        # Hard-delete terminal codes >24 h (DA-11).
        await db.execute(
            delete(LoginCode).where(
                LoginCode.status != "issued",
                LoginCode.created_at <= _now() - timedelta(hours=24),
            )
        )
        await db.commit()


async def sweep_sessions() -> None:
    async with get_session_factory()() as db:
        await db.execute(
            update(Session)
            .where(
                Session.status == "active",
                (Session.idle_expires_at <= _now()) | (Session.absolute_expires_at <= _now()),
            )
            .values(status="expired")
        )
        # Purge terminal sessions >90 d (audit store keeps the long-term record).
        await db.execute(
            delete(Session).where(
                Session.status != "active",
                Session.created_at <= _now() - timedelta(days=90),
            )
        )
        await db.commit()


async def sweep_idempotency() -> None:
    async with get_session_factory()() as db:
        await db.execute(
            delete(IdempotencyKey).where(
                IdempotencyKey.created_at <= _now() - timedelta(hours=24)
            )
        )
        await db.commit()


async def probe_binding_health() -> None:
    """Hourly re-probe of logical resources; visibility only (DA-20)."""
    async with get_session_factory()() as db:
        resources = (
            await db.execute(
                select(Resource).where(Resource.form == "logical", Resource.status == "active")
            )
        ).scalars().all()
        for resource in resources:
            reachable = await probe_logical_resource(resource.descriptor)
            new_health = "reachable" if reachable else "unreachable"
            if resource.health != new_health:
                logger.warning(
                    "resource health changed",
                    extra={"resource_id": resource.resource_id, "health": new_health},
                )
            resource.health = new_health
            resource.last_probe_at = _now()
        await db.commit()


async def _loop(interval_s: float, job, name: str) -> None:
    while True:
        try:
            await job()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("sweeper %s failed", name, exc_info=True)
        await asyncio.sleep(interval_s)


def start_sweepers() -> None:
    if not get_settings().sweepers_enabled:
        return
    _tasks.append(asyncio.create_task(_loop(60, sweep_login_codes, "code-sweeper")))
    _tasks.append(asyncio.create_task(_loop(300, sweep_sessions, "session-sweeper")))
    _tasks.append(asyncio.create_task(_loop(3600, sweep_idempotency, "idempotency-purge")))
    _tasks.append(asyncio.create_task(_loop(3600, probe_binding_health, "binding-health-probe")))


async def stop_sweepers() -> None:
    for task in _tasks:
        task.cancel()
    for task in _tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    _tasks.clear()
