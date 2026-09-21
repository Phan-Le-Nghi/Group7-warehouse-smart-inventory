from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.receive import (
    get_receive_context,
    record_receive,
    review_reference_mismatch,
)
from warehouse_api.schemas import (
    ReceiveContextResponse,
    ReceiveRecordRequest,
    ReferenceReviewRequest,
    ReferenceReviewResponse,
)

router = APIRouter(prefix="/api/v1/receives", tags=["receive"])


@router.get("/context/{receive_id}", response_model=ReceiveContextResponse)
def read_receive_context(
    receive_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> ReceiveContextResponse:
    return get_receive_context(session, receive_id)


@router.post(
    "", response_model=ReceiveContextResponse, status_code=status.HTTP_201_CREATED
)
def create_receive_record(
    command: ReceiveRecordRequest,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> ReceiveContextResponse:
    return record_receive(session, command, actor)


@router.post("/{receive_id}/reference-review", response_model=ReferenceReviewResponse)
def acknowledge_reference_mismatch(
    receive_id: UUID,
    _command: ReferenceReviewRequest,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> ReferenceReviewResponse:
    return review_reference_mismatch(session, receive_id, actor)
