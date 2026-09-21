# US-PICK-001 Technical Story Spec

## Status and authority

`IMPLEMENTATION-READY — HUMAN APPROVED AT DEC-037`

- Story: `US-PICK-001 — Thực hiện Pick từ tracked locations`
- Owner: Trương Huỳnh Thảo Ngân
- Canonical product story: [`../../04-product/stories/US-PICK-001.md`](../../04-product/stories/US-PICK-001.md)
- Technical approval: `DEC-037`
- This document defines the current implementation slice. It does not change the canonical Acceptance Criteria.
- Application implementation, migration, commit and push are outside this documentation task.

## Traceability

- Requirements: `REQ-002`, `REQ-003`, `CAND-REQ-003`, `CAND-REQ-006`, `CAND-REQ-010`, `CAND-REQ-011`.
- Business rules: `CAND-BR-003`, `CAND-BR-005`, `CAND-BR-006`, `CAND-BR-015`.
- Product decisions: `DEC-010`, `DEC-012`, `DEC-017`, `DEC-018`, `DEC-019`.
- Technical decisions: `DEC-020`, `DEC-021`, `DEC-022`, `DEC-025`, `DEC-031`, `DEC-033`, `DEC-035`, `DEC-037`.
- NFRs: `NFR-001`, `NFR-002`, `NFR-004`, `NFR-005`.
- Design: `PF-02`, `SCR-04`, `SCR-05`, `SCR-06`, and the human-reviewed P2 usability finding.
- Open boundaries: `OQ-012`, the future retry/cancel boundary in `OQ-013`, and `OQ-022`.
- Evidence classification: `EVD-006` through `EVD-009` are current-state context only. The approved Pick behavior is a HUMAN PRODUCT/TECHNICAL DECISION.

## Goal

Allow an authenticated Warehouse Staff actor to confirm one immutable result for a prepared/external single-SKU Pick request by explicitly allocating positive integer quantities from one or more tracked source locations. The command records either `FULLY_COMPLETED` or `PARTIAL_INSUFFICIENT`, decrements only the selected source balances, and preserves atomicity and non-negative per-location stock.

## Preconditions

- The Pick request already exists; request creation is outside the current story.
- The request belongs to the single MVP Warehouse and identifies one existing SKU.
- `requested_quantity` is a positive integer for this slice.
- `BACKROOM` and `SALES_SHELF` are the only tracked source-location codes.
- The actor is authenticated and has current database role `WAREHOUSE_STAFF`.
- A missing `StockBalance` row means no available stock. Pick does not create a missing balance row.
- The Pick request has not already been confirmed.

## Happy Path

1. Warehouse Staff loads `GET /api/v1/picks/context/{pick_id}`.
2. The UI displays SKU, requested quantity, current availability by tracked location and derived Warehouse total.
3. Warehouse Staff selects one or more source locations and explicitly enters a positive quantity for each source.
4. The UI displays picked, requested and remaining quantity.
5. For a partial result, the UI requires explicit confirmation that the Pick will remain not fully completed.
6. The client sends `POST /api/v1/picks` with `pick_id` and the explicit allocations.
7. The backend locks the Pick request, then locks all affected existing `StockBalance` rows in deterministic source-location order.
8. The backend re-reads stock after locking and validates the complete command before any write.
9. The backend inserts the allocation rows, records outcome/actor/time on the Pick request and decrements the selected source balances in one transaction.
10. The transaction commits and the response reports the immutable recorded result and derived stock values.

## Alternate / Error Paths

| Condition | Result | Data effect |
|---|---|---|
| Missing/invalid session or inactive user | `401` using the existing auth envelope | None |
| Authenticated actor is not Warehouse Staff | `403 FORBIDDEN` | None |
| Pick request does not exist | `404 PICK_NOT_FOUND` | None |
| Pick request is already confirmed | `409 PICK_ALREADY_RECORDED` | None; no second decrement |
| Empty allocations, zero picked total, non-integer or non-positive allocation | `422 INVALID_QUANTITY` or `422 INVALID_ALLOCATIONS` | None |
| Duplicate source location | `422 DUPLICATE_SOURCE_LOCATION` | None |
| Source is not a tracked location in the Pick warehouse | `422 INVALID_SOURCE_LOCATION` | None |
| Picked total exceeds requested quantity | `422 PICK_EXCEEDS_REQUESTED_QUANTITY` | None |
| Missing source balance or allocation exceeds locked source quantity | `409 INSUFFICIENT_SOURCE_STOCK` | None |
| State changes between context read and confirmation | Re-evaluate under lock; return typed conflict if invalid | None |
| Persistence or unexpected server failure | Existing server handling; transaction rolls back | None |

`PARTIAL_INSUFFICIENT` is not an error when `0 < picked_quantity < requested_quantity` and every allocation is valid. The system never auto-picks the maximum available quantity and never auto-allocates sources.

## Canonical Acceptance Criteria mapping

| AC | Requirement/rule/decision | Implementation behavior | Planned verification |
|---|---|---|---|
| `AC-PICK-001` | `CAND-REQ-006`, `CAND-BR-005/006`, `DEC-012/037` | Allocation sum equals requested quantity; persist `FULLY_COMPLETED`; decrement each source atomically | Single- and multi-location full confirmation; exact stock effects |
| `AC-PICK-002` | `CAND-REQ-003/006`, `CAND-BR-003/005`, `DEC-010/012/037` | Accept one or more unique tracked source allocations for the request SKU | One location insufficient but two valid allocations reach requested total |
| `AC-PICK-003` | `CAND-REQ-006`, `CAND-BR-006`, `DEC-012/037`, `NFR-005` | `0 < picked < requested`; explicit partial confirmation; persist `PARTIAL_INSUFFICIENT`; derive remaining; not fully completed | Backend outcome and UI picked/requested/remaining copy |
| `AC-PICK-004` | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019/022/037`, `NFR-001/002` | Lock and re-read affected balances; reject any insufficient source; rollback all effects | No negative stock, stale-context conflict, rollback and concurrent Pick tests |

## Stock Semantics

- `picked_quantity = SUM(pick_allocations.quantity)`; it is not stored as a duplicated column.
- `remaining_quantity = pick_requests.requested_quantity - picked_quantity`; it is derived.
- `picked_quantity == requested_quantity` produces `FULLY_COMPLETED`.
- `0 < picked_quantity < requested_quantity` produces `PARTIAL_INSUFFICIENT`.
- `picked_quantity == 0` and `picked_quantity > requested_quantity` are rejected.
- Each allocation quantity must be a positive integer and each source may appear only once.
- Each allocation is validated against the locked balance for the same request SKU and source location.
- Stock decrements only on successful confirmation. No reservation or pre-confirmation decrement exists.
- Warehouse total is derived by summing committed location balances and is never directly mutated.
- A failed command leaves no Pick result, allocation or stock mutation.
- Multiple later partial confirmations, correction and reversal are outside the current slice.

## Approved Data Model

### Existing reused entities

| Entity | Reuse |
|---|---|
| `warehouses` | Request relationship boundary |
| `skus` | Single SKU identity for the request |
| `internal_locations` | Tracked `BACKROOM` / `SALES_SHELF` sources |
| `stock_balances` | Authoritative per-SKU/location quantity; existing non-negative check |
| `users` | Confirmation actor FK |

### New `pick_requests`

| Field | Type/nullability | Constraint/index | Business meaning |
|---|---|---|---|
| `id` | UUID, non-null | PK | Prepared Pick identity |
| `warehouse_id` | UUID, non-null | FK `warehouses`, index | MVP Warehouse boundary |
| `sku_id` | UUID, non-null | FK `skus`, index | The request's one SKU |
| `requested_quantity` | Integer, non-null | `CHECK > 0` | Requested units for this slice |
| `outcome` | String, nullable before confirmation | `NULL` or `FULLY_COMPLETED` / `PARTIAL_INSUFFICIENT` | Immutable confirmed outcome |
| `confirmed_by_user_id` | UUID, nullable before confirmation | FK `users`, index | Warehouse Staff actor |
| `confirmed_at` | timezone-aware timestamp, nullable before confirmation | paired with actor/outcome | Commit timestamp |

Database checks must keep `outcome`, `confirmed_by_user_id` and `confirmed_at` all null for an unconfirmed request or all non-null for a confirmed request. No `picked_quantity` column is added.

### New `pick_allocations`

| Field | Type/nullability | Constraint/index | Business meaning |
|---|---|---|---|
| `id` | UUID, non-null | PK | Allocation identity |
| `pick_id` | UUID, non-null | FK `pick_requests`, index | Owning Pick request/result |
| `source_location_id` | UUID, non-null | FK `internal_locations`, index | Selected source |
| `quantity` | Integer, non-null | `CHECK > 0` | Confirmed source quantity |

Required uniqueness: `(pick_id, source_location_id)`. Do not add `PickLine`, a generic transaction engine, `warehouse_totals`, reservations or generic Movement persistence.

## API Contract

All routes use the existing base path, session authentication, role dependency and error envelope.

### `GET /api/v1/picks/context/{pick_id}`

Actor: `WAREHOUSE_STAFF` only.

Response fields:

```json
{
  "pick_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "sku_id": "<uuid>",
  "sku": "SKU-001",
  "requested_quantity": 12,
  "outcome": null,
  "locations": [
    {
      "id": "<uuid>",
      "code": "BACKROOM",
      "available_quantity": 8
    }
  ],
  "warehouse_total": 14
}
```

This is a current snapshot only. Confirmation must re-read stock under lock.

### `POST /api/v1/picks`

Actor: `WAREHOUSE_STAFF` only.

Request:

```json
{
  "pick_id": "<uuid>",
  "allocations": [
    {"source_location_id": "<uuid>", "quantity": 8},
    {"source_location_id": "<uuid>", "quantity": 2}
  ]
}
```

First successful confirmation returns `201 Created`:

```json
{
  "pick_id": "<uuid>",
  "sku_id": "<uuid>",
  "requested_quantity": 12,
  "picked_quantity": 10,
  "remaining_quantity": 2,
  "outcome": "PARTIAL_INSUFFICIENT",
  "allocations": [
    {
      "source_location_id": "<uuid>",
      "source_location": "BACKROOM",
      "quantity": 8,
      "remaining_source_quantity": 0
    }
  ],
  "confirmed_by_user_id": "<uuid>",
  "confirmed_at": "<timestamp>",
  "warehouse_total": 4
}
```

No Pick `Idempotency-Key` framework is added. A second confirmation returns `409 PICK_ALREADY_RECORDED` and never decrements stock twice.

## Authorization

- Both Pick routes require backend-enforced `WAREHOUSE_STAFF`.
- Unauthenticated/invalid session behavior is `401`; an authenticated wrong role is `403`.
- Frontend role checks are presentation only.
- No Manager endpoint, approve/reject action or Manager lifecycle is included. The durable outcome may support a future separately approved reporting contract.

## Validation

- Request and allocation identifiers must be valid UUIDs.
- `allocations` must be non-empty.
- Allocation quantities must be strict positive integers.
- Source IDs must be unique within the command.
- Sources must belong to the request Warehouse and use a tracked location code.
- Sum must be greater than zero and no greater than `requested_quantity`.
- Each selected source must have an existing balance for the request SKU and sufficient locked quantity.
- Client-supplied SKU, outcome, totals, actor and timestamps are not accepted.

## Concurrency / Transaction

1. Use the existing request-scoped PostgreSQL transaction.
2. Lock the `pick_requests` row first.
3. Reject immediately if it is already confirmed.
4. Sort unique source location IDs deterministically.
5. Lock all existing affected `stock_balances` rows in that order.
6. Re-read and validate location ownership, SKU, quantities and totals under the locks.
7. Insert allocations, set result fields and decrement all balances.
8. Flush so database FK, uniqueness and check constraints are evaluated.
9. Commit as one unit; roll back everything on any exception.

Future stock-changing services should preserve a compatible deterministic balance-lock order. PostgreSQL concurrency tests are required; SQLite component tests are not evidence of row-lock correctness.

## UI States

- Loading Pick context.
- Context load/server error.
- Default request with SKU and requested quantity.
- Current source availability for `BACKROOM` and `SALES_SHELF`.
- Explicit quantity input per selected source.
- Live picked/requested/remaining summary.
- Full confirmation-ready state.
- Partial confirmation state requiring an explicit user action.
- Validation error.
- Stale/insufficient source conflict with quantity unchanged.
- `FULLY_COMPLETED` success.
- `PARTIAL_INSUFFICIENT` result with wording that it is not fully completed and reports remaining units.

The UI does not add automatic allocation, FIFO, FEFO, reservation, barcode, scanner or device behavior.

## Observability / Logging

- Log successful confirmation only after transaction commit.
- Success context: Pick ID, actor user ID, requested quantity, derived picked quantity, allocation count and outcome.
- Rejections may log Pick ID, actor ID where available and stable error code.
- Do not log session tokens, cookies, passwords or secrets.
- No audit-history or generic Movement subsystem is introduced by this slice.

## Test Plan

### Backend/API

| Test | Expected result |
|---|---|
| Full single-source Pick | `201`, `FULLY_COMPLETED`, exact source decrement |
| Full multi-source Pick | Allocation sum equals requested; both sources decrement correctly |
| Partial explicit Pick | `201`, `PARTIAL_INSUFFICIENT`, correct remaining quantity and UI-facing result |
| Quantity equals available | Source becomes zero, never negative |
| Picked less than available | Only confirmed amount is decremented |
| Zero total / zero or negative allocation | `422`, no result/allocation/stock effect |
| Picked greater than requested | `422`, no effect |
| Duplicate source | `422`, no effect |
| Missing/foreign/untracked source | Typed `422`/`409`, no effect |
| Missing balance | `409 INSUFFICIENT_SOURCE_STOCK`, no balance created |
| Stale/insufficient locked stock | `409`, no effect |
| Already-confirmed Pick | `409 PICK_ALREADY_RECORDED`, no second decrement |
| Missing Pick | `404 PICK_NOT_FOUND` |
| Unauthenticated / wrong role | `401` / `403` |
| Forced failure after staged writes | Full rollback |
| Unrelated location and SKU | Unchanged |
| Derived Warehouse total | Equals sum of committed location balances |
| Concurrent conflicting Picks | Valid committed result(s) only; no negative stock |
| Opposite client allocation order | Server lock order remains deterministic |

### Migration/PostgreSQL

- Upgrade creates only `pick_requests` and `pick_allocations` with the approved fields, checks, FKs, indexes and uniqueness.
- Existing rows/tables remain intact; no fabricated Pick request is backfilled.
- Invalid outcome/result triples, non-positive quantities and duplicate sources are rejected by database constraints where applicable.
- Downgrade is tested in an isolated test database.
- PostgreSQL 17+ migration and concurrency evidence is required before release-ready claims.

### Frontend

- Loading, context error and default states.
- Source selection and positive-integer validation.
- Picked/requested/remaining calculations.
- Explicit partial confirmation gate.
- Full and partial result copy remain visibly distinct.
- Typed insufficient/stale-stock error leaves the form recoverable without claiming success.
- `401` returns to the existing authentication flow.

### Playwright

- Full multi-location Pick through the browser.
- Explicit partial confirmation and not-fully-completed copy.
- Blocked stale/insufficient confirmation with a database snapshot proving no mutation.
- Dedicated deterministic Pick fixtures; tests must not share mutable stock when executed in parallel.

## Data Read

- Pick request and its current result fields.
- Request Warehouse and SKU.
- Tracked internal locations.
- Selected per-SKU/location balances under lock for confirmation.
- Location balances needed to derive Warehouse total after commit.

## Data Write

- One immutable confirmed result on `pick_requests`.
- One allocation per selected source on `pick_allocations`.
- Decrements to exactly the selected existing `stock_balances` rows.

## No-Effect Guarantees

Pick must not:

- increase stock;
- create a missing `StockBalance` row;
- write a Warehouse-total row;
- mutate Receive facts or Putaway history;
- create Transfer, Adjust or generic Movement records;
- bypass backend authorization;
- create negative stock;
- auto-allocate, auto-pick maximum stock, apply FIFO/FEFO or reservation behavior;
- leave partial database mutation after any rejected or failed command.

## Implementation Slices

| Slice | Files | Purpose / dependency | Verification |
|---|---|---|---|
| 1 — schema | `backend/alembic/versions/<revision>_pick.py`, `models.py`, `tests/test_pick_migration.py` | Approved tables/constraints; depends on existing Warehouse/SKU/User/Location | Migration cycle and PostgreSQL constraints |
| 2 — domain/service | new `backend/src/warehouse_api/pick.py` | Lock, validate, derive outcome and mutate atomically | Service/API/rollback/concurrency tests |
| 3 — API | `schemas.py`, new `pick_routes.py`, `main.py` | Approved GET/POST and typed errors | Contract tests |
| 4 — authorization/validation | reuse `auth.py`; Pick route tests | Warehouse Staff only and strict request validation | `401`, `403`, `404`, `409`, `422` |
| 5 — fixtures/tests | `test_seed.py`, new `tests/test_pick.py` | Deterministic Pick contexts and stock states | Full backend suite |
| 6 — frontend | `api.ts`, new `PickPage.tsx`, `App.tsx`, `styles.css` | Approved states and explicit partial confirmation | Vitest, typecheck, lint, build |
| 7 — browser E2E | new `e2e/pick.spec.ts`, `e2e/global-setup.ts` | Full, partial and blocked paths | Playwright with isolated database |
| 8 — traceability | This spec, Story Specs Index, Traceability and AI Usage Log | Record implementation evidence only after review | Documentation diff review |

## Definition of Done

- Schema and migration implement exactly the approved two-table model.
- GET context and POST confirmation conform to this contract.
- Backend enforces Warehouse Staff authorization and existing `401`/`403` semantics.
- Full and partial results are persisted with the approved outcome values.
- The UI requires explicit confirmation for partial and clearly distinguishes it from completion.
- Pick request, all affected balances and allocations/result are handled atomically.
- Concurrent commands cannot produce negative stock or double-confirm the same request.
- No-effect guarantees have automated coverage.
- Backend, migration, frontend and Playwright checks produce fresh passing output.
- PostgreSQL 17+ evidence covers row locking and concurrency.
- Human reviews the implementation diff before commit/integration.
- Traceability is updated only with verified implementation evidence.

## Explicit Boundaries

- `OQ-012` remains open; integer quantity is only the current-slice technical baseline.
- `OQ-022` remains open; scanner/device/mobile/offline/integration behavior is not added.
- Future retry/idempotency enhancement remains `TBD / OUT OF CURRENT SLICE`.
- Correction, reversal and multiple later partial confirmations are outside the current story.
- Manager partial-review/reporting contract remains `TBD`; no Manager endpoint or action is implemented.
- Pick request creation is outside the story; a prepared/external request is the precondition.
- FIFO, FEFO, reservation and automatic allocation are excluded.

## Review Outcome

`US-PICK-001 READY FOR IMPLEMENTATION: YES`

Implementation must remain inside `DEC-037` and this spec. Any change to the approved lifecycle, outcome, partial semantics, allocation policy, data/API contract or explicit boundaries requires human review and the appropriate canonical update.
