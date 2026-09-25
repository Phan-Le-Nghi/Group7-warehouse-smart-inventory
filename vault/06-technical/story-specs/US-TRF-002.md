# US-TRF-002 Technical Story Spec

## Status and authority

`IMPLEMENTATION-READY — HUMAN APPROVED`

- Story: `US-TRF-002 — Xem Transfer history`
- Owner: Nguyễn Thị Ly Na
- Canonical product story: [`../../04-product/stories/US-TRF-002.md`](../../04-product/stories/US-TRF-002.md)
- Technical approval: `DEC-039`
- This document defines the current implementation slice and does not change the canonical Acceptance Criteria.
- No application code, migration, commit or push is part of this documentation update.

## Traceability

- Requirements: `REQ-002`, `REQ-003`, `REQ-004`, `FR-013`, `CAND-REQ-010`.
- Business rule: `CAND-BR-008`.
- Product decisions: `DEC-005`, `DEC-013`, `DEC-017`, `DEC-024`.
- Technical decisions: `DEC-020`, `DEC-025`, `DEC-031`, `DEC-033`, `DEC-035`, `DEC-038`, `DEC-039`.
- NFR: `NFR-004`.
- Design: no dedicated Transfer history screen or prototype is canonical. The approved current-slice UI contract below requires human visual review without adding product behavior.
- Open boundaries: broader Transfer failure/cancel/correction/reversal lifecycle at `OQ-013` and device/integration behavior at `OQ-022` remain open.
- Evidence classification: `EVD-010`, `EVD-011` and `EVD-019` are current-state context only. Approved history behavior is a HUMAN PRODUCT/TECHNICAL DECISION.

Historical `CAND-REQ-004` is `SUPERSEDED / DECOMPOSED`; it is not an active trace target. Transfer execution remains `US-TRF-001` and must not be changed by this read/query story.

## Goal

Allow an authenticated Manager to read confirmed durable Transfer records created by `US-TRF-001` for the canonical single MVP Warehouse, so the Manager can trace relocation and support discrepancy investigation without causing any stock or workflow mutation.

## Preconditions

- The actor has a valid server-side session and current database role `MANAGER`.
- The server resolves and enforces the canonical single MVP Warehouse using the current architecture; the client does not provide `warehouse_id`.
- Every returned row is an already committed durable `Transfer` created by successful Transfer confirmation.
- `US-TRF-001` execution semantics, immutable Transfer facts and idempotency behavior remain unchanged.

## Read Semantics

- History reads only confirmed durable `Transfer` rows belonging to the server-resolved canonical MVP Warehouse.
- The current model has no draft, failed, reversed or deleted Transfer state. A failed or rolled-back confirmation has no durable Transfer row and therefore cannot appear in history.
- Each result reports immutable confirmation facts. It does not reconstruct or return current stock balances or a historical stock snapshot.
- The default deterministic order is `transferred_at DESC`, then `id DESC`.
- Current slice has no pagination and no filters.
- The query must not be reused as an execution replay, correction, reversal or reconciliation command.

## Authorization

Backend authorization is authoritative.

| Actor/session | Result |
|---|---|
| Valid `MANAGER` | May read Transfer history |
| Valid `WAREHOUSE_STAFF` | `403 FORBIDDEN` |
| Valid `PURCHASING` | `403 FORBIDDEN` |
| Valid `ADMIN` | `403 FORBIDDEN` |
| Missing, invalid, expired or revoked session; inactive user | Existing `401` outcome |

Frontend role checks are presentation only and do not replace backend enforcement.

## Query Contract

### `GET /api/v1/transfers`

- Actor: `MANAGER` only.
- Request body: none.
- Query parameters: none in the current slice.
- Client-supplied `warehouse_id` is not accepted.
- Success: `200 OK`.
- Empty history: `200 OK` with `{"items": []}`; never `404`.

Response:

```json
{
  "items": [
    {
      "transfer_id": "<uuid>",
      "warehouse_id": "<uuid>",
      "sku": {
        "id": "<uuid>",
        "code": "SKU-001"
      },
      "quantity": 4,
      "source": {
        "id": "<uuid>",
        "code": "BACKROOM"
      },
      "destination": {
        "id": "<uuid>",
        "code": "SALES_SHELF"
      },
      "transferred_by": {
        "user_id": "<uuid>",
        "login_identifier": "demo.warehouse_staff"
      },
      "transferred_at": "<timestamp>"
    }
  ]
}
```

The response must not expose `idempotency_key`, `request_fingerprint`, current stock balances or a historical stock snapshot.

## Sorting, Filtering and Pagination

- Sort: `transferred_at DESC`, tie-break `id DESC`.
- Pagination: none.
- Filters: none.
- Search and export: none.
- SKU, source, destination, actor and date-range filters are deferred to a future approved requirement.

The absence of pagination is a deliberate current-slice decision, not a reusable project-wide pagination convention.

## Data Read

The query reuses:

- `transfers` for Transfer identity, Warehouse, SKU, quantity, source, destination, actor and confirmation time;
- `skus` for SKU code;
- two aliases of `internal_locations` for source and destination codes;
- `users` for the confirming actor login identifier.

Only records whose `transfers.warehouse_id` matches the server-resolved canonical MVP Warehouse are eligible. The implementation must not introduce a multi-Warehouse user-membership model or accept a client-controlled Warehouse scope.

## Data and Index Assessment

The existing `transfers` model and migration already provide:

- single-column indexes for `warehouse_id`, `sku_id`, `source_location_id` and `destination_location_id`;
- composite index `(warehouse_id, transferred_at)`;
- all response identities and immutable facts needed by this story.

`NO MIGRATION REQUIRED`.

No new index may be added without a real approved query requirement and query-plan evidence. The `id DESC` tie-break does not by itself authorize an index change in this no-pagination slice.

## No-Effect Guarantees

`GET /api/v1/transfers` is strictly read-only. It must not:

- create, update or delete a `Transfer`;
- move stock or mutate `StockBalance`;
- mutate Receive, Putaway, Pick, Adjust or Audit data;
- replay an existing Transfer;
- trigger Transfer correction or reversal;
- create a reservation, generic Movement record or stock snapshot;
- mutate idempotency state.

Repeated reads over unchanged committed data return the same immutable facts in the approved deterministic order and have no business-data effect.

## Canonical Acceptance Criteria Mapping

| AC | Requirement/rule/decision | Implementation behavior | Planned verification |
|---|---|---|---|
| `AC-TRF2-001` | `FR-013`, `CAND-REQ-010`, `DEC-013/017/024/039`, `NFR-004` | Manager-only GET returns confirmed history for the server-resolved canonical MVP Warehouse | Empty/one/multiple-row API tests; Manager `200`; unauthenticated `401`; three wrong-role `403` cases; Warehouse-scope assertion |
| `AC-TRF2-002` | `FR-013`, `CAND-BR-008`, `DEC-013/024/039` | Each item returns approved Transfer/SKU/source/destination/actor fields and quantity without internal idempotency or stock fields | Exact response-shape and field-value tests; forbidden-field assertions; UI table assertions |
| `AC-TRF2-003` | `FR-013`, `DEC-013/039` | `transferred_at` is the durable confirmation timestamp and results use approved newest-first deterministic ordering | Persisted-time equality and `transferred_at DESC, id DESC` ordering tests |

## UI Contract

- Manager-only route/page: `/transfers/history`.
- Presentation: table.
- Loading state.
- Empty state.
- Loaded table containing the approved API fields at the approved level of detail.
- Server/API error state with retry.
- Existing `401` authentication recovery.
- `403` forbidden state.

The page has no edit, delete, reverse, rerun or detail action. It has no filters, search, export or pagination. It must not link history reading to automatic Transfer execution.

## Observability

- Reuse existing request/error observability without introducing a business mutation event for a successful read.
- Authorization failures retain the existing stable error envelope.
- Never log session tokens, cookies, passwords, secrets, raw idempotency keys or request fingerprints.
- Read logs, if emitted by existing infrastructure, must not claim Transfer confirmation, replay, correction or reversal.

## Test Plan

### Backend/API

- Empty canonical-Warehouse history returns `200` and `{"items": []}`.
- One row returns the exact approved nested response shape.
- Multiple rows sort by `transferred_at DESC`, then `id DESC` for equal timestamps.
- Source, destination, SKU, quantity, actor and confirmation time match persisted immutable facts.
- History is restricted to the server-resolved canonical MVP Warehouse; the client cannot select another Warehouse.
- Manager receives `200`.
- Missing/invalid session receives `401`.
- Warehouse Staff, Purchasing and Admin each receive `403`.
- `idempotency_key`, `request_fingerprint`, current balances and historical stock snapshots are absent.
- Unexpected database/server failure uses existing error handling and makes no data change.

### Read-only/no-effect

Before and after GET, assert unchanged counts and relevant values for Transfer, StockBalance, Receive, Putaway, Pick and any implemented Adjust/Audit records. Assert no replay, correction/reversal or idempotency-state change. Repeat GET and assert the same facts and ordering over unchanged committed data.

### Frontend

- Loading, empty, loaded-table and server-error/retry states.
- Exact approved fields and confirmation time rendering.
- `401` returns to authentication recovery.
- `403` renders the forbidden state.
- No edit/delete/reverse/rerun/detail/filter/export controls.

### Playwright

- Manager signs in, opens `/transfers/history` and sees deterministic confirmed history.
- Manager sees the empty state for an isolated empty fixture.
- A wrong authenticated role sees forbidden behavior.
- A database snapshot before and after the browser history flow proves no Transfer or stock/workflow mutation.

## Definition of Done

- Manager-only backend authorization and `401`/`403` outcomes are covered by automated tests.
- The server enforces canonical single-Warehouse scope without accepting `warehouse_id` from the client.
- `GET /api/v1/transfers` implements the exact approved response and empty collection behavior.
- Results sort by `transferred_at DESC`, then `id DESC`, with no pagination, filters, search or export.
- API and UI do not leak idempotency fields, stock balances or stock snapshots.
- No-effect tests cover Transfer, StockBalance and implemented neighboring workflow persistence.
- The Manager table implements all approved UI states and no mutation actions.
- Backend, frontend and Playwright checks produce fresh passing output.
- Traceability is updated with implementation evidence only after that evidence exists.
- Human reviews the implementation diff before integration or commit.

## Open Questions and Explicit Boundaries

- `OQ-013` remains `PARTIALLY DECIDED / OPEN`. This story reads immutable successful Transfer facts only and does not decide broader failure/cancel/correction/reversal behavior.
- `OQ-022` remains open. Barcode/QR, scanner, mobile/offline and external integration behavior are not introduced or resolved.
- Multi-Warehouse membership and selection are outside this canonical single-Warehouse slice.
- Pagination, filters, search, export and detail-page behavior require a future approved requirement.
- The story does not change `US-TRF-001` execution, idempotency, stock mutation or concurrency semantics.

## Implementation Slices and Exact File Plan

| Slice | Files | Outcome | Verification |
|---|---|---|---|
| 1 — query schemas/service | `backend/src/warehouse_api/schemas.py`, `transfer.py` | Exact read model, single-Warehouse query and deterministic ordering | Empty/one/multiple, fields, order and scope tests |
| 2 — authorization/API | `auth.py` only if a reusable Manager dependency is needed; `transfer_routes.py` | Manager-only `GET /api/v1/transfers` with existing `401`/`403` envelope | Four-role and unauthenticated API tests |
| 3 — backend tests | new `backend/tests/test_transfer_history.py`; `test_seed.py` only if deterministic fixtures require it | Contract, forbidden-field and no-effect coverage | Backend suite; PostgreSQL-compatible query verification |
| 4 — frontend history UI | `frontend/src/api.ts`, new `TransferHistoryPage.tsx`, `App.tsx`, `styles.css` | `/transfers/history` table and approved states | Vitest, typecheck, lint, build |
| 5 — frontend tests | new `TransferHistoryPage.test.tsx` | Loading/empty/table/error/auth/forbidden and no-action coverage | Vitest |
| 6 — browser E2E | new `frontend/e2e/transfer-history.spec.ts`; global setup/fixtures only as needed | Manager history, empty, forbidden and no-effect flows | Chromium against PostgreSQL |
| 7 — docs/traceability | this spec, Decision Log, Story Specs Index, `TRACEABILITY.md`, AI Usage Log | Record implementation evidence only after it exists | Link/status/diff review |

No migration file or Transfer model change belongs to this implementation plan.
