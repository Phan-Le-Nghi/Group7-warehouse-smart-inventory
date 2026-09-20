# Technical Architecture — Warehouse & Smart Inventory Management

## Status

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Architecture and tooling are approved by `DEC-020`. Authentication/authorization design is approved by `DEC-031`, exact auth implementation details by `DEC-033`, and the revised Vercel → Render → Supabase staging/demo topology by `DEC-034/035`. The `US-PUT-001` vertical slice and auth implementation are merged implementation artifacts; human-confirmed merged-PR evidence records backend, frontend and browser E2E CI checks as `PASS`. Staging HTTPS cookie behavior and the Vercel/Render/Supabase deployment remain unverified because deployment has not been performed.

## System shape

```text
Browser
  -> React + TypeScript + Vite frontend
  -> HTTP/JSON
  -> FastAPI backend API
  -> application service / transaction boundary
  -> SQLAlchemy 2 persistence
  -> PostgreSQL 17+
```

The system is a modular monolith with:

- one frontend;
- one backend API;
- one PostgreSQL database;
- Docker for local database runtime;
- Alembic for schema migrations;
- pytest for backend tests and Playwright for end-to-end tests.

The foundation explicitly excludes microservices, CQRS, an event bus and a generic workflow engine.

## Layer responsibilities

| Layer | Responsibility | Boundary |
|---|---|---|
| Frontend | Present canonical UI states, collect input and call HTTP endpoints | Does not own or calculate authoritative stock |
| FastAPI route/schema | Parse HTTP, validate request shape, call actor/auth dependency and map application results to HTTP | Does not contain stock mutation logic |
| Actor/auth dependency | Resolve session cookie → PostgreSQL session → active user → current database role, then enforce canonical role outcomes | Implementation is merged and CI-verified; staging HTTPS cookie behavior remains unverified and test actor injection is restricted to automated tests |
| Application service | Orchestrate the use case, enforce approved rules and own the transaction boundary | Does not invent unresolved workflow lifecycle |
| Persistence | Use SQLAlchemy 2 for queries, row locks and writes | Does not contain UI/navigation behavior |
| PostgreSQL | Persist authoritative state and enforce FK, uniqueness and `quantity >= 0` constraints | Warehouse total is not persisted |
| Alembic | Version database schema changes | Remains migration source-of-truth; each release has exactly one migration runner |

## Request flow for a stock-changing command

1. The frontend sends an HTTP/JSON command.
2. FastAPI validates request shape and resolves the actor through the auth dependency boundary.
3. The application service starts a PostgreSQL transaction.
4. Persistence locks affected rows when concurrent commands could conflict.
5. The service validates canonical invariants and operation-specific technical guards.
6. The operational record and stock effect are written in the same transaction.
7. On success the transaction commits; on failure all effects roll back.
8. The response reports the committed result; Warehouse total, when returned, is derived from location balances.

## Module boundaries

Initial backend modules should follow business capabilities without becoming separate services: catalog/inventory, Receive, Putaway, Pick, Transfer, Audit and Adjust. Shared infrastructure is limited to database/session, configuration, actor/auth boundary and error mapping.

The first implemented module is intended to be `US-PUT-001`. Other modules remain conceptual until their technical contracts are reviewed.

## Approved authentication and authorization design

`DEC-031` approves PostgreSQL-backed server-side sessions for the production authentication baseline:

- a random session ID is sent only through a browser cookie and only its hash is stored in `auth_sessions`;
- the cookie is `HttpOnly`, uses `Path=/`, is `Secure` in staging/production and uses a `SameSite` value compatible with the approved deployment topology;
- passwords are stored only as Argon2id hashes; plaintext and demo passwords must not be stored in the repository, Vault or CI logs;
- current actor resolution uses the session record, active user and the user's current database role; frontend-supplied role data is never authoritative;
- protected routes use reusable authorization dependencies/policies for `WAREHOUSE_STAFF`, `MANAGER`, `PURCHASING` and `ADMIN`, preserving the permissions approved by `DEC-017`;
- missing, invalid, expired or revoked sessions and inactive users map to `401`; authenticated actors without the required permission map to `403`;
- test actor injection is permitted only in automated tests.
- staging/demo has at least one account for each approved role; the seed is idempotent and passwords come from environment/platform secrets or are generated outside source control.

The approved baseline does not add JWT, refresh tokens, self-registration, password reset, social login, OAuth, Keycloak or another external identity provider. `DEC-033` fixes the schema, 8-hour absolute lifetime, `warehouse_session` cookie and configurable topology-specific cookie/CORS settings. It does not hardcode `SameSite=None`; cross-site mode requires strict Origin validation and JSON-only mutations.

## Approved staging/demo deployment design

`DEC-034` supersedes only the frontend and database provider clauses of `DEC-032`. The approved staging/demo topology is:

```text
Browser
  -> public HTTPS Vercel React/Vite frontend
  -> same-origin /api/* rewrite
  -> public HTTPS Render FastAPI backend
  -> TLS connection
  -> Supabase PostgreSQL 17
```

The frontend calls relative `/api/...` paths and does not expose the Render backend URL in the browser bundle when the rewrite is used. Staging auth uses the existing host-only `warehouse_session` cookie with `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, `COOKIE_SECURE=true` and `COOKIE_SAMESITE=lax`. Direct Vercel → Render cross-site calls and hardcoded `SameSite=None` are not the baseline.

Supabase is only hosted PostgreSQL. FastAPI remains the application/backend authority and SQLAlchemy + Alembic remain the persistence/migration authority. Supabase Auth, browser SDK as a business-data path, Data API, JWT and external identity providers are excluded from this topology.

The retained `DEC-032` requirements are staging/demo-only scope, public HTTPS, secrets outside the repository, explicit Alembic migration, `/health`, database readiness before any release-ready claim, deterministic idempotent demo seed, smoke test and a backend production command without `--reload`. Render Free is permitted; its cold start must be handled by warm-up/rehearsal before a demo and is not production-grade availability evidence.

`DEC-035` approves Supabase PostgreSQL 17 for staging/demo and PostgreSQL 17+ application/migration compatibility. PostgreSQL 18 CI evidence remains useful compatibility evidence, but release requires PostgreSQL 17 verification matching staging and must not claim versions 17 and 18 are identical. `DATABASE_URL` comes from the real Supabase Dashboard/Connect value and requires TLS through `sslmode=require`; its exact host/mode and credentials are not documented or committed.

Alembic remains the migration source-of-truth. A release has exactly one migration runner: future preferred automation is GitHub Actions `workflow_dispatch` with a protected environment/secrets, while a named human operator may run the migration until that workflow exists. `alembic upgrade head` must not run on every application startup.

`/health` remains liveness. A future `/ready` endpoint must perform at least `SELECT 1`; it is not implemented. The future production-safe idempotent demo seed may create missing records and safely reconcile deterministic demo references, but must not reset operational state, arbitrarily delete staging records or reuse destructive test-seed behavior. Exact demo IDs/data remain an implementation-task decision.

Release smoke must verify frontend HTTPS, backend health, database readiness, login, cookie flags, `/auth/me`, `401`, `403`, Putaway, idempotency, logout and absence of leaked secrets. The topology remains `DESIGN / NOT DEPLOYED`; long-term production remains `TBD`.

## Configuration and delivery boundaries

- Runtime configuration must come from environment variables; repository examples must contain placeholders only.
- Exact lint/format packages and version pins remain implementation-tooling choices to review when scaffolding is authorized.
- Existing CI runs frontend/backend checks and the Putaway/auth Playwright slice; human-confirmed merged-PR evidence records backend, frontend and E2E checks as `PASS`. It does not provide staging PostgreSQL 17 or deployed HTTPS-cookie evidence.
- Authentication design/spec are approved by `DEC-031/033` and implementation is merged. The Vercel/Render/Supabase staging/demo topology is approved design only and long-term production deployment remains `TBD`.
- Quantitative NFR targets remain open at `OQ-033`.

## Decision trace

- `DEC-020`: approved stack, persistence tooling and modular-monolith shape.
- `DEC-021` / `ADR-001`: authoritative per-location stock and derived Warehouse total.
- `DEC-022` / `ADR-002`: transactions and non-negative stock.
- `DEC-023` / `ADR-003`: Receive records actual quantity; Putaway performs initial stock posting.
- `DEC-031`: PostgreSQL-backed server-side session authentication and database-role authorization baseline.
- `DEC-032`: retained minimum staging/demo release requirements; its Render frontend/database provider clauses are superseded by `DEC-034`.
- `DEC-033`: exact session-auth implementation contract; implementation is merged and CI-verified, while staging HTTPS-cookie behavior remains unverified.
- `DEC-034`: Vercel same-origin frontend rewrite → Render FastAPI → Supabase PostgreSQL staging/demo topology.
- `DEC-035`: Supabase PostgreSQL 17 staging target, PostgreSQL 17+ compatibility and single-runner Alembic policy.

