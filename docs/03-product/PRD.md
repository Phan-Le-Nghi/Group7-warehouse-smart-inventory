# Product Requirements Document — Warehouse & Smart Inventory Management

## 1. Document status and authority

| Field | Value |
|---|---|
| Status | BASELINE FOR REPORT ROUND 1 — HUMAN APPROVED PRODUCT DEFINITION |
| Scope | MVP product definition; không phải technical design |
| Canonical authority | Project Vault |
| Backlog baseline | 9 canonical User Stories — HUMAN APPROVED |
| Open-boundary policy | Nội dung `TBD` / `OPEN QUESTION` không phải approved behavior |

Tài liệu này trình bày Product Definition phục vụ báo cáo và phải trace về artifact canonical trong Vault. Khi có khác biệt, Vault và human decision mới nhất có thẩm quyền. Tài liệu không định nghĩa ERD, API, architecture, technology stack hoặc implementation.

## 2. Product overview

Warehouse & Smart Inventory Management hỗ trợ kiểm soát Receive, Putaway, Pick, Internal Transfer, Audit và Adjust trong một Warehouse. MVP duy trì `system stock quantity` của SKU theo hai tracked internal locations: `Backroom` và `Sales Shelf`. Warehouse total quantity của một SKU bằng tổng quantity tại các internal locations.

Sáu workflow tại `REQ-002` là danh sách capability bắt buộc, không phải một transaction tuần tự bắt buộc. Receive có thể dẫn tới Putaway; Pick và Transfer là các operational path độc lập; Audit có thể chạy theo selected scope. Audit mismatch chỉ dẫn tới việc cân nhắc Adjust sau discrepancy context và mandatory re-check (`DEC-018`).

## 3. Problem statement

Sản phẩm cần hỗ trợ kiểm soát nhập, xuất, chuyển kho và tồn kho; ghi nhận quantity theo hoạt động thực tế; và hỗ trợ phát hiện, kiểm tra, phê duyệt discrepancy trước khi quantity được điều chỉnh (`REQ-001`).

MVP tập trung vào các vấn đề đã được phê duyệt:

- Receive cần ghi actual quantity và đối chiếu expected quantity/reference.
- Stock cần được duy trì và tra cứu theo internal location.
- Pick có thể lấy từ nhiều locations và phải phản ánh trung thực trường hợp thiếu.
- Internal Transfer cần cập nhật nhất quán source/destination và có history.
- Audit cần so sánh physical count với system quantity theo selected scope.
- Adjust cần re-check, reason và Manager approval.
- Pick, Transfer và Adjust không được làm quantity tại internal location trở thành số âm.

## 4. Target users / roles

| Role | Approved MVP participation |
|---|---|
| Warehouse Staff | Perform Receive, Putaway, Pick, Transfer và Audit count; create discrepancy/Adjust request |
| Manager | View operational records; review exceptions/discrepancy; approve/reject Adjust; view Transfer history; confirm/close sensitive exception flows trong phạm vi behavior đã duyệt |
| Purchasing | Supporting role của Receive: provide/view expected quantity/reference; không có warehouse adjustment permission |
| Admin | Manage users, role assignments và basic system configuration; không bắt buộc tham gia daily warehouse operations |

Không suy diễn thêm create/edit/delete/override permission. Purchasing và Admin không cần standalone operational story trong canonical 9-story backlog (`DEC-017`).

## 5. Product goals

- Hỗ trợ đủ sáu workflow bắt buộc tại `REQ-002`.
- Duy trì `system stock quantity` theo tracked internal location và Warehouse total nhất quán.
- Ghi nhận actual-versus-expected discrepancy trong Receive.
- Hỗ trợ full, multi-location và `PARTIAL / INSUFFICIENT` Pick.
- Ghi confirmed Internal Transfer record và cung cấp history để trace relocation.
- Ghi Audit match/mismatch theo selected scope.
- Ngăn Audit tự động apply Adjust.
- Chỉ apply Adjust sau re-check, required reason và Manager approval.
- Không cho phép Pick, Transfer hoặc Adjust tạo negative location quantity.
- Áp dụng permission description cho bốn role đã duyệt.

## 6. Non-goals

- Multi-Warehouse hoặc cross-Warehouse operation (`DEC-005`, `DEC-007`).
- Aisle, rack, bin hoặc detailed shelf (`DEC-006`).
- Full Purchase Order lifecycle (`DEC-016`).
- Downstream fulfilment/use sau Pick (`DEC-012`).
- FIFO, FEFO hoặc reservation trong Pick MVP hiện tại (`DEC-012`).
- Pick scanning trong MVP hiện tại (`DEC-012`).
- Canonical stock buckets `on-hand`, `available`, `reserved`, `damaged` hoặc `in-transit` (`DEC-008`, `DEC-010`).
- Automatic Adjust từ Audit mismatch (`DEC-014`).
- Automatic Transfer hoặc Movement system record từ Putaway (`DEC-011`).
- Alert story hoặc AI story trong canonical 9-story backlog hiện tại.

Barcode/QR ngoài Pick, general scanner, mobile/offline và external integration không được tuyên bố out of scope chung vì `OQ-022` vẫn mở.

## 7. MVP boundaries

- Một Warehouse với `Backroom` và `Sales Shelf` ở mức area.
- Một SKU có thể có quantity tại nhiều internal locations.
- Warehouse total bằng tổng location quantities.
- Location quantity không được âm.
- Putaway là initial placement sau Receive.
- Pick và Transfer là các operational path độc lập, không phải chuỗi bắt buộc.
- Transfer chỉ là subsequent relocation nội bộ cùng Warehouse.
- Audit dùng selected scope: nhóm SKU/location hoặc toàn Warehouse.
- Adjust là action riêng sau discrepancy và re-check; Audit không auto Adjust.
- Expected quantity/reference của Receive đến từ external/manual reference do Purchasing cung cấp hoặc chuẩn bị.

Chi tiết phân loại nằm tại [MVP Scope](mvp-scope.md).

## 8. MVP scope

MVP gồm sáu workflow, quantity model theo location, approved exception branches, four-role permission description và negative-stock guard. Multi-Warehouse, detailed locations, full Purchase Order lifecycle, Pick downstream fulfilment, FIFO/FEFO/reservation và Pick scanning nằm ngoài MVP. Alert, AI directions, lifecycle gaps và device/integration behavior vẫn OPEN hoặc future direction; không được biến thành approved behavior.

## 9. Core workflows

### Receive

Purchasing provide/view external/manual expected quantity/reference. Warehouse Staff kiểm item, ghi actual quantity và compare với expected quantity. Quantity discrepancy phải ghi actual quantity và discrepancy. Nếu system reference khác document reference, user phải review mismatch và system không tự chọn authoritative source. Final completion và exact Putaway handoff vẫn `OQ-013`.

### Putaway

Warehouse Staff xác nhận SKU, quantity và initial destination là `Backroom` hoặc `Sales Shelf`. Confirmed Putaway phân bổ quantity vào destination và không tự tạo Transfer/Movement system record. Exception/downstream handoff và partial Putaway vẫn mở.

### Pick

Warehouse Staff thực hiện Pick request có SKU/requested quantity từ một hoặc nhiều selected source locations. Full requested quantity mới fully completed; thiếu được ghi `PARTIAL / INSUFFICIENT`. Pick không được confirm vượt tổng quantity tại selected sources; failed validation không apply quantity change. Retry/cancel lifecycle không được suy diễn.

### Transfer

Warehouse Staff xác nhận subsequent relocation giữa tracked locations trong cùng Warehouse. Confirmed Transfer giảm source, tăng cùng quantity tại destination, không đổi Warehouse total và tạo minimum system record. Manager có thể xem confirmed history. Transfer không được confirm vượt source quantity; failed validation không apply quantity change. Partial, failure/cancel/reversal lifecycle vẫn mở.

### Audit

Warehouse Staff chọn scope, ghi physical count, compare với `system stock quantity` và record match/mismatch. Match có thể complete sau confirmation. Mismatch tạo discrepancy/review context, bắt buộc re-check và không auto Adjust. Audit mismatch completion và schedule vẫn mở.

### Adjust

Nếu discrepancy vẫn còn sau re-check, Warehouse Staff có thể tạo Adjust request với required reason; attachment/evidence optional. Manager approve hoặc reject trước apply. Approved Adjust cập nhật affected location quantity nếu kết quả không âm. Reject, no-discrepancy-after-re-check hoặc failed negative-stock validation không thay đổi quantity. Rejected-case final closure vẫn mở.

Consolidated detail nằm tại [User Flow](user-flow.md).

## 10. Functional requirements

Active canonical FR count là **12**. `CAND-REQ-004` đã được decomposed thành `FR-012` và `FR-013` tại `DEC-024`, được giữ như lịch sử `SUPERSEDED / DECOMPOSED` và không được double-count. Các active `CAND-REQ-*` là approved canonical requirements dù giữ tiền tố lịch sử.

| ID | Approved requirement | Priority |
|---|---|---|
| `CAND-REQ-001` | Ghi actual quantity và compare với expected quantity trong Receive | MUST |
| `CAND-REQ-002` | Ghi quantity discrepancy để phục vụ xử lý tiếp theo | MUST |
| `CAND-REQ-003` | Duy trì/tra cứu quantity theo `Backroom` và `Sales Shelf`; Warehouse total bằng tổng location quantities | MUST |
| `CAND-REQ-005` | Selected-scope Audit: scope, count, compare và result | MUST |
| `CAND-REQ-006` | Multi-location Pick; full và `PARTIAL / INSUFFICIENT` result | MUST |
| `CAND-REQ-007` | Initial Putaway allocation vào tracked destination | MUST |
| `CAND-REQ-008` | Adjust request và Manager approve/reject trước quantity change | MUST |
| `CAND-REQ-009` | External/manual expected quantity/reference do Purchasing cung cấp/chuẩn bị | MUST |
| `CAND-REQ-010` | Four-role permission model | MUST |
| `CAND-REQ-011` | Ngăn Pick/Transfer/Adjust confirm hoặc apply nếu operation tạo negative location quantity | MUST |
| `FR-012` | Warehouse Staff confirm Internal Transfer và tạo minimum record | MUST |
| `FR-013` | Manager tra cứu confirmed Transfer history với minimum displayed fields | MUST |

### 10.1 Non-functional requirements

Canonical NFR count là **5**. Approval và priority được ghi tại `DEC-025/026`.

| ID | Approved NFR | Verification boundary | Priority |
|---|---|---|---|
| `NFR-001` | Stock-changing operation commit toàn bộ hoặc rollback toàn bộ khi thất bại | Không tồn tại partial write trên tested failure path | MUST |
| `NFR-002` | Conflicting concurrent stock commands giữ per-location consistency và negative-stock invariant | Concurrency test chứng minh invariant; không có load target | MUST |
| `NFR-003` | Same-key/same-payload Putaway replay không tạo allocation hoặc stock increment lần hai | `TEST-PUT-003`/equivalent; Putaway Round 1 only; retention window TBD | SHOULD |
| `NFR-004` | Protected operations enforce approved permission outcome qua actor/auth boundary | Authorization behavior and approved `401`/`403` outcomes testable; PostgreSQL-backed session design approved at `DEC-031`, implementation pending | MUST |
| `NFR-005` | UI phân biệt rõ Pick `PARTIAL / INSUFFICIENT` với completed | UI/state/copy review và P2 usability evidence; không có numeric threshold | SHOULD |

## 11. Business rules

| ID | Approved rule summary |
|---|---|
| `CAND-BR-001` | Receive sử dụng actual quantity khi actual khác expected |
| `CAND-BR-002` | Discrepancy phải được re-check trước Adjust |
| `CAND-BR-003` | Quantity duy trì theo location; Warehouse total là tổng location quantities |
| `CAND-BR-004` | Putaway phân bổ destination quantity; không tự tạo Transfer/Movement record |
| `CAND-BR-005` | Confirmed Pick giảm source quantity/quantities |
| `CAND-BR-006` | Chỉ full Pick mới fully completed; thiếu là `PARTIAL / INSUFFICIENT` |
| `CAND-BR-007` | Confirmed Transfer giảm source, tăng destination, không đổi Warehouse total |
| `CAND-BR-008` | Confirmed Transfer lưu minimum system record |
| `CAND-BR-009` | Audit compare physical count với system quantity và record result |
| `CAND-BR-010` | Audit mismatch không auto Adjust; phải re-check/review riêng |
| `CAND-BR-011` | Adjust chỉ apply sau re-check, reason và Manager approval |
| `CAND-BR-012` | Adjust attachment/evidence optional |
| `CAND-BR-013` | Approved Adjust cập nhật affected location; reject/no discrepancy không đổi quantity |
| `CAND-BR-014` | Reference mismatch cần user review; system không tự chọn authoritative source |
| `CAND-BR-015` | Location quantity không được âm; failed Pick/Transfer/Adjust validation không apply quantity change |

Canonical wording nằm tại `vault/02-requirements/business-rules.md`. Cả 15 active Business Rules có priority `MUST` theo `DEC-026`.

## 12. Canonical 9 User Stories

| Story | Scope |
|---|---|
| `US-REC-001` | Receive actual quantity, quantity discrepancy, reference mismatch review |
| `US-PUT-001` | Initial location Putaway |
| `US-PICK-001` | Full/multi-location/insufficient Pick và negative-stock guard |
| `US-TRF-001` | Internal Transfer confirmation, record và negative-stock guard |
| `US-TRF-002` | Confirmed Transfer history |
| `US-AUD-001` | Selected-scope Audit and match completion |
| `US-AUD-002` | Audit discrepancy review, re-check, no-auto-Adjust |
| `US-ADJ-001` | Adjust request, reason, re-check, optional attachment |
| `US-ADJ-002` | Manager decision, apply/no-change branches và negative-stock guard |

Canonical story và Acceptance Criteria nằm tại `vault/04-product/stories/`. Không có Alert, AI, Admin operational hoặc standalone Purchasing story trong baseline này.

## 13. Permissions

| Capability | Warehouse Staff | Manager | Purchasing | Admin |
|---|---|---|---|---|
| Receive | Perform | View/review exception trong phạm vi đã duyệt | Provide/view expected reference | Không bắt buộc daily operation |
| Putaway | Perform | View operational records | — | Không bắt buộc daily operation |
| Pick | Perform | May review insufficient exception | — | Không bắt buộc daily operation |
| Transfer | Perform/confirm | View history; review exception | — | Không bắt buộc daily operation |
| Audit | Perform count | Review discrepancy/re-check | — | Không bắt buộc daily operation |
| Adjust | Create request | Approve/reject | No adjustment permission | Không có operational behavior được suy diễn |
| Administration | Không được suy diễn | Không được suy diễn | Không được suy diễn | Manage users, role assignments, basic system configuration |

`—` nghĩa là không có approved permission trong baseline, không phải một explicit deny rule ngoài wording tại `DEC-017`.

## 14. Exceptions / limitations

Approved exceptions/guards:

- Receive quantity discrepancy ghi actual quantity và discrepancy.
- Receive reference mismatch bắt buộc human review.
- Pick thiếu quantity là `PARTIAL / INSUFFICIENT`, không fully completed.
- Pick/Transfer/Adjust không được tạo negative location quantity.
- Audit mismatch tạo discrepancy context, bắt buộc re-check, không auto Adjust.
- Adjust reject hoặc no discrepancy after re-check không đổi quantity.

Limitations và chưa quyết định:

- Không định nghĩa Receive final completion, automatic Putaway handoff hoặc general Receive exceptions.
- Không định nghĩa Putaway exceptions/downstream handoff.
- Không định nghĩa partial Receive/Putaway/Transfer.
- Không định nghĩa Pick cancellation/retry ngoài approved insufficient/validation branches.
- Không định nghĩa Transfer failure/cancel/reversal lifecycle.
- Không định nghĩa Audit mismatch completion/schedule.
- Không định nghĩa rejected Adjust final closure hoặc retry/cancel sau negative-stock validation.
- Không định nghĩa Alert trigger, recipient, threshold hoặc workflow.

## 15. Open Questions

Không block MVP feature-set baseline nếu được giữ rõ:

- `OQ-012`: lot/batch, serial, expiry, UOM/conversion.
- `OQ-013`: remaining trigger/completion/exception/handoff lifecycle gaps.
- `OQ-014`: partial Receive/Putaway/Transfer; Pick partial branch đã được quyết định riêng.
- `OQ-021`: Alert behavior.
- `OQ-022`: barcode/QR, general scanner, mobile/offline, external integration.
- `OQ-027–031`: AI data, anomaly definition, reorder authority, data availability và AI quality/safety criteria.
- `OQ-033`: `PARTIALLY DECIDED / OPEN`; năm NFR đã được approve, nhưng response-time, uptime, concurrent-user/load target, quantitative usability threshold, Putaway idempotency retention window và operating/deployment context vẫn mở.

`OQ-015` đã được resolve bởi `DEC-019`. AI directions `AI-DIR-001–003` là `OPEN / FUTURE DIRECTION / NOT YET CANONICAL MVP REQUIREMENT`.

Theo `DEC-026`, Alert functionality và `AI-DIR-001–003` có priority `OUT / DEFERRED` cho current MVP baseline. Priority này không đóng `OQ-021` hoặc `OQ-027–031`.

## 16. Success criteria

Report Round 1 dùng documentation-completeness criteria đã duyệt:

- Đủ 6 workflow.
- Đủ 9 canonical stories.
- Mọi story map vào flow.
- Approved branches có Acceptance Criteria.
- 4 roles có permission description.
- Requirement / Business Rule / Decision / Story / Flow trace được.
- Unresolved behavior ghi `TBD` / `OPEN QUESTION`.
- Không đưa out-of-scope behavior vào MVP.

Không có quantitative business KPI được phê duyệt trong baseline này.

## 17. Traceability summary

| Product area | Requirement | Business Rule | Decision | Story | Flow |
|---|---|---|---|---|---|
| Receive | `CAND-REQ-001/002/009/010` | `CAND-BR-001/014` | `DEC-016/017/018` | `US-REC-001` | Receive |
| Putaway | `CAND-REQ-003/007/010` | `CAND-BR-003/004` | `DEC-006/010/011/017/018` | `US-PUT-001` | Putaway |
| Pick | `CAND-REQ-003/006/010/011` | `CAND-BR-003/005/006/015` | `DEC-010/012/017/018/019` | `US-PICK-001` | Pick operational path |
| Transfer execution | `CAND-REQ-003/010/011`, `FR-012` | `CAND-BR-003/007/008/015` | `DEC-005/007/009/010/013/017/018/019/024` | `US-TRF-001` | Transfer confirmation/record |
| Transfer history | `FR-013`, `CAND-REQ-010` | `CAND-BR-008` | `DEC-013/017/024` | `US-TRF-002` | Confirmed history query |
| Audit | `CAND-REQ-003/005/010` | `CAND-BR-002/003/009/010` | `DEC-010/014/017/018` | `US-AUD-001/002` | Audit match/mismatch/re-check |
| Adjust | `CAND-REQ-003/008/010/011` | `CAND-BR-002/011/012/013/015` | `DEC-010/015/017/018/019` | `US-ADJ-001/002` | Request/decision/apply |
| Permissions | `CAND-REQ-010` | — | `DEC-017` | Supporting/actor coverage across stories | Role participation |
| Alert | `REQ-004`; no approved functional requirement | — | — | No story | `OPEN — OQ-021` |
| AI directions | No canonical MVP requirement | — | Human-approved future/open classification | No story | `OPEN — OQ-027–031` |

Chi tiết đầy đủ nằm tại [`../TRACEABILITY.md`](../TRACEABILITY.md).
