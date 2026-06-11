"""M03-10 authorization decision point (FDD §2.3.3, normative algorithm).

Evaluation order (deny-overrides):
  1. decision cache (TTL 60 s, explicit invalidation)
  2. deny-first short circuits: user status, scope-chain status
  3. Zanzibar-style scope walk project -> tenant -> platform, collecting live
     role bindings at every scope in the chain
  4. union role units (built-ins expand to boundary sets; persona templates
     attached via project membership contribute at project scope)
  5. key-in-union -> allow, else deny `no_grant`
"""
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.models.iam import PersonaTemplate, Role, RoleBinding, RolePermission, User
from app.models.tenancy import Project, ProjectMember, Tenant
from app.services.catalog import BUILTIN_ROLES, builtin_allows

ScopeType = Literal["platform", "tenant", "project"]

decision_cache = TTLCache(ttl_s=get_settings().introspection_cache_ttl_s)


@dataclass
class ScopeChain:
    scope_type: ScopeType
    scope_id: str | None
    project: Project | None = None
    tenant: Tenant | None = None

    @property
    def tenant_id(self) -> str | None:
        return self.tenant.tenant_id if self.tenant else None

    @property
    def project_id(self) -> str | None:
        return self.project.project_id if self.project else None


@dataclass
class Decision:
    decision: Literal["allow", "deny"]
    reason: str
    matched: dict | None = None
    provenance: list[dict] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"


class ScopeNotFound(Exception):
    pass


async def resolve_scope_chain(
    db: AsyncSession, scope_type: ScopeType, scope_id: str | None
) -> ScopeChain:
    """Resolve the ancestor chain; raises ScopeNotFound for dangling ids."""
    chain = ScopeChain(scope_type=scope_type, scope_id=scope_id)
    if scope_type == "platform":
        return chain
    if scope_id is None:
        raise ScopeNotFound("scope id required for non-platform scope")
    if scope_type == "project":
        project = await db.get(Project, scope_id)
        if project is None:
            raise ScopeNotFound(f"project {scope_id} not found")
        chain.project = project
        chain.tenant = await db.get(Tenant, project.tenant_id)
        if chain.tenant is None:  # FK guarantees this; fail loud anyway
            raise ScopeNotFound(f"tenant of project {scope_id} not found")
        return chain
    tenant = await db.get(Tenant, scope_id)
    if tenant is None:
        raise ScopeNotFound(f"tenant {scope_id} not found")
    chain.tenant = tenant
    return chain


def _scope_filters(chain: ScopeChain) -> list:
    """Binding (scope_type, scope_id) pairs collected along the chain."""
    pairs: list[tuple[str, str | None]] = [("platform", None)]
    if chain.tenant is not None:
        pairs.append(("tenant", chain.tenant.tenant_id))
    if chain.project is not None:
        pairs.append(("project", chain.project.project_id))
    return pairs


async def _collect_bindings(
    db: AsyncSession, user_id: str, chain: ScopeChain
) -> list[tuple[RoleBinding, Role]]:
    pairs = _scope_filters(chain)
    stmt = (
        select(RoleBinding, Role)
        .join(Role, Role.role_id == RoleBinding.role_id)
        .where(
            RoleBinding.user_id == user_id,
            RoleBinding.deleted_at.is_(None),
            Role.deleted_at.is_(None),
        )
    )
    rows = (await db.execute(stmt)).all()
    matched: list[tuple[RoleBinding, Role]] = []
    for binding, role in rows:
        for stype, sid in pairs:
            if binding.scope_type == stype and binding.scope_id == sid:
                matched.append((binding, role))
                break
    return matched


async def _custom_role_keys(db: AsyncSession, role_ids: list[str]) -> dict[str, set[str]]:
    if not role_ids:
        return {}
    stmt = select(RolePermission.role_id, RolePermission.permission_key).where(
        RolePermission.role_id.in_(role_ids)
    )
    out: dict[str, set[str]] = {}
    for role_id, key in (await db.execute(stmt)).all():
        out.setdefault(role_id, set()).add(key)
    return out


async def _persona_template_keys(
    db: AsyncSession, user_id: str, chain: ScopeChain
) -> tuple[set[str], list[str]]:
    """Permission keys granted through M02-10 project membership templates."""
    if chain.project is None:
        return set(), []
    member = await db.get(ProjectMember, (chain.project.project_id, user_id))
    if member is None:
        return set(), []
    stmt = select(PersonaTemplate).where(
        PersonaTemplate.template_key.in_(member.persona_templates)
    )
    templates = (await db.execute(stmt)).scalars().all()
    keys: set[str] = set()
    for t in templates:
        keys.update(t.permission_keys)
    return keys, list(member.persona_templates)


def _cache_key(user_id: str, permission_key: str, scope_type: str, scope_id: str | None):
    return (user_id, permission_key, scope_type, scope_id)


async def check_permission(
    db: AsyncSession,
    *,
    user_id: str,
    permission_key: str,
    scope_type: ScopeType,
    scope_id: str | None,
    use_cache: bool = True,
    collect_provenance: bool = False,
) -> Decision:
    cache_key = _cache_key(user_id, permission_key, scope_type, scope_id)
    if use_cache and not collect_provenance:
        cached = decision_cache.get(cache_key)
        if cached is not None:
            return cached

    decision = await _evaluate(
        db,
        user_id=user_id,
        permission_key=permission_key,
        scope_type=scope_type,
        scope_id=scope_id,
        collect_provenance=collect_provenance,
    )
    if use_cache and not collect_provenance:
        decision_cache.set(cache_key, decision)
    return decision


async def _evaluate(
    db: AsyncSession,
    *,
    user_id: str,
    permission_key: str,
    scope_type: ScopeType,
    scope_id: str | None,
    collect_provenance: bool,
) -> Decision:
    # Step 2 — deny-first short circuits.
    user = await db.get(User, user_id)
    if user is None or user.status != "active":
        return Decision("deny", "user_inactive")
    try:
        chain = await resolve_scope_chain(db, scope_type, scope_id)
    except ScopeNotFound:
        return Decision("deny", "scope_inactive")
    if chain.tenant is not None and chain.tenant.status != "active":
        # Tenant suspended/archived => deny all (caller maps suspended to E_TENANT_SUSPENDED).
        reason = "tenant_suspended" if chain.tenant.status == "suspended" else "scope_inactive"
        return Decision("deny", reason)
    if chain.project is not None and chain.project.status == "archived":
        # Archived project => read-only (deny all non-read actions).
        action = permission_key.rsplit(":", 1)[-1]
        if action != "read":
            return Decision("deny", "scope_inactive")

    # Step 3 — scope walk: collect bindings along the ancestor chain.
    bindings = await _collect_bindings(db, user_id, chain)
    custom_keys = await _custom_role_keys(
        db, [r.role_id for _, r in bindings if r.role_type == "custom"]
    )
    template_keys, member_templates = await _persona_template_keys(db, user_id, chain)

    # Steps 4-5 — union + membership test.
    provenance: list[dict] = []
    matched: dict | None = None
    for binding, role in bindings:
        if role.role_type == "builtin":
            allowed = builtin_allows(role.role_id, permission_key, binding.scope_type)
        else:
            allowed = permission_key in custom_keys.get(role.role_id, set())
        if allowed:
            entry = {
                "binding_id": binding.binding_id,
                "role_id": role.role_id,
                "via_scope": f"{binding.scope_type}:{binding.scope_id or 'platform'}",
            }
            provenance.append(entry)
            matched = matched or entry
            if not collect_provenance:
                break
    if matched is None and permission_key in template_keys:
        entry = {
            "binding_id": None,
            "role_id": f"persona:{'+'.join(member_templates)}",
            "via_scope": f"project:{chain.project_id}",
        }
        provenance.append(entry)
        matched = entry

    if matched is None:
        return Decision("deny", "no_grant")
    return Decision("allow", "ok", matched=matched, provenance=provenance)


async def effective_permission_keys(
    db: AsyncSession, *, user_id: str, scope_type: ScopeType, scope_id: str | None
) -> dict[str, list[dict]]:
    """Full effective-set resolution with provenance (M03-7; no cache)."""
    user = await db.get(User, user_id)
    if user is None:
        return {}
    chain = await resolve_scope_chain(db, scope_type, scope_id)
    bindings = await _collect_bindings(db, user_id, chain)
    custom_keys = await _custom_role_keys(
        db, [r.role_id for _, r in bindings if r.role_type == "custom"]
    )
    template_keys, member_templates = await _persona_template_keys(db, user_id, chain)

    from app.services.catalog import HUMAN_KEYS  # local import to avoid cycle at module load

    allowed: dict[str, list[dict]] = {}
    for binding, role in bindings:
        if role.role_type == "builtin":
            keys = {k for k in HUMAN_KEYS if builtin_allows(role.role_id, k, binding.scope_type)}
        else:
            keys = custom_keys.get(role.role_id, set())
        via = {
            "binding_id": binding.binding_id,
            "role": role.role_id if role.role_type == "builtin" else role.name,
            "scope": f"{binding.scope_type}:{binding.scope_id or 'platform'}",
        }
        for k in keys:
            allowed.setdefault(k, []).append(via)
    for k in template_keys:
        allowed.setdefault(k, []).append(
            {
                "binding_id": None,
                "role": f"persona:{'+'.join(member_templates)}",
                "scope": f"project:{chain.project_id}",
            }
        )
    return allowed


# --- Explicit cache invalidation (FDD §2.3.4, mandated granularity) ---


def invalidate_user(user_id: str) -> None:
    decision_cache.delete_where(lambda k: k[0] == user_id)


def invalidate_scope(scope_id: str) -> None:
    decision_cache.delete_where(lambda k: k[3] == scope_id)


def invalidate_all() -> None:
    decision_cache.clear()


def builtin_role_ids() -> set[str]:
    return set(BUILTIN_ROLES.keys())
