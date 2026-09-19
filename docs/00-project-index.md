# Mục lục dự án cho Report Round 1

- Hạn: **04/09/2026**
- Phạm vi: **Bài 1 + Bài 2**
- Yêu cầu sản phẩm là canonical tại [`vault/02-requirements/requirements.md`](../vault/02-requirements/requirements.md).
- Mục lục này theo dõi deliverable môn học/báo cáo và không gán ID yêu cầu sản phẩm cho chúng.

## Group Round 1 Report

| Deliverable | Artifact | Trạng thái |
|---|---|---|
| Báo cáo nhóm Round 1 — Bài 1 + Bài 2 | [`report-round1/group-round1-report.md`](report-round1/group-round1-report.md) | **Completed / Human-reviewed** |

## Bài 1

| Deliverable | Artifact phục vụ báo cáo | Nguồn/bằng chứng canonical | Người phụ trách | Trạng thái |
|---|---|---|---|---|
| Project Charter | [`01-discovery/project-charter.md`](01-discovery/project-charter.md) | Nguồn giảng viên + tri thức Vault và `DEC-027–029` đã duyệt | Product/BA — Thanh Ngân | Baseline Report Round 1 đã cập nhật từ human-approved objectives, success criteria và scope/constraint decisions; chờ human review documentation diff |
| User Research + Synthesis | [`01-discovery/user-research.md`](01-discovery/user-research.md) | `vault/01-sources/interview-notes.md`; `vault/01-sources/research-evidence.md` (`EVD-001–019`) | Product/BA — Thanh Ngân; UX/UI — Nghĩa | Report-facing summary đã đồng bộ với human-confirmed evidence từ P1/P2/P3; giới hạn một minimart và các OQ được giữ rõ |
| Requirements + Business Rules | [`02-requirements/requirements-and-business-rules.md`](02-requirements/requirements-and-business-rules.md) | `vault/02-requirements/` | Product/BA — Thanh Ngân | Requirements + NFR Round 1 human approved: 12 active FR, 5 NFR, 15 BR; `OQ-032/033` partially resolved by approved auth and Render staging/demo designs; long-term production deployment and other listed boundaries remain open |
| Project Vault | [`../vault/00-index.md`](../vault/00-index.md) | `vault/` | AI/Vault — Ly Na | Đã scaffold |
| Vault Q&A Benchmark | [`02-requirements/vault-qa-benchmark.md`](02-requirements/vault-qa-benchmark.md) | `vault/09-ai/qa-benchmark.md` | AI/Vault — Ly Na | Completed — 20 questions — Human reviewed — Accuracy: 100% |
| AI Usage Log v1 | [`AI_USAGE_LOG.md`](AI_USAGE_LOG.md) | Việc dùng AI cá nhân đã kiểm chứng | Tất cả thành viên; Ly Na điều phối | 16 mục; có Auth + Deployment human decision, Final Delivery readiness/scope-freeze reconciliation, Figma evidence reconciliation và human-verification boundary |

## Bài 2

| Deliverable | Artifact phục vụ báo cáo | Nguồn/bằng chứng canonical | Người phụ trách | Trạng thái |
|---|---|---|---|---|
| PRD | [`03-product/PRD.md`](03-product/PRD.md) | `vault/02-requirements/`, `vault/03-domain/`, canonical stories và Decision Log | Product/BA — Thanh Ngân | Baseline Report Round 1 — HUMAN APPROVED; 12 active FR, 5 canonical NFR và priority schema đã đồng bộ; OQ unresolved được giữ rõ |
| MVP Scope | [`03-product/mvp-scope.md`](03-product/mvp-scope.md) | Requirements, Business Rules, OQ và Decision Log canonical | Product/BA — Thanh Ngân | Baseline IN / OUT / OPEN đã tạo |
| User Flow | [`03-product/user-flow.md`](03-product/user-flow.md) | `vault/03-domain/workflow-overview.md`; canonical stories | UX/UI — Nghĩa + Story owner | Consolidated flow đã cập nhật; Pick/Transfer độc lập; Audit mismatch → re-check → Adjust consideration |
| Functional Prototype | [`03-product/functional-prototype.md`](03-product/functional-prototype.md), [`05-design/screen-inventory.md`](05-design/screen-inventory.md) | Canonical stories/flow + human-reviewed usability decisions | UX/UI — Nghĩa | PASS — 10 logical base screens; 31 wireframe states; 31 prototype counterparts; 3 critical flows human verified |
| Usability Test Script | [`05-design/usability-test-script.md`](05-design/usability-test-script.md) | Canonical stories/flow; không thay raw test evidence | UX/UI — Nghĩa; QA — Thảo Ngân | Hoàn thiện cho P1/P2/P3; chờ human review |
| Usability Findings | [`05-design/usability-findings.md`](05-design/usability-findings.md) | HUMAN-REVIEWED findings được cung cấp | UX/UI — Nghĩa; QA — Thảo Ngân | 3 findings theo Observation → Issue → Decision; chờ review diff |
| User Stories + AC | [`04-backlog/user-stories.md`](04-backlog/user-stories.md) | `vault/04-product/stories/` | Product/BA + Story owner | 9 canonical User Stories — HUMAN APPROVED; đạt mục tiêu 8–12 |
| Taiga Backlog | [`04-backlog/taiga-backlog.md`](04-backlog/taiga-backlog.md) | Story ID đã review + Taiga | QA/Release — Thảo Ngân | 6 Epic, 9 User Story và 27 Task refs đã đồng bộ; quyền truy cập/người phụ trách công cụ vẫn TBD |
| Figma + Design System | [`05-design/design-system.md`](05-design/design-system.md), [Figma prototype](https://www.figma.com/design/d5XrKKZGoeVefVGqVVTwlu/Warehouse---Smart-Inventory-Management?node-id=0-1) | Canonical stories/flow + downstream Figma artifact | UX/UI — Nghĩa | PARTIAL overall — browser access và 8 pages human verified; foundations PASS; components PASS/PARTIAL; High Fidelity và Dev Handoff chưa hoàn thành; exact hotspot count chưa verify |
| Architecture + ADR | [`06-technical/architecture.md`](06-technical/architecture.md) | [`vault/06-technical/`](../vault/06-technical/) | Engineering — Nghi | Technical Foundation + 3 ADR; `DEC-031/032` approve session-auth and Render staging/demo designs only; auth/deployment not implemented |
| Repo Scaffold + CI Baseline | [`../apps/README.md`](../apps/README.md), [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) | `DEC-020` và technical foundation đã duyệt | Engineering — Nghi | Completed; first vertical slice `US-PUT-001` completed and verified by GitHub Actions (`backend-checks`, `frontend-checks`, `putaway-e2e`) |
| ERD / Data Model | [`06-technical/data-model.md`](06-technical/data-model.md) | [`vault/06-technical/data-model.md`](../vault/06-technical/data-model.md) | Engineering — Nghi | Conceptual MVP model + implemented `US-PUT-001` schema; conceptual `users`/`auth_sessions` baseline approved but no auth migration exists |
| API Contract | [`06-technical/API.md`](06-technical/API.md) | [`vault/06-technical/api-contract.md`](../vault/06-technical/api-contract.md) | Engineering — Nghi | Auth route/401/403 baseline approved at `DEC-031` but not implemented; other MVP route map proposed; Putaway contract documented |
| Story Specs + Traceability | [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md) | Canonical stories + [`vault/06-technical/story-specs/`](../vault/06-technical/story-specs/) | Tất cả Story owner; QA điều phối | `US-PUT-001` completed; backend verified on PostgreSQL 18, frontend checks passed, and React → FastAPI → PostgreSQL 18 Playwright E2E passed in GitHub Actions |

## First vertical slice evidence

`US-PUT-001` is the first completed vertical slice; this status does not claim that the full MVP is implemented.

- Backend tests: [`../apps/backend/tests/test_putaway.py`](../apps/backend/tests/test_putaway.py)
- Playwright E2E: [`../apps/frontend/e2e/putaway.spec.ts`](../apps/frontend/e2e/putaway.spec.ts)
- GitHub Actions workflow: [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- Technical Story Spec: [`06-technical/story-specs/putaway.md`](06-technical/story-specs/putaway.md) and [`../vault/06-technical/story-specs/US-PUT-001.md`](../vault/06-technical/story-specs/US-PUT-001.md)
- Traceability: [`TRACEABILITY.md`](TRACEABILITY.md)

## Taiga references

- Project: [group-07-project](https://tree.taiga.io/project/lenghi-group-07-project/)
- Project ID: `1805021`
- Slug: `lenghi-group-07-project`
- Mapping chi tiết và trạng thái: [`04-backlog/taiga-backlog.md`](04-backlog/taiga-backlog.md)

### Epics

| Canonical Epic | Taiga ref / ID |
|---|---|
| `EP-01` | [#1](https://tree.taiga.io/project/lenghi-group-07-project/epic/1) / `366660` |
| `EP-02` | [#2](https://tree.taiga.io/project/lenghi-group-07-project/epic/2) / `366661` |
| `EP-03` | [#3](https://tree.taiga.io/project/lenghi-group-07-project/epic/3) / `366662` |
| `EP-04` | [#4](https://tree.taiga.io/project/lenghi-group-07-project/epic/4) / `366663` |
| `EP-05` | [#5](https://tree.taiga.io/project/lenghi-group-07-project/epic/5) / `366664` |
| `EP-06` | [#6](https://tree.taiga.io/project/lenghi-group-07-project/epic/6) / `366665` |

### User Stories

| Canonical Story | Taiga ref / ID | Status |
|---|---|---|
| `US-REC-001` | [#7](https://tree.taiga.io/project/lenghi-group-07-project/us/7) / `9523822` | Ready |
| `US-PUT-001` | [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) / `9523823` | Done |
| `US-PICK-001` | [#9](https://tree.taiga.io/project/lenghi-group-07-project/us/9) / `9523824` | Ready |
| `US-TRF-001` | [#10](https://tree.taiga.io/project/lenghi-group-07-project/us/10) / `9523825` | New |
| `US-TRF-002` | [#11](https://tree.taiga.io/project/lenghi-group-07-project/us/11) / `9523826` | New |
| `US-AUD-001` | [#12](https://tree.taiga.io/project/lenghi-group-07-project/us/12) / `9523827` | Ready |
| `US-AUD-002` | [#13](https://tree.taiga.io/project/lenghi-group-07-project/us/13) / `9523828` | Ready |
| `US-ADJ-001` | [#14](https://tree.taiga.io/project/lenghi-group-07-project/us/14) / `9523829` | Ready |
| `US-ADJ-002` | [#15](https://tree.taiga.io/project/lenghi-group-07-project/us/15) / `9523830` | Ready |

### Tasks

Tất cả 27 Tasks có trạng thái **New**.

| Canonical Story | Canonical Task → Taiga ref |
|---|---|
| `US-REC-001` | `T-REC-01` → [#16](https://tree.taiga.io/project/lenghi-group-07-project/task/16); `T-REC-02` → [#17](https://tree.taiga.io/project/lenghi-group-07-project/task/17); `T-REC-03` → [#18](https://tree.taiga.io/project/lenghi-group-07-project/task/18) |
| `US-PUT-001` | `T-PUT-01` → [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19); `T-PUT-02` → [#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20); `T-PUT-03` → [#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) |
| `US-PICK-001` | `T-PICK-01` → [#22](https://tree.taiga.io/project/lenghi-group-07-project/task/22); `T-PICK-02` → [#23](https://tree.taiga.io/project/lenghi-group-07-project/task/23); `T-PICK-03` → [#24](https://tree.taiga.io/project/lenghi-group-07-project/task/24) |
| `US-TRF-001` | `T-TRF1-01` → [#25](https://tree.taiga.io/project/lenghi-group-07-project/task/25); `T-TRF1-02` → [#26](https://tree.taiga.io/project/lenghi-group-07-project/task/26); `T-TRF1-03` → [#27](https://tree.taiga.io/project/lenghi-group-07-project/task/27) |
| `US-TRF-002` | `T-TRF2-01` → [#28](https://tree.taiga.io/project/lenghi-group-07-project/task/28); `T-TRF2-02` → [#29](https://tree.taiga.io/project/lenghi-group-07-project/task/29); `T-TRF2-03` → [#30](https://tree.taiga.io/project/lenghi-group-07-project/task/30) |
| `US-AUD-001` | `T-AUD1-01` → [#31](https://tree.taiga.io/project/lenghi-group-07-project/task/31); `T-AUD1-02` → [#32](https://tree.taiga.io/project/lenghi-group-07-project/task/32); `T-AUD1-03` → [#33](https://tree.taiga.io/project/lenghi-group-07-project/task/33) |
| `US-AUD-002` | `T-AUD2-01` → [#34](https://tree.taiga.io/project/lenghi-group-07-project/task/34); `T-AUD2-02` → [#35](https://tree.taiga.io/project/lenghi-group-07-project/task/35); `T-AUD2-03` → [#36](https://tree.taiga.io/project/lenghi-group-07-project/task/36) |
| `US-ADJ-001` | `T-ADJ1-01` → [#37](https://tree.taiga.io/project/lenghi-group-07-project/task/37); `T-ADJ1-02` → [#38](https://tree.taiga.io/project/lenghi-group-07-project/task/38); `T-ADJ1-03` → [#39](https://tree.taiga.io/project/lenghi-group-07-project/task/39) |
| `US-ADJ-002` | `T-ADJ2-01` → [#40](https://tree.taiga.io/project/lenghi-group-07-project/task/40); `T-ADJ2-02` → [#41](https://tree.taiga.io/project/lenghi-group-07-project/task/41); `T-ADJ2-03` → [#42](https://tree.taiga.io/project/lenghi-group-07-project/task/42) |

## Liên kết bên ngoài

- [Figma prototype — Warehouse & Smart Inventory Management](https://www.figma.com/design/d5XrKKZGoeVefVGqVVTwlu/Warehouse---Smart-Inventory-Management?node-id=0-1)
- [Taiga project — group-07-project](https://tree.taiga.io/project/lenghi-group-07-project/)
- Metadata/quyền truy cập Taiga và Figma được theo dõi trong [`vault/04-product/external-tools.md`](../vault/04-product/external-tools.md).
