from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.putaway import (
    confirm_putaway,
    get_putaway_context,
    list_eligible_putaway_lines,
)
from warehouse_api.schemas import (
    PutawayContextResponse,
    PutawayQueueResponse,
    PutawayRequest,
    PutawayResponse,
)

router = APIRouter(prefix="/api/v1", tags=["putaway"])


@router.get("/putaways/eligible-lines", response_model=PutawayQueueResponse)
def read_eligible_putaway_lines(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> PutawayQueueResponse:
    return list_eligible_putaway_lines(session)


@router.get(
    "/putaways/context/{receive_line_id}", response_model=PutawayContextResponse
)
def read_putaway_context(
    receive_line_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> PutawayContextResponse:
    return get_putaway_context(session, receive_line_id)


@router.post(
    "/putaways",
    response_model=PutawayResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_putaway(
    command: PutawayRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ],
) -> PutawayResponse:
    result = confirm_putaway(session, command, idempotency_key)
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return result.response
