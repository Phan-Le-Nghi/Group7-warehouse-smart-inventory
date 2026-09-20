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
| User | `users`: normalized unique login identity, Argon2id password hash, current role, active state | Exact schema approved tại `DEC-033`; implementation candidate chờ PostgreSQL evidence |
| Auth Session | `auth_sessions`: SHA-256 session digest, user link, created/expiry/revocation timestamps | Exact schema approved tại `DEC-033`; implementation candidate chờ PostgreSQL evidence |

Không tạo table chỉ vì business-object name tồn tại. Table chỉ được đưa vào implementation khi story cần durable state hoặc relational integrity.

`DEC-033` approve exact schema cho `users` và `auth_sessions`, gồm normalized `login_identifier`, role constraint, digest-only token storage, expiry ordering, FK/indexes và absolute lifetime 8 giờ. Migration `20260919_0002` là implementation candidate; component tests dùng SQLAlchemy metadata không được xem là Alembic/PostgreSQL migration evidence. `updated_at` được application quản lý qua SQLAlchemy trong baseline hiện tại; không có database trigger.

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
