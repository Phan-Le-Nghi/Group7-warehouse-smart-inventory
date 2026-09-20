# Warehouse & Smart Inventory Management — US-PUT-001 Vertical Slice

This directory contains the runnable first vertical slice for `US-PUT-001`,
from React through FastAPI and PostgreSQL persistence.

## Prerequisites

- Node.js 24 and npm
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker with Docker Compose (for local PostgreSQL)

## Environment

Create a local environment file from the committed placeholder values:

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by Git. The example credentials are for local development
only. Do not reuse them in a shared or production environment.

## PostgreSQL and backend

Start PostgreSQL from `apps/docker`, then apply the explicit migrations. Demo
accounts are created only by the explicit seed command and require one password
from the environment; never store that password in `.env.example` or source
control:

```powershell
docker compose --env-file ../.env up -d
Set-Location ../backend
uv sync --locked
uv run --env-file ../.env alembic upgrade head
$env:DEMO_USER_PASSWORD = Read-Host -AsSecureString | ConvertFrom-SecureString -AsPlainText
uv run --env-file ../.env python -m warehouse_api.demo_seed
uv run --env-file ../.env uvicorn warehouse_api.main:app --reload
```

The demo seed is idempotent and creates `demo.warehouse_staff`, `demo.manager`,
`demo.purchasing`, and `demo.admin`. Clear `DEMO_USER_PASSWORD` from the shell
after seeding. Expired or revoked sessions older than seven days can be removed
explicitly with `uv run --env-file ../.env python -m warehouse_api.auth_service`;
the application does not schedule cleanup automatically.

Local HTTP uses `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax`. Staging and
production must set `COOKIE_SECURE=true`; `COOKIE_SAMESITE` and `CORS_ORIGINS`
must match the approved deployment topology. `COOKIE_SAMESITE=none` is rejected
unless Secure is enabled and activates strict Origin plus JSON mutation checks.
The staging smoke/release checklist must inspect the issued session cookie and
verify the `Secure` attribute; the application does not infer the environment
or automatically promote `COOKIE_SECURE` for staging.

The API is available at `http://localhost:8000`. Importing the application does
not create tables or run migrations.

Backend checks:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Without `TEST_DATABASE_URL`, pytest uses SQLite for component-level feedback.
Set that variable to a real PostgreSQL test database for PostgreSQL evidence.

## Frontend

`VITE_API_BASE_URL` selects the FastAPI origin. `VITE_RECEIVE_LINE_ID` supplies
the explicit Putaway context without inventing an automatic Receive handoff.

```powershell
Set-Location frontend
npm ci
npm run dev
```

Frontend checks:

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

The Playwright tests refuse to run without a real PostgreSQL URL. They generate
a test password at runtime, migrate the database, reset the test-only fixture,
sign in through the real session API, and start FastAPI and Vite:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://warehouse_dev:warehouse_dev_only@localhost:5432/warehouse"
npm run test:e2e
```

## Scope boundary

Authentication and `US-PUT-001` are merged implementation baselines. Test actor
injection exists only through FastAPI dependency overrides in automated tests;
there is no runtime actor environment switch. Human-confirmed merged-PR evidence
records backend, frontend, and browser E2E CI checks as `PASS` on PostgreSQL 18.
No local Docker pass is claimed.

`DEC-034/035` approve a staging/demo design with a Vercel React/Vite frontend,
a same-origin `/api/*` rewrite to the Render FastAPI backend, and Supabase
PostgreSQL 17. That deployment has not been implemented or verified. Staging
HTTPS cookie behavior and PostgreSQL 17 release evidence remain pending;
long-term production deployment remains `TBD`. `OQ-012`, `OQ-013`, and
`OQ-014` remain open.

Auth evidence status:

- `APPROVED DESIGN`: `DEC-031` and exact implementation spec `DEC-033`.
- `MERGED / CI VERIFIED`: backend, frontend, and browser E2E checks passed on
  the merged PR according to human-confirmed evidence.
- `NOT YET VERIFIED`: public staging HTTPS cookie behavior and Supabase
  PostgreSQL 17 compatibility in the release environment.
