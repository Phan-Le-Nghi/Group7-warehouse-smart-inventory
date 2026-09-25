from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.audit_discrepancy import create_audit_recheck
from warehouse_api.auth import Actor, Role
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AuditLine,
    AuditRecheck,
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
from warehouse_api.schemas import (
    AuditRecheckRequest,
    TransferRequest,
)
from warehouse_api.schemas import (
    PickRequest as PickCommand,
)
from warehouse_api.transfer import confirm_transfer


@dataclass(frozen=True, slots=True)
class ConcurrencyFixture:
    manager: Actor
    staff: Actor
    audit_line_id: UUID
    sku_id: UUID
    source_id: UUID
    destination_id: UUID
    pick_id: UUID


@pytest.fixture
def postgres_recheck_factory():
    database_url = getenv("TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql"):
        pytest.skip("PostgreSQL TEST_DATABASE_URL is required")
    engine = create_engine(database_url, pool_size=8, max_overflow=0)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    fixture = _seed_case(factory)
    yield factory, fixture
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_case(factory: sessionmaker[Session]) -> ConcurrencyFixture:
    warehouse_id = uuid4()
    manager = Actor(uuid4(), "audit.manager", Role.MANAGER)
    staff = Actor(uuid4(), "audit.staff", Role.WAREHOUSE_STAFF)
    sku_id = uuid4()
    source_id = uuid4()
    destination_id = uuid4()
    audit_line_id = uuid4()
    pick_id = uuid4()
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=manager.user_id,
                    login_identifier=manager.login_identifier,
                    password_hash="test-only",
                    role=manager.role.value,
                ),
                User(
                    id=staff.user_id,
                    login_identifier=staff.login_identifier,
                    password_hash="test-only",
                    role=staff.role.value,
                ),
                Warehouse(id=warehouse_id, code=f"W-{uuid4().hex}"),
                Sku(id=sku_id, code=f"SKU-{uuid4().hex}"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=source_id,
                    warehouse_id=warehouse_id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=destination_id,
                    warehouse_id=warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        audit = AuditSession(
            warehouse_id=warehouse_id,
            scope_type="SELECTED_PAIRS",
            result="MISMATCH",
            status="MISMATCH_RECORDED",
            audited_by_user_id=staff.user_id,
            audited_at=func.now(),
            idempotency_key=f"source-{uuid4().hex}",
            request_fingerprint="a" * 64,
        )
        session.add(audit)
        session.flush()
        session.add_all(
            [
                AuditLine(
                    id=audit_line_id,
                    audit_id=audit.id,
                    sku_id=sku_id,
                    location_id=source_id,
                    system_quantity=22,
                    physical_quantity=20,
                    quantity_discrepancy=-2,
                    result="MISMATCH",
                ),
                StockBalance(
                    sku_id=sku_id,
                    location_id=source_id,
                    quantity=20,
                ),
                StockBalance(
                    sku_id=sku_id,
                    location_id=destination_id,
                    quantity=5,
                ),
                PickRequest(
                    id=pick_id,
                    warehouse_id=warehouse_id,
                    sku_id=sku_id,
                    requested_quantity=4,
                ),
            ]
        )
    return ConcurrencyFixture(
        manager=manager,
        staff=staff,
        audit_line_id=audit_line_id,
        sku_id=sku_id,
        source_id=source_id,
        destination_id=destination_id,
        pick_id=pick_id,
    )


def _run_rechecks(
    factory: sessionmaker[Session],
    fixture: ConcurrencyFixture,
    commands: list[tuple[int, str]],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(item: tuple[int, str]) -> str:
        quantity, key = item
        try:
            with factory() as session, session.begin():
                session.execute(select(1))
                barrier.wait(timeout=10)
                result = create_audit_recheck(
                    session,
                    fixture.audit_line_id,
                    AuditRecheckRequest(recheck_physical_quantity=quantity),
                    fixture.manager,
                    key,
                )
                return "REPLAY" if result.replayed else "CREATED"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        futures = [executor.submit(worker, item) for item in commands]
        return [future.result(timeout=20) for future in futures]


def _recheck_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return int(session.scalar(select(func.count(AuditRecheck.id))) or 0)


def test_concurrent_same_key_same_command(postgres_recheck_factory) -> None:
    factory, fixture = postgres_recheck_factory
    results = _run_rechecks(factory, fixture, [(20, "same-key"), (20, "same-key")])
    assert sorted(results) == ["CREATED", "REPLAY"]
    assert _recheck_count(factory) == 1


def test_concurrent_same_key_different_command(postgres_recheck_factory) -> None:
    factory, fixture = postgres_recheck_factory
    results = _run_rechecks(factory, fixture, [(20, "same-key"), (19, "same-key")])
    assert sorted(results) == ["CREATED", "IDEMPOTENCY_KEY_REUSED"]
    assert _recheck_count(factory) == 1


def test_concurrent_different_keys_same_line(postgres_recheck_factory) -> None:
    factory, fixture = postgres_recheck_factory
    results = _run_rechecks(factory, fixture, [(20, "first-key"), (20, "second-key")])
    assert sorted(results) == ["CREATED", "RECHECK_ALREADY_RECORDED"]
    assert _recheck_count(factory) == 1


def _run_with_workflow(factory, recheck_worker, workflow_worker) -> list[str]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(recheck_worker),
            executor.submit(workflow_worker),
        ]
        return [future.result(timeout=20) for future in futures]


def test_recheck_and_transfer_complete_without_deadlock(
    postgres_recheck_factory,
) -> None:
    factory, fixture = postgres_recheck_factory
    barrier = Barrier(2)

    def recheck_worker() -> str:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            create_audit_recheck(
                session,
                fixture.audit_line_id,
                AuditRecheckRequest(recheck_physical_quantity=20),
                fixture.manager,
                "recheck-vs-transfer",
            )
        return "RECHECK"

    def transfer_worker() -> str:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            confirm_transfer(
                session,
                TransferRequest(
                    sku_id=fixture.sku_id,
                    source_location_id=fixture.source_id,
                    destination_location_id=fixture.destination_id,
                    quantity=4,
                ),
                fixture.staff,
                "transfer-vs-recheck",
            )
        return "TRANSFER"

    results = _run_with_workflow(factory, recheck_worker, transfer_worker)
    assert sorted(results) == ["RECHECK", "TRANSFER"]
    with factory() as session:
        recheck = session.scalar(select(AuditRecheck))
        source = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.source_id,
            )
        )
        assert recheck is not None
        assert recheck.recheck_system_quantity in {16, 20}
        assert source is not None and source.quantity == 16
        assert session.scalar(select(func.count(Transfer.id))) == 1


def test_recheck_and_pick_complete_without_deadlock(postgres_recheck_factory) -> None:
    factory, fixture = postgres_recheck_factory
    barrier = Barrier(2)

    def recheck_worker() -> str:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            create_audit_recheck(
                session,
                fixture.audit_line_id,
                AuditRecheckRequest(recheck_physical_quantity=20),
                fixture.manager,
                "recheck-vs-pick",
            )
        return "RECHECK"

    def pick_worker() -> str:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            confirm_pick(
                session,
                PickCommand(
                    pick_id=fixture.pick_id,
                    allocations=[
                        {
                            "source_location_id": fixture.source_id,
                            "quantity": 4,
                        }
                    ],
                ),
                fixture.staff,
            )
        return "PICK"

    results = _run_with_workflow(factory, recheck_worker, pick_worker)
    assert sorted(results) == ["PICK", "RECHECK"]
    with factory() as session:
        recheck = session.scalar(select(AuditRecheck))
        source_quantity = session.scalar(
            select(StockBalance.quantity).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.source_id,
            )
        )
        pick = session.get(PickRequest, fixture.pick_id)
        assert recheck is not None
        assert recheck.recheck_system_quantity in {16, 20}
        assert source_quantity == 16
        assert pick is not None and pick.outcome == "FULLY_COMPLETED"
