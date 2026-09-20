import pytest

from warehouse_api.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
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


def test_cors_origins_accept_explicit_http_and_https_origins(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:4173,https://example.com",
    )

    assert get_settings().cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "https://example.com",
    )
