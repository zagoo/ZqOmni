"""Type-prefixed ULID identifiers (FDD §1.4.1)."""
from ulid import ULID

# Prefixes per FDD Table 0.3 / module data designs.
PREFIX_USER = "usr"
PREFIX_TENANT = "tnt"
PREFIX_PROJECT = "prj"
PREFIX_RESOURCE = "res"
PREFIX_BINDING = "rbd"
PREFIX_ROLE = "rol"
PREFIX_ROLE_BINDING = "rbn"
PREFIX_SESSION = "ses"
PREFIX_LOGIN_CODE = "lgc"
PREFIX_AUDIT_EVENT = "aud"
PREFIX_ACCESS_REVIEW = "arv"


def new_id(prefix: str) -> str:
    return f"{prefix}-{ULID()}"
