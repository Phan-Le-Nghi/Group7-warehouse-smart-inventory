# US-AUD-002 Technical Story Spec

## Status and authority

`IMPLEMENTED IN WORKTREE — LOCAL COMPONENT VERIFIED — HUMAN REVIEW PENDING`

Canonical product wording and Acceptance Criteria remain authoritative at
[`../../04-product/stories/US-AUD-002.md`](../../04-product/stories/US-AUD-002.md).
Human review approved the implementation contract below at `DEC-041`. This spec does
not change the canonical Acceptance Criteria and does not close `OQ-012`, the remaining
Audit close/resolve/correction aspects of `OQ-013`, or `OQ-022`.

| Field | Value |
|---|---|
| Story ID | `US-AUD-002` |
| Story | Manager review and mandatory recheck of an Audit discrepancy |
| Owner | Phan Lê Nghi |
| Requirement IDs | `REQ-002`, `REQ-004`, `CAND-REQ-005`, `CAND-REQ-010` |
| Business rules | `CAND-BR-002`, `CAND-BR-010` |
| Decisions | `DEC-014/015/017/018/031/040/041` |
| Verified evidence | `EVD-012/017` for current-state recheck context only |
| Design references | `SCR-08`, `PF-03` |
| Open boundaries | `OQ-012`, remaining `OQ-013`, `OQ-022`; Adjust creation/application remains `US-ADJ-001/002` |

`DEC-041` is a HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC, not verified research
evidence. The worktree implementation follows that contract. Fresh local evidence on
2026-09-26: backend Ruff lint/format PASS and pytest `191 passed, 18 PostgreSQL-only
skipped`; frontend ESLint/TypeScript PASS, Vitest `66 passed`, and production build
PASS; Playwright discovery lists 25 tests including five US-AUD-002 scenarios. SQLite
migration upgrade/downgrade/re-upgrade passes. PostgreSQL 17/18 migration/concurrency
execution and real Chromium/PostgreSQL execution remain pending because no local
`TEST_DATABASE_URL` is available.

## Goal

Allow an authenticated Manager to list and inspect mismatched `AuditLine` records,
enter one physical recheck quantity per mismatch, and persist a current-stock snapshot
and `MATCH` or `MISMATCH` recheck result. The original Audit remains immutable and no
stock or neighboring workflow data changes.

## Actor and authorization

- Only `MANAGER` may use the discrepancy list, detail and recheck endpoints.
- `WAREHOUSE_STAFF` performs the original Audit in `US-AUD-001` and does not perform a
  recheck in this story.
- `WAREHOUSE_STAFF`, `PURCHASING` and `ADMIN` receive `403` for every endpoint in this
  story.
- Missing, invalid, expired or revoked sessions and inactive users receive `401` under
  the existing session-auth contract.
- Backend actor resolution and authorization are authoritative. Frontend role checks
  are presentation only.

## Scope and explicit exclusions

Included:

- Manager-only discrepancy list and detail;
- one discrepancy per mismatched `AuditLine`, identified by `audit_line_id`;
- exactly one Manager recheck per mismatched line;
- submit-time current `StockBalance` snapshot;
- strict-integer recheck physical quantity;
- durable `audit_rechecks` persistence;
- Audit-specific safe idempotent replay;
- line-level Adjust eligibility context when the recheck remains a mismatch;
- strict no-stock-effect and original-Audit immutability guarantees.

Excluded:

- Warehouse Staff recheck or Manager delegation/confirmation flow;
- repeated recheck attempts;
- changing or closing the original `AuditSession` or `AuditLine`;
- creating or applying an Adjust;
- an Adjust form, CTA or automatic navigation;
- Audit correction/reversal or a generic review/workflow engine;
- scanner/device, mobile/offline, notification, alert or AI behavior.

## Preconditions and discrepancy identity

- The parent `AuditSession` exists in the server-resolved canonical MVP Warehouse and
  has status `MISMATCH_RECORDED`.
- The referenced `AuditLine` exists and has result `MISMATCH`.
- `audit_line_id` is the discrepancy identity. A session with three mismatch lines has
  three independent discrepancies.
- Lines with result `MATCH` never appear in the discrepancy list and are not eligible
  for recheck.
- A Manager may recheck eligible lines independently and is not required to submit all
  mismatches in one transaction.

## Original Audit facts and immutability

The list/detail read model exposes the original:

- Audit and Audit-line identity;
- Warehouse, SKU and internal-location identity/code;
- `system_quantity`, `physical_quantity`, `quantity_discrepancy` and line `result`;
- original auditor identity and `audited_at`.

US-AUD-002 never changes the original `AuditSession` or `AuditLine`. In particular,
`MISMATCH_RECORDED`, the original quantities, discrepancy and `MISMATCH` result remain
unchanged after either recheck outcome.

## Recheck snapshot and result semantics

At first successful POST, the backend:

1. validates the Manager and eligible mismatch line;
2. reads current committed `StockBalance` for the line's exact SKU/location;
3. maps a missing valid balance to `0` without creating a balance row;
4. calculates and persists the recheck facts atomically;
5. commits one `AuditRecheck`.

```text
recheck_quantity_discrepancy =
    recheck_physical_quantity - recheck_system_quantity
```

- Recheck result is `MATCH` exactly when the discrepancy is `0`.
- Recheck result is `MISMATCH` exactly when the discrepancy is non-zero.
- The original Audit snapshot and the recheck-time snapshot are distinct evidence.
- Context/list/detail stock values are not authoritative substitutes for the POST-time
  read.
- Recheck `MATCH` does not mark the Audit closed or resolved.
- Recheck `MISMATCH` exposes Adjust eligibility context but does not create an Adjust.

## Quantity validation

This slice uses strict integer quantities without resolving `OQ-012` globally.

- `recheck_physical_quantity` must be a JSON integer from `0` through `2147483647`.
- Boolean, string, float, negative and overflowing values return
  `422 INVALID_RECHECK_QUANTITY`.

## Persistence model

Create a separate `audit_rechecks` table. Do not add recheck columns to `audit_lines`.

| Field | Contract |
|---|---|
| `id` | UUID primary key |
| `audit_line_id` | Required FK to `audit_lines`, `RESTRICT`, unique |
| `recheck_system_quantity` | Integer, `>= 0`, immutable submit-time snapshot |
| `recheck_physical_quantity` | Integer, `0..2147483647` |
| `recheck_quantity_discrepancy` | Integer equal to physical minus system |
| `result` | `MATCH` or `MISMATCH`, consistent with discrepancy |
| `performed_by_user_id` | Required FK to `users`, `RESTRICT`, indexed |
| `performed_at` | Required timezone-aware timestamp |
| `idempotency_key` | Required, globally unique, case-sensitive opaque key |
| `request_fingerprint` | Required 64-character effective-command fingerprint |

Required constraints:

- unique `audit_line_id` for exactly one recheck per discrepancy;
- unique `idempotency_key` for atomic command claiming;
- non-negative system and physical quantities;
- discrepancy and result consistency;
- source foreign keys use `RESTRICT`.

Do not add an Adjust FK, stock-correction field, closed/resolved field, notification
field or generic review/workflow table.

## Exactly-one and idempotency semantics

`POST /api/v1/audit-discrepancies/{audit_line_id}/rechecks` requires:

```http
Idempotency-Key: <opaque case-sensitive value>
```

The key is required, must not be silently trimmed or lowercased, and whitespace-only is
invalid. The effective-command fingerprint contains only:

- `audit_line_id` from the path;
- `recheck_physical_quantity` from the body.

It excludes actor, system snapshot, discrepancy, result and timestamp.

- First successful command: `201 Created`.
- Same key and same effective command: `200 OK`, returning the original persisted
  recheck without re-reading `StockBalance`.
- Same key and different effective command: `409 IDEMPOTENCY_KEY_REUSED`.
- Different key for a line that already has a recheck:
  `409 RECHECK_ALREADY_RECORDED`.
- Concurrent claims must use a safe PostgreSQL atomic insert/claim pattern. A
  read-before-insert-only implementation is not acceptable.
- Replay lookup occurs before eligibility and stock-snapshot work so a historical
  replay cannot acquire a new snapshot.
- A race between different keys for one line produces one durable winner and one
  `RECHECK_ALREADY_RECORDED` result.

This is Audit-recheck-specific behavior, not a generic idempotency framework.

## Relationship to Adjust

US-AUD-002 creates no Adjust record and performs no correction.

The read model exposes derived `adjust_eligible` context:

```text
adjust_eligible = existing recheck exists AND existing recheck result == MISMATCH
```

`adjust_eligible` is context for future `US-ADJ-001`; it is not an Adjust status,
request, approval or application. A recheck `MATCH` is not eligible. No Adjust FK is
stored on `audit_rechecks`.

## Stock and neighboring-workflow no-effect guarantee

List, detail, first creation, replay, validation failure, duplicate conflict,
concurrent loss and rollback must not:

- insert, update or delete `StockBalance`;
- create Pick, Transfer, Putaway, Receive or Adjust records;
- apply a correction;
- update or delete the original `AuditSession` or `AuditLine`.

The only durable write allowed by this story is one valid `audit_rechecks` row.

## API contract

All endpoints are Manager-only and server-scoped to the canonical MVP Warehouse. No
endpoint accepts an authoritative `warehouse_id`.

### `GET /api/v1/audit-discrepancies`

- Returns only original `AuditLine.result == MISMATCH` lines in the canonical Warehouse.
- Includes lines with and without a recheck so the Manager can see the complete
  discrepancy set.
- Returns `200 {"items": []}` when empty.
- Current slice has no pagination, filtering, search or export.
- Results use deterministic `audited_at DESC`, then `audit_line_id DESC` order.

### `GET /api/v1/audit-discrepancies/{audit_line_id}`

Returns one discrepancy with its original facts and optional existing recheck. It does
not re-read current stock and does not expose `idempotency_key` or
`request_fingerprint`.

Shared discrepancy shape:

```json
{
  "audit_id": "<uuid>",
  "audit_line_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "sku": {"id": "<uuid>", "code": "SKU-001"},
  "location": {"id": "<uuid>", "code": "BACKROOM"},
  "original": {
    "system_quantity": 12,
    "physical_quantity": 10,
    "quantity_discrepancy": -2,
    "result": "MISMATCH",
    "audited_by": {"user_id": "<uuid>", "login_identifier": "audit.staff"},
    "audited_at": "<timestamp>"
  },
  "recheck": null,
  "adjust_eligible": false
}
```

When present, `recheck` contains its identity, three quantities, result, performer and
timestamp, but no idempotency/fingerprint fields.

### `POST /api/v1/audit-discrepancies/{audit_line_id}/rechecks`

Request:

```json
{
  "recheck_physical_quantity": 10
}
```

Success/replay response:

```json
{
  "recheck_id": "<uuid>",
  "audit_line_id": "<uuid>",
  "recheck_system_quantity": 12,
  "recheck_physical_quantity": 10,
  "recheck_quantity_discrepancy": -2,
  "result": "MISMATCH",
  "performed_by": {
    "user_id": "<uuid>",
    "login_identifier": "audit.manager"
  },
  "performed_at": "<timestamp>",
  "adjust_eligible": true
}
```

### Validation and typed errors

| Condition | Result | Effect |
|---|---|---|
| Missing/invalid session | `401` | None |
| Authenticated non-Manager | `403` | None |
| Unknown/non-canonical-Warehouse discrepancy | `404 AUDIT_DISCREPANCY_NOT_FOUND` | None |
| Existing line is not an eligible mismatch | `409 AUDIT_DISCREPANCY_NOT_ELIGIBLE` | None |
| Invalid strict-integer quantity | `422 INVALID_RECHECK_QUANTITY` | None |
| Missing/blank/oversized idempotency key | `422 INVALID_IDEMPOTENCY_KEY` | None |
| Same key, different effective command | `409 IDEMPOTENCY_KEY_REUSED` | None |
| Different command/key after the line was rechecked | `409 RECHECK_ALREADY_RECORDED` | None |
| Persistence failure | Existing error envelope; rollback | None |

## Concurrency and consistency

- Do not hold a database lock while the Manager performs the physical count.
- POST uses current committed stock at submission time.
- Do not use quantity-based optimistic stale detection in this slice.
- Do not use `FOR UPDATE` on `StockBalance` merely to read the snapshot.
- A Pick or Transfer committed before the recheck snapshot affects the snapshot; a
  later commit does not rewrite the persisted recheck.
- Eligibility validation, current-stock read, atomic claim, recheck insert and commit
  belong to one transaction.
- Unique constraints and atomic claim semantics protect exactly-one behavior.

## Frontend contract

Main route: `/audit-discrepancies`.

The Manager flow is list → select line → inspect original Audit → enter recheck physical
quantity → submit → inspect `MATCH` or `MISMATCH` result. A detail route may use
`/audit-discrepancies/{audit_line_id}` within the existing path-routing approach.

Required states:

- loading;
- empty;
- discrepancy list;
- detail;
- submitting;
- `MATCH` result;
- `MISMATCH` result;
- already rechecked/read-only result;
- retryable server error;
- `401` auth recovery;
- `403` forbidden.

The UI must visibly separate `ORIGINAL AUDIT` from `MANAGER RECHECK`, show that stock is
unchanged, and remove/disable the input after a recheck exists. It must not show an
Adjust form/CTA, stock-apply action, original-Audit edit or repeated-recheck action.

## Observability

- Reuse the stable API error envelope.
- After commit, application logs may include Audit/recheck/line IDs, Manager actor ID
  and result, but never session tokens, secrets, idempotency keys or fingerprints.
- Persisted `audit_rechecks` rows are the durable evidence; logs do not replace them.
- No unapproved latency, throughput or retention target is introduced.

## Test plan

### Backend and persistence

- Manager list returns only mismatch lines from the canonical Warehouse;
- empty list and deterministic ordering;
- detail includes immutable original facts and optional recheck;
- valid zero and positive strict-integer rechecks;
- recheck becomes `MATCH` and remains `MISMATCH` paths;
- missing valid `StockBalance` snapshots zero without creating a balance;
- original Audit session/line remains unchanged for every path;
- explicit before/after proof that stock and neighboring workflow records are unchanged;
- `401` and all three wrong-role `403` cases;
- unknown, non-mismatch and non-canonical-Warehouse references;
- boolean, string, float, negative and overflow quantity rejection;
- first request `201`; same-key/same-command replay `200` with original snapshot/time;
- same-key/different-command and different-key/same-line conflicts;
- concurrent same-key and different-key atomic-claim behavior;
- rollback on any persistence failure;
- concurrent Pick/Transfer proves current-submit snapshot semantics and no Audit-side
  stock mutation.

### Migration

- upgrade, downgrade and re-upgrade;
- table, FKs, checks, unique constraints and indexes;
- PostgreSQL 17 and 18 compatibility;
- SQLite component smoke is not PostgreSQL migration evidence.

### Frontend

- loading, empty, list and detail;
- original/recheck visual separation;
- strict-integer validation and submitting state;
- `MATCH`, `MISMATCH` and already-rechecked read-only states;
- server error, auth recovery and forbidden;
- no stock mutation or Adjust UI.

### Playwright

- Manager opens a Warehouse Staff-created mismatch and records a matching recheck;
- Manager records a still-mismatching recheck;
- stock and neighboring workflow state remain unchanged before/after;
- safe retry creates only one recheck and preserves the first snapshot;
- different key cannot create a second recheck;
- Warehouse Staff receives a real backend `403`.

## Exact implementation file plan

| Slice | Files | Outcome |
|---|---|---|
| Model/migration | `backend/src/warehouse_api/models.py`; new `backend/alembic/versions/20260926_0007_audit_recheck.py` | `audit_rechecks`, constraints and indexes |
| Query/service/API | new `backend/src/warehouse_api/audit_discrepancy.py`; new `backend/src/warehouse_api/audit_discrepancy_routes.py`; `schemas.py`; `main.py` | Manager list/detail/recheck, snapshot and atomic replay |
| Backend tests | new `test_audit_recheck.py`, `test_audit_recheck_migration.py`, `test_audit_recheck_concurrency.py` | AC, auth, replay, rollback, snapshot and no-effect proofs |
| Fixtures | `backend/src/warehouse_api/test_seed.py` | Isolated mismatch/recheck scenarios and effect snapshots |
| Frontend | `frontend/src/api.ts`, `App.tsx`, new `AuditDiscrepancyPage.tsx`, `styles.css` | `/audit-discrepancies` Manager flow |
| Frontend tests | new `AuditDiscrepancyPage.test.tsx`; `App.test.tsx` | Required states and role/error handling |
| Browser | `frontend/e2e/global-setup.ts` only as needed; new `audit-recheck.spec.ts` | PostgreSQL-backed Manager scenarios |
| Documentation | this spec, Decision Log, Open Questions, Story Specs Index, Traceability and AI Usage Log | Approved contract now; implementation evidence only after it exists |

## Implementation slices

1. `audit_rechecks` model and migration.
2. Manager discrepancy list/detail query.
3. Recheck snapshot, atomic idempotency and exactly-one service.
4. Authorization, schemas and routes.
5. Backend, migration and concurrency tests.
6. Manager discrepancy UI.
7. Frontend component tests.
8. PostgreSQL-backed Playwright scenarios.
9. Implementation evidence and traceability update.

## Definition of Done

- `DEC-041` contract is implemented without expanding the canonical story.
- Manager-only list/detail/recheck behavior passes authorization tests.
- Exactly one recheck and safe historical replay are concurrency-safe.
- Original Audit facts remain immutable and the session remains
  `MISMATCH_RECORDED`.
- Tests prove the strict stock and neighboring-workflow no-effect guarantee.
- Recheck mismatch exposes context only and creates no Adjust.
- Migration cycle passes PostgreSQL 17 and 18.
- Backend lint/format/tests and frontend lint/typecheck/tests/build pass with fresh
  output.
- Playwright scenarios pass against PostgreSQL.
- Implementation evidence and Traceability are updated after implementation.
- Human reviews the implementation diff before commit or integration.

## Current implementation evidence

- `audit_rechecks` model and Alembic revision `20260926_0007` implement only the
  approved recheck fields, constraints, unique claims and performer index; no
  speculative `audit_lines` index was added.
- Manager-only list/detail/recheck routes, shared discrepancy shape, current-stock
  snapshot, missing-zero behavior, typed conflicts and derived `adjust_eligible` are
  implemented.
- The `/audit-discrepancies` master/detail UI implements attempt-scoped idempotency,
  immutable original evidence, read-only persisted rechecks and backend-authoritative
  `401`/`403` handling.
- Local SQLite/component evidence is PASS as recorded above. The five PostgreSQL-only
  US-AUD-002 concurrency/workflow-race tests are present but skipped locally; CI must
  provide PostgreSQL 17/18 evidence. Five Chromium scenarios are discovered but not
  locally executed.

## Open questions and boundaries

- `OQ-012` remains open globally. Strict integer is only a current-slice constraint;
  UOM, decimal quantities and conversion behavior are not decided.
- `OQ-013` remains `PARTIALLY DECIDED / OPEN`. `DEC-041` decides one Manager recheck
  record and Adjust-eligibility context, but does not define Audit close, resolve,
  correction or reversal semantics.
- `OQ-022` remains open for scanner/device, mobile/offline and external integration.
- A `MATCH` recheck does not imply `CLOSED` or `RESOLVED`; a `MISMATCH` recheck does not
  imply an Adjust exists.
