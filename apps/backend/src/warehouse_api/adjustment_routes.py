from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from warehouse_api.adjustment import (
    create_adjustment_request,
    get_adjustment_context,
)
from warehouse_api.auth import Actor, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.schemas import (
    AdjustmentContextResponse,
    AdjustmentCreateRequest,
    AdjustmentResponse,
)

router = APIRouter(prefix="/api/v1/adjustments", tags=["adjustment"])


@router.get("/context/{audit_recheck_id}", response_model=AdjustmentContextResponse)
def read_adjustment_context(
    audit_recheck_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> AdjustmentContextResponse:
    return get_adjustment_context(session, audit_recheck_id)


@router.post(
    "",
    response_model=AdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_adjustment_request(
    command: AdjustmentCreateRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AdjustmentResponse:
    result = create_adjustment_request(session, command, actor, idempotency_key)
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return result.response
