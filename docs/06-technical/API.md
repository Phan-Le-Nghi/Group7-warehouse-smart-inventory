# API Contract — Bản phục vụ báo cáo

## Trạng thái

`IMPLEMENTED ROUTE INVENTORY THROUGH US-ADJ-002`

Canonical technical contract: [`../../vault/06-technical/api-contract.md`](../../vault/06-technical/api-contract.md). Exact route và JSON shape là technical contract, không phải product requirement.

## Auth API baseline đã duyệt

| Route | Purpose | Trạng thái |
|---|---|---|
| `POST /api/v1/auth/login` | `{login_identifier,password}`; verify Argon2id, tạo PostgreSQL session, set cookie; response chỉ có actor | IMPLEMENTED / MERGED |
| `POST /api/v1/auth/logout` | Revoke current server-side session, expire cookie, trả `204` | IMPLEMENTED / MERGED |
| `GET /api/v1/auth/me` | Trả actor từ session, active user và current database role | IMPLEMENTED / MERGED |

Session cookie là host-only `warehouse_session`, `HttpOnly`, `Path=/`, absolute 8 giờ, `Secure` tại staging/production và configurable `SameSite` theo topology. Missing/invalid/expired/revoked session hoặc inactive user trả `401`; authenticated actor thiếu quyền trả `403`. Login và `/me` trả `id`, normalized `login_identifier`, current `role`; token không xuất hiện trong JSON. Frontend không được truyền role làm source-of-truth; test actor injection chỉ dùng dependency override trong automated tests. Current MVP không thêm JWT, refresh token, self-registration, password reset, social login, OAuth, Keycloak hoặc external identity provider.

## Implemented MVP route map

| Route | Purpose | Story/boundary |
|---|---|---|
| `GET /api/v1/locations` | Tracked-location selection | Supporting `CAND-REQ-003` |
| `GET /api/v1/stock?sku_id={id}` | Location balances + derived Warehouse total | `CAND-REQ-003` |
| `GET /api/v1/receives/context/{receive_id}` | Prepared expected context and existing recording/review state | `US-REC-001`; Warehouse Staff only |
| `GET /api/v1/receives` | Prepared, unrecorded Receive queue | `US-REC-001`; read-only discovery, no create/completion semantics |
| `POST /api/v1/receives` | Atomically record the full prepared line set, actual quantity and discrepancy/reference context | `US-REC-001`; `RECEIVE_RECORDED`, not completion |
| `POST /api/v1/receives/{receive_id}/reference-review` | Warehouse Staff acknowledgement of a recorded reference mismatch | `US-REC-001`; no approve/reject or reference correction |
| `POST /api/v1/putaways` | Initial destination allocation | `US-PUT-001`; detailed below |
| `GET /api/v1/putaways/eligible-lines` | Receive lines with current `eligible_quantity > 0` | `US-PUT-001`; read-only, no new partial semantics |
| `GET /api/v1/putaways/context/{receive_line_id}` | SKU, eligible quantity và tracked destination IDs cho Putaway screen | `US-PUT-001`; không tạo automatic Receive handoff |
| `POST /api/v1/picks` | Multi-location/full/`PARTIAL / INSUFFICIENT` Pick | `US-PICK-001` |
| `GET /api/v1/picks` | Pick requests with persisted `outcome IS NULL` | `US-PICK-001`; excludes both current non-null outcomes, no reopen semantics |
| `POST /api/v1/transfers` | Atomic internal Transfer confirmation | `US-TRF-001` |
| `GET /api/v1/transfers/eligible-skus` | Positive-stock SKU selector with tracked-location quantities and derived total | `US-TRF-001`; no Transfer request lifecycle |
| `GET /api/v1/transfers` | Confirmed Transfer history | `US-TRF-002` |
| `GET /api/v1/audits/context` | Staff Audit SKU/location context with preview quantities | `US-AUD-001`; POST remains authoritative |
| `POST /api/v1/audits` | Selected-scope count and comparison | `US-AUD-001` |
| `GET /api/v1/audit-discrepancies` | Manager mismatch work list | `US-AUD-002`; read-only |
| `GET /api/v1/audit-discrepancies/{audit_line_id}` | Manager exact discrepancy/recheck detail | `US-AUD-002`; read-only |
| `POST /api/v1/audit-discrepancies/{id}/rechecks` | Mandatory re-check context; no auto Adjust | `US-AUD-002` |
| `GET /api/v1/adjustments/eligible-rechecks` | Staff read-only eligible mismatch-recheck queue | `US-ADJ-001`; excludes rechecks with an existing request |
| `GET /api/v1/adjustments/context/{audit_recheck_id}` | Staff exact Adjust context and persisted request status | `US-ADJ-001`; no current-stock preview |
| `POST /api/v1/adjustments` | Re-checked request with reason; no pre-decision stock change | `US-ADJ-001` |
| `GET /api/v1/adjustments?status=PENDING_MANAGER_DECISION` | Manager pending Adjust work queue only | `US-ADJ-002`; no history/search/export/advanced query |
| `GET /api/v1/adjustments/{id}` | Manager exact pending or terminal detail | `US-ADJ-002`; `PENDING_MANAGER_DECISION`, `APPLIED`, `REJECTED` |
| `POST /api/v1/adjustments/{id}/decision` | Manager approve/reject with separate required idempotency | `US-ADJ-002`; first commit/replay `200` |

Routes through `US-ADJ-002` above are implemented and merged at release candidate
`664d207`. Human-performed staging smoke exercised the nine story flows through
the deployed Vercel → Render → Supabase topology. Exact successful GitHub CI URLs
and job results for `664d207` are **NOT RECORDED** and are not inferred.

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

Implemented request:

```json
{
  "receive_line_id": "<id>",
  "sku_id": "<id>",
  "quantity": 16,
  "destination_location_id": "<tracked-location-id>"
}
```

Request dùng required `Idempotency-Key` header. Destination ID phải tham chiếu `BACKROOM` hoặc `SALES_SHELF` thuộc Warehouse của Receive line. Success trả Putaway ID, Receive line, SKU, quantity, destination ID/code, confirmation time, committed destination balance và derived Warehouse total.

Error cases gồm missing/mismatched Receive/SKU, non-positive or malformed Round 1 integer quantity, invalid destination, allocation vượt eligible remaining và idempotency conflict. Tất cả failure đều không có data effect. Same-key/same-payload replay trả original result và không increment lần hai.

Transaction tạo Putaway allocation và tăng destination balance atomically; Receive actual quantity không đổi; không tạo Transfer hoặc generic Movement record.

Quantity thấp hơn remaining không bị contract này reject chỉ vì có thể là partial. Partial Putaway vẫn OPEN tại `OQ-014`; first slice chỉ test happy path dùng toàn bộ 16 eligible units.

## US-ADJ-002 Manager decision contract

Only authenticated `MANAGER` may use the pending list, exact detail and decision
routes. Warehouse Staff, Purchasing and Admin receive `403`; unauthenticated
requests receive `401`. Detail supports pending and terminal reload, while the
list remains a pending-only work queue. The response includes requester/time,
reason, SKU/location, Original Audit, Manager Recheck, immutable snapshots and
requested change, status and applicable decision/apply evidence. It never
exposes idempotency facts or previews current stock.

The decision request requires an opaque case-sensitive `Idempotency-Key` and is
one of:

```json
{"decision": "APPROVE"}
```

```json
{"decision": "REJECT", "rejection_reason": "Required trimmed text"}
```

Reject reason is required, non-empty after trim and at most 500 characters;
approve forbids it. First successful commit and same-key/same-command historical
replay both return `200`. Decision idempotency key/fingerprint are separate from
US-ADJ-001 creation idempotency; replay never rereads or reapplies stock.

Approve locks the exact request, conflict-safely materializes a missing exact
balance as zero, locks/re-reads that balance, and requires current quantity to
equal the persisted recheck system snapshot. It then applies
`current_stock + requested_change` only when the result is non-negative and
atomically persists `APPLIED`, Manager/time and before/after evidence. Stale or
negative attempts return `409 ADJUSTMENT_STALE` or
`409 INSUFFICIENT_STOCK_FOR_ADJUSTMENT`, leave the request pending and have no
stock/decision effect. Reject locks only the request, persists required evidence
as terminal `REJECTED`, and has zero stock effect.

Other typed outcomes are `404 ADJUSTMENT_NOT_FOUND`,
`409 ADJUSTMENT_NOT_PENDING`, `409 IDEMPOTENCY_KEY_REUSED`,
`422 INVALID_REJECTION_REASON` and `422 INVALID_IDEMPOTENCY_KEY`. Rejected
requests cannot reopen or recreate from the same Audit recheck; a continuing
discrepancy requires a fresh Audit -> Recheck -> Adjust chain. The exact canonical
contract is in
[`../../vault/06-technical/story-specs/US-ADJ-002.md`](../../vault/06-technical/story-specs/US-ADJ-002.md).

## Contract boundaries

- Actor/auth dependency phải giữ canonical permission theo `DEC-017/031/033`; implementation đã merge. Human staging smoke verified login/session/logout và Manager-only Transfer History, nhưng exact external CI run URL/job evidence và cookie-attribute inspection riêng cho `664d207` không được ghi nhận.
- Adjust Manager decision/apply is approved at `DEC-043`; attachment storage, advanced pagination/filtering, long-term production deployment và unresolved NFR còn TBD. Vercel → Render → Supabase đã deploy cho staging/demo only.
- `OQ-012`, `OQ-013` và `OQ-014` vẫn OPEN.
