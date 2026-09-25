from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from warehouse_api.audit_discrepancy import (
    create_audit_recheck,
    get_audit_discrepancy,
    list_audit_discrepancies,
)
from warehouse_api.auth import Actor, require_manager
from warehouse_api.db import get_db_session
from warehouse_api.schemas import (
    AuditDiscrepancyItem,
    AuditDiscrepancyListResponse,
    AuditRecheckRequest,
    AuditRecheckResponse,
)

router = APIRouter(prefix="/api/v1/audit-discrepancies", tags=["audit"])


@router.get("", response_model=AuditDiscrepancyListResponse)
def read_audit_discrepancies(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_manager)],
) -> AuditDiscrepancyListResponse:
    return list_audit_discrepancies(session)


@router.get("/{audit_line_id}", response_model=AuditDiscrepancyItem)
def read_audit_discrepancy(
    audit_line_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_manager)],
) -> AuditDiscrepancyItem:
    return get_audit_discrepancy(session, audit_line_id)


@router.post(
    "/{audit_line_id}/rechecks",
    response_model=AuditRecheckResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_audit_recheck(
    audit_line_id: UUID,
    command: AuditRecheckRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_manager)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AuditRecheckResponse:
    result = create_audit_recheck(
        session, audit_line_id, command, actor, idempotency_key
    )
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return result.response
