# Warehouse & Smart Inventory Management — Staging/Demo Application

This directory contains the runnable implementation of all nine canonical Must
stories from React through FastAPI and PostgreSQL persistence. Commit `664d207`
is the current staging/demo release candidate; this is not a production-grade
release claim.

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

`VITE_API_BASE_URL` selects the FastAPI origin. Authenticated users enter the
role-based Dashboard at `/`. Warehouse Staff use generic discovery pages at
`/receive`, `/putaway`, `/picks`, and `/transfers`; each page loads a read-only
backend queue/selector and creates the exact-context link after item selection.
Receive and Putaway remain separate and neither creates an automatic
Receive-to-Putaway handoff.

The frontend keeps its small manual route matcher. Generic Staff entry points
are `/receive`, `/putaway`, `/picks`, `/transfers`, `/audits/new`, and `/adjustments`; Manager entry points are
`/transfers/history`, `/audit-discrepancies`, and `/adjustment-decisions`.
The Staff Adjust queue discovers manager-confirmed mismatch rechecks and links
to `/adjustments/{audit_recheck_id}` without exposing or hard-coding UUIDs.
Pick and Transfer details retain exact-context URLs, but users reach them from
the actionable Pick queue and current-stock Transfer selector without entering IDs.
Purchasing and Admin receive a neutral Dashboard state rather than invented
actions. Unknown frontend routes render a Page not found state.

The application does not create Receive or Pick requests. Prepared contexts must
already exist in backend data. Partial Picks require a second explicit
confirmation in the UI before `POST /api/v1/picks` is sent.

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
The current staging/demo deployment uses Vercel → Render → Supabase. Deployment
status and the human-performed smoke evidence are recorded in
[`../docs/07-release/STAGING-DEMO-RELEASE-CHECKLIST.md`](../docs/07-release/STAGING-DEMO-RELEASE-CHECKLIST.md).

## Scope boundary

All nine canonical Must stories and authentication are merged at release
candidate `664d207`. Test actor
injection exists only through FastAPI dependency overrides in automated tests;
there is no runtime actor environment switch. Human-confirmed merged-PR evidence
records backend, frontend, and browser E2E CI checks as `PASS` on PostgreSQL 18.
Those earlier CI results are historical evidence; exact GitHub Actions run
URL/results for `664d207` are **NOT RECORDED** and are not inferred.

`DEC-034/035` approve a staging/demo design with a Vercel React/Vite frontend,
a same-origin `/api/*` rewrite to the Render FastAPI backend, and Supabase
PostgreSQL 17. The topology is deployed for staging/demo at the URLs documented
in the release checklist. Human-performed smoke verified `/health`, `/ready`,
SPA deep-link refresh, authentication/session/logout and the nine-story workflow
evidence. Exact CI runs for `664d207`, a separate cookie-attribute inspection,
and an `alembic current` transcript are not recorded. Long-term production
deployment remains `TBD`; `OQ-012`, the unresolved parts of `OQ-013`, and
`OQ-014` remain open.

Auth evidence status:

- `APPROVED DESIGN`: `DEC-031` and exact implementation spec `DEC-033`.
- `MERGED / CI VERIFIED`: backend, frontend, and browser E2E checks passed on
  the merged PR according to human-confirmed evidence.
- `HUMAN STAGING SMOKE PASS`: login, session persistence and logout through the
  Vercel same-origin `/api/*` path; `/ready` confirmed database reachability.
- `NOT RECORDED`: exact cookie-attribute inspection, exact PostgreSQL version
  query output and GitHub Actions run URL/results for `664d207`.
