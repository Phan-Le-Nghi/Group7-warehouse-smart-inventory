# AI/Vault consistency notes

## 2026-10-09 — DEC-045 route reconciliation

- Application inspection confirmed that `GET /api/v1/locations` and
  `GET /api/v1/stock?sku_id={id}` were not exposed, despite earlier API inventory
  wording. They are no longer labelled implemented.
- `DEC-045` adds `GET /api/v1/skus`, `POST /api/v1/receives/prepared` and
  `POST /api/v1/picks/requests` as supporting usability extensions.
- No `US-REC-002` or `US-PICK-002` was created. The canonical metric remains
  9/9 stories, and historical `US-REC-001`/`US-PICK-001` ACs remain unchanged.
