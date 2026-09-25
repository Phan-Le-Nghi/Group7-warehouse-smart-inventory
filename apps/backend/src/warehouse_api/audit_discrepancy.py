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
    AuditLine,
    AuditRecheck,
    AuditSession,
    InternalLocation,
    Sku,
    StockBalance,
    User,
    Warehouse,
)
from warehouse_api.schemas import (
    AuditDiscrepancyActor,
    AuditDiscrepancyItem,
    AuditDiscrepancyListResponse,
    AuditDiscrepancyLocation,
    AuditDiscrepancySku,
    AuditRecheckEvidence,
    AuditRecheckRequest,
    AuditRecheckResponse,
    OriginalAuditEvidence,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditRecheckCreationResult:
    response: AuditRecheckResponse
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


def _fingerprint(audit_line_id: UUID, physical_quantity: int) -> str:
    canonical = json.dumps(
        {
            "audit_line_id": str(audit_line_id),
            "recheck_physical_quantity": physical_quantity,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _recheck_evidence(recheck: AuditRecheck, performer: User) -> AuditRecheckEvidence:
    return AuditRecheckEvidence(
        recheck_id=recheck.id,
        recheck_system_quantity=recheck.recheck_system_quantity,
        recheck_physical_quantity=recheck.recheck_physical_quantity,
        recheck_quantity_discrepancy=recheck.recheck_quantity_discrepancy,
        result=recheck.result,
        performed_by=AuditDiscrepancyActor(
            user_id=performer.id,
            login_identifier=performer.login_identifier,
        ),
        performed_at=_aware(recheck.performed_at),
    )


def _discrepancy_statement(warehouse_id: UUID):
    auditor = aliased(User, name="original_auditor")
    performer = aliased(User, name="recheck_performer")
    statement = (
        select(
            AuditLine,
            AuditSession,
            Sku,
            InternalLocation,
            auditor,
            AuditRecheck,
            performer,
        )
        .join(AuditSession, AuditSession.id == AuditLine.audit_id)
        .join(Sku, Sku.id == AuditLine.sku_id)
        .join(InternalLocation, InternalLocation.id == AuditLine.location_id)
        .join(auditor, auditor.id == AuditSession.audited_by_user_id)
        .outerjoin(AuditRecheck, AuditRecheck.audit_line_id == AuditLine.id)
        .outerjoin(performer, performer.id == AuditRecheck.performed_by_user_id)
        .where(
            AuditLine.result == "MISMATCH",
            AuditSession.status == "MISMATCH_RECORDED",
            AuditSession.warehouse_id == warehouse_id,
            InternalLocation.warehouse_id == warehouse_id,
        )
    )
    return statement


def _item_from_row(row: tuple[object, ...]) -> AuditDiscrepancyItem:
    line, audit, sku, location, auditor, recheck, performer = row
    if not isinstance(line, AuditLine):
        raise RuntimeError("Discrepancy query returned an invalid Audit line")
    if not isinstance(audit, AuditSession) or not isinstance(sku, Sku):
        raise RuntimeError("Discrepancy query returned invalid Audit evidence")
    if not isinstance(location, InternalLocation) or not isinstance(auditor, User):
        raise RuntimeError("Discrepancy query returned invalid source references")
    evidence = None
    if recheck is not None:
        if not isinstance(recheck, AuditRecheck) or not isinstance(performer, User):
            raise RuntimeError("Recheck query returned invalid performer evidence")
        evidence = _recheck_evidence(recheck, performer)
    return AuditDiscrepancyItem(
        audit_id=audit.id,
        audit_line_id=line.id,
        warehouse_id=audit.warehouse_id,
        sku=AuditDiscrepancySku(id=sku.id, code=sku.code),
        location=AuditDiscrepancyLocation(id=location.id, code=location.code),
        original=OriginalAuditEvidence(
            system_quantity=line.system_quantity,
            physical_quantity=line.physical_quantity,
            quantity_discrepancy=line.quantity_discrepancy,
            result="MISMATCH",
            audited_by=AuditDiscrepancyActor(
                user_id=auditor.id,
                login_identifier=auditor.login_identifier,
            ),
            audited_at=_aware(audit.audited_at),
        ),
        recheck=evidence,
        adjust_eligible=evidence is not None and evidence.result == "MISMATCH",
    )


def list_audit_discrepancies(session: Session) -> AuditDiscrepancyListResponse:
    warehouse_id = _canonical_warehouse_id(session)
    rows = session.execute(
        _discrepancy_statement(warehouse_id).order_by(
            AuditSession.audited_at.desc(), AuditLine.id.desc()
        )
    ).all()
    return AuditDiscrepancyListResponse(
        items=[_item_from_row(tuple(row)) for row in rows]
    )


def get_audit_discrepancy(
    session: Session, audit_line_id: UUID
) -> AuditDiscrepancyItem:
    warehouse_id = _canonical_warehouse_id(session)
    row = session.execute(
        _discrepancy_statement(warehouse_id).where(AuditLine.id == audit_line_id)
    ).one_or_none()
    if row is None:
        raise ApiError(
            404,
            "AUDIT_DISCREPANCY_NOT_FOUND",
            "The Audit discrepancy was not found.",
        )
    return _item_from_row(tuple(row))


def _response_for_recheck(
    session: Session, recheck: AuditRecheck
) -> AuditRecheckResponse:
    performer = session.get(User, recheck.performed_by_user_id)
    if performer is None:
        raise RuntimeError("Audit recheck references a missing performer")
    return AuditRecheckResponse(
        recheck_id=recheck.id,
        audit_line_id=recheck.audit_line_id,
        recheck_system_quantity=recheck.recheck_system_quantity,
        recheck_physical_quantity=recheck.recheck_physical_quantity,
        recheck_quantity_discrepancy=recheck.recheck_quantity_discrepancy,
        result=recheck.result,
        performed_by=AuditDiscrepancyActor(
            user_id=performer.id,
            login_identifier=performer.login_identifier,
        ),
        performed_at=_aware(recheck.performed_at),
        adjust_eligible=recheck.result == "MISMATCH",
    )


def _result_for_key(
    session: Session, idempotency_key: str, fingerprint: str
) -> AuditRecheckCreationResult | None:
    existing = session.scalar(
        select(AuditRecheck).where(AuditRecheck.idempotency_key == idempotency_key)
    )
    if existing is None:
        return None
    if existing.request_fingerprint != fingerprint:
        raise ApiError(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            "The idempotency key was already used for a different request.",
        )
    return AuditRecheckCreationResult(
        response=_response_for_recheck(session, existing), replayed=True
    )


def _insert_for_dialect(session: Session):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql_insert(AuditRecheck)
    if dialect == "sqlite":
        return sqlite_insert(AuditRecheck)
    raise RuntimeError(f"Unsupported database dialect: {dialect}")


def _log_after_commit(session: Session, recheck: AuditRecheck) -> None:
    details = {
        "recheck_id": str(recheck.id),
        "audit_line_id": str(recheck.audit_line_id),
        "actor_user_id": str(recheck.performed_by_user_id),
        "result": recheck.result,
    }

    def log_commit(_session: Session) -> None:
        logger.info("audit_recheck_recorded", extra={"audit_recheck_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def create_audit_recheck(
    session: Session,
    audit_line_id: UUID,
    command: AuditRecheckRequest,
    actor: Actor,
    idempotency_key: str | None,
) -> AuditRecheckCreationResult:
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
    physical_quantity = command.recheck_physical_quantity
    if (
        type(physical_quantity) is not int
        or not 0 <= physical_quantity <= 2_147_483_647
    ):
        raise ApiError(
            422,
            "INVALID_RECHECK_QUANTITY",
            "Recheck physical quantity must be an integer from 0 to 2147483647.",
        )
    fingerprint = _fingerprint(audit_line_id, physical_quantity)
    replay = _result_for_key(session, idempotency_key, fingerprint)
    if replay is not None:
        return replay

    source = session.execute(
        select(AuditLine, AuditSession, InternalLocation)
        .join(AuditSession, AuditSession.id == AuditLine.audit_id)
        .join(InternalLocation, InternalLocation.id == AuditLine.location_id)
        .where(AuditLine.id == audit_line_id)
    ).one_or_none()
    if source is None:
        raise ApiError(
            404,
            "AUDIT_DISCREPANCY_NOT_FOUND",
            "The Audit discrepancy was not found.",
        )
    line, audit, location = source
    if line.result != "MISMATCH" or audit.status != "MISMATCH_RECORDED":
        raise ApiError(
            409,
            "AUDIT_DISCREPANCY_NOT_ELIGIBLE",
            "The Audit line is not eligible for a Manager recheck.",
        )
    warehouse_id = _canonical_warehouse_id(session)
    if audit.warehouse_id != warehouse_id or location.warehouse_id != warehouse_id:
        raise ApiError(
            404,
            "AUDIT_DISCREPANCY_NOT_FOUND",
            "The Audit discrepancy was not found.",
        )
    existing_for_line = session.scalar(
        select(AuditRecheck).where(AuditRecheck.audit_line_id == audit_line_id)
    )
    if existing_for_line is not None:
        raise ApiError(
            409,
            "RECHECK_ALREADY_RECORDED",
            "A Manager recheck was already recorded for this discrepancy.",
        )

    stock_quantity = session.scalar(
        select(StockBalance.quantity).where(
            StockBalance.sku_id == line.sku_id,
            StockBalance.location_id == line.location_id,
        )
    )
    system_quantity = int(stock_quantity) if stock_quantity is not None else 0
    discrepancy = physical_quantity - system_quantity
    result = "MATCH" if discrepancy == 0 else "MISMATCH"
    recheck_id = uuid4()
    performed_at = datetime.now(UTC)
    claim = (
        _insert_for_dialect(session)
        .values(
            id=recheck_id,
            audit_line_id=audit_line_id,
            recheck_system_quantity=system_quantity,
            recheck_physical_quantity=physical_quantity,
            recheck_quantity_discrepancy=discrepancy,
            result=result,
            performed_by_user_id=actor.user_id,
            performed_at=performed_at,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        .on_conflict_do_nothing()
        .returning(AuditRecheck.id)
    )
    claimed_id = session.scalar(claim)
    if claimed_id is None:
        concurrent_replay = _result_for_key(session, idempotency_key, fingerprint)
        if concurrent_replay is not None:
            return concurrent_replay
        concurrent_line = session.scalar(
            select(AuditRecheck).where(AuditRecheck.audit_line_id == audit_line_id)
        )
        if concurrent_line is not None:
            raise ApiError(
                409,
                "RECHECK_ALREADY_RECORDED",
                "A Manager recheck was already recorded for this discrepancy.",
            )
        raise RuntimeError("Audit recheck conflict did not expose a persisted row")

    recheck = session.get(AuditRecheck, claimed_id)
    if recheck is None:
        raise RuntimeError("Claimed Audit recheck row could not be loaded")
    _log_after_commit(session, recheck)
    return AuditRecheckCreationResult(
        response=_response_for_recheck(session, recheck), replayed=False
    )
