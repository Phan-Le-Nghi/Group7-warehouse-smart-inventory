import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from warehouse_api.errors import ApiError
from warehouse_api.models import (
    InternalLocation,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
)
from warehouse_api.receive import ensure_putaway_eligible
from warehouse_api.schemas import (
    LocationOption,
    PutawayContextResponse,
    PutawayRequest,
    PutawayResponse,
    StockResult,
)


@dataclass(frozen=True, slots=True)
class PutawayResult:
    response: PutawayResponse
    replayed: bool


def _fingerprint(command: PutawayRequest) -> str:
    payload = command.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _allocation_total_statement(receive_line_id: UUID) -> Select[tuple[int]]:
    return select(func.coalesce(func.sum(PutawayAllocation.quantity), 0)).where(
        PutawayAllocation.receive_line_id == receive_line_id
    )


def _warehouse_total(session: Session, sku_id: UUID, warehouse_id: UUID) -> int:
    statement = (
        select(func.coalesce(func.sum(StockBalance.quantity), 0))
        .join(InternalLocation, InternalLocation.id == StockBalance.location_id)
        .where(
            StockBalance.sku_id == sku_id,
            InternalLocation.warehouse_id == warehouse_id,
        )
    )
    return int(session.scalar(statement) or 0)


def _destination_quantity(session: Session, sku_id: UUID, location_id: UUID) -> int:
    statement = select(StockBalance.quantity).where(
        StockBalance.sku_id == sku_id,
        StockBalance.location_id == location_id,
    )
    return int(session.scalar(statement) or 0)


def _response_for_allocation(
    session: Session, allocation: PutawayAllocation
) -> PutawayResponse:
    location = session.get(InternalLocation, allocation.destination_location_id)
    receive_line = session.get(ReceiveLine, allocation.receive_line_id)
    if location is None or receive_line is None:  # protected by database FKs
        raise RuntimeError("Putaway allocation references missing data")
    receive = session.get(Receive, receive_line.receive_id)
    if receive is None:
        raise RuntimeError("Receive line references missing receive")

    return PutawayResponse(
        putaway_id=allocation.id,
        receive_line_id=allocation.receive_line_id,
        sku_id=allocation.sku_id,
        quantity=allocation.quantity,
        destination_location_id=allocation.destination_location_id,
        destination_location=location.code,
        confirmed_at=allocation.confirmed_at,
        stock=StockResult(
            destination_quantity=_destination_quantity(
                session, allocation.sku_id, allocation.destination_location_id
            ),
            warehouse_total=_warehouse_total(
                session, allocation.sku_id, receive.warehouse_id
            ),
        ),
    )


def get_putaway_context(
    session: Session, receive_line_id: UUID
) -> PutawayContextResponse:
    statement = (
        select(ReceiveLine, Receive, Sku)
        .join(Receive, Receive.id == ReceiveLine.receive_id)
        .join(Sku, Sku.id == ReceiveLine.sku_id)
        .where(ReceiveLine.id == receive_line_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise ApiError(404, "RECEIVE_LINE_NOT_FOUND", "Receive line was not found.")
    receive_line, receive, sku = row
    ensure_putaway_eligible(receive, receive_line)
    confirmed = int(session.scalar(_allocation_total_statement(receive_line.id)) or 0)
    locations = session.scalars(
        select(InternalLocation)
        .where(InternalLocation.warehouse_id == receive.warehouse_id)
        .order_by(InternalLocation.code)
    ).all()
    return PutawayContextResponse(
        receive_line_id=receive_line.id,
        sku_id=sku.id,
        sku=sku.code,
        actual_quantity=receive_line.actual_quantity,
        confirmed_quantity=confirmed,
        eligible_quantity=receive_line.actual_quantity - confirmed,
        locations=[
            LocationOption(id=location.id, code=location.code) for location in locations
        ],
    )


def confirm_putaway(
    session: Session, command: PutawayRequest, idempotency_key: str
) -> PutawayResult:
    if command.quantity <= 0:
        raise ApiError(422, "INVALID_QUANTITY", "Quantity must be a positive integer.")

    fingerprint = _fingerprint(command)
    receive_statement = (
        select(ReceiveLine, Receive)
        .join(Receive, Receive.id == ReceiveLine.receive_id)
        .where(ReceiveLine.id == command.receive_line_id)
        .with_for_update()
    )
    row = session.execute(receive_statement).one_or_none()
    if row is None:
        raise ApiError(404, "RECEIVE_LINE_NOT_FOUND", "Receive line was not found.")
    receive_line, receive = row
    ensure_putaway_eligible(receive, receive_line)

    existing = session.scalar(
        select(PutawayAllocation).where(
            PutawayAllocation.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise ApiError(
                409,
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
            )
        return PutawayResult(_response_for_allocation(session, existing), replayed=True)

    if session.get(Sku, command.sku_id) is None:
        raise ApiError(404, "SKU_NOT_FOUND", "SKU was not found.")
    if receive_line.sku_id != command.sku_id:
        raise ApiError(
            409,
            "RECEIVE_LINE_SKU_MISMATCH",
            "SKU does not match the Receive line.",
        )

    destination = session.scalar(
        select(InternalLocation).where(
            InternalLocation.id == command.destination_location_id,
            InternalLocation.warehouse_id == receive.warehouse_id,
            InternalLocation.code.in_(("BACKROOM", "SALES_SHELF")),
        )
    )
    if destination is None:
        raise ApiError(
            422,
            "INVALID_DESTINATION",
            "Destination must be a tracked location in the Receive warehouse.",
        )

    confirmed = int(session.scalar(_allocation_total_statement(receive_line.id)) or 0)
    eligible = receive_line.actual_quantity - confirmed
    if command.quantity > eligible:
        raise ApiError(
            409,
            "PUTAWAY_EXCEEDS_ELIGIBLE_QUANTITY",
            "Quantity exceeds the eligible remaining quantity.",
            {"eligible_quantity": eligible},
        )

    allocation = PutawayAllocation(
        receive_line_id=command.receive_line_id,
        sku_id=command.sku_id,
        quantity=command.quantity,
        destination_location_id=command.destination_location_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    session.add(allocation)

    values = {
        "sku_id": command.sku_id,
        "location_id": command.destination_location_id,
        "quantity": command.quantity,
    }
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        insert_statement = postgresql_insert(StockBalance).values(**values)
    elif dialect == "sqlite":
        insert_statement = sqlite_insert(StockBalance).values(**values)
    else:
        raise RuntimeError(f"Unsupported database dialect: {dialect}")
    session.execute(
        insert_statement.on_conflict_do_update(
            index_elements=[StockBalance.sku_id, StockBalance.location_id],
            set_={"quantity": StockBalance.quantity + command.quantity},
        )
    )
    session.flush()

    return PutawayResult(_response_for_allocation(session, allocation), replayed=False)
