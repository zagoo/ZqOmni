# ZqOmni — Physical AI Data & Compute Infrastructure Platform

Implementation of the [FDD](FDD.md) platform with a strict scope lock:

| Scope | Modules |
|---|---|
| **Fully implemented** | **M01** Platform Login & Session Management · **M02** Tenant & Resource Management · **M03** User, Role & Permission Management |
| **Zero-implementation stubs** | M04–M20: navigation entries + empty page shells in the SPA; every API surface answers `501 Not Implemented` |

Stack per [ARCHITECTURE.md](ARCHITECTURE.md): FastAPI (async) + SQLAlchemy 2.0 + PostgreSQL + Alembic backend; Vue 3 + TypeScript + Vite + Pinia SPA with an `@hey-api/openapi-ts` generated client. UI follows the Notion design system in [DESIGN.md](DESIGN.md).

## Quickstart (Docker)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| SPA | http://localhost:5173 |
| API / OpenAPI | http://localhost:8000/docs · `/openapi.json` |
| Mailpit (login codes) | http://localhost:8025 |

Sign-in flow (BP-M1): the bootstrap Platform Administrator is `admin@zqomni.dev`
(override with `ZQ_INITIAL_ADMIN_EMAIL`). Request a code on the login page, read
it in Mailpit, verify. Login codes are never logged anywhere.

## Local development

Backend (needs a PostgreSQL; `docker compose up db mailpit` works):

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
ZQ_DATABASE_URL=postgresql+asyncpg://zqomni:zqomni@localhost:5432/zqomni \
  .venv/bin/alembic upgrade head
ZQ_DATABASE_URL=postgresql+asyncpg://zqomni:zqomni@localhost:5432/zqomni \
  .venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev          # proxies /api -> http://localhost:8000
npm run build        # vue-tsc type-check + vite build
npm run generate:api # regenerate src/api/generated from openapi.json
```

Tests (backend; expects PostgreSQL on `localhost:55432`, e.g.
`docker run -d -p 55432:5432 -e POSTGRES_USER=zqomni -e POSTGRES_PASSWORD=zqomni -e POSTGRES_DB=zqomni postgres:17-alpine`):

```bash
cd backend && .venv/bin/python -m pytest
```

## Layout

```
backend/   FastAPI app (app/routers per domain, app/models per schema,
           app/services for authz/audit/login logic, alembic/ migrations)
frontend/  Vue 3 SPA (src/views/{auth,tenancy,iam,stubs} modules,
           src/api/generated SSOT client, src/components AppShell+primitives)
```
