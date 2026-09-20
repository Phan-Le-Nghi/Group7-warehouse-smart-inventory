# Project Charter — Warehouse & Smart Inventory Management

## Trạng thái tài liệu

Baseline Report Round 1 được cập nhật từ các quyết định đã được con người phê duyệt tại `DEC-027` đến `DEC-029`. Project Vault là nguồn sự thật canonical; nội dung `TBD` / `OPEN QUESTION` không phải approved behavior.

## Thông tin dự án

- Project: Warehouse & Smart Inventory Management — Group 10
- Course: MIS3032_1
- Quy mô nhóm: 5
- Hạn Report Round 1: 04/09/2026
- Phương pháp: Requirement -> Vault -> User Story -> Codex Plan -> Artifact / Code -> Test -> Review -> Traceability -> Release

## Business context

Research hiện có gồm ba participant `P1`, `P2` và `P3`, tất cả đều làm việc tại cùng một minimart. Current operation tại minimart sử dụng KiotViet để theo dõi inventory quantity; physical location knowledge chủ yếu dựa vào cách sắp xếp thực tế và kinh nghiệm của staff. Evidence này chỉ mô tả current context của minimart đã nghiên cứu và không được generalize thành kết luận cho mọi Warehouse.

Research evidence và giới hạn canonical nằm tại [`../../vault/01-sources/research-evidence.md`](../../vault/01-sources/research-evidence.md) và [`../../vault/01-sources/interview-notes.md`](../../vault/01-sources/interview-notes.md). Không có transcript hoặc participant quote mới được suy diễn trong Charter.

## Problem statement

Warehouse & Smart Inventory Management cần hỗ trợ kiểm soát Receive, Putaway, Pick, Internal Transfer, Audit và Adjust trong một Warehouse; duy trì `system stock quantity` theo các internal location; ghi nhận và kiểm tra lại discrepancy trước khi điều chỉnh được Manager phê duyệt; đồng thời ngăn các stock operation đã được phê duyệt tạo quantity âm.

## Users và stakeholders

| Canonical role | Classification | Approved participation boundary |
|---|---|---|
| Warehouse Staff | Primary operational user | Thực hiện Receive, Putaway, Pick, Transfer và Audit count; tạo discrepancy / Adjust request |
| Manager | Decision/review stakeholder và operational user | Xem operational records; review exception/discrepancy; approve/reject Adjust; xem Transfer history; confirm/close sensitive exception flows trong phạm vi đã duyệt |
| Purchasing | Supporting/business stakeholder cho expected reference | Cung cấp/xem expected quantity/reference cho Receive; không có warehouse adjustment permission |
| Admin | Supporting/system administration role | Quản lý users, role assignments và basic system configuration; không bắt buộc tham gia daily warehouse operations |

Không suy diễn thêm role, persona hoặc create/edit/delete/override permission ngoài wording đã duyệt tại `DEC-017`.

## Project objectives

### OBJ-A — Product / project qualitative objective

Chuẩn hóa sáu workflow inventory chính trong phạm vi một Warehouse, duy trì stock có thể truy vết theo internal location, làm rõ discrepancy handling, và áp dụng các approved role outcomes mà không suy diễn lifecycle hoặc quyền hạn chưa được quyết định.

### OBJ-B — Delivery objective

Hoàn thiện baseline Report Round 1 với:

- đủ 6 workflow bắt buộc;
- đủ 9 canonical User Stories;
- mỗi story được map vào approved flow hoặc các approved flows tương ứng;
- các approved behavior branches có testable Acceptance Criteria;
- các unresolved behavior được ghi rõ là `TBD` hoặc `OPEN QUESTION`.

`OBJ-B` là delivery objective, không phải business outcome KPI. `OBJ-C` về duy trì CI pass cho first vertical slice đang `HOLD` và không phải project objective của toàn dự án.

## Success criteria

| ID | Type | Approved criterion | Verification boundary |
|---|---|---|---|
| `SC-01` | Delivery | 6/6 mandatory workflows được represented | Receive, Putaway, Pick, Transfer, Adjust và Audit xuất hiện trong baseline |
| `SC-02` | Delivery | 9/9 canonical User Stories được represented | Chỉ đếm active canonical stories, không đếm historical drafts |
| `SC-03` | Delivery | 9/9 canonical User Stories được map vào approved flow(s) | Kiểm tra mapping trong User Flow và Traceability |
| `SC-04` | Quality | Approved behavior branches có testable Acceptance Criteria | Không tạo AC cho behavior còn `TBD` / `OPEN QUESTION` |
| `SC-05` | Product / Delivery | 4/4 canonical roles có permission description | Warehouse Staff, Manager, Purchasing và Admin |
| `SC-06` | Delivery | Active approved items có traceability qua Requirement / BR / Decision / Story / Flow khi artifact tương ứng tồn tại | Không suy diễn unsupported percentage hoặc target mới |
| `SC-07` | Quality | Unsupported hoặc unresolved behavior được đánh dấu `TBD` / `OPEN QUESTION` | Kiểm tra report-facing và canonical artifacts |
| `SC-08` | Product / Scope quality | Không có known `OUT / DEFERRED` behavior bị trình bày như approved MVP behavior | Đối chiếu MVP Scope và Decision Log |
| `SC-09` | Quality / Delivery | First vertical slice `US-PUT-001` giữ backend/frontend/E2E CI verification `PASS` | Chỉ là criterion/evidence cho first vertical slice; không chứng minh toàn bộ MVP đã được implemented |

Không có quantitative business KPI được phê duyệt. Charter không đặt inventory accuracy, response-time, uptime, error-reduction hoặc productivity target.

## Product scope

### A. IN MVP

- Một Warehouse với hai tracked area-level internal locations: `Backroom` và `Sales Shelf`.
- `system stock quantity` theo internal location; Warehouse total được derive từ tổng location quantities.
- Receive actual-versus-expected comparison, quantity discrepancy và approved reference-review boundary.
- Initial Putaway allocation.
- Full, multi-location và `PARTIAL / INSUFFICIENT` Pick.
- Internal Transfer execution/confirmation, minimum system record và confirmed history.
- Selected-scope Audit với match/mismatch result, discrepancy context, mandatory re-check và no-auto-Adjust.
- Adjust request, required reason, optional attachment và Manager approve/reject trước apply.
- Approved permission outcomes của Warehouse Staff, Manager, Purchasing và Admin.
- Approved negative-stock guards cho Pick, Transfer và Adjust.

Chi tiết và trace ID-level nằm tại [`../03-product/mvp-scope.md`](../03-product/mvp-scope.md).

### B. OUT / DEFERRED trong current MVP

- Multi-Warehouse và cross-Warehouse operations.
- Aisle, rack, bin và detailed shelf.
- Full Purchase Order lifecycle.
- Downstream fulfilment/use sau Pick.
- FIFO, FEFO, reservation và Pick scanning.
- Automatic Adjust từ Audit mismatch.
- Automatic Transfer/Movement system record từ Putaway.
- Standalone Purchasing operational story và standalone Admin operational story.
- Alert implementation.
- Inventory Q&A, Explain inventory anomalies và Reorder recommendation AI directions.

`OUT / DEFERRED` chỉ mô tả current MVP baseline; không tự quyết định future scope hoặc đóng các Open Questions liên quan.

### C. OPEN / TBD

- `OQ-012`: lot/batch, serial, expiry, UOM/conversion, decimal quantity và precision/scale.
- `OQ-013`: các phần lifecycle/completion/handoff chưa được quyết định của các workflow.
- `OQ-014`: partial Receive, Putaway và Transfer; Pick partial đã được quyết định riêng.
- Alert trigger, recipient, threshold và workflow tại `OQ-021`.
- Production authentication mechanism.
- Deployment target và operating context.
- Barcode/QR, general scanner, mobile/offline và external integration tại `OQ-022`, trừ Pick scanning đã explicitly `OUT`.

Các mục `OPEN / TBD` không được trình bày như permanently out of scope hoặc approved behavior.

## Constraints và technical notes

### Product scope constraints

- Single-Warehouse MVP.
- Internal location ở mức area gồm `Backroom` và `Sales Shelf`.
- Sáu canonical workflows: Receive, Putaway, Pick, Transfer, Adjust và Audit.
- Bốn canonical roles: Warehouse Staff, Manager, Purchasing và Admin.
- Pick, Transfer và Adjust không được confirm/apply nếu operation sẽ làm affected internal-location quantity âm.

### Approved technical constraints

Theo `DEC-020/035`, stack đã được phê duyệt: React + TypeScript + Vite/npm; Python 3.13 + FastAPI/uv/pytest; PostgreSQL 17+ compatibility với PostgreSQL 18 local/CI baseline và Supabase PostgreSQL 17 staging target; Docker; SQLAlchemy 2 + Alembic; Playwright; modular monolith.

- Production authentication mechanism: PostgreSQL-backed server-side session design/spec approved at `DEC-031/033`; implementation đã merge và CI pass, còn staging HTTPS cookie behavior chưa verify.
- Staging/demo deployment target: Vercel frontend → Render FastAPI → Supabase PostgreSQL 17 approved at `DEC-032/034/035`; deployment chưa được implement/verify. Long-term production target và phần operating context còn lại vẫn `TBD`.
- Integer quantity chỉ là technical simplification cho `US-PUT-001` Round 1 vertical slice. UOM, decimal quantity, conversion behavior và precision/scale vẫn mở tại `OQ-012`; simplification này không phải product assumption.

## Assumptions

No active canonical assumptions.

Technical simplification của first vertical slice được ghi tại Constraints/Technical Notes và không được phân loại là product assumption.

## Risk register

| Risk | Impact | Current mitigation | Owner / TBD |
|---|---|---|---|
| Các phần của `OQ-013` và `OQ-014` còn mở | Charter, flow hoặc implementation có thể vô tình cam kết lifecycle/partial behavior chưa duyệt | Giữ explicit `TBD` / `OPEN QUESTION`; dùng bảng OPEN của MVP Scope làm boundary | Owner chưa được canonicalize; Product/BA và story owners quản lý artifact liên quan |
| Research sample chỉ gồm P1/P2/P3 tại cùng một minimart | Findings có thể bị generalize sai cho mọi Warehouse | Ghi rõ research limitation và tách verified evidence khỏi human product decisions | Risk owner: TBD; report-facing research artifact do Product/BA và UX/UI phụ trách |
| `user-research.md` hoặc report-facing status drift khỏi Vault | Báo cáo có thể mâu thuẫn với canonical evidence | Đồng bộ report-facing summary với `EVD-001–019`; Vault giữ thẩm quyền canonical | Product/BA — Thanh Ngân; UX/UI — Nghĩa |
| Figma High Fidelity và Dev Handoff chưa hoàn thành; exact hotspot wiring/metadata counts chưa verify | Chưa thể claim full interaction verification hoặc complete visual/handoff package | Browser access, 8 pages, 31 wireframe states, 31 prototype counterparts, 3 critical flows và 6 facilitator-only items đã human verify; giữ rõ các limitation còn lại | UX/UI — Nghĩa |
| Usability raw provenance bị giới hạn | Không có raw notes, recording, consent artifact hoặc participant quote để audit sâu hơn | Chỉ claim ba human-reviewed findings đã được cung cấp; không tạo quote/evidence mới | Risk owner: TBD |
| Production authentication chưa được quyết định | Không thể claim production-ready authentication | Giữ mechanism là `TBD`; chỉ áp dụng approved actor/auth boundary và `NFR-004` | Risk owner: TBD |
| Deployment target và operating context chưa được quyết định | Không thể claim deployment readiness hoặc đặt uptime/load target | Giữ `OQ-032/033` mở và không invent quantitative NFR | Risk owner: TBD |
| Chỉ `US-PUT-001` đã được implemented end-to-end | First slice có thể bị hiểu nhầm là full MVP implementation | Traceability ghi rõ trạng thái từng story và scope guard của first slice | Engineering/QA quản lý evidence liên quan; risk owner: TBD |

## First vertical slice

`US-PUT-001` là first completed and verified vertical slice. Backend PostgreSQL 18 checks, frontend checks và Playwright React -> FastAPI -> PostgreSQL 18 E2E đã được GitHub Actions xác minh.

Trạng thái này không có nghĩa full MVP complete hoặc toàn bộ system đã được implemented. Xem [`../TRACEABILITY.md`](../TRACEABILITY.md), [`../06-technical/story-specs/putaway.md`](../06-technical/story-specs/putaway.md) và [`../../vault/06-technical/story-specs/US-PUT-001.md`](../../vault/06-technical/story-specs/US-PUT-001.md).

## Nhóm và ownership

Xem [`team-roles.md`](team-roles.md) và ownership canonical trong [`../../vault/04-product/story-ownership.md`](../../vault/04-product/story-ownership.md).

## Open Questions

Danh sách và trạng thái canonical nằm tại [`../../vault/02-requirements/open-questions.md`](../../vault/02-requirements/open-questions.md). Việc hoàn thiện Charter không resolve `OQ-012`, phần unresolved của `OQ-013`, `OQ-014`, `OQ-021`, `OQ-022`, phần unresolved của `OQ-032/033` hoặc các AI Open Questions.
