# Staging/Demo Deployment Guide

Status: implementation guide only. No Supabase project, Render service, Vercel
project, release, or live deployment has been created or verified.

This guide implements the approved `DEC-034/035` topology:

```text
Browser -> Vercel React/Vite -> same-origin /api/* -> Render FastAPI
        -> TLS -> Supabase PostgreSQL 17
```

Long-term production hosting remains `TBD`. The production validation mode is a
fail-closed safety boundary, not approval of these providers for production.

## 1. Supabase PostgreSQL 17

1. Create a staging/demo PostgreSQL 17 project in Supabase.
2. In Dashboard **Connect**, select the connection mode approved by the human
   operator for the real project and copy its connection URL. Direct,
   session-pooler, and transaction-pooler modes are not interchangeable
   assumptions and this repository does not choose one without the actual
   project information.
3. Store the URL only as Render's secret `DATABASE_URL`. Do not put it in Git,
   Vercel, Vault, documentation, or logs.
4. Use a SQLAlchemy URL beginning with `postgresql+psycopg://`. A Dashboard URL
   beginning `postgresql://` is accepted and normalized by the application.
5. Ensure the query contains `sslmode=require`. Staging startup and Alembic both
   fail closed without it.

The application uses ordinary SQLAlchemy 2 + psycopg connections and Alembic.
It does not use Supabase Auth, browser SDK, Data API, anon key, or service-role
key. Compatibility with the exact Supabase host and connection mode remains
**NOT VERIFIED LOCALLY** until a real project exists.

Do not run `warehouse_api.test_seed` against Supabase staging. It is destructive,
requires both `APP_ENV=test` and `TEST_DATABASE_URL`, and is for disposable test
databases only.

## 2. Single Alembic release runner

Current migration head: `20260927_0009` (`adjustment_decision`). Alembic is the
only migration source-of-truth.

Until protected `workflow_dispatch` automation is separately approved and
implemented, use one named human Release Operator:

1. Stop other release operators and confirm no migration command is running.
2. From repository directory `apps/backend`, load the same secret
   `DATABASE_URL` and staging settings used by Render.
3. Run exactly once:

   ```powershell
   $env:APP_ENV = "staging"
   $env:COOKIE_SECURE = "true"
   $env:COOKIE_SAMESITE = "lax"
   $env:CORS_ORIGINS = "https://<vercel-staging-origin>"
   $databaseUrl = Read-Host -AsSecureString "Supabase DATABASE_URL"
   $env:DATABASE_URL = [System.Net.NetworkCredential]::new("", $databaseUrl).Password
   uv run --no-sync alembic upgrade head
   uv run --no-sync alembic current
   ```

4. Require `alembic current` to report the expected head before starting or
   promoting the web service. Any non-zero exit stops the release; do not seed,
   start a replacement release, or mark readiness successful.
5. Clear `DATABASE_URL` and the temporary variable from the operator shell:
   `Remove-Item Env:DATABASE_URL; Remove-Variable databaseUrl`.

Never put `alembic upgrade head` in the Render web start command. Multiple web
instances must not race as migration runners.

## 3. Render FastAPI service

Create one Web Service only after human approval, with:

- Root directory: `apps/backend`
- Runtime: Python 3.13 (pinned by `apps/backend/.python-version`)
- Build command: `uv sync --locked --no-dev`
- Start command:

  ```text
  uv run --no-sync uvicorn warehouse_api.main:app --host 0.0.0.0 --port $PORT
  ```

The command uses Render's injected `$PORT`, binds all interfaces, imports the
existing `warehouse_api.main:app`, and does not use `--reload`.

Configure `APP_ENV=staging`, `DATABASE_URL`, `CORS_ORIGINS` (the exact Vercel
HTTPS origin), `COOKIE_SECURE=true`, and `COOKIE_SAMESITE=lax`. Configure
`DEMO_USER_PASSWORD` only for a controlled one-time staging seed; it is not a
web startup variable.

Use `/health` as liveness. It is intentionally DB-independent. Use `/ready` as
readiness; it executes `SELECT 1`, returns `200 {"status":"ready"}` when the DB
is reachable, and generic `503 {"status":"unavailable"}` otherwise.

Render Free cold start is accepted only for staging/demo. Warm `/health`, then
require `/ready` before a rehearsal; this is not production-availability proof.

## 4. Controlled demo seed

The demo data seed is idempotent and uses one externally supplied password. It
creates or reconciles the four approved role accounts, then creates or validates
the canonical Warehouse, two tracked locations, and separate Receive, Putaway,
and Pick smoke data. Receive creates no stock: Receive records actual quantity
and Putaway performs the initial location posting. The dedicated Pick smoke SKU
starts with 6 units in `BACKROOM` and 4 in `SALES_SHELF` for a request of 10.
Existing canonical conflicts fail the whole transaction instead of being
overwritten. Reruns do not change Putaway effects or a Pick's confirmation,
allocations, or current stock quantities.

After migrations, a named operator may run from `apps/backend`:

```powershell
$env:APP_ENV = "staging"
$demoPassword = Read-Host -AsSecureString "Temporary demo password"
$env:DEMO_USER_PASSWORD = [System.Net.NetworkCredential]::new("", $demoPassword).Password
uv run --no-sync python -m warehouse_api.demo_data_seed
Remove-Item Env:DEMO_USER_PASSWORD
Remove-Variable demoPassword
```

Do not invent or document a default password. Do not run this command
automatically at web startup. `APP_ENV=production` explicitly rejects the demo
seed. The users-only `warehouse_api.demo_seed` command remains available when
operational demo data is intentionally not required. Never use
`warehouse_api.test_seed` for staging/demo data.

## 5. Vercel React/Vite project

Create the project only after human approval, with:

- Root directory: `apps/frontend`
- Framework preset: Vite
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `RENDER_API_ORIGIN=https://<render-service-host>`
- Environment variable:
  `VITE_RECEIVE_LINE_ID=daf594b9-9c1e-51ec-adf0-0055cb3a8ff3`
- Environment variable:
  `VITE_RECEIVE_ID=e34f5e8e-4b3a-55a1-9485-d411a1ede3a8` (temporary prepared,
  unrecorded Receive smoke context)
- `VITE_API_BASE_URL`: unset

Use this staging deep link for the dedicated Pick smoke fixture:
`/pick/d88066ff-46b8-5722-ba29-b11cfa01816d`.

`frontend/vercel.mjs` validates `RENDER_API_ORIGIN` and generates routes in this
order:

1. `/api/:path*` proxies to the same path on Render.
2. Remaining non-file routes fall back to `/index.html` for the React SPA.

Vercel gives real filesystem output precedence, so built JS/CSS/assets remain
static files. The API rule precedes the SPA fallback, so API failures cannot be
turned into frontend HTML. The Render URL is server-side Vercel configuration,
not a `VITE_*` browser variable and is not hardcoded in source.

## 6. Session/cookie behavior

The browser calls relative `/api/...` with `credentials: include`. Through the
Vercel rewrite, login responses are same-origin to the browser, so the existing
host-only `warehouse_session` cookie remains scoped to the Vercel host with
`HttpOnly`, `Secure`, `SameSite=Lax`, and `Path=/`. HTTPS is mandatory.

The Render backend must allow the exact Vercel HTTPS origin in `CORS_ORIGINS`.
Do not switch to direct browser-to-Render calls or `SameSite=None` without a new
review of the approved topology and CSRF boundary.

## 7. Post-deploy smoke checklist

No item below is currently claimed as passed:

- [ ] Warm `GET <render-origin>/health`; expect `200` without DB dependency.
- [ ] Call `GET <render-origin>/ready`; expect `200` only after migration and DB access.
- [ ] Load the Vercel HTTPS frontend and log in with a controlled demo account.
- [ ] Confirm the request URL is Vercel `/api/v1/auth/login`, not direct Render.
- [ ] Inspect `warehouse_session`: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, no `Domain`.
- [ ] Verify `GET /api/v1/auth/me`, a representative `401`, and role-based `403`.
- [ ] Complete the multi-location Pick at
      `/pick/d88066ff-46b8-5722-ba29-b11cfa01816d`.
- [ ] Refresh `/audits/new`, `/audit-discrepancies`, `/adjustment-decisions`,
      `/transfers/history`, and representative `/pick/...`, `/transfer/...`,
      `/adjustments/...` deep links; expect the SPA rather than 404.
- [ ] Verify one approved Staff flow and one Manager review flow through `/api/*`.
- [ ] Verify a repeated idempotent operation does not duplicate its effect.
- [ ] Confirm logs and responses contain no database URL, password, or cookie token.

## 8. Rollback

Prefer a forward fix. Before a risky migration, use the provider's approved
backup/restore capability and verify its retention for the real project. If an
application release fails but the schema is backward-compatible, roll the web
artifact back while keeping the migrated schema. Do not run arbitrary Alembic
downgrades against shared data and never downgrade a destructive migration
without a reviewed recovery plan and verified backup.
