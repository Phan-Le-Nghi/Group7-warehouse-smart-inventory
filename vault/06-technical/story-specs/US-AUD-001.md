# US-AUD-001 Technical Story Spec

## Status and authority

`IMPLEMENTED IN WORKTREE — LOCAL COMPONENT VERIFIED — HUMAN REVIEW PENDING`

Canonical product wording and Acceptance Criteria remain authoritative at
[`../../04-product/stories/US-AUD-001.md`](../../04-product/stories/US-AUD-001.md).
Human review approved the implementation contract below at `DEC-040`; the worktree
implementation now follows that contract. This spec does not change the canonical
Acceptance Criteria and does not close `OQ-012`, the broader
Audit lifecycle/recheck/correction aspects of `OQ-013`, or `OQ-022`.

Fresh local evidence on 2026-09-26: backend Ruff lint/format PASS and pytest
`164 passed, 13 PostgreSQL-only skipped`; frontend ESLint/TypeScript PASS, Vitest
`56 passed`, and production build PASS; Playwright discovery lists 20 tests including
six Audit scenarios. PostgreSQL 17/18 concurrency/migration evidence and real browser
execution remain pending CI because no local `TEST_DATABASE_URL` or Docker CLI exists.

| Field | Value |
|---|---|
| Story ID | `US-AUD-001` |
| Story | Perform selected-scope Audit and record match or mismatch |
| Owner | Phan Lê Nghi |
| Requirement IDs | `REQ-002`, `REQ-004`, `CAND-REQ-003/005/010` |
| Business rules | `CAND-BR-003`, `CAND-BR-009` |
| Decisions | `DEC-010/014/017/018/021/025/031/040` |
| Verified evidence | `EVD-015/016` for current-state count/compare only |
| Design references | `SCR-07`, `PF-03` |
| Open boundaries | `OQ-012`, broader `OQ-013`, `OQ-022`; Manager review/recheck remains `US-AUD-002` |

`DEC-040` is a HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC, not verified research
evidence. No application code or migration was created while finalizing this document.

## Goal

Allow an authenticated Warehouse Staff actor to choose an explicit Audit scope, enter
physical counts, compare them with an authoritative submit-time snapshot of per-location
system stock, and persist a durable `MATCH` or `MISMATCH` result without changing stock.

## Actor and authorization

- `WAREHOUSE_STAFF` may call `GET /api/v1/audits/context`, submit
  `POST /api/v1/audits`, and receive the command result for the Audit just submitted.
- `MANAGER` does not create or submit an Audit in this story. Manager query, review and
  recheck behavior remains in `US-AUD-002`.
- `PURCHASING` and `ADMIN` receive `403` for the two Audit endpoints in this story.
- Missing, invalid, expired or revoked sessions and inactive users receive `401` under
  the existing session-auth contract.
- Backend actor resolution and authorization are authoritative. Frontend role checks
  are presentation only.
- This story does not add an Audit history or result-query endpoint.

## Scope and explicit exclusions

Included:

- context loading for the canonical MVP Warehouse;
- `SELECTED_PAIRS` and `WHOLE_WAREHOUSE` scope selection;
- strict-integer physical count entry;
- submit-time authoritative stock snapshot;
- atomic AuditSession/AuditLine persistence;
- line and session match/mismatch calculation;
- safe idempotent replay;
- match completion and mismatch recording;
- an explicit guarantee that Audit does not mutate stock.

Excluded:

- Manager review, discrepancy recheck or resolution;
- Adjust request, approval, rejection or application;
- stock correction, Transfer, Pick, Putaway or Receive effects;
- correction/reversal of an Audit;
- Audit history/filter/query UI;
- scanner/device, mobile/offline, notification, alert or AI behavior;
- a generic workflow or generic idempotency framework.

## Preconditions

- The database contains exactly the canonical MVP Warehouse required by the approved
  one-Warehouse model.
- Selected SKU and InternalLocation records exist. Tracked locations remain
  `BACKROOM` and `SALES_SHELF`.
- The actor has an active server-side session and current database role
  `WAREHOUSE_STAFF`.
- `StockBalance` remains authoritative at `(sku_id, location_id)`. Absence of a valid
  pair's balance is interpreted as submit-time system quantity `0` for Audit only and
  does not cause a balance row to be created.

## Audit structure

One Audit consists of one `AuditSession` and one or more `AuditLine` rows.

Each `AuditLine` uniquely represents one `(sku_id, location_id)` pair inside the Audit.
The same pair must not appear twice in one Audit. A pair is not represented as a
separate Audit session.

## Selected scope semantics

### `SELECTED_PAIRS`

- The client sends one or more explicit SKU/location pairs with physical quantities.
- There is no SKU-only implicit expansion.
- There is no location-only implicit expansion.
- Duplicate pairs are invalid.
- Every SKU and location must exist, and every location must belong to the
  server-resolved canonical Warehouse.

### `WHOLE_WAREHOUSE`

- The server resolves the canonical MVP Warehouse; the client never supplies an
  authoritative `warehouse_id`.
- The full scope is the Cartesian product of every current `Sku` row and every tracked
  `InternalLocation` row belonging to the canonical Warehouse.
- The current model has no active/inactive SKU concept, so every existing SKU row is
  included in this slice.
- Context load returns the current full pair set for physical-count entry.
- Submit re-resolves the current full pair set. The submitted pair set must equal it
  exactly.
- If membership changed after context load, return `409 AUDIT_SCOPE_CHANGED`. Do not
  silently add or drop physical-count lines.
- Full-matrix pairs without `StockBalance` use system quantity `0` and do not create a
  balance row.

## System quantity and snapshot semantics

- Context quantities are preview values only.
- System quantity is authoritatively snapshotted at submit.
- Submit validates scope, performs one set-based read of current committed stock for
  the complete pair set, maps a missing valid balance to `0`, and persists those values
  into Audit lines.
- The current slice does not use quantity-based optimistic stale detection.
- No database or row lock is held while a user enters physical counts.
- Audit does not serialize the broader workflow with Pick or Transfer.
- A stock change after the submit-time read does not invalidate the Audit: the persisted
  Audit is a historical record of that snapshot.
- `AuditSession` and all `AuditLine` rows commit or roll back atomically.

## Physical quantity and validation

Audit uses strict integer quantities in this slice. This is an implementation constraint
for `US-AUD-001`; it does not resolve `OQ-012` globally.

- `physical_quantity` must be a JSON integer greater than or equal to zero.
- Boolean, string, float and negative values are rejected.
- Empty scope and duplicate pairs are rejected.
- Unknown SKU/location and cross-Warehouse location references are rejected without
  persistence.
- No active/inactive SKU or location validation is introduced because the current model
  has no such approved concept.

## Discrepancy, result and status semantics

For every line:

```text
quantity_discrepancy = physical_quantity - system_quantity
```

- Persist `system_quantity`, `physical_quantity`, `quantity_discrepancy` and line
  `result`.
- Line `MATCH` requires `quantity_discrepancy == 0`.
- Line `MISMATCH` requires `quantity_discrepancy != 0`.
- Session `MATCH` requires every line to be `MATCH`.
- Session `MISMATCH` applies when at least one line is `MISMATCH`.
- Session status is `MATCH_COMPLETED` for session result `MATCH`.
- Session status is `MISMATCH_RECORDED` for session result `MISMATCH`.
- `MISMATCH_RECORDED` means the discrepancy facts were recorded. It does not mean the
  stock was corrected, reviewed or rechecked.

## Persistence model

### `audit_sessions`

Minimum fields:

| Field | Contract |
|---|---|
| `id` | UUID primary key |
| `warehouse_id` | Required FK to `warehouses`, `RESTRICT` |
| `scope_type` | `SELECTED_PAIRS` or `WHOLE_WAREHOUSE` |
| `result` | `MATCH` or `MISMATCH` |
| `status` | `MATCH_COMPLETED` or `MISMATCH_RECORDED` |
| `audited_by_user_id` | Required FK to `users`, `RESTRICT` |
| `audited_at` | Required timezone-aware timestamp |
| `idempotency_key` | Required, globally unique, case-sensitive opaque key |
| `request_fingerprint` | Required effective-command fingerprint |

Required index: `(warehouse_id, audited_at)`. Existing FK/index conventions should be
followed for `audited_by_user_id`.

### `audit_lines`

Minimum fields:

| Field | Contract |
|---|---|
| `id` | UUID primary key |
| `audit_id` | Required FK to `audit_sessions`, `RESTRICT`, indexed |
| `sku_id` | Required FK to `skus`, `RESTRICT`, indexed as appropriate |
| `location_id` | Required FK to `internal_locations`, `RESTRICT`, indexed as appropriate |
| `system_quantity` | Integer, `>= 0`, immutable snapshot |
| `physical_quantity` | Integer, `>= 0` |
| `quantity_discrepancy` | Integer equal to physical minus system |
| `result` | `MATCH` or `MISMATCH`, consistent with discrepancy |

Required constraints:

- unique `(audit_id, sku_id, location_id)`;
- system and physical quantities non-negative;
- discrepancy consistency;
- line result consistent with zero/non-zero discrepancy;
- source foreign keys use `RESTRICT`.

Do not add recheck actor/time/result, Manager decision, Adjust FK, stock-correction fields
or a generic workflow table.

## Stock no-effect guarantee

Audit reads `StockBalance` but never mutates it. Success, mismatch, validation failure,
scope conflict, idempotent replay and transaction rollback must not:

- insert, update or delete `StockBalance`;
- create Receive, Putaway, Pick or Transfer records;
- create or apply an Adjust;
- persist a Warehouse-total quantity;
- automatically resolve a discrepancy.

A missing balance remains missing after Audit, even when physical quantity is positive.

## API contract

### `GET /api/v1/audits/context`

| Item | Contract |
|---|---|
| Actor | `WAREHOUSE_STAFF` |
| Warehouse | Server-resolved canonical MVP Warehouse; no client `warehouse_id` |
| Output | Current SKU list, tracked locations, full pair membership and preview quantities sufficient for both scope modes |
| Quantity authority | Preview only; POST re-reads current committed stock |
| Effects | Strictly read-only |
| Errors | Existing `401`/`403`; typed error if the canonical Warehouse invariant is unavailable |

The response must provide stable SKU/location identity and code plus preview system
quantity for every current full-matrix pair. A missing `StockBalance` appears as preview
quantity `0` without creating a row.

Response shape:

```json
{
  "warehouse_id": "<uuid>",
  "pairs": [
    {
      "sku_id": "<uuid>",
      "sku": "SKU-001",
      "location_id": "<uuid>",
      "location": "BACKROOM",
      "preview_system_quantity": 12
    }
  ]
}
```

Pairs are returned in canonical deterministic SKU/location identity order. The same
pair identities form the context-load whole-Warehouse membership presented to the UI;
POST still re-resolves membership and quantities independently.

### `POST /api/v1/audits`

Required header:

```http
Idempotency-Key: <opaque case-sensitive value>
```

The key is required, must not be silently trimmed or lowercased, and whitespace-only is
invalid.

Request shape:

```json
{
  "scope_type": "SELECTED_PAIRS",
  "lines": [
    {
      "sku_id": "<uuid>",
      "location_id": "<uuid>",
      "physical_quantity": 10
    }
  ]
}
```

`WHOLE_WAREHOUSE` uses the same line shape; submitted pairs must equal the submit-time
full pair set exactly. The client does not submit authoritative warehouse or system
quantity.

Success response:

```json
{
  "audit_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "scope_type": "SELECTED_PAIRS",
  "result": "MISMATCH",
  "status": "MISMATCH_RECORDED",
  "audited_by_user_id": "<uuid>",
  "audited_at": "<timestamp>",
  "lines": [
    {
      "sku_id": "<uuid>",
      "location_id": "<uuid>",
      "system_quantity": 12,
      "physical_quantity": 10,
      "quantity_discrepancy": -2,
      "result": "MISMATCH"
    }
  ]
}
```

First successful creation returns `201 Created`. The response ordering of lines must be
canonical and deterministic by SKU/location identity.

### Idempotency

The effective-command fingerprint includes only:

- scope type;
- canonical ordered SKU/location pairs;
- physical quantities.

It excludes actor, server-derived Warehouse, system snapshot, discrepancy, result,
status and timestamps.

- Same key and same effective command: safe replay with `200 OK`; return the original
  persisted Audit identity, system snapshot, physical counts, discrepancy, result,
  status and timestamp. Do not re-read or re-snapshot current stock.
- Same key and different effective command: `409 IDEMPOTENCY_KEY_REUSED`, no effect.
- The implementation must use an atomic PostgreSQL claim/insert pattern. An unsafe
  read-before-insert sequence is not acceptable under concurrent requests.
- This is Audit-specific behavior, not a generic idempotency framework.

### Validation and typed errors

| Condition | Result | Effect |
|---|---|---|
| Missing/invalid session | `401` | None |
| Authenticated wrong role | `403` | None |
| Missing/whitespace-only idempotency key | `422 INVALID_IDEMPOTENCY_KEY` | None |
| Empty line set | `422 EMPTY_AUDIT_SCOPE` | None |
| Duplicate pair | `422 DUPLICATE_AUDIT_LINE` | None |
| Invalid strict-integer physical quantity | `422 INVALID_QUANTITY` | None |
| Unknown SKU/location or cross-Warehouse location | typed `404`/`422` following existing reference/integrity convention | None |
| Whole-Warehouse submitted set differs from current full set | `409 AUDIT_SCOPE_CHANGED` | None |
| Same key, different effective command | `409 IDEMPOTENCY_KEY_REUSED` | None |
| Persistence failure | Existing error envelope; rollback session and lines | None |

Implementation must choose stable exact codes for unknown references consistently with
the existing API conventions; it must not change the approved behavior above.

## Concurrency and consistency

- Do not hold a lock while the user counts.
- At submit, validate the complete scope and use one set-based authoritative stock read.
- Missing valid balances map to zero in application result construction; no balance row
  is inserted.
- Persist the session and all lines atomically in one transaction.
- No quantity-based stale conflict exists in this slice.
- For whole-Warehouse mode, membership is re-resolved at submit and compared with the
  submitted set before persistence.
- Audit does not lock or serialize the whole Pick/Transfer workflow and never changes
  stock from its side.
- Idempotency-key claiming must be safe under concurrent identical and conflicting
  requests.

## Frontend contract

Route: `/audits/new`.

Use a one-page Audit table/form with modes `Selected pairs` and `Whole Warehouse`.
Display SKU, location, preview system quantity, physical quantity input and discrepancy
preview. Preview values are informational; the backend response is authoritative.

Required states:

- loading;
- context error;
- scope selection;
- validation;
- submitting;
- `MATCH_COMPLETED` success;
- `MISMATCH_RECORDED` success;
- server error;
- `401` auth recovery;
- `403` forbidden;
- `AUDIT_SCOPE_CHANGED` conflict for whole-Warehouse mode.

Mismatch success must state that the discrepancy was recorded and stock did not change.
Do not add Manager review/recheck UI, Adjust CTA, automatic Adjust navigation,
scanner/device behavior, filters/history or AI.

## Observability

- Reuse the existing stable API error envelope.
- Application logging may include Audit ID, actor ID, scope type, line count and final
  result after commit, but must not expose session tokens or secrets.
- Persisted Audit rows are the durable business record; logs do not replace them.
- No response-time, throughput or retention target is introduced because no such NFR is
  approved.

## Test plan

### Backend and persistence

- selected-pair single-line and multi-line success;
- whole-Warehouse full matrix, including missing balances as zero;
- duplicate pair and empty scope rejection;
- unknown SKU/location and cross-Warehouse rejection;
- boolean, string, float and negative physical quantity rejection;
- zero, positive and negative discrepancy calculations;
- line/session result and status consistency;
- correct actor/time and immutable submit-time system snapshot;
- `401` and three wrong-role `403` cases;
- first request `201`, same-key/same-command replay `200` with the original persisted
  snapshot and timestamp;
- same-key/different-command `409`;
- concurrent same-key atomic-claim behavior;
- whole-Warehouse membership change returns `409 AUDIT_SCOPE_CHANGED` without a write;
- transaction rollback when one line or persistence step fails;
- explicit before/after proof that `StockBalance` and neighboring workflow records are
  unchanged;
- Audit concurrent with Pick/Transfer proves no Audit-side stock mutation.

### Migration

- upgrade, downgrade and re-upgrade;
- tables, FKs, checks, unique constraints and indexes;
- PostgreSQL 17 and 18 compatibility;
- SQLite component smoke is not PostgreSQL migration evidence.

### Frontend

- loading and context error;
- both scope modes and selected-pair add/remove behavior;
- quantity validation and discrepancy preview;
- submitting and both success states;
- mismatch copy explicitly says stock did not change;
- server error, auth recovery, forbidden and scope-changed conflict;
- safe replay renders the persisted historical response.

### Playwright

- Staff completes a selected-pair match Audit;
- Staff records a mismatch and stock remains unchanged;
- whole-Warehouse membership conflict;
- wrong role receives backend `403`;
- retry with the same key does not create a second Audit or resnapshot stock.

## Exact implementation file plan

| Slice | Files | Outcome |
|---|---|---|
| Model/migration | `backend/src/warehouse_api/models.py`; `backend/alembic/versions/20260926_0006_audit_selected_scope.py` | `audit_sessions`, `audit_lines`, constraints and indexes |
| Service/API | new `audit.py`, new `audit_routes.py`, `schemas.py`, `main.py` | Context, submit, snapshot, idempotency and authorization contract |
| Backend tests | new `test_audit.py`, `test_audit_migration.py`, and concurrency coverage as appropriate | AC, errors, replay, rollback and no-effect proof |
| Fixtures | `backend/src/warehouse_api/test_seed.py` only as needed | Deterministic isolated Audit data |
| Frontend | `frontend/src/api.ts`, `App.tsx`, new `AuditPage.tsx`, `styles.css` | `/audits/new` one-page flow |
| Frontend tests | new `AuditPage.test.tsx` | Required states and role/error handling |
| Browser | `frontend/e2e/global-setup.ts`, new `audit.spec.ts` | PostgreSQL-backed browser scenarios |
| Documentation | this spec, Decision Log, Story Specs Index, Traceability and AI Usage Log | Record implementation evidence only after it exists |

## Definition of Done

- `DEC-040` contract is implemented without expanding the canonical story.
- Both scope modes and submit-time snapshot semantics pass automated tests.
- Audit-specific idempotency is concurrency-safe and replay returns the original
  historical result.
- Database constraints protect quantity/discrepancy/result consistency and pair
  uniqueness.
- Backend authorization proves `401`/`403` outcomes.
- Tests prove Audit never mutates `StockBalance` or creates neighboring workflow data.
- Migration cycle passes on PostgreSQL 17 and 18.
- Backend lint/format/tests and frontend lint/typecheck/tests/build pass with fresh output.
- Playwright Audit scenarios pass against PostgreSQL.
- Implementation evidence and Traceability are updated after implementation.
- Human reviews the implementation diff before commit or integration.

## Open questions and boundaries

- `OQ-012` remains open globally. Strict integer is only the current Audit slice
  constraint; UOM, decimal and conversion behavior are not decided.
- `OQ-013` remains `PARTIALLY DECIDED / OPEN` for Manager recheck, discrepancy
  resolution, correction/reversal and broader Audit lifecycle. This story decides only
  `MATCH_COMPLETED` and `MISMATCH_RECORDED` recording semantics.
- `OQ-022` remains open for scanner/device, mobile/offline and external integration.
- `US-AUD-002` owns mismatch recheck, Manager review and discrepancy-resolution paths.
