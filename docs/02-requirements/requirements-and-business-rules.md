# Requirements và Business Rules — Bản phục vụ báo cáo

Tài liệu này là bản phục vụ báo cáo, không phải bản canonical thứ hai.

## Yêu cầu sản phẩm

Yêu cầu canonical và bằng chứng được duy trì trong [`../../vault/02-requirements/requirements.md`](../../vault/02-requirements/requirements.md).

Hiện đã xác nhận ở cấp cao:

- `REQ-001`: kiểm soát nhập, xuất/lấy hàng, chuyển kho và tồn kho;
- `REQ-002`: phạm vi vận hành gồm Receive, Putaway, Pick, Transfer, Adjust và Audit;
- `REQ-003`: các role Warehouse Staff, Manager, Purchasing và Admin;
- `REQ-004`: các khái niệm SKU, Warehouse, Stock, Movement, Transfer, Alert và Audit.

Round 2 đã bổ sung HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS cho per-location quantity, Putaway, Pick, Transfer, Audit, Adjust, Receive/Purchasing và permissions. Các quyết định này không phải verified research findings. Danh sách canonical và stable IDs nằm trong Vault.

Requirements + NFR Round 1 đã được human review tại `DEC-024` đến `DEC-026`:

- Active canonical FR count: **12**.
- `CAND-REQ-004` là lịch sử `SUPERSEDED / DECOMPOSED`, không được double-count.
- `FR-012` (`MUST`) cover Warehouse Staff confirm Internal Transfer và tạo minimum record; trace tới `US-TRF-001`.
- `FR-013` (`MUST`) cover Manager tra cứu confirmed Transfer history; trace tới `US-TRF-002`.
- Các active `CAND-REQ-*` còn lại là approved canonical requirements dù giữ tiền tố lịch sử `CAND`; mỗi active FR có priority `MUST`.

## Non-functional Requirements

Canonical NFR count: **5**.

| ID | Summary | Priority | Source / verification boundary |
|---|---|---|---|
| `NFR-001` | Atomic stock mutation: commit toàn bộ hoặc rollback toàn bộ | MUST | `DEC-022`, `ADR-002`; no partial write trên tested failure path |
| `NFR-002` | Consistency under conflicting concurrent stock commands | MUST | `DEC-022`, `ADR-002`; concurrency test giữ invariant, không có load target |
| `NFR-003` | Putaway Round 1 idempotency cho cùng key/payload | SHOULD | `ADR-003`, Putaway spec, `TEST-PUT-003`; retention window TBD |
| `NFR-004` | Enforce approved role outcome qua actor/auth boundary | MUST | `DEC-017/031/033`, architecture; PostgreSQL-backed session implementation merged và CI verified; staging HTTPS behavior chưa verify |
| `NFR-005` | Phân biệt rõ Pick `PARTIAL / INSUFFICIENT` với completed | SHOULD | Human-reviewed P2 usability finding; không có numeric threshold |

`OQ-033` chỉ được partially addressed. `DEC-032/034/035` approve Vercel → Render → Supabase PostgreSQL 17 staging/demo environment và release boundaries; response-time, uptime, concurrent-user/load target, numeric usability threshold và long-term production operating/deployment context vẫn OPEN/TBD. `CNFR-06` không được approve.

## Quy tắc nghiệp vụ

Các rule canonical đã human review gồm `CAND-BR-001` đến `CAND-BR-015`; từng rule có priority `MUST`. Chúng bao phủ actual Receive quantity, re-check trước Adjust, location aggregation, Putaway/Pick/Transfer effects, Transfer recording, Audit comparison/no-auto-Adjust, Adjust control/outcome, Receive reference mismatch và negative-stock guard. Xem [`../../vault/02-requirements/business-rules.md`](../../vault/02-requirements/business-rules.md) để có wording và classification chính xác.

## Khoảng trống

`OQ-015` đã được resolve bởi `DEC-019`. `OQ-012` và `OQ-014` vẫn OPEN; `OQ-013` vẫn `PARTIALLY DECIDED / OPEN`. `OQ-032` và phần quantitative/context còn lại của `OQ-033` chưa được resolve. Alert/AI có priority `OUT / DEFERRED` cho current MVP nhưng các OQ liên quan không bị đóng. Xem [`../../vault/02-requirements/open-questions.md`](../../vault/02-requirements/open-questions.md).
