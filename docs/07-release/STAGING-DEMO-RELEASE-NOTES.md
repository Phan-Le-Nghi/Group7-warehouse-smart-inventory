# Staging/Demo Release Notes — `664d207`

## Release summary

This release deploys the nine human-approved Must stories to the staging/demo
topology at:

- Frontend: <https://group7-warehouse-smart-inventory.vercel.app>
- Backend: <https://group7-warehouse-smart-inventory.onrender.com>

It is a **staging/demo release**, not a production-grade or production-readiness
claim. Human-performed staging smoke passed; exact GitHub Actions run URL/results
for `664d207` are not recorded.

## Included Must stories

1. `US-REC-001` — record Receive actual quantity and reference comparison
   without mutating stock.
2. `US-PUT-001` — post received quantity into a tracked location.
3. `US-PICK-001` — pick from explicit one-or-more location allocations.
4. `US-TRF-001` — atomically transfer stock between tracked locations.
5. `US-TRF-002` — Manager-only, read-only Transfer History.
6. `US-AUD-001` — record physical count, system snapshot and discrepancy
   without changing stock.
7. `US-AUD-002` — Manager discrepancy review and immutable recheck without
   changing stock.
8. `US-ADJ-001` — Staff request for the backend-derived signed adjustment,
   pending Manager decision and without changing stock.
9. `US-ADJ-002` — Manager approve/apply or reject; an applied decision records
   before/after evidence and cannot apply twice on reload.

Authentication uses PostgreSQL-backed server-side sessions and database roles.
The frontend is served by Vercel, proxies relative `/api/*` requests to Render,
and preserves SPA deep links. Render connects to Supabase PostgreSQL over TLS.

## Verification summary

The human-performed staging smoke verified `/health`, `/ready`, SPA/deep-link
refresh, login/session persistence/logout, and all nine story flows. It also
verified important no-effect boundaries: Receive, Audit, Manager Recheck and a
pending Staff Adjust request did not change stock; Transfer History refresh did
not mutate or duplicate a Transfer; an applied Adjust did not apply twice.

The exact quantities, statuses and evidence classifications are in the
[release checklist](STAGING-DEMO-RELEASE-CHECKLIST.md). Staging/demo fixtures
were created with production-safe `warehouse_api.demo_data_seed`; destructive
`warehouse_api.test_seed` was not used.

## Known limitations and deferred scope

- Long-term production hosting and operating model remain `TBD`; no production
  availability, SLA, load, backup/restore or disaster-recovery claim is made.
- Exact GitHub Actions run URL/job results for `664d207` are not recorded.
- An exact `alembic current` transcript, named migration-runner record, direct
  PostgreSQL version-query output and separate cookie-attribute inspection are
  not recorded in this release evidence.
- Render Free cold start requires warm-up/rehearsal and is not availability
  evidence.
- `OQ-012` remains open for the broader quantity model.
- `OQ-013` remains partially open for lifecycle, handoff, correction and
  reversal behavior outside the approved story slices.
- `OQ-014` remains open across partial Receive/Putaway/Transfer boundaries;
  current Pick partial behavior does not close it globally.
- `OQ-022` remains open for scanner/device/mobile/offline/integration behavior.
- `OQ-033` remains partially open for quantitative performance, uptime, load
  and usability targets.
- Attachment storage/provider/policy and advanced pagination/filter/search/export
  remain deferred where documented by the canonical contracts.

This release does not close unrelated open questions or expand the canonical
business scope.
