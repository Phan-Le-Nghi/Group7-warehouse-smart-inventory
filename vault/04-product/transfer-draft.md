# Transfer — Product Artifact Draft

## Status

`SUPERSEDED — SPLIT INTO US-TRF-001 AND US-TRF-002`

This historical artifact reflects approved HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS from Round 2. Human review split it into [`US-TRF-001`](stories/US-TRF-001.md) for execution/confirmation and [`US-TRF-002`](stories/US-TRF-002.md) for history lookup. Use those canonical stories for current wording and Acceptance Criteria.

## Approved scope and sources

- `REQ-002`, `REQ-004`: Transfer is a required workflow area and a core domain concept.
- `CAND-REQ-003`: `system stock quantity` is maintained by tracked internal location.
- `FR-012`: active canonical requirement cho Warehouse Staff confirm Internal Transfer và tạo minimum Transfer record.
- `FR-013`: active canonical requirement cho Manager xem confirmed Transfer history.
- Historical `CAND-REQ-004`: `SUPERSEDED / DECOMPOSED` by `FR-012` and `FR-013`; không phải active canonical requirement.
- `CAND-BR-007`: confirmed Transfer reduces source quantity, increases the same quantity at destination and does not change Warehouse total.
- `CAND-BR-008`: confirmed Transfer has a minimum system record.
- `DEC-005`, `DEC-007`, `DEC-009`, `DEC-010`, `DEC-013`, `DEC-017`: one-Warehouse boundary, Transfer modeling, quantity behavior, recording/history and permissions.
- `EVD-010`, `EVD-011` remain current-state context only; they do not verify the approved system behavior.

## DRAFT User Story

### DRAFT-US-TRF-001

> Là Warehouse Staff, tôi muốn ghi nhận Transfer của một SKU từ source internal location sang destination internal location, để location quantities được cập nhật nhất quán và Transfer history có thể được dùng cho trace và discrepancy investigation.

## DRAFT Acceptance Criteria

### AC-TRF-001 — Confirm internal Transfer

```gherkin
Given SKU, quantity, source internal location và destination internal location trong cùng Warehouse
When Warehouse Staff confirm Transfer
Then source quantity được giảm theo Transfer quantity
And destination quantity được tăng cùng quantity
And Warehouse total quantity không thay đổi
```

### AC-TRF-002 — Minimum Transfer record

```gherkin
Given một Transfer được confirm
When system Transfer record được ghi nhận
Then record chứa SKU, quantity, source internal location, destination internal location và confirmation timestamp
```

### AC-TRF-003 — Transfer history

```gherkin
Given confirmed Transfer records tồn tại
When Manager xem Transfer history
Then history cho phép xem source, destination, quantity và time
```

These ACs are preserved as historical draft content. Current canonical ACs are split between `US-TRF-001` and `US-TRF-002`.

## High-level Transfer flow

```text
Need for subsequent relocation between tracked internal locations
  ↓
Warehouse Staff identifies SKU, quantity, source and destination
  ↓
Physical relocation + Transfer confirmation
  ↓
Reduce source quantity + increase same destination quantity
  ↓
Warehouse total remains unchanged
  ↓
Create system Transfer record
  ↓
Transfer history supports trace/discrepancy investigation
```

## Minimum record and query boundary

- Stored minimum: SKU, quantity, source internal location, destination internal location, confirmation timestamp.
- Query/history output: source, destination, quantity, time.
- Manager may view Transfer history and review exceptions.

## Scope guards and remaining questions

- Cross-Warehouse Transfer is outside MVP.
- Partial Transfer remains `OQ-014`.
- Historical note superseded: negative-stock behavior was later resolved by `DEC-019`; canonical behavior is in `US-TRF-001` and `CAND-BR-015`.
- Transfer exception, cancellation/reversal and failed-confirmation behavior remain `TBD / OQ-013`.
- No API, data model, persistence technology or architecture is defined here.

## Readiness

`SUPERSEDED`; canonical story review is complete. Technical implementation readiness remains subject to separately approved technical contracts.
