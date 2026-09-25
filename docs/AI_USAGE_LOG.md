# AI Usage Log v1

## Trạng thái hiện tại

Log đã có các mục sử dụng AI; mỗi output vẫn cần human verification trước khi được tích hợp hoặc canonical hóa.

Mỗi sinh viên phải cung cấp ít nhất một mục có ý nghĩa và đã được kiểm chứng cho Report Round 1. Mục ghi nhận việc AI hỗ trợ và cách kiểm chứng; mục này không làm cho output AI trở thành nguồn có thẩm quyền.

## Template cho mỗi mục

### AI-USE-### — Kết quả ngắn gọn

- Thành viên: TBD
- Ngày/giờ: TBD
- Mục tiêu: TBD
- Ngữ cảnh có giới hạn đã cung cấp: TBD
- Tham chiếu prompt hoặc tương tác: TBD
- Tóm tắt output: TBD
- Cách con người kiểm chứng: TBD
- Thay đổi được chấp nhận: TBD
- Đề xuất bị từ chối/điều chỉnh: TBD
- ID/link artifact bị ảnh hưởng: TBD
- Người review: TBD

Không đưa secret, dữ liệu cá nhân, Context Pack tạm thời hoặc bước kiểm chứng giả vào đây.

### AI-USE-001 — Consistency review giữa Requirements và downstream artifacts

- Thành viên: Ly Na
- Ngày/giờ: 2026-09-03
- ID/link artifact bị ảnh hưởng:
  - `vault/02-requirements/requirements.md`
  - `vault/02-requirements/open-questions.md`
  - `docs/04-backlog/user-stories.md`
  - `docs/TRACEABILITY.md`
- Mục đích sử dụng AI:
  - Hỗ trợ kiểm tra tính nhất quán giữa requirement status, User Story, traceability và Open Questions.
- Kết quả AI hỗ trợ phát hiện:
  1. `CAND-REQ-003` có trạng thái không nhất quán: `APPROVED` trong Requirements nhưng `DRAFT` trong User Stories và TRACEABILITY.
  2. Một ID Open Question không canonical về location cardinality được tham chiếu trong downstream artifacts nhưng không tồn tại trong canonical `open-questions.md`.
- Cách kiểm chứng:
  - Kiểm tra trực tiếp các artifact trong repository và đối chiếu ID/status giữa các file.
  - Không sử dụng output của AI làm nguồn có thẩm quyền.
- Quyết định xử lý:
  - Không tự ý thay đổi trạng thái `CAND-REQ-003`.
  - Không tự tạo stable Open Question ID cho location cardinality.
  - Đánh dấu hai vấn đề để BA/team xác nhận trước khi cập nhật artifact.

  ## AI-USE-002 — Draft Transfer Story và Traceability consistency review

* **Member:** Ly Na
* **Date:** 2026-09-03
* **Affected artifacts:** `docs/04-backlog/user-stories.md`, `docs/TRACEABILITY.md`
* **AI purpose:** Hỗ trợ kiểm tra consistency và draft User Story Transfer từ các requirement, evidence và open questions đã có trong Vault.
* **Scope:** `REQ-002`, `REQ-004`, `CAND-REQ-004`, `EVD-010`, `EVD-011`, `EVD-019`, `OQ-013`, `OQ-014`, `OQ-016`, `OQ-020`, `OQ-022`.
* **AI output:** Đề xuất Transfer draft story ID (hiện đã được chuẩn hóa thành `DRAFT-US-TRF-001`) và downstream trace tương ứng, đồng thời giữ các behavior chưa được xác nhận ở trạng thái `TBD` / `OPEN QUESTION`.
* **Human verification:** Đã đối chiếu lại với `requirements.md`, `research-evidence.md`, `open-questions.md`, `user-stories.md` và `TRACEABILITY.md`.
* **Consistency decision:** Giữ `CAND-REQ-004` ở trạng thái `DRAFT`; không biến `EVD-010` thành bằng chứng cho việc hệ thống bắt buộc có Transfer/Movement transaction riêng.
* **Scope guard:** Không xác nhận automatic Stock update, Movement transaction, location change, warehouse scope hoặc role permission khi chưa có requirement được phê duyệt.
* **Verification status:** AI output không phải nguồn authoritative; Product/BA review vẫn cần thiết trước khi canonical hóa Story.

### AI-USE-003 — Prototype / usability artifact synthesis

- **Task:** Tổng hợp prototype/usability artifacts cho 3 critical flows.
- **Context/Input:** PRD, MVP Scope, consolidated User Flow, canonical User Stories, Traceability, Decision Log, Figma URL và 3 bộ human-reviewed findings cho `P1`/`P2`/`P3`.
- **AI/tool:** Codex hỗ trợ đọc repository, soạn/cập nhật Markdown và kiểm tra diff; không đóng vai participant và không thực hiện usability session.
- **Output:** Usability Test Script, Usability Findings, Screen Inventory; cập nhật Project Index, Traceability và các landing/status links liên quan.
- **Human verification:** Hoàn tất cho inventory-level evidence: con người mở Figma trực tiếp, xác minh 8 pages, 31 wireframe states, 31 prototype counterparts, 3 critical flows và 6 `FACILITATOR ONLY` items. Exact hotspot total/full wiring vẫn chưa independently verified.
- **Human decision:** Findings và ba UX clarity decisions đầu vào đã được xác nhận là human-reviewed; không tạo Requirement/Business Rule mới và không tạo decision-log entry trùng các `DEC-012/014/015/018/019`.
- **Artifact link:** [`05-design/usability-test-script.md`](05-design/usability-test-script.md), [`05-design/usability-findings.md`](05-design/usability-findings.md), [`05-design/screen-inventory.md`](05-design/screen-inventory.md), [`TRACEABILITY.md`](TRACEABILITY.md).

### AI-USE-004 — Taiga backlog synchronization

- **Task:** Taiga backlog synchronization.
- **Context/Input:** Project metadata, write plan đã được con người phê duyệt và các nguồn repository gồm Project Index, canonical backlog, Traceability, story ownership và external-tools metadata.
- **Tool:** Codex CLI dùng `fetch` tích hợp sẵn của Node.js với Taiga REST API, dưới sự phê duyệt rõ ràng của con người, để tạo và đọc lại các Taiga backlog items; credentials/tokens không được lưu trong repository.
- **Output:** Tạo 6 Epics, 9 canonical User Stories và 27 Tasks trong Taiga, đọc lại để kiểm tra mapping/status, rồi đồng bộ refs/statuses vào tài liệu repository.
- **Human verification:** Con người đã review/phê duyệt write plan và phải kiểm tra các Taiga refs/statuses cuối cùng trước khi tích hợp.
- **Human decision:** Product scope, canonical IDs, ownership, Acceptance Criteria và business behavior là đầu vào đã được con người phê duyệt; AI không độc lập quyết định hoặc mở rộng các nội dung này.
- **Artifact references:** [`00-project-index.md`](00-project-index.md), [`04-backlog/taiga-backlog.md`](04-backlog/taiga-backlog.md), [`04-backlog/user-stories.md`](04-backlog/user-stories.md), [`TRACEABILITY.md`](TRACEABILITY.md), [`../vault/04-product/external-tools.md`](../vault/04-product/external-tools.md).

### AI-USE-005 — Technical Foundation synthesis

- **Task:** Tổng hợp và ghi Technical Foundation documentation; chưa scaffold hoặc implement application.
- **Human-approved technical inputs:** React, TypeScript, Vite, npm; Python 3.13, FastAPI, uv, pytest; PostgreSQL 18, Docker; Playwright; SQLAlchemy 2, Alembic; modular monolith; authoritative stock theo SKU/location; derived Warehouse total; transactional/non-negative guards; Receive records actual quantity và Putaway performs initial posting.
- **AI/tool:** Codex đọc các canonical product/decision artifacts, soạn Markdown và chạy read-only/diff verification commands. AI không tự quyết architecture hoặc product behavior.
- **Output:** Canonical technical index, architecture, conceptual/vertical-slice data model, proposed API contract, 3 ADR, `US-PUT-001` technical Story Spec và report-facing/traceability updates.
- **Human verification:** Pending — con người cần review diff, xác nhận technical contract wording, route/payload/error proposal và ranh giới conceptual model trước integration.
- **Human decision:** Technical stack, persistence tooling, modular-monolith boundary và nội dung 3 ADR là human-approved inputs. `OQ-012`, `OQ-013`, `OQ-014`, production authentication, deployment, Adjust representation, attachment storage, advanced pagination/filtering và NFR vẫn OPEN/TBD.
- **Artifact references:** [`../vault/06-technical/README.md`](../vault/06-technical/README.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`06-technical/architecture.md`](06-technical/architecture.md), [`06-technical/data-model.md`](06-technical/data-model.md), [`06-technical/API.md`](06-technical/API.md), [`06-technical/story-specs/putaway.md`](06-technical/story-specs/putaway.md), [`TRACEABILITY.md`](TRACEABILITY.md).

### AI-USE-006 — Repo Scaffold + CI baseline

- **Task:** Dựng application repository scaffold và CI baseline; không implement business feature.
- **Human-approved stack:** React + TypeScript + Vite/npm; Python 3.13 + FastAPI/uv/pytest/Ruff; PostgreSQL 18/Docker Compose; SQLAlchemy 2 + Alembic; Playwright; GitHub Actions.
- **AI/tool:** Codex đọc các technical source/decision liên quan, tạo scaffold/config/lockfile/test/workflow, chạy dependency tooling và local verification commands. AI không tự tạo business behavior, schema, migration hoặc API Putaway.
- **Output:** Frontend placeholder với unit/E2E smoke tests; FastAPI với technical `GET /health`; lazy SQLAlchemy engine/session infrastructure; PostgreSQL 18 Compose; `.env.example`; README; Git ignore rules; hai CI jobs frontend/backend.
- **Human verification:** Pending — con người cần review toàn bộ diff. Evidence local: `npm ci`, lint, typecheck, 1 unit test, build và 1 Playwright smoke test pass; `uv sync --locked`, Ruff lint/format check và 1 pytest pass. `docker compose config` không chạy được vì Docker CLI không có trên máy; không claim PostgreSQL runtime.
- **Human decision:** Stack là input đã được duyệt tại `DEC-020`; production authentication/deployment vẫn `TBD`. `US-PUT-001` và mọi business feature/schema/API vẫn Not started.
- **Artifact references:** [`../apps/README.md`](../apps/README.md), [`../apps/frontend/`](../apps/frontend/), [`../apps/backend/`](../apps/backend/), [`../apps/docker/compose.yml`](../apps/docker/compose.yml), [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml), [`../vault/06-technical/README.md`](../vault/06-technical/README.md), [`../vault/06-technical/architecture.md`](../vault/06-technical/architecture.md), [`06-technical/architecture.md`](06-technical/architecture.md), [`00-project-index.md`](00-project-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).

### AI-USE-007 — US-PUT-001 Vertical Slice implementation

- **Task:** Triển khai first vertical slice end-to-end cho `US-PUT-001`; không commit, push hoặc đổi trạng thái Taiga.
- **Context/Input:** Canonical Story/AC `US-PUT-001`, Technical Architecture, Data Model, API Contract, `ADR-001/002/003`, Technical Story Spec, Putaway report spec, Traceability, Taiga mapping và scaffold hiện có.
- **AI/tool:** Codex đọc context giới hạn, sửa source/config/docs bằng patch, dùng Ruff/pytest/npm/Vitest/Vite/Alembic cho verification. Không tạo product rule mới và không dùng AI output làm nguồn canonical.
- **Output:** Schema/migration tối thiểu; actor dependency boundary; context read và `POST /api/v1/putaways`; transactional allocation + location balance upsert; idempotency guard; structured errors; test-only fixture; React UI; API/component tests; Playwright thật; PostgreSQL 18 CI jobs.
- **Human verification:** Con người đã review Git diff và thực hiện local frontend/backend checks. GitHub Actions sau đó xác minh `backend-checks` trên PostgreSQL 18, `frontend-checks`, và `putaway-e2e` qua React → FastAPI → PostgreSQL 18. Backend CI ban đầu fail do thứ tự flush fixture vi phạm FK; nguyên nhân đã được điều tra, fixture ordering đã được sửa và cả push lẫn pull-request reruns đều pass.
- **Human decision:** Chấp nhận vertical slice sau khi review diff và CI evidence. Stack, technical contracts và fixture 16 units là input đã duyệt; AI không tự quyết business behavior. Full placement chỉ là test scope; `OQ-012`, `OQ-013`, `OQ-014`, production authentication và deployment vẫn OPEN/TBD.
- **Actual verification commands/results (2026-09-05):** `$env:NODE_OPTIONS='--use-system-ca'; npm.cmd ci --cache .npm-cache --no-audit --no-fund` pass (`259 packages`); frontend lint/typecheck pass; Vitest `3 passed`; Vite build pass; Ruff lint/format-check pass; pytest `8 passed` trên SQLite component database; Alembic upgrade và downgrade smoke pass trên SQLite tạm. `uv sync --locked` không chạy vì `uv` không có trong PATH, nhưng checked-in `.venv` executables chạy được. Docker CLI không có, vì vậy PostgreSQL integration và `TEST-PUT-E2E-001` không chạy local và không được claim Pass.
- **Artifact references:** [`../apps/backend/alembic/`](../apps/backend/alembic/), [`../apps/backend/src/warehouse_api/`](../apps/backend/src/warehouse_api/), [`../apps/backend/tests/test_putaway.py`](../apps/backend/tests/test_putaway.py), [`../apps/frontend/src/App.tsx`](../apps/frontend/src/App.tsx), [`../apps/frontend/e2e/putaway.spec.ts`](../apps/frontend/e2e/putaway.spec.ts), [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml), [`TRACEABILITY.md`](TRACEABILITY.md).

### AI-USE-008 — CI failure diagnosis and verification

- **Task:** Diagnose the initial `US-PUT-001` backend CI failure and verify the corrected vertical slice.
- **Input/context:** Failed PostgreSQL 18 backend check, Putaway test fixture, SQLAlchemy model relationships, CI workflow, and the already-approved `US-PUT-001` behavior/contracts.
- **Tool:** Codex supported repository inspection and failure diagnosis; GitHub Actions executed the authoritative CI checks.
- **Output:** Identified fixture foreign-key ordering as the cause: `Warehouse` and `InternalLocation` were not flushed in dependency order under PostgreSQL FK enforcement, while the earlier local SQLite path did not enforce the same FK behavior by default. The fixture was ordered as Warehouse → flush → InternalLocation → flush → SKU → Receive → ReceiveLine → StockBalance.
- **Human verification:** Human reviewed the Git diff and local checks, inspected the failure/fix, and confirmed successful GitHub Actions reruns for both push and pull-request events: `backend-checks`, `frontend-checks`, and `putaway-e2e` all passed.
- **Decision:** Accept the fixture-ordering correction and the vertical slice based on the resulting evidence. No business behavior, canonical Acceptance Criterion, production authentication, or deployment decision was changed.
- **Evidence:** [`../apps/backend/tests/test_putaway.py`](../apps/backend/tests/test_putaway.py), [`../apps/frontend/e2e/putaway.spec.ts`](../apps/frontend/e2e/putaway.spec.ts), [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Time impact:** Not measured; the diagnosis isolated the PostgreSQL-specific fixture issue and supported a focused rerun.

### AI-USE-009 — Human-confirmed Taiga status documentation sync

- **Task:** Đồng bộ tài liệu repository với trạng thái Taiga của `US-PUT-001` sau khi evidence đã pass.
- **Input/context:** Human xác nhận Taiga Story [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) và Tasks [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19), [#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20), [#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) đã được cập nhật thủ công thành `Done`.
- **AI/tool:** Codex chỉ đồng bộ các trạng thái đã được human xác nhận vào tài liệu và kiểm tra Git diff; AI không thao tác Taiga, không sửa application code, business rule hoặc canonical Acceptance Criteria.
- **Human decision:** Human cập nhật trạng thái Taiga sau khi Technical Story Spec, implementation merge, frontend checks, backend PostgreSQL 18 checks, Playwright E2E và Traceability evidence đã pass.
- **Scope guard:** First vertical slice được ghi nhận `Completed / Verified`; không claim toàn bộ MVP Done. `OQ-012`, `OQ-013`, `OQ-014`, production authentication và deployment giữ nguyên trạng thái.
- **Human verification:** Chờ human review documentation diff trước khi tích hợp; không commit hoặc push trong lần đồng bộ này.

### AI-USE-010 — Q&A Benchmark Round 1 human-review finalization

- **Task:** Finalize trạng thái human review cho Q&A Benchmark Round 1 gồm 20 câu.
- **AI support:** AI đọc Vault, tạo Actual answer draft, so khớp Expected answer với Actual answer và tính score draft.
- **AI authority guard:** AI không tự xác nhận benchmark, không tự approve/reject score và không dùng output AI làm evidence có thẩm quyền.
- **Human verification:** Human đã kiểm tra Expected answer, Actual answer, supporting source và score của 20 câu.
- **Human responsibility and decision:** Human chịu trách nhiệm verify source, approve/reject score và đã chấp nhận benchmark cuối cùng với Total 20, Correct 20, Partial 0, Wrong 0, Unsupported 0, Accuracy 100%.
- **Scope guard:** Không thay đổi Question, Expected answer, Actual answer, Result hoặc supporting source; không đóng `OQ-013`, `OQ-014`, `OQ-027`, `OQ-029` hay Open Question nào khác.
- **Artifact references:** [`../vault/09-ai/qa-benchmark.md`](../vault/09-ai/qa-benchmark.md), [`../vault/00-index.md`](../vault/00-index.md), [`00-project-index.md`](00-project-index.md).

### AI-USE-011 — Requirements + NFR audit/finalization

- **Task:** Audit Requirement Inventory và hỗ trợ đồng bộ documentation sau Requirements + NFR Round 1 human review.
- **AI support:** AI đọc các artifact canonical/report-facing, phân loại FR/NFR/Business Rule/Constraint/Open Question, đề xuất decomposition và NFR candidates, hỗ trợ consistency checks, traceability update và diff verification. AI không tự canonicalize candidate hoặc quyết định metric.
- **Human decisions:** Human approve `CFR-01`/`CFR-02` và canonicalize thành `FR-012`/`FR-013`; đánh dấu historical `CAND-REQ-004` là `SUPERSEDED / DECOMPOSED`; approve `NFR-001` đến `NFR-005`; chọn priority schema và priority cho scope/FR/BR/NFR/Alert/AI.
- **Held/rejected proposals:** `CFR-03` đến `CFR-06` và `CNFR-06` tiếp tục `HOLD / NOT APPROVED`; không được canonicalize.
- **Open-boundary guard:** `OQ-012`, `OQ-014`, phần unresolved của `OQ-013`, `OQ-032` và `OQ-033` tiếp tục mở. Không quyết định partial Putaway, Receive completion/handoff, UOM/decimal, production authentication, deployment, performance/uptime/concurrent-user metrics, Alert workflow hoặc AI implementation.
- **Result:** Active canonical inventory được ghi nhận là 12 FR, 5 NFR và 15 Business Rules; priority coverage đầy đủ cho active requirements. Canonical Acceptance Criteria và application code không thay đổi.
- **Artifact references:** [`../vault/02-requirements/requirements.md`](../vault/02-requirements/requirements.md), [`../vault/02-requirements/business-rules.md`](../vault/02-requirements/business-rules.md), [`../vault/02-requirements/open-questions.md`](../vault/02-requirements/open-questions.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`02-requirements/requirements-and-business-rules.md`](02-requirements/requirements-and-business-rules.md), [`03-product/PRD.md`](03-product/PRD.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human verification:** Chờ human review documentation diff; không commit hoặc push.

### AI-USE-012 — Project Charter Round 1 finalization

- **Task:** Audit Project Charter completeness và đồng bộ documentation từ Human Decision Pack đã được phê duyệt.
- **AI support:** AI đọc Project Charter, research evidence, requirements/business rules, domain roles/workflow, PRD, MVP Scope, Traceability và Decision Log; đề xuất evidence-backed wording/options; kiểm tra consistency; cập nhật documentation sau khi có human approval. AI không tự quyết business objective, KPI, scope hoặc Open Question.
- **Human decisions:** Human approve `OBJ-A` và `OBJ-B`; giữ `OBJ-C` ở trạng thái `HOLD`; approve `SC-01` đến `SC-09`; approve việc tách `IN MVP`, `OUT / DEFERRED`, `OPEN / TBD`; approve risk và constraint wording được ghi tại `DEC-027–029`.
- **Scope and authority guard:** Không thêm quantitative business KPI; không resolve `OQ-012`, phần unresolved của `OQ-013`, `OQ-014`, production authentication, deployment hoặc Open Question khác; không thay đổi MVP behavior, canonical Acceptance Criteria hoặc application code.
- **Research consistency:** Report-facing User Research được đồng bộ với human-confirmed `EVD-001–019`, ba participant `P1/P2/P3` và limitation rằng tất cả cùng một minimart; không tạo transcript, quote hoặc evidence mới.
- **First-slice boundary:** `US-PUT-001` được giữ là first completed and verified vertical slice. `SC-09` là quality/delivery criterion cho slice này và không chứng minh full MVP đã được implemented.
- **Artifact references:** [`01-discovery/project-charter.md`](01-discovery/project-charter.md), [`01-discovery/user-research.md`](01-discovery/user-research.md), [`00-project-index.md`](00-project-index.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human verification:** Chờ human review documentation diff; không commit hoặc push.

### AI-USE-013 — Group Round 1 Report synthesis

- **Task:** Tổng hợp báo cáo nhóm ngắn cho Round 1 từ các artifact hiện có của Bài 1 và Bài 2.
- **AI support:** AI audit các artifact hiện có, đề xuất report structure có evidence, tổng hợp 10 highlights và 9 open risks, đồng thời giữ rõ verification limitation và scope boundary.
- **Human decisions:** Human approve toàn bộ report structure; approve 10 highlights; approve risks `R-01` đến `R-09`; approve wording đóng góp của năm thành viên; và cho phép tạo report cùng liên kết trong Project Index.
- **Authority guard:** AI không tự quyết contribution, không tự chấp nhận risk, không tạo evidence mới và không thay đổi business behavior hoặc canonical Acceptance Criteria.
- **Verification boundary:** Trạng thái Taiga, Figma và GitHub Actions trong report dựa trên repository-recorded/API read-back evidence; không claim live external-system verification trong phiên tổng hợp này. Report không claim full MVP implemented, production-ready hoặc deployed.
- **Artifact references:** [`report-round1/group-round1-report.md`](report-round1/group-round1-report.md), [`00-project-index.md`](00-project-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human verification:** Report được tạo theo Human Decision Pack đã phê duyệt; chờ human review documentation diff trước khi commit hoặc push.

### AI-USE-014 — Figma evidence reconciliation and human verification

- **Task:** Reconcile Figma/design evidence và đồng bộ trạng thái cuối vào tài liệu Round 1.
- **AI support:** AI audit design evidence trong repository, attempted MCP verification, nhận diện MCP result không đầy đủ và tổng hợp evidence status có giới hạn.
- **Human verification:** Human mở Figma trực tiếp trên browser; xác minh đủ 8 pages, Design System foundations, reusable components hiện diện, 31 wireframe states, 31 prototype counterparts, 3 critical flows và 6 layer/group bắt đầu bằng `FACILITATOR ONLY`; đồng thời xác nhận `05 - High Fidelity` và `07 - Dev Handoff` đang trống.
- **Decision:** Dùng human visual verification làm nguồn cho Figma evidence; MCP page inventory chỉ trả `00 - Cover` được coi là **INCOMPLETE / NON-AUTHORITATIVE**.
- **Limitations retained:** Không claim exact component count, radius/shadow/variables/text-style counts, exact hotspot total hoặc full interaction-level wiring. High Fidelity là **DEFERRED / NOT COMPLETED FOR ROUND 1**; Dev Handoff là **PARTIAL / NOT COMPLETED**.
- **Authority guard:** Không thay đổi product behavior, canonical Acceptance Criteria, Figma hoặc application code.
- **Artifact references:** [`05-design/design-system.md`](05-design/design-system.md), [`05-design/screen-inventory.md`](05-design/screen-inventory.md), [`03-product/functional-prototype.md`](03-product/functional-prototype.md), [`TRACEABILITY.md`](TRACEABILITY.md), [`00-project-index.md`](00-project-index.md), [`../vault/04-product/external-tools.md`](../vault/04-product/external-tools.md), [`report-round1/group-round1-report.md`](report-round1/group-round1-report.md).
- **Human review:** Chờ human review documentation diff; không commit hoặc push.

### AI-USE-015 — Final Delivery readiness and scope freeze

- **Task:** Audit Final Delivery readiness và reconcile planning/report-facing documentation sau human review; không sửa application code hoặc canonical Acceptance Criteria.
- **AI support:** AI audit implementation/release gaps, phát hiện Putaway Story Spec index drift, Taiga status drift và stale Transfer requirement/Technical Foundation references; đề xuất implementation ordering để con người review.
- **Human decisions:** Human giữ cả 9 canonical stories là `MUST`, thay đổi implementation order để đặt `US-PICK-001` trước Transfer, giữ `US-TRF-001` trước `US-TRF-002` và Audit trước Adjust, đồng thời approve reconciliation work.
- **Approved order:** `US-PUT-001` completed baseline → `US-REC-001` → `US-PICK-001` → `US-TRF-001` → `US-TRF-002` → `US-AUD-001` → `US-AUD-002` → `US-ADJ-001` → `US-ADJ-002`.
- **Authority guard:** Không thay đổi canonical product scope, canonical FR priority, Business Rule hoặc Acceptance Criteria; không resolve Open Question. Production authentication mechanism và deployment target vẫn `TBD`.
- **Verification boundary:** Putaway CI/PR/Taiga statuses là repository-recorded evidence; task này không live-verify GitHub Actions hoặc Taiga và không thao tác external system.
- **Artifact references:** [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`04-backlog/taiga-backlog.md`](04-backlog/taiga-backlog.md), [`04-backlog/user-stories.md`](04-backlog/user-stories.md), [`03-product/mvp-scope.md`](03-product/mvp-scope.md), [`06-technical/story-specs/transfer.md`](06-technical/story-specs/transfer.md), [`TRACEABILITY.md`](TRACEABILITY.md), [`../vault/04-product/transfer-draft.md`](../vault/04-product/transfer-draft.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md).
- **Human review:** Human approved the scope/order inputs and reconciliation task; resulting documentation diff still requires review before commit or integration.

### AI-USE-016 — Auth + Deployment decision

- **Task:** Audit authentication/deployment gaps, compare practical options and synchronize documentation after human approval; no application code, migration, commit or push.
- **AI support:** AI inspected the current actor boundary, protected Putaway routes, test-only actor injection, missing login/user/password/session implementation, Docker/PostgreSQL/Alembic/CORS/health/CI state; compared JWT with server-side sessions and compared Render, Railway, VPS/server trường and Docker-local-only deployment.
- **Human decisions:** Human approved PostgreSQL-backed server-side session authentication, random session IDs with only token hashes stored, secure browser cookies, Argon2id password hashing, database-resolved authorization for `WAREHOUSE_STAFF`, `MANAGER`, `PURCHASING` and `ADMIN`, and `401`/`403` semantics. Human approved Render for staging/demo with React Static Site, FastAPI Web Service and managed PostgreSQL, while keeping long-term production deployment `TBD`.
- **Scope guard:** Approved design is not implementation. No auth application code or migration was created; no deployment was performed or verified. Test actor injection remains automated-test-only. No JWT, refresh token, self-registration, password reset, social login, OAuth, Keycloak or external identity provider was added to the MVP baseline.
- **Decision/OQ trace:** `DEC-031`, `DEC-032`; `OQ-032` partially resolved and `OQ-033` partially updated without closing unrelated Open Questions.
- **Artifact references:** [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`../vault/02-requirements/open-questions.md`](../vault/02-requirements/open-questions.md), [`../vault/06-technical/architecture.md`](../vault/06-technical/architecture.md), [`../vault/06-technical/api-contract.md`](../vault/06-technical/api-contract.md), [`../vault/06-technical/data-model.md`](../vault/06-technical/data-model.md), [`06-technical/architecture.md`](06-technical/architecture.md), [`06-technical/API.md`](06-technical/API.md), [`06-technical/data-model.md`](06-technical/data-model.md), [`TRACEABILITY.md`](TRACEABILITY.md), [`00-project-index.md`](00-project-index.md).
- **Human review:** Human approved the decisions and requested this docs-only synchronization; resulting documentation diff still requires review before commit or integration.

### AI-USE-017 — Deployment re-decision: Vercel, Render and Supabase

- **Task:** Audit the teacher-directed Vercel/Supabase deployment change, compare Render and Railway for the FastAPI backend, identify compatibility/security impacts and synchronize documentation after human review; no application code, cloud resource, deployment, commit or push.
- **AI support:** AI audited `DEC-032`, technical documentation, Traceability, application configuration and CI; compared Render/Railway; identified the PostgreSQL 17 staging versus PostgreSQL 18 foundation conflict; proposed Vercel same-origin `/api/*` rewrite to retain secure session-cookie auth; and documented migration, readiness, seed and smoke gaps.
- **Human decisions:** Human approved Vercel for the React/Vite frontend, Render for the FastAPI backend, Supabase only as hosted PostgreSQL, Supabase PostgreSQL 17 for staging/demo, PostgreSQL 17+ application/migration compatibility, and the Vercel same-origin `/api/*` rewrite with host-only `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` cookie behavior. Human retained FastAPI as application authority, SQLAlchemy + Alembic as persistence/migration authority and long-term production deployment as `TBD`.
- **Supersession boundary:** `DEC-034` supersedes only the Render Static Site and Render managed PostgreSQL clauses of `DEC-032`; Render remains the FastAPI host and all staging/demo-only public HTTPS, external-secret, migration/readiness/seed/smoke and no-`--reload` requirements remain active. `DEC-035` supersedes only an all-environment exact PostgreSQL 18 interpretation of `DEC-020`; it does not change the PostgreSQL engine or erase PostgreSQL 18 CI evidence.
- **Implementation boundary:** Auth implementation is merged and human-confirmed merged-PR backend/frontend/E2E CI checks pass. Vercel/Render/Supabase deployment, PostgreSQL 17 staging verification, `/ready`, production-safe demo-data seed, migration automation and public HTTPS cookie smoke remain not implemented or not verified.
- **Authority guard:** No Supabase Auth, browser SDK business-data path, Data API, Supabase JWT or external identity provider was added. No provider URL, database credential or secret was invented or recorded. No application code, deployment workflow or cloud resource was created.
- **Decision trace:** `DEC-034`, `DEC-035`; `DEC-032` and `DEC-020` remain append-only history with explicit clause-level supersession.
- **Artifact references:** [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`../vault/06-technical/architecture.md`](../vault/06-technical/architecture.md), [`06-technical/architecture.md`](06-technical/architecture.md), [`TRACEABILITY.md`](TRACEABILITY.md), [`00-project-index.md`](00-project-index.md), [`../apps/README.md`](../apps/README.md).
- **Human review:** Human approved the deployment re-decision and this docs-only synchronization; resulting documentation diff still requires review before commit or integration.

### AI-USE-018 — US-REC-001 Technical Story Spec human-review finalization

- **Task:** Audit the current Receive scaffold, prepare an implementation-ready `US-REC-001` Technical Story Spec, and synchronize the human-reviewed contract without writing application code or migrations.
- **AI support:** AI mapped canonical AC to requirements, evidence, rules and decisions; audited `Receive`/`ReceiveLine`, Putaway coupling, auth/error/migration/frontend/test conventions; proposed minimum data/API/UI/test contracts; and preserved unresolved lifecycle boundaries for explicit human review.
- **Human decisions:** Human approved `RECEIVE_RECORDED`; minimum external/manual expected context; `REFERENCE_MATCH` / `REFERENCE_MISMATCH`; Warehouse Staff mismatch acknowledgement with reviewer/time; a Putaway eligibility gate for unreviewed mismatch; full prepared-context recording without partial semantics; typed duplicate conflict; legacy-safe nullable migration without fabricated facts; Warehouse Staff backend authorization; and Receive no-effect guarantees. These decisions are recorded at `DEC-036`.
- **Scope guard:** No Purchase Order/procurement lifecycle, final Receive completion, automatic Receive -> Putaway trigger/navigation, Receive stock mutation, partial status/remaining lifecycle, approve/reject reference flow, correction/reversal history or Receive idempotency requirement was added.
- **Open boundaries:** `OQ-013` remains `PARTIALLY DECIDED / OPEN` for final completion/handoff. `OQ-014` remains `OPEN`; partial Receive is `NOT IMPLEMENTED` in this slice, not permanently excluded.
- **Verification boundary:** Documentation-only task. The unchanged application baseline had fresh local backend pytest `57 passed`, frontend Vitest `15 passed`, ESLint PASS and TypeScript PASS during the pre-review audit. No Receive implementation, migration, PostgreSQL migration cycle or Receive Playwright evidence is claimed.
- **Artifact references:** [`../vault/06-technical/story-specs/US-REC-001.md`](../vault/06-technical/story-specs/US-REC-001.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`../vault/02-requirements/open-questions.md`](../vault/02-requirements/open-questions.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human review:** Human approved the implementation decisions and requested docs-only synchronization; implementation still requires normal code diff review and fresh test evidence. No commit or push was performed.

### AI-USE-019 — US-PICK-001 Technical Story Spec human-review finalization

- **Task:** Audit the current inventory/application foundation, prepare an implementation-ready `US-PICK-001` Technical Story Spec, and synchronize the human-approved contract without writing application code or migrations.
- **AI support:** AI mapped all four canonical Pick ACs to requirements, rules, decisions and NFRs; audited StockBalance, location/SKU, Receive/Putaway transaction conventions, auth/error handling, frontend structure, Pick design, fixtures and Playwright; proposed minimum lifecycle, data, API, locking, UI and test contracts; and separated proposals from unresolved boundaries for human review.
- **Human decisions:** Human approved one immutable confirmed result per prepared/external single-SKU Pick request; outcomes `FULLY_COMPLETED` and `PARTIAL_INSUFFICIENT`; explicit Warehouse Staff-selected unique positive source allocations; no automatic maximum/assignment; explicit partial confirmation with picked/requested/remaining values; rejection of zero and over-requested totals; `pick_requests` plus `pick_allocations` without `PickLine` or duplicated picked quantity; approved GET context and POST confirmation routes; deterministic request/balance locking and atomic source decrement; typed duplicate conflict without a new Pick idempotency framework; and no Manager endpoint/action. These decisions are recorded at `DEC-037`.
- **Scope guard:** No Pick request creation, correction/reversal, multiple later partial confirmations, Manager review lifecycle, auto-allocation, FIFO, FEFO, reservation, scanner/device flow, generic Movement, Transfer, Adjust or Receive/Putaway mutation was added.
- **Open boundaries:** `OQ-012` and `OQ-022` remain open. Future retry/idempotency, Manager partial-review contract and retry/cancel topics outside the approved boundary remain `TBD / OUT OF CURRENT SLICE`. `OQ-014` remains open at cross-workflow level while current-slice partial Pick semantics are decided.
- **Verification boundary:** Documentation-only finalization. During the pre-review audit, the unchanged baseline produced backend pytest `86 passed`, frontend Vitest `23 passed`, ESLint PASS, TypeScript PASS and production build PASS; Playwright discovery listed four existing tests but no Pick test. No Pick code, migration, PostgreSQL concurrency result or Pick browser E2E evidence is claimed.
- **Artifact references:** [`../vault/06-technical/story-specs/US-PICK-001.md`](../vault/06-technical/story-specs/US-PICK-001.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`../vault/02-requirements/open-questions.md`](../vault/02-requirements/open-questions.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human review:** Human approved the implementation decisions and requested docs-only synchronization; implementation still requires normal code diff review and fresh test evidence. No commit or push was performed.

### AI-USE-020 — US-PICK-001 worktree implementation

- **Task:** Implement the human-approved `US-PICK-001` Technical Story Spec across schema, migration, backend, frontend, automated tests, Playwright fixtures and traceability without commit, push or deployment.
- **AI support:** AI added the two-table Pick model, immutable confirmation service, Warehouse Staff GET/POST API, deterministic request/balance locking, strict typed validation, full/partial UI with a second explicit partial confirmation, isolated browser fixtures, PostgreSQL 17/18 CI matrix, and automated no-effect/concurrency coverage.
- **Human decisions:** Frontend path `/pick/{pick_id}`; no router dependency; two-step partial confirmation without an API flag; isolated-only destructive downgrade; PostgreSQL 17/18 verification matrix; exact Pick error mapping; parallel-safe E2E fixtures; and the `DEC-037` scope exclusions were explicitly approved before coding.
- **Scope guard:** No Pick request creation, correction/reversal, later partial confirmation, Manager action, Pick idempotency key, FIFO/FEFO, reservation, scanner/device behavior, Supabase resource, deployment workflow, commit or push was added.
- **Verification boundary:** Fresh local commands produced Ruff lint/format PASS; pytest `113 passed, 3 PostgreSQL-only skipped`; frontend ESLint and TypeScript PASS, Vitest `30 passed`, production build PASS; and Playwright discovery listed 7 tests including 3 Pick scenarios. PostgreSQL 17/18 migration/concurrency execution and real browser E2E execution remain pending CI or an available local PostgreSQL environment; no pass is claimed for them.
- **Artifact references:** [`../vault/06-technical/story-specs/US-PICK-001.md`](../vault/06-technical/story-specs/US-PICK-001.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md), application files under `../apps/`, and [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
- **Human review:** Implementation diff and fresh evidence await human review. No commit, push or deployment was performed.

### AI-USE-021 — US-TRF-001 Technical Story Spec human-review finalization

- **Task:** Audit the current stock/application foundation, prepare an implementation-ready `US-TRF-001` Technical Story Spec, and synchronize the human-approved contract without writing application code or migrations.
- **AI support:** AI mapped all four canonical Transfer ACs to requirements, rules, decisions and NFRs; audited `StockBalance`, SKU/location ownership, Putaway idempotency, Pick deterministic locking, auth/error handling, frontend structure, design gaps, fixtures and Playwright; analyzed destination-row races, Transfer-vs-Transfer/Pick lock compatibility, no-effect guarantees and exact implementation slices; and separated proposals from unresolved boundaries for human review.
- **Human decisions:** Human approved an immutable durable Transfer with no edit/update/delete; correction/reversal outside the story; different source/destination enforced by API and database; same-transaction missing-destination creation with unique conflict protection; sorted location UUID balance locking compatible with Pick; atomic equal source decrement/destination increment; approved model fields/indexes; Warehouse Staff context GET and idempotent confirmation POST; Putaway-style `Idempotency-Key` safe replay and conflict semantics; typed errors and explicit feature exclusions. These decisions are recorded at `DEC-038`.
- **Scope guard:** No Transfer history/query from `US-TRF-002`, partial Transfer, correction/reversal, bulk/multi-SKU Transfer, FIFO/FEFO, reservation, scanner/device, auto-route, generic Movement, Warehouse-total persistence or application/migration change was added.
- **Open boundaries:** `OQ-012` remains open; integer quantity is current-slice only. `OQ-013` remains partially open beyond the approved immutable success/safe-retry and correction/reversal-outside-story boundary. `OQ-014` remains globally open; partial Transfer is `NOT IMPLEMENTED` in this slice, not permanently excluded. `OQ-022` remains open.
- **Verification boundary:** Documentation-only finalization. During the pre-review audit, the unchanged application baseline produced backend pytest `113 passed, 3 PostgreSQL-only skipped`, frontend Vitest `30 passed`, ESLint PASS, TypeScript PASS and production build PASS. No Transfer implementation, migration, PostgreSQL Transfer concurrency result or Transfer browser E2E evidence is claimed.
- **Artifact references:** [`../vault/06-technical/story-specs/US-TRF-001.md`](../vault/06-technical/story-specs/US-TRF-001.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`../vault/02-requirements/open-questions.md`](../vault/02-requirements/open-questions.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human review:** Human approved the implementation decisions and requested docs-only synchronization; implementation still requires normal code diff review and fresh test evidence. No commit or push was performed.

### AI-USE-022 — US-TRF-002 Technical Story Spec human-review finalization

- **Task:** Audit the durable Transfer implementation and canonical sources, prepare `US-TRF-002` for human review, then synchronize the approved implementation-ready history contract without application code, migration, commit or push.
- **AI support:** AI mapped the three canonical history ACs; audited the Transfer model, indexes, actor/SKU/location/time fields, execution API, authorization foundation, frontend structure, fixtures and Playwright setup; separated canonical behavior from query/UI proposals; and produced the exact API, no-effect tests, implementation slices and file plan for review.
- **Human decisions:** Human approved Manager-only backend-authoritative access; `401` for unauthenticated/invalid sessions and `403` for Warehouse Staff, Purchasing and Admin; server-resolved canonical single-Warehouse scope without client `warehouse_id`; `transferred_at DESC, id DESC`; no pagination, filters, search or export; exact `GET /api/v1/transfers` nested response and empty `200`; Manager table route `/transfers/history`; strict read-only guarantees; reuse of existing indexes with no migration. These decisions are recorded at `DEC-039`.
- **Scope guard:** No Transfer execution change, multi-Warehouse membership model, mutation/replay, edit/delete/reverse/rerun/detail action, pagination, filter, search, export, idempotency-field exposure, stock balance/snapshot response, new index or migration was added.
- **Open boundaries:** `OQ-013` remains `PARTIALLY DECIDED / OPEN` for broader Transfer failure/cancel/correction/reversal lifecycle. `OQ-022` remains open for barcode/QR, scanner, mobile/offline and external integration behavior.
- **Verification boundary:** Documentation-only finalization. The pre-review audit ran existing Transfer foundation checks only: backend Transfer component/migration tests `18 passed` and frontend Transfer execution tests `5 passed`. These are not history implementation evidence. No history code, migration, backend history test, frontend history test or browser history E2E result is claimed.
- **Artifact references:** [`../vault/06-technical/story-specs/US-TRF-002.md`](../vault/06-technical/story-specs/US-TRF-002.md), [`../vault/08-decisions/decision-log.md`](../vault/08-decisions/decision-log.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md).
- **Human review:** Human approved H1–H7 and requested docs-only synchronization. Implementation still requires normal code diff review and fresh verification. No commit or push was performed.

### AI-USE-023 — US-TRF-002 worktree implementation

- **Task:** Implement the human-approved `US-TRF-002` Transfer history contract across backend query/API, Manager authorization, frontend table states, automated tests, Playwright fixtures and traceability without migration, commit, push or deployment.
- **AI support:** AI added dedicated nested history response schemas; an exactly-one-Warehouse server resolver; an aliased SKU/source/destination/actor read query ordered by `transferred_at DESC, id DESC`; Manager-only GET routing; a `/transfers/history` table with loading/empty/error-retry/auth-recovery/real-403 states; deterministic history fixtures; no-effect state digests; and backend, frontend and browser scenarios.
- **Human decisions:** Human explicitly approved the one-Warehouse database invariant, real backend `403` flow for wrong roles, dedicated response safety boundary, `<time dateTime>` timestamp preservation and one-worker Playwright execution for the shared PostgreSQL database.
- **Scope guard:** No model/index/migration, Transfer execution change, stock query/response, idempotency exposure, mutation/replay, edit/delete/reverse/rerun/detail action, pagination, filter, search, export, multi-Warehouse membership, deployment, commit or push was added. `OQ-013` and `OQ-022` remain unchanged.
- **Verification boundary:** Fresh local evidence: Ruff lint/format PASS; pytest `142 passed, 9 PostgreSQL-only skipped`; frontend ESLint/TypeScript PASS, Vitest `46 passed`, production build PASS; Playwright discovery lists 14 tests including four `US-TRF-002` scenarios. Real browser execution is `NOT VERIFIED` because no local `TEST_DATABASE_URL` or Docker CLI is available; PostgreSQL-only tests remain skipped.
- **Artifact references:** [`../vault/06-technical/story-specs/US-TRF-002.md`](../vault/06-technical/story-specs/US-TRF-002.md), [`06-technical/story-specs-index.md`](06-technical/story-specs-index.md), [`TRACEABILITY.md`](TRACEABILITY.md), application files under `../apps/`.
- **Human review:** Implementation diff, table visual quality and PostgreSQL/browser evidence await human review. No commit, push or deployment was performed.
