"""Standardized response envelope (ARCHITECTURE §2.3 / CLAUDE.md Rule 6.6).

`ApiResponse[T]`: code=0 success; code!=0 domain error (frontend Rule 5.12).
`PageData[T]` realizes the FDD §1.4.1 list envelope as the nested generic.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    items: list[T]
    next_page_token: str | None = None
    total_size: int | None = None


class ErrorData(BaseModel):
    """Error payload carried in ApiResponse.data; error_code holds the
    normative FDD `E_*` string."""

    error_code: str
    details: list[dict] = Field(default_factory=list)
    trace_id: str | None = None
