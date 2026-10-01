# Staging/Demo Release Checklist — `664d207`

## Release identity and evidence boundary

- Release type: **staging/demo**, not production-grade.
- Release candidate commit: `664d207`.
- Frontend: <https://group7-warehouse-smart-inventory.vercel.app>.
- Backend: <https://group7-warehouse-smart-inventory.onrender.com>.
- Topology: Vercel React/Vite → same-origin `/api/*` rewrite → Render FastAPI
  → TLS → Supabase PostgreSQL 17.
- Working tree at release verification: **clean** — human confirmed; the same
  state was observed during this documentation audit.
- Exact GitHub Actions run URL/results for `664d207`: **NOT RECORDED**. No CI
  result from an older commit is used as release-candidate evidence.
- Primary evidence: commit identity, deployed URLs, runtime/DB checks and the
  human-performed staging smoke below. Screenshots are not the primary artifact.

## Deployment and runtime checks

| Check | Result | Evidence classification |
|---|---|---|
| Frontend staging URL loads | PASS | Human-performed staging verification |
| Backend `GET /health` | PASS | Human-performed staging runtime smoke |
| Backend `GET /ready` | PASS | Human-performed staging DB-readiness smoke |
| Vercel SPA/deep-link refresh | PASS | Human-performed staging browser smoke |
| Login, session persistence and logout | PASS | Human-performed staging browser smoke |
| Fixture command | PASS — `warehouse_api.demo_data_seed` used; `warehouse_api.test_seed` not used | Human-confirmed staging operation |
| Exact `alembic current` output / named migration runner | NOT RECORDED | Must not be inferred from readiness |
| Exact cookie-attribute inspection | NOT RECORDED | Login/session PASS does not replace attribute inspection |
| GitHub Actions run/jobs for `664d207` | NOT RECORDED | Automated evidence unavailable for this commit |

## Human-performed story smoke

| Story | Staging check | Result |
|---|---|---|
| `US-REC-001` — Receive | Actual quantity recorded correctly; reference matched; actor/time persisted; Receive did not mutate stock | PASS |
| `US-PUT-001` — Putaway | 16 units placed into Backroom; location stock and derived Warehouse total updated correctly | PASS |
| `US-PICK-001` — Pick | Backroom 6 + Sales Shelf 4; picked 10/10; derived Warehouse total became 0 | PASS |
| `US-TRF-001` — Transfer | 4 units Backroom → Sales Shelf; balances changed 12/6 → 8/10; Warehouse total remained 18 | PASS |
| `US-TRF-002` — Transfer History | Manager-only and read-only; refresh did not mutate stock or duplicate the Transfer | PASS |
| `US-AUD-001` — Audit | System 8, physical 6, discrepancy -2; stock remained 8 | PASS |
| `US-AUD-002` — Manager Recheck | System 8, physical 6, discrepancy -2; stock remained unchanged | PASS |
| `US-ADJ-001` — Staff Adjust Request | `requested_change = -2`; status `PENDING_MANAGER_DECISION`; stock remained 8 | PASS |
| `US-ADJ-002` — Manager Approve/Apply | Status `APPLIED`; before 8, requested change -2, after 6; DB stock 6; reload did not apply twice | PASS |

## Release decision

- [x] Commit and deployed endpoints identified.
- [x] All nine canonical Must stories have human-performed staging smoke PASS.
- [x] Runtime and DB readiness endpoints PASS.
- [x] SPA refresh and auth/session/logout PASS.
- [x] Demo data used the production-safe seed path.
- [x] Evidence gaps remain explicitly marked rather than inferred.
- [x] Release is labeled staging/demo only.
- [ ] Production-readiness approval — out of scope and not claimed.

Result: **PASS for the current staging/demo release at `664d207`**, subject to
the known limitations in the accompanying
[release notes](STAGING-DEMO-RELEASE-NOTES.md).

