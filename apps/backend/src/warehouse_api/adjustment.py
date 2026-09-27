import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, aliased

from warehouse_api.auth import Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AdjustRequest,
    AuditLine,
    AuditRecheck,
    AuditSession,
    InternalLocation,
    Sku,
    User,
    Warehouse,
)
from warehouse_api.schemas import (
    AdjustmentActor,
    AdjustmentContextResponse,
    AdjustmentCreateRequest,
    AdjustmentLocation,
    AdjustmentOriginalAuditEvidence,
    AdjustmentRecheckEvidence,
    AdjustmentResponse,
    AdjustmentSku,
    ExistingAdjustmentSummary,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AdjustmentCreationResult:
    response: AdjustmentResponse
    replayed: bool


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _canonical_warehouse_id(session: Session) -> UUID:
    warehouse_ids = list(session.scalars(select(Warehouse.id).limit(2)))
    if len(warehouse_ids) != 1:
        raise ApiError(
            500,
            "CANONICAL_WAREHOUSE_UNAVAILABLE",
            "The canonical Warehouse is unavailable.",
        )
    return warehouse_ids[0]


def _fingerprint(audit_recheck_id: UUID, reason: str) -> str:
    canonical = json.dumps(
        {"audit_recheck_id": str(audit_recheck_id), "reason": reason},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _source_statement(warehouse_id: UUID):
    requester = aliased(User, name="adjustment_requester")
    return (
        select(
            AuditRecheck,
            AuditLine,
            AuditSession,
            Sku,
            InternalLocation,
            AdjustRequest,
            requester,
        )
        .join(AuditLine, AuditLine.id == AuditRecheck.audit_line_id)
        .join(AuditSession, AuditSession.id == AuditLine.audit_id)
        .join(Sku, Sku.id == AuditLine.sku_id)
        .join(InternalLocation, InternalLocation.id == AuditLine.location_id)
        .outerjoin(AdjustRequest, AdjustRequest.audit_recheck_id == AuditRecheck.id)
        .outerjoin(requester, requester.id == AdjustRequest.requested_by_user_id)
        .where(
            AuditSession.warehouse_id == warehouse_id,
            InternalLocation.warehouse_id == warehouse_id,
        )
    )


def _existing_summary(
    adjustment: AdjustRequest | None, requester: User | None
) -> ExistingAdjustmentSummary | None:
    if adjustment is None:
        return None
    if requester is None:
        raise RuntimeError("Adjust request references a missing requester")
    return ExistingAdjustmentSummary(
        adjustment_id=adjustment.id,
        reason=adjustment.reason,
        requested_change=adjustment.requested_change,
        status="PENDING_MANAGER_DECISION",
        requested_by=AdjustmentActor(
            user_id=requester.id,
            login_identifier=requester.login_identifier,
        ),
        requested_at=_aware(adjustment.requested_at),
    )


def _context_from_row(row: tuple[object, ...]) -> AdjustmentContextResponse:
    recheck, line, audit, sku, location, adjustment, requester = row
    if not isinstance(recheck, AuditRecheck) or not isinstance(line, AuditLine):
        raise RuntimeError("Adjustment query returned invalid recheck evidence")
    if not isinstance(audit, AuditSession) or not isinstance(sku, Sku):
        raise RuntimeError("Adjustment query returned invalid Audit evidence")
    if not isinstance(location, InternalLocation):
        raise RuntimeError("Adjustment query returned an invalid location")
    if adjustment is not None and not isinstance(adjustment, AdjustRequest):
        raise RuntimeError("Adjustment query returned an invalid request")
    if requester is not None and not isinstance(requester, User):
        raise RuntimeError("Adjustment query returned an invalid requester")
    requested_change = (
        recheck.recheck_physical_quantity - recheck.recheck_system_quantity
    )
    return AdjustmentContextResponse(
        audit_recheck_id=recheck.id,
        warehouse_id=audit.warehouse_id,
        sku=AdjustmentSku(id=sku.id, code=sku.code),
        location=AdjustmentLocation(id=location.id, code=location.code),
        original_audit=AdjustmentOriginalAuditEvidence(
            audit_id=audit.id,
            audit_line_id=line.id,
            system_quantity=line.system_quantity,
            physical_quantity=line.physical_quantity,
            quantity_discrepancy=line.quantity_discrepancy,
        ),
        recheck=AdjustmentRecheckEvidence(
            recheck_system_quantity=recheck.recheck_system_quantity,
            recheck_physical_quantity=recheck.recheck_physical_quantity,
            recheck_quantity_discrepancy=recheck.recheck_quantity_discrepancy,
            result="MISMATCH",
            performed_at=_aware(recheck.performed_at),
        ),
        requested_change=requested_change,
        existing_adjustment=_existing_summary(adjustment, requester),
    )


def get_adjustment_context(
    session: Session, audit_recheck_id: UUID
) -> AdjustmentContextResponse:
    warehouse_id = _canonical_warehouse_id(session)
    row = session.execute(
        _source_statement(warehouse_id).where(AuditRecheck.id == audit_recheck_id)
    ).one_or_none()
    if row is None:
        raise ApiError(
            404,
            "AUDIT_RECHECK_NOT_FOUND",
            "The Audit recheck was not found.",
        )
    recheck = row[0]
    if not isinstance(recheck, AuditRecheck):
        raise RuntimeError("Adjustment query returned invalid recheck evidence")
    if recheck.result != "MISMATCH":
        raise ApiError(
            409,
            "ADJUSTMENT_NOT_ELIGIBLE",
            "The Audit recheck is not eligible for an Adjust request.",
        )
    return _context_from_row(tuple(row))


def _response_for_adjustment(
    session: Session, adjustment: AdjustRequest
) -> AdjustmentResponse:
    row = session.execute(
        select(
            AuditSession.warehouse_id,
            Sku,
            InternalLocation,
            User,
        )
        .select_from(AdjustRequest)
        .join(
            AuditRecheck,
            AuditRecheck.id == AdjustRequest.audit_recheck_id,
        )
        .join(AuditLine, AuditLine.id == AuditRecheck.audit_line_id)
        .join(AuditSession, AuditSession.id == AuditLine.audit_id)
        .join(Sku, Sku.id == AdjustRequest.sku_id)
        .join(InternalLocation, InternalLocation.id == AdjustRequest.location_id)
        .join(User, User.id == AdjustRequest.requested_by_user_id)
        .where(AdjustRequest.id == adjustment.id)
    ).one()
    warehouse_id, sku, location, requester = row
    return AdjustmentResponse(
        adjustment_id=adjustment.id,
        audit_recheck_id=adjustment.audit_recheck_id,
        warehouse_id=warehouse_id,
        sku=AdjustmentSku(id=sku.id, code=sku.code),
        location=AdjustmentLocation(id=location.id, code=location.code),
        recheck_system_quantity_snapshot=(adjustment.recheck_system_quantity_snapshot),
        recheck_physical_quantity_snapshot=(
            adjustment.recheck_physical_quantity_snapshot
        ),
        requested_change=adjustment.requested_change,
        reason=adjustment.reason,
        status="PENDING_MANAGER_DECISION",
        requested_by=AdjustmentActor(
            user_id=requester.id,
            login_identifier=requester.login_identifier,
        ),
        requested_at=_aware(adjustment.requested_at),
    )


def _result_for_key(
    session: Session, idempotency_key: str, fingerprint: str
) -> AdjustmentCreationResult | None:
    existing = session.scalar(
        select(AdjustRequest).where(AdjustRequest.idempotency_key == idempotency_key)
    )
    if existing is None:
        return None
    if existing.request_fingerprint != fingerprint:
        raise ApiError(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            "The idempotency key was already used for a different request.",
        )
    return AdjustmentCreationResult(
        response=_response_for_adjustment(session, existing), replayed=True
    )


def _insert_for_dialect(session: Session):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql_insert(AdjustRequest)
    if dialect == "sqlite":
        return sqlite_insert(AdjustRequest)
    raise RuntimeError(f"Unsupported database dialect: {dialect}")


def _log_after_commit(session: Session, adjustment: AdjustRequest) -> None:
    details = {
        "adjustment_id": str(adjustment.id),
        "audit_recheck_id": str(adjustment.audit_recheck_id),
        "actor_user_id": str(adjustment.requested_by_user_id),
        "status": adjustment.status,
    }

    def log_commit(_session: Session) -> None:
        logger.info("adjustment_requested", extra={"adjustment_request_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def create_adjustment_request(
    session: Session,
    command: AdjustmentCreateRequest,
    actor: Actor,
    idempotency_key: str | None,
) -> AdjustmentCreationResult:
    if (
        idempotency_key is None
        or not idempotency_key
        or idempotency_key.isspace()
        or len(idempotency_key) > 255
    ):
        raise ApiError(
            422,
            "INVALID_IDEMPOTENCY_KEY",
            "A non-blank Idempotency-Key of at most 255 characters is required.",
        )
    reason = command.reason.strip()
    if not reason or len(reason) > 500:
        raise ApiError(
            422,
            "INVALID_REASON",
            "Reason must contain from 1 to 500 characters after trimming.",
        )
    fingerprint = _fingerprint(command.audit_recheck_id, reason)
    replay = _result_for_key(session, idempotency_key, fingerprint)
    if replay is not None:
        return replay

    context = get_adjustment_context(session, command.audit_recheck_id)
    if context.existing_adjustment is not None:
        raise ApiError(
            409,
            "ADJUSTMENT_ALREADY_EXISTS",
            "An Adjust request already exists for this Audit recheck.",
        )

    adjustment_id = uuid4()
    requested_at = datetime.now(UTC)
    claim = (
        _insert_for_dialect(session)
        .values(
            id=adjustment_id,
            audit_recheck_id=command.audit_recheck_id,
            sku_id=context.sku.id,
            location_id=context.location.id,
            recheck_system_quantity_snapshot=(context.recheck.recheck_system_quantity),
            recheck_physical_quantity_snapshot=(
                context.recheck.recheck_physical_quantity
            ),
            requested_change=context.requested_change,
            reason=reason,
            status="PENDING_MANAGER_DECISION",
            requested_by_user_id=actor.user_id,
            requested_at=requested_at,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        .on_conflict_do_nothing()
        .returning(AdjustRequest.id)
    )
    claimed_id = session.scalar(claim)
    if claimed_id is None:
        concurrent_replay = _result_for_key(session, idempotency_key, fingerprint)
        if concurrent_replay is not None:
            return concurrent_replay
        concurrent_request = session.scalar(
            select(AdjustRequest).where(
                AdjustRequest.audit_recheck_id == command.audit_recheck_id
            )
        )
        if concurrent_request is not None:
            raise ApiError(
                409,
                "ADJUSTMENT_ALREADY_EXISTS",
                "An Adjust request already exists for this Audit recheck.",
            )
        raise RuntimeError("Adjust request conflict did not expose a persisted row")

    adjustment = session.get(AdjustRequest, claimed_id)
    if adjustment is None:
        raise RuntimeError("Claimed Adjust request row could not be loaded")
    _log_after_commit(session, adjustment)
    return AdjustmentCreationResult(
        response=_response_for_adjustment(session, adjustment), replayed=False
    )
