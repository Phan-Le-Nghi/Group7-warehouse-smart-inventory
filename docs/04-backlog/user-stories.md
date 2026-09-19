# User Story và Acceptance Criteria — Canonical Backlog

## Trạng thái

Final backlog có **9 canonical User Stories**, nằm trong mục tiêu môn học 8–12 stories. Backlog được human approve sau Round 2.

- Receive reference mismatch là AC/scenario trong `US-REC-001`.
- `PARTIAL / INSUFFICIENT` Pick là AC/scenario trong `US-PICK-001`.
- Transfer, Audit và Adjust được tách theo actor/value.
- `OQ-013` vẫn `PARTIALLY DECIDED / OPEN`; các lifecycle gap không được suy diễn.

Canonical source cho từng story nằm tại [`../../vault/04-product/stories/`](../../vault/04-product/stories/).

Product Definition baseline: [PRD](../03-product/PRD.md), [MVP Scope](../03-product/mvp-scope.md) và [Consolidated User Flow](../03-product/user-flow.md).

## Canonical backlog và ownership

| Story ID | Title | Actor | Owner | Taiga ref | Taiga status | Source classification |
|---|---|---|---|---|---|---|
| `US-REC-001` | Ghi nhận Receive theo số lượng thực nhận | Warehouse Staff | Nguyễn Thị Nghĩa | [#7](https://tree.taiga.io/project/lenghi-group-07-project/us/7) / ID `9523822` | Ready | Verified evidence + HUMAN PRODUCT DECISION |
| `US-PUT-001` | Phân bổ Putaway vào initial location | Warehouse Staff | Phan Lê Nghi | [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) / ID `9523823` | Done — repository-recorded, not live-verified in this reconciliation | HUMAN PRODUCT DECISION |
| `US-PICK-001` | Thực hiện Pick từ tracked locations | Warehouse Staff | Trương Huỳnh Thảo Ngân | [#9](https://tree.taiga.io/project/lenghi-group-07-project/us/9) / ID `9523824` | Ready | HUMAN PRODUCT DECISION |
| `US-TRF-001` | Xác nhận Internal Transfer | Warehouse Staff | Nguyễn Thị Ly Na | [#10](https://tree.taiga.io/project/lenghi-group-07-project/us/10) / ID `9523825` | New | HUMAN PRODUCT DECISION |
| `US-TRF-002` | Xem Transfer history | Manager | Nguyễn Thị Ly Na | [#11](https://tree.taiga.io/project/lenghi-group-07-project/us/11) / ID `9523826` | New | HUMAN PRODUCT DECISION |
| `US-AUD-001` | Thực hiện selected-scope Audit | Warehouse Staff | Phan Lê Nghi | [#12](https://tree.taiga.io/project/lenghi-group-07-project/us/12) / ID `9523827` | Ready | Verified evidence + HUMAN PRODUCT DECISION |
| `US-AUD-002` | Review và re-check Audit discrepancy | Manager | Phan Lê Nghi | [#13](https://tree.taiga.io/project/lenghi-group-07-project/us/13) / ID `9523828` | Ready | Verified evidence + HUMAN PRODUCT DECISION |
| `US-ADJ-001` | Tạo Adjust request | Warehouse Staff | Đặng Thị Thanh Ngân | [#14](https://tree.taiga.io/project/lenghi-group-07-project/us/14) / ID `9523829` | Ready | Verified evidence + HUMAN PRODUCT DECISION |
| `US-ADJ-002` | Quyết định và apply Adjust | Manager | Đặng Thị Thanh Ngân | [#15](https://tree.taiga.io/project/lenghi-group-07-project/us/15) / ID `9523830` | Ready | Verified evidence + HUMAN PRODUCT DECISION |

## US-REC-001 — Ghi nhận Receive theo số lượng thực nhận

> Là Warehouse Staff, tôi muốn kiểm tra item, ghi nhận actual quantity và đối chiếu với expected quantity/reference, để Receive phản ánh hàng thực tế và các mismatch được nhận biết trước khi completion được cân nhắc.

- Given Receive context có item và expected quantity, when Warehouse Staff nhập actual quantity, then system ghi actual quantity và compare với expected quantity.
- Given actual quantity bằng expected quantity, when Receive được ghi nhận, then Receive quantity bằng actual quantity.
- Given actual quantity khác expected quantity, when Receive được ghi nhận, then Receive quantity vẫn bằng actual quantity và discrepancy được ghi nhận.
- Given system reference khác document reference, when Receive được xử lý, then mismatch phải được user review trước completion và system không tự chọn authoritative reference.

Trace: `CAND-REQ-001/002/009/010`, `CAND-BR-001/014`, `EVD-002–005`, `DEC-016/017`, `OQ-013/014/022`.

## US-PUT-001 — Phân bổ Putaway vào initial location

> Là Warehouse Staff, tôi muốn xác nhận SKU, quantity và destination internal location cho initial placement sau Receive, để quantity được phân bổ vào `Backroom` hoặc `Sales Shelf`.

- Given SKU và quantity cần initial placement sau Receive, when Warehouse Staff confirm destination là `Backroom` hoặc `Sales Shelf`, then quantity được phân bổ vào destination đã confirm.
- Given một MVP Putaway destination được chọn, when Putaway được confirm, then destination được ghi nhận ở mức tracked internal location `Backroom` hoặc `Sales Shelf`.
- Given Putaway được confirm, when quantity được phân bổ, then Putaway không tự tạo Transfer hoặc Movement system record.

Trace: `CAND-REQ-003/007/010`, `CAND-BR-003/004`, `DEC-006/010/011/017`, `OQ-013/014/022`.

## US-PICK-001 — Thực hiện Pick từ tracked locations

> Là Warehouse Staff, tôi muốn thực hiện Pick từ một Pick request bằng một hoặc nhiều tracked internal locations, để cung cấp confirmed quantity cho downstream use và ghi nhận trung thực trường hợp không đủ.

- Given Pick request có SKU/requested quantity, when Warehouse Staff confirm full requested quantity từ một hoặc nhiều source locations, then Pick là fully completed và confirmed quantity được giảm tại các source tương ứng.
- Given một location không đủ nhưng location khác có quantity cho cùng SKU, when Pick được thực hiện, then requested quantity có thể được lấy từ nhiều tracked internal locations.
- Given tổng quantity được lấy nhỏ hơn requested quantity, when result được ghi nhận, then Pick là `PARTIAL / INSUFFICIENT` và không fully completed.
- Given confirmed quantity lớn hơn tổng `system stock quantity` tại các selected source locations, when Warehouse Staff cố confirm Pick, then Pick không được confirm, quantity change không được apply và operation được báo không hợp lệ/không thể confirm.

Trace: `CAND-REQ-003/006/010/011`, `CAND-BR-003/005/006/015`, `DEC-010/012/017/019`, `OQ-013/022`.

## US-TRF-001 — Xác nhận Internal Transfer

> Là Warehouse Staff, tôi muốn xác nhận Internal Transfer giữa tracked internal locations, để source và destination quantities được cập nhật nhất quán mà không đổi Warehouse total.

- Given SKU, quantity, source và destination tracked locations trong cùng Warehouse, when Warehouse Staff confirm Transfer, then source giảm Transfer quantity và destination tăng cùng quantity.
- Given Internal Transfer được confirm, when quantity effects được ghi nhận, then Warehouse total quantity không thay đổi.
- Given Transfer được confirm, when system record được tạo, then record chứa SKU, quantity, source, destination và confirmation timestamp.
- Given Transfer quantity lớn hơn `system stock quantity` tại source location, when Warehouse Staff cố confirm Transfer, then Transfer không được confirm, quantity change không được apply và operation được báo không hợp lệ/không thể confirm.

Trace: `CAND-REQ-003/010/011`, `FR-012`, `CAND-BR-003/007/008/015`, `DEC-005/007/009/010/013/017/019/024`, `OQ-013/014/022`. Historical `CAND-REQ-004` was `SUPERSEDED / DECOMPOSED` by `FR-012` and `FR-013` and is not an active trace target.

## US-TRF-002 — Xem Transfer history

> Là Manager, tôi muốn xem Transfer history, để trace relocation và hỗ trợ discrepancy investigation.

- Given confirmed Transfer records tồn tại, when Manager mở Transfer history, then Manager có thể xem history.
- Given một confirmed Transfer xuất hiện trong history, when Manager xem record, then source, destination, quantity và time được hiển thị.
- Given một Transfer có confirmation timestamp, when record được xem trong history, then displayed time phản ánh confirmation time của record.

Trace: `FR-013`, `CAND-REQ-010`, `CAND-BR-008`, `DEC-013/017/024`, `OQ-013/022`. Historical `CAND-REQ-004` was `SUPERSEDED / DECOMPOSED` by `FR-012` and `FR-013` and is not an active trace target.

## US-AUD-001 — Thực hiện selected-scope Audit

> Là Warehouse Staff, tôi muốn thực hiện selected-scope Audit và so sánh physical count với `system stock quantity`, để ghi nhận kết quả match hoặc mismatch.

- Given Audit session được bắt đầu, when Warehouse Staff chọn scope, then scope là nhóm SKU/location hoặc toàn Warehouse.
- Given selected scope, when Warehouse Staff ghi physical count, then count được compare với `system stock quantity` tại scope/location tương ứng.
- Given comparison đã thực hiện, when result được ghi nhận, then Audit lưu kết quả match hoặc mismatch.
- Given result là match, when result được confirm, then Audit có thể complete.

Trace: `CAND-REQ-003/005/010`, `CAND-BR-003/009`, `EVD-015/016`, `DEC-010/014/017`, `OQ-013/022`.

## US-AUD-002 — Review và re-check Audit discrepancy

> Là Manager, tôi muốn review Audit discrepancy và bảo đảm discrepancy được re-check, để Adjust không được áp dụng tự động từ một mismatch chưa kiểm tra lại.

- Given Audit result là mismatch, when result được ghi nhận, then discrepancy/review context được tạo.
- Given discrepancy/review context tồn tại, when discrepancy được xử lý tiếp, then re-check là bắt buộc trước khi Adjust được cân nhắc.
- Given Audit mismatch được ghi nhận, when Audit result được xử lý, then Audit không tự động apply Adjust.

Trace: `CAND-REQ-005/010`, `CAND-BR-002/010`, `EVD-012/017`, `DEC-014/017`, `OQ-013`.

## US-ADJ-001 — Tạo Adjust request

> Là Warehouse Staff, tôi muốn tạo Adjust request cho discrepancy đã re-check và ghi reason, để Manager có đủ context quyết định trước khi quantity thay đổi.

- Given discrepancy tại affected SKU/location đã được re-check và vẫn còn, when Warehouse Staff tạo Adjust request, then Adjust reason được ghi nhận.
- Given discrepancy chưa được re-check, when Adjust được cân nhắc, then điều kiện bắt buộc về re-check chưa được đáp ứng.
- Given re-check và reason đã có nhưng không có attachment, when request được tạo, then attachment không phải điều kiện bắt buộc trong MVP.
- Given Adjust request đang chờ Manager decision, when request được ghi nhận, then `system stock quantity` chưa được thay đổi bởi Adjust đó.

Trace: `CAND-REQ-008/010`, `CAND-BR-002/011/012`, `EVD-012/013/017`, `DEC-015/017`, `OQ-013/015`.

## US-ADJ-002 — Quyết định và apply Adjust

> Là Manager, tôi muốn approve hoặc reject Adjust request, để chỉ approved Adjust mới cập nhật `system stock quantity` tại affected location.

- Given discrepancy đã re-check, reason đã ghi và Manager approves request, when Adjust được apply, then `system stock quantity` tại affected internal location được cập nhật.
- Given Manager rejects request, when rejection được ghi nhận, then `system stock quantity` không thay đổi.
- Given re-check không còn discrepancy, when case được xử lý, then Adjust không được apply và quantity không thay đổi.
- Given một approved Adjust sẽ làm `system stock quantity` tại affected internal location nhỏ hơn 0, when Adjust được cân nhắc apply, then Adjust không được apply, quantity không thay đổi và operation được báo không hợp lệ/không thể confirm.

Trace: `CAND-REQ-003/008/010/011`, `CAND-BR-002/011/013/015`, `EVD-012/013/017`, `DEC-010/015/017/019`, `OQ-013`.

## Preserved open boundaries

- `OQ-013` remains `PARTIALLY DECIDED / OPEN`.
- `OQ-015` is `RESOLVED — HUMAN PRODUCT DECISION` by `DEC-019`; `OQ-014` and `OQ-022` remain open.
- Không có AC về Receive final completion, automatic Putaway handoff, Putaway exception, Transfer failure/cancel/reversal, Audit mismatch closure, Adjust rejected-case closure hoặc retry/cancel sau failed negative-stock validation.
- Không có barcode, mobile/offline, FIFO/FEFO, reservation, multi-Warehouse hoặc Purchase Order lifecycle behavior.
