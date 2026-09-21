import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import Receive, ReceiveLine, Sku
from warehouse_api.schemas import (
    ReceiveContextResponse,
    ReceiveLineState,
    ReceiveRecordRequest,
    ReceiveReferenceState,
    ReferenceReviewResponse,
)

REFERENCE_MATCH = "REFERENCE_MATCH"
REFERENCE_MISMATCH = "REFERENCE_MISMATCH"

logger = logging.getLogger(__name__)


def _log_rejection(receive_id: UUID, actor: Actor, code: str) -> None:
    logger.warning(
        "receive_command_rejected",
        extra={
            "receive_event": {
                "receive_id": str(receive_id),
                "actor_user_id": str(actor.user_id),
                "reason": code,
            }
        },
    )


def is_receive_putaway_eligible(receive: Receive) -> bool:
    if receive.recorded_at is None:
        return False
    if receive.reference_match_status == REFERENCE_MATCH:
        return True
    return (
        receive.reference_match_status == REFERENCE_MISMATCH
        and receive.reference_reviewed_by_user_id is not None
        and receive.reference_reviewed_at is not None
    )


def ensure_putaway_eligible(receive: Receive, receive_line: ReceiveLine) -> None:
    if receive_line.actual_quantity is None:
        raise ApiError(
            409,
            "RECEIVE_NOT_RECORDED",
            "Receive facts have not been recorded for this line.",
        )
    if receive.reference_match_status == REFERENCE_MISMATCH and (
        receive.reference_reviewed_by_user_id is None
        or receive.reference_reviewed_at is None
    ):
        raise ApiError(
            409,
            "REFERENCE_REVIEW_REQUIRED",
            "The Receive reference mismatch must be reviewed before Putaway.",
        )


def _receive_rows(session: Session, receive_id: UUID) -> list[tuple[ReceiveLine, Sku]]:
    statement = (
        select(ReceiveLine, Sku)
        .join(Sku, Sku.id == ReceiveLine.sku_id)
        .where(ReceiveLine.receive_id == receive_id)
        .order_by(ReceiveLine.id)
    )
    return list(session.execute(statement).tuples())


def _require_prepared(receive: Receive, rows: list[tuple[ReceiveLine, Sku]]) -> None:
    if (
        receive.expected_reference is None
        or not receive.expected_reference.strip()
        or not rows
        or any(line.expected_quantity is None for line, _sku in rows)
    ):
        raise ApiError(
            409,
            "RECEIVE_CONTEXT_NOT_PREPARED",
            "The Receive expected context has not been prepared.",
        )


def _context_response(
    receive: Receive, rows: list[tuple[ReceiveLine, Sku]]
) -> ReceiveContextResponse:
    expected_reference = receive.expected_reference
    if expected_reference is None:  # guarded by _require_prepared
        raise RuntimeError("Prepared Receive is missing its expected reference")
    lines: list[ReceiveLineState] = []
    for line, sku in rows:
        if line.expected_quantity is None:  # guarded by _require_prepared
            raise RuntimeError("Prepared Receive line is missing expected quantity")
        lines.append(
            ReceiveLineState(
                receive_line_id=line.id,
                sku_id=line.sku_id,
                sku=sku.code,
                expected_quantity=line.expected_quantity,
                actual_quantity=line.actual_quantity,
                quantity_discrepancy=line.quantity_discrepancy,
            )
        )
    return ReceiveContextResponse(
        receive_id=receive.id,
        warehouse_id=receive.warehouse_id,
        reference=ReceiveReferenceState(
            expected=expected_reference.strip(),
            document=receive.document_reference,
            match_status=receive.reference_match_status,
            reviewed_by_user_id=receive.reference_reviewed_by_user_id,
            reviewed_at=receive.reference_reviewed_at,
        ),
        recorded_at=receive.recorded_at,
        putaway_eligible=is_receive_putaway_eligible(receive),
        lines=lines,
    )


def get_receive_context(session: Session, receive_id: UUID) -> ReceiveContextResponse:
    receive = session.get(Receive, receive_id)
    if receive is None:
        raise ApiError(404, "RECEIVE_NOT_FOUND", "Receive was not found.")
    rows = _receive_rows(session, receive_id)
    _require_prepared(receive, rows)
    return _context_response(receive, rows)


def _log_after_commit(
    session: Session, message: str, details: dict[str, object]
) -> None:
    def log_commit(_session: Session) -> None:
        logger.info(message, extra={"receive_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def record_receive(
    session: Session, command: ReceiveRecordRequest, actor: Actor
) -> ReceiveContextResponse:
    receive = session.get(Receive, command.receive_id, with_for_update=True)
    if receive is None:
        _log_rejection(command.receive_id, actor, "RECEIVE_NOT_FOUND")
        raise ApiError(404, "RECEIVE_NOT_FOUND", "Receive was not found.")
    if receive.recorded_at is not None:
        _log_rejection(receive.id, actor, "RECEIVE_ALREADY_RECORDED")
        raise ApiError(
            409,
            "RECEIVE_ALREADY_RECORDED",
            "Receive facts have already been recorded.",
        )

    rows = _receive_rows(session, receive.id)
    try:
        _require_prepared(receive, rows)
    except ApiError as error:
        _log_rejection(receive.id, actor, error.code)
        raise
    prepared_by_id = {line.id: line for line, _sku in rows}
    submitted_ids = [item.receive_line_id for item in command.lines]
    submitted_set = set(submitted_ids)
    if len(submitted_ids) != len(submitted_set):
        _log_rejection(receive.id, actor, "INCOMPLETE_RECEIVE_CONTEXT")
        raise ApiError(
            422,
            "INCOMPLETE_RECEIVE_CONTEXT",
            "Each prepared Receive line must be submitted exactly once.",
        )
    foreign_ids = submitted_set - prepared_by_id.keys()
    if foreign_ids:
        _log_rejection(receive.id, actor, "RECEIVE_CONTEXT_MISMATCH")
        raise ApiError(
            409,
            "RECEIVE_CONTEXT_MISMATCH",
            "A supplied line does not belong to the Receive context.",
        )
    if submitted_set != prepared_by_id.keys():
        _log_rejection(receive.id, actor, "INCOMPLETE_RECEIVE_CONTEXT")
        raise ApiError(
            422,
            "INCOMPLETE_RECEIVE_CONTEXT",
            "The request must contain the complete prepared Receive line set.",
        )

    document_reference = command.document_reference.strip()
    if not document_reference:
        _log_rejection(receive.id, actor, "INVALID_REQUEST")
        raise ApiError(422, "INVALID_REQUEST", "Document reference must not be empty.")
    expected_reference = receive.expected_reference
    if expected_reference is None:  # guarded by _require_prepared
        raise RuntimeError("Prepared Receive is missing its expected reference")
    expected_reference = expected_reference.strip()

    for item in command.lines:
        line = prepared_by_id[item.receive_line_id]
        if line.sku_id != item.sku_id:
            _log_rejection(receive.id, actor, "RECEIVE_CONTEXT_MISMATCH")
            raise ApiError(
                409,
                "RECEIVE_CONTEXT_MISMATCH",
                "SKU does not match the prepared Receive line.",
            )
        if item.actual_quantity < 0:
            _log_rejection(receive.id, actor, "INVALID_QUANTITY")
            raise ApiError(
                422,
                "INVALID_QUANTITY",
                "Actual quantity must be a non-negative integer.",
            )

    now = datetime.now(UTC)
    receive.expected_reference = expected_reference
    receive.document_reference = document_reference
    receive.reference_match_status = (
        REFERENCE_MATCH
        if document_reference == expected_reference
        else REFERENCE_MISMATCH
    )
    receive.recorded_by_user_id = actor.user_id
    receive.recorded_at = now
    for item in command.lines:
        line = prepared_by_id[item.receive_line_id]
        expected_quantity = line.expected_quantity
        if expected_quantity is None:  # guarded by _require_prepared
            raise RuntimeError("Prepared Receive line is missing expected quantity")
        line.actual_quantity = item.actual_quantity
        line.quantity_discrepancy = item.actual_quantity - expected_quantity

    session.flush()
    _log_after_commit(
        session,
        "receive_recorded",
        {
            "receive_id": str(receive.id),
            "actor_user_id": str(actor.user_id),
            "line_count": len(rows),
            "has_quantity_discrepancy": any(
                line.quantity_discrepancy != 0 for line, _sku in rows
            ),
            "reference_match_status": receive.reference_match_status,
            "outcome": "RECEIVE_RECORDED",
        },
    )
    return _context_response(receive, rows)


def review_reference_mismatch(
    session: Session, receive_id: UUID, actor: Actor
) -> ReferenceReviewResponse:
    receive = session.get(Receive, receive_id, with_for_update=True)
    if receive is None:
        _log_rejection(receive_id, actor, "RECEIVE_NOT_FOUND")
        raise ApiError(404, "RECEIVE_NOT_FOUND", "Receive was not found.")
    if receive.recorded_at is None:
        _log_rejection(receive.id, actor, "RECEIVE_NOT_RECORDED")
        raise ApiError(
            409, "RECEIVE_NOT_RECORDED", "Receive facts have not been recorded."
        )
    if receive.reference_match_status != REFERENCE_MISMATCH:
        _log_rejection(receive.id, actor, "REFERENCE_REVIEW_NOT_REQUIRED")
        raise ApiError(
            409,
            "REFERENCE_REVIEW_NOT_REQUIRED",
            "The Receive reference does not require mismatch review.",
        )
    if (
        receive.reference_reviewed_by_user_id is not None
        or receive.reference_reviewed_at is not None
    ):
        _log_rejection(receive.id, actor, "REFERENCE_ALREADY_REVIEWED")
        raise ApiError(
            409,
            "REFERENCE_ALREADY_REVIEWED",
            "The Receive reference mismatch has already been reviewed.",
        )

    receive.reference_reviewed_by_user_id = actor.user_id
    receive.reference_reviewed_at = datetime.now(UTC)
    session.flush()
    _log_after_commit(
        session,
        "receive_reference_reviewed",
        {
            "receive_id": str(receive.id),
            "actor_user_id": str(actor.user_id),
            "reference_match_status": receive.reference_match_status,
            "outcome": "REFERENCE_MISMATCH_ACKNOWLEDGED",
        },
    )
    return ReferenceReviewResponse(
        receive_id=receive.id,
        match_status=receive.reference_match_status,
        reviewed_by_user_id=actor.user_id,
        reviewed_at=receive.reference_reviewed_at,
        putaway_eligible=True,
    )
