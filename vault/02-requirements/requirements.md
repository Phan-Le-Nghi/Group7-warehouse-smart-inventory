# Yêu cầu sản phẩm Warehouse

File này chỉ chứa yêu cầu sản phẩm/nghiệp vụ Warehouse được dẫn xuất từ bối cảnh dự án đã được giảng viên xác nhận, nghiên cứu đã được kiểm chứng hoặc HUMAN PRODUCT DECISIONS được ghi trong Decision Log. Không đưa deliverable môn học/báo cáo vào đây và không mô tả MVP assumptions như verified research findings.

## Schema priority canonical

Các giá trị priority canonical là `MUST`, `SHOULD`, `COULD` và `OUT / DEFERRED`. Priority chỉ áp dụng cho item đang active; item lịch sử đã supersede không được tính vào coverage active.

## Bối cảnh sản phẩm đã được giảng viên xác nhận

Các mục dưới đây chỉ bảo tồn phát biểu phạm vi đã được giảng viên xác nhận rõ ràng. Chúng không ngầm xác định hành vi hệ thống chi tiết.

| ID | Loại | Nội dung | Nguồn | Trạng thái | Priority |
|---|---|---|---|---|---|
| REQ-001 | Bài toán nghiệp vụ / scope context | Kiểm soát nhập, xuất, chuyển kho và tồn kho. | `SRC-01`, đoạn xác nhận nguyên văn: “Business problem: Kiểm soát nhập/xuất/chuyển kho và tồn.” | CONFIRMED bài toán; hành vi giải pháp TBD | MUST |
| REQ-002 | Phạm vi quy trình bắt buộc / scope constraint | Receive -> Putaway -> Pick -> Transfer -> Adjust -> Audit | `SRC-01`, đoạn xác nhận nguyên văn: “Required workflow: Receive -> Putaway -> Pick -> Transfer -> Adjust -> Audit” | CONFIRMED các khu vực/chuỗi; Round 2 quyết định một phần lifecycle, `OQ-013` vẫn mở | MUST |
| REQ-003 | Phạm vi role tối thiểu / scope constraint | Warehouse Staff; Manager; Purchasing; Admin | `SRC-01`, đoạn xác nhận nguyên văn: “Minimum roles: Warehouse Staff, Manager, Purchasing, Admin” | CONFIRMED tên role; MVP permissions được duyệt tại `DEC-017` / `CAND-REQ-010` | MUST |
| REQ-004 | Phạm vi core domain / scope constraint | SKU; Warehouse; Stock; Movement; Transfer; Alert; Audit | `SRC-01`, đoạn xác nhận nguyên văn: “Core domain: SKU, Warehouse, Stock, Movement, Transfer, Alert, Audit” | CONFIRMED thuật ngữ; Round 2 quyết định một phần Stock/Transfer/Audit behavior; phần còn lại TBD | MUST |

`SRC-01` được xác định trong [`../01-sources/assignment-brief.md`](../01-sources/assignment-brief.md) là bối cảnh dự án Nhóm 10 được giảng viên xác nhận từ `MIS3032_1_Aug2026_Plan_Master / De_Tai / Group 10`. Các đoạn nguyên văn phía trên là phát biểu do con người cung cấp và xác nhận để dùng cho scaffold này.

## Phạm vi MVP từ Human Product Decisions

Các mục dưới đây là lựa chọn phạm vi do con người phê duyệt. Chúng không phải research findings và không được dùng để khái quát vận hành ngoài phạm vi MVP.

| Decision | Phạm vi đã duyệt | Phần vẫn TBD / OPEN |
|---|---|---|
| `DEC-005` | MVP quản lý một Warehouse duy nhất; multi-Warehouse và cross-Warehouse operation ngoài MVP. | Không suy rộng thành kết luận rằng mọi hệ thống thực tế chỉ cần một Warehouse. |
| `DEC-006` | MVP hỗ trợ internal location ở mức area-level với `Backroom` và `Sales Shelf`; không gồm aisle, rack, bin hoặc detailed shelf. Một SKU có thể liên kết với nhiều internal locations trong cùng Warehouse. | Quantity model ban đầu để mở; được quyết định về sau tại `DEC-010`. |
| `DEC-007` | Transfer trong MVP chỉ nằm trong boundary subsequent relocation giữa tracked internal locations trong cùng một Warehouse. | Functional recording/effect ban đầu để mở; được quyết định về sau tại `DEC-013`. |
| `DEC-008` | MVP dùng thuật ngữ `system stock quantity`; không canonicalize `on-hand`, `available`, `reserved`, `damaged` hoặc `in-transit`. | Granularity/aggregation/effects ban đầu để mở; được quyết định một phần tại `DEC-010` đến `DEC-015`. |
| `DEC-009` | Phân biệt Physical movement và Movement system record. Putaway là initial placement sau Receive; Transfer là subsequent internal relocation; Pick là lấy quantity từ source internal location cho downstream purpose. | Detailed behavior ban đầu để mở; các behavior được duyệt về sau tại `DEC-011` đến `DEC-013`. |
| `DEC-010`–`DEC-015` | Duy trì quantity theo internal location và phê duyệt các effects cụ thể của Putaway, Pick, Transfer, Audit, Adjust. | Các partial behavior chưa được duyệt và lifecycle gaps tại `OQ-013` vẫn OPEN; negative stock được quyết định sau tại `DEC-019`. |
| `DEC-016` | Purchase Order lifecycle ngoài MVP; Receive dùng external/manual expected quantity/reference và bắt buộc human review khi reference mismatch. | Receive completion/handoff wording cuối vẫn thuộc `OQ-013`. |
| `DEC-017` | Phê duyệt MVP permission model cho Warehouse Staff, Manager, Purchasing và Admin. | Không suy diễn quyền ngoài wording được duyệt. |
| `DEC-018` | Làm rõ sáu workflow tại `REQ-002` là capability list, không phải transaction bắt buộc tuần tự; Pick và Transfer là các operational path độc lập, còn Audit có thể dẫn tới Adjust qua discrepancy và re-check. | Lifecycle gaps chưa được duyệt vẫn thuộc `OQ-013` và `OQ-014`. |
| `DEC-019` | Không cho phép `system stock quantity` tại internal location trở thành số âm; áp dụng validation guard cho Pick, Transfer và Adjust. | Retry/cancel lifecycle và reservation semantics không được quyết định bởi guard này. |

## Hướng AI đã xác nhận

Các mục này được giữ riêng khỏi yêu cầu sản phẩm đã cam kết vì giảng viên mô tả chúng là hướng tính năng AI. Chúng chưa phải yêu cầu tính năng chi tiết hoặc đã có Acceptance Criteria.

| ID | Loại | Nội dung | Nguồn | Trạng thái | Priority |
|---|---|---|---|---|---|
| AI-DIR-001 | Hướng tính năng AI | Inventory Q&A | `SRC-01`, đoạn xác nhận nguyên văn: “AI feature direction: Inventory Q&A” | CONFIRMED hướng; phạm vi tính năng và Acceptance Criteria TBD; không đóng `OQ-027` | OUT / DEFERRED |
| AI-DIR-002 | Hướng tính năng AI | Explain inventory anomalies | `SRC-01`, đoạn xác nhận nguyên văn: “AI feature direction: Explain inventory anomalies” | CONFIRMED hướng; định nghĩa anomaly, bằng chứng và Acceptance Criteria TBD; không đóng `OQ-028` | OUT / DEFERRED |
| AI-DIR-003 | Hướng tính năng AI | Reorder recommendation | `SRC-01`, đoạn xác nhận nguyên văn: “AI feature direction: Reorder recommendation” | CONFIRMED hướng; đầu vào, thẩm quyền, biện pháp an toàn và Acceptance Criteria TBD; không đóng `OQ-029` | OUT / DEFERRED |

`REQ-004` vẫn là `MUST` ở cấp core-domain scope đã được giảng viên xác nhận. Riêng Alert workflow/functionality có priority `OUT / DEFERRED` cho current MVP baseline theo `DEC-026`; `OQ-021` vẫn OPEN và không có Alert behavior nào được suy diễn.

## Functional Requirements đã được human review

Active canonical FR count là **12**. Các ID `CAND-REQ-*` đang active là approved canonical requirements dù giữ tiền tố lịch sử `CAND` để bảo toàn stable ID. `CAND-REQ-004` là lịch sử đã decomposed, không phải active FR và không được double-count. Cột nguồn phân biệt verified evidence với HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS; không được biến decision thành `EVD-*`.

| ID | Functional Requirement | Evidence -> Theme -> Insight | Trạng thái | Priority |
|---|---|---|---|---|
| CAND-REQ-001 | Sản phẩm nên hỗ trợ ghi nhận số lượng thực nhận và đối chiếu với số lượng kỳ vọng trong khu vực Receive. | `EVD-002`, `EVD-003` -> Kiểm nhận dựa trên số lượng thực tế -> Vận hành hiện tại đếm thực nhận và so với kỳ vọng. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-002 | Sản phẩm nên hỗ trợ ghi nhận chênh lệch giữa số lượng thực nhận và số lượng kỳ vọng để phục vụ việc xử lý tiếp theo. | `EVD-004`, `EVD-005` -> Kiểm nhận dựa trên số lượng thực tế -> Có chênh lệch khi nhận hàng cần được xử lý với bên giao; nguyên nhân, bằng chứng và phê duyệt TBD. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-003 | Trong MVP một Warehouse, sản phẩm phải duy trì và cho phép tra cứu `system stock quantity` của SKU theo từng tracked internal location. Các internal location là `Backroom` và `Sales Shelf`; một SKU có thể có quantity tại nhiều internal locations. Warehouse total quantity được xác định bằng tổng quantity của SKU tại các internal locations. MVP không bao gồm aisle, rack, bin hoặc detailed shelf. | `DEC-006`, `DEC-010` — HUMAN PRODUCT DECISION / MVP ASSUMPTION. `EVD-006` đến `EVD-009` chỉ cung cấp current-state context, không xác nhận quantity model. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-004 | Trong MVP, sản phẩm phải hỗ trợ ghi nhận và tra cứu Transfer là subsequent relocation của một SKU giữa tracked internal locations trong cùng một Warehouse. Mỗi system Transfer record phải chứa tối thiểu SKU, quantity, source internal location, destination internal location và confirmation timestamp. Transfer history phải cho phép xem source, destination, quantity và time để hỗ trợ trace và discrepancy investigation. | `DEC-007`, `DEC-013` — HUMAN PRODUCT DECISION / MVP ASSUMPTION. `EVD-010`, `EVD-011` chỉ là current-state context và không phải evidence cho system record. | SUPERSEDED / DECOMPOSED by `FR-012` and `FR-013` at `DEC-024`; historical only, not active | — |
| CAND-REQ-005 | Sản phẩm phải hỗ trợ selected-scope Audit session cho một nhóm SKU/location hoặc toàn Warehouse, gồm chọn scope, ghi physical count, so sánh với `system stock quantity` tại scope/location tương ứng và ghi nhận kết quả. | `EVD-015`, `EVD-016` hỗ trợ count/compare trong current state; selected-scope product behavior là HUMAN PRODUCT DECISION / MVP ASSUMPTION tại `DEC-014`. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-006 | Sản phẩm phải hỗ trợ Warehouse Staff thực hiện Pick từ một Pick request có SKU và requested quantity, lấy quantity từ một hoặc nhiều tracked internal locations, xác nhận Pick và ghi nhận trường hợp `PARTIAL / INSUFFICIENT`. Downstream fulfilment/use nằm ngoài MVP. | `DEC-012` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; không phải verified research finding. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-007 | Sản phẩm phải hỗ trợ Warehouse Staff thực hiện initial placement sau Receive bằng cách xác nhận SKU, quantity và destination internal location là `Backroom` hoặc `Sales Shelf`, đồng thời phân bổ quantity vào destination internal location. | `DEC-011` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; `EVD-006`, `EVD-007` chỉ là current-state context. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-008 | Sản phẩm phải hỗ trợ Warehouse Staff tạo discrepancy/Adjust request và Manager review, approve hoặc reject request. Approved Adjust cập nhật `system stock quantity` tại internal location bị ảnh hưởng. | `DEC-015` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; `EVD-012`, `EVD-013`, `EVD-017` chỉ hỗ trợ re-check/current-state handling. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-009 | Trong Receive, sản phẩm phải hỗ trợ expected quantity từ external/manual order or delivery reference do Purchasing cung cấp hoặc chuẩn bị. Full Purchase Order lifecycle nằm ngoài MVP. | `DEC-016` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; không phải verified research finding. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-010 | Sản phẩm phải áp dụng MVP permission model đã duyệt cho Warehouse Staff, Manager, Purchasing và Admin, phân biệt quyền thực hiện operation, xem record, xử lý exception, approve/reject Adjust và quản trị users/role assignments/basic system configuration. | `DEC-017` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; `EVD-013`, `EVD-014` chỉ là current-state context. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| CAND-REQ-011 | Sản phẩm phải ngăn Pick, Transfer hoặc Adjust được confirm/apply nếu operation sẽ làm `system stock quantity` tại internal location nhỏ hơn 0. Khi validation không đạt, không apply quantity change và operation được báo không hợp lệ/không thể confirm. | `DEC-019` — HUMAN PRODUCT DECISION / MVP ASSUMPTION; resolve `OQ-015`. Không phải verified research finding. | APPROVED CANONICAL — historical `CAND` prefix retained | MUST |
| FR-012 | Hệ thống phải cho Warehouse Staff confirm Internal Transfer và tạo record tối thiểu gồm SKU, quantity, source, destination và confirmation timestamp. | `DEC-013`, `CAND-BR-007`, `CAND-BR-008`, `US-TRF-001`; approved decomposition tại `DEC-024`. | APPROVED CANONICAL — active | MUST |
| FR-013 | Hệ thống phải cho Manager tra cứu confirmed Transfer history, tối thiểu hiển thị source, destination, quantity và confirmation time. | `DEC-013`, `DEC-017`, `US-TRF-002`; approved decomposition tại `DEC-024`. | APPROVED CANONICAL — active | MUST |

## Non-functional Requirements

Canonical NFR count là **5**. Các metric chưa được human approve vẫn giữ `TBD`; phần unresolved của `OQ-033` tiếp tục mở.

| ID | Nhóm | Non-functional Requirement | Verification | Nguồn | Trạng thái | Priority |
|---|---|---|---|---|---|---|
| NFR-001 | Data integrity / Reliability | Mọi stock-changing operation phải commit toàn bộ các thay đổi liên quan hoặc rollback toàn bộ nếu operation thất bại. | Không tồn tại partial write trên failure path được test. | `DEC-022`, [`ADR-002`](../06-technical/adrs/ADR-002-transactional-stock-consistency.md), approval tại `DEC-025` | APPROVED CANONICAL | MUST |
| NFR-002 | Data integrity / Concurrency | Các stock-changing command xung đột đồng thời không được làm vi phạm per-location stock consistency hoặc negative-stock invariant. | Concurrency test phải chứng minh invariant vẫn được giữ; không có load/concurrent-user target. | `DEC-022`, [`ADR-002`](../06-technical/adrs/ADR-002-transactional-stock-consistency.md), approval tại `DEC-025` | APPROVED CANONICAL | MUST |
| NFR-003 | Reliability | Trong phạm vi Putaway Round 1, replay cùng command với cùng `Idempotency-Key` và cùng payload không được tạo thêm Putaway allocation hoặc tăng stock lần hai. | `TEST-PUT-003` hoặc equivalent existing test evidence; retention window `TBD`; không mở rộng sang command khác. | [`ADR-003`](../06-technical/adrs/ADR-003-receive-putaway-stock-posting.md), [`US-PUT-001` Technical Story Spec](../06-technical/story-specs/US-PUT-001.md), [`TEST-PUT-003`](../../apps/backend/tests/test_putaway.py), approval tại `DEC-025` | APPROVED CANONICAL | SHOULD |
| NFR-004 | Security / Authorization | Mọi protected operation phải enforce permission outcome đã được duyệt trong `DEC-017` thông qua actor/auth boundary. Production authentication baseline là PostgreSQL-backed server-side session theo `DEC-031`. | Authorization behavior phải test được theo approved role outcome và `401`/`403` semantics; approved design chưa phải implementation evidence. | `DEC-017`, `DEC-031`, [Technical Architecture](../06-technical/architecture.md), approval tại `DEC-025` | APPROVED CANONICAL | MUST |
| NFR-005 | Usability | UI phải thể hiện `PARTIAL / INSUFFICIENT` khác rõ ràng với Pick completed để tránh người dùng hiểu nhầm là hoàn tất. | UI/state/copy review và human-reviewed P2 usability evidence; không có numeric usability threshold. | [Human-reviewed P2 usability finding](../../docs/05-design/usability-findings.md), approval tại `DEC-025` | APPROVED CANONICAL | SHOULD |

### Scope guard cho CAND-REQ-003

`CAND-REQ-003` được giới hạn bởi `DEC-010` và `DEC-019`: quantity được duy trì theo internal location, Warehouse total là tổng các location quantities và quantity tại internal location không được âm. Workflow effects chỉ áp dụng theo các Business Rules được duyệt; không được suy diễn thêm Receive Stock effect, retry/cancel lifecycle, reservation semantics hoặc behavior ngoài các quyết định đã duyệt.

## Quy tắc tiếp nhận yêu cầu

Yêu cầu mới phải dẫn xác nhận của giảng viên, bằng chứng nghiên cứu đã được kiểm chứng hoặc HUMAN PRODUCT DECISION được ghi trong Decision Log; phải có stable ID và được con người review. Không được âm thầm nâng giả định, simulated input hoặc đề xuất AI thành yêu cầu.
