# Architecture và ADR — Bản phục vụ báo cáo

## Trạng thái

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Canonical technical source: [`../../vault/06-technical/architecture.md`](../../vault/06-technical/architecture.md). Technical Foundation được ghi tại `DEC-020` đến `DEC-023`; authentication/authorization design/spec tại `DEC-031/033`; revised staging/demo topology và PostgreSQL compatibility tại `DEC-034/035`. Auth implementation đã merge; human-confirmed merged-PR evidence ghi nhận backend, frontend và Playwright E2E CI checks `PASS`. Staging HTTPS cookie behavior và Vercel/Render/Supabase deployment chưa được verify.

## Kiến trúc được duyệt

- Modular monolith.
- Một React + TypeScript + Vite frontend, quản lý package bằng npm.
- Một Python 3.13 + FastAPI backend API, quản lý package bằng uv và test bằng pytest.
- PostgreSQL 17+ compatibility; PostgreSQL 18 là local/CI baseline và Supabase PostgreSQL 17 là staging/demo target; Docker dùng cho local database runtime.
- SQLAlchemy 2 và Alembic cho persistence/migrations.
- Playwright cho E2E.
- Không microservices, CQRS, event bus hoặc generic workflow engine.

```text
React frontend
  -> HTTP/JSON
  -> FastAPI route + actor/auth dependency
  -> application service / PostgreSQL transaction
  -> SQLAlchemy 2
  -> PostgreSQL 17+
```

Frontend không sở hữu authoritative stock. Application service giữ use-case và transaction boundary; persistence thực hiện query/lock/write; PostgreSQL giữ constraints. Production authentication baseline dùng server-side session trong PostgreSQL: cookie → session record → active user → current database role. Frontend không phải role source-of-truth. Protected routes dùng reusable authorization dependency/policy; test actor injection chỉ dành cho automated tests. Design/spec đã được approve tại `DEC-031/033`; implementation đã merge và CI pass, nhưng staging HTTPS cookie behavior chưa verify.

## Authentication/authorization design đã duyệt

- Random session ID; database chỉ lưu session-token hash.
- Cookie `HttpOnly`, `Path=/`, `Secure` tại staging/production và `SameSite` phù hợp topology.
- Password chỉ lưu Argon2id hash; không lưu plaintext hoặc demo password trong repository, Vault hay CI log.
- Bốn database roles: `WAREHOUSE_STAFF`, `MANAGER`, `PURCHASING`, `ADMIN`; permission boundary giữ nguyên `DEC-017`.
- Missing/invalid/expired/revoked session hoặc inactive user → `401`; authenticated actor thiếu quyền → `403`.
- Không JWT, refresh token, self-registration, password reset, social login, OAuth, Keycloak hoặc external identity provider trong current MVP baseline.
- Staging/demo có tối thiểu một account cho mỗi role; seed idempotent và password đến từ environment/platform secrets hoặc được tạo ngoài source control.

`DEC-033` approve exact `users`/`auth_sessions` schema, cookie `warehouse_session`, 8-hour absolute lifetime và configurable `COOKIE_SECURE`/`COOKIE_SAMESITE`/`CORS_ORIGINS`. Không hardcode `SameSite=None`; ưu tiên same-site topology và cross-site mode bắt buộc strict Origin plus JSON-only mutation.

## Staging/demo design đã duyệt

```text
Browser
  -> public HTTPS Vercel React/Vite frontend
  -> same-origin /api/* rewrite
  -> public HTTPS Render FastAPI backend
  -> TLS
  -> Supabase PostgreSQL 17
```

`DEC-034` supersede riêng Render Static Site và Render managed PostgreSQL clauses của `DEC-032`; Render tiếp tục host FastAPI. Frontend gọi relative `/api/...`; staging cookie là host-only `warehouse_session` với `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, `COOKIE_SECURE=true` và `COOKIE_SAMESITE=lax`. Direct Vercel → Render cross-site mode và hardcoded `SameSite=None` không phải baseline.

Supabase chỉ là hosted PostgreSQL; không dùng Supabase Auth, browser SDK làm business-data path, Data API, JWT hoặc external identity provider. `DATABASE_URL` lấy từ project thật, không commit URL/password và dùng TLS `sslmode=require`. Exact host/connection mode không được invent trong docs. `DEC-035` approve PostgreSQL 17 cho staging, yêu cầu application/migrations tương thích PostgreSQL 17+ và PostgreSQL 17 verification trước release; PostgreSQL 18 CI evidence vẫn có giá trị nhưng không chứng minh hai major version hoàn toàn giống nhau.

Alembic tiếp tục là migration source-of-truth; mỗi release chỉ có một migration runner. Future preference là protected GitHub Actions `workflow_dispatch`; khi chưa có workflow, named human operator được phép chạy thủ công. Không chạy `alembic upgrade head` trong mọi application startup.

`/health` tiếp tục là liveness. Future `/ready` phải thực hiện ít nhất `SELECT 1` và hiện chưa implemented. Future production-safe idempotent demo seed được phép create missing records/reconcile deterministic references khi an toàn, nhưng không reset toàn bộ operational state, tùy tiện delete staging records hoặc reuse destructive `test_seed.py` behavior. Exact demo IDs/data thuộc implementation task riêng.

Release smoke phải verify frontend HTTPS, backend health, database readiness, login, cookie flags, `/auth/me`, `401`, `403`, Putaway, idempotency, logout và secrets không leak. Các yêu cầu retained từ `DEC-032` gồm staging/demo-only, public HTTPS, secrets ngoài repository, migration/readiness/seed/smoke và no-`--reload`. Render Free được phép, nhưng phải warm-up/rehearse trước demo và không được claim production-grade availability. Topology vẫn `DESIGN / NOT DEPLOYED`; long-term production target vẫn `TBD`.

## ADR

| ADR | Accepted decision |
|---|---|
| [`ADR-001`](../../vault/06-technical/adrs/ADR-001-location-stock-authoritative.md) | Persist stock theo SKU/location; derive Warehouse total; không tạo `warehouse_totals` |
| [`ADR-002`](../../vault/06-technical/adrs/ADR-002-transactional-stock-consistency.md) | Stock-changing operations dùng transaction/row locking khi cần và enforce non-negative stock ở application + database |
| [`ADR-003`](../../vault/06-technical/adrs/ADR-003-receive-putaway-stock-posting.md) | Receive ghi actual quantity nhưng không tăng location stock; Putaway thực hiện initial posting và không tạo Transfer/Movement side effect |

## Vẫn TBD / OPEN

- Staging HTTPS cookie behavior, Supabase PostgreSQL 17 release evidence, `/ready`, safe demo-data seed, migration workflow và smoke automation chưa implemented/verified.
- Long-term production deployment target; Vercel/Render/Supabase chỉ được approve cho staging/demo.
- Adjust dùng target quantity hay signed delta; attachment storage.
- Advanced pagination/filtering và quantitative NFR tại `OQ-033`.
- `OQ-012`, `OQ-013` và `OQ-014` không bị đóng bởi Technical Foundation.

Technical application scaffold, `US-PUT-001` vertical slice và auth implementation đã merge; CI evidence được theo dõi tại [`../TRACEABILITY.md`](../TRACEABILITY.md). Không claim local Docker pass, staging deployment hoặc public HTTPS verification.
