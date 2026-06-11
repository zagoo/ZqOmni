"""Credential primitives (ARCHITECTURE §2.6: JWT encode/decode and secret
hashing live ONLY here; FDD §2.1: OTP hash-at-rest, opaque session tokens).
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

# --- Login codes (FDD §2.1.2 login-code policy) ---


def generate_login_code() -> str:
    """8-digit numeric code from a CSPRNG (entropy ~26.6 bits >= 20-bit mandate)."""
    return f"{secrets.randbelow(10**8):08d}"


def new_code_salt() -> bytes:
    return secrets.token_bytes(16)


def hash_login_code(code: str, salt: bytes) -> bytes:
    """HMAC-SHA-256(pepper, salt || code); pepper never stored in the database."""
    pepper = get_settings().otp_pepper.encode()
    return hmac.new(pepper, salt + code.encode(), hashlib.sha256).digest()


def verify_login_code(code: str, salt: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(hash_login_code(code, salt), expected)


# --- Session tokens (FDD: opaque 256-bit, server stores SHA-256 only) ---


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def hash_identifier(value: str) -> bytes:
    """Salted hash for abuse forensics (IPs, emails in throttle rows)."""
    pepper = get_settings().otp_pepper.encode()
    return hmac.new(pepper, value.encode(), hashlib.sha256).digest()


# --- Access tokens (ARCHITECTURE §2.6 dual-token: short-lived JWT) ---


def issue_access_token(*, user_id: str, session_id: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.access_token_ttl_s)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "typ": "access",
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    return payload


# --- Local encrypted credential store (stands in for the platform vault) ---


def _fernet() -> Fernet:
    key = hashlib.sha256(get_settings().vault_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt_secret(ciphertext: bytes) -> str | None:
    try:
        return _fernet().decrypt(ciphertext).decode()
    except InvalidToken:
        return None
