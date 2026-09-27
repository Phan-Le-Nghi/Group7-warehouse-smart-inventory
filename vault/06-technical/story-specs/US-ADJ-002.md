# US-ADJ-002 Technical Story Spec

## Status and authority

`IMPLEMENTATION-READY — HUMAN APPROVED`

Canonical product wording and Acceptance Criteria remain authoritative at
[`../../04-product/stories/US-ADJ-002.md`](../../04-product/stories/US-ADJ-002.md).
The implementation contract below was human approved at `DEC-043`. It does not
change the canonical Acceptance Criteria and does not close global quantity
modeling at `OQ-012`, broader Audit correction/reversal lifecycle at `OQ-013`,
or device/integration behavior at `OQ-022`.

| Field | Value |
|---|---|
| Story ID | `US-ADJ-002` |
| Story | Manager reviews, approves or rejects an Adjust request and applies stock only on valid approval |
| Owner | Đặng Thị Thanh Ngân |
| Requirement IDs | `REQ-001/002/003`, `CAND-REQ-003/008/010/011`, `NFR-001/002/004` |
| Business rules | `CAND-BR-002/011/013/015` |
| Decisions | `DEC-010/015/017/019/021/022/031/041/042/043` |
| Verified evidence | `EVD-012/013/017` for current-state recheck/escalation context only |
| Design references | `SCR-10`, `PF-03` |
| Open boundaries | `OQ-012`; broader Audit correction/reversal aspects of `OQ-013`; `OQ-022`; attachment storage/provider/policy |

`DEC-043` is a HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC, not verified
research evidence. No application code, migration or automated test was created
while finalizing this document.

## Goal

Allow an authenticated Manager to read the pending Adjust work queue, inspect
one exact Adjust request, and record exactly one terminal decision. Reject never
changes stock. Approve atomically validates current authoritative stock, applies
the immutable signed `requested_change`, and persists the decision and apply
evidence. Stale or negative approval attempts leave both stock and request state
unchanged.

## Actor and authorization

- Only `MANAGER` may use the Manager Adjust list, detail and decision endpoints.
- `WAREHOUSE_STAFF`, `PURCHASING` and `ADMIN` receive `403` from all three.
- Missing, invalid, expired or revoked sessions and inactive users receive `401`
  under the existing session-auth contract.
- Backend actor resolution and authorization are authoritative. Frontend role
  checks are presentation only.
- The Manager identity and decision time come from the backend; the client never
  submits either value.

## Scope and explicit exclusions

Included:

- pending-only Manager work queue;
- exact detail for pending and terminal requests;
- immutable source Audit, recheck and request evidence;
- required-idempotency approve/reject decision;
- stale-stock and non-negative validation under row locks;
- concurrency-safe zero-balance materialization during approve only;
- atomic stock apply plus terminal evidence;
- terminal read-only UI states.

Excluded:

- historical list, search, export, advanced filters or advanced pagination;
- current-stock preview before decision;
- Manager-entered quantity, quantity edit or partial approval;
- reopening, retrying or recreating an Adjust from the same rejected recheck;
- attachment behavior, Audit correction/reversal or repeated recheck;
- generic workflow, approval, idempotency, locking or stock-movement framework;
- scanner/device, mobile/offline, notification, alert or AI behavior.

## Manager read scope

`GET /api/v1/adjustments?status=PENDING_MANAGER_DECISION` returns only the
pending work queue for the server-resolved canonical Warehouse. The current
slice accepts exactly the `PENDING_MANAGER_DECISION` filter and does not expose
terminal history through the list.

`GET /api/v1/adjustments/{adjustment_id}` returns exact detail when status is
`PENDING_MANAGER_DECISION`, `APPLIED` or `REJECTED`, allowing a decision response
or page reload to render a terminal read-only state.

List/detail expose the Adjust identity, requester/time, reason, SKU/location,
original Audit evidence, Manager Recheck evidence, immutable snapshots and
`requested_change`, current status and any applicable decision/apply evidence.
They never expose creation or decision idempotency keys/fingerprints. They do not
read or display current `StockBalance` in this slice and perform no write.

## Preconditions and immutable source consistency

The decision service loads the exact persisted `AdjustRequest` and reaches its
source through `AdjustRequest -> AuditRecheck -> AuditLine -> AuditSession`.
Before a decision commits, it verifies:

- the request belongs to the server-resolved canonical Warehouse;
- the source recheck exists and remains `MISMATCH`;
- persisted request SKU/location match the source Audit line;
- persisted system/physical snapshots match the source recheck;
- `requested_change` equals physical snapshot minus system snapshot and is
  non-zero;
- status is still `PENDING_MANAGER_DECISION`, except historical decision replay
  handled under the idempotency contract.

The client cannot supply or override Warehouse, SKU, location, source evidence,
snapshots, requested change, status, current stock, decision actor/time or apply
evidence. Original Audit/Recheck facts and the request intent fields remain
immutable.

## Approve semantics

Manager approves the exact immutable `requested_change`; there is no quantity
input, edit or partial approval.

After the exact balance row has been materialized if absent and locked, approval
requires:

```text
current_stock == recheck_system_quantity_snapshot
```

If that stale check passes:

```text
candidate_quantity = current_stock + requested_change
```

The service does not set stock blindly to the old physical snapshot, rederive
the change, or rebase the old change onto a different current quantity.

If `candidate_quantity >= 0`, the same transaction updates only the exact
persisted SKU/location balance and transitions the request to `APPLIED` with
decision/application evidence. Approve and apply are one atomic action; there is
no `APPROVED` or `APPROVED_APPLIED` state.

## Stale and negative-stock behavior

If locked authoritative current stock differs from the persisted recheck system
snapshot, approval returns `409 ADJUSTMENT_STALE`:

- no stock update;
- no successful decision or decision-idempotency evidence;
- status remains `PENDING_MANAGER_DECISION`;
- no automatic rejection.

If the candidate quantity is negative, approval returns
`409 INSUFFICIENT_STOCK_FOR_ADJUSTMENT` with the same no-effect and still-pending
guarantees. This defensive validation remains required even when valid snapshots
make the branch uncommon.

The Manager may reject the old request. If the discrepancy still requires
handling, recovery is a fresh Audit -> Recheck -> Adjust request chain. The old
request is never rebased.

## Missing StockBalance rule

Only inside an approve transaction, a missing exact SKU/location balance is
materialized as zero using a conflict-safe insert. The service then selects the
exact balance `FOR UPDATE` and re-reads its authoritative quantity before stale
and negative validation. A lock attempt on a nonexistent row is not treated as
sufficient serialization.

A positive change may proceed from materialized/current zero only when the
persisted recheck system snapshot is also zero. Concurrent creation that results
in a different current quantity is classified as `ADJUSTMENT_STALE`. A negative
candidate is classified as `INSUFFICIENT_STOCK_FOR_ADJUSTMENT`. No balance row is
created by list, detail, reject or any failed transaction that rolls back.

## Reject semantics

Reject is valid only for a pending request and requires `rejection_reason`:

- free text, trimmed before fingerprinting and persistence;
- non-empty after trimming;
- maximum 500 characters;
- absent/forbidden for approve.

Invalid rejection reason returns `422 INVALID_REJECTION_REASON`. Reject locks
only the exact request, reads or locks no `StockBalance`, transitions to
`REJECTED`, records decision evidence, and has zero stock effect.

`REJECTED` is terminal. The request cannot reopen or return to pending, and the
unique source link continues to prevent another Adjust request for the same
`AuditRecheck`.

## Status lifecycle and persistence

Allowed status values are exactly:

```text
PENDING_MANAGER_DECISION
APPLIED
REJECTED
```

Extend `adjust_requests` with nullable decision-specific fields:

| Field | Contract |
|---|---|
| `decided_by_user_id` | FK to `users`, `RESTRICT`; backend-derived Manager |
| `decided_at` | Timezone-aware backend decision timestamp |
| `rejection_reason` | Normalized `1..500` only for `REJECTED` |
| `applied_stock_before` | Non-negative authoritative locked quantity, required only for `APPLIED` |
| `applied_stock_after` | Non-negative committed candidate, required only for `APPLIED` |
| `decision_idempotency_key` | Nullable until successful terminal decision; globally unique opaque case-sensitive key |
| `decision_request_fingerprint` | Nullable until successful terminal decision; SHA-256 effective-command fingerprint |

Required state constraints:

- pending: all decision, application and decision-idempotency fields are null;
- applied: actor/time, before/after and decision-idempotency fields are non-null;
  rejection reason is null;
- rejected: actor/time, normalized rejection reason and decision-idempotency
  fields are non-null; application fields are null;
- applied stock satisfies
  `applied_stock_after = applied_stock_before + requested_change` and both values
  are non-negative;
- fingerprint is null or exactly 64 characters; rejection reason is null or
  trimmed with length `1..500`.

No separate application table, duplicated `applied_change`, generic movement
ledger or generic decision table is introduced.

## Decision idempotency

`POST /api/v1/adjustments/{adjustment_id}/decision` requires an opaque,
case-sensitive `Idempotency-Key` of at most 255 characters. Decision fields are
separate from the existing request-creation idempotency fields.

The canonical effective-command fingerprint contains only:

- path `adjustment_id`;
- `decision` (`APPROVE` or `REJECT`);
- normalized `rejection_reason`, or null for approve.

It excludes actor, current stock, before/after values, timestamps and original
creation fields.

- First successful committed decision: `200 OK`.
- Same key and same effective command: `200 OK` with the historical persisted
  response, without rereading or reapplying stock.
- Same key and different command: `409 IDEMPOTENCY_KEY_REUSED`.
- Different key after terminal decision: `409 ADJUSTMENT_NOT_PENDING`.
- Failed stale/negative/validation attempts do not populate decision idempotency
  fields and therefore do not become successful historical replays.

Historical lookup occurs before pending-state validation where applicable, but
the request-row lock and database uniqueness remain authoritative for races. No
raw uniqueness error or unhandled `500` may escape.

## Atomicity, locking and concurrency

Approve uses one PostgreSQL transaction in this order:

1. authenticate and authorize Manager;
2. look up a historical decision-idempotency replay when applicable;
3. select the exact `AdjustRequest FOR UPDATE`;
4. verify it is pending;
5. validate immutable source consistency;
6. conflict-safe insert zero `StockBalance` if the exact row is missing;
7. select the exact `StockBalance FOR UPDATE`;
8. read authoritative current quantity;
9. perform stale validation;
10. perform non-negative candidate validation;
11. update the balance;
12. persist `APPLIED`, actor/time, before/after and decision idempotency facts;
13. commit once.

Reject locks the exact request, validates pending state, writes `REJECTED`
evidence and commits once without a stock read or lock.

Approve/approve, approve/reject and reject/reject races produce exactly one
terminal winner. A loser receives same-key historical replay where applicable;
otherwise it receives `409 ADJUSTMENT_NOT_PENDING`. Approved Adjust serializes on
the same exact balance row used by Pick, Transfer and Putaway stock mutations.
Receive has no `StockBalance` mutation. Locking remains story-specific; no generic
locking framework is added.

## API contract

All routes below are Manager-only and server-scoped to the canonical Warehouse.

### `GET /api/v1/adjustments?status=PENDING_MANAGER_DECISION`

Returns `200` with `{ "items": [] }` when no pending work exists. Items contain
the minimum queue identity and review summary. This contract does not assign
business priority or user-selectable sorting to the queue. No terminal history,
current balance, idempotency fact or advanced query feature is exposed.

### `GET /api/v1/adjustments/{adjustment_id}`

Returns the exact pending or terminal review model described above. Unknown or
out-of-canonical-Warehouse identity uses `404 ADJUSTMENT_NOT_FOUND`.

### `POST /api/v1/adjustments/{adjustment_id}/decision`

Required header:

```http
Idempotency-Key: <opaque case-sensitive value>
```

Approve request:

```json
{"decision": "APPROVE"}
```

Reject request:

```json
{"decision": "REJECT", "rejection_reason": "Count evidence is not accepted"}
```

Extra authoritative fields are rejected. Approve must not contain a rejection
reason. Success and historical replay both return `200` with the exact terminal
detail response.

### Typed outcomes

| Condition | Result | Effect |
|---|---|---|
| Missing/invalid session | `401` | None |
| Authenticated Staff/Purchasing/Admin | `403 FORBIDDEN` | None |
| Unknown/out-of-Warehouse request | `404 ADJUSTMENT_NOT_FOUND` | None |
| Different-key decision after terminal state | `409 ADJUSTMENT_NOT_PENDING` | None |
| Locked stock differs from recheck system snapshot | `409 ADJUSTMENT_STALE` | None; stays pending |
| Candidate quantity is negative | `409 INSUFFICIENT_STOCK_FOR_ADJUSTMENT` | None; stays pending |
| Same decision key, different command | `409 IDEMPOTENCY_KEY_REUSED` | None |
| Invalid/forbidden rejection reason | `422 INVALID_REJECTION_REASON` | None |
| Missing/blank/oversized decision key | `422 INVALID_IDEMPOTENCY_KEY` | None |

No `ADJUSTMENT_BALANCE_NOT_FOUND` outcome exists because approve uses the safe
zero-materialization rule.

## Frontend contract

The Manager page contains a pending work queue and exact selected/detail view
showing requester/time, reason, SKU/location, Original Audit, Manager Recheck,
immutable requested change and current request status. It provides approve and
reject confirmations and terminal read-only states.

Required states include loading, empty queue, loaded pending detail, submitting,
applied, rejected, stale, insufficient stock, already decided, not found,
retryable server error, `401` auth recovery and `403` forbidden.

The page does not show a current-stock preview, quantity edit, partial approval,
Staff edit, attachment behavior, reopen action or generic workflow controls.

## Stock and neighboring-workflow effect boundaries

- Reject has zero stock effect.
- Successful approve changes only the exact persisted SKU/location balance.
- AuditSession, AuditLine, AuditRecheck and original Adjust intent fields remain
  unchanged.
- Pick, Transfer, Putaway and Receive records are not created or mutated.
- Decision status/evidence and the balance update commit or roll back together.

## Observability

- Reuse the stable API error envelope.
- After commit, application logs may include Adjust request ID, Manager actor ID,
  terminal decision/status, source SKU/location and applied before/after values.
- Never log session tokens, idempotency keys, fingerprints, request reason or
  rejection reason text.
- Durable database evidence is authoritative; application logs do not replace it.

## Test plan

### Backend and persistence

- Manager pending list, empty list and pending/terminal exact detail;
- all three wrong-role `403` cases and unauthenticated `401`;
- unknown/out-of-Warehouse non-disclosure;
- approve exact delta when locked current equals snapshot;
- reject with normalized required reason and no stock read/effect;
- approve rejects rejection reason; reject blank/over-500 reason;
- stale and negative failures leave request pending and all evidence null;
- missing balance zero materialization, concurrent creation and rollback;
- terminal status/evidence constraints and immutable source facts;
- same-key historical approve/reject replay; conflicting-key/command behavior;
- approve/approve, approve/reject, reject/reject and different-key terminal races;
- approve against concurrent Pick, Transfer, Putaway and another Adjust on the
  same balance;
- rollback if balance or decision persistence fails;
- original Audit/Recheck and neighboring workflow no-effect proof.

### Migration

- upgrade, downgrade and re-upgrade on PostgreSQL 17 and 18;
- three-value status constraint;
- state-dependent evidence/idempotency checks, FK/index/unique constraints;
- before/change/after arithmetic and non-negative constraints;
- existing pending rows remain valid without fabricated decision evidence.

### Frontend and Playwright

- pending list/detail and separated Original Audit/Manager Recheck evidence;
- approve/reject confirmation and terminal reload;
- requested change remains read-only and no current-stock preview exists;
- stale, insufficient, already-decided, auth and retryable errors;
- Staff creates request -> Manager approves -> stock changes exactly once;
- lost-response historical replay does not apply twice;
- reject path leaves stock unchanged; wrong roles receive real backend `403`.

## Definition of Done

- persistence and API implement this exact human-approved contract;
- backend, migration, concurrency, frontend and browser tests above pass with
  fresh output, including PostgreSQL 17/18 evidence where applicable;
- no generic workflow/ledger/locking framework or excluded behavior is added;
- Traceability, Story Specs Index and AI Usage Log reflect implementation truth;
- a human reviews the implementation diff before integration or commit.

## Open questions and explicit boundaries

- `OQ-012` remains globally open; this contract operates on the existing strict
  integer request snapshots and does not decide UOM/decimal/conversion behavior.
- `OQ-013` is further decided for the current Adjust lifecycle: pending requests
  terminate as `APPLIED` or `REJECTED`; stale/negative failed approval remains
  pending; rejected requests cannot reopen or recreate from the same recheck.
  Broader Audit correction/reversal and other unapproved lifecycle behavior stay
  `PARTIALLY DECIDED / OPEN`.
- `OQ-022` remains open. No scanner, mobile/offline or integration behavior is
  introduced.
- Attachment storage/provider/policy remains outside this story.
