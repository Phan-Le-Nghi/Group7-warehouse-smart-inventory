# US-ADJ-001 Technical Story Spec

## Status and authority

`IMPLEMENTATION-READY — HUMAN APPROVED`

Canonical product wording and Acceptance Criteria remain authoritative at
[`../../04-product/stories/US-ADJ-001.md`](../../04-product/stories/US-ADJ-001.md).
The implementation contract below was human approved at `DEC-042`. It does not
change the canonical Acceptance Criteria and does not close `OQ-012`, the broader
Audit/Adjust lifecycle aspects of `OQ-013`, `OQ-022`, or the open attachment
storage/provider/policy boundary.

| Field | Value |
|---|---|
| Story ID | `US-ADJ-001` |
| Story | Warehouse Staff creates an Adjust request |
| Owner | Đặng Thị Thanh Ngân |
| Requirement IDs | `REQ-001/002/003`, `CAND-REQ-008/010` |
| Business rules | `CAND-BR-002/011/012` |
| Decisions | `DEC-015/017/018/031/041/042` |
| Verified evidence | `EVD-012/013/017` for current-state recheck/escalation context only |
| Design references | `SCR-09`, `PF-03` |
| Open boundaries | `OQ-012`, broader `OQ-013`, `OQ-022`; attachment storage/provider/policy; Manager decision/apply remains `US-ADJ-002` |

`DEC-042` is a HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC, not verified
research evidence. No application code, migration or automated test was created
while finalizing this document.

## Goal

Allow an authenticated Warehouse Staff actor to create one durable Adjust request
for an exact `AuditRecheck` whose result remains `MISMATCH`. The backend derives
the requested signed change from immutable recheck evidence, records a mandatory
reason and preserves enough facts for future Manager review in `US-ADJ-002`, while
leaving all stock and Audit evidence unchanged.

## Actor and authorization

- Only `WAREHOUSE_STAFF` may read an Adjust creation context and create an Adjust
  request in this story.
- `MANAGER`, `PURCHASING` and `ADMIN` receive `403` for both endpoints.
- Missing, invalid, expired or revoked sessions and inactive users receive `401`
  under the existing session-auth contract.
- Backend actor resolution and authorization are authoritative. Frontend role
  checks are presentation only.
- Manager read, approve, reject and apply behavior belongs to `US-ADJ-002`.

## Scope and explicit exclusions

Included:

- Staff-readable context for one exact `audit_recheck_id`;
- database-derived eligibility from the exact recheck;
- backend-derived signed requested change;
- mandatory normalized free-text reason;
- one durable request per recheck;
- Adjust-specific safe idempotent replay;
- initial `PENDING_MANAGER_DECISION` state;
- strict stock, Audit and neighboring-workflow no-effect guarantees.

Excluded:

- Manager list, detail, approve, reject or apply behavior;
- stock reread, stale-stock conflict or negative-stock apply validation at request
  creation;
- request recreation/reopening after rejection;
- attachment upload, storage, metadata/reference or provider integration;
- Adjust history or generic Staff request list/detail;
- Audit close/resolve/correction/reversal;
- scanner/device, mobile/offline, notification, alert or AI behavior;
- a generic workflow or generic idempotency framework.

## Eligibility and source identity

An Adjust request is eligible exactly when:

```text
AuditRecheck exists
AND AuditRecheck.result == MISMATCH
AND its AuditLine/AuditSession belongs to the canonical MVP Warehouse
```

- The backend resolves eligibility from persisted database facts.
- The client cannot supply or override `adjust_eligible`, Warehouse, SKU,
  location, source quantities, requested change or status.
- A missing recheck, a `MATCH` recheck, a non-canonical-Warehouse reference, a
  wrong role or an existing Adjust request is blocked.
- `audit_recheck_id` is the required source link. The related `AuditLine` and
  `AuditSession` are reached through `AuditRecheck -> AuditLine -> AuditSession`.
- The original Audit and recheck remain immutable.

## Requested quantity semantics

Warehouse Staff never enters an adjustment quantity. The backend derives:

```text
requested_change =
    recheck_physical_quantity - recheck_system_quantity
```

Examples:

- system `10`, physical `8` -> requested change `-2`;
- system `10`, physical `13` -> requested change `+3`.

The request preserves the recheck intent by snapshotting:

- `recheck_system_quantity_snapshot`;
- `recheck_physical_quantity_snapshot`;
- the derived signed `requested_change`;
- the source SKU and internal location.

All snapshot values come from the exact source recheck and its parent Audit line,
never from the client. A valid source `MISMATCH` necessarily produces a non-zero
requested change.

## Stock and stale-state semantics

US-ADJ-001 does not read `StockBalance` to recalculate the request and does not
compare current stock with the recheck snapshot. There is no create-time stale
conflict.

The request remains a durable statement of the exact recheck intent. Future
`US-ADJ-002` must read current stock and decide approved-apply safety, including
negative-stock and stale-state behavior. This story does not define or perform
that decision.

## Reason and attachment

`reason` is:

- required free text;
- normalized by trimming surrounding whitespace before fingerprinting and
  persistence;
- invalid when empty after trimming;
- limited to at most 500 characters after trimming.

Invalid reason returns `422 INVALID_REASON`. This slice adds no reason enum,
predefined taxonomy or separate note field.

Attachment/evidence remains optional at product level. Actual attachment upload,
storage, metadata/reference and provider integration are deferred. The minimum
current schema contains no attachment field and no file I/O. A request without an
attachment must succeed when all other conditions pass. Attachment
storage/provider/policy remains `OPEN / TBD`.

## Persistence model

Create an `adjust_requests` table with the minimum durable fields below.

| Field | Contract |
|---|---|
| `id` | UUID primary key |
| `audit_recheck_id` | Required FK to `audit_rechecks`, `RESTRICT`, unique |
| `sku_id` | Required FK to `skus`, `RESTRICT`; snapshot identity derived from source Audit line |
| `location_id` | Required FK to `internal_locations`, `RESTRICT`; snapshot identity derived from source Audit line |
| `recheck_system_quantity_snapshot` | Required non-negative integer copied from source recheck |
| `recheck_physical_quantity_snapshot` | Required non-negative integer copied from source recheck |
| `requested_change` | Required signed integer equal to physical snapshot minus system snapshot; non-zero |
| `reason` | Required normalized string, length `1..500` |
| `status` | Required exact value `PENDING_MANAGER_DECISION` in this slice |
| `requested_by_user_id` | Required FK to `users`, `RESTRICT`, indexed |
| `requested_at` | Required timezone-aware timestamp |
| `idempotency_key` | Required, globally unique, case-sensitive opaque key |
| `request_fingerprint` | Required effective-command fingerprint |

Required relational/integrity protection:

- unique `audit_recheck_id` for exactly one request per recheck;
- unique `idempotency_key` for atomic command claiming;
- snapshot discrepancy consistency;
- non-zero `requested_change`;
- normalized non-empty reason with maximum length 500;
- status constrained to `PENDING_MANAGER_DECISION` for this slice;
- source foreign keys use `RESTRICT`.

Do not add a redundant `audit_line_id`, attachment placeholder, approval/rejection
actor/time, applied quantity/time, stock snapshot at request creation, close/reopen
field or generic workflow table.

## Initial status and multiplicity

- Every newly created request has status `PENDING_MANAGER_DECISION`.
- US-ADJ-001 never creates `APPROVED`, `REJECTED` or `APPLIED`.
- Exactly one Adjust request may exist for each `AuditRecheck` in the current
  slice.
- A different key after a request exists returns
  `409 ADJUSTMENT_ALREADY_EXISTS`.
- Recreation or reopening after rejection is not supported by this story and
  requires a future approved decision.

## Idempotency and concurrency

`POST /api/v1/adjustments` requires:

```http
Idempotency-Key: <opaque case-sensitive value>
```

The effective-command fingerprint contains only:

- `audit_recheck_id` from the request body;
- the normalized trimmed `reason`.

It excludes actor, Warehouse, SKU/location, derived snapshots/change, status and
timestamp.

- First successful command: `201 Created`.
- Same key and same effective command: `200 OK`, returning the original persisted
  Adjust request.
- Replay lookup occurs before current eligibility/source derivation so historical
  replay does not re-read stock or re-derive the persisted request.
- Same key and different effective command:
  `409 IDEMPOTENCY_KEY_REUSED`.
- Different key for a recheck that already has a request:
  `409 ADJUSTMENT_ALREADY_EXISTS`.
- Concurrent claims use a PostgreSQL-safe atomic insert/claim pattern backed by
  both unique constraints. A read-before-insert-only implementation is not
  acceptable.
- A race between different keys for one recheck produces one durable winner and
  one `ADJUSTMENT_ALREADY_EXISTS` result.

This is Adjust-request-specific behavior, not a generic idempotency framework.

## Stock and neighboring-workflow no-effect guarantee

Context read, first creation, replay, validation failure, duplicate conflict,
concurrent loss and rollback must not:

- insert, update or delete `StockBalance`;
- create Pick, Transfer, Putaway or Receive records;
- approve, reject or apply an Adjust;
- update or delete `AuditSession`, `AuditLine` or `AuditRecheck`;
- reread stock to replace the source recheck intent.

The only durable business mutation allowed by this story is one valid
`adjust_requests` row.

## API contract

Both endpoints are Warehouse-Staff-only and server-scoped to the canonical MVP
Warehouse.

### `GET /api/v1/adjustments/context/{audit_recheck_id}`

The endpoint:

- revalidates the exact recheck from the database;
- requires recheck result `MISMATCH` and canonical-Warehouse ownership;
- performs no stock read and no write;
- returns original Audit evidence, recheck evidence, derived requested change and
  an optional existing Adjust summary.

Response shape:

```json
{
  "audit_recheck_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "sku": {"id": "<uuid>", "code": "SKU-001"},
  "location": {"id": "<uuid>", "code": "BACKROOM"},
  "original_audit": {
    "audit_id": "<uuid>",
    "audit_line_id": "<uuid>",
    "system_quantity": 10,
    "physical_quantity": 8,
    "quantity_discrepancy": -2
  },
  "recheck": {
    "recheck_system_quantity": 10,
    "recheck_physical_quantity": 8,
    "recheck_quantity_discrepancy": -2,
    "result": "MISMATCH",
    "performed_at": "<timestamp>"
  },
  "requested_change": -2,
  "existing_adjustment": null
}
```

When present, `existing_adjustment` exposes the persisted request identity,
normalized reason, requested change, status, requester identity and request time.
It does not expose the idempotency key or fingerprint.

### `POST /api/v1/adjustments`

Required header:

```http
Idempotency-Key: <opaque case-sensitive value>
```

Request:

```json
{
  "audit_recheck_id": "<uuid>",
  "reason": "Count confirmed after mandatory recheck"
}
```

Extra fields are rejected. In particular, the client cannot submit Warehouse,
SKU, location, quantity snapshots, requested change or status.

Success/replay response:

```json
{
  "adjustment_id": "<uuid>",
  "audit_recheck_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "sku": {"id": "<uuid>", "code": "SKU-001"},
  "location": {"id": "<uuid>", "code": "BACKROOM"},
  "recheck_system_quantity_snapshot": 10,
  "recheck_physical_quantity_snapshot": 8,
  "requested_change": -2,
  "reason": "Count confirmed after mandatory recheck",
  "status": "PENDING_MANAGER_DECISION",
  "requested_by": {
    "user_id": "<uuid>",
    "login_identifier": "warehouse.staff"
  },
  "requested_at": "<timestamp>"
}
```

### Validation and typed outcomes

| Condition | Result | Effect |
|---|---|---|
| Missing/invalid session | `401` | None |
| Authenticated Manager/Purchasing/Admin | `403` | None |
| Unknown or non-canonical-Warehouse recheck | `404` using the existing non-disclosure error convention | None |
| Recheck result is not `MISMATCH` | `409` ineligible context | None |
| Reason blank after trim or longer than 500 | `422 INVALID_REASON` | None |
| Missing/blank/oversized idempotency key | `422 INVALID_IDEMPOTENCY_KEY` | None |
| Same key, different effective command | `409 IDEMPOTENCY_KEY_REUSED` | None |
| Different key after request exists | `409 ADJUSTMENT_ALREADY_EXISTS` | None |
| Persistence failure | Existing error envelope; rollback | None |

The exact internal code names for the two source-context failures may follow the
existing API naming convention during implementation; their HTTP semantics and
no-effect behavior above are fixed. No stock/stale error exists in this story.

## Frontend contract

The Warehouse Staff flow opens one exact eligible context, reviews immutable
Audit/recheck evidence, enters a reason and submits the request. The current slice
does not add an own-request list, history, generic detail page or Manager UI.

Required states:

- loading eligible context;
- eligible context with SKU/location, original Audit and recheck quantities;
- visible derived signed requested change that Staff cannot edit;
- required reason validation and 500-character limit;
- submitting;
- success with `PENDING_MANAGER_DECISION` and explicit stock-unchanged copy;
- existing request summary after context reload;
- ineligible/not-found, duplicate, retryable server error;
- `401` auth recovery and `403` forbidden.

No attachment input is shown in this slice. The UI must not show Manager
approve/reject/apply controls or claim stock was changed.

## Observability

- Reuse the stable API error envelope.
- After commit, application logs may include Adjust request ID, source recheck ID,
  Staff actor ID and status, but never session tokens, reason text, idempotency
  keys or fingerprints.
- The durable request is the audit evidence; logs do not replace it.
- No unapproved latency, throughput or retention target is introduced.

## Test plan

### Backend and persistence

- eligible `MISMATCH` recheck creates one request with derived snapshots/change;
- system `10`, physical `8` persists `-2`; system `10`, physical `13` persists
  `+3`;
- client cannot submit authoritative Warehouse/SKU/location/quantity/status;
- missing recheck, `MATCH` recheck and non-canonical-Warehouse source are blocked;
- reason trimming, blank, exactly 500 and over 500 cases;
- first request `201`; same-key/same-command replay `200` with original facts/time;
- same-key/different-command and different-key/same-recheck conflicts;
- concurrent same-key and different-key atomic-claim behavior;
- `401` and all three wrong-role `403` cases;
- context before/after creation and existing-request summary;
- explicit before/after proof that `StockBalance`, Audit/Recheck and neighboring
  workflow records are unchanged;
- no create-time stock read/recalculation behavior;
- rollback on persistence failure.

### Migration

- upgrade, downgrade and re-upgrade;
- table, FKs, checks, unique constraints and indexes;
- snapshot/change, reason and status consistency;
- PostgreSQL 17 and 18 compatibility;
- SQLite component smoke is not PostgreSQL migration evidence.

### Frontend

- loading and eligible evidence rendering;
- requested change is visible and non-editable;
- reason trimming/required/length validation;
- submitting, success and stock-unchanged copy;
- existing request summary, duplicate and ineligible states;
- server error, auth recovery and forbidden;
- no attachment, Manager-decision or stock-apply UI.

### Playwright

- Warehouse Staff opens an existing mismatching recheck and creates a request;
- request persists and context reload shows its existing summary;
- stock, original Audit and recheck remain unchanged before/after;
- safe retry creates only one request and preserves the first facts/time;
- different key cannot create a second request;
- Manager receives a real backend `403` for context/create.

## Exact implementation file plan

| Slice | Files | Outcome |
|---|---|---|
| Model/migration | `backend/src/warehouse_api/models.py`; new Alembic revision after `20260926_0007_audit_recheck.py` | Minimum constrained `adjust_requests` table |
| Domain/API | new `backend/src/warehouse_api/adjustment.py`; new `backend/src/warehouse_api/adjustment_routes.py`; `schemas.py`; `main.py` | Staff context, atomic create/replay and typed outcomes |
| Backend tests | new `test_adjustment.py`, `test_adjustment_migration.py`, `test_adjustment_concurrency.py` | AC, auth, derivation, replay, rollback, concurrency and no-effect proofs |
| Fixtures | `backend/src/warehouse_api/test_seed.py` | Isolated mismatch/match/existing-request scenarios and effect snapshots |
| Frontend | `frontend/src/api.ts`, `App.tsx`, new `AdjustmentPage.tsx`, `styles.css` | Exact-context Staff request flow using existing path-routing approach |
| Frontend tests | new `AdjustmentPage.test.tsx`; `api.test.ts`; `App.test.tsx` | Required states, validation and role/error handling |
| Browser | `frontend/e2e/global-setup.ts` only as needed; new `adjustment.spec.ts` | PostgreSQL-backed Staff scenarios |
| Documentation | this spec, Decision Log, Open Questions, Story Specs Index, Traceability and AI Usage Log | Approved contract now; implementation evidence only after it exists |

## Implementation slices

1. `adjust_requests` model and migration.
2. Exact source-context query and eligibility derivation.
3. Snapshot/change derivation and atomic idempotent creation.
4. Authorization, schemas, routes and typed outcomes.
5. Backend, migration and concurrency tests.
6. Warehouse Staff Adjust request UI.
7. Frontend component/API tests.
8. PostgreSQL-backed Playwright scenarios.
9. Implementation evidence and traceability update.

## Definition of Done

- `DEC-042` contract is implemented without expanding the canonical story.
- Only Warehouse Staff can read context/create; verified `401` and `403` behavior
  exists.
- Eligibility is derived from one exact `MISMATCH` recheck in the canonical
  Warehouse.
- Staff cannot edit quantity; source snapshots and signed change are backend
  derived and durably consistent.
- Exactly one request per recheck and safe historical replay are concurrency-safe.
- Reason normalization and 500-character limit are enforced consistently.
- Request starts only in `PENDING_MANAGER_DECISION`.
- Tests prove strict stock, Audit/Recheck and neighboring-workflow no-effect.
- No attachment I/O, Manager decision or apply behavior is introduced.
- Migration cycle passes PostgreSQL 17 and 18.
- Backend lint/format/tests and frontend lint/typecheck/tests/build pass with fresh
  output.
- Playwright scenarios pass against PostgreSQL.
- Implementation evidence and Traceability are updated after implementation.
- Human reviews the implementation diff before commit or integration.

## Open questions and boundaries

- `OQ-012` remains open globally. This story derives from the existing integer
  recheck slice and does not canonicalize UOM, decimal quantity or conversion.
- `OQ-013` remains `PARTIALLY DECIDED / OPEN`. `DEC-042` decides current Adjust
  request creation only; Manager decision/apply, stale apply handling, rejected-case
  closure and broader Audit/Adjust lifecycle remain outside this story.
- `OQ-022` remains open for scanner/device, mobile/offline and external integration.
- Attachment is optional, but storage/provider/policy and actual file I/O remain
  `OPEN / TBD` and are not implemented in this slice.

