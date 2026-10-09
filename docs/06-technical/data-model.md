# ERD / Data Model — Bản phục vụ báo cáo

## Trạng thái

`IMPLEMENTED MODEL THROUGH MIGRATION 20260927_0009`

Canonical detail: [`../../vault/06-technical/data-model.md`](../../vault/06-technical/data-model.md).

## Inventory model được duyệt

- Authoritative stock được persist theo `SKU + internal location`.
- MVP có `BACKROOM` và `SALES_SHELF` trong một Warehouse.
- Một SKU có thể có quantity tại cả hai locations.
- Warehouse total được derive từ location balances; không có `warehouse_totals`.
- Application và PostgreSQL đều bảo vệ `quantity >= 0`.
- Quantity dùng integer unit trong Round 1 vertical slice như technical simplification; UOM/decimal/conversion/precision tại `OQ-012` vẫn OPEN.

## Implemented MVP model

| Area | Proposed persistence | Mức chi tiết hiện tại |
|---|---|---|
| SKU/Warehouse/Location | `skus`, `warehouses`, `internal_locations` | Implemented foundation |
| Stock | `stock_balances`, unique theo SKU/location | Implemented foundation |
| Receive | `receives`, `receive_lines` | US-REC-001 recording context implemented; final completion/handoff remains open |
| Putaway | `putaway_allocations` | First vertical-slice model |
| Pick | `pick_requests`, `pick_allocations` | Implemented current slice |
| Transfer | `transfers` immutable confirmed record | Implemented current slice |
| Audit | `audit_sessions`, `audit_lines`, `audit_rechecks` | Implemented through migrations `20260926_0006`–`0007`; broader lifecycle remains open |
| Adjust | `adjust_requests` with immutable request intent plus terminal decision/apply evidence | Implemented through migrations `20260927_0008`–`0009`; attachment storage TBD |
| User | `users`: normalized unique login identity, Argon2id password hash, current role, active state | Exact schema approved tại `DEC-033`; implementation merged và CI verified |
| Auth Session | `auth_sessions`: SHA-256 session digest, user link, created/expiry/revocation timestamps | Exact schema approved tại `DEC-033`; implementation merged và CI verified |

Không tạo table chỉ vì business-object name tồn tại. Table chỉ được đưa vào implementation khi story cần durable state hoặc relational integrity.

`DEC-033` approve exact schema cho `users` và `auth_sessions`, gồm normalized `login_identifier`, role constraint, digest-only token storage, expiry ordering, FK/indexes và absolute lifetime 8 giờ. Migration `20260919_0002` đã merge và có human-confirmed PostgreSQL 18 CI evidence; PostgreSQL 17 staging verification vẫn bắt buộc theo `DEC-035`. Component tests dùng SQLAlchemy metadata không tự động được xem là Alembic/PostgreSQL migration evidence. `updated_at` được application quản lý qua SQLAlchemy trong baseline hiện tại; không có database trigger.

## US-PUT-001 vertical-slice model

Các bảng trực tiếp cần cho slice: `warehouses`, `internal_locations`, `skus`, `receive_lines`, `stock_balances`, `putaway_allocations`.

Receive ghi actual quantity nhưng không tăng tracked-location stock. Putaway transaction:

1. lock Receive line;
2. lấy `actual_quantity - sum(previously confirmed allocations)`;
3. ngăn allocation vượt eligible remaining quantity;
4. tạo Putaway allocation và tăng destination balance trong cùng transaction;
5. derive Warehouse total sau commit.

Guard này ngăn double-count nhưng không cấm partial Putaway. Fixture 16 units được post toàn bộ chỉ là happy path của slice; `OQ-014` vẫn OPEN.

## DEC-045 supporting creation model

The upstream usability extension requires no schema or migration. A new prepared
Receive uses the existing nullable pre-recording state in `receives`/`receive_lines`;
a new Pick Request uses the existing null outcome/confirmation state in
`pick_requests`. `skus` supplies the stock-free selector. Creation stores no
creator/time/idempotency facts and does not insert/update `stock_balances`,
`putaway_allocations` or `pick_allocations`.

## US-REC-001 recording model

`receives` stores nullable legacy-safe expected/document references, reference
match status, recording actor/time, and mismatch-review actor/time.
`receive_lines` stores nullable expected quantity, nullable actual quantity before
recording, and signed quantity discrepancy. New prepared contexts are validated
by the application; the migration does not fabricate expected/reference/reviewer
facts for legacy rows.

Database checks protect non-negative present quantities, discrepancy consistency,
allowed reference status, paired review metadata, and mismatch-only review.
Recording/review actors reference `users`. No Receive status/completion, Purchase
Order, correction history, Transfer, Movement, or Warehouse-total persistence is
introduced.

Downgrade to `20260919_0002` fails explicitly when any post-migration Receive line
still has `actual_quantity IS NULL`; it neither backfills nor deletes that data.

## US-ADJ-002 decision/apply model

`DEC-043` approves extending `adjust_requests` rather than creating an
application table or generic movement/decision ledger. Status is exactly
`PENDING_MANAGER_DECISION`, `APPLIED` or `REJECTED`. Nullable decision fields are
`decided_by_user_id`, `decided_at`, normalized `rejection_reason`,
`applied_stock_before`, `applied_stock_after`,
`decision_idempotency_key` and `decision_request_fingerprint`.

State-dependent checks require all decision/application fields null while
pending; Manager/time plus before/after and decision-idempotency facts for
`APPLIED`; and Manager/time, required rejection reason and decision-idempotency
facts for `REJECTED`. Apply evidence satisfies
`applied_stock_after = applied_stock_before + requested_change` with non-negative
before/after values. Creation and decision idempotency remain separate.

Approve conflict-safely inserts an exact missing `stock_balances` row at zero,
then locks/re-reads it before snapshot-match and non-negative validation. The
balance change and terminal decision evidence share one transaction. Reject does
not read, create, lock or mutate stock. No `adjustment_applications`, generic
Movement, Warehouse total or duplicated applied-change field is introduced.

## Audit and Adjust migration chain

- `20260926_0006` creates `audit_sessions` and `audit_lines`, including scope,
  result/status, submit idempotency, unique Audit pair, quantity/discrepancy/result
  consistency and source foreign keys.
- `20260926_0007` creates exactly-one-per-line `audit_rechecks`, current-stock and
  physical snapshots, result consistency, performer/time and recheck idempotency.
- `20260927_0008` creates exactly-one-per-recheck `adjust_requests`, immutable source
  snapshots, signed non-zero requested change, normalized reason, requester/time and
  creation idempotency in initial `PENDING_MANAGER_DECISION` state.
- `20260927_0009` extends that table with terminal `APPLIED`/`REJECTED` state,
  Manager/time, reject or apply evidence and separate decision idempotency. It refuses
  downgrade while terminal rows exist.

## Operational downgrade warning

Downgrades across migrations `0006`–`0008` drop Audit/Adjust business tables and can
destroy their data. Treat those downgrades as development/test operations unless data
loss is explicitly accepted. Production rollback should prefer a forward fix or a
verified backup/restore strategy unless an approved migration-specific rollback plan
exists. The `0009` terminal-row refusal is an additional guard; it does not make the
earlier destructive downgrades safe.

## Không thuộc model này

Không có `warehouse_totals`, generic Movement abstraction, alert/AI tables, full PO lifecycle, reservation, FIFO/FEFO, lot/batch hoặc multi-Warehouse routing.
