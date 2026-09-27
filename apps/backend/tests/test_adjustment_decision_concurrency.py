from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from warehouse_api.adjustment import decide_adjustment
from warehouse_api.auth import Actor, Role
from warehouse_api.errors import ApiError
from warehouse_api.models import (
    AdjustRequest,
    AuditLine,
    AuditRecheck,
    AuditSession,
    Base,
    InternalLocation,
    PickRequest,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    User,
    Warehouse,
)
from warehouse_api.pick import confirm_pick
from warehouse_api.putaway import confirm_putaway
from warehouse_api.schemas import (
    AdjustmentDecisionRequest,
    PickAllocationRequest,
    PutawayRequest,
    TransferRequest,
)
from warehouse_api.schemas import PickRequest as PickCommand
from warehouse_api.transfer import confirm_transfer


@dataclass(frozen=True, slots=True)
class DecisionRaceFixture:
    manager: Actor
    staff_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    second_sku_id: UUID
    source_id: UUID
    destination_id: UUID
    adjustment_id: UUID
    same_balance_adjustment_id: UUID
    other_balance_adjustment_id: UUID
    pick_id: UUID
    receive_line_id: UUID


@pytest.fixture
def postgres_decision_factory():
    database_url = getenv("TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql"):
        pytest.skip("PostgreSQL TEST_DATABASE_URL is required")
    engine = create_engine(database_url, pool_size=12, max_overflow=0)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    fixture = _seed(factory)
    yield factory, fixture
    Base.metadata.drop_all(engine)
    engine.dispose()


def _add_adjustment(
    session: Session,
    *,
    warehouse_id: UUID,
    sku_id: UUID,
    location_id: UUID,
    staff_id: UUID,
    manager_id: UUID,
) -> UUID:
    audit = AuditSession(
        warehouse_id=warehouse_id,
        scope_type="SELECTED_PAIRS",
        result="MISMATCH",
        status="MISMATCH_RECORDED",
        audited_by_user_id=staff_id,
        audited_at=datetime.now(UTC),
        idempotency_key=f"audit-{uuid4()}",
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
        idempotency_key=f"recheck-{uuid4()}",
        request_fingerprint="b" * 64,
    )
    session.add(recheck)
    session.flush()
    adjustment = AdjustRequest(
        audit_recheck_id=recheck.id,
        sku_id=sku_id,
        location_id=location_id,
        recheck_system_quantity_snapshot=10,
        recheck_physical_quantity_snapshot=8,
        requested_change=-2,
        reason="Concurrent decision",
        status="PENDING_MANAGER_DECISION",
        requested_by_user_id=staff_id,
        requested_at=datetime.now(UTC),
        idempotency_key=f"create-{uuid4()}",
        request_fingerprint="c" * 64,
    )
    session.add(adjustment)
    session.flush()
    return adjustment.id


def _seed(factory: sessionmaker[Session]) -> DecisionRaceFixture:
    manager = Actor(uuid4(), "decision.manager", Role.MANAGER)
    staff_id = uuid4()
    warehouse_id = uuid4()
    sku_id = uuid4()
    second_sku_id = uuid4()
    source_id = uuid4()
    destination_id = uuid4()
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
                    id=staff_id,
                    login_identifier="decision.staff",
                    password_hash="test-only",
                    role=Role.WAREHOUSE_STAFF.value,
                ),
                Warehouse(id=warehouse_id, code="MAIN"),
                Sku(id=sku_id, code="RACE-SKU"),
                Sku(id=second_sku_id, code="RACE-SKU-2"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=source_id, warehouse_id=warehouse_id, code="BACKROOM"
                ),
                InternalLocation(
                    id=destination_id,
                    warehouse_id=warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                StockBalance(sku_id=sku_id, location_id=source_id, quantity=10),
                StockBalance(sku_id=sku_id, location_id=destination_id, quantity=0),
                StockBalance(
                    sku_id=second_sku_id, location_id=destination_id, quantity=10
                ),
            ]
        )
        adjustment_id = _add_adjustment(
            session,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            location_id=source_id,
            staff_id=staff_id,
            manager_id=manager.user_id,
        )
        same_balance_adjustment_id = _add_adjustment(
            session,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            location_id=source_id,
            staff_id=staff_id,
            manager_id=manager.user_id,
        )
        other_balance_adjustment_id = _add_adjustment(
            session,
            warehouse_id=warehouse_id,
            sku_id=second_sku_id,
            location_id=destination_id,
            staff_id=staff_id,
            manager_id=manager.user_id,
        )
        pick = PickRequest(
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            requested_quantity=1,
        )
        session.add(pick)
        receive = Receive(
            warehouse_id=warehouse_id,
            expected_reference="RACE-RECEIVE",
            document_reference="RACE-RECEIVE",
            reference_match_status="REFERENCE_MATCH",
            recorded_by_user_id=staff_id,
            recorded_at=datetime.now(UTC),
        )
        session.add(receive)
        session.flush()
        receive_line = ReceiveLine(
            receive_id=receive.id,
            sku_id=sku_id,
            expected_quantity=1,
            actual_quantity=1,
            quantity_discrepancy=0,
        )
        session.add(receive_line)
        session.flush()
        result = DecisionRaceFixture(
            manager=manager,
            staff_id=staff_id,
            warehouse_id=warehouse_id,
            sku_id=sku_id,
            second_sku_id=second_sku_id,
            source_id=source_id,
            destination_id=destination_id,
            adjustment_id=adjustment_id,
            same_balance_adjustment_id=same_balance_adjustment_id,
            other_balance_adjustment_id=other_balance_adjustment_id,
            pick_id=pick.id,
            receive_line_id=receive_line.id,
        )
    return result


def _run_decisions(
    factory: sessionmaker[Session],
    fixture: DecisionRaceFixture,
    commands: list[tuple[UUID, str, str, str | None]],
) -> list[str]:
    barrier = Barrier(len(commands))

    def worker(item: tuple[UUID, str, str, str | None]) -> str:
        adjustment_id, decision, key, reason = item
        try:
            with factory() as session, session.begin():
                barrier.wait(timeout=10)
                result = decide_adjustment(
                    session,
                    adjustment_id,
                    AdjustmentDecisionRequest(
                        decision=decision, rejection_reason=reason
                    ),
                    fixture.manager,
                    key,
                )
                return result.status
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        futures = [executor.submit(worker, command) for command in commands]
        return [future.result(timeout=20) for future in futures]


def _stock(factory: sessionmaker[Session], sku_id: UUID, location_id: UUID) -> int:
    with factory() as session:
        return int(
            session.scalar(
                select(StockBalance.quantity).where(
                    StockBalance.sku_id == sku_id,
                    StockBalance.location_id == location_id,
                )
            )
            or 0
        )


def test_approve_vs_approve_and_same_key_replay(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    different = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "approve-1", None),
            (fixture.adjustment_id, "APPROVE", "approve-2", None),
        ],
    )
    assert sorted(different) == ["ADJUSTMENT_NOT_PENDING", "APPLIED"]
    assert _stock(factory, fixture.sku_id, fixture.source_id) == 8


def test_reject_races_and_approve_vs_reject(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    rejected = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "REJECT", "reject-1", "First"),
            (fixture.adjustment_id, "REJECT", "reject-2", "Second"),
        ],
    )
    assert sorted(rejected) == ["ADJUSTMENT_NOT_PENDING", "REJECTED"]
    assert _stock(factory, fixture.sku_id, fixture.source_id) == 10


def test_approve_vs_reject_different_keys(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    results = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "approve-key", None),
            (fixture.adjustment_id, "REJECT", "reject-key", "Reject"),
        ],
    )
    assert "ADJUSTMENT_NOT_PENDING" in results
    assert any(result in {"APPLIED", "REJECTED"} for result in results)
    final = _stock(factory, fixture.sku_id, fixture.source_id)
    assert final in {8, 10}


def test_same_key_approve_replay_and_conflicting_reject(
    postgres_decision_factory,
) -> None:
    factory, fixture = postgres_decision_factory
    replay = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "same-key", None),
            (fixture.adjustment_id, "APPROVE", "same-key", None),
        ],
    )
    assert replay == ["APPLIED", "APPLIED"]
    assert _stock(factory, fixture.sku_id, fixture.source_id) == 8


def test_same_key_approve_vs_reject(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    results = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "conflict-key", None),
            (fixture.adjustment_id, "REJECT", "conflict-key", "Reject"),
        ],
    )
    assert "IDEMPOTENCY_KEY_REUSED" in results
    assert any(result in {"APPLIED", "REJECTED"} for result in results)


def test_two_adjustments_same_balance(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    results = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "first-adjust", None),
            (
                fixture.same_balance_adjustment_id,
                "APPROVE",
                "second-adjust",
                None,
            ),
        ],
    )
    assert sorted(results) == ["ADJUSTMENT_STALE", "APPLIED"]
    assert _stock(factory, fixture.sku_id, fixture.source_id) == 8


def test_global_decision_key_race_across_requests(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    raced_ids = {
        fixture.adjustment_id,
        fixture.other_balance_adjustment_id,
    }
    results = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "global-key", None),
            (
                fixture.other_balance_adjustment_id,
                "APPROVE",
                "global-key",
                None,
            ),
        ],
    )
    assert sorted(results) == ["APPLIED", "IDEMPOTENCY_KEY_REUSED"]
    with factory() as session:
        requests = list(
            session.scalars(
                select(AdjustRequest).where(AdjustRequest.id.in_(raced_ids))
            )
        )
    assert sorted(request.status for request in requests) == [
        "APPLIED",
        "PENDING_MANAGER_DECISION",
    ]
    winner = next(request for request in requests if request.status == "APPLIED")
    loser = next(
        request for request in requests if request.status == "PENDING_MANAGER_DECISION"
    )
    assert winner.decision_idempotency_key == "global-key"
    assert winner.decided_by_user_id == fixture.manager.user_id
    assert winner.applied_stock_before == 10
    assert winner.applied_stock_after == 8
    assert loser.decision_idempotency_key is None
    assert loser.decision_request_fingerprint is None
    assert loser.decided_by_user_id is None
    assert loser.decided_at is None
    assert loser.applied_stock_before is None
    assert loser.applied_stock_after is None
    assert sorted(
        [
            _stock(factory, fixture.sku_id, fixture.source_id),
            _stock(factory, fixture.second_sku_id, fixture.destination_id),
        ]
    ) == [8, 10]


def test_global_decision_key_race_on_same_balance(postgres_decision_factory) -> None:
    factory, fixture = postgres_decision_factory
    results = _run_decisions(
        factory,
        fixture,
        [
            (fixture.adjustment_id, "APPROVE", "shared-global-key", None),
            (
                fixture.same_balance_adjustment_id,
                "APPROVE",
                "shared-global-key",
                None,
            ),
        ],
    )
    assert sorted(results) == ["APPLIED", "IDEMPOTENCY_KEY_REUSED"]
    assert _stock(factory, fixture.sku_id, fixture.source_id) == 8


@pytest.mark.parametrize("workflow", ["pick", "transfer", "putaway"])
def test_approve_serializes_with_stock_workflows(
    postgres_decision_factory, workflow: str
) -> None:
    factory, fixture = postgres_decision_factory
    barrier = Barrier(2)

    def approve() -> str:
        try:
            with factory() as session, session.begin():
                barrier.wait(timeout=10)
                return decide_adjustment(
                    session,
                    fixture.adjustment_id,
                    AdjustmentDecisionRequest(decision="APPROVE"),
                    fixture.manager,
                    f"approve-{workflow}",
                ).status
        except ApiError as error:
            return error.code

    def mutate() -> str:
        with factory() as session, session.begin():
            barrier.wait(timeout=10)
            if workflow == "pick":
                confirm_pick(
                    session,
                    PickCommand(
                        pick_id=fixture.pick_id,
                        allocations=[
                            PickAllocationRequest(
                                source_location_id=fixture.source_id, quantity=1
                            )
                        ],
                    ),
                    Actor(fixture.staff_id, "decision.staff", Role.WAREHOUSE_STAFF),
                )
            elif workflow == "transfer":
                confirm_transfer(
                    session,
                    TransferRequest(
                        sku_id=fixture.sku_id,
                        source_location_id=fixture.source_id,
                        destination_location_id=fixture.destination_id,
                        quantity=1,
                    ),
                    Actor(fixture.staff_id, "decision.staff", Role.WAREHOUSE_STAFF),
                    f"transfer-{uuid4()}",
                )
            else:
                confirm_putaway(
                    session,
                    PutawayRequest(
                        receive_line_id=fixture.receive_line_id,
                        sku_id=fixture.sku_id,
                        quantity=1,
                        destination_location_id=fixture.source_id,
                    ),
                    f"putaway-{uuid4()}",
                )
            return workflow.upper()

    with ThreadPoolExecutor(max_workers=2) as executor:
        approve_future = executor.submit(approve)
        mutation_future = executor.submit(mutate)
        results = [
            approve_future.result(timeout=20),
            mutation_future.result(timeout=20),
        ]
    assert workflow.upper() in results
    assert any(result in {"APPLIED", "ADJUSTMENT_STALE"} for result in results)
    final = _stock(factory, fixture.sku_id, fixture.source_id)
    expected = {
        "pick": {7, 9},
        "transfer": {7, 9},
        "putaway": {9, 11},
    }
    assert final in expected[workflow]
