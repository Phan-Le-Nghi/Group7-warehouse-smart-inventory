# API Contract — Bản phục vụ báo cáo

## Trạng thái

`PROPOSED TECHNICAL CONTRACT — DOCUMENTATION ONLY`

Canonical technical proposal: [`../../vault/06-technical/api-contract.md`](../../vault/06-technical/api-contract.md). Exact route và JSON shape là technical contract, không phải product requirement.

## Auth API baseline đã duyệt

| Route | Purpose | Trạng thái |
|---|---|---|
| `POST /api/v1/auth/login` | `{login_identifier,password}`; verify Argon2id, tạo PostgreSQL session, set cookie; response chỉ có actor | POST-REVIEW IMPLEMENTATION CANDIDATE — chờ PostgreSQL/E2E evidence |
| `POST /api/v1/auth/logout` | Revoke current server-side session, expire cookie, trả `204` | POST-REVIEW IMPLEMENTATION CANDIDATE — chờ PostgreSQL/E2E evidence |
| `GET /api/v1/auth/me` | Trả actor từ session, active user và current database role | POST-REVIEW IMPLEMENTATION CANDIDATE — chờ PostgreSQL/E2E evidence |

Session cookie là host-only `warehouse_session`, `HttpOnly`, `Path=/`, absolute 8 giờ, `Secure` tại staging/production và configurable `SameSite` theo topology. Missing/invalid/expired/revoked session hoặc inactive user trả `401`; authenticated actor thiếu quyền trả `403`. Login và `/me` trả `id`, normalized `login_identifier`, current `role`; token không xuất hiện trong JSON. Frontend không được truyền role làm source-of-truth; test actor injection chỉ dùng dependency override trong automated tests. Current MVP không thêm JWT, refresh token, self-registration, password reset, social login, OAuth, Keycloak hoặc external identity provider.

## MVP route map đề xuất

| Route | Purpose | Story/boundary |
|---|---|---|
| `GET /api/v1/locations` | Tracked-location selection | Supporting `CAND-REQ-003` |
| `GET /api/v1/stock?sku_id={id}` | Location balances + derived Warehouse total | `CAND-REQ-003` |
| `GET /api/v1/receives/context/{receive_id}` | Prepared expected context and existing recording/review state | `US-REC-001`; Warehouse Staff only |
| `POST /api/v1/receives` | Atomically record the full prepared line set, actual quantity and discrepancy/reference context | `US-REC-001`; `RECEIVE_RECORDED`, not completion |
| `POST /api/v1/receives/{receive_id}/reference-review` | Warehouse Staff acknowledgement of a recorded reference mismatch | `US-REC-001`; no approve/reject or reference correction |
| `POST /api/v1/putaways` | Initial destination allocation | `US-PUT-001`; detailed below |
| `GET /api/v1/putaways/context/{receive_line_id}` | SKU, eligible quantity và tracked destination IDs cho Putaway screen | `US-PUT-001`; không tạo automatic Receive handoff |
| `POST /api/v1/picks` | Multi-location/full/`PARTIAL / INSUFFICIENT` Pick | `US-PICK-001` |
| `POST /api/v1/transfers` | Atomic internal Transfer confirmation | `US-TRF-001` |
| `GET /api/v1/transfers` | Confirmed Transfer history | `US-TRF-002` |
| `POST /api/v1/audits` | Selected-scope count and comparison | `US-AUD-001` |
| `POST /api/v1/audit-discrepancies/{id}/rechecks` | Mandatory re-check context; no auto Adjust | `US-AUD-002` |
| `POST /api/v1/adjustments` | Re-checked request with reason; no pre-decision stock change | `US-ADJ-001` |
| `POST /api/v1/adjustments/{id}/decision` | Manager approve/reject | `US-ADJ-002` |

The three Receive routes and Putaway routes are implemented. Other listed routes
remain conceptual and require story-specific technical review.

## US-REC-001 Receive contract

Receive stores prepared expected quantity/reference separately from observed
actual quantity/document reference. Recording persists signed
`actual_quantity - expected_quantity` and exact, case-sensitive reference match
status after trimming surrounding whitespace. A second record command returns
`409 RECEIVE_ALREADY_RECORDED`; no correction or reversal workflow is exposed.

An unrecorded line returns `409 RECEIVE_NOT_RECORDED` at the Putaway boundary.
An unreviewed `REFERENCE_MISMATCH` returns
`409 REFERENCE_REVIEW_REQUIRED` from both Putaway context and confirmation before
allocation or stock mutation. `REFERENCE_MATCH`, reviewed mismatch, and legacy
rows with existing actual quantity remain compatible with Putaway.

Receive routes require the backend `WAREHOUSE_STAFF` session role and preserve
`401`/`403` semantics. They do not mutate `stock_balances`, create
`putaway_allocations`, create Transfer/Movement records, complete Receive, or
automatically navigate/call Putaway.

## POST /api/v1/putaways

Proposed request:

```json
{
  "receive_line_id": "<id>",
  "sku_id": "<id>",
  "quantity": 16,
  "destination_location_id": "<tracked-location-id>"
}
```

Request dùng proposed `Idempotency-Key` header. Destination ID phải tham chiếu `BACKROOM` hoặc `SALES_SHELF` thuộc Warehouse của Receive line. Success trả Putaway ID, Receive line, SKU, quantity, destination ID/code, confirmation time, committed destination balance và derived Warehouse total.

Error cases gồm missing/mismatched Receive/SKU, non-positive or malformed Round 1 integer quantity, invalid destination, allocation vượt eligible remaining và idempotency conflict. Tất cả failure đều không có data effect. Same-key/same-payload replay trả original result và không increment lần hai.

Transaction tạo Putaway allocation và tăng destination balance atomically; Receive actual quantity không đổi; không tạo Transfer hoặc generic Movement record.

Quantity thấp hơn remaining không bị contract này reject chỉ vì có thể là partial. Partial Putaway vẫn OPEN tại `OQ-014`; first slice chỉ test happy path dùng toàn bộ 16 eligible units.

## Contract boundaries

- Actor/auth dependency phải giữ canonical permission theo `DEC-017/031/033`; implementation đã merge và CI pass, nhưng staging HTTPS cookie behavior và PostgreSQL 17/Supabase evidence chưa được verify.
- Adjust target-vs-delta, attachment storage, advanced pagination/filtering, long-term production deployment và unresolved NFR còn TBD. Render chỉ được approve cho staging/demo tại `DEC-032`.
- `OQ-012`, `OQ-013` và `OQ-014` vẫn OPEN.
