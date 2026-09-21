# US-REC-001 Technical Story Spec

## Status and authority

`HUMAN-REVIEWED TECHNICAL SPEC — READY FOR IMPLEMENTATION`

Canonical product wording and Acceptance Criteria remain authoritative at
[`../../04-product/stories/US-REC-001.md`](../../04-product/stories/US-REC-001.md).
This spec does not modify canonical Acceptance Criteria or close `OQ-013`/`OQ-014`.
Human review approved the implementation contract at `DEC-036`.

| Field | Value |
|---|---|
| Story ID | `US-REC-001` |
| Story | Receive — record actual quantity and compare expected quantity/reference |
| Owner | Nguyễn Thị Nghĩa |
| Requirement IDs | `REQ-001/002/003`, `CAND-REQ-001/002/009/010` |
| Business rules | `CAND-BR-001`, `CAND-BR-014` |
| Decisions | `DEC-016/017/018/023/036` |
| Verified evidence | `EVD-002/003/004/005` |
| Design references | `SCR-01`, `SCR-02`, `PF-01` |
| Open boundaries | `OQ-013`, `OQ-014`, `OQ-022`; quantity representation remains constrained by `OQ-012` |

`DEC-016/017/018/023/036` are HUMAN PRODUCT/TECHNICAL DECISIONS, not verified
research evidence. They must not be relabelled as `EVD-*`.

## Worktree implementation status — 2026-09-22

The `DEC-036` contract has been implemented in the current worktree and remains
uncommitted pending human diff review. The implementation includes the legacy-safe
schema/migration, three Receive routes, Warehouse Staff enforcement, reference-review
acknowledgement, Putaway eligibility guards, React `/receive` UI, component tests and
Playwright scenarios. Fresh local verification: Ruff lint/format PASS, backend
`86 passed`, frontend lint/typecheck/`23` Vitest/build PASS, and SQLite
upgrade/downgrade/re-upgrade PASS. Playwright discovery lists both Receive scenarios,
but browser execution is NOT VERIFIED because no local PostgreSQL/Docker runtime is
available. Local evidence must not be reported as PostgreSQL 18/17 or browser E2E
evidence. PostgreSQL 18/browser evidence remains assigned to current CI; PostgreSQL 17
remains pending staging deployment.

This implementation status does not change `OQ-012`, the open portions of `OQ-013`,
`OQ-014`, or `OQ-022` and does not add completion, partial Receive, correction,
Purchase Order, deployment, or automatic Putaway behavior.

## Executive conclusion

The pre-implementation repository had a working Putaway/auth foundation but only a
fixture-level Receive persistence scaffold. The current worktree now implements the
approved Receive persistence, API, UI, review and Putaway-eligibility contract; it is
uncommitted and awaiting human diff review and CI evidence as recorded above.

Human review approved the data, API, authorization, lifecycle, no-effect and test
contract below. The slice uses `RECEIVE_RECORDED`; it does not canonicalize final
Receive completion. It deliberately does not define automatic Putaway handoff,
partial Receive, correction/reversal workflow or an authoritative reference.

## A. Pre-implementation Receive code audit

### Baseline audit result

| Area | Result | Current evidence | Gap / implication |
|---|---|---|---|
| `Receive` model | `PARTIAL` | `models.py`: `id`, `warehouse_id` | No expected/document reference, recording timestamp/actor or review context. |
| `ReceiveLine` model | `PARTIAL` | `id`, `receive_id`, `sku_id`, non-negative integer `actual_quantity` | No expected quantity or persisted discrepancy; `actual_quantity` is mandatory, so a pre-recording context cannot be represented faithfully. |
| Fixture/data | `PARTIAL` | `test_seed.py` and `test_putaway.py` create one Receive line with `actual_quantity = 16` | Putaway fixture only; expected quantity/reference and mismatch branches are absent. It is not Receive behavior evidence. |
| Putaway dependency | `PASS — boundary exists` | Putaway reads `ReceiveLine.actual_quantity`; locks the line; subtracts prior allocations; posts to `StockBalance` | Receive changes must preserve this contract or explicitly adapt Putaway. Receive itself must not write `StockBalance`. |
| Receive service/API | `MISSING` | No receive module or route | Requires story-specific service and route contract. |
| API patterns | `PASS — reusable foundation` | FastAPI `/api/v1`; Pydantic schemas; service functions; SQLAlchemy session; `ApiError`; JSON response models | Receive route/payload contract is approved below. |
| Auth/role foundation | `PASS` | PostgreSQL session -> active user -> DB role; reusable `require_roles` | Receive mutation must use backend `WAREHOUSE_STAFF` enforcement. Frontend role is display/UX only. |
| Error envelope | `PASS` | `{ "error": { "code", "message", "details" } }`; request-validation handler | Existing handler special-cases a field named `quantity`; Receive fields are `actual_quantity`, so error mapping needs deliberate extension. |
| Migration conventions | `PASS` | Sequential Alembic revisions, named FK/check/unique constraints and indexes; current head `20260919_0002` | Receive migration would be next revision. Legacy fixture/backfill cannot be invented. |
| Frontend architecture | `PARTIAL` | React/Vite, shared `apiRequest`, session `AuthGate`, Putaway-specific `App` | No page routing/navigation abstraction or Receive components. Do not add a routing library without separate approval. |
| Receive design/screens | `PASS — design reference only` | `SCR-01`, `SCR-02`, `PF-01`; 10 human-verified PF-01 states across Receive/Putaway | Figma remains downstream design. PF-01 transition is facilitator-only and is not production navigation/completion behavior. |
| Existing Receive tests | `MISSING` | No backend/frontend/E2E Receive test | Existing Putaway tests only prove the downstream stock-posting boundary. |
| Current verification | `PASS with environment boundary` | 2026-09-22 local: backend `57 passed` using `.venv`; frontend Vitest `15 passed`, ESLint PASS, TypeScript PASS | These checks validate the unchanged baseline only. No PostgreSQL migration or Playwright run was executed for this analysis. |

### Reuse boundary

Reuse:

- `Warehouse`, `Sku`, `Receive`, `ReceiveLine`, and the existing foreign-key chain;
- FastAPI/SQLAlchemy transaction pattern and `ApiError` envelope;
- PostgreSQL-backed session actor and `require_roles` policy;
- frontend `apiRequest`, auth gate, status/error accessibility patterns;
- pytest fixture/dependency override, Vitest/Testing Library and Playwright structure.

Do not reuse as business truth:

- `actual_quantity = 16` fixture as a full-only or partial-Receive rule;
- Putaway eligibility as Receive completion;
- the PF-01 facilitator arrow as automatic navigation;
- Putaway idempotency (`NFR-003`) as an approved Receive requirement;
- frontend role checks as authorization.

## Goal

Allow an authenticated Warehouse Staff actor to read a prepared Receive context,
record actual received quantity, compare it with expected quantity, preserve actual
quantity when discrepant, and expose reference mismatch for required human review,
without changing tracked-location stock or creating Putaway.

## Preconditions

- An existing Receive context identifies one Warehouse and at least one item/SKU.
- Expected quantity and expected/manual order or delivery reference have been
  prepared from an external/manual source associated with Purchasing.
- The actor has a valid server-side session and current database role
  `WAREHOUSE_STAFF` for mutation.
- Creating/editing the Purchasing preparation workflow is outside this story; its
  minimum expected quantity/reference is an approved precondition under `DEC-036`.
- Final Receive completion and exact Putaway handoff remain open at `OQ-013`.

## Happy Path

1. Warehouse Staff loads the prepared Receive context.
2. The UI shows item/SKU, expected quantity and expected/manual reference.
3. Warehouse Staff checks the item and enters actual received quantity and the
   document reference observed during Receive.
4. The backend validates actor, context and quantities; comparison occurs on the
   backend.
5. If actual equals expected and references match, the system records the actual
   quantity with zero discrepancy and a non-mismatch reference result.
6. The response/UI reports that Receive facts were recorded.
7. No stock, Putaway, Transfer or Movement effect occurs.

“Recorded” in this spec does not mean final Receive completion.

## Alternate / Error Paths

| Path | Required treatment | Boundary |
|---|---|---|
| Actual differs from expected | Persist actual, expected and signed difference; never replace actual with expected | Canonical `AC-03`, `CAND-BR-001` |
| System expected reference differs from observed document reference | Record mismatch context; show that review is required; do not choose an authoritative reference | Canonical `AC-04`, `CAND-BR-014` |
| Missing/malformed quantity or reference | Reject with `422`, existing error envelope, no write | Required fields and comparison normalization are defined below |
| Unknown Receive | `404 RECEIVE_NOT_FOUND`, no write | Approved technical contract |
| Unknown supplied line/SKU or line/SKU not in Receive | `409 RECEIVE_CONTEXT_MISMATCH`, no write | Approved integrity guard |
| Request omits or duplicates a prepared line | `422 INCOMPLETE_RECEIVE_CONTEXT`, no write | Current full-context command; does not close `OQ-014` |
| Already recorded context | `409 RECEIVE_ALREADY_RECORDED`; no overwrite | Correction/reversal is outside this story and remains open |
| Unauthenticated | `401` | Approved auth semantics |
| Authenticated wrong role | `403` | Approved auth semantics |
| Persistence/server failure | Roll back all Receive writes and return existing envelope where handled | No stock or Putaway effect |
| Partial line set / repeat delivery | Do not invent behavior | `OQ-014` |
| Completion/handoff requested | Do not expose/claim until approved | `OQ-013` |

## B. Canonical Acceptance Criteria mapping

| AC | Requirement source | Rule / decision | Expected behavior | Data read | Data write | API need | UI state | Planned test | Unresolved boundary |
|---|---|---|---|---|---|---|---|---|---|
| `AC-01` record and compare | `CAND-REQ-001`, `EVD-002/003` | `DEC-016/023/036` | Read prepared item/expected data; accept actual; compare backend-side | Receive, lines, SKU, expected qty/reference | Actual, discrepancy result, document/reference comparison context, actor/time | Context GET + record POST | Loading, default, validation, recorded | Context + successful record integration tests | Expected context is a precondition supplied/prepared by Purchasing; quantity type `OQ-012` |
| `AC-02` match | `CAND-REQ-001`, `EVD-002/003` | `CAND-BR-001`, `DEC-036` | Persist actual exactly when actual = expected; discrepancy `0` | Expected qty | Actual and zero difference | Record POST | `actual = expected`, success | Equality case | None inside this slice |
| `AC-03` discrepancy | `CAND-REQ-002`, `EVD-004/005` | `CAND-BR-001`, `DEC-023` | Persist actual, not expected; record signed difference | Expected qty | Actual and `actual - expected` | Record POST | Quantity discrepancy | Under- and over-expected cases; no stock write | Detailed handling with delivery party, causes/evidence/approval; partial semantics |
| `AC-04` reference review | `CAND-REQ-009` | `CAND-BR-014`, `DEC-016/036` | Detect/record mismatch, require Warehouse Staff acknowledgement, never auto-select authority | Stored expected reference + observed document reference | Match status; review actor/time for mismatch | Record POST + reference-review POST | Reference mismatch / review required / reviewed | Mismatch shown; acknowledgement recorded; Putaway blocked before review; no authority selected | Final Receive completion/handoff remains `OQ-013` |

All four ACs are implementable under `DEC-036`. In this slice, “before completion” is
enforced as a concrete downstream-eligibility guard: an unreviewed reference mismatch
cannot be read/confirmed by Putaway. This does not define final Receive completion or
the exact Receive -> Putaway handoff under `OQ-013`.

## C. Approved data model

### Existing fields

| Entity | Existing field | Treatment |
|---|---|---|
| `Receive` | `id`, `warehouse_id` | Reuse unchanged |
| `ReceiveLine` | `id`, `receive_id`, `sku_id` | Reuse unchanged |
| `ReceiveLine` | `actual_quantity INTEGER NOT NULL CHECK >= 0` | Concept is reusable, but nullability/backfill must change if the same row represents a prepared context before recording |
| `PutawayAllocation` | `receive_line_id` FK | Preserve; recorded Receive quantity remains the Putaway eligibility ceiling |

### Approved minimal fields

| Entity | Proposed field | Type / constraint | Purpose |
|---|---|---|---|
| `Receive` | `expected_reference` | `VARCHAR(255)`, non-empty for new contexts | External/manual expected order or delivery reference |
| `Receive` | `document_reference` | `VARCHAR(255) NULL`, non-empty when present | Reference observed on the receiving document; preserve separately |
| `Receive` | `reference_match_status` | `VARCHAR(24) NULL`, check `REFERENCE_MATCH` / `REFERENCE_MISMATCH` | Persist comparison result without selecting authority; nullable only for legacy/unrecorded rows |
| `Receive` | `recorded_by_user_id` | UUID FK `users.id`, nullable before record, indexed | Audit actor for the fact-recording command |
| `Receive` | `recorded_at` | timezone-aware timestamp, nullable before record | Time facts were recorded; deliberately not named `completed_at` |
| `Receive` | `reference_reviewed_by_user_id` | UUID FK `users.id`, nullable, indexed | Warehouse Staff who acknowledged a recorded mismatch |
| `Receive` | `reference_reviewed_at` | timezone-aware timestamp, nullable | Time human review acknowledgement occurred; no approve/reject meaning |
| `ReceiveLine` | `expected_quantity` | `INTEGER NULL` for legacy-safe migration; application-required for new contexts; check `>= 0` when present | Expected quantity for backend comparison |
| `ReceiveLine` | `actual_quantity` | existing integer changed nullable before record; check `>= 0` when present | Actual quantity; remains source for Putaway after recording |
| `ReceiveLine` | `quantity_discrepancy` | `INTEGER NULL`, equal to `actual_quantity - expected_quantity` when recorded | Persist the canonical discrepancy, including under/over sign |

Do not add:

- Purchase Order tables/lifecycle;
- `authoritative_reference` or automatic source-selection field;
- `completed_at` or final `Receive.status` before `OQ-013` is resolved;
- stock balance, Warehouse total, Transfer or Movement fields/effects;
- generic workflow/event tables.

### Approved invariants and indexes

- Existing Receive -> Warehouse and ReceiveLine -> Receive/SKU FKs remain.
- `expected_quantity >= 0`; `actual_quantity IS NULL OR actual_quantity >= 0`.
- When a line is recorded, `quantity_discrepancy = actual_quantity - expected_quantity`.
- Reference comparison trims surrounding whitespace and then uses case-sensitive exact
  equality. Equal values produce `REFERENCE_MATCH`; unequal values produce
  `REFERENCE_MISMATCH`. Both original trimmed values are preserved; no authority is
  selected and neither value is auto-corrected.
- `reference_reviewed_by_user_id` and `reference_reviewed_at` are both null or both
  non-null, and may be populated only for `REFERENCE_MISMATCH`.
- A mismatch does not populate any authoritative-reference value.
- Putaway context/confirmation must reject an unrecorded Receive line whose
  `actual_quantity` is `NULL`; it must not treat missing actual quantity as zero or
  infer that Receive is completed, using `409 RECEIVE_NOT_RECORDED`.
- Putaway context and confirmation must reject `REFERENCE_MISMATCH` without both
  review fields using `409 REFERENCE_REVIEW_REQUIRED`, before allocation or stock
  mutation. `REFERENCE_MATCH`, reviewed mismatch and legacy rows with an existing
  actual quantity and null new reference fields remain compatible with the existing
  Putaway contract.
- `recorded_by_user_id` should be indexed. Existing `receive_id`, `sku_id` and
  `warehouse_id` indexes are sufficient for the minimal command/read path.
- Do not add `(receive_id, sku_id)` uniqueness: canonical sources do not say the same
  SKU cannot appear on multiple reference lines.
- DB checks enforce allowed match values, paired reviewer/time nullability and review
  metadata only on `REFERENCE_MISMATCH`; application validation enforces the complete
  new-context invariant that cannot be fabricated for legacy rows.

### Migration impact

Planned revision: `20260922_0003_receive_recording_context.py`, with actual timestamp
chosen at implementation time according to repository convention.

Migration must not invent expected quantity/reference/reviewer facts. New fields are
nullable at database level for legacy compatibility. Existing rows keep their current
`actual_quantity`; no fake expected/reference/reviewer value is backfilled. New Receive
contexts created for this slice must satisfy application validation requiring expected
quantity/reference before recording. `actual_quantity` becomes nullable so a prepared
new context can exist before recording. Legacy rows with an existing actual quantity
remain readable by the existing Putaway contract; this compatibility exception must
not be used for newly created contexts.

The migration must be verified with upgrade -> downgrade -> upgrade on PostgreSQL,
including PostgreSQL 17 staging compatibility. SQLite metadata tests are not migration
evidence.

## D. API contract

The routes and JSON shapes below are the approved story-specific technical contract.
They follow the existing `/api/v1`, context-read and command conventions without
adding a new library.

### `GET /api/v1/receives/context/{receive_id}`

| Item | Contract |
|---|---|
| Actor | `WAREHOUSE_STAFF` |
| Output | Receive/Warehouse identity, expected reference, lines with `receive_line_id`, SKU ID/code and expected quantity; existing recorded/reference state if present |
| Validation | UUID shape; Receive exists; context is prepared |
| Errors | `401`, `403`, `404 RECEIVE_NOT_FOUND`, `409 RECEIVE_CONTEXT_NOT_PREPARED` |
| DB effects | None |
| No-effect guarantee | No stock, Receive recording, Putaway, Transfer or Movement write |

Response for a prepared, not-yet-recorded context:

```json
{
  "receive_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "reference": {
    "expected": "DELIVERY-001",
    "document": null,
    "match_status": null,
    "reviewed_by_user_id": null,
    "reviewed_at": null
  },
  "recorded_at": null,
  "putaway_eligible": false,
  "lines": [
    {
      "receive_line_id": "<uuid>",
      "sku_id": "<uuid>",
      "sku": "SKU-001",
      "expected_quantity": 16,
      "actual_quantity": null,
      "quantity_discrepancy": null
    }
  ]
}
```

### `POST /api/v1/receives`

This command records observed facts; it does not complete Receive or start Putaway.

| Item | Contract |
|---|---|
| Actor | `WAREHOUSE_STAFF` only |
| Input | Existing `receive_id`, observed `document_reference`, and actual quantity per identified Receive line |
| Output | Recorded actual/expected/difference per line, reference match result, review status, recording actor/time |
| Validation | Context/line/SKU integrity; all quantities integer and non-negative for current technical baseline; document reference non-empty; request contains exactly every line in the prepared context once. This slice-level atomic command does not canonicalize or permanently exclude partial Receive, which remains open at `OQ-014`. |
| Errors | Existing envelope: `401`, `403`, `404 RECEIVE_NOT_FOUND`, `409 RECEIVE_CONTEXT_NOT_PREPARED`, `409 RECEIVE_CONTEXT_MISMATCH`, `409 RECEIVE_ALREADY_RECORDED`, `422 INVALID_QUANTITY`, `422 INVALID_REQUEST`, `422 INCOMPLETE_RECEIVE_CONTEXT` |
| DB effects | Update only Receive/ReceiveLine recording facts in one transaction |
| No-effect guarantees | No `StockBalance` change; no Putaway allocation; no Transfer/Movement; no authoritative-reference selection; no automatic navigation/handoff |

Request:

```json
{
  "receive_id": "<uuid>",
  "document_reference": "DELIVERY-001",
  "lines": [
    {
      "receive_line_id": "<uuid>",
      "sku_id": "<uuid>",
      "actual_quantity": 16
    }
  ]
}
```

Successful response (`201` for first record):

```json
{
  "receive_id": "<uuid>",
  "recorded_at": "2026-09-22T00:00:00Z",
  "reference": {
    "expected": "DELIVERY-001",
    "document": "DELIVERY-001",
    "match_status": "REFERENCE_MATCH",
    "reviewed_by_user_id": null,
    "reviewed_at": null
  },
  "putaway_eligible": true,
  "lines": [
    {
      "receive_line_id": "<uuid>",
      "sku_id": "<uuid>",
      "expected_quantity": 16,
      "actual_quantity": 16,
      "quantity_discrepancy": 0
    }
  ]
}
```

For mismatch, preserve both reference strings, return
`match_status = REFERENCE_MISMATCH`, null review metadata and
`putaway_eligible = false`. Do not return an authoritative reference.

### `POST /api/v1/receives/{receive_id}/reference-review`

This command records Warehouse Staff acknowledgement of an existing reference
mismatch. It does not approve/reject, correct either reference, complete Receive or
trigger Putaway.

| Item | Contract |
|---|---|
| Actor | `WAREHOUSE_STAFF` only |
| Input | Path `receive_id` and empty JSON object `{}`; no business-decision payload |
| Output | Receive ID, `REFERENCE_MISMATCH`, reviewer ID/time and `putaway_eligible = true` |
| Validation | Receive is recorded; comparison is `REFERENCE_MISMATCH`; review has not already been recorded |
| Errors | `401`, `403`, `404 RECEIVE_NOT_FOUND`, `409 RECEIVE_NOT_RECORDED`, `409 REFERENCE_REVIEW_NOT_REQUIRED`, `409 REFERENCE_ALREADY_REVIEWED` |
| DB effects | Set `reference_reviewed_by_user_id` and `reference_reviewed_at` atomically |
| No-effect guarantees | No reference correction/authority selection; no StockBalance, PutawayAllocation, Transfer or Movement write; no Putaway call/navigation |

### Deliberately absent API

- No `complete Receive` endpoint until `OQ-013` is resolved.
- No automatic `create Putaway` call or Putaway navigation response.
- No Purchasing create/edit context endpoint in this story. Expected context is an
  approved precondition supplied/prepared according to `DEC-016/036`; a later story
  may specify its workflow without blocking this slice.
- No update/delete/correct/reopen endpoint; correction/reversal is outside the current
  story and remains open.
- No partial status, remaining-quantity lifecycle or repeat-partial command;
  `OQ-014` remains open.

## E. Authorization

| Operation | Backend policy | Result |
|---|---|---|
| Read Receive execution context | `require_roles(Role.WAREHOUSE_STAFF)` | Missing/invalid session `401`; authenticated disallowed role `403` |
| Record Receive facts | `require_roles(Role.WAREHOUSE_STAFF)` | Missing/invalid session `401`; Manager/Purchasing/Admin `403` unless later decision expands permission |
| Acknowledge reference mismatch review | `require_roles(Role.WAREHOUSE_STAFF)` | Missing/invalid session `401`; Manager/Purchasing/Admin `403`; acknowledgement only, no approve/reject |
| Provide/edit expected reference | Outside this story's API | Purchasing supplies/prepares the precondition according to `DEC-016/036`; no PO/procurement lifecycle |

Every route resolves the actor from the PostgreSQL session and current database role.
The UI may hide/disable controls but is never the authority.

## F. Approved UI / state contract

Use `SCR-01` and `SCR-02` as design references, not new product authority.

| State | Minimum treatment |
|---|---|
| Loading | Announce loading of Receive context; no editable default until context arrives |
| Default | Show SKU/item, expected quantity and expected reference; actual quantity and document reference inputs |
| Actual = expected | Neutral/positive comparison; submitted result preserves actual |
| Quantity discrepancy | Clearly show expected, actual and signed/labelled difference before submit and in recorded result |
| Reference mismatch | Preserve/show both references; prominent `Review required`; acknowledgement control for Warehouse Staff; never label either authoritative |
| Validation error | Field-level message plus summary/alert; retain safe user input |
| API/server error | Existing accessible alert; do not claim recorded/success |
| Submitting | Disable repeated submit while request is pending |
| Success / recorded | State “Receive recorded”, not “Receive completed”; show recorded quantities and mismatch/review state; match is Putaway-eligible, unreviewed mismatch is not |
| Mismatch reviewed | Show acknowledgement actor/time and Putaway eligibility without auto-navigation or Putaway creation |
| Unauthorized/forbidden | Auth gate for `401`; role-appropriate forbidden state for `403` |

No success state may automatically navigate to Putaway. PF-01's Receive -> Putaway
transition remains facilitator-only. A future human-approved navigation affordance must
not imply automatic Putaway creation.

Approved frontend structure without adding a dependency:

- add `ReceivePage.tsx` and `ReceivePage.test.tsx`;
- extend the existing `api.ts` client with typed Receive functions;
- make the existing application shell select/render the Receive page through a small
  approved path/config decision;
- keep Putaway flow reachable and its existing tests intact.

The implementation may use the existing application shell/direct configured context
without adding a routing dependency. It must preserve Putaway reachability and must
not navigate automatically from Receive success/review.

## Observability / Logging

Approved implementation expectations:

- structured application event after commit with `receive_id`, actor user ID,
  line count, `has_quantity_discrepancy`, `reference_match_status` and outcome;
- warning event for rejected integrity/conflict commands without logging session
  token, password or full request payload;
- exception logging must not claim a commit and must preserve rollback;
- no new analytics/telemetry provider or logging dependency in this story.

Exact log retention, correlation ID and operational alerting remain outside the
approved contract.

## G. Test plan

### Backend/API

| Test ID | Scenario | Required assertions |
|---|---|---|
| `TEST-REC-001` | expected = actual | Actual persists unchanged; discrepancy `0`; references match; no stock/Putaway effect |
| `TEST-REC-002` | expected != actual (under) | Actual persists, expected not substituted; signed discrepancy persists |
| `TEST-REC-003` | expected != actual (over) | Same invariant for over-expected branch; this does not define over-receive handling beyond recording |
| `TEST-REC-004` | reference match | Both values preserved; status `REFERENCE_MATCH`; no authoritative field |
| `TEST-REC-005` | reference mismatch | Both values preserved; `REFERENCE_MISMATCH`; `putaway_eligible = false`; no automatic authority/completion |
| `TEST-REC-006` | invalid quantity | `422 INVALID_QUANTITY`; no Receive mutation |
| `TEST-REC-007` | missing required field | `422 INVALID_REQUEST`; no Receive mutation |
| `TEST-REC-008` | Warehouse Staff | Mutation allowed through production auth dependency or isolated dependency override as appropriate |
| `TEST-REC-009` | wrong role | Authenticated Purchasing/Manager/Admin mutation returns `403`; no mutation |
| `TEST-REC-010` | missing/invalid session | `401`; no mutation |
| `TEST-REC-011` | unknown Receive or mismatched line/SKU | Unknown Receive returns `404 RECEIVE_NOT_FOUND`; line/SKU mismatch returns `409 RECEIVE_CONTEXT_MISMATCH`; atomic no-write |
| `TEST-REC-012` | server/persistence failure | Transaction rolls back; UI/API does not report success |
| `TEST-REC-013` | no stock effect | Before/after `StockBalance` rows and quantities identical |
| `TEST-REC-014` | no Putaway effect | No new `PutawayAllocation`; no Transfer/Movement path |
| `TEST-REC-015` | existing Putaway compatibility | Recorded actual remains usable as eligibility input; existing Putaway tests pass unchanged/adapted without new handoff rule |
| `TEST-REC-016` | acknowledge reference review | Warehouse Staff reviewer/time recorded; references unchanged; no approve/reject state; eligible becomes true |
| `TEST-REC-017` | unreviewed mismatch Putaway context | `409 REFERENCE_REVIEW_REQUIRED`; no allocation/stock effect |
| `TEST-REC-018` | unreviewed mismatch Putaway confirmation | `409 REFERENCE_REVIEW_REQUIRED`; no allocation/stock effect |
| `TEST-REC-019` | reviewed mismatch or match Putaway compatibility | Existing Putaway contract can read/confirm when all other validations pass; Receive does not trigger it |
| `TEST-REC-020` | duplicate/conflicting Receive record | `409 RECEIVE_ALREADY_RECORDED`; original facts unchanged; no correction history invented |
| `TEST-REC-021` | incomplete/duplicated prepared line set | `422 INCOMPLETE_RECEIVE_CONTEXT`; no line is recorded; no partial status/lifecycle created |

Do not add a test that declares partial Receive permanently supported or forbidden.
The current command requires the complete prepared line set and has no partial status
or remaining-quantity lifecycle. Do not test final completion until `OQ-013` is
resolved.

### Migration/PostgreSQL

- Alembic upgrade from current head, downgrade and re-upgrade on PostgreSQL.
- Constraint/FK/index inspection and existing-row migration scenario approved by H1.
- PostgreSQL 18 CI compatibility plus PostgreSQL 17 staging-compatible evidence before
  release, per `DEC-035`.
- No SQLite-only result may be labelled PostgreSQL migration evidence.

### Frontend

- Loading and default context.
- Equality and discrepancy rendering.
- Reference mismatch `Review required`, with both references and no authority claim.
- Required/invalid input messages.
- `401` auth reset, `403` forbidden, API/server error and success/recorded states.
- Submit pending prevents duplicate UI action.
- Putaway UI remains a separate reachable flow.

### Playwright

- `TEST-REC-E2E-001`: Warehouse Staff logs in, loads prepared context, records matching
  actual/reference through React -> FastAPI -> PostgreSQL, sees recorded state.
- `TEST-REC-E2E-002`: discrepancy/reference mismatch branch shows recorded actual,
  difference and review-required state; DB stock and Putaway count remain unchanged.
- Authentication coverage for missing session and wrong role may reuse/shared E2E setup,
  but backend authorization assertions remain mandatory.

## Definition of Done

- Canonical AC remains unchanged and traceable to requirement/rule/decision/evidence.
- Schema, legacy-safe migration treatment, API payload/routes, Warehouse Staff review
  acknowledgement and recorded-vs-completed boundary implement `DEC-036` exactly.
- Receive records the full prepared line set with actual/expected/discrepancy and
  reference context atomically; no partial lifecycle/status is introduced.
- Reference mismatch is not silently accepted as completed and no source is selected
  as authoritative by the system.
- Backend enforces `WAREHOUSE_STAFF`; verified `401` and `403` behavior exists.
- Receive does not alter `StockBalance` and does not create Putaway/Transfer/Movement;
  unreviewed mismatch is blocked at both Putaway context and confirmation boundaries.
- No automatic Receive -> Putaway navigation or command exists.
- Backend tests, frontend lint/typecheck/unit tests and Playwright Receive flow pass with
  fresh output.
- Alembic upgrade/downgrade/upgrade passes on PostgreSQL; PostgreSQL 17 release evidence
  is obtained before staging/release claim.
- Diff receives human review before integration/commit.
- Approved implementation/contract/test changes are reflected in Traceability without
  marking unimplemented behavior as implementation evidence.

## H. Approved story behavior summary

### Data Read

- Receive ID and Warehouse association.
- Receive lines and SKU identity/code.
- Prepared expected quantity per line.
- Prepared external/manual expected reference.
- Existing recording/review context when present.

### Data Write

- Actual quantity per recorded line.
- Signed quantity discrepancy.
- Observed document reference and reference comparison result.
- Recording actor/time and reference review acknowledgement actor/time.

### No-Effect Guarantees

- No `StockBalance` insert/update/delete.
- No Putaway allocation or automatic Putaway command.
- No Transfer or generic Movement record.
- No Warehouse total write.
- No authoritative-reference selection.
- No final completion claim or automatic navigation.

### Explicit boundaries

- Purchase Order lifecycle is out of MVP.
- Final Receive trigger/completion/handoff is `OQ-013`.
- Partial Receive is `OQ-014`.
- Barcode/QR/scanner/mobile/offline/integration is `OQ-022`.
- Exact quantity UOM/decimal policy remains `OQ-012`; existing integer type is only the
  current technical baseline.
- Detailed discrepancy handling with delivery party, evidence, reason and approval is
  not defined by `EVD-005`.

## I. Implementation slices

Human review authorizes these implementation slices subject to normal diff review and
fresh verification; this document update itself does not implement them.

| Slice | Exact files | Change purpose | Tests | Verify commands |
|---|---|---|---|---|
| 1 — schema/migration | `backend/src/warehouse_api/models.py`; new `backend/alembic/versions/<revision>_receive_recording_context.py`; `backend/src/warehouse_api/test_seed.py` only if approved fixture treatment requires it | Add approved expected/actual/discrepancy/reference/review fields and migration/backfill | Migration + schema constraints; existing Putaway suite | `backend/.venv/Scripts/python.exe -m alembic upgrade head`; downgrade/upgrade against PostgreSQL; `backend/.venv/Scripts/python.exe -m pytest` |
| 2 — backend Receive service/API | new `backend/src/warehouse_api/receive.py`; `backend/src/warehouse_api/schemas.py`; new `backend/src/warehouse_api/receive_routes.py`; `backend/src/warehouse_api/main.py`; `backend/src/warehouse_api/putaway.py` | Context read and atomic fact-record command; existing envelope; explicit rejection of unrecorded lines at the downstream Putaway boundary | `tests/test_receive.py` AC/integrity/no-effect cases; existing Putaway suite plus unrecorded-line guard | `backend/.venv/Scripts/python.exe -m pytest tests/test_receive.py tests/test_putaway.py`; full pytest |
| 3 — authorization/validation | `backend/src/warehouse_api/auth.py` only if a named Receive policy is added; `receive_routes.py`; `receive.py`; `main.py` validation mapping | Backend role enforcement; `401/403`; strict Receive validation | Receive auth/validation cases; existing auth suite | full backend pytest; Ruff check/format check using project environment |
| 4 — backend tests | new `backend/tests/test_receive.py`; optionally shared fixture in `backend/tests/conftest.py` | PostgreSQL-capable API/data assertions including no StockBalance/Putaway effects | `TEST-REC-001`…`021` | full pytest locally; CI PostgreSQL migration/test job |
| 5 — frontend Receive UI | new `frontend/src/ReceivePage.tsx`; `frontend/src/api.ts`; `frontend/src/App.tsx`; `frontend/src/styles.css` | `SCR-01/02` states; keep Putaway separate; no new router dependency by default | Component tests and existing App/Auth tests | `npm.cmd run lint`; `npm.cmd run typecheck`; `npm.cmd test -- --run`; `npm.cmd run build` |
| 6 — frontend tests | new `frontend/src/ReceivePage.test.tsx`; `frontend/src/api.test.ts`; existing tests as needed | Loading/equality/discrepancy/mismatch/errors/success | Vitest/Testing Library | frontend lint/typecheck/test/build |
| 7 — PostgreSQL + Playwright E2E | new `frontend/e2e/receive.spec.ts`; `frontend/e2e/global-setup.ts` only if fixture setup is extended; approved non-destructive seed path | Real browser -> API -> PostgreSQL Receive flow and no-effect checks | `TEST-REC-E2E-001/002`; migration cycle | `npm.cmd run test:e2e`; CI PostgreSQL 18; staging-compatible PostgreSQL 17 verification |
| 8 — docs/traceability | this spec; `docs/06-technical/API.md`; `docs/06-technical/data-model.md`; `docs/06-technical/story-specs-index.md`; `docs/TRACEABILITY.md`; `vault/08-decisions/decision-log.md` | Record `DEC-036`, approved contract and later implementation evidence without overstating status | Link/status review | `rg` trace review; human diff review |

## J. Exact file plan and non-files

Expected implementation touch set:

```text
apps/backend/src/warehouse_api/models.py
apps/backend/src/warehouse_api/schemas.py
apps/backend/src/warehouse_api/receive.py                         (new)
apps/backend/src/warehouse_api/receive_routes.py                  (new)
apps/backend/src/warehouse_api/main.py
apps/backend/src/warehouse_api/putaway.py
apps/backend/alembic/versions/<revision>_receive_recording_context.py (new)
apps/backend/tests/test_receive.py                                (new)
apps/backend/src/warehouse_api/test_seed.py                       (conditional)
apps/frontend/src/api.ts
apps/frontend/src/ReceivePage.tsx                                 (new)
apps/frontend/src/ReceivePage.test.tsx                            (new)
apps/frontend/src/App.tsx
apps/frontend/src/styles.css
apps/frontend/e2e/receive.spec.ts                                 (new)
apps/frontend/e2e/global-setup.ts                                 (conditional)
vault/06-technical/story-specs/US-REC-001.md
docs/06-technical/API.md
docs/06-technical/data-model.md
docs/06-technical/story-specs-index.md
docs/TRACEABILITY.md
```

Do not create Purchase Order, stock mutation, Transfer/Movement, generic workflow,
new auth mechanism or automatic Putaway navigation files for this story.

## K. Human Decision Record

Human review approved the following at `DEC-036`:

| Area | Approved treatment | Preserved boundary |
|---|---|---|
| Lifecycle | Use `RECEIVE_RECORDED`; do not canonicalize `RECEIVE_COMPLETED` | Final completion/handoff remains `OQ-013` |
| Expected context | Store/read minimum external/manual expected quantity/reference prepared or supplied by Purchasing | No Purchase Order/procurement lifecycle |
| Quantity/discrepancy | Current-slice non-negative integer; persist signed `actual - expected`; record full prepared line set atomically | UOM/decimal remains `OQ-012`; partial Receive remains `OQ-014` |
| Reference comparison | Trim surrounding whitespace, then exact case-sensitive equality to `REFERENCE_MATCH` / `REFERENCE_MISMATCH` | No automatic authoritative source or correction |
| Mismatch review | Warehouse Staff acknowledgement; persist `reviewed_by` / `reviewed_at`; no approve/reject | Final completion remains open |
| Putaway eligibility | Match or reviewed mismatch is eligible; unreviewed mismatch is blocked in Putaway context and confirmation | No auto-trigger/navigation/handoff |
| Duplicate/correction | Second recording conflicts with `RECEIVE_ALREADY_RECORDED`; original facts remain | Correction/reversal outside current story |
| Legacy migration | New business fields nullable for existing rows; no fabricated backfill; new contexts application-validated | Legacy compatibility does not weaken new-context validation |
| Authorization | Warehouse Staff executes context/read, record and mismatch acknowledgement; backend session role is authoritative | `401` unauthenticated; `403` wrong role |
| No effects | Receive never changes stock or creates Putaway/Transfer/Movement | Putaway alone performs initial stock posting |
| Receive idempotency | No new idempotency contract; duplicates use typed conflict | `NFR-003` remains Putaway Round 1 only |

## L. Risks / unresolved Open Questions

| Risk | Impact | Treatment |
|---|---|---|
| Implementing “recorded” as “completed” | Violates `OQ-013` and can bypass reference review | Separate terminology/state; no completion API |
| Current full-context command is mistaken for permanent rejection of partial Receive | Silently resolves `OQ-014` | Label `NOT IMPLEMENTED / OPEN`; no partial status or remaining lifecycle |
| Putaway bypasses an unreviewed mismatch | Violates `DEC-036` | Enforce the same eligibility guard in context read and confirmation; assert no allocation/stock effect |
| Legacy row backfill invents expected data | Corrupts provenance and canonical facts | Nullable technical migration; no fabricated business values |
| Reference comparison generates unexpected mismatch | Incorrect exception path | Test documented trim + case-sensitive exact comparison; preserve both values for review |
| UI warning without durable review | Cannot enforce AC-04 before completion | Persist approved review state/action; backend enforcement |
| New Receive page displaces Putaway root flow | Regression/navigation ambiguity | Reuse the shell/direct context without new router dependency; preserve existing E2E; no auto-navigation |
| Integer quantity generalized as product rule | Prematurely resolves `OQ-012` | Label as current technical baseline only |
| Tests pass only on SQLite/component DB | Weak migration/locking evidence | PostgreSQL migration/integration and PostgreSQL 17 release verification |

## Review outcome

`US-REC-001 READY FOR HUMAN SPEC REVIEW: COMPLETED`

`US-REC-001 IMPLEMENTED IN WORKTREE: AWAITING HUMAN DIFF REVIEW AND CI`

`OQ-013 remains PARTIALLY DECIDED / OPEN for final completion/handoff. OQ-014 remains OPEN; partial Receive is NOT IMPLEMENTED in this slice.`
