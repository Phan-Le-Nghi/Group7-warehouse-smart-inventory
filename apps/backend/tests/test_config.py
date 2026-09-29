import pytest

from warehouse_api.config import DEFAULT_DATABASE_URL, get_settings


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch):
    for name in (
        "APP_ENV",
        "DATABASE_URL",
        "CORS_ORIGINS",
        "COOKIE_SECURE",
        "COOKIE_SAMESITE",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "origins",
    (
        "*",
        "",
        "https://example.com,",
        "https://example.com/path",
        "https://example.com?query=value",
        "https://example.com#fragment",
        "example.com",
        "ftp://example.com",
        "https://user@example.com",
        "https://example.com:invalid",
        "https://example.com:",
        "https://exa mple.com",
        "https://bad_host.example",
    ),
)
def test_cors_origins_reject_unsafe_or_malformed_values(
    monkeypatch, origins: str
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", origins)

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        get_settings()


def test_development_config_keeps_safe_local_defaults() -> None:
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:4173",
    )
    assert settings.cookie_secure is False
    assert settings.cookie_samesite == "lax"


@pytest.mark.parametrize("app_env", ("staging", "production"))
def test_deployed_config_accepts_approved_same_origin_topology(
    monkeypatch, app_env: str
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com:5432/warehouse?sslmode=require",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://warehouse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("COOKIE_SAMESITE", "lax")

    settings = get_settings()

    assert settings.app_env == app_env
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.cors_origins == ("https://warehouse.example.com",)
    assert settings.cookie_secure is True
    assert settings.cookie_samesite == "lax"


@pytest.mark.parametrize("missing_name", ("DATABASE_URL", "CORS_ORIGINS"))
def test_deployed_config_requires_critical_variables(
    monkeypatch, missing_name: str
) -> None:
    values = {
        "DATABASE_URL": (
            "postgresql+psycopg://user:password@db.example.com/warehouse"
            "?sslmode=require"
        ),
        "CORS_ORIGINS": "https://warehouse.example.com",
    }
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    for name, value in values.items():
        if name != missing_name:
            monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=missing_name):
        get_settings()


def test_deployed_config_requires_secure_cookie(monkeypatch) -> None:
    _set_valid_deployed_environment(monkeypatch)
    monkeypatch.setenv("COOKIE_SECURE", "false")

    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        get_settings()


@pytest.mark.parametrize(
    "origin", ("http://warehouse.example.com", "https://localhost:5173")
)
def test_deployed_config_rejects_non_public_https_cors(
    monkeypatch, origin: str
) -> None:
    _set_valid_deployed_environment(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", origin)

    with pytest.raises(RuntimeError, match="non-loopback HTTPS"):
        get_settings()


@pytest.mark.parametrize(
    ("database_url", "message"),
    (
        ("sqlite:///warehouse.db", "PostgreSQL"),
        (
            "postgresql+psycopg://user:password@db.example.com/warehouse",
            "sslmode=require",
        ),
        (
            "postgresql+psycopg://user:password@db.example.com/warehouse"
            "?sslmode=prefer",
            "sslmode=require",
        ),
    ),
)
def test_deployed_config_requires_postgresql_tls(
    monkeypatch, database_url: str, message: str
) -> None:
    _set_valid_deployed_environment(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match=message):
        get_settings()


def test_deployed_config_requires_lax_samesite(monkeypatch) -> None:
    _set_valid_deployed_environment(monkeypatch)
    monkeypatch.setenv("COOKIE_SAMESITE", "strict")

    with pytest.raises(RuntimeError, match="COOKIE_SAMESITE"):
        get_settings()


def _set_valid_deployed_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@db.example.com/warehouse?sslmode=require",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://warehouse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("COOKIE_SAMESITE", "lax")
