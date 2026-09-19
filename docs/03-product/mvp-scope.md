# MVP Scope — Warehouse & Smart Inventory Management

## Status

`BASELINE FOR REPORT ROUND 1 — HUMAN APPROVED PRODUCT DEFINITION`

Mỗi item dưới đây trace về Requirement, Business Rule, Decision hoặc Open Question canonical. `OPEN / NOT DECIDED` không phải approved behavior.

## IN MVP

| Item | Trace |
|---|---|
| Một Warehouse | `DEC-005`, `CAND-REQ-003` |
| `Backroom` và `Sales Shelf` ở mức area | `DEC-006`, `DEC-010` |
| Per-location `system stock quantity`; Warehouse total là tổng location quantities | `CAND-REQ-003`, `CAND-BR-003`, `DEC-010` |
| Location quantity không được âm | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019`; resolves `OQ-015` |
| Receive actual-versus-expected comparison và quantity discrepancy | `CAND-REQ-001/002`, `CAND-BR-001`, `US-REC-001` |
| External/manual expected quantity/reference | `CAND-REQ-009`, `DEC-016` |
| Human review cho system/document reference mismatch | `CAND-BR-014`, `DEC-016`, `US-REC-001` |
| Initial Putaway allocation | `CAND-REQ-007`, `CAND-BR-004`, `DEC-011`, `US-PUT-001` |
| Full, multi-location và `PARTIAL / INSUFFICIENT` Pick | `CAND-REQ-006`, `CAND-BR-005/006`, `DEC-012`, `US-PICK-001` |
| Pick validation không cho confirm vượt total selected-source quantity | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019`, `US-PICK-001` |
| Internal Transfer execution/confirmation và minimum record | `FR-012`, `CAND-BR-007/008`, `DEC-013/024`, `US-TRF-001` |
| Transfer history | `FR-013`, `DEC-013/024`, `US-TRF-002` |
| Transfer validation không cho confirm vượt source quantity | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019`, `US-TRF-001` |
| Selected-scope Audit với match/mismatch result | `CAND-REQ-005`, `CAND-BR-009`, `DEC-014`, `US-AUD-001` |
| Audit discrepancy context, mandatory re-check và no-auto-Adjust | `CAND-BR-002/010`, `DEC-014`, `US-AUD-002` |
| Adjust request, reason, optional attachment và Manager decision | `CAND-REQ-008`, `CAND-BR-011/012/013`, `DEC-015`, `US-ADJ-001/002` |
| Adjust validation không cho affected location quantity âm | `CAND-REQ-011`, `CAND-BR-015`, `DEC-019`, `US-ADJ-002` |
| Permission description cho Warehouse Staff, Manager, Purchasing và Admin | `CAND-REQ-010`, `DEC-017` |

## OUT OF MVP

| Item | Trace |
|---|---|
| Multi-Warehouse và cross-Warehouse operation | `DEC-005`, `DEC-007` |
| Aisle, rack, bin và detailed shelf | `DEC-006` |
| Full Purchase Order lifecycle | `DEC-016` |
| Downstream fulfilment/use sau Pick | `CAND-REQ-006`, `DEC-012` |
| FIFO, FEFO và reservation trong Pick MVP hiện tại | `DEC-012` |
| Pick scanning trong MVP hiện tại | `DEC-012` |
| Automatic Adjust từ Audit mismatch | `CAND-BR-010`, `DEC-014` |
| Automatic Transfer/Movement system record từ Putaway | `CAND-BR-004`, `DEC-011` |
| Standalone Purchasing operational story | `DEC-017`; Purchasing is a supporting role of Receive |
| Standalone Admin operational story | `DEC-017`; Admin permission remains in the permission model |

## OPEN / NOT DECIDED

| Item | Trace / boundary |
|---|---|
| Receive final completion và exact Putaway handoff | `OQ-013` |
| Putaway exception/downstream handoff | `OQ-013` |
| Transfer exception/failure/cancel/reversal | `OQ-013` |
| Audit mismatch completion và schedule | `OQ-013` |
| Adjust rejected-case final closure | `OQ-013` |
| Pick cancellation/retry ngoài approved insufficient và negative-stock guards | `OQ-013` |
| Partial Receive, Putaway và Transfer | `OQ-014`; Pick partial behavior đã được quyết định tại `DEC-012` |
| Retry/cancel behavior sau failed negative-stock validation | Không được quyết định bởi `DEC-019`; không tự suy diễn |
| Lot/batch, serial, expiry, UOM/conversion | `OQ-012` |
| Alert trigger, recipient, threshold và workflow | `REQ-004`, `OQ-021` |
| Barcode/QR, general scanner, mobile/offline, external integration | `OQ-022`; Pick scanning riêng đã out of MVP tại `DEC-012` |
| Inventory Q&A data sources | `AI-DIR-001`, `OQ-027` |
| Inventory anomaly definition/evidence | `AI-DIR-002`, `OQ-028` |
| Reorder advisory/action authority | `AI-DIR-003`, `OQ-029` |
| AI data availability và evaluation/safety criteria | `OQ-030/031` |
| Quantitative product metrics / NFR | `OQ-033`; no approved quantitative KPI |

## Workflow interpretation

`Receive -> Putaway -> Pick -> Transfer -> Adjust -> Audit` tại `REQ-002` là capability list. Consolidated flow không yêu cầu Pick, Transfer, Audit và Adjust xảy ra tuần tự cho mọi inventory item. Approved relationships được ghi tại `DEC-018` và [User Flow](user-flow.md).
