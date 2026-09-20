from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from warehouse_api.auth import (
    SESSION_COOKIE_NAME,
    Actor,
    AuthContext,
    Role,
    get_actor,
    get_auth_context,
)
from warehouse_api.auth_schemas import ActorResponse, LoginRequest
from warehouse_api.auth_service import (
    SESSION_LIFETIME,
    authenticate_user,
    create_session,
    revoke_session,
)
from warehouse_api.config import Settings, get_settings
from warehouse_api.db import get_db_session
from warehouse_api.errors import ApiError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _actor_response(actor: Actor) -> ActorResponse:
    return ActorResponse(
        id=actor.user_id,
        login_identifier=actor.login_identifier,
        role=actor.role,
    )


@router.post("/login", response_model=ActorResponse)
def login(
    command: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ActorResponse:
    user = authenticate_user(session, command.login_identifier, command.password)
    if user is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid credentials.")

    created = create_session(session, user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=created.token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        expires=created.expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return _actor_response(
        Actor(
            user_id=user.id,
            login_identifier=user.login_identifier,
            role=Role(user.role),
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    revoke_session(session, context.auth_session)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


@router.get("/me", response_model=ActorResponse)
def me(actor: Annotated[Actor, Depends(get_actor)]) -> ActorResponse:
    return _actor_response(actor)
