# Warehouse & Smart Inventory Management — Implemented Vertical Slices

This directory contains the runnable `US-PUT-001`, `US-REC-001`, and
`US-PICK-001` worktree slices from React through FastAPI persistence.

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
uv run --env-file ../.env python -m warehouse_api.demo_data_seed
uv run --env-file ../.env uvicorn warehouse_api.main:app --reload
```

The demo data seed is idempotent and creates the four demo users, the canonical
`MAIN` Warehouse, `BACKROOM` and `SALES_SHELF`, `DEMO-SKU-001`, and one recorded
Receive line ready for Putaway. It creates no initial stock; Putaway performs
the initial location posting. The seed validates existing canonical rows and
fails instead of overwriting conflicts or resetting operational effects. Clear
`DEMO_USER_PASSWORD` from the shell after seeding. The older
`warehouse_api.demo_seed` command remains the users-only seed. Expired or
revoked sessions older than seven days can be removed explicitly with
`uv run --env-file ../.env python -m warehouse_api.auth_service`; the
application does not schedule cleanup automatically.

`APP_ENV` defaults to `development`, where local HTTP uses
`COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax`. Staging and production fail
startup unless `DATABASE_URL`, `CORS_ORIGINS`, `COOKIE_SECURE=true`, and
`COOKIE_SAMESITE=lax` satisfy the approved topology; their PostgreSQL URL must
include `sslmode=require`. The production environment refuses the demo seed.

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
the explicit Putaway context at `/`; `VITE_RECEIVE_ID` supplies the prepared
Receive context at `/receive`. The two screens remain separate and neither
creates an automatic Receive-to-Putaway handoff.

For the canonical demo dataset, set
`VITE_RECEIVE_LINE_ID=daf594b9-9c1e-51ec-adf0-0055cb3a8ff3` and
`VITE_RECEIVE_ID=e34f5e8e-4b3a-55a1-9485-d411a1ede3a8` at Vercel build time.
The Receive ID is the separate prepared, unrecorded staging smoke context. The
Putaway line still belongs to the original recorded demo Receive, so Receive
smoke recording cannot change the existing Putaway evidence.

Prepared Pick requests are opened at `/pick/{pick_id}`. The Pick ID comes from
the URL; the application does not create Pick requests. Partial Picks require
a second explicit confirmation in the UI before `POST /api/v1/picks` is sent.

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

The Playwright setup supplies `APP_ENV=test` to its child backend processes.
Do not invoke `warehouse_api.test_seed` against shared staging or production
data.

## Deployment foundation

The approved staging/demo foundation is documented in
[`../docs/06-technical/DEPLOYMENT.md`](../docs/06-technical/DEPLOYMENT.md), with
the complete variable matrix in
[`../docs/06-technical/ENVIRONMENT.md`](../docs/06-technical/ENVIRONMENT.md).
These are setup instructions only; no cloud deployment is claimed.

## Scope boundary

Authentication and `US-PUT-001` are merged implementation baselines. `US-REC-001`
and `US-PICK-001` are implemented in the worktree pending human diff review and
CI evidence. Test actor
injection exists only through FastAPI dependency overrides in automated tests;
there is no runtime actor environment switch. Human-confirmed merged-PR evidence
records backend, frontend, and browser E2E CI checks as `PASS` on PostgreSQL 18.
No local PostgreSQL, Docker, or browser E2E pass is claimed for the Pick slice.

`DEC-034/035` approve a staging/demo design with a Vercel React/Vite frontend,
a same-origin `/api/*` rewrite to the Render FastAPI backend, and Supabase
PostgreSQL 17. The deployment foundation is implemented in the worktree pending
human review, but no deployment has been performed. Staging HTTPS cookie
behavior and PostgreSQL 17 release evidence remain pending;
long-term production deployment remains `TBD`. `OQ-012`, `OQ-013`, and
`OQ-014` remain open.

Auth evidence status:

- `APPROVED DESIGN`: `DEC-031` and exact implementation spec `DEC-033`.
- `MERGED / CI VERIFIED`: backend, frontend, and browser E2E checks passed on
  the merged PR according to human-confirmed evidence.
- `NOT YET VERIFIED`: public staging HTTPS cookie behavior and Supabase
  PostgreSQL 17 compatibility in the release environment.
