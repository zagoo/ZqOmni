"""Database-level pagination helpers (ARCHITECTURE §2.8: LIMIT/OFFSET +
COUNT(*) in SQL; opaque page tokens per FDD §1.4.1)."""
import base64
import binascii

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import validation_error

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


class PageParams(BaseModel):
    page_size: int
    offset: int

    @property
    def next_token(self) -> str:
        return encode_page_token(self.offset + self.page_size)


def encode_page_token(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def decode_page_token(token: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        kind, value = raw.split(":", 1)
        if kind != "o":
            raise ValueError
        offset = int(value)
        if offset < 0:
            raise ValueError
        return offset
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise validation_error("Invalid page_token.") from None


def page_params(
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    page_token: str | None = Query(None),
) -> PageParams:
    offset = decode_page_token(page_token) if page_token else 0
    return PageParams(page_size=page_size, offset=offset)


async def paginate(
    db: AsyncSession, stmt: Select, page: PageParams
) -> tuple[list, str | None, int]:
    """Run COUNT + LIMIT/OFFSET at the database layer."""
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(page.page_size).offset(page.offset))).scalars().all()
    next_token = page.next_token if page.offset + len(rows) < total else None
    return list(rows), next_token, total
