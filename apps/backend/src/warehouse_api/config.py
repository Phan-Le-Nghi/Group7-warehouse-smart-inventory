from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
from os import getenv
from re import fullmatch
from typing import Literal
from urllib.parse import parse_qs, urlsplit, urlunsplit

AppEnvironment = Literal["development", "test", "staging", "production"]

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://warehouse_dev:warehouse_dev_only@localhost:5432/warehouse"
)
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:4173"
DEPLOYED_ENVIRONMENTS = frozenset({"staging", "production"})


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    cookie_secure: bool
    cookie_samesite: Literal["lax", "strict", "none"]
    app_env: AppEnvironment = "development"


def _read_app_env() -> AppEnvironment:
    value = getenv("APP_ENV", "development").strip().lower()
    if value not in {"development", "test", "staging", "production"}:
        raise RuntimeError("APP_ENV must be development, test, staging, or production")
    return value  # type: ignore[return-value]


def _read_bool(name: str, default: bool) -> bool:
    raw_value = getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value")


def _read_samesite() -> Literal["lax", "strict", "none"]:
    value = getenv("COOKIE_SAMESITE", "lax").strip().lower()
    if value not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE must be lax, strict, or none")
    return value  # type: ignore[return-value]


def _is_valid_hostname(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        ip_address(hostname)
        return True
    except ValueError:
        pass
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    if len(ascii_hostname) > 253:
        return False
    return all(
        fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
        for label in ascii_hostname.split(".")
    )


def _is_loopback_hostname(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def _read_cors_origins(app_env: AppEnvironment) -> tuple[str, ...]:
    raw_origins = getenv("CORS_ORIGINS")
    if raw_origins is None:
        if app_env in DEPLOYED_ENVIRONMENTS:
            raise RuntimeError(f"CORS_ORIGINS is required when APP_ENV={app_env}")
        raw_origins = DEFAULT_CORS_ORIGINS

    origins = tuple(item.strip() for item in raw_origins.split(","))
    for origin in origins:
        if not origin or origin == "*":
            raise RuntimeError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        parsed = urlsplit(origin)
        try:
            port = parsed.port
        except ValueError as error:
            raise RuntimeError("CORS_ORIGINS contains an invalid origin") from error
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or not _is_valid_hostname(parsed.hostname)
            or any(character.isspace() for character in origin)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.netloc.endswith(":")
            or parsed.path
            or parsed.query
            or parsed.fragment
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise RuntimeError("CORS_ORIGINS contains an invalid origin")
        if app_env in DEPLOYED_ENVIRONMENTS and (
            parsed.scheme != "https" or _is_loopback_hostname(parsed.hostname)
        ):
            raise RuntimeError(
                "CORS_ORIGINS must contain only non-loopback HTTPS origins "
                f"when APP_ENV={app_env}"
            )
    return origins


def _read_database_url(app_env: AppEnvironment) -> str:
    database_url = getenv("DATABASE_URL")
    if database_url is None:
        if app_env in DEPLOYED_ENVIRONMENTS:
            raise RuntimeError(f"DATABASE_URL is required when APP_ENV={app_env}")
        return DEFAULT_DATABASE_URL

    database_url = database_url.strip()
    parsed = urlsplit(database_url)
    if app_env not in DEPLOYED_ENVIRONMENTS and parsed.scheme.startswith("sqlite"):
        return database_url
    if parsed.scheme == "postgresql":
        parsed = parsed._replace(scheme="postgresql+psycopg")
        database_url = urlunsplit(parsed)
    if parsed.scheme != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use PostgreSQL with the psycopg driver")
    if app_env in DEPLOYED_ENVIRONMENTS:
        sslmode = parse_qs(parsed.query).get("sslmode", [])
        if sslmode != ["require"]:
            raise RuntimeError(
                f"DATABASE_URL must include sslmode=require when APP_ENV={app_env}"
            )
    return database_url


@lru_cache
def get_settings() -> Settings:
    app_env = _read_app_env()
    settings = Settings(
        app_env=app_env,
        database_url=_read_database_url(app_env),
        cors_origins=_read_cors_origins(app_env),
        cookie_secure=_read_bool("COOKIE_SECURE", False),
        cookie_samesite=_read_samesite(),
    )
    if settings.cookie_samesite == "none" and not settings.cookie_secure:
        raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
    if settings.app_env in DEPLOYED_ENVIRONMENTS:
        if not settings.cookie_secure:
            raise RuntimeError(
                f"COOKIE_SECURE must be true when APP_ENV={settings.app_env}"
            )
        if settings.cookie_samesite != "lax":
            raise RuntimeError(
                f"COOKIE_SAMESITE must be lax when APP_ENV={settings.app_env}"
            )
    return settings
