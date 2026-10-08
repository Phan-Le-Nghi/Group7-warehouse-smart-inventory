# API Contract — Implemented MVP Baseline

## Status and authority boundary

`IMPLEMENTED ROUTE CONTRACT THROUGH US-ADJ-002`

Canonical behavior comes from requirements, Business Rules, decisions and canonical User Story Acceptance Criteria. HTTP routes and JSON shapes are technical contracts, not product requirements.

Base path: `/api/v1`.

`DEC-031` approves PostgreSQL-backed server-side sessions as the production authentication baseline and `DEC-033` approves the exact implementation contract. API routes depend on an actor/auth boundary that resolves the session cookie to an active user and current database role, then enforces the canonical permissions in `DEC-017`. The implementation is merged; dependency override remains automated-test-only and no production runtime actor switch exists. Human staging smoke at `664d207` verified login/session/logout and database-backed story persistence. Exact CI run results and a separate cookie-attribute inspection for this commit are not recorded.

## Common error shape

```json
{
  "error": {
    "code": "STABLE_TECHNICAL_CODE",
    "message": "Human-readable summary",
    "details": {}
  }
}
```

Implemented mapping: `401` for a missing, invalid, expired or revoked session or an inactive user; `403` for an authenticated actor without the canonical permission. The implemented `404`, `409` and `422` mappings cover their respective reference, state/idempotency/concurrency and malformed-data cases.

## Approved authentication API baseline

| Method and route | Purpose | Boundary |
|---|---|---|
| `POST /api/v1/auth/login` | Verify login identifier and Argon2id password hash, create a PostgreSQL session and set the secure session cookie | No self-registration, social login, JWT or refresh token |
| `POST /api/v1/auth/logout` | Revoke the current server-side session and expire the browser cookie | Logout is server-side revocation, not token denylisting |
| `GET /api/v1/auth/me` | Return the authenticated actor resolved from the current session and database role | Frontend-supplied role is never authoritative |

The browser cookie is `warehouse_session`, `HttpOnly`, host-only, uses `Path=/`, has an absolute eight-hour lifetime, is `Secure` in staging/production and uses configurable `SameSite` according to deployment topology. Login accepts `login_identifier` and `password`; login and `/me` return only actor `id`, normalized identifier and current role; logout returns `204`. Session tokens never appear in JSON. Demo account passwords enter through the single `DEMO_USER_PASSWORD` environment/platform secret and must not appear in the repository, Vault or CI logs.

## Implemented MVP route map summary

| Method and route | Request/response purpose | Canonical behavior traced | Contract gaps |
|---|---|---|---|
| `GET /api/v1/locations` | Return the two tracked locations for selection | `CAND-REQ-003`, `DEC-006/010` | Catalog administration not defined |
| `GET /api/v1/stock?sku_id={id}` | Return location balances and derived Warehouse total | `CAND-REQ-003`, `CAND-BR-003` | Advanced filtering/pagination TBD |
| `POST /api/v1/receives` | Record actual quantity and discrepancy/reference context | `US-REC-001` | Completion/handoff remains `OQ-013` |
| `GET /api/v1/receives` | Return prepared, unrecorded Receive contexts for Staff selection | `US-REC-001` discovery support | Does not create Receive or define completion |
| `POST /api/v1/putaways` | Confirm initial allocation into a tracked destination | `US-PUT-001` | Detailed contract below |
| `GET /api/v1/putaways/eligible-lines` | Return recorded Receive lines whose current canonical `eligible_quantity` is positive | `US-PUT-001` discovery support | Does not decide partial Putaway behavior |
| `GET /api/v1/putaways/context/{receive_line_id}` | Load the SKU, eligible quantity and tracked destination IDs needed by the standalone Putaway screen | `US-PUT-001` UI support only | Does not define an automatic Receive → Putaway handoff |
| `POST /api/v1/picks` | Confirm one-or-many source allocations and report full or `PARTIAL / INSUFFICIENT` | `US-PICK-001` | Retry/cancel lifecycle remains open |
| `GET /api/v1/picks` | Return Pick requests whose current persisted outcome is `null` | `US-PICK-001` discovery support | `FULLY_COMPLETED` and `PARTIAL_INSUFFICIENT` are excluded; no reopen/retry/cancel semantics |
| `POST /api/v1/transfers` | Atomically reduce source, increase destination and record confirmation | `US-TRF-001` | Partial/failure/reversal remain open |
| `GET /api/v1/transfers/eligible-skus` | Return SKUs with positive stock and a valid tracked source/destination combination, including current per-location quantities and derived total | `US-TRF-001` discovery support | Does not create a Transfer request lifecycle |
| `GET /api/v1/transfers` | Return confirmed Transfer history fields | `US-TRF-002` | Advanced filter/sort/export TBD |
| `POST /api/v1/audits` | Record selected-scope count/comparison and match/mismatch | `US-AUD-001` | Mismatch completion/schedule remain open |
| `POST /api/v1/audit-discrepancies/{id}/rechecks` | Record required re-check context without automatic Adjust | `US-AUD-002` | Exact lifecycle/handoff remains `OQ-013` |
| `POST /api/v1/adjustments` | Record re-checked discrepancy request and required reason; stock unchanged | `US-ADJ-001` | Attachment storage remains deferred |
| `POST /api/v1/adjustments/{id}/decision` | Manager approve/reject; only valid approved apply may change stock | `US-ADJ-002` | Broader correction/reversal lifecycle remains open |

Routes through `US-ADJ-002` are implemented and merged. The exact route
inventory is maintained in [`../../docs/06-technical/API.md`](../../docs/06-technical/API.md).

## Human-approved product discovery boundary — 2026-10-08

The four discovery GET routes above are read-only navigation support. They do
not add models, migrations, request creation, transaction effects or lifecycle
states. Receive returns only prepared contexts with `recorded_at IS NULL`.
Putaway reuses the existing eligibility calculation and excludes exhausted
lines. Pick returns only `outcome IS NULL`; both current non-null outcomes are
kept outside the queue without defining reopen behavior. Transfer returns only
SKUs with positive stock when at least two tracked locations provide a distinct
source/destination combination. Exact-context routes remain authoritative after
the user selects an item.

## US-PUT-001 — POST /api/v1/putaways

### Request

Required header:

```http
Idempotency-Key: <client-generated opaque value>
```

```json
{
  "receive_line_id": "<id>",
  "sku_id": "<id>",
  "quantity": 16,
  "destination_location_id": "<tracked-location-id>"
}
```

Round 1 quantity is an integer-unit simplification; this request shape does not resolve `OQ-012`. `destination_location_id` must reference `BACKROOM` or `SALES_SHELF` in the Receive line's MVP Warehouse.

### Success response

Implemented status: `201 Created` for the first successful confirmation and `200 OK` when replaying the same idempotent request.

```json
{
  "putaway_id": "<id>",
  "receive_line_id": "<id>",
  "sku_id": "<id>",
  "quantity": 16,
  "destination_location_id": "<tracked-location-id>",
  "destination_location": "BACKROOM",
  "confirmed_at": "<timestamp>",
  "stock": {
    "destination_quantity": 16,
    "warehouse_total": 16
  }
}
```

Warehouse total is derived from committed location balances.

### Validation and errors

| Condition | Implemented result | Data effect |
|---|---|---|
| Missing Receive line or SKU | `404 RECEIVE_LINE_NOT_FOUND` / `SKU_NOT_FOUND` | None |
| Quantity is not a positive Round 1 integer | `422 INVALID_QUANTITY` | None |
| SKU does not match Receive line | `409 RECEIVE_LINE_SKU_MISMATCH` | None |
| Destination is not a tracked MVP location or belongs outside the MVP Warehouse | `422 INVALID_DESTINATION` | None |
| Quantity exceeds the not-yet-posted quantity for the Receive line | `409 PUTAWAY_EXCEEDS_ELIGIBLE_QUANTITY` | None |
| Same idempotency key and same payload is replayed | Return the original committed result | No additional effect |
| Same idempotency key is reused with a different payload | `409 IDEMPOTENCY_KEY_REUSED` | None |

Quantity below eligible remaining is not rejected merely because it could be partial. Partial Putaway behavior remains open at `OQ-014`; the first slice exercises only a full-quantity happy-path fixture.

### Transaction effect

Within one PostgreSQL transaction:

1. lock the referenced Receive line;
2. calculate previously posted and remaining eligible quantity;
3. validate request and idempotency state;
4. create one Putaway allocation;
5. increment the destination `stock_balances` row;
6. commit and derive the Warehouse total.

The transaction does not modify Receive actual quantity and does not create a Transfer or generic Movement record. Any failure rolls back the allocation and stock update together.

## Open contract decisions

- `OQ-012`, `OQ-013` and `OQ-014` remain open.
- Authentication design and exact contract are approved by `DEC-031/033`; implementation is merged. Human staging smoke verified login/session/logout, while exact cookie-attribute inspection and exact CI results for `664d207` are not recorded. `DEC-034` fixes the staging baseline at Vercel same-origin rewrite with `Secure` and `SameSite=Lax`.
- Idempotency key retention and storage detail are technical follow-up decisions.
- Attachment storage, advanced pagination/filtering, long-term production deployment and unresolved NFR targets remain `TBD`. `DEC-034/035` approve Vercel → Render → Supabase PostgreSQL 17 only for staging/demo; that topology is deployed and human-smoke verified at `664d207` without a production-grade claim.

