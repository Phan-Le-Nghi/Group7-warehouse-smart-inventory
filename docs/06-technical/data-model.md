# ERD / Data Model — Bản phục vụ báo cáo

## Trạng thái

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Canonical detail: [`../../vault/06-technical/data-model.md`](../../vault/06-technical/data-model.md).

## Inventory model được duyệt

- Authoritative stock được persist theo `SKU + internal location`.
- MVP có `BACKROOM` và `SALES_SHELF` trong một Warehouse.
- Một SKU có thể có quantity tại cả hai locations.
- Warehouse total được derive từ location balances; không có `warehouse_totals`.
- Application và PostgreSQL đều bảo vệ `quantity >= 0`.
- Quantity dùng integer unit trong Round 1 vertical slice như technical simplification; UOM/decimal/conversion/precision tại `OQ-012` vẫn OPEN.

## Conceptual MVP model

| Area | Proposed persistence | Mức chi tiết hiện tại |
|---|---|---|
| SKU/Warehouse/Location | `skus`, `warehouses`, `internal_locations` | Conceptual foundation |
| Stock | `stock_balances`, unique theo SKU/location | Approved foundation |
| Receive | `receives`, `receive_lines` | Conceptual; actual quantity và context cần cho Putaway |
| Putaway | `putaway_allocations` | First vertical-slice model |
| Pick | request + source allocations | Conceptual; schema chi tiết deferred |
| Transfer | minimum confirmed Transfer record | Conceptual; canonical fields đã duyệt |
| Audit | session + comparison lines + discrepancy/re-check persistence khi cần | Conceptual; lifecycle còn OPEN |
| Adjust | request/decision context | Conceptual; quantity representation và attachment storage TBD |
| User | `users`: login identity, Argon2id password hash, current role, active state | APPROVED DESIGN tại `DEC-031`; chưa implement |
| Auth Session | `auth_sessions`: hashed random session token, user link, created/expiry/revocation timestamps | APPROVED DESIGN tại `DEC-031`; chưa implement |

Không tạo table chỉ vì business-object name tồn tại. Table chỉ được đưa vào implementation khi story cần durable state hoặc relational integrity.

Auth baseline approve các field conceptual: `users(id, login identifier, password_hash, role, is_active, created_at/updated_at nếu cần)` và `auth_sessions(id, session_token_hash, user_id, created_at, expires_at, revoked_at)`. Plaintext password và raw session token không được persist. Exact SQL types/indexes/constraints và session lifetime thuộc implementation spec; chưa có auth migration hoặc implementation.

## US-PUT-001 vertical-slice model

Các bảng trực tiếp cần cho slice: `warehouses`, `internal_locations`, `skus`, `receive_lines`, `stock_balances`, `putaway_allocations`.

Receive ghi actual quantity nhưng không tăng tracked-location stock. Putaway transaction:

1. lock Receive line;
2. lấy `actual_quantity - sum(previously confirmed allocations)`;
3. ngăn allocation vượt eligible remaining quantity;
4. tạo Putaway allocation và tăng destination balance trong cùng transaction;
5. derive Warehouse total sau commit.

Guard này ngăn double-count nhưng không cấm partial Putaway. Fixture 16 units được post toàn bộ chỉ là happy path của slice; `OQ-014` vẫn OPEN.

## Không thuộc model này

Không có `warehouse_totals`, generic Movement abstraction, alert/AI tables, full PO lifecycle, reservation, FIFO/FEFO, lot/batch hoặc multi-Warehouse routing.
