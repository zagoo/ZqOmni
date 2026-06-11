"""Domain error model.

Reconciliation of two binding contracts (surfaced per CLAUDE.md Rule 11):
- FDD §1.4.3 defines string error codes (`E_*`) + HTTP statuses.
- ARCHITECTURE.md §2.3 / CLAUDE.md Rule 6.6 require every response wrapped in
  `ApiResponse {code:int, message, data}` with `code != 0` as the domain error
  signal.

We keep both: HTTP status per FDD, envelope `code` is a stable integer derived
from the registry below, and the FDD string code travels in
`data.error_code` so clients and tests can assert on the normative codes.
"""
from typing import Any


class DomainError(Exception):
    """Raised by services/routers; converted to an ApiResponse envelope."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or []
        self.headers = headers or {}
        try:
            self.http_status, self.code = ERROR_REGISTRY[error_code]
        except KeyError as exc:  # programming error, fail loud
            raise ValueError(f"unregistered error code: {error_code}") from exc


# error_code -> (http_status, envelope business code)
# Envelope codes: http_status * 100 + stable 2-digit sequence.
ERROR_REGISTRY: dict[str, tuple[int, int]] = {
    # --- shared (FDD §1.4.3) ---
    "E_UNAUTHENTICATED": (401, 40100),
    "E_PERMISSION_DENIED": (403, 40300),
    "E_TENANT_SUSPENDED": (403, 40301),
    "E_RESTRICTED_DATA": (403, 40302),
    "E_NOT_FOUND": (404, 40400),
    "E_CONFLICT": (409, 40900),
    "E_STATE_INVALID": (409, 40901),
    "E_PRECONDITION_FAILED": (412, 41200),
    "E_PRECONDITION_REQUIRED": (428, 42800),
    "E_VALIDATION": (422, 42200),
    "E_RATE_LIMITED": (429, 42900),
    "E_QUOTA_EXCEEDED": (429, 42901),
    "E_IDEMPOTENCY_CONFLICT": (409, 40902),
    "E_INTERNAL": (500, 50000),
    "E_UPSTREAM_UNAVAILABLE": (503, 50300),
    "E_NOT_IMPLEMENTED": (501, 50100),
    # --- M01 (FDD §2.1.3) ---
    "E_AUTH_CODE_INVALID": (401, 40101),
    "E_AUTH_TENANT_NOT_ASSIGNED": (403, 40310),
    # --- M02 (FDD §2.2.3) ---
    "E_TNT_BINDING_CONFLICT": (409, 40910),
    "E_TNT_RESOURCE_IN_USE": (409, 40911),
    "E_TNT_CREDENTIAL_INVALID": (422, 42210),
    "E_TNT_TENANT_NOT_EMPTY": (409, 40912),
    "E_TNT_PROJECT_ACTIVE_WORK": (409, 40913),
    # --- M03 (FDD §2.3.3) ---
    "E_IAM_EMAIL_EXISTS": (409, 40920),
    "E_IAM_BUILTIN_IMMUTABLE": (409, 40921),
    "E_IAM_ROLE_IN_USE": (409, 40922),
    "E_IAM_UNKNOWN_PERMISSION": (422, 42220),
    "E_IAM_SCOPE_MISMATCH": (422, 42221),
    "E_IAM_LAST_PLATFORM_ADMIN": (409, 40923),
    "E_IAM_LAST_TENANT_ADMIN": (409, 40924),
}


def not_found(message: str = "Resource not found.") -> DomainError:
    return DomainError("E_NOT_FOUND", message)


def permission_denied(message: str = "You do not have permission to perform this action.") -> DomainError:
    return DomainError("E_PERMISSION_DENIED", message)


def validation_error(message: str, details: list[dict[str, Any]] | None = None) -> DomainError:
    return DomainError("E_VALIDATION", message, details=details)


def state_invalid(message: str, allowed_transitions: list[str] | None = None) -> DomainError:
    details = (
        [{"allowed_transitions": allowed_transitions}] if allowed_transitions is not None else []
    )
    return DomainError("E_STATE_INVALID", message, details=details)
