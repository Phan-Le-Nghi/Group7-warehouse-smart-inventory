from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import warehouse_api.auth_service as auth_service
import warehouse_api.main as main_module
from warehouse_api.auth_service import (
    SESSION_LIFETIME,
    authenticate_user,
    cleanup_stale_sessions,
    create_session,
    hash_session_token,
    resolve_session,
    revoke_session,
)
from warehouse_api.config import Settings, get_settings
from warehouse_api.models import AuthSession, User

PASSWORD = "test-only-password"


def add_user(
    factory: sessionmaker[Session],
    login_identifier: str = "demo.warehouse_staff",
    role: str = "WAREHOUSE_STAFF",
    is_active: bool = True,
) -> User:
    with factory.begin() as session:
        user = User(
            login_identifier=login_identifier,
            password_hash=auth_service.hash_password(PASSWORD),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        session.flush()
        user_id = user.id
    with factory() as session:
        return session.get(User, user_id)


def test_unknown_identifier_still_performs_dummy_verification(
    db_session: Session, monkeypatch
) -> None:
    calls: list[tuple[str, str]] = []

    def verify_and_update(password: str, encoded_hash: str):
        calls.append((password, encoded_hash))
        return False, None

    monkeypatch.setattr(
        auth_service,
        "password_hasher",
        SimpleNamespace(verify_and_update=verify_and_update),
    )

    assert authenticate_user(db_session, "missing-user", "submitted-secret") is None
    assert calls == [("submitted-secret", auth_service._dummy_password_hash)]


def test_authenticate_user_normalizes_identifier_and_rejects_inactive_user(
    db_session: Session, user_factory
) -> None:
    active = user_factory()
    inactive = user_factory(
        login_identifier="demo.manager", role="MANAGER", is_active=False
    )

    assert (
        authenticate_user(db_session, "  DEMO.WAREHOUSE_STAFF ", "test-only-password")
        == active
    )
    assert (
        authenticate_user(db_session, inactive.login_identifier, "test-only-password")
        is None
    )


def test_session_stores_only_digest_and_expires_after_eight_hours(
    db_session: Session, user_factory
) -> None:
    now = datetime(2026, 9, 19, 1, 0, tzinfo=UTC)
    user = user_factory()

    created = create_session(db_session, user, now)
    stored = db_session.scalar(select(AuthSession))

    assert stored is not None
    assert stored.session_token_hash == hash_session_token(created.token)
    assert created.token.encode() != stored.session_token_hash
    assert created.expires_at == now + SESSION_LIFETIME
    assert resolve_session(db_session, created.token, now) == (stored, user)


def test_expired_revoked_and_inactive_sessions_do_not_resolve(
    db_session: Session, user_factory
) -> None:
    now = datetime(2026, 9, 19, 1, 0, tzinfo=UTC)
    user = user_factory()
    expired = create_session(db_session, user, now - SESSION_LIFETIME)
    revoked = create_session(db_session, user, now)

    assert resolve_session(db_session, expired.token, now) is None
    revoked_row, _ = resolve_session(db_session, revoked.token, now) or (None, None)
    assert revoked_row is not None
    revoke_session(db_session, revoked_row, now)
    assert resolve_session(db_session, revoked.token, now) is None

    active = create_session(db_session, user, now)
    user.is_active = False
    db_session.flush()
    assert resolve_session(db_session, active.token, now) is None


def test_cleanup_removes_only_sessions_stale_for_more_than_seven_days(
    db_session: Session, user_factory
) -> None:
    now = datetime(2026, 9, 19, 1, 0, tzinfo=UTC)
    user = user_factory()
    stale = create_session(db_session, user, now - timedelta(days=8, hours=8))
    recent = create_session(db_session, user, now - timedelta(days=1))

    assert cleanup_stale_sessions(db_session, now) == 1
    assert resolve_session(db_session, stale.token, now) is None
    assert (
        db_session.scalar(
            select(AuthSession).where(
                AuthSession.session_token_hash == hash_session_token(recent.token)
            )
        )
        is not None
    )


def test_user_role_is_read_from_database_on_each_resolution(
    db_session: Session, user_factory
) -> None:
    now = datetime(2026, 9, 19, 1, 0, tzinfo=UTC)
    user = user_factory()
    created = create_session(db_session, user, now)

    user.role = "MANAGER"
    db_session.flush()
    resolved = resolve_session(db_session, created.token, now)

    assert resolved is not None
    assert resolved[1].role == "MANAGER"


def test_login_creates_session_cookie_without_exposing_token(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user = add_user(session_factory)

    response = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": " DEMO.WAREHOUSE_STAFF ", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "login_identifier": "demo.warehouse_staff",
        "role": "WAREHOUSE_STAFF",
    }
    cookie_header = response.headers["set-cookie"]
    assert "warehouse_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert "Domain=" not in cookie_header
    token = api_client.cookies.get("warehouse_session")
    assert token is not None
    assert token not in response.text
    with session_factory() as session:
        stored = session.scalar(select(AuthSession))
        assert stored is not None
        assert stored.session_token_hash == hash_session_token(token)


def test_invalid_credentials_are_generic_and_create_no_session(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    add_user(session_factory)

    unknown = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": "missing", "password": "wrong"},
    )
    incorrect = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": "demo.warehouse_staff", "password": "wrong"},
    )

    assert unknown.status_code == incorrect.status_code == 401
    assert (
        unknown.json()
        == incorrect.json()
        == {
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid credentials.",
                "details": {},
            }
        }
    )
    with session_factory() as session:
        assert session.scalar(select(AuthSession)) is None


def test_inactive_user_cannot_login(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    add_user(session_factory, is_active=False)

    response = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": "demo.warehouse_staff", "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_valid_session_and_reads_current_database_role(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user = add_user(session_factory)
    assert api_client.get("/api/v1/auth/me").status_code == 401
    api_client.cookies.set("warehouse_session", "invalid-token")
    invalid = api_client.get("/api/v1/auth/me")
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "INVALID_SESSION"

    login = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": user.login_identifier, "password": PASSWORD},
    )
    assert login.status_code == 200
    with session_factory.begin() as session:
        stored_user = session.get(User, user.id)
        assert stored_user is not None
        stored_user.role = "MANAGER"

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "MANAGER"


def test_expired_revoked_and_inactive_sessions_return_401(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user = add_user(session_factory)

    for state in ("expired", "revoked", "inactive"):
        with session_factory.begin() as session:
            stored_user = session.get(User, user.id)
            assert stored_user is not None
            stored_user.is_active = True
            session_created_at = None
            if state == "expired":
                session_created_at = (
                    datetime.now(UTC) - SESSION_LIFETIME - timedelta(seconds=1)
                )
            created = create_session(session, stored_user, session_created_at)
            auth_session = session.scalar(
                select(AuthSession).where(
                    AuthSession.session_token_hash == hash_session_token(created.token)
                )
            )
            assert auth_session is not None
            if state == "revoked":
                auth_session.revoked_at = datetime.now(UTC)
            else:
                stored_user.is_active = False

        api_client.cookies.set("warehouse_session", created.token)
        response = api_client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_SESSION"


def test_logout_revokes_only_current_session_and_clears_cookie(
    api_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user = add_user(session_factory)
    with session_factory.begin() as session:
        stored_user = session.get(User, user.id)
        assert stored_user is not None
        other_session = create_session(session, stored_user)

    login = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": user.login_identifier, "password": PASSWORD},
    )
    current_token = api_client.cookies.get("warehouse_session")
    assert login.status_code == 200
    assert current_token is not None

    logout = api_client.post("/api/v1/auth/logout")

    assert logout.status_code == 204
    assert api_client.cookies.get("warehouse_session") is None
    with session_factory() as session:
        current = session.scalar(
            select(AuthSession).where(
                AuthSession.session_token_hash == hash_session_token(current_token)
            )
        )
        assert current is not None and current.revoked_at is not None
        assert resolve_session(session, other_session.token) is not None


def test_credentialed_cors_allows_configured_local_origin(
    api_client: TestClient,
) -> None:
    response = api_client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_samesite_none_requires_secure_cookie(monkeypatch) -> None:
    monkeypatch.setenv("COOKIE_SAMESITE", "none")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="requires COOKIE_SECURE=true"):
        get_settings()

    get_settings.cache_clear()


def test_cross_site_mode_rejects_unapproved_origin_and_non_json_mutation(
    api_client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        main_module,
        "settings",
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            cors_origins=("https://approved.example",),
            cookie_secure=True,
            cookie_samesite="none",
        ),
    )

    missing_origin = api_client.post(
        "/api/v1/auth/login",
        json={"login_identifier": "missing", "password": "secret"},
    )
    wrong_media_type = api_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://approved.example"},
    )

    assert missing_origin.status_code == 400
    assert missing_origin.json()["error"]["code"] == "INVALID_ORIGIN"
    assert wrong_media_type.status_code == 415
    assert wrong_media_type.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize(
    "content_type", ("application/jsonp", "application/json-evil", "text/json")
)
def test_cross_site_mode_rejects_non_json_media_types(
    api_client: TestClient, monkeypatch, content_type: str
) -> None:
    monkeypatch.setattr(
        main_module,
        "settings",
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            cors_origins=("https://approved.example",),
            cookie_secure=True,
            cookie_samesite="none",
        ),
    )

    response = api_client.post(
        "/api/v1/auth/login",
        content='{"login_identifier":"missing","password":"secret"}',
        headers={
            "Origin": "https://approved.example",
            "Content-Type": content_type,
        },
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize(
    "content_type",
    (
        "application/json",
        "application/json; charset=utf-8",
        "application/json;charset=UTF-8",
    ),
)
def test_cross_site_mode_accepts_json_media_type_with_optional_parameters(
    api_client: TestClient, monkeypatch, content_type: str
) -> None:
    monkeypatch.setattr(
        main_module,
        "settings",
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            cors_origins=("https://approved.example",),
            cookie_secure=True,
            cookie_samesite="none",
        ),
    )

    response = api_client.post(
        "/api/v1/auth/login",
        content='{"login_identifier":"missing","password":"secret"}',
        headers={
            "Origin": "https://approved.example",
            "Content-Type": content_type,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
