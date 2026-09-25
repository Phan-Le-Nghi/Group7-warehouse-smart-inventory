from concurrent.futures import ThreadPoolExecutor
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.audit import create_audit
from warehouse_api.auth import WAREHOUSE_STAFF, Actor
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AuditLine,
    AuditSession,
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
from warehouse_api.schemas import AuditRequest, TransferRequest
from warehouse_api.schemas import PickRequest as PickCommand
from warehouse_api.transfer import confirm_transfer


@pytest.fixture
def postgres_audit_factory():
    database_url = getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL concurrency evidence requires TEST_DATABASE_URL")
    engine = create_engine(database_url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Audit concurrency evidence requires PostgreSQL")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed_case(
    factory: sessionmaker[Session],
) -> tuple[Actor, UUID, UUID, UUID, UUID]:
    actor = Actor(uuid4(), f"audit.{uuid4().hex}", WAREHOUSE_STAFF)
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
        session.add_all(
            [
                StockBalance(
                    sku_id=sku_id,
                    location_id=backroom_id,
                    quantity=10,
                ),
                StockBalance(
                    sku_id=sku_id,
                    location_id=shelf_id,
                    quantity=10,
                ),
            ]
        )
    return actor, warehouse_id, sku_id, backroom_id, shelf_id


def audit_command(
    sku_id: UUID,
    backroom_id: UUID,
    shelf_id: UUID,
    *,
    backroom_physical: int = 10,
) -> AuditRequest:
    return AuditRequest(
        scope_type="WHOLE_WAREHOUSE",
        lines=[
            {
                "sku_id": sku_id,
                "location_id": backroom_id,
                "physical_quantity": backroom_physical,
            },
            {
                "sku_id": sku_id,
                "location_id": shelf_id,
                "physical_quantity": 10,
            },
        ],
    )


def run_audits(
    factory: sessionmaker[Session],
    actor: Actor,
    commands: list[tuple[AuditRequest, str]],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(item: tuple[AuditRequest, str]) -> str:
        command, key = item
        try:
            with factory() as session, session.begin():
                barrier.wait(timeout=10)
                result = create_audit(session, command, actor, key)
                return "REPLAY" if result.replayed else "CREATED"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        return list(executor.map(worker, commands))


def test_concurrent_same_key_creates_one_audit(postgres_audit_factory) -> None:
    factory = postgres_audit_factory
    actor, _warehouse_id, sku_id, backroom_id, shelf_id = seed_case(factory)
    command = audit_command(sku_id, backroom_id, shelf_id)
    results = run_audits(
        factory,
        actor,
        [(command, "same-key"), (command, "same-key")],
    )
    assert sorted(results) == ["CREATED", "REPLAY"]
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 1
        assert session.scalar(select(func.count(AuditLine.id))) == 2


def test_concurrent_same_key_different_command_conflicts(
    postgres_audit_factory,
) -> None:
    factory = postgres_audit_factory
    actor, _warehouse_id, sku_id, backroom_id, shelf_id = seed_case(factory)
    results = run_audits(
        factory,
        actor,
        [
            (audit_command(sku_id, backroom_id, shelf_id), "conflicting-key"),
            (
                audit_command(
                    sku_id,
                    backroom_id,
                    shelf_id,
                    backroom_physical=9,
                ),
                "conflicting-key",
            ),
        ],
    )
    assert sorted(results) == ["CREATED", "IDEMPOTENCY_KEY_REUSED"]
    with factory() as session:
        assert session.scalar(select(func.count(AuditSession.id))) == 1


def _audit_snapshot(factory: sessionmaker[Session], audit_id: UUID) -> dict[UUID, int]:
    with factory() as session:
        return dict(
            session.execute(
                select(AuditLine.location_id, AuditLine.system_quantity).where(
                    AuditLine.audit_id == audit_id
                )
            ).all()
        )


def _stock_snapshot(factory: sessionmaker[Session], sku_id: UUID) -> dict[UUID, int]:
    with factory() as session:
        return dict(
            session.execute(
                select(StockBalance.location_id, StockBalance.quantity).where(
                    StockBalance.sku_id == sku_id
                )
            ).all()
        )


def test_audit_and_transfer_have_coherent_snapshot(postgres_audit_factory) -> None:
    factory = postgres_audit_factory
    actor, _warehouse_id, sku_id, backroom_id, shelf_id = seed_case(factory)
    barrier = Barrier(2)

    def audit_worker() -> UUID:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            result = create_audit(
                session,
                audit_command(sku_id, backroom_id, shelf_id),
                actor,
                "audit-vs-transfer",
            )
            return result.response.audit_id

    def transfer_worker() -> None:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            confirm_transfer(
                session,
                TransferRequest(
                    sku_id=sku_id,
                    source_location_id=backroom_id,
                    destination_location_id=shelf_id,
                    quantity=4,
                ),
                actor,
                "concurrent-transfer",
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        audit_future = executor.submit(audit_worker)
        transfer_future = executor.submit(transfer_worker)
        audit_id = audit_future.result(timeout=15)
        transfer_future.result(timeout=15)

    snapshot = _audit_snapshot(factory, audit_id)
    assert snapshot in (
        {backroom_id: 10, shelf_id: 10},
        {backroom_id: 6, shelf_id: 14},
    )
    assert _stock_snapshot(factory, sku_id) == {backroom_id: 6, shelf_id: 14}
    with factory() as session:
        assert session.scalar(select(func.count(Transfer.id))) == 1


def test_audit_and_pick_complete_without_audit_mutation(
    postgres_audit_factory,
) -> None:
    factory = postgres_audit_factory
    actor, warehouse_id, sku_id, backroom_id, shelf_id = seed_case(factory)
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

    def audit_worker() -> UUID:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            return create_audit(
                session,
                audit_command(sku_id, backroom_id, shelf_id),
                actor,
                "audit-vs-pick",
            ).response.audit_id

    def pick_worker() -> None:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            confirm_pick(
                session,
                PickCommand(
                    pick_id=pick_id,
                    allocations=[{"source_location_id": backroom_id, "quantity": 7}],
                ),
                actor,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        audit_future = executor.submit(audit_worker)
        pick_future = executor.submit(pick_worker)
        audit_id = audit_future.result(timeout=15)
        pick_future.result(timeout=15)

    snapshot = _audit_snapshot(factory, audit_id)
    assert snapshot in (
        {backroom_id: 10, shelf_id: 10},
        {backroom_id: 3, shelf_id: 10},
    )
    assert _stock_snapshot(factory, sku_id) == {backroom_id: 3, shelf_id: 10}
