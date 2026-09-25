from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from warehouse_api.auth_service import resolve_session
from warehouse_api.db import get_db_session
from warehouse_api.errors import ApiError
from warehouse_api.models import AuthSession

SESSION_COOKIE_NAME = "warehouse_session"


class Role(StrEnum):
    WAREHOUSE_STAFF = "WAREHOUSE_STAFF"
    MANAGER = "MANAGER"
    PURCHASING = "PURCHASING"
    ADMIN = "ADMIN"


WAREHOUSE_STAFF = Role.WAREHOUSE_STAFF


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    login_identifier: str
    role: Role


@dataclass(frozen=True, slots=True)
class AuthContext:
    actor: Actor
    auth_session: AuthSession


def get_auth_context(
    session: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> AuthContext:
    if session_token is None:
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
    resolved = resolve_session(session, session_token)
    if resolved is None:
        raise ApiError(401, "INVALID_SESSION", "The session is not valid.")
    auth_session, user = resolved
    return AuthContext(
        actor=Actor(
            user_id=user.id,
            login_identifier=user.login_identifier,
            role=Role(user.role),
        ),
        auth_session=auth_session,
    )


def get_actor(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> Actor:
    return context.actor


def require_roles(*roles: Role) -> Callable[[Actor], Actor]:
    allowed_roles = frozenset(roles)
    if not allowed_roles:
        raise ValueError("require_roles needs at least one role")

    def dependency(actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
        if actor.role not in allowed_roles:
            raise ApiError(
                403,
                "FORBIDDEN",
                "The authenticated actor does not have the required role.",
                {"required_roles": sorted(role.value for role in allowed_roles)},
            )
        return actor

    return dependency


require_warehouse_staff = require_roles(Role.WAREHOUSE_STAFF)
require_manager = require_roles(Role.MANAGER)
