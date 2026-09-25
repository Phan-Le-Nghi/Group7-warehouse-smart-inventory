from concurrent.futures import ThreadPoolExecutor
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.auth import WAREHOUSE_STAFF, Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    Base,
    InternalLocation,
    PickRequest,
    Sku,
    StockBalance,
    Transfer,
    User,
    Warehouse,
)
from warehouse_api.pick import confirm_pick
from warehouse_api.schemas import PickRequest as PickCommand
from warehouse_api.schemas import TransferRequest
from warehouse_api.transfer import confirm_transfer


@pytest.fixture
def postgres_transfer_factory():
    database_url = getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL concurrency evidence requires TEST_DATABASE_URL")
    engine = create_engine(database_url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Row-lock concurrency evidence requires PostgreSQL")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed_case(
    factory: sessionmaker[Session],
    *,
    backroom_quantity: int = 10,
    shelf_quantity: int | None = 10,
) -> tuple[Actor, UUID, UUID, UUID, UUID]:
    actor = Actor(uuid4(), f"transfer.{uuid4().hex}", WAREHOUSE_STAFF)
    warehouse_id, sku_id, backroom_id, shelf_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=actor.user_id,
                    login_identifier=actor.login_identifier,
                    password_hash="test-only",
                    role=actor.role.value,
                ),
                Warehouse(id=warehouse_id, code=f"W-{uuid4().hex}"),
                Sku(id=sku_id, code=f"SKU-{uuid4().hex}"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=backroom_id,
                    warehouse_id=warehouse_id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=shelf_id,
                    warehouse_id=warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        session.add(
            StockBalance(
                sku_id=sku_id,
                location_id=backroom_id,
                quantity=backroom_quantity,
            )
        )
        if shelf_quantity is not None:
            session.add(
                StockBalance(
                    sku_id=sku_id,
                    location_id=shelf_id,
                    quantity=shelf_quantity,
                )
            )
    return actor, warehouse_id, sku_id, backroom_id, shelf_id


def command(
    sku_id: UUID, source_id: UUID, destination_id: UUID, quantity: int
) -> TransferRequest:
    return TransferRequest(
        sku_id=sku_id,
        source_location_id=source_id,
        destination_location_id=destination_id,
        quantity=quantity,
    )


def run_transfers(
    factory: sessionmaker[Session],
    actor: Actor,
    commands: list[tuple[TransferRequest, str]],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(item: tuple[TransferRequest, str]) -> str:
        transfer_command, key = item
        try:
            with factory() as session, session.begin():
                session.execute(select(1))
                barrier.wait(timeout=10)
                result = confirm_transfer(session, transfer_command, actor, key)
                return "REPLAY" if result.replayed else "CREATED"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        return list(executor.map(worker, commands))


def stock_snapshot(
    factory: sessionmaker[Session], sku_id: UUID
) -> tuple[dict[UUID, int], int]:
    with factory() as session:
        return (
            dict(
                session.execute(
                    select(StockBalance.location_id, StockBalance.quantity).where(
                        StockBalance.sku_id == sku_id
                    )
                ).all()
            ),
            int(
                session.scalar(
                    select(func.count(Transfer.id)).where(Transfer.sku_id == sku_id)
                )
                or 0
            ),
        )


def test_concurrent_same_key_moves_stock_once(postgres_transfer_factory) -> None:
    factory = postgres_transfer_factory
    actor, _warehouse_id, sku_id, source_id, destination_id = seed_case(factory)
    transfer_command = command(sku_id, source_id, destination_id, 4)

    results = run_transfers(
        factory,
        actor,
        [(transfer_command, "concurrent-key"), (transfer_command, "concurrent-key")],
    )

    assert sorted(results) == ["CREATED", "REPLAY"]
    balances, count = stock_snapshot(factory, sku_id)
    assert balances == {source_id: 6, destination_id: 14}
    assert count == 1


def test_concurrent_same_key_different_command_conflicts(
    postgres_transfer_factory,
) -> None:
    factory = postgres_transfer_factory
    actor, _warehouse_id, sku_id, source_id, destination_id = seed_case(factory)
    results = run_transfers(
        factory,
        actor,
        [
            (command(sku_id, source_id, destination_id, 4), "conflicting-key"),
            (command(sku_id, source_id, destination_id, 3), "conflicting-key"),
        ],
    )
    assert sorted(results) == ["CREATED", "IDEMPOTENCY_KEY_REUSED"]
    balances, count = stock_snapshot(factory, sku_id)
    assert balances[source_id] in {6, 7}
    assert balances[destination_id] in {13, 14}
    assert sum(balances.values()) == 20
    assert count == 1


def test_opposite_transfers_use_one_lock_order(postgres_transfer_factory) -> None:
    factory = postgres_transfer_factory
    actor, _warehouse_id, sku_id, first_id, second_id = seed_case(factory)
    results = run_transfers(
        factory,
        actor,
        [
            (command(sku_id, first_id, second_id, 4), "forward"),
            (command(sku_id, second_id, first_id, 3), "reverse"),
        ],
    )
    assert results == ["CREATED", "CREATED"]
    balances, count = stock_snapshot(factory, sku_id)
    assert balances == {first_id: 9, second_id: 11}
    assert count == 2


def test_same_source_and_destination_creation_are_serialized(
    postgres_transfer_factory,
) -> None:
    factory = postgres_transfer_factory
    actor, _warehouse_id, sku_id, source_id, destination_id = seed_case(
        factory, backroom_quantity=20, shelf_quantity=None
    )
    results = run_transfers(
        factory,
        actor,
        [
            (command(sku_id, source_id, destination_id, 7), "first"),
            (command(sku_id, source_id, destination_id, 7), "second"),
        ],
    )
    assert results == ["CREATED", "CREATED"]
    balances, count = stock_snapshot(factory, sku_id)
    assert balances == {source_id: 6, destination_id: 14}
    assert count == 2


def test_two_transfers_same_source_preserve_nonnegative_stock(
    postgres_transfer_factory,
) -> None:
    factory = postgres_transfer_factory
    actor, _warehouse_id, sku_id, source_id, destination_id = seed_case(factory)
    results = run_transfers(
        factory,
        actor,
        [
            (command(sku_id, source_id, destination_id, 7), "source-first"),
            (command(sku_id, source_id, destination_id, 7), "source-second"),
        ],
    )
    assert sorted(results) == ["CREATED", "INSUFFICIENT_SOURCE_STOCK"]
    balances, count = stock_snapshot(factory, sku_id)
    assert balances == {source_id: 3, destination_id: 17}
    assert count == 1


def test_transfer_and_pick_preserve_nonnegative_source(
    postgres_transfer_factory,
) -> None:
    factory = postgres_transfer_factory
    actor, warehouse_id, sku_id, source_id, destination_id = seed_case(factory)
    pick_id = uuid4()
    with factory.begin() as session:
        session.add(
            PickRequest(
                id=pick_id,
                warehouse_id=warehouse_id,
                sku_id=sku_id,
                requested_quantity=7,
            )
        )
    barrier = Barrier(2)

    def transfer_worker() -> str:
        try:
            with factory() as session, session.begin():
                barrier.wait(timeout=10)
                confirm_transfer(
                    session,
                    command(sku_id, source_id, destination_id, 7),
                    actor,
                    "transfer-vs-pick",
                )
            return "TRANSFER"
        except ApiError as error:
            return error.code

    def pick_worker() -> str:
        try:
            with factory() as session, session.begin():
                barrier.wait(timeout=10)
                confirm_pick(
                    session,
                    PickCommand(
                        pick_id=pick_id,
                        allocations=[{"source_location_id": source_id, "quantity": 7}],
                    ),
                    actor,
                )
            return "PICK"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda fn: fn(), [transfer_worker, pick_worker]))
    assert sorted(results) == ["INSUFFICIENT_SOURCE_STOCK", "PICK"] or sorted(
        results
    ) == ["INSUFFICIENT_SOURCE_STOCK", "TRANSFER"]
    balances, transfer_count = stock_snapshot(factory, sku_id)
    assert balances[source_id] == 3
    assert balances[destination_id] in {10, 17}
    assert transfer_count in {0, 1}
