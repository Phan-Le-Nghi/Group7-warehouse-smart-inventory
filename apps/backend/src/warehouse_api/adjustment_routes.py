from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from warehouse_api.adjustment import (
    create_adjustment_request,
    decide_adjustment,
    get_adjustment_context,
    get_adjustment_detail,
    list_eligible_adjustment_rechecks,
    list_pending_adjustments,
)
from warehouse_api.auth import Actor, require_manager, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.errors import ApiError
from warehouse_api.schemas import (
    AdjustmentContextResponse,
    AdjustmentCreateRequest,
    AdjustmentDecisionRequest,
    AdjustmentDetailResponse,
    AdjustmentQueueResponse,
    AdjustmentResponse,
    EligibleAdjustmentRecheckListResponse,
)

router = APIRouter(prefix="/api/v1/adjustments", tags=["adjustment"])


@router.get("/eligible-rechecks", response_model=EligibleAdjustmentRecheckListResponse)
def read_eligible_adjustment_rechecks(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> EligibleAdjustmentRecheckListResponse:
    return list_eligible_adjustment_rechecks(session)


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


@router.get("", response_model=AdjustmentQueueResponse)
def read_pending_adjustments(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_manager)],
    status_filter: Annotated[str, Query(alias="status")],
) -> AdjustmentQueueResponse:
    if status_filter != "PENDING_MANAGER_DECISION":
        raise ApiError(
            422,
            "INVALID_REQUEST",
            "Only the PENDING_MANAGER_DECISION status filter is supported.",
        )
    return list_pending_adjustments(session)


@router.get("/{adjustment_id}", response_model=AdjustmentDetailResponse)
def read_adjustment_detail(
    adjustment_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_manager)],
) -> AdjustmentDetailResponse:
    return get_adjustment_detail(session, adjustment_id)


@router.post("/{adjustment_id}/decision", response_model=AdjustmentDetailResponse)
def submit_adjustment_decision(
    adjustment_id: UUID,
    command: AdjustmentDecisionRequest,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_manager)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AdjustmentDetailResponse:
    return decide_adjustment(session, adjustment_id, command, actor, idempotency_key)
