"""Application settings (ARCHITECTURE.md: configuration via env vars only).

Every deployment-variable value flows through this module; business code
never reads .env directly.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ZQ_", extra="ignore")

    app_name: str = "ZqOmni Physical AI Platform"
    environment: str = "dev"  # dev | test | prod

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://zqomni:zqomni@localhost:5432/zqomni"
    )
    db_echo: bool = False

    # --- Security (FDD §2.1; ARCHITECTURE §2.6) ---
    # Pepper for HMAC-SHA-256 hashing of login codes (FDD: held outside the DB).
    otp_pepper: str = "dev-otp-pepper-change-me"
    # Symmetric key for JWT access tokens (HS256) signed/verified in core/security.py.
    jwt_secret: str = "dev-jwt-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_ttl_s: int = 600  # short-lived Access Token (dual-token system)
    # FDD session policy: idle 60 min sliding, absolute 24 h (configurable downward only).
    session_idle_ttl_s: int = 3600
    session_absolute_ttl_s: int = 86400
    introspection_cache_ttl_s: int = 60
    # Fernet key material for the local encrypted credential store standing in
    # for the platform vault (M02 logical-resource credentials).
    vault_key: str = "dev-vault-key-change-me"

    # --- Internal service plane (stands in for mTLS service identity, FDD §1.4.2) ---
    internal_service_token: str = "dev-internal-service-token"

    # --- M01 login-code policy (FDD §2.1.2, normative) ---
    login_code_ttl_s: int = 600
    login_code_max_attempts: int = 5
    resend_cooldown_s: int = 60
    throttle_ip_per_hour: int = 10
    throttle_email_per_15m: int = 3
    throttle_email_per_24h: int = 10
    verify_backoff_threshold: int = 5
    verify_backoff_base_s: int = 30
    verify_backoff_cap_s: int = 900

    # --- Mail (SVC-14 equivalent; DA-17 corporate SMTP relay) ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@zqomni.dev"
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False

    # --- M03 platform policy ---
    # Empty list = any domain accepted (dev default); production sets the corporate list.
    allowed_email_domains: list[str] = Field(default_factory=list)
    audit_query_max_window_days: int = 92

    # --- Bootstrap (BP-M1 step 0: the first PA must exist before anyone can
    # log in). NOTE: special-use TLDs (.local/.test) fail RFC validation at
    # M01-1; use a routable-looking domain even in dev. ---
    initial_admin_email: str = "admin@zqomni.dev"
    initial_admin_display_name: str = "Platform Administrator"

    # --- M02 ---
    resource_probe_enabled: bool = False  # reachability probe for logical resources
    resource_probe_timeout_s: float = 3.0

    # --- Background jobs (code/session sweepers, binding health probe) ---
    sweepers_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
