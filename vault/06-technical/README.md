# Technical Foundation — Canonical Index

## Status and authority

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Thư mục này là nguồn canonical cho các technical decisions đã được human review. Product requirements, Business Rules và Acceptance Criteria vẫn do các artifact product canonical quản lý; technical documentation không được thay đổi hoặc mở rộng chúng.

Application scaffold, first vertical slice `US-PUT-001` và auth implementation tại `apps/` đã merge, được human review và có human-confirmed merged-PR evidence rằng backend, frontend và Playwright E2E CI checks `PASS` trên PostgreSQL 18. `DEC-031/033` approve PostgreSQL-backed session authentication/design spec; `DEC-034/035` approve Vercel → Render → Supabase PostgreSQL 17 cho staging/demo. Deployment chưa được thực hiện; staging HTTPS cookie behavior và PostgreSQL 17 staging verification vẫn pending, còn long-term production deployment vẫn `TBD`.

Auth evidence được phân loại rõ: `APPROVED DESIGN` tại `DEC-031/033`; implementation là `MERGED / CI VERIFIED`; staging HTTPS cookie behavior là `NOT YET VERIFIED`; Vercel/Render/Supabase topology là `DESIGN / NOT DEPLOYED`.

## Approved foundation

- Frontend: React, TypeScript, Vite, npm.
- Backend: Python 3.13, FastAPI, uv, pytest.
- Database/runtime: PostgreSQL 17+ compatibility; PostgreSQL 18 local/CI baseline và Supabase PostgreSQL 17 staging target; Docker cho local runtime.
- Persistence tooling: SQLAlchemy 2, Alembic.
- E2E: Playwright.
- Architecture: modular monolith với một frontend, một backend API và một PostgreSQL database; không microservices, CQRS, event bus hoặc generic workflow engine.

Decision trace: `DEC-020` đến `DEC-023`, `DEC-031` đến `DEC-035` tại [`../08-decisions/decision-log.md`](../08-decisions/decision-log.md).

## Canonical artifacts

| Artifact | Status | Purpose |
|---|---|---|
| [`architecture.md`](architecture.md) | HUMAN APPROVED FOUNDATION + AUTH/STAGING DESIGN | Application boundaries, merged session-auth status và Vercel → Render → Supabase staging/demo topology; deployment status kept explicit |
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
- Exact authentication spec đã được approve tại `DEC-033`; implementation đã merge và CI pass, nhưng staging HTTPS cookie behavior chưa verify.
- Vercel frontend, Render FastAPI backend và Supabase PostgreSQL 17 được approve chỉ cho staging/demo; deployment chưa thực hiện và long-term production vẫn `TBD`.
- Adjust representation, attachment storage, advanced pagination/filtering and unresolved NFR targets remain `TBD`.

