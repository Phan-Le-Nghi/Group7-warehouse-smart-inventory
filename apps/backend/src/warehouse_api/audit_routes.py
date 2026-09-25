from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from warehouse_api.audit import create_audit, get_audit_context
from warehouse_api.auth import Actor, require_warehouse_staff
from warehouse_api.db import get_db_session
from warehouse_api.schemas import AuditContextResponse, AuditRequest, AuditResponse

router = APIRouter(prefix="/api/v1/audits", tags=["audit"])


@router.get("/context", response_model=AuditContextResponse)
def read_audit_context(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_warehouse_staff)],
) -> AuditContextResponse:
    return get_audit_context(session)


@router.post("", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
def submit_audit(
    command: AuditRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    actor: Annotated[Actor, Depends(require_warehouse_staff)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AuditResponse:
    result = create_audit(session, command, actor, idempotency_key)
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return result.response
