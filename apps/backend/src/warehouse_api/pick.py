import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    InternalLocation,
    PickAllocation,
    PickRequest,
    Sku,
    StockBalance,
)
from warehouse_api.schemas import (
    PickAllocationResult,
    PickContextResponse,
    PickLocationAvailability,
    PickResponse,
)
from warehouse_api.schemas import PickRequest as PickCommand
from warehouse_api.stock import ordered_location_ids

FULLY_COMPLETED = "FULLY_COMPLETED"
PARTIAL_INSUFFICIENT = "PARTIAL_INSUFFICIENT"
TRACKED_LOCATION_CODES = ("BACKROOM", "SALES_SHELF")

logger = logging.getLogger(__name__)


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


def _log_rejection(pick_id: UUID, actor: Actor, code: str) -> None:
    logger.warning(
        "pick_command_rejected",
        extra={
            "pick_event": {
                "pick_id": str(pick_id),
                "actor_user_id": str(actor.user_id),
                "reason": code,
            }
        },
    )


def _log_after_commit(session: Session, details: dict[str, object]) -> None:
    def log_commit(_session: Session) -> None:
        logger.info("pick_confirmed", extra={"pick_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def get_pick_context(session: Session, pick_id: UUID) -> PickContextResponse:
    statement = (
        select(PickRequest, Sku)
        .join(Sku, Sku.id == PickRequest.sku_id)
        .where(PickRequest.id == pick_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise ApiError(404, "PICK_NOT_FOUND", "Pick request was not found.")
    pick, sku = row

    locations = session.scalars(
        select(InternalLocation)
        .where(
            InternalLocation.warehouse_id == pick.warehouse_id,
            InternalLocation.code.in_(TRACKED_LOCATION_CODES),
        )
        .order_by(InternalLocation.code, InternalLocation.id)
    ).all()
    quantities = dict(
        session.execute(
            select(StockBalance.location_id, StockBalance.quantity).where(
                StockBalance.sku_id == pick.sku_id,
                StockBalance.location_id.in_([location.id for location in locations]),
            )
        ).all()
    )
    return PickContextResponse(
        pick_id=pick.id,
        warehouse_id=pick.warehouse_id,
        sku_id=pick.sku_id,
        sku=sku.code,
        requested_quantity=pick.requested_quantity,
        outcome=pick.outcome,
        locations=[
            PickLocationAvailability(
                id=location.id,
                code=location.code,
                available_quantity=int(quantities.get(location.id, 0)),
            )
            for location in locations
        ],
        warehouse_total=_warehouse_total(session, pick.sku_id, pick.warehouse_id),
    )


def confirm_pick(session: Session, command: PickCommand, actor: Actor) -> PickResponse:
    pick = session.scalar(
        select(PickRequest)
        .where(PickRequest.id == command.pick_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if pick is None:
        _log_rejection(command.pick_id, actor, "PICK_NOT_FOUND")
        raise ApiError(404, "PICK_NOT_FOUND", "Pick request was not found.")
    if pick.outcome is not None:
        _log_rejection(pick.id, actor, "PICK_ALREADY_RECORDED")
        raise ApiError(
            409,
            "PICK_ALREADY_RECORDED",
            "The Pick result has already been recorded.",
        )
    if not command.allocations:
        _log_rejection(pick.id, actor, "INVALID_ALLOCATIONS")
        raise ApiError(
            422, "INVALID_ALLOCATIONS", "At least one source allocation is required."
        )

    source_ids = [allocation.source_location_id for allocation in command.allocations]
    if len(source_ids) != len(set(source_ids)):
        _log_rejection(pick.id, actor, "DUPLICATE_SOURCE_LOCATION")
        raise ApiError(
            422,
            "DUPLICATE_SOURCE_LOCATION",
            "Each source location may be allocated only once.",
        )
    if any(allocation.quantity <= 0 for allocation in command.allocations):
        _log_rejection(pick.id, actor, "INVALID_QUANTITY")
        raise ApiError(422, "INVALID_QUANTITY", "Quantity must be a positive integer.")

    picked_quantity = sum(allocation.quantity for allocation in command.allocations)
    if picked_quantity <= 0:
        _log_rejection(pick.id, actor, "INVALID_QUANTITY")
        raise ApiError(422, "INVALID_QUANTITY", "Picked quantity must be positive.")
    if picked_quantity > pick.requested_quantity:
        _log_rejection(pick.id, actor, "PICK_EXCEEDS_REQUESTED_QUANTITY")
        raise ApiError(
            422,
            "PICK_EXCEEDS_REQUESTED_QUANTITY",
            "Picked quantity exceeds the requested quantity.",
            {"requested_quantity": pick.requested_quantity},
        )

    locations = {
        location.id: location
        for location in session.scalars(
            select(InternalLocation).where(InternalLocation.id.in_(source_ids))
        ).all()
    }
    invalid_source = any(
        source_id not in locations
        or locations[source_id].warehouse_id != pick.warehouse_id
        or locations[source_id].code not in TRACKED_LOCATION_CODES
        for source_id in source_ids
    )
    if invalid_source:
        _log_rejection(pick.id, actor, "INVALID_SOURCE_LOCATION")
        raise ApiError(
            422,
            "INVALID_SOURCE_LOCATION",
            "Every source must be a tracked location in the Pick warehouse.",
        )

    allocations_by_source = {
        allocation.source_location_id: allocation for allocation in command.allocations
    }
    locked_balances: dict[UUID, StockBalance] = {}
    for source_id in ordered_location_ids(source_ids):
        balance = session.scalar(
            select(StockBalance)
            .where(
                StockBalance.sku_id == pick.sku_id,
                StockBalance.location_id == source_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        requested = allocations_by_source[source_id].quantity
        if balance is None or balance.quantity < requested:
            _log_rejection(pick.id, actor, "INSUFFICIENT_SOURCE_STOCK")
            raise ApiError(
                409,
                "INSUFFICIENT_SOURCE_STOCK",
                "A selected source does not have enough available stock.",
                {"source_location_id": str(source_id)},
            )
        locked_balances[source_id] = balance

    now = datetime.now(UTC)
    outcome = (
        FULLY_COMPLETED
        if picked_quantity == pick.requested_quantity
        else PARTIAL_INSUFFICIENT
    )
    allocation_rows: list[PickAllocation] = []
    for source_id in ordered_location_ids(source_ids):
        requested = allocations_by_source[source_id].quantity
        locked_balances[source_id].quantity -= requested
        allocation = PickAllocation(
            pick_id=pick.id,
            source_location_id=source_id,
            quantity=requested,
        )
        session.add(allocation)
        allocation_rows.append(allocation)

    pick.outcome = outcome
    pick.confirmed_by_user_id = actor.user_id
    pick.confirmed_at = now
    session.flush()

    response = PickResponse(
        pick_id=pick.id,
        sku_id=pick.sku_id,
        requested_quantity=pick.requested_quantity,
        picked_quantity=picked_quantity,
        remaining_quantity=pick.requested_quantity - picked_quantity,
        outcome=outcome,
        allocations=[
            PickAllocationResult(
                source_location_id=allocation.source_location_id,
                source_location=locations[allocation.source_location_id].code,
                quantity=allocation.quantity,
                remaining_source_quantity=locked_balances[
                    allocation.source_location_id
                ].quantity,
            )
            for allocation in allocation_rows
        ],
        confirmed_by_user_id=actor.user_id,
        confirmed_at=now,
        warehouse_total=_warehouse_total(session, pick.sku_id, pick.warehouse_id),
    )
    _log_after_commit(
        session,
        {
            "pick_id": str(pick.id),
            "actor_user_id": str(actor.user_id),
            "requested_quantity": pick.requested_quantity,
            "picked_quantity": picked_quantity,
            "allocation_count": len(allocation_rows),
            "outcome": outcome,
        },
    )
    return response
