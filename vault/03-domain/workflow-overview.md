# Tổng quan quy trình

## Chuỗi đã xác nhận

`Receive -> Putaway -> Pick -> Transfer -> Adjust -> Audit`

Chuỗi này xác định các khu vực quy trình/capability bắt buộc, không phải một transaction tuần tự bắt buộc. Receive có thể dẫn tới Putaway; sau Putaway, Pick và Transfer là các operational path độc lập. Audit có thể được thực hiện trên inventory theo selected scope, không bắt buộc xảy ra sau Pick hoặc Transfer. Audit mismatch tạo discrepancy context và bắt buộc re-check; chỉ khi discrepancy vẫn còn thì Adjust mới có thể được cân nhắc. Audit không auto Adjust (`DEC-018`).

## Boundary được human phê duyệt cho MVP

- MVP quản lý một Warehouse duy nhất; multi-Warehouse và cross-Warehouse operation ngoài MVP (`DEC-005`).
- Internal location ở mức area-level gồm `Backroom` và `Sales Shelf`; một SKU có thể có `system stock quantity` tại nhiều internal locations. Warehouse total quantity bằng tổng location quantities (`DEC-006`, `DEC-010`).
- Putaway là initial placement sau Receive. Confirmed Putaway phân bổ quantity vào destination internal location và không tự tạo Transfer hoặc Movement system record (`DEC-011`).
- Pick bắt đầu từ Pick request có SKU/requested quantity. Warehouse Staff có thể lấy từ một hoặc nhiều internal locations; confirmed Pick giảm source quantity; chỉ full requested quantity mới fully completed (`DEC-012`).
- Transfer là subsequent relocation giữa tracked internal locations trong cùng Warehouse. Confirmed Transfer có system record, giảm source, tăng cùng quantity tại destination và không đổi Warehouse total (`DEC-007`, `DEC-013`).
- Audit dùng selected scope; match có thể complete sau confirmation; mismatch tạo discrepancy/review context, bắt buộc re-check và không auto Adjust (`DEC-014`).
- Adjust là action riêng do Warehouse Staff request và Manager approve/reject; approved Adjust cập nhật affected location quantity (`DEC-015`).
- Full Purchase Order lifecycle ngoài MVP; Receive dùng external/manual expected quantity/reference do Purchasing cung cấp/chuẩn bị (`DEC-016`).
- `system stock quantity` tại internal location không được âm. Pick, Transfer và Adjust không được confirm/apply nếu operation sẽ tạo quantity âm; không apply quantity change và operation được báo không hợp lệ/không thể confirm (`DEC-019`).

Các mục trên là HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS, không phải verified research findings.

## Supporting upstream work-item creation — `DEC-045`

- Purchasing có thể tạo minimum prepared Receive context gồm expected reference và
  một hoặc nhiều unique SKU/positive expected-quantity lines.
- Manager có thể tạo minimum single-SKU Pick Request với positive requested quantity.
- Cả hai actor được đọc minimum SKU catalog phục vụ form; catalog không expose stock.
- Creation resolve canonical single Warehouse ở backend, không nhận authoritative
  `warehouse_id`, không mutate/reserve stock và không tự execute downstream workflow.
- Đây là supporting capability/usability extension cho hai precondition hiện hữu,
  không phải canonical User Story mới. Tổng canonical story tiếp tục là 9.
- Không thêm creator/time, durable creation idempotency, Purchase Order/order/shipping,
  Pick retry/cancel/reopen hoặc Receive correction/reversal.

## Lifecycle đã quyết định một phần

### Receive — `US-REC-001` — Nguyễn Thị Nghĩa

- Trigger: Receive context khi hàng được giao để kiểm nhận; wording cuối vẫn thuộc `OQ-013`.
- Precondition/input: item, actual quantity và external/manual expected quantity từ order or delivery reference.
- Action: kiểm item, đếm actual quantity, compare và ghi nhận actual quantity/discrepancy theo `CAND-REQ-001`, `CAND-REQ-002`, `CAND-BR-001`.
- Exception: nếu system reference và document reference khác nhau, user phải review mismatch trước completion; system không tự chọn authoritative source (`CAND-BR-014`).
- Completion/handoff: wording cuối và exact handoff sang Putaway vẫn `PARTIALLY DECIDED / OPEN` tại `OQ-013`.

### Putaway — `US-PUT-001` — Phan Lê Nghi

- Trigger: initial placement sau Receive.
- Precondition/input: SKU, quantity, destination `Backroom` hoặc `Sales Shelf`.
- Action/outcome: Warehouse Staff confirm; quantity được phân bổ vào destination internal location.
- Completion: quantity và destination được confirm.
- Guard: không tự tạo Transfer hoặc Movement system record.
- Exception/downstream handoff: `TBD / OQ-013`; partial Putaway vẫn `OQ-014`.

### Pick — `US-PICK-001` — Trương Huỳnh Thảo Ngân

- Trigger: Pick request có SKU và requested quantity.
- Precondition/input: request và một hoặc nhiều tracked source internal locations.
- Action/outcome: Warehouse Staff lấy và confirm quantity; confirmed quantity giảm tại source location(s).
- Completion: chỉ full requested quantity mới fully completed.
- Exception: thiếu quantity được ghi `PARTIAL / INSUFFICIENT`, không fully complete; Manager có thể review.
- Guard: không confirm quantity lớn hơn tổng quantity tại các selected source locations; nếu vi phạm thì không apply quantity change và operation được báo không hợp lệ/không thể confirm.
- Handoff: downstream fulfilment/use; downstream module ngoài MVP.
- Guard: FIFO/FEFO/reservation/scanning ngoài MVP hiện tại.

### Transfer — `US-TRF-001`, `US-TRF-002` — Nguyễn Thị Ly Na

- Trigger: nhu cầu subsequent relocation giữa tracked internal locations trong cùng Warehouse.
- Precondition/input: SKU, quantity, source internal location, destination internal location.
- Action/outcome: Warehouse Staff thực hiện và confirm Transfer; source giảm, destination tăng cùng quantity, Warehouse total không đổi.
- System record: SKU, quantity, source, destination, confirmation timestamp; history/query hiển thị source, destination, quantity, time.
- Completion: system Transfer được confirm; exception vẫn `TBD / OQ-013`.
- Guard: không confirm Transfer quantity lớn hơn source location quantity; nếu vi phạm thì không apply quantity change và operation được báo không hợp lệ/không thể confirm.
- Handoff: history hỗ trợ trace và discrepancy investigation.

### Audit — `US-AUD-001`, `US-AUD-002` — Phan Lê Nghi

- Trigger/precondition: selected-scope Audit session được bắt đầu và scope được chọn.
- Input/action: scope là nhóm SKU/location hoặc toàn Warehouse; ghi physical count, compare với `system stock quantity`, record result.
- Match: có thể complete sau confirmation.
- Mismatch: tạo discrepancy/review context, bắt buộc re-check, không auto Adjust.
- Mismatch completion và schedule: `TBD / OQ-013`; không canonicalize `cycle count`.

### Adjust — `US-ADJ-001`, `US-ADJ-002` — Đặng Thị Thanh Ngân

- Trigger/input: Warehouse Staff tạo discrepancy/Adjust request cho affected SKU/location với Adjust reason; attachment/evidence optional.
- Precondition/action: re-check bắt buộc; Manager approve/reject trước apply.
- Approved outcome: cập nhật `system stock quantity` tại affected internal location.
- Guard: Adjust không được apply nếu kết quả làm affected-location quantity nhỏ hơn 0; không apply quantity change và operation được báo không hợp lệ/không thể confirm.
- Re-check không còn discrepancy: không Adjust; case có thể close.
- Manager reject: quantity không thay đổi; rejected-case closure vẫn `TBD / OQ-013`.

`OQ-013` giữ trạng thái `PARTIALLY DECIDED / OPEN`. Không suy diễn exception, partial behavior, handoff hoặc completion chưa được ghi ở trên.
