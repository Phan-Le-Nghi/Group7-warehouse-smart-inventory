from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
from os import getenv
from re import fullmatch
from typing import Literal
from urllib.parse import urlsplit

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://warehouse_dev:warehouse_dev_only@localhost:5432/warehouse"
)


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    cookie_secure: bool
    cookie_samesite: Literal["lax", "strict", "none"]


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


def _read_cors_origins() -> tuple[str, ...]:
    raw_origins = getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:4173")
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
    return origins


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        database_url=getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        cors_origins=_read_cors_origins(),
        cookie_secure=_read_bool("COOKIE_SECURE", False),
        cookie_samesite=_read_samesite(),
    )
    if settings.cookie_samesite == "none" and not settings.cookie_secure:
        raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
    return settings
