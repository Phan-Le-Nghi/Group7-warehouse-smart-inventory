# Technical Story Spec — US-PUT-001

## Status and authority

`HUMAN-REVIEWED TECHNICAL SPEC — IMPLEMENTATION COMPLETED AND CI VERIFIED`

Canonical product wording and Acceptance Criteria remain authoritative at [`../../04-product/stories/US-PUT-001.md`](../../04-product/stories/US-PUT-001.md). This spec does not modify them.

Owner: Phan Lê Nghi.

## Goal

Demonstrate a minimal end-to-end Putaway path from UI to FastAPI to PostgreSQL and back, with test evidence, while preserving open product boundaries.

## Traceability chain

```text
REQ-002/003/004 + CAND-REQ-003/007/010
  + CAND-BR-003/004
  + DEC-006/010/011/017/020/021/022/023
    -> US-PUT-001
      -> AC-PUT-001/002/003 (unchanged)
        -> SCR-03 / PF-01 boundary
          -> proposed POST /api/v1/putaways
            -> Putaway allocation + location stock effect
              -> unit + PostgreSQL integration + Playwright evidence
```

## Canonical Acceptance Criteria mapping

| Canonical AC | Figma/UI state | Proposed API behavior | Data effect | Planned test evidence |
|---|---|---|---|---|
| `AC-PUT-001` — confirm destination allocation | `SCR-03`: show SKU and eligible quantity; select `BACKROOM` or `SALES_SHELF`; confirm; show committed result | Validate request and confirm allocation atomically | Create Putaway allocation and increment confirmed destination balance | API/integration tests for both tracked destinations; Playwright happy path |
| `AC-PUT-002` — tracked internal location | Selection contains only the two MVP tracked locations | Reject any destination outside the tracked-location contract | Allocation references the tracked location in the MVP Warehouse | Request validation test; assert zero data effect on failure |
| `AC-PUT-003` — no automatic Movement record | Success copy identifies Putaway allocation, not Transfer/Movement | Endpoint has no Transfer/Movement side effect | No Transfer row; no generic Movement table is introduced | Integration assertion that Transfer data is unchanged/absent |

## UI states

- Loading Putaway context.
- Ready with SKU, eligible quantity and destination selection.
- Confirming; repeated UI submission disabled while the request is pending.
- Confirmed with destination and committed quantity summary.
- Validation/conflict failure with no claimed stock change.

`SCR-03` remains a separate flow. The `PF-01` transition is a facilitator transition only, not an automatic production CTA or a Receive completion rule.

## Proposed API contract

`POST /api/v1/putaways` with an idempotency key; exact URL is a technical contract, not a product requirement.

```json
{
  "receive_line_id": "<fixture receive line>",
  "sku_id": "<fixture SKU>",
  "quantity": 16,
  "destination_location_id": "<BACKROOM fixture id>"
}
```

The original slice injects a Warehouse Staff actor through the actor/auth dependency boundary for its isolated automated test. The separate authentication implementation following `DEC-031/033` is merged and CI verified; dependency override remains test-only and is not a production mechanism.

The operation must reject malformed/non-positive quantity, missing/mismatched references, invalid destination and allocation exceeding eligible remaining quantity. A failed request has no allocation or balance effect.

Duplicate handling:

- replaying the same idempotency key and payload returns the original committed result;
- the replay does not increment stock again;
- reusing a key with a different payload is a conflict;
- Receive-line locking and the eligible-remaining check protect against concurrent double-count.

## Vertical-slice fixture and expected effect

Precondition:

- one `receive_line` exists;
- `actual_quantity = 16` integer units;
- previously posted quantity is `0`;
- initial Backroom and Sales Shelf balances are captured by the test fixture;
- no new Receive completion state is assumed.

Action: Warehouse Staff selects `BACKROOM` and confirms Putaway for the 16 eligible units.

Expected committed result:

- one Putaway allocation for 16 units is created;
- Backroom stock increases by 16;
- Sales Shelf stock is unchanged;
- derived Warehouse total increases by 16;
- Receive actual quantity remains 16;
- no Transfer record is created;
- no generic Movement record is created;
- duplicate request replay does not double-count.

This full-quantity fixture is only the selected slice happy path. It is not a rule that partial Putaway is forbidden, and it adds no Acceptance Criterion. `OQ-014` remains open.

## Executed test evidence

| Test ID | Level | Scenario / evidence |
|---|---|---|
| `TEST-PUT-001` | PostgreSQL-backed API test | Allocation created; Backroom +16; Sales Shelf unchanged; derived total 16; Receive actual quantity unchanged |
| `TEST-PUT-002` | PostgreSQL-backed API test | Invalid destination rejected with no allocation or balance effect |
| `TEST-PUT-003` | PostgreSQL-backed API test | Same idempotency request replays without a second allocation or stock increment |
| `TEST-PUT-004` | PostgreSQL-backed API test | Allocation above eligible remaining quantity rejected with no data effect |
| `TEST-PUT-005` | PostgreSQL-backed API/schema assertion | No Transfer or generic Movement persistence path exists |
| `TEST-PUT-E2E-001` | Playwright | React UI loads the fixture, selects Backroom, submits through FastAPI and shows the committed success state backed by PostgreSQL 18 |

GitHub Actions `backend-checks`, `frontend-checks`, and `putaway-e2e` passed for both push and pull-request runs. `backend-checks` includes Alembic upgrade/downgrade/upgrade and the backend suite on PostgreSQL 18; `frontend-checks` includes lint/typecheck/test/build; `putaway-e2e` covers React → FastAPI → PostgreSQL 18. The first backend CI run exposed fixture FK ordering; flushing Warehouse before InternalLocation and then the dependent fixture records corrected the test setup without changing product behavior or canonical Acceptance Criteria.

## Preserved TBD/open items

- `OQ-012`: integer quantity is a Round 1 slice simplification only.
- `OQ-013`: Receive completion/handoff and Putaway exception/downstream lifecycle.
- `OQ-014`: partial Putaway.
- Staging HTTPS cookie evidence, PostgreSQL 17/Supabase verification, long-term production deployment, advanced pagination/filtering and unresolved NFR targets. `DEC-034/035` approve Vercel → Render → Supabase only for staging/demo; deployment has not been performed.

