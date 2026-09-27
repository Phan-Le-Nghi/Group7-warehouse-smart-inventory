from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.adjustment import create_adjustment_request
from warehouse_api.auth import Actor, Role
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AdjustRequest,
    AuditLine,
    AuditRecheck,
    AuditSession,
    Base,
    InternalLocation,
    Sku,
    User,
    Warehouse,
)
from warehouse_api.schemas import AdjustmentCreateRequest


@dataclass(frozen=True, slots=True)
class ConcurrencyFixture:
    staff: Actor
    audit_recheck_id: UUID


@pytest.fixture
def postgres_adjustment_factory():
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
    staff = Actor(uuid4(), "adjust.staff", Role.WAREHOUSE_STAFF)
    manager_id = uuid4()
    sku_id = uuid4()
    location_id = uuid4()
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=staff.user_id,
                    login_identifier=staff.login_identifier,
                    password_hash="test-only",
                    role=staff.role.value,
                ),
                User(
                    id=manager_id,
                    login_identifier="adjust.manager",
                    password_hash="test-only",
                    role=Role.MANAGER.value,
                ),
                Warehouse(id=warehouse_id, code=f"W-{uuid4().hex}"),
                Sku(id=sku_id, code=f"SKU-{uuid4().hex}"),
            ]
        )
        session.flush()
        session.add(
            InternalLocation(
                id=location_id,
                warehouse_id=warehouse_id,
                code="BACKROOM",
            )
        )
        session.flush()
        audit = AuditSession(
            warehouse_id=warehouse_id,
            scope_type="SELECTED_PAIRS",
            result="MISMATCH",
            status="MISMATCH_RECORDED",
            audited_by_user_id=staff.user_id,
            audited_at=datetime.now(UTC),
            idempotency_key=f"audit-{uuid4().hex}",
            request_fingerprint="a" * 64,
        )
        session.add(audit)
        session.flush()
        line = AuditLine(
            audit_id=audit.id,
            sku_id=sku_id,
            location_id=location_id,
            system_quantity=10,
            physical_quantity=8,
            quantity_discrepancy=-2,
            result="MISMATCH",
        )
        session.add(line)
        session.flush()
        recheck = AuditRecheck(
            audit_line_id=line.id,
            recheck_system_quantity=10,
            recheck_physical_quantity=8,
            recheck_quantity_discrepancy=-2,
            result="MISMATCH",
            performed_by_user_id=manager_id,
            performed_at=datetime.now(UTC),
            idempotency_key=f"recheck-{uuid4().hex}",
            request_fingerprint="b" * 64,
        )
        session.add(recheck)
        session.flush()
        recheck_id = recheck.id
    return ConcurrencyFixture(staff=staff, audit_recheck_id=recheck_id)


def _run_requests(
    factory: sessionmaker[Session],
    fixture: ConcurrencyFixture,
    commands: list[tuple[str, str]],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(item: tuple[str, str]) -> str:
        reason, key = item
        try:
            with factory() as session, session.begin():
                session.execute(select(1))
                barrier.wait(timeout=10)
                result = create_adjustment_request(
                    session,
                    AdjustmentCreateRequest(
                        audit_recheck_id=fixture.audit_recheck_id,
                        reason=reason,
                    ),
                    fixture.staff,
                    key,
                )
                return "REPLAY" if result.replayed else "CREATED"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        futures = [executor.submit(worker, item) for item in commands]
        return [future.result(timeout=20) for future in futures]


def _request_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return int(session.scalar(select(func.count(AdjustRequest.id))) or 0)


def test_concurrent_same_key_same_command(postgres_adjustment_factory) -> None:
    factory, fixture = postgres_adjustment_factory
    results = _run_requests(
        factory, fixture, [("Same reason", "same-key"), ("Same reason", "same-key")]
    )
    assert sorted(results) == ["CREATED", "REPLAY"]
    assert _request_count(factory) == 1


def test_concurrent_same_key_different_reason(postgres_adjustment_factory) -> None:
    factory, fixture = postgres_adjustment_factory
    results = _run_requests(
        factory,
        fixture,
        [("First reason", "same-key"), ("Different reason", "same-key")],
    )
    assert sorted(results) == ["CREATED", "IDEMPOTENCY_KEY_REUSED"]
    assert _request_count(factory) == 1


def test_concurrent_different_keys_same_recheck(postgres_adjustment_factory) -> None:
    factory, fixture = postgres_adjustment_factory
    results = _run_requests(
        factory,
        fixture,
        [("Same reason", "first-key"), ("Same reason", "second-key")],
    )
    assert sorted(results) == ["ADJUSTMENT_ALREADY_EXISTS", "CREATED"]
    assert _request_count(factory) == 1
