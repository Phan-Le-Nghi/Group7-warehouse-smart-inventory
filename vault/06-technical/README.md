# Technical Foundation — Canonical Index

## Status and authority

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Thư mục này là nguồn canonical cho các technical decisions đã được human review. Product requirements, Business Rules và Acceptance Criteria vẫn do các artifact product canonical quản lý; technical documentation không được thay đổi hoặc mở rộng chúng.

Application scaffold và first vertical slice `US-PUT-001` tại `apps/` và `.github/workflows/ci.yml` đã completed, được human review và được GitHub Actions xác minh bằng PostgreSQL 18 backend checks, frontend checks và Playwright React → FastAPI → PostgreSQL 18 E2E. Không claim local Docker/PostgreSQL pass. `DEC-031` approve PostgreSQL-backed server-side session authentication và DB-based role resolution; `DEC-032` approve Render cho staging/demo. Cả hai là `APPROVED DESIGN`, chưa được implement hoặc verify; long-term production deployment vẫn `TBD`.

## Approved foundation

- Frontend: React, TypeScript, Vite, npm.
- Backend: Python 3.13, FastAPI, uv, pytest.
- Database/runtime: PostgreSQL 18, Docker.
- Persistence tooling: SQLAlchemy 2, Alembic.
- E2E: Playwright.
- Architecture: modular monolith với một frontend, một backend API và một PostgreSQL database; không microservices, CQRS, event bus hoặc generic workflow engine.

Decision trace: `DEC-020` đến `DEC-023`, `DEC-031` và `DEC-032` tại [`../08-decisions/decision-log.md`](../08-decisions/decision-log.md).

## Canonical artifacts

| Artifact | Status | Purpose |
|---|---|---|
| [`architecture.md`](architecture.md) | HUMAN APPROVED FOUNDATION + AUTH/STAGING DESIGN | Application boundaries, approved session-auth design và Render staging/demo topology; implementation status kept explicit |
| [`data-model.md`](data-model.md) | HUMAN APPROVED FOUNDATION / conceptual portions noted | Inventory authority, conceptual MVP model, approved conceptual auth entities và Putaway slice model |
| [`api-contract.md`](api-contract.md) | AUTH BASELINE APPROVED / OTHER CONTRACTS PROPOSED | Approved auth routes and HTTP semantics; proposed MVP route map và detailed `US-PUT-001` contract |
| [`adrs/ADR-001-location-stock-authoritative.md`](adrs/ADR-001-location-stock-authoritative.md) | ACCEPTED | Per-location stock authority và derived Warehouse total |
| [`adrs/ADR-002-transactional-stock-consistency.md`](adrs/ADR-002-transactional-stock-consistency.md) | ACCEPTED | Transactional stock consistency và non-negative guard |
| [`adrs/ADR-003-receive-putaway-stock-posting.md`](adrs/ADR-003-receive-putaway-stock-posting.md) | ACCEPTED | Receive records actual quantity; Putaway performs initial posting |
| [`story-specs/US-PUT-001.md`](story-specs/US-PUT-001.md) | IMPLEMENTATION COMPLETED / CI VERIFIED | First vertical slice mapping and test evidence; no canonical AC changes |

## Preserved open boundaries

- `OQ-012`: UOM, decimal quantity, conversion behavior và precision/scale remain open. Round 1 uses integer units only as a vertical-slice technical simplification.
- `OQ-013`: Receive completion/handoff, Putaway exceptions/downstream handoff và other lifecycle details remain open.
- `OQ-014`: partial Putaway remains open. The full-quantity happy-path fixture is not a rule prohibiting partial Putaway.
- Exact authentication SQL/index/cookie/session-lifetime details remain implementation-spec work; auth implementation is not claimed.
- Render is approved only for staging/demo; long-term production deployment remains `TBD`.
- Adjust representation, attachment storage, advanced pagination/filtering and unresolved NFR targets remain `TBD`.

