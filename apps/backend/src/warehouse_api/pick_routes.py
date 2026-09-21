from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.pick import confirm_pick, get_pick_context
from warehouse_api.schemas import PickContextResponse, PickRequest, PickResponse

router = APIRouter(prefix="/api/v1/picks", tags=["pick"])


@router.get("/context/{pick_id}", response_model=PickContextResponse)
def read_pick_context(
    pick_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> PickContextResponse:
    return get_pick_context(session, pick_id)


@router.post("", response_model=PickResponse, status_code=status.HTTP_201_CREATED)
def create_pick_result(
    command: PickRequest,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> PickResponse:
    return confirm_pick(session, command, actor)
