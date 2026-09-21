from concurrent.futures import ThreadPoolExecutor
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.auth import WAREHOUSE_STAFF, Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    Base,
    InternalLocation,
    PickAllocation,
    PickRequest,
    Sku,
    StockBalance,
    User,
    Warehouse,
)
from warehouse_api.pick import confirm_pick
from warehouse_api.schemas import PickRequest as PickCommand


@pytest.fixture
def postgres_pick_factory():
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


def _seed_concurrency_case(
    factory: sessionmaker[Session], *, balance_quantity: int, same_pick: bool = False
) -> tuple[Actor, list[UUID], UUID, list[UUID]]:
    warehouse_id, sku_id = uuid4(), uuid4()
    location_ids = [uuid4(), uuid4()]
    pick_ids = [uuid4(), uuid4()]
    if same_pick:
        pick_ids[1] = pick_ids[0]
    actor = Actor(uuid4(), f"concurrent.{uuid4().hex}", WAREHOUSE_STAFF)
    with factory.begin() as session:
        session.add(
            User(
                id=actor.user_id,
                login_identifier=actor.login_identifier,
                password_hash="test-only",
                role=actor.role.value,
                is_active=True,
            )
        )
        session.add(Warehouse(id=warehouse_id, code=f"W-{uuid4().hex}"))
        session.add(Sku(id=sku_id, code=f"SKU-{uuid4().hex}"))
        session.add_all(
            [
                InternalLocation(
                    id=location_ids[0], warehouse_id=warehouse_id, code="BACKROOM"
                ),
                InternalLocation(
                    id=location_ids[1],
                    warehouse_id=warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.add_all(
            [
                StockBalance(
                    sku_id=sku_id,
                    location_id=location_id,
                    quantity=balance_quantity,
                )
                for location_id in location_ids
            ]
        )
        for pick_id in set(pick_ids):
            session.add(
                PickRequest(
                    id=pick_id,
                    warehouse_id=warehouse_id,
                    sku_id=sku_id,
                    requested_quantity=2 if balance_quantity == 2 else 7,
                )
            )
    return actor, pick_ids, sku_id, location_ids


def _run_concurrently(
    factory: sessionmaker[Session],
    actor: Actor,
    commands: list[PickCommand],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(command: PickCommand) -> str:
        try:
            with factory() as session, session.begin():
                session.execute(select(1))
                barrier.wait(timeout=10)
                return confirm_pick(session, command, actor).outcome
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        return list(executor.map(worker, commands))


def test_opposite_client_order_uses_safe_deterministic_balance_order(
    postgres_pick_factory,
) -> None:
    factory = postgres_pick_factory
    actor, pick_ids, sku_id, location_ids = _seed_concurrency_case(
        factory, balance_quantity=2
    )
    commands = [
        PickCommand(
            pick_id=pick_ids[0],
            allocations=[
                {"source_location_id": location_ids[0], "quantity": 1},
                {"source_location_id": location_ids[1], "quantity": 1},
            ],
        ),
        PickCommand(
            pick_id=pick_ids[1],
            allocations=[
                {"source_location_id": location_ids[1], "quantity": 1},
                {"source_location_id": location_ids[0], "quantity": 1},
            ],
        ),
    ]

    results = _run_concurrently(factory, actor, commands)

    assert results == ["FULLY_COMPLETED", "FULLY_COMPLETED"]
    with factory() as session:
        assert session.scalars(
            select(StockBalance.quantity)
            .where(StockBalance.sku_id == sku_id)
            .order_by(StockBalance.location_id)
        ).all() == [0, 0]


def test_conflicting_picks_preserve_nonnegative_stock(postgres_pick_factory) -> None:
    factory = postgres_pick_factory
    actor, pick_ids, sku_id, location_ids = _seed_concurrency_case(
        factory, balance_quantity=10
    )
    commands = [
        PickCommand(
            pick_id=pick_id,
            allocations=[{"source_location_id": location_ids[0], "quantity": 7}],
        )
        for pick_id in pick_ids
    ]

    results = _run_concurrently(factory, actor, commands)

    assert sorted(results) == ["FULLY_COMPLETED", "INSUFFICIENT_SOURCE_STOCK"]
    with factory() as session:
        assert (
            session.scalar(
                select(StockBalance.quantity).where(
                    StockBalance.sku_id == sku_id,
                    StockBalance.location_id == location_ids[0],
                )
            )
            == 3
        )


def test_concurrent_confirmation_of_same_pick_decrements_once(
    postgres_pick_factory,
) -> None:
    factory = postgres_pick_factory
    actor, pick_ids, sku_id, location_ids = _seed_concurrency_case(
        factory, balance_quantity=10, same_pick=True
    )
    command = PickCommand(
        pick_id=pick_ids[0],
        allocations=[{"source_location_id": location_ids[0], "quantity": 7}],
    )

    results = _run_concurrently(factory, actor, [command, command])

    assert sorted(results) == ["FULLY_COMPLETED", "PICK_ALREADY_RECORDED"]
    with factory() as session:
        assert (
            session.scalar(
                select(StockBalance.quantity).where(
                    StockBalance.sku_id == sku_id,
                    StockBalance.location_id == location_ids[0],
                )
            )
            == 3
        )
        assert (
            len(
                session.scalars(
                    select(PickAllocation).where(PickAllocation.pick_id == pick_ids[0])
                ).all()
            )
            == 1
        )
