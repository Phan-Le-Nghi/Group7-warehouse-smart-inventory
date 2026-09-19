# Story Spec — Transfer / Movement Tracking

**Status:** HISTORICAL DRAFT — product stories canonicalized; technical contract review pending

**Canonical Story IDs:** `US-TRF-001`, `US-TRF-002`

**Owner:** Nguyễn Thị Ly Na

This spec records approved functional outcomes only. It does not choose architecture, data model, API, persistence technology, validation design or implementation. Round 2 decisions are HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS, not verified research findings.

## 1. Traceability

- Requirements: `REQ-002`, `REQ-003`, `REQ-004`, `CAND-REQ-003`, `CAND-REQ-010`, `CAND-REQ-011`, `FR-012` for `US-TRF-001` and `FR-013` for `US-TRF-002`. Historical `CAND-REQ-004` is `SUPERSEDED / DECOMPOSED` and is not an active trace target.
- Business Rules: `CAND-BR-003`, `CAND-BR-007`, `CAND-BR-008`, `CAND-BR-015`.
- Human decisions: `DEC-005`, `DEC-007`, `DEC-009`, `DEC-010`, `DEC-013`, `DEC-017`, `DEC-019`.
- Current-state evidence only: `EVD-010`, `EVD-011`, `EVD-019`.
- Open: `OQ-013` for Transfer exception/reversal, `OQ-014` for partial Transfer and `OQ-022` for device/integration behavior. `OQ-015` is resolved by `DEC-019`.

`OQ-011`, `OQ-016` and `OQ-020` are resolved by HUMAN PRODUCT DECISIONS. Their resolution does not turn the supporting simulated input into verified research evidence.

## 2. Goal

Support subsequent relocation of a SKU between tracked internal locations in the same Warehouse, keep per-location quantities consistent and expose Transfer history for trace and discrepancy investigation.

Cross-Warehouse Transfer is outside MVP.

## 3. Canonical User Stories

### US-TRF-001 — Execution/confirmation

> Là Warehouse Staff, tôi muốn xác nhận Internal Transfer giữa tracked internal locations, để source và destination quantities được cập nhật nhất quán mà không đổi Warehouse total.

### US-TRF-002 — History lookup

> Là Manager, tôi muốn xem Transfer history, để trace relocation và hỗ trợ discrepancy investigation.

Canonical wording and AC are maintained in `vault/04-product/stories/US-TRF-001.md` and `US-TRF-002.md`. This technical draft does not override them.

## 4. Approved functional inputs and outputs

### Minimum confirmed Transfer record

| Field | Approved meaning |
|---|---|
| SKU | SKU being relocated |
| quantity | Quantity transferred |
| source internal location | Tracked source within the MVP Warehouse |
| destination internal location | Tracked destination within the MVP Warehouse |
| confirmation timestamp | Time of Transfer confirmation |

This table defines product information requirements, not a database schema or API contract.

### History/query output

- source
- destination
- quantity
- time

Manager may view Transfer history. The approved purpose is trace and discrepancy investigation.

## 5. Approved happy path

1. A need exists for subsequent relocation between tracked internal locations.
2. Warehouse Staff identifies SKU, quantity, source and destination.
3. Physical relocation occurs and Warehouse Staff confirms Transfer.
4. Source `system stock quantity` decreases by Transfer quantity.
5. Destination `system stock quantity` increases by the same quantity.
6. Warehouse total quantity remains unchanged.
7. The system records SKU, quantity, source, destination and confirmation timestamp.
8. The record is available through Transfer history/query.

## 6. Canonical Acceptance Criteria reference

### US-TRF-001 / AC-TRF1-001 — Confirm quantity effects

```gherkin
Given SKU, quantity, source internal location và destination internal location trong cùng Warehouse
When Warehouse Staff confirm Transfer
Then source quantity được giảm theo Transfer quantity
And destination quantity được tăng cùng quantity
```

### US-TRF-001 / AC-TRF1-002 — Preserve Warehouse total

```gherkin
Given Internal Transfer được confirm
When quantity effects được ghi nhận
Then Warehouse total quantity không thay đổi
```

### US-TRF-001 / AC-TRF1-003 — Minimum Transfer record

```gherkin
Given một Transfer được confirm
When system Transfer record được ghi nhận
Then record chứa SKU, quantity, source internal location, destination internal location và confirmation timestamp
```

### US-TRF-001 / AC-TRF1-004 — Prevent negative source quantity

```gherkin
Given Transfer quantity lớn hơn system stock quantity tại source location
When Warehouse Staff cố confirm Transfer
Then Transfer không được confirm
And quantity change không được apply
And operation được báo không hợp lệ hoặc không thể confirm
```

### US-TRF-002 / AC-TRF2-001 to AC-TRF2-003 — Transfer history

```gherkin
Given confirmed Transfer records tồn tại
When Manager mở Transfer history
Then Manager có thể xem history
And confirmed records expose source, destination, quantity và confirmation time
```

The canonical story files are authoritative if this historical technical draft becomes stale.

## 7. Unresolved behavior

- Transfer exception, cancellation, reversal and failed-confirmation behavior: `OQ-013`.
- Partial Transfer: `OQ-014`.
- Negative-stock guard: approved at `DEC-019`; retry/cancel lifecycle after failed validation remains TBD.
- Barcode/QR/scanner/mobile/offline/integration behavior: `OQ-022`.
- Validation details beyond the approved same-Warehouse/tracked-location and negative-stock guards: TBD.

No unresolved behavior above may be inferred during implementation.

## 8. Technical boundary

- Architecture foundation: approved at `DEC-020` — modular monolith with React + TypeScript + Vite, Python 3.13 + FastAPI, PostgreSQL 18, SQLAlchemy 2 + Alembic and Playwright.
- Stock/data foundation: approved at `DEC-021` and `DEC-022` — per-location stock is authoritative and stock-changing operations use transactional consistency guards. Transfer-specific schema still requires story-specific technical review.
- API foundation: HTTP/JSON through the approved FastAPI boundary; exact Transfer route/payload/error contract still requires story-specific technical review.
- Authentication/authorization implementation: TBD; only the product permission outcome is approved.
- Deployment target: TBD.
- Implementation and tests: not started.

This spec is not implementation-ready until the technical contract receives its required review.
