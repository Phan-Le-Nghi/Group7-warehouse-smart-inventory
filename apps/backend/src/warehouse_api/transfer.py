import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import case, event, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, aliased

from warehouse_api.auth import Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    InternalLocation,
    Sku,
    StockBalance,
    Transfer,
    User,
    Warehouse,
)
from warehouse_api.schemas import (
    TransferContextResponse,
    TransferHistoryActor,
    TransferHistoryItem,
    TransferHistoryLocation,
    TransferHistoryResponse,
    TransferHistorySku,
    TransferLocationAvailability,
    TransferRequest,
    TransferResponse,
    TransferStockResult,
)
from warehouse_api.stock import ordered_location_ids

TRACKED_LOCATION_CODES = ("BACKROOM", "SALES_SHELF")
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TransferResult:
    response: TransferResponse
    replayed: bool


def _canonical_warehouse_id(session: Session) -> UUID:
    warehouse_ids = list(session.scalars(select(Warehouse.id).limit(2)))
    if len(warehouse_ids) != 1:
        raise RuntimeError("The MVP database must contain exactly one Warehouse")
    return warehouse_ids[0]


def get_transfer_history(session: Session) -> TransferHistoryResponse:
    warehouse_id = _canonical_warehouse_id(session)
    source = aliased(InternalLocation, name="source_location")
    destination = aliased(InternalLocation, name="destination_location")
    rows = session.execute(
        select(Transfer, Sku, source, destination, User)
        .join(Sku, Sku.id == Transfer.sku_id)
        .join(source, source.id == Transfer.source_location_id)
        .join(destination, destination.id == Transfer.destination_location_id)
        .join(User, User.id == Transfer.transferred_by_user_id)
        .where(Transfer.warehouse_id == warehouse_id)
        .order_by(Transfer.transferred_at.desc(), Transfer.id.desc())
    ).all()
    return TransferHistoryResponse(
        items=[
            TransferHistoryItem(
                transfer_id=transfer.id,
                warehouse_id=transfer.warehouse_id,
                sku=TransferHistorySku(id=sku.id, code=sku.code),
                quantity=transfer.quantity,
                source=TransferHistoryLocation(
                    id=source_location.id, code=source_location.code
                ),
                destination=TransferHistoryLocation(
                    id=destination_location.id,
                    code=destination_location.code,
                ),
                transferred_by=TransferHistoryActor(
                    user_id=user.id,
                    login_identifier=user.login_identifier,
                ),
                transferred_at=transfer.transferred_at,
            )
            for transfer, sku, source_location, destination_location, user in rows
        ]
    )


def _fingerprint(command: TransferRequest) -> str:
    payload = command.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _warehouse_total(session: Session, sku_id: UUID, warehouse_id: UUID) -> int:
    return int(
        session.scalar(
            select(func.coalesce(func.sum(StockBalance.quantity), 0))
            .join(InternalLocation, InternalLocation.id == StockBalance.location_id)
            .where(
                StockBalance.sku_id == sku_id,
                InternalLocation.warehouse_id == warehouse_id,
            )
        )
        or 0
    )


def get_transfer_context(session: Session, sku_id: UUID) -> TransferContextResponse:
    sku = session.get(Sku, sku_id)
    if sku is None:
        raise ApiError(404, "SKU_NOT_FOUND", "SKU was not found.")
    locations = session.scalars(
        select(InternalLocation)
        .where(InternalLocation.code.in_(TRACKED_LOCATION_CODES))
        .order_by(InternalLocation.code, InternalLocation.id)
    ).all()
    if not locations:
        raise ApiError(422, "INVALID_SOURCE_LOCATION", "No tracked location exists.")
    warehouse_id = locations[0].warehouse_id
    warehouse_locations = [
        location for location in locations if location.warehouse_id == warehouse_id
    ]
    quantities = dict(
        session.execute(
            select(StockBalance.location_id, StockBalance.quantity).where(
                StockBalance.sku_id == sku_id,
                StockBalance.location_id.in_(
                    [location.id for location in warehouse_locations]
                ),
            )
        ).all()
    )
    return TransferContextResponse(
        warehouse_id=warehouse_id,
        sku_id=sku.id,
        sku=sku.code,
        locations=[
            TransferLocationAvailability(
                id=location.id,
                code=location.code,
                available_quantity=int(quantities.get(location.id, 0)),
            )
            for location in warehouse_locations
        ],
        warehouse_total=sum(
            int(quantities.get(location.id, 0)) for location in warehouse_locations
        ),
    )


def _response_for_transfer(session: Session, transfer: Transfer) -> TransferResponse:
    locations = {
        location.id: location
        for location in session.scalars(
            select(InternalLocation).where(
                InternalLocation.id.in_(
                    [transfer.source_location_id, transfer.destination_location_id]
                )
            )
        ).all()
    }
    if len(locations) != 2:
        raise RuntimeError("Transfer references missing locations")
    stock = session.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            StockBalance.location_id == transfer.source_location_id,
                            StockBalance.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            StockBalance.location_id
                            == transfer.destination_location_id,
                            StockBalance.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(StockBalance.quantity), 0),
        )
        .join(InternalLocation, InternalLocation.id == StockBalance.location_id)
        .where(
            StockBalance.sku_id == transfer.sku_id,
            InternalLocation.warehouse_id == transfer.warehouse_id,
        )
    ).one()
    return TransferResponse(
        transfer_id=transfer.id,
        warehouse_id=transfer.warehouse_id,
        sku_id=transfer.sku_id,
        quantity=transfer.quantity,
        source_location_id=transfer.source_location_id,
        source_location=locations[transfer.source_location_id].code,
        destination_location_id=transfer.destination_location_id,
        destination_location=locations[transfer.destination_location_id].code,
        transferred_by_user_id=transfer.transferred_by_user_id,
        transferred_at=transfer.transferred_at,
        stock=TransferStockResult(
            source_quantity=int(stock[0]),
            destination_quantity=int(stock[1]),
            warehouse_total=int(stock[2]),
        ),
    )


def _insert_for_dialect(session: Session, model: type[Transfer] | type[StockBalance]):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql_insert(model)
    if dialect == "sqlite":
        return sqlite_insert(model)
    raise RuntimeError(f"Unsupported database dialect: {dialect}")


def _log_after_commit(session: Session, transfer: Transfer) -> None:
    details = {
        "transfer_id": str(transfer.id),
        "actor_user_id": str(transfer.transferred_by_user_id),
        "sku_id": str(transfer.sku_id),
        "source_location_id": str(transfer.source_location_id),
        "destination_location_id": str(transfer.destination_location_id),
        "quantity": transfer.quantity,
    }

    def log_commit(_session: Session) -> None:
        logger.info("transfer_confirmed", extra={"transfer_event": details})

    event.listen(session, "after_commit", log_commit, once=True)


def confirm_transfer(
    session: Session,
    command: TransferRequest,
    actor: Actor,
    idempotency_key: str,
) -> TransferResult:
    if command.quantity <= 0:
        raise ApiError(422, "INVALID_QUANTITY", "Quantity must be a positive integer.")
    if command.source_location_id == command.destination_location_id:
        raise ApiError(
            422,
            "SAME_TRANSFER_LOCATION",
            "Source and destination locations must be different.",
        )
    if session.get(Sku, command.sku_id) is None:
        raise ApiError(404, "SKU_NOT_FOUND", "SKU was not found.")

    locations = {
        location.id: location
        for location in session.scalars(
            select(InternalLocation).where(
                InternalLocation.id.in_(
                    [command.source_location_id, command.destination_location_id]
                )
            )
        ).all()
    }
    source = locations.get(command.source_location_id)
    if source is None or source.code not in TRACKED_LOCATION_CODES:
        raise ApiError(
            422,
            "INVALID_SOURCE_LOCATION",
            "Source must be a tracked location.",
        )
    destination = locations.get(command.destination_location_id)
    if (
        destination is None
        or destination.code not in TRACKED_LOCATION_CODES
        or destination.warehouse_id != source.warehouse_id
    ):
        raise ApiError(
            422,
            "INVALID_DESTINATION_LOCATION",
            "Destination must be a tracked location in the source warehouse.",
        )

    fingerprint = _fingerprint(command)
    transfer_id = uuid4()
    transferred_at = datetime.now(UTC)
    claim = (
        _insert_for_dialect(session, Transfer)
        .values(
            id=transfer_id,
            warehouse_id=source.warehouse_id,
            sku_id=command.sku_id,
            source_location_id=command.source_location_id,
            destination_location_id=command.destination_location_id,
            quantity=command.quantity,
            transferred_by_user_id=actor.user_id,
            transferred_at=transferred_at,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        .on_conflict_do_nothing(index_elements=[Transfer.idempotency_key])
        .returning(Transfer.id)
    )
    claimed_id = session.scalar(claim)
    if claimed_id is None:
        existing = session.scalar(
            select(Transfer).where(Transfer.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise RuntimeError("Idempotency conflict did not expose a Transfer row")
        if existing.request_fingerprint != fingerprint:
            raise ApiError(
                409,
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
            )
        return TransferResult(_response_for_transfer(session, existing), replayed=True)

    transfer = session.get(Transfer, claimed_id)
    if transfer is None:
        raise RuntimeError("Claimed Transfer row could not be loaded")

    destination_insert = (
        _insert_for_dialect(session, StockBalance)
        .values(
            id=uuid4(),
            sku_id=command.sku_id,
            location_id=command.destination_location_id,
            quantity=0,
        )
        .on_conflict_do_nothing(
            index_elements=[StockBalance.sku_id, StockBalance.location_id]
        )
    )
    session.execute(destination_insert)

    locked: dict[UUID, StockBalance] = {}
    for location_id in ordered_location_ids(
        [command.source_location_id, command.destination_location_id]
    ):
        balance = session.scalar(
            select(StockBalance)
            .where(
                StockBalance.sku_id == command.sku_id,
                StockBalance.location_id == location_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if balance is not None:
            locked[location_id] = balance

    source_balance = locked.get(command.source_location_id)
    if source_balance is None or source_balance.quantity < command.quantity:
        raise ApiError(
            409,
            "INSUFFICIENT_SOURCE_STOCK",
            "The source does not have enough available stock.",
            {"source_location_id": str(command.source_location_id)},
        )
    destination_balance = locked.get(command.destination_location_id)
    if destination_balance is None:
        raise RuntimeError("Destination balance could not be materialized")

    source_balance.quantity -= command.quantity
    destination_balance.quantity += command.quantity
    session.flush()
    response = _response_for_transfer(session, transfer)
    _log_after_commit(session, transfer)
    return TransferResult(response, replayed=False)
