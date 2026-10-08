# Traceability v12 — Staging/Demo Release Evidence Baseline

Final backlog gồm 9 canonical stories đã được human approve. Active canonical inventory gồm 12 FR và 5 NFR; priority coverage là 100% cho active requirements theo `DEC-024` đến `DEC-026`. `CAND-REQ-004` được giữ làm lịch sử `SUPERSEDED / DECOMPOSED` và không được double-count. Human Product Decisions / MVP Assumptions không được ghi như verified evidence và không tạo `EVD-*` mới.

## Final Delivery release planning baseline

Theo human-approved `DEC-030`, cả 9 canonical stories được giữ trong Final Delivery release scope với priority planning `MUST`; quyết định này không thay đổi priority canonical của FR, không sửa canonical Acceptance Criteria và không resolve Open Question.

Implementation order được duyệt:

`US-PUT-001` completed baseline → `US-REC-001` → `US-PICK-001` → `US-TRF-001` → `US-TRF-002` → `US-AUD-001` → `US-AUD-002` → `US-ADJ-001` → `US-ADJ-002`.

Thứ tự này giữ Transfer execution trước Transfer history và Audit trước Adjust. `DEC-031/033` đã approve authentication design/spec. Cả 9 Must stories và auth đã merged tại release candidate `664d207`. `DEC-034/035` staging/demo topology đã deploy tại Vercel frontend → Render FastAPI → Supabase PostgreSQL 17; human-performed staging smoke đã PASS runtime, DB readiness, SPA refresh, auth/session/logout và 9 story flows. Exact GitHub Actions run URL/results cho `664d207`, cookie-attribute inspection và `alembic current` transcript không được ghi nhận. Long-term production deployment target vẫn `TBD`.

## Staging/demo release verification

Primary release evidence: commit `664d207`, working tree clean tại thời điểm
verification, [frontend Vercel](https://group7-warehouse-smart-inventory.vercel.app),
[backend Render](https://group7-warehouse-smart-inventory.onrender.com), `/health`
PASS, `/ready` PASS và
[human-performed staging smoke checklist](07-release/STAGING-DEMO-RELEASE-CHECKLIST.md).
Screenshots không phải primary release artifact. Exact CI run của commit release
không được ghi nhận và không được suy ra từ CI của commit cũ. Đây là staging/demo
release, không phải production-grade claim.

## Role-based product discovery worktree

Human approved the product discovery queue phase on 2026-10-08. The current
worktree keeps `/` as the authenticated role-based Dashboard and gives Warehouse
Staff six real entry points: Receive, Putaway, Pick, Transfer, New Audit and
Adjust Requests. Receive and Putaway now use read-only queues; Pick uses an
`outcome IS NULL` queue; Transfer uses a positive-stock selector with current
tracked-location quantities. Queue selection creates the existing exact-context
URL, so users do not supply UUIDs. Purchasing/Admin remain unchanged.

The four discovery APIs and pages add no model, migration, transaction effect,
Receive/Pick create lifecycle, retry/reopen behavior, public reset or automatic
Receive-to-Putaway handoff. `FULLY_COMPLETED` and `PARTIAL_INSUFFICIENT` Picks
stay outside the actionable queue. Exact-context transaction routes remain
authoritative and action pages now link back to their queue/selector. Verification
evidence for this uncommitted worktree: backend Ruff lint/format PASS and pytest
`269 passed, 32 PostgreSQL-only skipped`; frontend ESLint/TypeScript PASS, Vitest
`101 passed`, production build PASS, Vercel config `4 passed`, Playwright
discovery `37 tests`, and `git diff --check` PASS. `TEST_DATABASE_URL` is unset
and Docker is unavailable, so PostgreSQL/Chromium execution is not claimed.

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
| `DEC-036` | `US-REC-001` implementation contract | `RECEIVE_RECORDED`; minimum expected context; Warehouse Staff mismatch acknowledgement; Putaway eligibility gate; duplicate conflict; legacy-safe migration; no stock/auto-Putaway effect | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; does not close `OQ-013/014` |
| `DEC-037` | `US-PICK-001` implementation contract | One immutable `FULLY_COMPLETED` or `PARTIAL_INSUFFICIENT` result; explicit unique source allocations; atomic locked source decrements; typed duplicate conflict; approved data/API/UI boundaries | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; preserves `OQ-012/022` and future retry/Manager-review boundaries |
| `DEC-038` | `US-TRF-001` implementation contract | Immutable durable Transfer; different same-Warehouse locations; atomic source/destination effects; transactional missing-destination creation; sorted UUID locks; explicit idempotent retry; approved data/API/error boundaries | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; preserves `OQ-012`, remaining `OQ-013`, global `OQ-014` and `OQ-022`; history remains `US-TRF-002` |
| `DEC-039` | `US-TRF-002` implementation contract | Manager-only confirmed history for the server-resolved single MVP Warehouse; exact read response; `transferred_at DESC, id DESC`; no pagination/filter; table UI; strict no-effect guarantee | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; reuses `US-TRF-001` records/indexes with no migration; preserves broader Transfer lifecycle at `OQ-013` and device/integration at `OQ-022` |
| `DEC-040` | `US-AUD-001` implementation contract | One session/many unique pair lines; selected pairs and current SKU × tracked-location whole-Warehouse scope; submit-time stock snapshot; missing balance zero; strict integer; persisted signed discrepancy; match/mismatch statuses; Staff-only idempotent API; strict no-stock-effect guarantee | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; preserves global `OQ-012`, broader Audit lifecycle/recheck/correction at `OQ-013` and device/integration at `OQ-022`; Manager review remains `US-AUD-002` |
| `DEC-041` | `US-AUD-002` implementation contract | Manager-only per-`audit_line_id` mismatch list/detail/recheck; current-stock submit snapshot; separate exactly-one `audit_rechecks`; strict integer; atomic historical replay; immutable original Audit; Adjust-eligibility context only; strict no-effect guarantee | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; preserves global `OQ-012`, Audit close/resolve/correction/reversal at `OQ-013` and device/integration at `OQ-022`; no Adjust creation/application |
| `DEC-042` | `US-ADJ-001` implementation contract | Staff-only exact recheck context and Adjust creation; exact `MISMATCH` eligibility; backend-derived source snapshots and signed change; required normalized reason; exactly one request per recheck; `PENDING_MANAGER_DECISION`; atomic historical replay; strict no-stock-effect guarantee | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; deferred Manager decision/apply to `US-ADJ-002`, now approved at `DEC-043`; preserves global `OQ-012`, broader lifecycle at `OQ-013`, device/integration at `OQ-022`, and attachment storage/provider/policy as OPEN/TBD |
| `DEC-043` | `US-ADJ-002` implementation contract | Manager-only pending queue/exact detail/decision; immutable full requested change; request/balance locks; snapshot-match then current-plus-delta apply; safe zero-balance materialization; `APPLIED/REJECTED`; required reject reason; before/after evidence; separate atomic decision replay | HUMAN APPROVED TECHNICAL IMPLEMENTATION SPEC; decides current Adjust apply/reject/stale/negative/post-reject lifecycle while preserving global `OQ-012`, broader Audit correction/reversal at `OQ-013`, `OQ-022` and attachment boundary |
| `DEC-044` | `US-ADJ-001` Staff handoff clarification | Staff-only read-only eligible mismatch-recheck queue; excludes existing requests; newest-first deterministic order; generic `/adjustments` discovery then exact context/create | HUMAN APPROVED SCOPE CLARIFICATION; no Manager create, auto-create, role switch, stock effect, migration, authorization relaxation or attachment implementation |
| `DEC-025`, `DEC-026` | `NFR-001` đến `NFR-005`; canonical priority schema | Supported stories/artifacts theo NFR trace bên dưới | HUMAN APPROVED NFR / PRIORITY DECISION; `OQ-033` partially addressed |

## Technical foundation decisions

| Decision / ADR | Technical contract | Story impact | Boundary |
|---|---|---|---|
| `DEC-020` | React + TypeScript + Vite/npm; Python 3.13 + FastAPI/uv/pytest; PostgreSQL/Docker; SQLAlchemy 2/Alembic; Playwright; modular monolith | Foundation for all future implementation; first slice `US-PUT-001` | PostgreSQL 18 remains local/CI compatibility evidence; `DEC-035` supersedes only an all-environment exact-major interpretation and requires PostgreSQL 17+ compatibility |
| `DEC-021` / `ADR-001` | Per-location stock is authoritative; Warehouse total is derived; no `warehouse_totals` | `US-PUT-001`, Pick, Transfer, Audit, Adjust | Does not add stock buckets |
| `DEC-022` / `ADR-002` | PostgreSQL transaction boundary, row locking when needed, application + DB non-negative guard | `NFR-001/002`; all stock-changing operations | Does not define retry/cancel, reservation semantics or load target |
| `DEC-023` / `ADR-003` | Receive records actual quantity; Putaway performs initial posting; Putaway idempotency | `US-REC-001`, `US-PUT-001`, `NFR-003` | Does not resolve `OQ-013` or `OQ-014`; idempotency retention window TBD |
| `DEC-031` / `DEC-033` | PostgreSQL-backed server-side sessions; approved exact schema; 8-hour absolute session; hashed random token; configurable secure cookie/CORS; Argon2id; database-role actor resolution; approved 401/403 semantics | `NFR-004`; protected operations across all stories; auth API baseline | Implementation merged; human staging smoke PASS for login/session persistence/logout; exact cookie attributes and exact CI run for `664d207` not recorded |
| `DEC-032` / `DEC-034` | Retain staging/demo-only public HTTPS, external secrets, migration/readiness/seed/smoke and no-`--reload`; replace Render Static Site/DB with Vercel same-origin `/api/*` rewrite and Supabase PostgreSQL while retaining Render FastAPI | Release/staging environment for the MVP | DEPLOYED / HUMAN STAGING SMOKE PASS at `664d207`; Render Free requires demo warm-up/rehearsal; long-term production target remains TBD |
| `DEC-035` | Supabase PostgreSQL 17 staging target; PostgreSQL 17+ compatibility; TLS `sslmode=require`; Alembic single-runner policy and staging-compatible release verification | Persistence/release evidence across implemented stories | `/ready` and persisted workflow smoke PASS; exact PostgreSQL version query and `alembic current` transcript not recorded; PostgreSQL 18 historical CI does not prove major versions identical |
| `DEC-036` | Receive records a full prepared context atomically; mismatch acknowledgement controls Putaway eligibility; no fabricated legacy backfill | `US-REC-001` implementation and downstream `US-PUT-001` eligibility guard | No final completion/handoff, partial Receive, correction/reversal, PO lifecycle or Receive stock mutation |
| `DEC-037` | Pick uses `pick_requests` + `pick_allocations`, explicit Warehouse Staff allocation, deterministic row locking, derived picked/remaining quantity and approved GET/POST routes | `US-PICK-001`, `NFR-001/002/004/005` | No request creation, correction/reversal, later partials, Pick idempotency framework, Manager endpoint, auto-allocation, FIFO/FEFO/reservation or device flow |
| `DEC-038` | Transfer uses an immutable durable `transfers` row with actor/time and transactional idempotency fields; creates a missing destination balance in the same transaction; locks all affected balances in sorted location UUID order; exposes approved context GET and idempotent confirmation POST | `US-TRF-001`, `NFR-001/002/004` | No history/query, partial Transfer, correction/reversal, bulk/multi-SKU, generic Movement, FIFO/FEFO/reservation, scanner/device or auto-route; integer is current-slice only |
| `DEC-039` | Transfer history reads the existing durable rows through Manager-only `GET /api/v1/transfers`, server-enforced single-Warehouse scope and deterministic newest-first order; response excludes idempotency and stock fields | `US-TRF-002`, `NFR-004` | No mutation, replay, correction/reversal, pagination, filter, search, export, detail action, multi-Warehouse membership model, migration or new index |
| `DEC-040` | Audit uses `audit_sessions` + `audit_lines`, server-resolved Warehouse, submit-time set-based stock snapshot, Audit-specific atomic idempotency claim and `/audits/new` UI | `US-AUD-001`, `NFR-004` | No stock mutation, Manager workflow, recheck, Adjust, history/filter, generic workflow/idempotency framework, scanner/device or AI; integer is current-slice only |
| `DEC-041` | Audit discrepancy review uses `audit_line_id` identity and separate `audit_rechecks`; Manager-only current-stock snapshot, exactly-one constraint and Audit-recheck-specific atomic replay; `/audit-discrepancies` UI | `US-AUD-002`, `NFR-004` | No original Audit mutation, stock mutation, repeated/session-batch recheck, Adjust creation/application, generic workflow/idempotency framework, scanner/device or AI; integer is current-slice only |
| `DEC-042/044` | Adjust request uses required unique `audit_recheck_id`; Staff eligible queue discovers mismatch rechecks without requests; exact create snapshots source SKU/location and recheck quantities, derives signed change and uses required Adjust-specific atomic idempotency | `US-ADJ-001`, `NFR-004` | No create-time stock read/stale conflict, attachment I/O, Staff history/generic request detail, Manager create, stock mutation, generic workflow/idempotency framework, scanner/device or AI |
| `DEC-043` | Manager decision uses separate required idempotency; locks request then exact balance; stale/negative validation and terminal evidence share the stock transaction | `US-ADJ-002`, `NFR-001/002/004` | No current-stock preview, editable/partial quantity, reopen/recreate, generic workflow/ledger/locking framework, scanner/device or AI |

## Canonical NFR trace

| NFR | Priority | Supported story/artifact | Verification evidence / boundary |
|---|---|---|---|
| `NFR-001` — atomic stock mutation | MUST | `US-PUT-001`, `US-PICK-001`, `US-TRF-001`, `US-ADJ-002`; `ADR-002` | No partial write on tested failure paths; no broader implementation claim |
| `NFR-002` — consistency under concurrency | MUST | Same stock-changing stories; `ADR-002` | Concurrency tests required when conflicting/multi-row commands are implemented; no load/user target |
| `NFR-003` — Putaway idempotency | SHOULD | `US-PUT-001` → Technical Story Spec → `TEST-PUT-003` | Existing test verifies same key/payload produces no second allocation/increment; Putaway Round 1 only; retention TBD |
| `NFR-004` — authorization enforcement | MUST | Approved role outcomes across protected stories; `DEC-031/033` session/auth boundary | Merged implementation includes DB actor resolution and role tests; dependency override is automated-test-only. Human staging login/session/logout and Manager-only Transfer History PASS; exact release CI run and cookie-attribute inspection not recorded |
| `NFR-005` — Pick status clarity | SHOULD | `US-PICK-001` → `PF-02` → human-reviewed P2 usability finding | UI/state/copy review and existing usability evidence; no numeric threshold |

## Repo scaffold / CI baseline

| Status | Artifact path | Verification evidence | Scope boundary |
|---|---|---|---|
| Application baseline; all 9 Must stories merged | `apps/frontend/`, `apps/backend/`, `apps/docker/`, `apps/.env.example`, `apps/README.md`, `.github/workflows/ci.yml` | Commit `664d207`; historical local/CI evidence remains scoped to the commits it covered; human staging story smoke recorded separately | Exact GitHub Actions run URL/results for `664d207` are NOT RECORDED |
| Auth implementation merged and staging-smoke verified | `apps/backend/src/warehouse_api/auth*`, `apps/backend/alembic/versions/20260919_0002_auth_session_foundation.py`, `apps/frontend/src/AuthGate.tsx`, supporting config/tests/docs | Historical CI evidence remains; human staging login/session persistence/logout PASS at `664d207` | Exact cookie-attribute inspection and release-candidate CI run not recorded |
| Staging/demo deployment | `apps/frontend/vercel.mjs`, backend readiness/seed guards, `apps/backend/.python-version`, `apps/.env.example`, `apps/README.md`, `docs/06-technical/ENVIRONMENT.md`, `docs/06-technical/DEPLOYMENT.md` | Vercel and Render public URLs; `/health`, `/ready`, SPA refresh and story smoke PASS; production-safe `demo_data_seed.py` used | Staging/demo only; no production-grade claim; exact migration transcript, DB version query and secret-log inspection not recorded |

## US-PUT-001 vertical-slice implementation

| Requirement / Story / delivery trace | Implementation artifact | Test IDs and current evidence | Scope boundary |
|---|---|---|---|
| `REQ-002/003/004`, `CAND-REQ-003/007/010` → `US-PUT-001` → Taiga [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) → tasks [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19)/[#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20)/[#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) → `PF-01` / `SCR-03` → Technical Story Spec | React Putaway UI; `POST /api/v1/putaways`; Putaway context read; actor dependency boundary; SQLAlchemy models; Alembic `20260905_0001` | `TEST-PUT-001`…`TEST-PUT-005`: PASS on PostgreSQL 18 in `backend-checks`; frontend lint/typecheck/test/build: PASS in `frontend-checks`; `TEST-PUT-E2E-001`: PASS in `putaway-e2e` through React → FastAPI → PostgreSQL 18 | No Transfer/Movement write is performed by Putaway, verified by `TEST-PUT-005`; duplicate replay does not double-count verified by `TEST-PUT-003`; no persisted Warehouse total; Receive actual unchanged; full 16-unit placement is fixture scope only; `OQ-012/013/014` remain open |

Local evidence on 2026-09-05 remains: Ruff lint and format-check pass; pytest `8 passed` on the SQLite component database; frontend ESLint, TypeScript, Vitest `3 passed`, and Vite build pass; Alembic upgrade/downgrade smoke pass on a temporary SQLite database. Post-merge GitHub Actions evidence confirms successful push and pull-request runs: `backend-checks` passed migration and backend tests on PostgreSQL 18, `frontend-checks` passed lint/typecheck/test/build, and `putaway-e2e` passed the real-browser React → FastAPI → PostgreSQL 18 slice. These CI results are not presented as local Docker execution.

Fresh local evidence on 2026-10-01 for the fully-put-away UI guard: when Putaway context reports `eligible_quantity <= 0`, the frontend shows a completed-state message and exposes neither destination selection nor the confirmation action; the submit handler also rejects that state. Frontend ESLint, TypeScript, Vitest (`81 passed`), and the Vite production build pass. The backend contract and Putaway business logic are unchanged; the change is merged into `664d207`.

## US-TRF-001 merged implementation

| Requirement / Story / decision trace | Implementation artifact | Fresh local evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-001/002/004`, `CAND-REQ-003/010/011`, `FR-012` → `US-TRF-001` → `DEC-038` | Alembic `20260925_0005`; immutable `transfers`; atomic key claim; transactional destination materialization; shared Pick/Transfer UUID lock order; Warehouse Staff context/confirmation API; `/transfer/{sku_id}` UI; component, migration, concurrency and browser scenarios | Historical local evidence remains as recorded. Merged at release candidate `664d207`; human staging smoke moved 4 units Backroom → Sales Shelf, changed 12/6 → 8/10 and preserved Warehouse total 18. | Exact release-candidate CI run is not recorded. No correction/reversal, partial, bulk/multi-SKU, FIFO/FEFO, reservation, scanner/device or generic Movement. `OQ-012`, remaining `OQ-013`, `OQ-014`, `OQ-022` remain open. |

## US-TRF-002 implementation contract

| Requirement / Story / decision trace | Approved implementation contract | Current evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-002/003/004`, `CAND-REQ-010`, `FR-013` → `US-TRF-002` → `DEC-039` | Dedicated history schemas/query; Manager-only `GET /api/v1/transfers`; server-enforced exactly-one-Warehouse invariant; exact nested Transfer/SKU/location/actor response; `transferred_at DESC, id DESC`; `/transfers/history` table; strict read-only/no-effect fixtures; existing indexes and no migration | Historical local evidence remains as recorded. Merged at `664d207`; human staging smoke verified Manager-only, read-only behavior and refresh without stock mutation or duplicate Transfer. | Exact release-candidate CI run is not recorded. No idempotency/stock fields, mutation actions, multi-Warehouse membership, pagination, filters, search, export, detail page, correction/reversal or device/integration behavior. `OQ-013` and `OQ-022` remain open. |

## US-AUD-001 implementation contract

| Requirement / Story / decision trace | Approved implementation contract | Current evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-002/004`, `CAND-REQ-003/005/010`, `CAND-BR-003/009` → `US-AUD-001` → technical spec → `DEC-040` | One `AuditSession` with unique pair lines; selected/full scope; submit snapshot; missing zero; strict integer; `MATCH_COMPLETED`/`MISMATCH_RECORDED`; Staff context/submit; strict no-stock-effect | **IMPLEMENTED / MERGED** (`66d4e5c`). Implementation: `models.py`, `audit.py`, `audit_routes.py`, migration `20260926_0006`, `AuditPage.tsx`. Tests: `test_audit.py`, `test_audit_migration.py`, `test_audit_concurrency.py`, `AuditPage.test.tsx`; E2E `audit.spec.ts`. | Exact external CI run/SHA/job results are not recorded locally. Manager review is `US-AUD-002`; `OQ-012`, broader `OQ-013`, `OQ-022` remain open. |

## US-AUD-002 implementation contract

| Requirement / Story / decision trace | Approved implementation contract | Current evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-002/004`, `CAND-REQ-005/010`, `CAND-BR-002/010` → `US-AUD-002` → technical spec → `DEC-041` | Manager mismatch list/detail and exactly-one current-stock recheck; separate immutable `audit_rechecks`; safe replay; original Audit unchanged; Adjust eligibility context only | **IMPLEMENTED / MERGED** (`0b0ff17`). Implementation: `audit_discrepancy.py`, `audit_discrepancy_routes.py`, `models.py`, migration `20260926_0007`, `AuditDiscrepancyPage.tsx`. Tests: `test_audit_recheck.py`, `test_audit_recheck_migration.py`, `test_audit_recheck_concurrency.py`, `AuditDiscrepancyPage.test.tsx`; E2E `audit-recheck.spec.ts`. | Exact external CI run/SHA/job results are not recorded locally. No repeated/batch recheck, original Audit/stock mutation or auto Adjust; `OQ-012/013/022` remain open as scoped. |

## US-ADJ-001 implementation contract

| Requirement / Story / decision trace | Approved implementation contract | Current evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-001/002/003`, `CAND-REQ-008/010`, `CAND-BR-002/011/012` → `US-ADJ-001` → technical spec → `DEC-042` | Staff exact mismatch-recheck context; backend-derived snapshots/signed change; one normalized reason; exactly one request; creation replay; no creation-time stock effect | **IMPLEMENTED / MERGED** (`c34b4b1`). Implementation: `adjustment.py`, `adjustment_routes.py`, `models.py`, migration `20260927_0008`, `AdjustmentPage.tsx`. Tests: `test_adjustment.py`, `test_adjustment_migration.py`, `test_adjustment_concurrency.py`, `AdjustmentPage.test.tsx`; E2E `TEST-ADJ1-E2E-001…003`. | `DEC-043` supersedes the former terminal-lifecycle gap. Attachment I/O, broader Audit correction/reversal, `OQ-012/022` remain outside scope. External CI evidence requires manual entry. |
| `DEC-044` handoff clarification | Staff Dashboard → generic `/adjustments` eligible queue → exact `/adjustments/{audit_recheck_id}` context; queue excludes existing requests and cannot bypass exact create guards | **IMPLEMENTATION CANDIDATE / HUMAN DIFF REVIEW REQUIRED.** Adds read-only query/route/schema, `EligibleAdjustmentsPage.tsx`, Dashboard/manual routing, backend/component/E2E coverage; no migration. Local verification: Ruff/format PASS; pytest `264 passed, 32 skipped`; ESLint/typecheck PASS; Vitest `97 passed`; build PASS; Vercel config `4 passed`; Playwright discovery `37`. | PostgreSQL/Chromium execution not verified locally because `TEST_DATABASE_URL` and Docker are unavailable; no commit/push/merge. |

## US-ADJ-002 implementation contract

| Requirement / Story / decision trace | Approved implementation contract | Current evidence | Scope boundary / pending evidence |
|---|---|---|---|
| `REQ-001/002/003`, `CAND-REQ-003/008/010/011`, `CAND-BR-002/011/013/015`, `NFR-001/002/004` → `US-ADJ-002` → technical spec → `DEC-043` | Manager pending list/exact detail/decision; locked stale guard; non-negative full apply; terminal evidence; reject no-stock path; separate decision replay; Staff current-status reload | **IMPLEMENTED / MERGED** (`af72ba7`, included in `664d207`). Repository tests remain recorded; human staging smoke verified `APPLIED`, before 8, requested change -2, after/DB stock 6 and no second apply on reload. | No current-stock preview, edit/partial, reopen or same-recheck recreate. Exact external CI evidence for `664d207` is not recorded. |

## Audit/Adjust external CI evidence gap

Repository history proves merge commits, and `.github/workflows/ci.yml` defines
`frontend-checks`, `backend-checks` for PostgreSQL 17 and 18, and `putaway-e2e`
(the Chromium suite). It does not store inspectable successful run URLs/results for
these four merges. A human must record, for the relevant integration commit:

- exact commit SHA and GitHub Actions workflow run URL;
- `frontend-checks` result;
- `backend-checks (postgres-version: 17)` result;
- `backend-checks (postgres-version: 18)` result;
- `putaway-e2e` / Chromium Playwright result.

Until those values are pasted, external GitHub CI evidence is explicitly **NOT
RECORDED LOCALLY** and no PASS result is inferred.

## Canonical story coverage

| Story | Requirement | Business Rule | Decision | Evidence classification | OQ boundary |
|---|---|---|---|---|---|
| `US-REC-001` | `REQ-001/002/003`, `CAND-REQ-001/002/009/010` | `CAND-BR-001/014` | `DEC-016/017/018/023/036` | `EVD-002–005` verify actual-vs-expected behavior; later additions are HUMAN PRODUCT/TECHNICAL DECISIONS | `OQ-013` final completion/handoff; `OQ-014` partial not implemented/open; `OQ-022` open |
| `US-PUT-001` | `REQ-002/003/004`, `CAND-REQ-003/007/010` | `CAND-BR-003/004` | `DEC-006/010/011/017` | HUMAN PRODUCT DECISION; `EVD-006/007` context only | `OQ-013` exception/handoff; `OQ-014`, `OQ-022` open |
| `US-PICK-001` | `REQ-002/003`, `CAND-REQ-003/006/010/011` | `CAND-BR-003/005/006/015` | `DEC-010/012/017/018/019/037` | HUMAN PRODUCT/TECHNICAL DECISION; `EVD-006–009` context only | `OQ-012/022` open; future retry/idempotency, correction/reversal and Manager partial-review contract remain outside current slice |
| `US-TRF-001` | `REQ-001/002/004`, `CAND-REQ-003/010/011`, `FR-012` | `CAND-BR-003/007/008/015` | `DEC-005/007/009/010/013/017/018/019/024/038` | HUMAN PRODUCT/TECHNICAL DECISION; `EVD-010/011` context only | `OQ-012/022` open; `OQ-013` remains open beyond immutable success/safe retry and out-of-story correction/reversal boundary; partial Transfer is not implemented while global `OQ-014` stays open |
| `US-TRF-002` | `REQ-002/003/004`, `FR-013`, `CAND-REQ-010` | `CAND-BR-008` | `DEC-013/017/024/039` | HUMAN PRODUCT/TECHNICAL DECISION; `EVD-010/011` context only | Manager-only single-Warehouse read contract approved; broader lifecycle at `OQ-013` and device/integration at `OQ-022` remain open |
| `US-AUD-001` | `REQ-002/004`, `CAND-REQ-003/005/010` | `CAND-BR-003/009` | `DEC-010/014/017/018/021/025/031/040` | Verified evidence `EVD-015/016` + HUMAN PRODUCT/TECHNICAL DECISIONS | `OQ-012` global quantity model, remaining `OQ-013` close/resolve/correction/reversal lifecycle and `OQ-022` device/integration remain open; `US-AUD-002` owns Manager review/recheck |
| `US-AUD-002` | `REQ-002/004`, `CAND-REQ-005/010` | `CAND-BR-002/010` | `DEC-014/015/017/018/031/040/041` | Verified evidence `EVD-012/017` + HUMAN PRODUCT/TECHNICAL DECISIONS | Manager-only per-line recheck contract approved; `OQ-012` global quantity, `OQ-013` close/resolve/correction/reversal and `OQ-022` device/integration remain open |
| `US-ADJ-001` | `REQ-001/002/003`, `CAND-REQ-008/010` | `CAND-BR-002/011/012` | `DEC-015/017/018/031/041/042/044` | Verified evidence `EVD-012/013/017` + HUMAN PRODUCT/TECHNICAL DECISIONS | Staff queue/handoff and exact creation approved; Manager decision/apply belongs to `US-ADJ-002`; `OQ-012`, broader Audit lifecycle at `OQ-013`, `OQ-022`, and attachment storage/provider/policy remain open; queue/context/create do not mutate stock |
| `US-ADJ-002` | `REQ-001/002/003`, `CAND-REQ-003/008/010/011`, `NFR-001/002/004` | `CAND-BR-002/011/013/015` | `DEC-010/015/017/018/019/021/022/031/041/042/043` | Verified evidence `EVD-012/013/017` + HUMAN PRODUCT/TECHNICAL DECISIONS | Current Manager decision/apply lifecycle approved; `OQ-012`, broader Audit correction/reversal at `OQ-013`, `OQ-022` and attachment boundary remain open |

## Story-to-AC mapping

| Story | Canonical AC coverage | Downstream status |
|---|---|---|
| `US-REC-001` | actual entry/compare; match; quantity discrepancy; Warehouse Staff reference-mismatch acknowledgement and Putaway eligibility guard | **MERGED** at `664d207`; human staging smoke verified actual quantity, reference match, persisted actor/time and no stock mutation. Exact release CI run not recorded; `OQ-013/014` remain open |
| `US-PUT-001` | destination allocation; tracked location; no automatic Movement record | **MERGED** at `664d207`; historical PostgreSQL 18 CI evidence remains scoped to its run; human staging smoke verified 16 units → Backroom and correct stock/Warehouse total. Exact release CI run not recorded. |
| `US-PICK-001` | full Pick; multi-location; explicit `PARTIAL_INSUFFICIENT`; negative-stock guard | **MERGED** at `664d207`; human staging smoke verified Backroom 6 + Sales Shelf 4, picked 10/10 and Warehouse total 0. Exact release CI run not recorded. |
| `US-TRF-001` | source/destination effects; Warehouse total; minimum record; negative-stock guard | **MERGED** at `664d207`; human staging smoke verified 4 units Backroom → Sales Shelf, 12/6 → 8/10 and unchanged Warehouse total 18. Exact release CI run not recorded. |
| `US-TRF-002` | Manager history access; exact history fields; confirmation time; newest-first deterministic order; strict read-only behavior | **MERGED** at `664d207`; human staging smoke verified Manager-only/read-only behavior and refresh without mutation or duplication. Exact release CI run not recorded. |
| `US-AUD-001` | explicit selected pairs or whole-Warehouse full matrix; submit-time count/compare; durable result; `MATCH_COMPLETED` or `MISMATCH_RECORDED`; no stock effect | **MERGED** at `664d207`; human staging smoke verified system 8, physical 6, discrepancy -2 and stock remained 8. Exact release CI run not recorded. |
| `US-AUD-002` | Manager-only discrepancy list/detail; exactly-one per-line current-stock recheck; immutable original Audit; no auto Adjust or stock effect | **MERGED** at `664d207`; human staging smoke verified recheck system 8, physical 6, discrepancy -2 and unchanged stock. Exact release CI run not recorded. |
| `US-ADJ-001` | exact mismatching-recheck eligibility; backend-derived signed change and snapshots; required reason; exactly-one request; safe replay; no pre-decision change | **MERGED** at `664d207`; human staging smoke verified requested change -2, `PENDING_MANAGER_DECISION` and stock remained 8. Exact release CI run not recorded. |
| `US-ADJ-002` | approve/apply; reject/no change; no-discrepancy/no change; negative-stock and stale guards | **MERGED** at `664d207`; human staging smoke verified `APPLIED`, 8 + (-2) = 6, DB stock 6 and no second apply on reload. Exact release CI run not recorded. |

## Requirement → Canonical Story → Taiga → Design/Prototype → Implementation/Test

Taiga references dưới đây theo dõi thực thi và không thay thế nguồn yêu cầu canonical. Trạng thái implementation/test không được suy ra từ trạng thái Taiga.

| Requirement | Canonical Story | Taiga Story | Taiga Tasks | Design/Prototype | Implementation/Test status |
|---|---|---|---|---|---|
| `REQ-001/002/003`, `CAND-REQ-001/002/009/010` | `US-REC-001` | [#7](https://tree.taiga.io/project/lenghi-group-07-project/us/7) / ID `9523822` — Ready | `T-REC-01` [#16](https://tree.taiga.io/project/lenghi-group-07-project/task/16); `T-REC-02` [#17](https://tree.taiga.io/project/lenghi-group-07-project/task/17); `T-REC-03` [#18](https://tree.taiga.io/project/lenghi-group-07-project/task/18) — New | `PF-01 — Receive → Putaway`; 10 wireframe states và 10 prototype counterparts human verified | **MERGED** at `664d207`; human staging smoke PASS for recording/reference/actor-time and no stock effect; release CI run not recorded |
| `REQ-002/003/004`, `CAND-REQ-003/007/010` | `US-PUT-001` | [#8](https://tree.taiga.io/project/lenghi-group-07-project/us/8) / ID `9523823` — Done | `T-PUT-01` [#19](https://tree.taiga.io/project/lenghi-group-07-project/task/19) — Done; `T-PUT-02` [#20](https://tree.taiga.io/project/lenghi-group-07-project/task/20) — Done; `T-PUT-03` [#21](https://tree.taiga.io/project/lenghi-group-07-project/task/21) — Done | `PF-01 — Receive → Putaway`; `SCR-03`; [`06-technical/story-specs/putaway.md`](06-technical/story-specs/putaway.md) | COMPLETED; API/DB/migration/UI merged; PostgreSQL 18 backend, frontend and Playwright E2E checks PASS in GitHub Actions |
| `REQ-002/003`, `CAND-REQ-003/006/010/011` | `US-PICK-001` | [#9](https://tree.taiga.io/project/lenghi-group-07-project/us/9) / ID `9523824` — Ready | `T-PICK-01` [#22](https://tree.taiga.io/project/lenghi-group-07-project/task/22); `T-PICK-02` [#23](https://tree.taiga.io/project/lenghi-group-07-project/task/23); `T-PICK-03` [#24](https://tree.taiga.io/project/lenghi-group-07-project/task/24) — New | `PF-02 — Pick`; 7 wireframe states và 7 prototype counterparts human verified; implementation-ready spec at `DEC-037` | **MERGED** at `664d207`; human staging multi-location 10/10 smoke PASS; release CI run not recorded |
| `REQ-001/002/004`, `CAND-REQ-003/010/011`, `FR-012` | `US-TRF-001` | [#10](https://tree.taiga.io/project/lenghi-group-07-project/us/10) / ID `9523825` — New | `T-TRF1-01` [#25](https://tree.taiga.io/project/lenghi-group-07-project/task/25); `T-TRF1-02` [#26](https://tree.taiga.io/project/lenghi-group-07-project/task/26); `T-TRF1-03` [#27](https://tree.taiga.io/project/lenghi-group-07-project/task/27) — New | Consolidated User Flow; implementation-ready Technical Story Spec at `DEC-038`; no dedicated Transfer screen/prototype | **MERGED** at `664d207`; human staging atomic stock/total smoke PASS; release CI run not recorded |
| `REQ-002/003/004`, `FR-013`, `CAND-REQ-010` | `US-TRF-002` | [#11](https://tree.taiga.io/project/lenghi-group-07-project/us/11) / ID `9523826` — New | `T-TRF2-01` [#28](https://tree.taiga.io/project/lenghi-group-07-project/task/28); `T-TRF2-02` [#29](https://tree.taiga.io/project/lenghi-group-07-project/task/29); `T-TRF2-03` [#30](https://tree.taiga.io/project/lenghi-group-07-project/task/30) — New | Consolidated User Flow; implemented Technical Story Spec at `DEC-039`; no dedicated history prototype | **MERGED** at `664d207`; human staging Manager-only/read-only/reload smoke PASS; release CI run not recorded |
| `REQ-002/004`, `CAND-REQ-003/005/010` | `US-AUD-001` | [#12](https://tree.taiga.io/project/lenghi-group-07-project/us/12) / ID `9523827` — Ready | `T-AUD1-01` [#31](https://tree.taiga.io/project/lenghi-group-07-project/task/31); `T-AUD1-02` [#32](https://tree.taiga.io/project/lenghi-group-07-project/task/32); `T-AUD1-03` [#33](https://tree.taiga.io/project/lenghi-group-07-project/task/33) — New | `PF-03`; `SCR-07`; implemented spec at `DEC-040` | **IMPLEMENTED / MERGED** (`66d4e5c`); external CI evidence gap documented above |
| `REQ-002/004`, `CAND-REQ-005/010` | `US-AUD-002` | [#13](https://tree.taiga.io/project/lenghi-group-07-project/us/13) / ID `9523828` — Ready | `T-AUD2-01` [#34](https://tree.taiga.io/project/lenghi-group-07-project/task/34); `T-AUD2-02` [#35](https://tree.taiga.io/project/lenghi-group-07-project/task/35); `T-AUD2-03` [#36](https://tree.taiga.io/project/lenghi-group-07-project/task/36) — New | `PF-03`; `SCR-08`; `/audit-discrepancies`; implemented spec at `DEC-041` | **IMPLEMENTED / MERGED** (`0b0ff17`); external CI evidence gap documented above |
| `REQ-001/002/003`, `CAND-REQ-008/010` | `US-ADJ-001` | [#14](https://tree.taiga.io/project/lenghi-group-07-project/us/14) / ID `9523829` — Ready | `T-ADJ1-01` [#37](https://tree.taiga.io/project/lenghi-group-07-project/task/37); `T-ADJ1-02` [#38](https://tree.taiga.io/project/lenghi-group-07-project/task/38); `T-ADJ1-03` [#39](https://tree.taiga.io/project/lenghi-group-07-project/task/39) — New | `PF-03`; `SCR-09`; `/adjustments` → `/adjustments/{audit_recheck_id}`; implemented specs at `DEC-042/043/044` | Base merged (`c34b4b1`); `DEC-044` handoff candidate awaits human diff review and external CI evidence |
| `REQ-001/002/003`, `CAND-REQ-003/008/010/011`, `NFR-001/002/004` | `US-ADJ-002` | [#15](https://tree.taiga.io/project/lenghi-group-07-project/us/15) / ID `9523830` — Ready | `T-ADJ2-01` [#40](https://tree.taiga.io/project/lenghi-group-07-project/task/40); `T-ADJ2-02` [#41](https://tree.taiga.io/project/lenghi-group-07-project/task/41); `T-ADJ2-03` [#42](https://tree.taiga.io/project/lenghi-group-07-project/task/42) — New | `PF-03`; `SCR-10`; `/adjustment-decisions`; implemented spec at `DEC-043` | **IMPLEMENTED / MERGED** (`af72ba7`); external CI evidence gap documented above |

## OQ decision trace

| OQ | Current status | Decision/impact |
|---|---|---|
| `OQ-012` | OPEN QUESTION | `DEC-037/038/040/041` use strict integer only as current Pick/Transfer/original-Audit/recheck slice constraints; `DEC-042/043` preserve, derive and apply those integer recheck snapshots/signed change for current Adjust slices. UOM, decimal quantity, conversion behavior and precision/scale remain globally undecided |
| `OQ-011` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-010–015`; per-location `system stock quantity` |
| `OQ-013` | PARTIALLY DECIDED / OPEN | `DEC-036` defines `RECEIVE_RECORDED` and reference-review eligibility; `DEC-037` defines current Pick confirmation; `DEC-038/039` define immutable Transfer success/replay and history; `DEC-040/041` define original Audit and Manager recheck; `DEC-042` defines exactly-one pending Staff Adjust request; `DEC-043` defines current Manager decision/apply, `APPLIED/REJECTED`, stale/negative still-pending failures and no reopen/recreate from the same rejected recheck. Final Receive handoff, future Pick lifecycle, Putaway exception/handoff, broader Transfer lifecycle and Audit close/resolve/correction/reversal remain open |
| `OQ-017` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-014/015` |
| `OQ-018` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-014` |
| `OQ-019` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-016/017` |
| `OQ-020` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-017` |
| `OQ-015` | RESOLVED — HUMAN PRODUCT DECISION | `DEC-019`; location quantity cannot be negative; no retry/cancel semantics inferred |
| `OQ-014`, `OQ-021`, `OQ-022` | OPEN QUESTION | `DEC-037` resolves partial semantics only for the current Pick slice; partial Receive and partial Transfer are not implemented in their current slices and are not permanently excluded; partial Putaway remains undecided. Alert and device/integration behavior remain open; `DEC-040/041/042/043` exclude scanner/device/mobile/offline/integration only from current Audit/Adjust slices without resolving `OQ-022` globally |
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
| `PF-01 — Receive → Putaway` | `US-REC-001`, `US-PUT-001` | `P1`: expected/actual và discrepancy rõ; `DEC-036` xác định mismatch acknowledgement/eligibility, còn final completion và exact handoff chưa rõ | Giữ hai flow tách biệt; không production CTA tự động; prototype chỉ dùng facilitator transition | `DEC-016`, `DEC-018`, `DEC-036`; `OQ-013` vẫn mở |
| `PF-02 — Pick` | `US-PICK-001` | `P2`: multi-location/full/blocked rõ; partial có thể bị hiểu là fully completed | Giữ partial hợp lệ; hiển thị picked/requested/remaining và yêu cầu explicit partial confirmation; thêm copy “Pick is not fully completed. 4 units remain unfulfilled.”; giữ blocked/no-change guard | `DEC-012`, `DEC-019`, `DEC-037` |
| `PF-03 — Audit → Adjust` | `US-AUD-001`, `US-AUD-002`, `US-ADJ-001`, `US-ADJ-002` | `P3`: mismatch và re-check rõ; thời điểm quantity đổi qua actor handoff chưa rõ | Hiển thị no-change sau mismatch/re-check/waiting/reject; chỉ approved/applied mới cập nhật quantity; `/audits/new` mismatch success phải nói rõ stock không đổi; `/audit-discrepancies` tách Original Audit và Manager Recheck; Staff Adjust request hiển thị derived non-editable change và `PENDING_MANAGER_DECISION`; Manager decision page không preview stock và giữ quantity read-only | `DEC-014`, `DEC-015`, `DEC-018`, `DEC-019`, `DEC-040`, `DEC-041`, `DEC-042`, `DEC-043` |

## Decomposition record

- `DRAFT-US-PUT-001` was promoted to `US-PUT-001`.
- `DRAFT-US-PICK-001` was promoted to `US-PICK-001`; insufficient Pick remains an AC/scenario.
- `DRAFT-US-TRF-001` was split into `US-TRF-001` and `US-TRF-002`.
- `DRAFT-US-AUD-001` was split into `US-AUD-001` and `US-AUD-002`.
- `DRAFT-US-ADJ-001` was split into `US-ADJ-001` and `US-ADJ-002`.
- Receive reference mismatch remains an AC/scenario in `US-REC-001`.

Historical draft references are valid only when explicitly labeled as promoted, split, historical or superseded.

## CI failure audit - 2026-10-08

- Putaway discovery authorization remains Warehouse Staff only. The E2E test now
  verifies the real `403`, `FORBIDDEN`, required role metadata, and the stable UI
  heading instead of comparing the UI heading with the backend's generic message.
- Audit recheck and Adjust decision E2E setup now waits for successful login and
  Audit context responses before interacting with the selected-pair controls.
- Local evidence: frontend lint, typecheck, and 101 unit tests pass; all 14 targeted
  Playwright tests collect. Runtime PostgreSQL Playwright verification remains
  pending because the local environment has no `TEST_DATABASE_URL` or Docker.

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
| Architecture/Data Model/API | Technical Foundation human reviewed; 3 accepted ADR; all 9 Must stories and auth merged; Vercel → Render → Supabase deployed and human-smoke verified for staging/demo |
| Implementation/Test | Release candidate `664d207`; `/health`, `/ready`, SPA refresh, auth/session/logout and 9 story workflows human-smoke PASS. Exact GitHub Actions run URL/results for this commit are NOT RECORDED; no production-grade claim |
