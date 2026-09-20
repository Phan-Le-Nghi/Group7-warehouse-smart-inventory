# Traceability v7 — Requirements + NFR + Deployment Decision Baseline

Final backlog gồm 9 canonical stories đã được human approve. Active canonical inventory gồm 12 FR và 5 NFR; priority coverage là 100% cho active requirements theo `DEC-024` đến `DEC-026`. `CAND-REQ-004` được giữ làm lịch sử `SUPERSEDED / DECOMPOSED` và không được double-count. Human Product Decisions / MVP Assumptions không được ghi như verified evidence và không tạo `EVD-*` mới.

## Final Delivery release planning baseline

Theo human-approved `DEC-030`, cả 9 canonical stories được giữ trong Final Delivery release scope với priority planning `MUST`; quyết định này không thay đổi priority canonical của FR, không sửa canonical Acceptance Criteria và không resolve Open Question.

Implementation order được duyệt:

`US-PUT-001` completed baseline → `US-REC-001` → `US-PICK-001` → `US-TRF-001` → `US-TRF-002` → `US-AUD-001` → `US-AUD-002` → `US-ADJ-001` → `US-ADJ-002`.

Thứ tự này giữ Transfer execution trước Transfer history và Audit trước Adjust. `DEC-031/033` đã approve authentication design/spec; auth implementation đã merge và human-confirmed merged-PR evidence ghi nhận backend, frontend và Playwright E2E CI checks `PASS`. `DEC-034/035` approve Vercel frontend → Render FastAPI → Supabase PostgreSQL 17 cho staging/demo; deployment, staging HTTPS cookie behavior và PostgreSQL 17 release verification chưa thực hiện. Long-term production deployment target vẫn `TBD`.

## Product foundation

| Source | Requirement/rule | Story impact | Classification |
|---|---|---|---|
| `DEC-005` | One-Warehouse MVP | Tất cả workflow stories | HUMAN PRODUCT DECISION |
| `DEC-006`, `DEC-010` | `CAND-REQ-003`, `CAND-BR-003` | Putaway, Pick, Transfer, Audit, Adjust use per-location quantity | HUMAN PRODUCT DECISION |
| `DEC-008`, `DEC-009` | `system stock quantity`; Physical movement khác Movement system record; Putaway/Pick/Transfer boundaries | Putaway, Pick, Transfer và product vocabulary | HUMAN PRODUCT DECISION |
| `DEC-011` | `CAND-REQ-007`, `CAND-BR-004` | `US-PUT-001` | HUMAN PRODUCT DECISION |
| `DEC-012` | `CAND-REQ-006`, `CAND-BR-005/006` | `US-PICK-001` | HUMAN PRODUCT DECISION |
| `DEC-007`, `DEC-013`, `DEC-024` | `FR-012`, `FR-013`, `CAND-BR-007/008`; historical `CAND-REQ-004` superseded | `FR-012` → `US-TRF-001`; `FR-013` → `US-TRF-002` | HUMAN PRODUCT DECISION / APPROVED DECOMPOSITION |
| `DEC-014` | `CAND-REQ-005`, `CAND-BR-009/010` | `US-AUD-001`, `US-AUD-002` | HUMAN PRODUCT DECISION; `EVD-015/016` support current-state count/compare |
| `DEC-015` | `CAND-REQ-008`, `CAND-BR-011–013` | `US-ADJ-001`, `US-ADJ-002` | HUMAN PRODUCT DECISION; `EVD-012/013/017` support limited current-state context |
| `DEC-016` | `CAND-REQ-009`, `CAND-BR-014` | `US-REC-001` reference-mismatch AC | HUMAN PRODUCT DECISION |
| `DEC-017` | `CAND-REQ-010` | Actors and permissions across all stories | HUMAN PRODUCT DECISION |
| `DEC-018` | `REQ-002` interpretation | Receive may lead to Putaway; Pick/Transfer independent paths; Audit mismatch may lead to Adjust consideration after re-check | HUMAN PRODUCT DECISION |
| `DEC-019` | `CAND-REQ-011`, `CAND-BR-015` | Negative-stock guards in `US-PICK-001`, `US-TRF-001`, `US-ADJ-002` | HUMAN PRODUCT DECISION; resolves `OQ-015` |
| `DEC-025`, `DEC-026` | `NFR-001` đến `NFR-005`; canonical priority schema | Supported stories/artifacts theo NFR trace bên dưới | HUMAN APPROVED NFR / PRIORITY DECISION; `OQ-033` partially addressed |

## Technical foundation decisions

| Decision / ADR | Technical contract | Story impact | Boundary |
|---|---|---|---|
| `DEC-020` | React + TypeScript + Vite/npm; Python 3.13 + FastAPI/uv/pytest; PostgreSQL/Docker; SQLAlchemy 2/Alembic; Playwright; modular monolith | Foundation for all future implementation; first slice `US-PUT-001` | PostgreSQL 18 remains local/CI compatibility evidence; `DEC-035` supersedes only an all-environment exact-major interpretation and requires PostgreSQL 17+ compatibility |
| `DEC-021` / `ADR-001` | Per-location stock is authoritative; Warehouse total is derived; no `warehouse_totals` | `US-PUT-001`, Pick, Transfer, Audit, Adjust | Does not add stock buckets |
| `DEC-022` / `ADR-002` | PostgreSQL transaction boundary, row locking when needed, application + DB non-negative guard | `NFR-001/002`; all stock-changing operations | Does not define retry/cancel, reservation semantics or load target |
| `DEC-023` / `ADR-003` | Receive records actual quantity; Putaway performs initial posting; Putaway idempotency | `US-REC-001`, `US-PUT-001`, `NFR-003` | Does not resolve `OQ-013` or `OQ-014`; idempotency retention window TBD |
| `DEC-031` / `DEC-033` | PostgreSQL-backed server-side sessions; approved exact schema; 8-hour absolute session; hashed random token; configurable secure cookie/CORS; Argon2id; database-role actor resolution; approved 401/403 semantics | `NFR-004`; protected operations across all stories; auth API baseline | Implementation merged; human-confirmed merged-PR backend/frontend/E2E CI checks PASS; staging HTTPS cookie behavior remains unverified |
| `DEC-032` / `DEC-034` | Retain staging/demo-only public HTTPS, external secrets, migration/readiness/seed/smoke and no-`--reload`; replace Render Static Site/DB with Vercel same-origin `/api/*` rewrite and Supabase PostgreSQL while retaining Render FastAPI | Release/staging environment for the MVP | APPROVED DESIGN only; deployment not performed; Render Free requires demo warm-up/rehearsal; long-term production target remains TBD |
| `DEC-035` | Supabase PostgreSQL 17 staging target; PostgreSQL 17+ compatibility; TLS `sslmode=require`; Alembic single-runner policy and staging-compatible release verification | Persistence/release evidence across implemented stories | PostgreSQL 18 CI evidence remains valid but does not replace PostgreSQL 17 staging verification or prove major versions identical |

## Canonical NFR trace

| NFR | Priority | Supported story/artifact | Verification evidence / boundary |
|---|---|---|---|
| `NFR-001` — atomic stock mutation | MUST | `US-PUT-001`, `US-PICK-001`, `US-TRF-001`, `US-ADJ-002`; `ADR-002` | No partial write on tested failure paths; no broader implementation claim |
| `NFR-002` — consistency under concurrency | MUST | Same stock-changing stories; `ADR-002` | Concurrency tests required when conflicting/multi-row commands are implemented; no load/user target |
| `NFR-003` — Putaway idempotency | SHOULD | `US-PUT-001` → Technical Story Spec → `TEST-PUT-003` | Existing test verifies same key/payload produces no second allocation/increment; Putaway Round 1 only; retention TBD |
| `NFR-004` — authorization enforcement | MUST | Approved role outcomes across protected stories; `DEC-031/033` session/auth boundary | Merged implementation includes DB actor resolution and role tests; dependency override is automated-test-only. CI checks pass; staging HTTPS cookie behavior remains unverified |
| `NFR-005` — Pick status clarity | SHOULD | `US-PICK-001` → `PF-02` → human-reviewed P2 usability finding | UI/state/copy review and existing usability evidence; no numeric threshold |

## Repo scaffold / CI baseline

| Status | Artifact path | Verification evidence | Scope boundary |
|---|---|---|---|
| Completed; `US-PUT-001` merged and accepted after human review | `apps/frontend/`, `apps/backend/`, `apps/docker/`, `apps/.env.example`, `apps/README.md`, `.github/workflows/ci.yml` | Baseline verification is recorded in `AI-USE-006`; PostgreSQL 18 and E2E CI evidence for the slice is listed below | No Vercel/Render/Supabase deployment is claimed |
| Auth implementation merged and CI verified | `apps/backend/src/warehouse_api/auth*`, `apps/backend/alembic/versions/20260919_0002_auth_session_foundation.py`, `apps/frontend/src/AuthGate.tsx`, supporting config/tests/docs | 2026-09-20 local checks PASS as previously recorded; human-confirmed merged-PR evidence records backend, frontend and browser E2E CI checks PASS on PostgreSQL 18 | Staging HTTPS cookie behavior and PostgreSQL 17/Supabase verification remain pending; deployment is not implemented |

## US-PUT-001 vertical-slice implementation

| Requirement / Story / delivery trace | Implementation artifact | Test IDs and current evidence | Scope boundary |
|---|---|---|---|
| `REQ-002/003/004`, `CAND-REQ-003/007/010` → `US-PUT-001` → Taiga [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) → tasks [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19)/[#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20)/[#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) → `PF-01` / `SCR-03` → Technical Story Spec | React Putaway UI; `POST /api/v1/putaways`; Putaway context read; actor dependency boundary; SQLAlchemy models; Alembic `20260905_0001` | `TEST-PUT-001`…`TEST-PUT-005`: PASS on PostgreSQL 18 in `backend-checks`; frontend lint/typecheck/test/build: PASS in `frontend-checks`; `TEST-PUT-E2E-001`: PASS in `putaway-e2e` through React → FastAPI → PostgreSQL 18 | No Transfer/Movement table or write path verified by `TEST-PUT-005`; duplicate replay does not double-count verified by `TEST-PUT-003`; no persisted Warehouse total; Receive actual unchanged; full 16-unit placement is fixture scope only; `OQ-012/013/014` remain open |

Local evidence on 2026-09-05 remains: Ruff lint and format-check pass; pytest `8 passed` on the SQLite component database; frontend ESLint, TypeScript, Vitest `3 passed`, and Vite build pass; Alembic upgrade/downgrade smoke pass on a temporary SQLite database. Post-merge GitHub Actions evidence confirms successful push and pull-request runs: `backend-checks` passed migration and backend tests on PostgreSQL 18, `frontend-checks` passed lint/typecheck/test/build, and `putaway-e2e` passed the real-browser React → FastAPI → PostgreSQL 18 slice. These CI results are not presented as local Docker execution.

## Canonical story coverage

| Story | Requirement | Business Rule | Decision | Evidence classification | OQ boundary |
|---|---|---|---|---|---|
| `US-REC-001` | `REQ-001/002/003`, `CAND-REQ-001/002/009/010` | `CAND-BR-001/014` | `DEC-016/017/018` | `EVD-002–005` verify actual-vs-expected behavior; later additions are HUMAN PRODUCT DECISIONS | `OQ-013` final completion/handoff; `OQ-014`, `OQ-022` open |
| `US-PUT-001` | `REQ-002/003/004`, `CAND-REQ-003/007/010` | `CAND-BR-003/004` | `DEC-006/010/011/017` | HUMAN PRODUCT DECISION; `EVD-006/007` context only | `OQ-013` exception/handoff; `OQ-014`, `OQ-022` open |
| `US-PICK-001` | `REQ-002/003`, `CAND-REQ-003/006/010/011` | `CAND-BR-003/005/006/015` | `DEC-010/012/017/018/019` | HUMAN PRODUCT DECISION; `EVD-006–009` context only | `OQ-013` cancellation/retry; `OQ-022` open; negative-stock guard approved |
| `US-TRF-001` | `REQ-001/002/004`, `CAND-REQ-003/010/011`, `FR-012` | `CAND-BR-003/007/008/015` | `DEC-005/007/009/010/013/017/018/019/024` | HUMAN PRODUCT DECISION; `EVD-010/011` context only | `OQ-013` failure/cancel/reversal; `OQ-014/022` open; negative-stock guard approved |
| `US-TRF-002` | `REQ-002/003/004`, `FR-013`, `CAND-REQ-010` | `CAND-BR-008` | `DEC-013/017/024` | HUMAN PRODUCT DECISION; `EVD-010/011` context only | `OQ-013`, `OQ-022` remain open |
| `US-AUD-001` | `REQ-002/004`, `CAND-REQ-003/005/010` | `CAND-BR-003/009` | `DEC-010/014/017` | Verified evidence `EVD-015/016` + HUMAN PRODUCT DECISION | `OQ-013` mismatch completion/schedule; `OQ-022` open |
| `US-AUD-002` | `REQ-002/004`, `CAND-REQ-005/010` | `CAND-BR-002/010` | `DEC-014/017` | Verified evidence `EVD-012/017` + HUMAN PRODUCT DECISION | `OQ-013` mismatch closure open |
| `US-ADJ-001` | `REQ-001/002/003`, `CAND-REQ-008/010` | `CAND-BR-002/011/012` | `DEC-015/017/018` | Verified evidence `EVD-012/013/017` + HUMAN PRODUCT DECISION | `OQ-013`; this story does not apply quantity |
| `US-ADJ-002` | `REQ-001/002/003`, `CAND-REQ-003/008/010/011` | `CAND-BR-002/011/013/015` | `DEC-010/015/017/018/019` | Verified evidence `EVD-012/013/017` + HUMAN PRODUCT DECISION | `OQ-013` rejected closure; negative-stock guard approved |

## Story-to-AC mapping

| Story | Canonical AC coverage | Downstream status |
|---|---|---|
| `US-REC-001` | actual entry/compare; match; quantity discrepancy; reference mismatch review | Design/spec/implementation/test not started |
| `US-PUT-001` | destination allocation; tracked location; no automatic Movement record | Implementation COMPLETED; PostgreSQL 18 backend verification, frontend checks and Playwright E2E PASS in GitHub Actions; accepted after human diff review |
| `US-PICK-001` | full Pick; multi-location; `PARTIAL / INSUFFICIENT`; negative-stock guard | Not started |
| `US-TRF-001` | source/destination effects; Warehouse total; minimum record; negative-stock guard | Technical contract still TBD |
| `US-TRF-002` | Manager history access; history fields; confirmation time | Technical contract still TBD |
| `US-AUD-001` | selected scope; count/compare; result; match completion | Not started |
| `US-AUD-002` | discrepancy context; mandatory re-check; no auto Adjust | Not started |
| `US-ADJ-001` | request/reason; re-check; optional attachment; no pre-decision change | Not started |
| `US-ADJ-002` | approve/apply; reject/no change; no-discrepancy/no change; negative-stock guard | Not started |

## Requirement → Canonical Story → Taiga → Design/Prototype → Implementation/Test

Taiga references dưới đây theo dõi thực thi và không thay thế nguồn yêu cầu canonical. Trạng thái implementation/test không được suy ra từ trạng thái Taiga.

| Requirement | Canonical Story | Taiga Story | Taiga Tasks | Design/Prototype | Implementation/Test status |
|---|---|---|---|---|---|
| `REQ-001/002/003`, `CAND-REQ-001/002/009/010` | `US-REC-001` | [#7](https://tree.taiga.io/project/lenghi-group-07-project/us/7) / ID `9523822` — Ready | `T-REC-01` [#16](https://tree.taiga.io/project/lenghi-group-07-project/task/16); `T-REC-02` [#17](https://tree.taiga.io/project/lenghi-group-07-project/task/17); `T-REC-03` [#18](https://tree.taiga.io/project/lenghi-group-07-project/task/18) — New | `PF-01 — Receive → Putaway`; 10 wireframe states và 10 prototype counterparts human verified | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-002/003/004`, `CAND-REQ-003/007/010` | `US-PUT-001` | [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) / ID `9523823` — Done | `T-PUT-01` [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19) — Done; `T-PUT-02` [#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20) — Done; `T-PUT-03` [#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) — Done | `PF-01 — Receive → Putaway`; `SCR-03`; [`06-technical/story-specs/putaway.md`](06-technical/story-specs/putaway.md) | COMPLETED; API/DB/migration/UI merged; PostgreSQL 18 backend, frontend and Playwright E2E checks PASS in GitHub Actions |
| `REQ-002/003`, `CAND-REQ-003/006/010/011` | `US-PICK-001` | [#9](https://tree.taiga.io/project/lenghi-group-07-project/us/9) / ID `9523824` — Ready | `T-PICK-01` [#22](https://tree.taiga.io/project/lenghi-group-07-project/task/22); `T-PICK-02` [#23](https://tree.taiga.io/project/lenghi-group-07-project/task/23); `T-PICK-03` [#24](https://tree.taiga.io/project/lenghi-group-07-project/task/24) — New | `PF-02 — Pick`; 7 wireframe states và 7 prototype counterparts human verified | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-001/002/004`, `CAND-REQ-003/010/011`, `FR-012` | `US-TRF-001` | [#10](https://tree.taiga.io/project/lenghi-group-07-project/us/10) / ID `9523825` — New | `T-TRF1-01` [#25](https://tree.taiga.io/project/lenghi-group-07-project/task/25); `T-TRF1-02` [#26](https://tree.taiga.io/project/lenghi-group-07-project/task/26); `T-TRF1-03` [#27](https://tree.taiga.io/project/lenghi-group-07-project/task/27) — New | Consolidated User Flow; technical contract vẫn TBD | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-002/003/004`, `FR-013`, `CAND-REQ-010` | `US-TRF-002` | [#11](https://tree.taiga.io/project/lenghi-group-07-project/us/11) / ID `9523826` — New | `T-TRF2-01` [#28](https://tree.taiga.io/project/lenghi-group-07-project/task/28); `T-TRF2-02` [#29](https://tree.taiga.io/project/lenghi-group-07-project/task/29); `T-TRF2-03` [#30](https://tree.taiga.io/project/lenghi-group-07-project/task/30) — New | Consolidated User Flow; technical contract vẫn TBD | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-002/004`, `CAND-REQ-003/005/010` | `US-AUD-001` | [#12](https://tree.taiga.io/project/lenghi-group-07-project/us/12) / ID `9523827` — Ready | `T-AUD1-01` [#31](https://tree.taiga.io/project/lenghi-group-07-project/task/31); `T-AUD1-02` [#32](https://tree.taiga.io/project/lenghi-group-07-project/task/32); `T-AUD1-03` [#33](https://tree.taiga.io/project/lenghi-group-07-project/task/33) — New | `PF-03 — Audit → Adjust`; 14 wireframe states và 14 prototype counterparts human verified cho flow group | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-002/004`, `CAND-REQ-005/010` | `US-AUD-002` | [#13](https://tree.taiga.io/project/lenghi-group-07-project/us/13) / ID `9523828` — Ready | `T-AUD2-01` [#34](https://tree.taiga.io/project/lenghi-group-07-project/task/34); `T-AUD2-02` [#35](https://tree.taiga.io/project/lenghi-group-07-project/task/35); `T-AUD2-03` [#36](https://tree.taiga.io/project/lenghi-group-07-project/task/36) — New | `PF-03 — Audit → Adjust`; human-verified flow group evidence | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-001/002/003`, `CAND-REQ-008/010` | `US-ADJ-001` | [#14](https://tree.taiga.io/project/lenghi-group-07-project/us/14) / ID `9523829` — Ready | `T-ADJ1-01` [#37](https://tree.taiga.io/project/lenghi-group-07-project/task/37); `T-ADJ1-02` [#38](https://tree.taiga.io/project/lenghi-group-07-project/task/38); `T-ADJ1-03` [#39](https://tree.taiga.io/project/lenghi-group-07-project/task/39) — New | `PF-03 — Audit → Adjust`; human-verified flow group evidence | Chưa bắt đầu / Chưa bắt đầu |
| `REQ-001/002/003`, `CAND-REQ-003/008/010/011` | `US-ADJ-002` | [#15](https://tree.taiga.io/project/lenghi-group-07-project/us/15) / ID `9523830` — Ready | `T-ADJ2-01` [#40](https://tree.taiga.io/project/lenghi-group-07-project/task/40); `T-ADJ2-02` [#41](https://tree.taiga.io/project/lenghi-group-07-project/task/41); `T-ADJ2-03` [#42](https://tree.taiga.io/project/lenghi-group-07-project/task/42) — New | `PF-03 — Audit → Adjust`; human-verified flow group evidence | Chưa bắt đầu / Chưa bắt đầu |

## OQ decision trace

| OQ | Current status | Decision/impact |
|---|---|---|
| `OQ-012` | OPEN QUESTION | Integer quantity remains a Round 1 slice simplification; UOM, decimal quantity, conversion behavior and precision/scale remain undecided |
| `OQ-011` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-010–015`; per-location `system stock quantity` |
| `OQ-013` | PARTIALLY DECIDED / OPEN | Receive completion/handoff, Putaway exception/handoff, Transfer exception/reversal, Audit mismatch completion and Adjust rejected-case closure remain open |
| `OQ-017` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-014/015` |
| `OQ-018` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-014` |
| `OQ-019` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-016/017` |
| `OQ-020` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-017` |
| `OQ-015` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-019`; location quantity cannot be negative; no retry/cancel semantics inferred |
| `OQ-014`, `OQ-021`, `OQ-022` | OPEN QUESTION | Partial workflow, Alert and device/integration behavior remain undecided |
| `OQ-032` | PARTIALLY RESOLVED / OPEN | `DEC-031/033` approve session auth; `DEC-034/035` approve Vercel → Render → Supabase PostgreSQL 17 for staging/demo; long-term production deployment remains TBD |
| `OQ-033` | PARTIALLY DECIDED / OPEN | `NFR-001` đến `NFR-005`, priorities and minimum staging/demo release environment are approved; response-time, uptime, concurrent-user/load target, numeric usability threshold, idempotency retention and long-term production operating context remain open |

AI-related OQs remain unchanged and are future/open directions, not canonical MVP requirements.

## Product Definition artifact mapping

| Artifact | Coverage | Canonical source |
|---|---|---|
| [`03-product/PRD.md`](03-product/PRD.md) | Product overview, scope, workflows, requirements, rules, stories, permissions, OQs, success criteria | Requirements, Business Rules, Domain, Decisions, canonical stories |
| [`03-product/mvp-scope.md`](03-product/mvp-scope.md) | IN MVP / OUT OF MVP / OPEN with ID-level trace | Requirements, Decisions, OQs |
| [`03-product/user-flow.md`](03-product/user-flow.md) | Independent Pick/Transfer paths; selected-scope Audit; discrepancy/re-check/Adjust relationship; negative-stock guards | `DEC-018/019`, canonical stories and AC |
| [`04-backlog/user-stories.md`](04-backlog/user-stories.md) | Report-facing summary of 9 canonical stories | `vault/04-product/stories/` |
| [`05-design/screen-inventory.md`](05-design/screen-inventory.md) | 10 logical base screens; 31 wireframe states; 31 prototype counterparts; 3 critical flows | Canonical stories, consolidated flow, human-reviewed usability decisions and direct human Figma verification |
| [`05-design/usability-test-script.md`](05-design/usability-test-script.md) | Task script for `P1`/`P2`/`P3` | Canonical stories and approved flow boundaries |
| [`05-design/usability-findings.md`](05-design/usability-findings.md) | Human-reviewed Observation → Issue → Decision findings | Findings supplied by human reviewer; no new Requirement/BR |

## Prototype → usability traceability

Các “Usability Decision” dưới đây là decision cục bộ của artifact về wording, state visibility hoặc prototype transition. Chúng không phải Requirement/Business Rule mới và không được gán `DEC-*` mới vì không thay đổi product behavior canonical.

| Prototype Flow | Story | Usability Finding | Usability Decision | Existing canonical decision |
|---|---|---|---|---|
| `PF-01 — Receive → Putaway` | `US-REC-001`, `US-PUT-001` | `P1`: expected/actual và discrepancy rõ; completion sau reference review và boundary sang Putaway chưa rõ | Giữ hai flow tách biệt; không production CTA tự động; prototype chỉ dùng facilitator transition | `DEC-016`, `DEC-018`; `OQ-013` vẫn mở |
| `PF-02 — Pick` | `US-PICK-001` | `P2`: multi-location/full/blocked rõ; partial có thể bị hiểu là fully completed | Giữ partial hợp lệ; thêm copy “Pick is not fully completed. 4 units remain unfulfilled.”; giữ blocked/no-change guard | `DEC-012`, `DEC-019` |
| `PF-03 — Audit → Adjust` | `US-AUD-001`, `US-AUD-002`, `US-ADJ-001`, `US-ADJ-002` | `P3`: mismatch và re-check rõ; thời điểm quantity đổi qua actor handoff chưa rõ | Hiển thị no-change sau mismatch/re-check/waiting/reject; chỉ approved/applied mới cập nhật quantity | `DEC-014`, `DEC-015`, `DEC-018`, `DEC-019` |

## Decomposition record

- `DRAFT-US-PUT-001` was promoted to `US-PUT-001`.
- `DRAFT-US-PICK-001` was promoted to `US-PICK-001`; insufficient Pick remains an AC/scenario.
- `DRAFT-US-TRF-001` was split into `US-TRF-001` and `US-TRF-002`.
- `DRAFT-US-AUD-001` was split into `US-AUD-001` and `US-AUD-002`.
- `DRAFT-US-ADJ-001` was split into `US-ADJ-001` and `US-ADJ-002`.
- Receive reference mismatch remains an AC/scenario in `US-REC-001`.

Historical draft references are valid only when explicitly labeled as promoted, split, historical or superseded.

## Downstream status

| Artifact | Current truthful status |
|---|---|
| Canonical stories | 9 HUMAN APPROVED stories |
| Historical drafts | Superseded; not active backlog items |
| PRD / MVP Scope | Baseline for Report Round 1; open questions preserved |
| Report user flow | Consolidated flow updated; independent operational paths and lifecycle gaps preserved |
| Design/Figma/Prototype | **PARTIAL overall**: browser access và 8 pages human verified; Design System foundations PASS; reusable components PASS/PARTIAL; 31 wireframe states, 31 prototype counterparts, 3 critical flows và 6 `FACILITATOR ONLY` items verified. High Fidelity và Dev Handoff trống; exact hotspot total/full wiring chưa verify. MCP page inventory là INCOMPLETE / NON-AUTHORITATIVE. |
| Usability artifacts | Script và 3 human-reviewed findings đã được tổng hợp; không claim AI thực hiện participant test |
| Taiga | Project metadata và 6 Epic / 9 User Story / 27 Task references đã đồng bộ; quyền truy cập/người phụ trách công cụ vẫn TBD |
| Architecture/Data Model/API | Technical Foundation human reviewed; 3 accepted ADR; merged auth implementation; Vercel → Render → Supabase deployment remains approved design only |
| Implementation/Test | Repo scaffold, `US-PUT-001` and auth implementation merged; human-confirmed PostgreSQL 18 backend, frontend and React → FastAPI → PostgreSQL 18 Playwright CI checks PASS; PostgreSQL 17 staging verification and deployment remain pending; no local Docker pass is claimed |
