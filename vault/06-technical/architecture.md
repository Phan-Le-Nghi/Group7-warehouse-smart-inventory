# Technical Architecture — Warehouse & Smart Inventory Management

## Status

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Architecture and tooling are approved by `DEC-020`. Authentication/authorization design is approved by `DEC-031`, and Render staging/demo topology is approved by `DEC-032`. The `US-PUT-001` vertical slice exists as a downstream implementation artifact. Authentication and deployment described below remain design-only and are not implementation claims.

## System shape

```text
Browser
  -> React + TypeScript + Vite frontend
  -> HTTP/JSON
  -> FastAPI backend API
  -> application service / transaction boundary
  -> SQLAlchemy 2 persistence
  -> PostgreSQL 18
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
| Actor/auth dependency | Resolve session cookie → PostgreSQL session → active user → current database role, then enforce canonical role outcomes | Server-side session design is approved but not implemented; test actor injection is restricted to automated tests |
| Application service | Orchestrate the use case, enforce approved rules and own the transaction boundary | Does not invent unresolved workflow lifecycle |
| Persistence | Use SQLAlchemy 2 for queries, row locks and writes | Does not contain UI/navigation behavior |
| PostgreSQL | Persist authoritative state and enforce FK, uniqueness and `quantity >= 0` constraints | Warehouse total is not persisted |
| Alembic | Version database schema changes | Migration implementation is not created in this documentation phase |

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

The approved baseline does not add JWT, refresh tokens, self-registration, password reset, social login, OAuth, Keycloak or another external identity provider. Exact SQL types/indexes/constraints, session lifetime and the topology-specific `SameSite` value remain implementation-spec details.

## Approved staging/demo deployment design

`DEC-032` approves Render only for staging/demo:

```text
React frontend -> public HTTPS Render Static Site
FastAPI backend -> public HTTPS Render Web Service
PostgreSQL -> Render managed PostgreSQL
```

The environment must expose public frontend/backend URLs, keep secrets outside the repository, apply Alembic migrations, expose `/health`, pass a database readiness check before any release-ready claim, create deterministic idempotent demo accounts from external secrets and pass a smoke test. The backend production command must not use `--reload`. CORS allows only the approved staging frontend origin and must enable credential-compatible configuration when required by session cookies. This topology is not implemented or verified yet; the long-term production target remains `TBD`.

## Configuration and delivery boundaries

- Runtime configuration must come from environment variables; repository examples must contain placeholders only.
- Exact lint/format packages and version pins remain implementation-tooling choices to review when scaffolding is authorized.
- Existing CI runs frontend/backend checks and the Putaway Playwright slice; no staging deployment job is implemented.
- Production authentication design and the Render staging/demo target are approved by `DEC-031/032`, but implementation and verification remain pending. Long-term production deployment remains `TBD`.
- Quantitative NFR targets remain open at `OQ-033`.

## Decision trace

- `DEC-020`: approved stack, persistence tooling and modular-monolith shape.
- `DEC-021` / `ADR-001`: authoritative per-location stock and derived Warehouse total.
- `DEC-022` / `ADR-002`: transactions and non-negative stock.
- `DEC-023` / `ADR-003`: Receive records actual quantity; Putaway performs initial stock posting.
- `DEC-031`: PostgreSQL-backed server-side session authentication and database-role authorization baseline.
- `DEC-032`: Render staging/demo topology and minimum release-environment requirements; long-term production target remains `TBD`.

