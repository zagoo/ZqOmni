"""FastAPI entrypoint: middleware, error envelope handlers, router mounts,
lifespan (bootstrap + sweepers). Exposes /openapi.json as the frontend SSOT."""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import ERROR_REGISTRY, DomainError
from app.routers import (
    access_reviews,
    audit_events,
    auth,
    internal,
    permissions,
    projects,
    resources,
    role_bindings,
    roles,
    stubs,
    tenants,
    users,
)
from app.schemas.response import ApiResponse, ErrorData
from app.services.bootstrap import ensure_initial_admin
from app.services.sweepers import start_sweepers, stop_sweepers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_initial_admin()
    start_sweepers()
    yield
    await stop_sweepers()


app = FastAPI(
    title="ZqOmni Physical AI Data & Compute Infrastructure Platform",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
if settings.environment == "dev":
    # Vite dev server proxies /api, but allow direct calls too.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["ETag", "Idempotency-Replayed", "Retry-After"],
    )


def _error_response(
    *, http_status: int, code: int, message: str, error_code: str, details: list, headers: dict
) -> JSONResponse:
    trace_id = uuid.uuid4().hex
    envelope = ApiResponse[ErrorData](
        code=code,
        message=message,
        data=ErrorData(error_code=error_code, details=details, trace_id=trace_id),
    )
    return JSONResponse(
        status_code=http_status, content=envelope.model_dump(mode="json"), headers=headers
    )


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return _error_response(
        http_status=exc.http_status,
        code=exc.code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    http_status, code = ERROR_REGISTRY["E_VALIDATION"]
    details = [
        {"loc": [str(p) for p in err.get("loc", [])], "msg": err.get("msg", "")}
        for err in exc.errors()
    ]
    return _error_response(
        http_status=http_status,
        code=code,
        message="Request validation failed.",
        error_code="E_VALIDATION",
        details=details,
        headers={},
    )


@app.exception_handler(Exception)
async def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("app").error("unhandled error", exc_info=exc)
    http_status, code = ERROR_REGISTRY["E_INTERNAL"]
    return _error_response(
        http_status=http_status,
        code=code,
        message="Internal error.",
        error_code="E_INTERNAL",
        details=[],
        headers={},
    )


# In-scope module routers (M01, M02, M03) — mounted before the stubs.
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(resources.router)
app.include_router(projects.router)
app.include_router(users.router)
app.include_router(permissions.router)
app.include_router(roles.router)
app.include_router(role_bindings.router)
app.include_router(audit_events.router)
app.include_router(access_reviews.router)
app.include_router(internal.router)
# Zero-implementation stubs for M04-M20 (mounted last).
app.include_router(stubs.router)


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    return {"status": "ok"}
