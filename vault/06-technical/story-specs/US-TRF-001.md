# US-TRF-001 Technical Story Spec

## Status and authority

`IMPLEMENTATION-READY — HUMAN APPROVED`

- Story: `US-TRF-001 — Xác nhận Internal Transfer`
- Owner: Nguyễn Thị Ly Na
- Canonical product story: [`../../04-product/stories/US-TRF-001.md`](../../04-product/stories/US-TRF-001.md)
- Technical approval: `DEC-038`
- This document defines the current implementation slice and does not change the canonical Acceptance Criteria.
- No application code, migration, commit or push is part of this documentation update.

## Traceability

- Requirements: `REQ-001`, `REQ-002`, `REQ-004`, `CAND-REQ-003`, `CAND-REQ-010`, `CAND-REQ-011`, `FR-012`.
- Business rules: `CAND-BR-003`, `CAND-BR-007`, `CAND-BR-008`, `CAND-BR-015`.
- Product decisions: `DEC-005`, `DEC-007`, `DEC-009`, `DEC-010`, `DEC-013`, `DEC-017`, `DEC-018`, `DEC-019`, `DEC-024`.
- Technical decisions: `DEC-020`, `DEC-021`, `DEC-022`, `DEC-025`, `DEC-031`, `DEC-033`, `DEC-035`, `DEC-038`.
- NFRs: `NFR-001`, `NFR-002`, `NFR-004`.
- Design: no dedicated Transfer screen or prototype is canonical. Existing frontend patterns may be reused without treating Pick design as Transfer requirements.
- Open boundaries: `OQ-012`, remaining Transfer lifecycle topics in `OQ-013`, cross-workflow partial behavior in `OQ-014`, and `OQ-022`.
- Evidence classification: `EVD-010`, `EVD-011` and `EVD-019` are current-state context only. The approved behavior is a HUMAN PRODUCT/TECHNICAL DECISION.

Historical `CAND-REQ-004` is `SUPERSEDED / DECOMPOSED`; it is not an active trace target. Transfer history/query belongs to `US-TRF-002` and is outside this slice.

## Goal

Allow an authenticated Warehouse Staff actor to confirm one immutable Internal Transfer for one SKU between two different tracked locations in the same MVP Warehouse. Confirmation atomically decrements the source, increments the destination by the same positive integer quantity, persists a durable Transfer record, preserves the derived Warehouse total and prevents duplicate stock movement on safe client retry.

## Preconditions

- The actor is authenticated and has current database role `WAREHOUSE_STAFF`.
- The SKU exists.
- Source and destination are different tracked locations in the same Warehouse.
- The source has an existing `StockBalance` for the SKU and enough quantity.
- Quantity is a strict positive integer for this implementation slice. This does not resolve `OQ-012`.
- A missing destination balance may be created in the Transfer transaction; a missing source balance is insufficient stock and is never created.
- The client supplies a non-empty explicit `Idempotency-Key`.

## Happy Path

1. Warehouse Staff loads `GET /api/v1/transfers/context/{sku_id}`.
2. The UI displays the SKU, tracked locations, current quantities and derived Warehouse total as a read-only snapshot.
3. Warehouse Staff selects different source and destination locations and enters a positive integer quantity.
4. The client sends `POST /api/v1/transfers` with the command and an `Idempotency-Key`.
5. The backend validates actor, key, request shape, SKU and location relationship.
6. The backend atomically claims the idempotency key for a new uncommitted Transfer row or resolves an existing committed replay/conflict.
7. For a new command, the backend safely materializes a missing destination balance inside the same transaction when needed.
8. The backend locks all affected balance rows in sorted location UUID order, independent of client/source/destination order.
9. The backend re-reads and validates source stock under lock.
10. The backend decrements source, increments destination and completes the immutable Transfer result with actor and timestamp.
11. The transaction commits and the response reports resulting balances and the derived Warehouse total.

## Alternate / Error Paths

| Condition | Result | Data effect |
|---|---|---|
| Missing/invalid session or inactive user | Existing `401` auth envelope | None |
| Authenticated actor is not Warehouse Staff | `403 FORBIDDEN` | None |
| SKU does not exist | `404 SKU_NOT_FOUND` | None |
| Quantity is missing, non-integer, zero or negative | `422 INVALID_QUANTITY` | None |
| Source is absent, untracked or not in the Transfer Warehouse | `422 INVALID_SOURCE_LOCATION` | None |
| Destination is absent, untracked or not in the Transfer Warehouse | `422 INVALID_DESTINATION_LOCATION` | None |
| Source equals destination | `422 SAME_TRANSFER_LOCATION` | None |
| Source balance is missing or locked quantity is insufficient | `409 INSUFFICIENT_SOURCE_STOCK` | None; source balance is not created |
| Same idempotency key and same effective command is replayed | Return the same immutable Transfer identity/command using the safe-replay representation below; no second stock movement | None beyond the original committed result |
| Same idempotency key is reused for a different effective command | `409 IDEMPOTENCY_KEY_REUSED` | None |
| State changes between context read and confirmation | Re-evaluate under locks; return the applicable typed conflict | None |
| Destination creation, persistence or unexpected failure | Existing server handling; the transaction rolls back | No Transfer row, no new destination row and no stock mutation |

Correction, reversal, update and deletion are not error-recovery paths in this story. They require a separate future contract and must never rewrite the original confirmed Transfer.

## Canonical Acceptance Criteria mapping

| AC | Requirement/rule/decision | Implementation behavior | Planned verification |
|---|---|---|---|
| `AC-TRF1-001` | `FR-012`, `CAND-REQ-003`, `CAND-BR-003/007`, `DEC-013/022/038` | Lock two balances deterministically; decrement source and increment destination by the same quantity in one transaction | Exact source/destination effects, missing-destination creation, rollback and concurrency tests |
| `AC-TRF1-002` | `CAND-REQ-003`, `CAND-BR-003/007`, `DEC-010/013/021/038` | Never persist or mutate Warehouse total; derive the same sum after the Transfer | Before/after derived total equality and absence of a Warehouse-total write |
| `AC-TRF1-003` | `FR-012`, `CAND-BR-008`, `DEC-013/024/038` | Insert one immutable durable record containing the canonical minimum plus approved Warehouse and actor fields | Persistence, FK, field, timestamp, replay and immutability assertions |
| `AC-TRF1-004` | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019/022/038`, `NFR-001/002` | Re-read locked source; reject missing/insufficient stock and roll back all effects | Typed conflict, no negative stock, conflicting Pick/Transfer and Transfer/Transfer tests |

## Stock Semantics

For approved quantity `q`:

```text
source.quantity      := source.quantity - q
destination.quantity := destination.quantity + q
```

- `q > 0`.
- Source and destination belong to the same Warehouse and reference the same command SKU.
- Source and destination IDs are different.
- `source.quantity >= q` is checked after locking.
- Source quantity never becomes negative.
- Warehouse total is derived from location balances and remains unchanged.
- Unrelated SKU/location balances remain unchanged.
- No generic Movement record is created.
- There is no reservation or pre-confirmation stock effect.
- Any failure rolls back the Transfer row, both stock effects, idempotency state and a newly created destination balance.

## Approved Data Model

### Existing reused entities

| Entity | Reuse |
|---|---|
| `warehouses` | Same-Warehouse relationship boundary |
| `skus` | Transferred SKU identity |
| `internal_locations` | Tracked `BACKROOM` / `SALES_SHELF` source and destination |
| `stock_balances` | Authoritative per-SKU/location quantity; unique `(sku_id, location_id)` and non-negative check |
| `users` | Warehouse Staff actor FK |

### New `transfers`

| Field | Type/nullability | Constraint/index | Meaning |
|---|---|---|---|
| `id` | UUID, non-null | PK | Immutable Transfer identity |
| `warehouse_id` | UUID, non-null | FK `warehouses`, index; composite history index with time | Same-Warehouse boundary |
| `sku_id` | UUID, non-null | FK `skus`, index | Transferred SKU |
| `source_location_id` | UUID, non-null | FK `internal_locations`, index | Source tracked location |
| `destination_location_id` | UUID, non-null | FK `internal_locations`, index | Destination tracked location |
| `quantity` | Integer, non-null | `CHECK quantity > 0` | Current-slice units transferred |
| `transferred_by_user_id` | UUID, non-null | FK `users` | Confirming Warehouse Staff actor |
| `transferred_at` | timezone-aware timestamp, non-null | `(warehouse_id, transferred_at)` index | Confirmation time |
| `idempotency_key` | String, non-null | unique | Explicit safe-retry identity |
| `request_fingerprint` | String, non-null | exact request comparison | Detect conflicting key reuse |

Required table check: `source_location_id <> destination_location_id`.

`idempotency_key` and `request_fingerprint` are approved technical fields required to satisfy H8 transactionally. They are stored on the Transfer row, following the minimum existing Putaway-style pattern rather than introducing a generic idempotency subsystem. The effective command fingerprint covers `sku_id`, `source_location_id`, `destination_location_id` and `quantity` in a stable canonical representation.

The implementation must claim a new key atomically, for example with PostgreSQL `INSERT ... ON CONFLICT DO NOTHING RETURNING`, after SKU/location validation has derived the authoritative Warehouse and before any stock effect. A losing concurrent request re-reads the committed row, compares the fingerprint and either performs a safe replay or returns `IDEMPOTENCY_KEY_REUSED`. If the winning transaction rolls back, its Transfer/key claim rolls back with it.

The service validates that both locations belong to `warehouse_id`; existing single-column FKs do not by themselves enforce that cross-table relationship. Do not add editable status, `warehouse_total`, generic Movement persistence, correction or reversal fields.

## Destination Balance Policy

- A missing source balance is treated as insufficient stock and is never created.
- A missing destination balance for the same SKU may be inserted with the Transfer quantity inside the Transfer transaction.
- No zero destination row is committed separately.
- The existing unique `(sku_id, location_id)` constraint is the concurrency guard.
- Implementation must use a dialect-appropriate insert/conflict pattern so concurrent destination creation produces one balance row.
- After materialization or conflict resolution, both affected balance rows are locked in the approved deterministic order and re-read before mutation/result construction.
- If any later validation or write fails, a newly inserted destination balance rolls back with the Transfer.

## API Contract

All routes use the existing session authentication, role dependency and error envelope.

### `GET /api/v1/transfers/context/{sku_id}`

Actor: `WAREHOUSE_STAFF` only.

Response:

```json
{
  "warehouse_id": "<uuid>",
  "sku_id": "<uuid>",
  "sku": "SKU-001",
  "locations": [
    {
      "id": "<uuid>",
      "code": "BACKROOM",
      "available_quantity": 12
    }
  ],
  "warehouse_total": 18
}
```

The context is a read-only current snapshot. It creates no reservation, holds no long-lived lock and cannot guarantee that availability remains unchanged before POST.

### `POST /api/v1/transfers`

Actor: `WAREHOUSE_STAFF` only.

Required header:

```http
Idempotency-Key: <client-generated opaque value>
```

Request:

```json
{
  "sku_id": "<uuid>",
  "source_location_id": "<uuid>",
  "destination_location_id": "<uuid>",
  "quantity": 4
}
```

The first successful confirmation returns `201 Created`:

```json
{
  "transfer_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "sku_id": "<uuid>",
  "quantity": 4,
  "source_location_id": "<uuid>",
  "source_location": "BACKROOM",
  "destination_location_id": "<uuid>",
  "destination_location": "SALES_SHELF",
  "transferred_by_user_id": "<uuid>",
  "transferred_at": "<timestamp>",
  "stock": {
    "source_quantity": 8,
    "destination_quantity": 10,
    "warehouse_total": 18
  }
}
```

Same-key/same-command replay returns `200 OK` with the same Transfer ID and immutable command/actor/time fields and must not move stock again. Following the existing Putaway-style convention, the response stock block is read from current committed balances at replay time; it is not persisted as a historical response snapshot and may differ after later valid stock operations. The first success remains `201 Created`. Same-key/different-command returns `409 IDEMPOTENCY_KEY_REUSED`.

This replay contract intentionally avoids a persisted `warehouse_total`, response JSON blob or generic idempotency-result subsystem. `US-TRF-002` history continues to expose the immutable Transfer facts, not historical balance snapshots.

`GET /api/v1/transfers` and all history/query UI belong to `US-TRF-002`.

## Authorization

- Both routes require backend-enforced `WAREHOUSE_STAFF`.
- Missing/invalid/expired/revoked session or inactive user returns the existing `401` outcome.
- An authenticated `MANAGER`, `PURCHASING` or `ADMIN` actor receives `403 FORBIDDEN` for these execution routes.
- Frontend role checks are presentation only.
- Manager Transfer history remains a separate `US-TRF-002` contract.

## Validation

- IDs must be valid UUIDs.
- Quantity must be a strict positive integer.
- SKU must exist.
- Source and destination must exist, be tracked and belong to the same Warehouse.
- Source and destination must differ; enforce in the API/service and with a database check.
- Source balance must exist for the command SKU and have sufficient locked quantity.
- The idempotency key must be present and may only be reused with the same effective command.
- Client-supplied Warehouse, actor, timestamp, totals, location codes and resulting quantities are not accepted as authority.

## Concurrency / Transaction

1. Use the existing request-scoped PostgreSQL transaction.
2. Validate the request shape, SKU and location ownership and derive the authoritative Warehouse.
3. Atomically insert/claim the Transfer row and idempotency key with no stock effect; on key conflict, compare the committed fingerprint and return safe replay or `IDEMPOTENCY_KEY_REUSED`.
4. For a newly claimed command, ensure a missing destination balance is materialized safely in the current transaction using unique `(sku_id, location_id)` conflict protection.
5. Sort the two affected location UUIDs deterministically using the same ordering contract as Pick.
6. Lock both `StockBalance` rows in sorted UUID order, never client, source-first or destination-first order.
7. Re-read source/destination quantities under the locks.
8. Validate source sufficiency and all invariants.
9. Apply both balance effects and finalize the immutable result representation.
10. Flush so FK, uniqueness and check constraints are evaluated.
11. Commit as one unit; roll back the Transfer/key claim, destination creation and stock effects on any exception.

An implementation may minimally extract/reuse the Pick UUID-order helper. It must not perform a broad inventory refactor. PostgreSQL concurrency tests are required; SQLite component tests are not row-lock evidence.

## UI States

- Loading Transfer context.
- Context load/server error.
- SKU and derived Warehouse total.
- Source selection with current availability.
- Destination selection.
- Positive integer quantity input.
- Same-source/destination validation.
- Insufficient or stale source conflict with a reload action.
- Submitting state that prevents accidental duplicate local submission while the idempotency key provides backend safety.
- Validation/API error without a success claim.
- Confirmed success showing source/destination, quantity, resulting balances and unchanged derived total.
- Existing `401` authentication recovery and wrong-role forbidden presentation.

There is no approved dedicated Transfer prototype. Implementation must use existing design-system primitives and receive human UI review. It must not add history, partial Transfer, bulk/multi-SKU Transfer, FIFO/FEFO, reservation, scanner/device behavior or auto-routing.

## Observability / Logging

- Log successful confirmation only after transaction commit.
- Success context: Transfer ID, actor user ID, SKU ID, source/destination IDs and quantity.
- Safe replay may be logged distinctly without claiming a second confirmation.
- Rejections may log stable error code and non-secret identifiers.
- Never log session tokens, cookies, passwords, secrets or the raw idempotency key.
- No generic Movement/audit-history subsystem is introduced.

## Test Plan

### Backend/API

| Test | Expected result |
|---|---|
| Valid Transfer with two existing balances | `201`; one record; exact decrement/increment |
| Warehouse total | Derived before/after total unchanged |
| Minimum durable record | Approved fields, actor and timestamp persisted |
| Same source/destination | `422 SAME_TRANSFER_LOCATION`; no effects; DB check also rejects invalid direct insert |
| Zero, negative, non-integer, boolean or string quantity | `422 INVALID_QUANTITY`; no effects |
| Quantity equals source | Source becomes zero, never negative |
| Quantity exceeds source | `409 INSUFFICIENT_SOURCE_STOCK`; no effects |
| Missing source balance | Same typed conflict; source row not created |
| Missing destination balance | Destination row and Transfer created atomically on success |
| Failure after missing-destination staging | Destination row, Transfer and stock effects all roll back |
| Invalid/foreign/untracked locations | Approved `422` code; no effects |
| Unrelated SKU/location | Unchanged |
| Same key/same command replay | Original result; one Transfer; one stock movement |
| Same key/different command | `409 IDEMPOTENCY_KEY_REUSED`; no additional effects |
| Missing key | Typed validation response; no effects |
| Missing SKU | `404 SKU_NOT_FOUND` |
| Unauthenticated / wrong role | `401` / `403` |
| Receive/Putaway/Pick/Adjust/Movement | No mutation or record creation |

### Migration/PostgreSQL

- Upgrade creates `transfers` with exactly the approved fields, checks, FKs, indexes, unique idempotency identity and composite history index.
- Existing tables and data remain intact; no Transfer is fabricated.
- Non-positive quantity, same locations and duplicate idempotency keys are rejected by database constraints where applicable.
- Downgrade is exercised only in an isolated test database.
- PostgreSQL 17+ migration evidence is required before release-ready claims.

### Concurrency

- Transfer-vs-Transfer commands using opposite client source/destination order follow sorted UUID locks and do not deadlock.
- Conflicting Transfers from the same source preserve non-negative stock; only serially valid commands commit.
- Pick-vs-Transfer on a shared source uses compatible balance ordering and preserves non-negative stock.
- Concurrent Transfers creating the same destination balance leave one balance row and correct total effects.
- Concurrent same-key retries create one Transfer and move stock once.
- Concurrency evidence must run on PostgreSQL.

### Frontend

- Loading, context error and default form states.
- Source/destination and quantity validation.
- Same-location error.
- Stale/insufficient conflict keeps the form recoverable and does not claim success.
- One idempotency key remains stable for retries of the same effective submission and changes when the effective command intentionally changes after a completed/abandoned attempt according to implementation tests.
- Success displays resulting balances and derived total.
- `401` returns to authentication; wrong role shows forbidden state.

### Playwright

- Successful Transfer through browser/API/PostgreSQL with a database snapshot proving exact effects and unchanged total.
- Missing-destination Transfer creates the balance atomically.
- Stale/insufficient source is rejected with an unchanged snapshot.
- Retry of the same effective command does not move stock twice.
- Dedicated deterministic fixtures must not share mutable balances when tests run in parallel.

## Data Read

- Current actor from the authenticated session.
- SKU.
- Tracked source/destination locations and their Warehouse ownership.
- Source/destination balances under lock for confirmation.
- Location balances required to derive Warehouse total.
- Existing Transfer by idempotency key for replay/conflict handling.

## Data Write

- One immutable `transfers` row for the first successful command.
- Decrement to the existing source balance.
- Increment to the existing or transactionally created destination balance.
- No separate generic idempotency table is required for this slice.

## No-Effect Guarantees

Transfer must not:

- mutate Receive facts, Putaway history or Pick history;
- create or apply Adjust;
- create generic Movement persistence;
- directly persist or mutate Warehouse total;
- create a missing source balance;
- create negative stock;
- treat same-location Transfer as a valid no-op;
- overwrite, edit or delete an existing confirmed Transfer;
- move stock twice for a safe idempotent replay;
- add history/query UI or API from `US-TRF-002`;
- add partial, correction/reversal, bulk, multi-SKU, FIFO/FEFO, reservation, scanner/device or auto-route behavior;
- leave partial database mutation after a rejected or failed command.

## Implementation Slices

| Slice | Files | Purpose / dependency | Verification |
|---|---|---|---|
| 1 — schema | `backend/src/warehouse_api/models.py`, new `backend/alembic/versions/<revision>_transfer.py`, new `backend/tests/test_transfer_migration.py` | Approved immutable model, constraints, indexes and idempotency fields | Migration cycle and PostgreSQL constraints |
| 2 — locking/service | new `backend/src/warehouse_api/transfer.py`; minimal shared ordering helper or narrow `pick.py` reuse | Destination race, sorted locks, validation, atomic mutation/replay | Service, rollback and PostgreSQL concurrency tests |
| 3 — API | `schemas.py`, new `transfer_routes.py`, `main.py` | Approved context GET and confirmation POST | Contract/error tests |
| 4 — authorization | reuse `auth.py`; Transfer route tests | Warehouse Staff only | `401`, `403` |
| 5 — fixtures/backend tests | `test_seed.py`, new `tests/test_transfer.py`, new `tests/test_transfer_concurrency.py` | Deterministic stock/idempotency cases | Full backend and PostgreSQL suites |
| 6 — frontend | `frontend/src/api.ts`, new `TransferPage.tsx`, `App.tsx`, `styles.css` | Approved UI states without history or new product behavior | Vitest, typecheck, lint, build |
| 7 — browser E2E | new `frontend/e2e/transfer.spec.ts`, fixture/global setup as needed | Success, missing destination, stale and retry flows | Chromium against PostgreSQL |
| 8 — docs/traceability | Story Spec, decision log, OQ boundary, Story Specs Index, `TRACEABILITY.md`, AI Usage Log | Record implementation evidence only after it exists | Link/status/diff review |

## Definition of Done

- Migration/model exactly implement the approved data contract.
- Context GET and idempotent confirmation POST match the approved contract and error envelope.
- Backend enforces Warehouse Staff authorization.
- Same-location and positive-quantity checks exist at application/API and database levels as approved.
- Missing destination creation, sorted UUID locking, stock effects, Transfer record and idempotency result are one atomic transaction.
- Unit/integration/migration/no-effect tests pass.
- PostgreSQL Transfer-vs-Transfer and Pick-vs-Transfer concurrency tests pass without negative stock or deadlock.
- Frontend lint, typecheck, component tests and build pass.
- Playwright Transfer flows pass against PostgreSQL.
- No excluded feature or generic Movement engine is introduced.
- Traceability is updated with actual evidence, and a human reviews the implementation diff before commit/integration.

## Open Questions / Explicit Boundaries

- `OQ-012` remains open. Integer quantity is only the approved current-slice technical baseline; it does not decide UOM, decimal quantity, conversion or precision/scale.
- `OQ-013` remains partially open. This slice decides immutable successful confirmation, safe replay and that correction/reversal are outside the story; broader failure/cancel lifecycle and any future reversal contract remain open.
- `OQ-014` remains open globally. Partial Transfer is not implemented in this slice and is not declared permanently out.
- `OQ-022` remains open. Scanner/device/mobile/offline/external integration behavior is not implemented or resolved.
- Transfer history/query remains `US-TRF-002`.
- No dedicated Transfer screen/prototype is currently canonical; UI implementation requires human review without inventing new product behavior.
