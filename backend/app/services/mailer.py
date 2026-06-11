"""OTP mail delivery (SVC-14 equivalent inside the monolith, DA-17).

The login code is passed transiently to SMTP and never logged (§1.4.7).
Failures are logged WARN/ERROR by the caller's wrapper — M01-1 has already
returned 202 by the time delivery runs (post-commit), matching the FDD's
outbox -> mailer decoupling.
"""
import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger("app.mailer")


async def send_login_code(email: str, code: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    message["Subject"] = f"{settings.app_name} login code"
    message.set_content(
        "Your one-time login code is:\n\n"
        f"    {code}\n\n"
        "It expires in 10 minutes and can be used once. "
        "If you did not request it, ignore this email."
    )
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_use_tls,
        timeout=10,
    )


async def send_login_code_safe(email: str, code: str) -> None:
    try:
        await send_login_code(email, code)
    except Exception:
        # Never log the code; mask the address (§1.4.7).
        masked = f"{email[:1]}***@{email.split('@')[-1]}" if "@" in email else "***"
        logger.error("login-code mail delivery failed for %s", masked, exc_info=True)
