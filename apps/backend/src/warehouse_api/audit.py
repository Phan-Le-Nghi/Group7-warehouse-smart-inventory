import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, event, func, select, true
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AuditLine,
    AuditSession,
    InternalLocation,
    Sku,
    StockBalance,
    Warehouse,
)
from warehouse_api.schemas import (
    AuditContextPair,
    AuditContextResponse,
    AuditLineRequest,
    AuditLineResponse,
    AuditRequest,
    AuditResponse,
)

TRACKED_LOCATION_CODES = ("BACKROOM", "SALES_SHELF")
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditCreationResult:
    response: AuditResponse
    replayed: bool


def _canonical_warehouse_id(session: Session) -> UUID:
    warehouse_ids = list(session.scalars(select(Warehouse.id).limit(2)))
    if len(warehouse_ids) != 1:
        raise ApiError(
            500,
            "CANONICAL_WAREHOUSE_UNAVAILABLE",
            "The canonical Warehouse is unavailable.",
        )
    return warehouse_ids[0]


def _matrix_statement(warehouse_id: UUID):
    return (
        select(
            Sku.id,
            Sku.code,
            InternalLocation.id,
            InternalLocation.code,
            func.coalesce(StockBalance.quantity, 0),
        )
        .select_from(Sku)
        .join(InternalLocation, true())
        .outerjoin(
            StockBalance,
            and_(
                StockBalance.sku_id == Sku.id,
                StockBalance.location_id == InternalLocation.id,
            ),
        )
        .where(
            InternalLocation.warehouse_id == warehouse_id,
            InternalLocation.code.in_(TRACKED_LOCATION_CODES),
        )
        .order_by(Sku.id, InternalLocation.id)
    )


def get_audit_context(session: Session) -> AuditContextResponse:
    warehouse_id = _canonical_warehouse_id(session)
    rows = session.execute(_matrix_statement(warehouse_id)).all()
    return AuditContextResponse(
        warehouse_id=warehouse_id,
        pairs=[
            AuditContextPair(
                sku_id=sku_id,
                sku=sku_code,
                location_id=location_id,
                location=location_code,
                preview_system_quantity=int(quantity),
            )
            for sku_id, sku_code, location_id, location_code, quantity in rows
        ],
    )


def _canonical_lines(command: AuditRequest) -> list[AuditLineRequest]:
    if not command.lines:
        raise ApiError(422, "EMPTY_AUDIT_SCOPE", "Audit scope must not be empty.")
    seen: set[tuple[UUID, UUID]] = set()
    for line in command.lines:
        pair = (line.sku_id, line.location_id)
        if pair in seen:
            raise ApiError(
                422,
                "DUPLICATE_AUDIT_LINE",
                "An SKU/location pair may appear only once in an Audit.",
            )
        seen.add(pair)
    return sorted(
        command.lines,
        key=lambda line: (str(line.sku_id), str(line.location_id)),
    )


def _fingerprint(scope_type: str, lines: list[AuditLineRequest]) -> str:
    payload = {
        "scope_type": scope_type,
        "lines": [
            {
                "sku_id": str(line.sku_id),
                "location_id": str(line.location_id),
                "physical_quantity": line.physical_quantity,
            }
            for line in lines
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _response_for_audit(session: Session, audit: AuditSession) -> AuditResponse:
    lines = session.scalars(
        select(AuditLine)
        .where(AuditLine.audit_id == audit.id)
        .order_by(AuditLine.sku_id, AuditLine.location_id)
    ).all()
    return AuditResponse(
        audit_id=audit.id,
        warehouse_id=audit.warehouse_id,
        scope_type=audit.scope_type,
        result=audit.result,
        status=audit.status,
        audited_by_user_id=audit.audited_by_user_id,
        audited_at=_aware(audit.audited_at),
        lines=[
            AuditLineResponse(
                sku_id=line.sku_id,
                location_id=line.location_id,
                system_quantity=line.system_quantity,
                physical_quantity=line.physical_quantity,
                quantity_discrepancy=line.quantity_discrepancy,
                result=line.result,
            )
            for line in lines
        ],
    )


def _existing_result(
    session: Session, idempotency_key: str, fingerprint: str
) -> AuditCreationResult | None:
    existing = session.scalar(
        select(AuditSession).where(AuditSession.idempotency_key == idempotency_key)
    )
    if existing is None:
        return None
    if existing.request_fingerprint != fingerprint:
        raise ApiError(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            "The idempotency key was already used for a different request.",
        )
    return AuditCreationResult(_response_for_audit(session, existing), replayed=True)


def _selected_snapshot(
    session: Session,
    warehouse_id: UUID,
    lines: list[AuditLineRequest],
) -> dict[tuple[UUID, UUID], int]:
    sku_ids = {line.sku_id for line in lines}
    location_ids = {line.location_id for line in lines}
    found_skus = set(session.scalars(select(Sku.id).where(Sku.id.in_(sku_ids))).all())
    if found_skus != sku_ids:
        raise ApiError(404, "SKU_NOT_FOUND", "SKU was not found.")

    locations = {
        location.id: location
        for location in session.scalars(
            select(InternalLocation).where(InternalLocation.id.in_(location_ids))
        ).all()
    }
    if set(locations) != location_ids:
        raise ApiError(404, "LOCATION_NOT_FOUND", "Location was not found.")
    if any(location.warehouse_id != warehouse_id for location in locations.values()):
        raise ApiError(
            422,
            "LOCATION_OUTSIDE_WAREHOUSE",
            "Location does not belong to the canonical Warehouse.",
        )

    quantities = {
        (sku_id, location_id): int(quantity)
        for sku_id, location_id, quantity in session.execute(
            select(
                StockBalance.sku_id,
                StockBalance.location_id,
                StockBalance.quantity,
            ).where(
                StockBalance.sku_id.in_(sku_ids),
                StockBalance.location_id.in_(location_ids),
            )
        ).all()
    }
    return {
        (line.sku_id, line.location_id): quantities.get(
            (line.sku_id, line.location_id), 0
        )
        for line in lines
    }


def _whole_warehouse_snapshot(
    session: Session,
    warehouse_id: UUID,
    lines: list[AuditLineRequest],
) -> dict[tuple[UUID, UUID], int]:
    rows = session.execute(_matrix_statement(warehouse_id)).all()
    snapshot = {
        (sku_id, location_id): int(quantity)
        for sku_id, _sku, location_id, _location, quantity in rows
    }
    if not snapshot:
        raise ApiError(422, "EMPTY_AUDIT_SCOPE", "Audit scope must not be empty.")
    submitted_pairs = {(line.sku_id, line.location_id) for line in lines}
    if submitted_pairs != set(snapshot):
        raise ApiError(
            409,
            "AUDIT_SCOPE_CHANGED",
            "The Whole Warehouse Audit scope has changed.",
            {
                "missing_pair_count": len(set(snapshot) - submitted_pairs),
                "extra_pair_count": len(submitted_pairs - set(snapshot)),
            },
        )
    return snapshot


def _insert_for_dialect(session: Session):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql_insert(AuditSession)
    if dialect == "sqlite":
        return sqlite_insert(AuditSession)
    raise RuntimeError(f"Unsupported database dialect: {dialect}")


def _log_after_commit(session: Session, audit: AuditSession, line_count: int) -> None:
    details = {
        "audit_id": str(audit.id),
        "actor_user_id": str(audit.audited_by_user_id),
        "scope_type": audit.scope_type,
        "line_count": line_count,
        "result": audit.result,
    }

    def log_commit(_session: Session) -> None:
        logger.info("audit_recorded", extra={"audit_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def create_audit(
    session: Session,
    command: AuditRequest,
    actor: Actor,
    idempotency_key: str | None,
) -> AuditCreationResult:
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

    lines = _canonical_lines(command)
    fingerprint = _fingerprint(command.scope_type, lines)

    existing = _existing_result(session, idempotency_key, fingerprint)
    if existing is not None:
        return existing

    warehouse_id = _canonical_warehouse_id(session)
    if command.scope_type == "WHOLE_WAREHOUSE":
        snapshot = _whole_warehouse_snapshot(session, warehouse_id, lines)
    else:
        snapshot = _selected_snapshot(session, warehouse_id, lines)

    response_lines: list[AuditLineResponse] = []
    for line in lines:
        system_quantity = snapshot[(line.sku_id, line.location_id)]
        discrepancy = line.physical_quantity - system_quantity
        response_lines.append(
            AuditLineResponse(
                sku_id=line.sku_id,
                location_id=line.location_id,
                system_quantity=system_quantity,
                physical_quantity=line.physical_quantity,
                quantity_discrepancy=discrepancy,
                result="MATCH" if discrepancy == 0 else "MISMATCH",
            )
        )

    all_match = all(line.result == "MATCH" for line in response_lines)
    result = "MATCH" if all_match else "MISMATCH"
    audit_id = uuid4()
    audited_at = datetime.now(UTC)
    status = "MATCH_COMPLETED" if result == "MATCH" else "MISMATCH_RECORDED"
    claim = (
        _insert_for_dialect(session)
        .values(
            id=audit_id,
            warehouse_id=warehouse_id,
            scope_type=command.scope_type,
            result=result,
            status=status,
            audited_by_user_id=actor.user_id,
            audited_at=audited_at,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        .on_conflict_do_nothing(index_elements=[AuditSession.idempotency_key])
        .returning(AuditSession.id)
    )
    claimed_id = session.scalar(claim)
    if claimed_id is None:
        concurrent_result = _existing_result(session, idempotency_key, fingerprint)
        if concurrent_result is None:
            raise RuntimeError("Idempotency conflict did not expose an Audit row")
        return concurrent_result

    audit = session.get(AuditSession, claimed_id)
    if audit is None:
        raise RuntimeError("Claimed Audit row could not be loaded")
    session.add_all(
        [
            AuditLine(
                audit_id=audit.id,
                sku_id=line.sku_id,
                location_id=line.location_id,
                system_quantity=line.system_quantity,
                physical_quantity=line.physical_quantity,
                quantity_discrepancy=line.quantity_discrepancy,
                result=line.result,
            )
            for line in response_lines
        ]
    )
    session.flush()
    _log_after_commit(session, audit, len(response_lines))
    return AuditCreationResult(
        AuditResponse(
            audit_id=audit.id,
            warehouse_id=audit.warehouse_id,
            scope_type=audit.scope_type,
            result=audit.result,
            status=audit.status,
            audited_by_user_id=audit.audited_by_user_id,
            audited_at=_aware(audit.audited_at),
            lines=response_lines,
        ),
        replayed=False,
    )
