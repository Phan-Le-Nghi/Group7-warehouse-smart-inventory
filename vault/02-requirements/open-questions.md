# Câu hỏi mở

Ownership của Audit đã được xác nhận và không phải câu hỏi mở: Nghi sở hữu Putaway như User Story cá nhân chính, đồng thời sở hữu/hỗ trợ quy trình Audit bắt buộc.

## Môn học và phê duyệt

| ID | Câu hỏi mở | Hạng mục bị chặn |
|---|---|---|
| OQ-001 | Thời điểm nộp bài chính xác và múi giờ áp dụng ngày 04/09/2026 là gì? | Kế hoạch nộp bài cuối |
| OQ-002 | Gói nộp bài gồm repository, báo cáo, slide, live demo hay kết hợp các hình thức nào? | Đóng gói báo cáo |
| OQ-003 | Số người tham gia/phương pháp tối thiểu cho User Research và Usability Test là gì? | Bằng chứng nghiên cứu và usability |
| OQ-004 | Ngoài ít nhất 20 câu và các loại câu hỏi bắt buộc, Q&A Benchmark có format, cách chạy hoặc ngưỡng đạt nào khác không? | Hoàn thành benchmark |
| OQ-005 | Template hoặc tiêu chí chấm nào xác định một AI Usage Log cá nhân có ý nghĩa? | Bằng chứng AI cá nhân |
| OQ-006 | Mỗi sinh viên phải nộp bằng chứng đóng góp cá nhân nào? | Bằng chứng báo cáo theo sinh viên |
| OQ-007 | Ai là người phê duyệt cuối cùng cho yêu cầu sản phẩm và quy tắc nghiệp vụ? | Phê duyệt yêu cầu |
| OQ-008 | Nguồn course/assignment gốc, có thẩm quyền và đúng encoding cần bảo tồn là nguồn nào? | Tính toàn vẹn của nguồn thô |

## Nghiên cứu, sản phẩm và thiết kế

| ID | Câu hỏi mở | Hạng mục bị chặn |
|---|---|---|
| OQ-009 | Nhóm có thể tiếp cận stakeholder hoặc người tham gia thực tế nào cho nghiên cứu và usability testing? | Nghiên cứu đã kiểm chứng |
| OQ-010 | Phạm vi hệ thống gồm một Warehouse hay nhiều Warehouse? | `RESOLVED — HUMAN PRODUCT DECISION`: MVP quản lý một Warehouse duy nhất; multi-Warehouse ngoài MVP. Đây là product-scope choice, không phải research conclusion (`DEC-005`). |
| OQ-011 | Stock on-hand, available, reserved, damaged và in-transit được định nghĩa như thế nào, nếu có áp dụng? | `RESOLVED — HUMAN PRODUCT DECISION`: MVP dùng `system stock quantity` theo internal location; Warehouse total là tổng location quantities. Workflow effects được chốt tại `DEC-010` đến `DEC-015`. Không canonicalize các bucket đã nêu. |
| OQ-012 | Lot/batch, serial number, expiry date, unit of measure hoặc unit conversion có thuộc phạm vi không? | `OPEN`: `DEC-037`, `DEC-038` và `DEC-040` chỉ approve strict integer như implementation constraint cho current Pick, Transfer và Audit slices. Các quyết định slice này không canonicalize global quantity representation; lot/batch, serial, expiry, UOM, decimal quantity và conversion vẫn mở. |
| OQ-013 | Trigger, điều kiện trước, kết quả thành công, ngoại lệ và trạng thái hoàn tất của từng khu vực quy trình bắt buộc là gì? | `PARTIALLY DECIDED / OPEN`: `DEC-036` approve `RECEIVE_RECORDED`, Warehouse Staff mismatch acknowledgement và downstream Putaway eligibility guard, nhưng không canonicalize final Receive completion hoặc exact Receive -> Putaway handoff. `DEC-037` approve một immutable Pick result cho prepared/external request và typed conflict khi confirm lần hai; correction/reversal, future retry/idempotency và Manager partial-review contract vẫn ngoài current Pick slice. `DEC-038` approve immutable Transfer confirmation, transactional safe replay và đặt correction/reversal ngoài `US-TRF-001`. `DEC-039` chỉ approve read-only confirmed Transfer history và không quyết định failure/cancel/correction/reversal lifecycle. `DEC-040` approve `US-AUD-001` submit-time snapshot, `MATCH_COMPLETED`/`MISMATCH_RECORDED`, Audit-specific safe replay và strict no-stock-effect contract; Manager review, mandatory recheck, discrepancy resolution, correction/reversal và broader Audit lifecycle tiếp tục thuộc `US-AUD-002` hoặc future contract. Putaway exception/downstream handoff, broader Transfer lifecycle, Adjust rejected-case closure và các handoff chưa nêu rõ vẫn mở. |
| OQ-014 | Có hỗ trợ thực hiện một phần đối với Receive, Putaway, Pick hoặc Transfer không? | `OPEN` ở cấp cross-workflow: `DEC-037` đã quyết định current Pick slice cho phép một explicit `PARTIAL_INSUFFICIENT` result với `0 < picked_quantity < requested_quantity`, explicit user confirmation và không auto-allocation; multiple later partial confirmations ngoài slice. Partial Receive là `NOT IMPLEMENTED` trong current slice theo `DEC-036` nhưng không bị loại vĩnh viễn; partial Putaway vẫn chưa quyết định. `DEC-038` xác định partial Transfer là `NOT IMPLEMENTED` trong current `US-TRF-001` slice, không loại vĩnh viễn hoặc đóng câu hỏi toàn cục. |
| OQ-015 | Có cho phép tồn kho âm không? | `RESOLVED — HUMAN PRODUCT DECISION`: `system stock quantity` tại internal location không được âm. Pick, Transfer và Adjust không được confirm/apply nếu operation sẽ tạo quantity âm; không apply quantity change và báo operation không hợp lệ/không thể confirm (`DEC-019`, `CAND-REQ-011`, `CAND-BR-015`). Retry/cancel lifecycle và reservation semantics không được suy diễn. |
| OQ-016 | Transfer là giữa các location, giữa các Warehouse hay cả hai? | `RESOLVED — HUMAN PRODUCT DECISION`: trong MVP, Transfer chỉ là subsequent relocation giữa tracked internal locations trong cùng một Warehouse; cross-Warehouse Transfer ngoài MVP (`DEC-007`). |
| OQ-017 | Adjust và Audit yêu cầu lý do, bằng chứng và phê duyệt nào? | `RESOLVED — HUMAN PRODUCT DECISION`: re-check và Adjust reason bắt buộc; attachment/evidence optional; Manager approve/reject trước apply; Audit không auto Adjust (`DEC-014`, `DEC-015`). |
| OQ-018 | Audit là cycle count, full stocktake hay cả hai? | `RESOLVED — HUMAN PRODUCT DECISION`: MVP dùng selected-scope Audit session cho nhóm SKU/location hoặc toàn Warehouse; không canonicalize `cycle count` (`DEC-014`). |
| OQ-019 | Purchasing tham gia như thế nào và Purchase Order có thuộc phạm vi sản phẩm không? | `RESOLVED — HUMAN PRODUCT DECISION`: full Purchase Order lifecycle ngoài MVP; Purchasing cung cấp/xem external/manual expected quantity/reference; reference mismatch phải được user review trước Receive completion (`DEC-016`, `DEC-017`). |
| OQ-020 | Warehouse Staff, Manager, Purchasing và Admin có những quyền nào? | `RESOLVED — HUMAN PRODUCT DECISION`: MVP permission model được xác định tại `DEC-017` và `roles.md`. |
| OQ-021 | Alert nào thuộc phạm vi, điều kiện nào kích hoạt và ai nhận Alert? | Yêu cầu Alert |
| OQ-022 | Barcode/QR, scanner, sử dụng mobile/offline hoặc tích hợp bên ngoài có thuộc phạm vi không? | `OPEN`: current approved slices, gồm `US-AUD-001` tại `DEC-040`, không thêm scanner/device, mobile/offline hoặc external integration behavior; việc loại khỏi current slice không giải quyết câu hỏi toàn cục. |
| OQ-023 | Yêu cầu bổ sung nào chứng minh các User Story còn lại cần có để đạt mục tiêu 8–12 và ai sẽ sở hữu chúng? | Mục tiêu backlog |
| OQ-024 | Functional Prototype bắt buộc làm trong Figma hay có thể dùng công cụ prototype khác bên cạnh bằng chứng Figma/Design System bắt buộc? | Kế hoạch prototype |
| OQ-025 | URL dự án Taiga, URL dự án Figma, quyền truy cập và người phụ trách công cụ là gì? | Traceability với công cụ bên ngoài |
| OQ-026 | Ngôn ngữ canonical/báo cáo là tiếng Việt, English hay song ngữ? | Tính nhất quán tài liệu |

## AI và nền tảng kỹ thuật

| ID | Câu hỏi mở | Hạng mục bị chặn |
|---|---|---|
| OQ-027 | Inventory Q&A được phép sử dụng nguồn dữ liệu nào? | Phạm vi AI |
| OQ-028 | Inventory anomaly được định nghĩa và chứng minh bằng bằng chứng như thế nào? | Explain inventory anomalies |
| OQ-029 | Reorder recommendation chỉ mang tính tư vấn hay có thể khởi tạo hành động Purchasing? | Phạm vi và độ an toàn của reorder |
| OQ-030 | Có dữ liệu mẫu hoặc dữ liệu lịch sử nào cho các hướng AI? | Tính khả thi/đánh giá AI |
| OQ-031 | Tiêu chí groundedness, accuracy, explainability và safe fallback nào áp dụng cho output AI? | Acceptance Criteria cho AI |
| OQ-032 | Con người sẽ phê duyệt hướng frontend, backend, database, authentication, architecture và deployment nào? | `PARTIALLY RESOLVED / OPEN`: stack và modular-monolith architecture được approve tại `DEC-020`; PostgreSQL-backed session auth tại `DEC-031/033`; Vercel frontend → Render FastAPI → Supabase PostgreSQL 17 staging/demo topology và PostgreSQL 17+ compatibility tại `DEC-034/035`. Deployment chưa thực hiện và long-term production target vẫn `TBD`. |
| OQ-033 | Non-functional requirement nào bắt buộc cho Report Round 1 hoặc sản phẩm cuối? | `PARTIALLY DECIDED / OPEN`: `DEC-025` approve `NFR-001` đến `NFR-005`, `DEC-026` approve priority, còn `DEC-032/034/035` xác định minimum staging/demo release environment, PostgreSQL compatibility và release verification boundaries. Response-time, uptime, concurrent-user/load target, quantitative usability threshold, Putaway idempotency retention window và long-term production operating/deployment context vẫn chưa được quyết định. |

Khi câu trả lời được phê duyệt, phải dẫn nguồn, cập nhật artifact canonical bị ảnh hưởng và ghi quyết định khi phù hợp. Không âm thầm xóa câu hỏi lịch sử.

## Human decision status cho Domain và Workflow MVP

- `OQ-010` — `RESOLVED — HUMAN PRODUCT DECISION`: MVP quản lý một Warehouse duy nhất. Quyết định này giới hạn product scope và không phải kết luận từ research.
- `OQ-011` — `RESOLVED — HUMAN PRODUCT DECISION`: dùng `system stock quantity` theo internal location; Warehouse total bằng tổng location quantities; workflow effects được chốt tại `DEC-010` đến `DEC-015`; không canonicalize `on-hand`, `available`, `reserved`, `damaged` hoặc `in-transit`.
- `OQ-016` — `RESOLVED — HUMAN PRODUCT DECISION`: Transfer trong MVP chỉ là subsequent relocation giữa tracked internal locations trong cùng một Warehouse. Resolution này không xác nhận system Transfer transaction, Movement system record, Stock effect hoặc automatic location update.
- Location cardinality không có canonical OQ ID. `DEC-006` xác nhận như product modeling rằng một SKU có thể liên kết với nhiều internal locations trong cùng Warehouse; không tạo OQ ID mới.
- `OQ-013` — `PARTIALLY DECIDED / OPEN`: Round 2 và `DEC-036–040` đã xác định nhiều trigger, precondition, action và outcome, gồm `RECEIVE_RECORDED`, Pick result, immutable Transfer confirmation/safe replay, read-only confirmed Transfer history và Audit `MATCH_COMPLETED`/`MISMATCH_RECORDED` recording semantics. Final Receive completion/handoff, broader Transfer lifecycle, Audit Manager review/recheck/correction và các lifecycle gap còn lại được ghi tại bảng OQ và `workflow-overview.md`; không được suy diễn.

## Human decision status sau Round 2

- `OQ-017` — `RESOLVED — HUMAN PRODUCT DECISION` bởi `DEC-014`, `DEC-015`.
- `OQ-018` — `RESOLVED — HUMAN PRODUCT DECISION` bởi `DEC-014`.
- `OQ-019` — `RESOLVED — HUMAN PRODUCT DECISION` bởi `DEC-016`, `DEC-017`.
- `OQ-020` — `RESOLVED — HUMAN PRODUCT DECISION` bởi `DEC-017`.
- `OQ-015` — `RESOLVED — HUMAN PRODUCT DECISION` bởi `DEC-019`; không cho phép quantity âm tại internal location.
- `OQ-014` vẫn `OPEN`; partial Receive và partial Transfer là `NOT IMPLEMENTED` trong current slices, không phải permanently out. `DEC-040` loại device/integration khỏi current Audit slice nhưng không đóng `OQ-022`; các OQ AI chưa có quyết định mới vẫn `OPEN QUESTION`.
- Các quyết định Round 2 là HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS, không phải verified research findings và không tạo `EVD-*` mới.

## Research Synthesis v1 — trạng thái được thông tin một phần

Evidence P1/P2/P3 trong [`../01-sources/research-evidence.md`](../01-sources/research-evidence.md) chỉ mô tả vận hành hiện tại tại một minimart. Tại thời điểm Research Synthesis v1, evidence này không tự đóng các OQ dưới đây. Các HUMAN PRODUCT DECISIONS về sau được ghi riêng; `DEC-007` resolve `OQ-016`, và `DEC-010` đến `DEC-017` resolve hoặc thu hẹp các OQ Round 2 mà không biến quyết định thành research finding. Bảng dưới đây bảo tồn trạng thái lịch sử của Research Synthesis v1.

| ID | Evidence đã thông tin | Nội dung vẫn `OPEN QUESTION` |
|---|---|---|
| OQ-009 | Có evidence từ ba participant tại một minimart (`EVD-018`, `EVD-019`). | Khả năng tiếp cận stakeholder/participant bổ sung và usability testing vẫn chưa rõ. |
| OQ-013 | Có mô tả cấp cao từ research (`EVD-002` đến `EVD-017`), boundary Putaway/Transfer/Pick từ `DEC-009`, `RECEIVE_RECORDED`/reference-review eligibility từ `DEC-036`, current Pick confirmation lifecycle từ `DEC-037`, immutable Transfer confirmation/safe retry boundary từ `DEC-038`, read-only confirmed history contract từ `DEC-039` và Audit recording contract từ `DEC-040`. | Final Receive completion/exact Putaway handoff, future Pick retry/idempotency/correction/reversal/Manager review, broader Transfer failure/cancel/future reversal, Audit Manager review/recheck/correction và các lifecycle gap khác vẫn chưa rõ; câu hỏi tiếp tục `PARTIALLY DECIDED / OPEN`. |
| OQ-016 | Có physical movement giữa backroom và sales shelf (`EVD-010`). HUMAN PRODUCT DECISION `DEC-007` đã giới hạn Transfer trong MVP là subsequent relocation giữa tracked internal locations trong cùng một Warehouse. | System Transfer transaction, Movement system record, Stock effect và automatic location update chưa được xác nhận; chúng không phải nội dung được resolution của `OQ-016` tự động quyết định. |
| OQ-017 | Có re-check chênh lệch và manager involvement trong vận hành hiện tại (`EVD-012`, `EVD-013`, `EVD-017`). | Lý do, evidence, approval và authority bắt buộc vẫn chưa rõ. |
| OQ-018 | Có inventory checking hằng ngày, gồm đếm và đối chiếu (`EVD-015`, `EVD-016`). | Audit là cycle count, full stocktake hay cả hai vẫn chưa rõ. |
| OQ-020 | Staff hiện report/escalate chênh lệch cho manager (`EVD-013`). | Quyền chính thức của Warehouse Staff, Manager, Purchasing và Admin vẫn chưa rõ. |
| OQ-028 | Có chênh lệch actual-vs-system trong vận hành hiện tại (`EVD-012`, `EVD-017`). | Định nghĩa anomaly, nguyên nhân, tần suất và cách chứng minh vẫn chưa rõ. |
