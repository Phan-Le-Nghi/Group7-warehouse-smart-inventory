from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, require_manager, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.schemas import (
    TransferContextResponse,
    TransferHistoryResponse,
    TransferRequest,
    TransferResponse,
)
from warehouse_api.transfer import (
    confirm_transfer,
    get_transfer_context,
    get_transfer_history,
)

router = APIRouter(prefix="/api/v1/transfers", tags=["transfer"])


@router.get("", response_model=TransferHistoryResponse)
def read_transfer_history(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_manager)],
) -> TransferHistoryResponse:
    return get_transfer_history(session)


@router.get("/context/{sku_id}", response_model=TransferContextResponse)
def read_transfer_context(
    sku_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> TransferContextResponse:
    return get_transfer_context(session, sku_id)


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    command: TransferRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
            pattern=r".*\S.*",
        ),
    ],
) -> TransferResponse:
    result = confirm_transfer(session, command, actor, idempotency_key)
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return result.response
