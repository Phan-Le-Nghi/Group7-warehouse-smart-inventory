# Data Model — Warehouse & Smart Inventory Management

## Status and modeling policy

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

This document distinguishes the conceptual MVP model from the first vertical-slice implementation model. It is not an implemented schema or migration.

## Inventory authority

- Authoritative stock is persisted per `SKU + internal location`.
- MVP internal locations are `BACKROOM` and `SALES_SHELF` in one Warehouse.
- One SKU may have balances at both internal locations.
- Warehouse total is derived by summing those location balances; there is no `warehouse_totals` table.
- Application validation and a database `CHECK quantity >= 0` protect the non-negative invariant.
- Round 1 represents quantity as integer units only as a technical simplification. `OQ-012` remains open for UOM, decimal quantity, conversion and precision/scale.

## Conceptual MVP model

| Concept | Proposed persistence need | Minimum responsibility | Detail status |
|---|---|---|---|
| SKU | `skus` | Stable item identity used by stock and operations | Conceptual; catalog management behavior is not defined |
| Warehouse | `warehouses` | Single MVP Warehouse identity and relationship boundary | Conceptual; multi-Warehouse is out of MVP |
| Internal Location | `internal_locations` | `BACKROOM` or `SALES_SHELF`, belonging to the MVP Warehouse | Approved technical foundation |
| Stock by location | `stock_balances` | Unique balance per SKU/location with non-negative quantity | Approved technical foundation |
| Receive | `receives`, `receive_lines` | External/manual reference context, SKU, expected/actual quantity and discrepancy context | Conceptual except fields needed by Putaway slice |
| Putaway | `putaway_allocations` | Record confirmed initial destination allocation and prevent double-count | First vertical-slice model |
| Pick | `pick_requests`, `pick_allocations` | Represent a Pick request and its one-or-many source allocations | Conceptual; full schema deferred |
| Transfer | `transfers` | Minimum confirmed record: SKU, quantity, source, destination, confirmation time | Conceptual; required by canonical stories |
| Audit | `audit_sessions`, `audit_lines`; discrepancy/re-check persistence as needed | Selected scope, physical/system comparison and match/mismatch context | Conceptual; lifecycle details remain open |
| Adjust | `adjust_requests` | Reason, re-check link, optional attachment reference, Manager decision and approved apply context | Conceptual; target-vs-delta and attachment storage are `TBD` |
| User | `users` | Normalized unique login identity, Argon2id `password_hash`, one current role and active/inactive state | Exact schema approved at `DEC-033`; implementation candidate pending PostgreSQL evidence |
| Auth Session | `auth_sessions` | Store only the SHA-256 digest of a random session token, link to user, and track creation, expiry and revocation | Exact schema and cleanup policy approved at `DEC-033`; implementation candidate pending PostgreSQL evidence |

Table names above are technical proposals. A business-object name alone is not sufficient reason to create a table; a table should be introduced only when its story is implemented and needs durable state or relational integrity.

For `users` and `auth_sessions`, `DEC-033` approves the exact implementation schema. `users` contains UUID `id`, normalized unique `login_identifier`, Argon2id `password_hash`, constrained `role`, `is_active` and timezone-aware timestamps. `auth_sessions` contains UUID `id`, unique 32-byte SHA-256 `session_token_hash`, cascading `user_id`, `created_at`, `expires_at`, nullable `revoked_at`, expiry ordering check, user index and active-expiry partial index. Plaintext passwords and raw session tokens must not be persisted. Migration `20260919_0002` is a post-review implementation candidate pending PostgreSQL verification.

The normalized identifier invariant is enforced by `login_identifier = lower(trim(login_identifier))`. `updated_at` is application-managed through SQLAlchemy in the current baseline; no database trigger is required. SQLAlchemy `create_all` component tests are not Alembic migration evidence.

## First vertical-slice model — US-PUT-001

| Proposed table | Minimum fields/invariants |
|---|---|
| `warehouses` | `id`; slice fixture contains one Warehouse |
| `internal_locations` | `id`, `warehouse_id`, `code`; unique warehouse/code; codes limited to `BACKROOM` and `SALES_SHELF` for MVP |
| `skus` | `id`, stable SKU code |
| `receive_lines` | `id`, `sku_id`, `actual_quantity`; fixture actual quantity is 16; actual quantity remains unchanged by Putaway |
| `stock_balances` | `sku_id`, `location_id`, integer `quantity`; unique SKU/location; `CHECK quantity >= 0` |
| `putaway_allocations` | `id`, `receive_line_id`, `sku_id`, `quantity`, `destination_location_id`, `confirmed_at`, idempotency identity |

No `warehouse_totals`, generic `movements` or Putaway-created `transfers` are part of this model.

## Receive → Putaway consistency

Receive persists actual received quantity and discrepancy/reference context but does not increase tracked-location stock. Putaway performs the initial posting.

For each Putaway confirmation, the application transaction locks the relevant Receive line and computes:

```text
eligible remaining quantity
  = receive_line.actual_quantity
  - sum(previously confirmed Putaway allocations for that Receive line)
```

An allocation must be positive and must not exceed eligible remaining quantity. This over-allocation guard prevents double-count but does not prohibit partial Putaway. Partial Putaway remains open at `OQ-014`.

The vertical-slice test uses all 16 eligible units only as its selected happy-path fixture. It is not a full-only business rule or a new Acceptance Criterion.

## Transaction and concurrency constraints

- Putaway inserts its allocation and increments its destination balance in one transaction.
- Pick, Transfer and approved Adjust will also use a transaction when implemented.
- A command that violates an invariant rolls back without partial effects.
- A unique idempotency identity plus Receive-line locking prevents duplicate requests from incrementing stock twice.
- Exact idempotency transport/retention is part of the proposed API contract, not a product requirement.

## Explicit exclusions

The data model does not introduce warehouse totals, generic Movement abstraction, alert/AI tables, full Purchase Order lifecycle, reservations, FIFO/FEFO, lot/batch or multi-Warehouse routing.

