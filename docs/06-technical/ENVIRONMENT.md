# Runtime Environment Guide

Status: deployment foundation prepared for human review; no cloud deployment is
claimed.

## Variables

| Variable | Dev required? | Staging required? | Production required? | Sensitive? | Default | Example format | Notes |
|---|---:|---:|---:|---:|---|---|---|
| `APP_ENV` | No | Yes | Yes | No | `development` | `staging` | Allowed: `development`, `test`, `staging`, `production`. Deployed values enable fail-closed validation. |
| `DATABASE_URL` | No | Yes | Yes | **Yes** | Local development PostgreSQL URL | `postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require` | `postgresql://` is normalized to `postgresql+psycopg://`. Staging/production require `sslmode=require`. Percent-encode reserved characters in credentials. |
| `CORS_ORIGINS` | No | Yes | Yes | No | Local Vite origins | `https://warehouse.example.com` | Comma-separated exact origins. Staging/production accept only non-loopback HTTPS origins; wildcard, paths, credentials, localhost, and loopback are rejected. Use the Vercel frontend origin. |
| `COOKIE_SECURE` | No | Yes | Yes | No | `false` | `true` | Must be `true` in staging/production. |
| `COOKIE_SAMESITE` | No | Yes | Yes | No | `lax` | `lax` | Staging/production require `lax`, matching the approved same-origin `/api/*` topology. |
| `DEMO_USER_PASSWORD` | Only when explicitly seeding | Only when explicitly seeding | No | **Yes** | None | Platform secret or controlled input | No fallback exists. The explicit demo seed is disabled for `APP_ENV=production`. Clear interactive values after use. |
| `TEST_DATABASE_URL` | Only for PostgreSQL tests/E2E | No | No | **Yes** | None | Dedicated disposable PostgreSQL URL | `test_seed.py` additionally requires `APP_ENV=test`. Never point this at staging/production. |
| `RENDER_API_ORIGIN` | Only for Vercel config validation | Yes on Vercel | Depends on any future approved topology | No | None | `https://service-name.onrender.com` | HTTPS origin only: no path, query, fragment, or embedded credentials. Used at Vercel config/build time; not exposed through `VITE_*`. |
| `VITE_API_BASE_URL` | No | No | No | No | Empty (same origin) | `http://localhost:8000` | Local development override. Leave unset for Vercel so browser calls stay relative `/api/...`. |
| `VITE_RECEIVE_LINE_ID` | Per local/demo context | Per demo context | TBD | No | None | `daf594b9-9c1e-51ec-adf0-0055cb3a8ff3` | Canonical demo Putaway context created by `warehouse_api.demo_data_seed`; set at Vercel build time. |
| `VITE_RECEIVE_ID` | Per local/demo context | Per demo context | TBD | No | None | `435cd10b-4cfe-53a4-bbcf-f63735a8292e` | Canonical recorded demo Receive context; set at Vercel build time. |
| `PORT` | No | Injected by Render | Provider-specific | No | None | `10000` | Render supplies this. Do not commit or hardcode it. |

The session absolute lifetime remains the approved fixed eight hours
(`SESSION_LIFETIME` in backend code). It is not an environment variable. Stale
session retention remains the approved fixed seven days and cleanup is an
explicit command, not a scheduler.

## Fail-closed behavior

Importing the FastAPI application loads settings. With `APP_ENV=staging` or
`APP_ENV=production`, startup fails before serving requests if:

- `DATABASE_URL` or `CORS_ORIGINS` is missing;
- the database URL is not PostgreSQL/psycopg or lacks exactly
  `sslmode=require`;
- a CORS origin is not an explicit non-loopback HTTPS origin;
- `COOKIE_SECURE` is not true; or
- `COOKIE_SAMESITE` is not `lax`.

Development retains local defaults. `APP_ENV=test` is explicit for destructive
browser fixtures but otherwise permits test-controlled database configuration.
