"""Reachability probe for logical resources (M02-3 step 3, M02-5 re-probe).

The platform brokers externally provisioned services (DA-20); the probe only
verifies the declared endpoint answers. Disabled by default in dev/test via
settings.resource_probe_enabled (probing fake endpoints would block local
registration flows)."""
import httpx

from app.core.config import get_settings


def _endpoint_of(descriptor: dict) -> str | None:
    for branch in ("compute_logical", "storage_logical"):
        node = descriptor.get(branch)
        if node and node.get("endpoint_url"):
            return node["endpoint_url"]
    return None


async def probe_logical_resource(descriptor: dict) -> bool:
    """True = reachable. When probing is disabled, optimistically True."""
    settings = get_settings()
    if not settings.resource_probe_enabled:
        return True
    endpoint = _endpoint_of(descriptor)
    if endpoint is None:
        return False
    url = endpoint.replace("s3://", "https://", 1) if endpoint.startswith("s3://") else endpoint
    try:
        async with httpx.AsyncClient(timeout=settings.resource_probe_timeout_s, verify=False) as client:
            await client.head(url)
        return True
    except httpx.HTTPError:
        return False
