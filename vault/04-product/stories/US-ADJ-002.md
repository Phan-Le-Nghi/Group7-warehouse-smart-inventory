# US-ADJ-002 — Quyết định và apply Adjust

## Trạng thái và ownership

`CANONICAL — HUMAN APPROVED`

Owner: Đặng Thị Thanh Ngân.

## User Story

Là Manager, tôi muốn approve hoặc reject Adjust request, để chỉ approved Adjust mới cập nhật `system stock quantity` tại affected location.

## Business value và scope

Story cover Manager decision, approved apply effect và no-change branches. Theo
`DEC-043`, `APPLIED` và `REJECTED` là terminal trong current slice; stale hoặc
insufficient failed approval giữ request ở `PENDING_MANAGER_DECISION`.

## Traceability

- Requirements: `REQ-001`, `REQ-002`, `REQ-003`, `CAND-REQ-003`, `CAND-REQ-008`, `CAND-REQ-010`, `CAND-REQ-011`.
- Business rules: `CAND-BR-002`, `CAND-BR-011`, `CAND-BR-013`, `CAND-BR-015`.
- Evidence: `EVD-012`, `EVD-013`, `EVD-017` hỗ trợ current-state re-check/Manager involvement.
- Human decisions: `DEC-010`, `DEC-015`, `DEC-017`, `DEC-019`.
- Open question: `OQ-013`.
- Source classification: verified evidence + HUMAN PRODUCT DECISION.

## Acceptance Criteria

### AC-ADJ2-001 — Approve and apply

Given discrepancy đã re-check, reason đã ghi và Manager approves request, when Adjust được apply, then `system stock quantity` tại affected internal location được cập nhật.

### AC-ADJ2-002 — Reject without quantity change

Given Manager rejects request, when rejection được ghi nhận, then `system stock quantity` không thay đổi.

### AC-ADJ2-003 — No discrepancy after re-check

Given re-check không còn discrepancy, when case được xử lý, then Adjust không được apply và quantity không thay đổi.

### AC-ADJ2-004 — Prevent negative adjusted quantity

Given một approved Adjust sẽ làm `system stock quantity` tại affected internal location nhỏ hơn 0, when Adjust được cân nhắc apply, then Adjust không được apply, quantity không thay đổi và operation được báo không hợp lệ/không thể confirm.

## Remaining gaps và scope guards

- `DEC-043` supersedes các gap cũ cho current slice: rejected request không reopen
  hoặc recreate từ cùng recheck; stale/insufficient failed approval vẫn pending.
- Broader Audit correction/reversal và lifecycle ngoài current Adjust slice tiếp tục
  `PARTIALLY DECIDED / OPEN` tại `OQ-013`.
