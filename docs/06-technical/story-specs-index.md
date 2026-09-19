# Mục lục Story Spec

## Trạng thái

Technical Foundation đã được human approve. Canonical Technical Story Spec cho `US-PUT-001` tồn tại và vertical slice đã **COMPLETED / CI VERIFIED** qua React frontend, FastAPI API, PostgreSQL 18 persistence/migration, backend/frontend checks và Playwright E2E. Implementation được merge tại PR #22. Trạng thái này chỉ áp dụng cho first vertical slice và không phải bằng chứng full MVP đã hoàn thành. Historical Transfer draft được bảo tồn; Transfer technical contract vẫn cần story-specific review.

## Mapping

| Story ID | Người phụ trách | Requirement/Rule | Flow/Design | Taiga | Technical contract | Test | Bằng chứng |
|---|---|---|---|---|---|---|---|
| [`US-PUT-001`](story-specs/putaway.md) | Phan Lê Nghi | `CAND-REQ-003/007/010`, `CAND-BR-003/004`, `DEC-006/010/011/017/020–023` | `SCR-03`; `PF-01` facilitator boundary | [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) — Done | Canonical human-reviewed Technical Story Spec; `POST /api/v1/putaways` implemented with React, FastAPI and PostgreSQL 18 persistence/migration | COMPLETED; backend/frontend/Playwright CI evidence recorded PASS | PR #22 merged; HUMAN PRODUCT DECISION + HUMAN APPROVED TECHNICAL DECISIONS; canonical AC unchanged; full MVP not claimed |
| `US-TRF-001` | Nguyễn Thị Ly Na | `CAND-REQ-003/010/011`, `FR-012`, `CAND-BR-003/007/008/015`, `DEC-007/010/013/017/019/024` | Canonical execution/confirmation and negative-stock guard flow | [#10](https://tree.taiga.io/project/lenghi-group-07-project/us/10) | Historical draft only; story-specific contract pending | Chưa thực thi | HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS; historical `CAND-REQ-004` was superseded/decomposed; `EVD-010`, `EVD-011`, `EVD-019` are context only |
| `US-TRF-002` | Nguyễn Thị Ly Na | `CAND-REQ-010`, `FR-013`, `CAND-BR-008`, `DEC-013/017/024` | Canonical Transfer history flow | [#11](https://tree.taiga.io/project/lenghi-group-07-project/us/11) | Historical draft only; story-specific contract pending | Chưa thực thi | HUMAN PRODUCT DECISIONS / MVP ASSUMPTIONS; historical `CAND-REQ-004` was superseded/decomposed; `EVD-010`, `EVD-011`, `EVD-019` are context only |

Canonical product story files nằm trong `vault/04-product/stories/`; canonical technical artifacts nằm trong [`../../vault/06-technical/`](../../vault/06-technical/). A full-quantity Putaway fixture is test scope only and does not resolve partial Putaway at `OQ-014`.
