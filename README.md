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

---

# Production deployment

The `docker-compose.yml` and the two `Dockerfile`s in this repo are tuned for **local development** (hot-reload, the Vite dev server, Mailpit, default secrets). They are **not** a production deployment. This section is the complete, code-grounded checklist to run ZqOmni as a real online service.

> Every value below is read through `backend/app/core/config.py` (Pydantic Settings, env prefix **`ZQ_`**). Business code never reads `.env` directly — set these as real environment variables / platform secrets.

## 1. Generate the four cryptographic secrets

These four default to obvious `dev-*` placeholders and **must** be replaced. Generate strong values once:

```bash
python3 - <<'PY'
import secrets
for k in ("ZQ_OTP_PEPPER", "ZQ_JWT_SECRET", "ZQ_VAULT_KEY", "ZQ_INTERNAL_SERVICE_TOKEN"):
    print(f"{k}={secrets.token_urlsafe(48)}")
PY
```

| Secret | Role | Rotation rules |
|---|---|---|
| `ZQ_OTP_PEPPER` | HMAC pepper for login-code hashing (codes are stored only as `HMAC-SHA-256(pepper, salt‖code)`). | Must be **stable across all replicas and restarts**. Changing it invalidates outstanding (10-min) login codes only — safe to rotate during a quiet window. |
| `ZQ_JWT_SECRET` | HS256 signing key for short-lived access tokens. **≥ 32 bytes** (the lib warns below that). | Stable across replicas. Rotating it invalidates live access tokens, but clients silently re-mint via the refresh endpoint (which validates the DB session, not the JWT) — effectively zero user impact. |
| `ZQ_VAULT_KEY` | Key material for the Fernet store that encrypts M02 logical-resource credentials at rest. | **Set once, back it up, never change after any credential is stored.** Changing it makes every stored resource credential undecryptable. Treat like a database encryption key. |
| `ZQ_INTERNAL_SERVICE_TOKEN` | Shared token guarding the `/internal/v1/*` service plane (authz check, audit ingest, introspect). | Rotate from the default. **Also block `/internal/v1` at the edge** (see §4) — it must never be reachable from the public internet. |

Store all secrets in your platform's secret manager (AWS Secrets Manager, GCP Secret Manager, Kubernetes Secrets, Doppler, Vault). Do **not** commit them or bake them into images.

## 2. Full environment-variable reference

**Must set for production:**

| Variable | Dev default | Production value & why |
|---|---|---|
| `ZQ_ENVIRONMENT` | `dev` | **`prod`** — gates two behaviors: the session cookie becomes `Secure` (HTTPS-only), and the permissive dev CORS middleware is **disabled** (prod is same-origin only — see §4). |
| `ZQ_DATABASE_URL` | local Postgres | `postgresql+asyncpg://USER:PW@HOST:5432/DB` for your managed Postgres 17. Enable TLS to the DB (see §3). |
| `ZQ_OTP_PEPPER` / `ZQ_JWT_SECRET` / `ZQ_VAULT_KEY` / `ZQ_INTERNAL_SERVICE_TOKEN` | `dev-*` | Generated secrets from §1. |
| `ZQ_INITIAL_ADMIN_EMAIL` | `admin@zqomni.dev` | A **real corporate email of your first Platform Administrator**. On startup the app idempotently ensures this user + the `builtin:platform_admin` binding exist (BP-M1 step 0). Use a routable domain — special-use TLDs like `.local`/`.test` fail RFC email validation at login. |
| `ZQ_INITIAL_ADMIN_DISPLAY_NAME` | `Platform Administrator` | Display name for that admin. |
| `ZQ_SMTP_HOST` | `localhost` | Your corporate SMTP relay or ESP (SES / SendGrid / Postmark). **Login is impossible without working mail** — codes are delivered only by email. |
| `ZQ_SMTP_PORT` | `1025` | `587` (STARTTLS) or `465` (implicit TLS). |
| `ZQ_SMTP_USE_TLS` | `false` | `true` **only for port 465** (implicit TLS). For port 587 leave `false` — the mailer auto-negotiates STARTTLS when the server advertises it. Avoid plaintext port 25. |
| `ZQ_SMTP_USERNAME` / `ZQ_SMTP_PASSWORD` | empty | ESP credentials (password is a secret). |
| `ZQ_SMTP_FROM` | `no-reply@zqomni.dev` | A from-address authorized on your domain (SPF/DKIM aligned) so codes don't land in spam. |
| `ZQ_ALLOWED_EMAIL_DOMAINS` | `[]` (any) | **JSON array** of allowed corporate domains for user pre-registration, e.g. `["yourco.com","yourco.io"]`. Empty means any domain is accepted — lock this down. (Restricts M03 pre-registration; the bootstrap admin and login itself are not domain-filtered.) |
| `ZQ_SWEEPERS_ENABLED` | `true` | See the **multi-replica caveat** in §6 — run sweepers on exactly one instance. |
| `ZQ_RESOURCE_PROBE_ENABLED` | `false` | `true` if you want logical-resource registration/binding to reachability-probe the endpoint. Note the TLS caveat in §7. |
| `ZQ_DB_ECHO` | `false` | Keep `false` (SQL logging is noisy and may leak query shapes). |

**Tunable, safe to leave at defaults** (override only with intent):

| Variable | Default | Notes |
|---|---|---|
| `ZQ_ACCESS_TOKEN_TTL_S` | `600` | Access-JWT lifetime. |
| `ZQ_SESSION_IDLE_TTL_S` | `3600` | Sliding idle timeout. FDD: **configurable downward only**. |
| `ZQ_SESSION_ABSOLUTE_TTL_S` | `86400` | Hard session lifetime. Downward only. |
| `ZQ_INTROSPECTION_CACHE_TTL_S` | `60` | Also the bound on cross-replica permission-staleness (§6). |
| `ZQ_THROTTLE_IP_PER_HOUR` | `10` | Login-code requests per IP/hour — **requires real client IPs** (§4). |
| `ZQ_THROTTLE_EMAIL_PER_15M` / `_PER_24H` | `3` / `10` | Silent per-email issue limits. |
| `ZQ_VERIFY_BACKOFF_THRESHOLD` / `_BASE_S` / `_CAP_S` | `5` / `30` / `900` | Verification backoff (DB-backed, holds across replicas). |
| `ZQ_LOGIN_CODE_TTL_S` / `_MAX_ATTEMPTS` / `ZQ_RESEND_COOLDOWN_S` | `600` / `5` / `60` | Login-code policy. |
| `ZQ_AUDIT_QUERY_MAX_WINDOW_DAYS` | `92` | Max audit query window. |
| `ZQ_RESOURCE_PROBE_TIMEOUT_S` | `3.0` | Probe timeout. |

## 3. Database

- Use **managed PostgreSQL 17** with automated backups + PITR. The platform stores the audit chain and all control-plane data — back it up like a system of record.
- **Run migrations as a one-shot step before/alongside rollout**, not inside every web replica's start command:
  ```bash
  cd backend && alembic upgrade head      # idempotent; Alembic holds a lock so it's safe if double-run
  ```
- **TLS to the database:** `create_async_engine` is called with no `connect_args`, so TLS must be expressed via the DSN your driver accepts, or by a one-line hardening edit in `backend/app/database.py`:
  ```python
  # backend/app/database.py — for verified TLS + a bounded pool in prod
  _engine = create_async_engine(
      settings.database_url,
      echo=settings.db_echo,
      pool_size=10, max_overflow=20, pool_pre_ping=True,
      connect_args={"ssl": "require"},   # or an ssl.SSLContext with your CA
  )
  ```
- Create the DB role with least privilege (it needs DML + DDL for migrations, or split into a migrator role and a runtime role).

## 4. Edge / reverse proxy (the critical security + same-origin boundary)

In production there is **no CORS** and the session cookie is `Secure`, `SameSite=Lax`, scoped to `/api/v1/auth`. Therefore the SPA and API **must be served same-origin over HTTPS**. The generated client calls **relative `/api/...`** URLs, so a same-origin deployment needs **no frontend API-URL configuration**.

Terminate TLS at a reverse proxy / load balancer and:

1. Serve the built SPA (`frontend/dist`) as static files with **history-mode fallback** to `index.html`.
2. Proxy `/api/` to the backend, **forwarding the real client IP**.
3. **Block `/internal/v1/` entirely** — it is the service plane, guarded only by a shared token and not used by any first-party browser client.

Example nginx:

```nginx
server {
  listen 443 ssl http2;
  server_name app.yourco.com;
  # ssl_certificate / ssl_certificate_key ...

  root /srv/zqomni/dist;          # frontend `npm run build` output

  location / {                    # SPA history-mode fallback
    try_files $uri $uri/ /index.html;
  }

  location /api/ {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location /internal/ { return 404; }   # never expose the service plane
}
```

**Make the IP throttle (`T1`) work:** behind a proxy, every request appears to come from the proxy unless the app trusts forwarded headers. Start uvicorn with `--proxy-headers --forwarded-allow-ips="<proxy CIDR>"` so `request.client.host` reflects the true client. Without this, the per-IP login-code limit collapses onto the proxy IP.

## 5. Building and running each tier (production, not the dev Dockerfiles)

**Backend** — drop `--reload`, run multiple workers, don't migrate inside the web container:

```bash
# one-shot migrate job
alembic upgrade head
# web tier
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --workers 4 --proxy-headers --forwarded-allow-ips="10.0.0.0/8"
```
(`uvicorn[standard]` is already a dependency; no gunicorn needed.)

**Frontend** — the dev Dockerfile runs the Vite dev server; production ships static files. Build, then serve `dist/` from the same origin as `/api` (the nginx block above):

```bash
cd frontend
npm ci
npm run generate:api     # only if the backend OpenAPI changed; commits the SSOT client
npm run build            # → frontend/dist  (vue-tsc type-check + vite build)
```

A production multi-stage frontend image (replaces the dev `frontend/Dockerfile` for deploy):

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf   # the §4 server block
```

## 6. Scaling and the in-process state (read before running >1 replica)

For correctness, in-process caches and jobs matter. The code is structured so these can move to Redis later (`backend/app/core/cache.py` documents the swap point), but **as shipped they are per-process**:

- **Permission / introspection caches** are per-replica, and cache invalidation on a role/user/tenant change happens **in-process** — it does **not** propagate to other replicas. A changed grant is therefore honored everywhere within **`ZQ_INTROSPECTION_CACHE_TTL_S` (60s)** by bounded staleness (this matches the FDD's 60s backstop). Options: **(a)** start single-replica, **(b)** accept ≤60s propagation, or **(c)** wire Redis for strict cross-replica invalidation.
- **Throttle counters `T1`/`T2`** (per-IP, per-email issue limits) are per-replica → effective limits loosen ~N× with N replicas. The **security-critical limits `T3` (per-code attempts) and `T4` (verification backoff) are database-backed** and hold globally.
- **Sweepers** (code/session expiry, idempotency purge, binding-health probe) run as in-process loops **in every worker/replica that has `ZQ_SWEEPERS_ENABLED=true`**. Recommended topology: run the web tier with **`ZQ_SWEEPERS_ENABLED=false`**, and run **one** separate single-process "jobs" instance with `ZQ_SWEEPERS_ENABLED=true`.
- **First rollout:** deploy **single-replica / single-worker first** so the bootstrap admin and first-run state settle, then scale out. Concurrent cold starts can race on the unique admin-email insert.

## 7. Known operational gaps (be aware before go-live)

These are honest limitations of the in-scope build, each with a mitigation:

- **Audit partition maintenance is not automated.** The audit table is monthly-range-partitioned with a `DEFAULT` partition; the FDD's `audit-archiver` (monthly partition creation + WORM export + retention) is part of the out-of-scope service layer. As shipped, all events accumulate in `events_default` — functionally correct, but no partition pruning or automated retention. Mitigation: periodically `CREATE TABLE ... PARTITION OF audit.events FOR VALUES FROM ... TO ...` per month, or implement the archiver before audit volume is large.
- **Logical-resource probe skips TLS verification** (`verify=False` in `app/services/probes.py`) — a dev convenience. If you enable `ZQ_RESOURCE_PROBE_ENABLED` against TLS endpoints with untrusted certs, tighten this to verify against your CA.
- **Application logs are plain text to stdout** (`logging.basicConfig`), not the structured JSON the FDD describes. Ship stdout to your log stack; add a JSON formatter if you need structured fields. Login codes, session tokens, and credentials are already never logged.
- **`/healthz` is liveness-only** (returns `{"status":"ok"}`, no DB check). Use it for liveness; for readiness add a DB ping or gate on a successful migration.
- **Email is the only login channel** (no SSO/passwords by design, DA-03). If the SMTP relay is down, no one can sign in — monitor mail delivery.

## 8. Go-live checklist

- [ ] `ZQ_ENVIRONMENT=prod`
- [ ] All four secrets (§1) generated, stored in a secret manager, and **`ZQ_VAULT_KEY` backed up**
- [ ] `ZQ_DATABASE_URL` → managed Postgres 17 with TLS + backups; `alembic upgrade head` run as a one-shot job
- [ ] `ZQ_INITIAL_ADMIN_EMAIL` set to a real admin on a routable domain; confirm you can receive its login code
- [ ] SMTP configured and a test code delivered end-to-end; `ZQ_SMTP_FROM` SPF/DKIM-aligned
- [ ] `ZQ_ALLOWED_EMAIL_DOMAINS` locked to your corporate domain(s)
- [ ] HTTPS terminated; SPA + `/api` served **same-origin**; `/internal/v1` blocked at the edge
- [ ] uvicorn started with `--proxy-headers --forwarded-allow-ips=<proxy CIDR>` (real client IPs for throttling)
- [ ] Sweepers on exactly one instance (`ZQ_SWEEPERS_ENABLED=false` on web replicas, `true` on one jobs instance)
- [ ] First deploy single-replica, verified, then scaled; cross-replica permission staleness (≤60s) accepted or Redis wired
- [ ] Backups, log shipping, and uptime/health monitoring in place
