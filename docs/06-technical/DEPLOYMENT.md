# Staging/Demo Deployment Guide

Status: **DEPLOYED AND HUMAN-VERIFIED FOR STAGING/DEMO** at commit `664d207`.
This guide does not claim production readiness or production-grade availability.

- Frontend: <https://group7-warehouse-smart-inventory.vercel.app>
- Backend: <https://group7-warehouse-smart-inventory.onrender.com>
- Release evidence: [`../07-release/STAGING-DEMO-RELEASE-CHECKLIST.md`](../07-release/STAGING-DEMO-RELEASE-CHECKLIST.md)

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
key. The deployed `/ready` PASS and persisted staging workflow results verify
database reachability and application persistence through the real staging
topology. The exact Supabase host/connection mode, a direct PostgreSQL version
query transcript and credentials are intentionally not documented.

Do not run `warehouse_api.test_seed` against Supabase staging. It is destructive,
requires both `APP_ENV=test` and `TEST_DATABASE_URL`, and is for disposable test
databases only.

## 2. Single Alembic release runner

Current repository migration head: `20260927_0009` (`adjustment_decision`).
Alembic is the only migration source-of-truth. The staging runtime and database
were usable for the verified workflows, but an exact `alembic current`
transcript and named migration-runner record were not supplied for this pass;
they remain **NOT RECORDED**, not inferred.

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

The release-candidate staging fixtures were created with
`warehouse_api.demo_data_seed`. Human confirmation explicitly records that
`warehouse_api.test_seed` was not used. This is operational evidence for this
staging/demo release, not authorization to seed production.

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

Authenticated frontend navigation starts at the role-based Dashboard on `/`.
The prepared Putaway smoke context is opened explicitly at `/putaway`; Receive
remains `/receive`. Manager master pages are `/transfers/history`,
`/audit-discrepancies`, and `/adjustment-decisions`. Exact-context Pick,
Transfer execution, and Staff Adjust routes keep their existing path IDs and
are not exposed as generic Dashboard actions.

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

Checked items below are **human-performed staging smoke evidence** for commit
`664d207`; they are not automated CI results. The exact GitHub Actions run
URL/results for this commit are **NOT RECORDED**.

- [x] Warm `GET https://group7-warehouse-smart-inventory.onrender.com/health` — PASS.
- [x] Call `GET https://group7-warehouse-smart-inventory.onrender.com/ready` — PASS.
- [x] Load the Vercel HTTPS frontend and complete login, session persistence and logout — PASS.
- [ ] Confirm the request URL is Vercel `/api/v1/auth/login`, not direct Render.
- [ ] Inspect `warehouse_session`: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, no `Domain`.
- [ ] Verify `GET /api/v1/auth/me`, a representative `401`, and role-based `403`.
- [ ] Verify `/` loads the role-based Dashboard for all four demo roles without
      loading or mutating business context.
- [ ] Verify Warehouse Staff sees only configured Receive/Putaway and New Audit
      actions; Manager sees only Transfer History, Audit Discrepancies, and
      Adjust Decisions; Purchasing/Admin show the neutral current-MVP state.
- [ ] Refresh `/`, `/putaway`, and representative Manager/exact-context deep
      links; verify an unknown frontend path renders Page not found.
- [ ] Verify Manager direct `/putaway` and `/audits/new` navigation receives the
      backend-authoritative `403`, without issuing a mutation request.
- [x] Complete the multi-location Pick: Backroom 6 + Sales Shelf 4, picked 10/10,
      Warehouse total 0 — PASS.
- [x] Refresh representative Vercel SPA/deep links; the SPA remains available — PASS.
- [x] Verify Staff flows for Receive, Putaway, Pick, Transfer, Audit and Adjust request — PASS.
- [x] Verify Manager Transfer History, Audit recheck and Adjust approve/apply flows — PASS.
- [x] Reload Transfer History without stock mutation or duplicate Transfer — PASS.
- [x] Reload an applied Adjust without applying it twice — PASS.
- [ ] Confirm logs and responses contain no database URL, password, or cookie token.

The full quantities, statuses and no-effect checks are recorded in the release
checklist rather than duplicated in this operational runbook.

## 8. Rollback

Prefer a forward fix. Before a risky migration, use the provider's approved
backup/restore capability and verify its retention for the real project. If an
application release fails but the schema is backward-compatible, roll the web
artifact back while keeping the migrated schema. Do not run arbitrary Alembic
downgrades against shared data and never downgrade a destructive migration
without a reviewed recovery plan and verified backup.
