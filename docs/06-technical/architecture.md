# Architecture và ADR — Bản phục vụ báo cáo

## Trạng thái

`HUMAN APPROVED TECHNICAL FOUNDATION — DOCUMENTATION ONLY`

Canonical technical source: [`../../vault/06-technical/architecture.md`](../../vault/06-technical/architecture.md). Technical Foundation được ghi tại `DEC-020` đến `DEC-023`; authentication/authorization design được approve tại `DEC-031` và Render staging/demo design tại `DEC-032`. Các quyết định mới là approved design, không phải implementation claim.

## Kiến trúc được duyệt

- Modular monolith.
- Một React + TypeScript + Vite frontend, quản lý package bằng npm.
- Một Python 3.13 + FastAPI backend API, quản lý package bằng uv và test bằng pytest.
- Một PostgreSQL 18 database; Docker dùng cho local database runtime.
- SQLAlchemy 2 và Alembic cho persistence/migrations.
- Playwright cho E2E.
- Không microservices, CQRS, event bus hoặc generic workflow engine.

```text
React frontend
  -> HTTP/JSON
  -> FastAPI route + actor/auth dependency
  -> application service / PostgreSQL transaction
  -> SQLAlchemy 2
  -> PostgreSQL 18
```

Frontend không sở hữu authoritative stock. Application service giữ use-case và transaction boundary; persistence thực hiện query/lock/write; PostgreSQL giữ constraints. Production authentication baseline dùng server-side session trong PostgreSQL: cookie → session record → active user → current database role. Frontend không phải role source-of-truth. Protected routes dùng reusable authorization dependency/policy; test actor injection chỉ dành cho automated tests. Thiết kế này đã được approve nhưng chưa implement.

## Authentication/authorization design đã duyệt

- Random session ID; database chỉ lưu session-token hash.
- Cookie `HttpOnly`, `Path=/`, `Secure` tại staging/production và `SameSite` phù hợp topology.
- Password chỉ lưu Argon2id hash; không lưu plaintext hoặc demo password trong repository, Vault hay CI log.
- Bốn database roles: `WAREHOUSE_STAFF`, `MANAGER`, `PURCHASING`, `ADMIN`; permission boundary giữ nguyên `DEC-017`.
- Missing/invalid/expired/revoked session hoặc inactive user → `401`; authenticated actor thiếu quyền → `403`.
- Không JWT, refresh token, self-registration, password reset, social login, OAuth, Keycloak hoặc external identity provider trong current MVP baseline.
- Staging/demo có tối thiểu một account cho mỗi role; seed idempotent và password đến từ environment/platform secrets hoặc được tạo ngoài source control.

Conceptual `users` và `auth_sessions` entities đã được approve; exact SQL types/indexes/constraints, session lifetime và topology-specific `SameSite` thuộc implementation spec.

## Render staging/demo design đã duyệt

```text
React -> public HTTPS Render Static Site
FastAPI -> public HTTPS Render Web Service
PostgreSQL -> Render managed PostgreSQL
```

Staging phải có public frontend/backend URLs, secrets ngoài repository, Alembic migration, `/health`, DB readiness check trước release-ready claim, deterministic idempotent demo seed và smoke test. Backend production command không dùng `--reload`; CORS chỉ allow approved staging frontend origin và phải tương thích credentials khi session cookie yêu cầu. Render chỉ là staging/demo target; chưa được triển khai hoặc verify. Long-term production target vẫn `TBD`.

## ADR

| ADR | Accepted decision |
|---|---|
| [`ADR-001`](../../vault/06-technical/adrs/ADR-001-location-stock-authoritative.md) | Persist stock theo SKU/location; derive Warehouse total; không tạo `warehouse_totals` |
| [`ADR-002`](../../vault/06-technical/adrs/ADR-002-transactional-stock-consistency.md) | Stock-changing operations dùng transaction/row locking khi cần và enforce non-negative stock ở application + database |
| [`ADR-003`](../../vault/06-technical/adrs/ADR-003-receive-putaway-stock-posting.md) | Receive ghi actual quantity nhưng không tăng location stock; Putaway thực hiện initial posting và không tạo Transfer/Movement side effect |

## Vẫn TBD / OPEN

- Exact auth implementation details: SQL/index/constraint choices, session lifetime, cookie name và topology-specific `SameSite`.
- Long-term production deployment target; Render chỉ được approve cho staging/demo.
- Adjust dùng target quantity hay signed delta; attachment storage.
- Advanced pagination/filtering và quantitative NFR tại `OQ-033`.
- `OQ-012`, `OQ-013` và `OQ-014` không bị đóng bởi Technical Foundation.

Technical application scaffold và `US-PUT-001` vertical slice đã được tạo, đang chờ human diff review; evidence được theo dõi tại [`../TRACEABILITY.md`](../TRACEABILITY.md). Docker/PostgreSQL runtime chưa được verify trên máy triển khai slice nên PostgreSQL integration và Playwright local không được claim Pass.
