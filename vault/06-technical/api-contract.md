# API Contract — MVP Technical Proposal

## Status and authority boundary

`PROPOSED TECHNICAL CONTRACT — DOCUMENTATION ONLY`

Canonical behavior comes from requirements, Business Rules, decisions and canonical User Story Acceptance Criteria. HTTP routes and JSON shapes in this document are technical contracts proposed for implementation review; they are not product requirements.

Base path proposal: `/api/v1`.

`DEC-031` approves PostgreSQL-backed server-side sessions as the production authentication baseline and `DEC-033` approves the exact implementation contract. API routes depend on an actor/auth boundary that resolves the session cookie to an active user and current database role, then enforces the canonical permissions in `DEC-017`. A post-review implementation candidate now exists; dependency override remains automated-test-only and no production runtime actor switch exists. PostgreSQL/E2E verification remains pending.

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

Approved mapping: `401` for a missing, invalid, expired or revoked session or an inactive user; `403` for an authenticated actor without the canonical permission. The existing `404`, `409` and `422` mappings remain proposed technical contract behavior for their respective reference, state/idempotency/concurrency and malformed-data cases.

## Approved authentication API baseline

| Method and route | Purpose | Boundary |
|---|---|---|
| `POST /api/v1/auth/login` | Verify login identifier and Argon2id password hash, create a PostgreSQL session and set the secure session cookie | No self-registration, social login, JWT or refresh token |
| `POST /api/v1/auth/logout` | Revoke the current server-side session and expire the browser cookie | Logout is server-side revocation, not token denylisting |
| `GET /api/v1/auth/me` | Return the authenticated actor resolved from the current session and database role | Frontend-supplied role is never authoritative |

The browser cookie is `warehouse_session`, `HttpOnly`, host-only, uses `Path=/`, has an absolute eight-hour lifetime, is `Secure` in staging/production and uses configurable `SameSite` according to deployment topology. Login accepts `login_identifier` and `password`; login and `/me` return only actor `id`, normalized identifier and current role; logout returns `204`. Session tokens never appear in JSON. Demo account passwords enter through the single `DEMO_USER_PASSWORD` environment/platform secret and must not appear in the repository, Vault or CI logs.

## Proposed MVP route map

| Method and route | Request/response purpose | Canonical behavior traced | Contract gaps |
|---|---|---|---|
| `GET /api/v1/locations` | Return the two tracked locations for selection | `CAND-REQ-003`, `DEC-006/010` | Catalog administration not defined |
| `GET /api/v1/stock?sku_id={id}` | Return location balances and derived Warehouse total | `CAND-REQ-003`, `CAND-BR-003` | Advanced filtering/pagination TBD |
| `POST /api/v1/receives` | Record actual quantity and discrepancy/reference context | `US-REC-001` | Completion/handoff remains `OQ-013`; exact reference shape needs story-contract review |
| `POST /api/v1/putaways` | Confirm initial allocation into a tracked destination | `US-PUT-001` | Detailed contract below |
| `GET /api/v1/putaways/context/{receive_line_id}` | Load the SKU, eligible quantity and tracked destination IDs needed by the standalone Putaway screen | `US-PUT-001` UI support only | Does not define an automatic Receive → Putaway handoff |
| `POST /api/v1/picks` | Confirm one-or-many source allocations and report full or `PARTIAL / INSUFFICIENT` | `US-PICK-001` | Retry/cancel lifecycle remains open |
| `POST /api/v1/transfers` | Atomically reduce source, increase destination and record confirmation | `US-TRF-001` | Partial/failure/reversal remain open |
| `GET /api/v1/transfers` | Return confirmed Transfer history fields | `US-TRF-002` | Advanced filter/sort/export TBD |
| `POST /api/v1/audits` | Record selected-scope count/comparison and match/mismatch | `US-AUD-001` | Mismatch completion/schedule remain open |
| `POST /api/v1/audit-discrepancies/{id}/rechecks` | Record required re-check context without automatic Adjust | `US-AUD-002` | Exact lifecycle/handoff remains `OQ-013` |
| `POST /api/v1/adjustments` | Record re-checked discrepancy request and required reason; stock unchanged | `US-ADJ-001` | Target quantity vs signed delta and attachment storage TBD |
| `POST /api/v1/adjustments/{id}/decision` | Manager approve/reject; only valid approved apply may change stock | `US-ADJ-002` | Rejected-case closure remains open |

Routes other than Putaway remain conceptual and require story-specific technical review before implementation.

## US-PUT-001 — POST /api/v1/putaways

### Request

Header proposal:

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

Proposed status: `201 Created` for the first successful confirmation and `200 OK` when replaying the same idempotent request.

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

| Condition | Proposed result | Data effect |
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
- Authentication design and exact contract are approved by `DEC-031/033`; an implementation candidate exists, while PostgreSQL migration and browser E2E acceptance evidence remain pending. The topology-specific `SameSite` value remains deployment configuration.
- Idempotency key retention and storage detail are technical follow-up decisions.
- Adjust representation, attachment storage, advanced pagination/filtering, long-term production deployment and unresolved NFR targets remain `TBD`. Render is approved only for staging/demo by `DEC-032`.

