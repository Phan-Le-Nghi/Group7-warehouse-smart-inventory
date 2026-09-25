from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth import Actor, Role, get_actor
from warehouse_api.db import get_db_session
from warehouse_api.main import app
from warehouse_api.models import (
    Base,
    InternalLocation,
    PickAllocation,
    PickRequest,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    Transfer,
    User,
    Warehouse,
)
from warehouse_api.transfer import get_transfer_history


@dataclass(frozen=True, slots=True)
class HistoryFixture:
    warehouse_id: UUID
    sku_id: UUID
    source_id: UUID
    destination_id: UUID
    staff_id: UUID
    manager: Actor


@pytest.fixture
def history_api() -> Iterator[tuple[TestClient, sessionmaker[Session], HistoryFixture]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    fixture = HistoryFixture(
        warehouse_id=uuid4(),
        sku_id=uuid4(),
        source_id=uuid4(),
        destination_id=uuid4(),
        staff_id=uuid4(),
        manager=Actor(uuid4(), "history.manager", Role.MANAGER),
    )
    receive_id = uuid4()
    receive_line_id = uuid4()
    pick_id = uuid4()
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=fixture.staff_id,
                    login_identifier="history.staff",
                    password_hash="test-only",
                    role=Role.WAREHOUSE_STAFF.value,
                ),
                User(
                    id=fixture.manager.user_id,
                    login_identifier=fixture.manager.login_identifier,
                    password_hash="test-only",
                    role=fixture.manager.role.value,
                ),
                Warehouse(id=fixture.warehouse_id, code="MAIN"),
                Sku(id=fixture.sku_id, code="SKU-HISTORY"),
            ]
        )
        session.flush()
        session.add_all(
            [
                InternalLocation(
                    id=fixture.source_id,
                    warehouse_id=fixture.warehouse_id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=fixture.destination_id,
                    warehouse_id=fixture.warehouse_id,
                    code="SALES_SHELF",
                ),
                Receive(id=receive_id, warehouse_id=fixture.warehouse_id),
                PickRequest(
                    id=pick_id,
                    warehouse_id=fixture.warehouse_id,
                    sku_id=fixture.sku_id,
                    requested_quantity=3,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.source_id,
                    quantity=9,
                ),
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.destination_id,
                    quantity=4,
                ),
                ReceiveLine(
                    id=receive_line_id,
                    receive_id=receive_id,
                    sku_id=fixture.sku_id,
                    actual_quantity=2,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                PutawayAllocation(
                    receive_line_id=receive_line_id,
                    sku_id=fixture.sku_id,
                    quantity=2,
                    destination_location_id=fixture.source_id,
                    idempotency_key="history-putaway",
                    request_fingerprint="p" * 64,
                ),
                PickAllocation(
                    pick_id=pick_id,
                    source_location_id=fixture.source_id,
                    quantity=1,
                ),
            ]
        )

    def override_session() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_actor] = lambda: fixture.manager
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_transfer(
    factory: sessionmaker[Session],
    fixture: HistoryFixture,
    *,
    transfer_id: UUID | None = None,
    transferred_at: datetime | None = None,
    quantity: int = 2,
) -> UUID:
    transfer_id = transfer_id or uuid4()
    with factory.begin() as session:
        session.add(
            Transfer(
                id=transfer_id,
                warehouse_id=fixture.warehouse_id,
                sku_id=fixture.sku_id,
                source_location_id=fixture.source_id,
                destination_location_id=fixture.destination_id,
                quantity=quantity,
                transferred_by_user_id=fixture.staff_id,
                transferred_at=transferred_at or datetime(2026, 9, 25, tzinfo=UTC),
                idempotency_key=f"history-{transfer_id}",
                request_fingerprint=transfer_id.hex.ljust(64, "0"),
            )
        )
    return transfer_id


def business_snapshot(factory: sessionmaker[Session]) -> dict[str, list[tuple]]:
    with factory() as session:
        return {
            "transfers": list(
                session.execute(
                    select(
                        Transfer.id,
                        Transfer.quantity,
                        Transfer.transferred_by_user_id,
                        Transfer.transferred_at,
                        Transfer.idempotency_key,
                        Transfer.request_fingerprint,
                    ).order_by(Transfer.id)
                ).all()
            ),
            "stock": list(
                session.execute(
                    select(
                        StockBalance.id,
                        StockBalance.sku_id,
                        StockBalance.location_id,
                        StockBalance.quantity,
                    ).order_by(StockBalance.id)
                ).all()
            ),
            "receives": list(
                session.execute(
                    select(Receive.id, Receive.recorded_at).order_by(Receive.id)
                ).all()
            ),
            "receive_lines": list(
                session.execute(
                    select(ReceiveLine.id, ReceiveLine.actual_quantity).order_by(
                        ReceiveLine.id
                    )
                ).all()
            ),
            "putaways": list(
                session.execute(
                    select(PutawayAllocation.id, PutawayAllocation.quantity).order_by(
                        PutawayAllocation.id
                    )
                ).all()
            ),
            "picks": list(
                session.execute(
                    select(PickRequest.id, PickRequest.outcome).order_by(PickRequest.id)
                ).all()
            ),
            "pick_allocations": list(
                session.execute(
                    select(PickAllocation.id, PickAllocation.quantity).order_by(
                        PickAllocation.id
                    )
                ).all()
            ),
        }


def test_empty_history_returns_exact_collection(history_api) -> None:
    client, _factory, _fixture = history_api
    response = client.get("/api/v1/transfers")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_one_row_has_exact_approved_shape_and_no_forbidden_fields(history_api) -> None:
    client, factory, fixture = history_api
    transfer_id = add_transfer(factory, fixture, quantity=4)
    response = client.get("/api/v1/transfers")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "items": [
            {
                "transfer_id": str(transfer_id),
                "warehouse_id": str(fixture.warehouse_id),
                "sku": {"id": str(fixture.sku_id), "code": "SKU-HISTORY"},
                "quantity": 4,
                "source": {"id": str(fixture.source_id), "code": "BACKROOM"},
                "destination": {
                    "id": str(fixture.destination_id),
                    "code": "SALES_SHELF",
                },
                "transferred_by": {
                    "user_id": str(fixture.staff_id),
                    "login_identifier": "history.staff",
                },
                "transferred_at": "2026-09-25T00:00:00",
            }
        ]
    }
    serialized = response.text.lower()
    for forbidden in (
        "idempotency_key",
        "request_fingerprint",
        "stock",
        "balance",
        "snapshot",
    ):
        assert forbidden not in serialized


def test_history_uses_newest_first_and_id_desc_tie_break(history_api) -> None:
    client, factory, fixture = history_api
    older = UUID("00000000-0000-0000-0000-000000000010")
    tied_low = UUID("00000000-0000-0000-0000-000000000020")
    tied_high = UUID("00000000-0000-0000-0000-000000000030")
    add_transfer(
        factory,
        fixture,
        transfer_id=older,
        transferred_at=datetime(2026, 9, 24, tzinfo=UTC),
    )
    tied_time = datetime(2026, 9, 25, tzinfo=UTC)
    add_transfer(factory, fixture, transfer_id=tied_low, transferred_at=tied_time)
    add_transfer(factory, fixture, transfer_id=tied_high, transferred_at=tied_time)

    response = client.get("/api/v1/transfers")
    assert response.status_code == 200
    assert [item["transfer_id"] for item in response.json()["items"]] == [
        str(tied_high),
        str(tied_low),
        str(older),
    ]


@pytest.mark.parametrize("role", [Role.WAREHOUSE_STAFF, Role.PURCHASING, Role.ADMIN])
def test_wrong_roles_receive_real_forbidden(history_api, role: Role) -> None:
    client, _factory, _fixture = history_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    response = client.get("/api/v1/transfers")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_unauthenticated_history_is_unauthorized(history_api) -> None:
    client, _factory, _fixture = history_api
    del app.dependency_overrides[get_actor]
    response = client.get("/api/v1/transfers")
    assert response.status_code == 401


def test_client_warehouse_parameter_is_ignored(history_api) -> None:
    client, factory, fixture = history_api
    transfer_id = add_transfer(factory, fixture)
    response = client.get(f"/api/v1/transfers?warehouse_id={uuid4()}")
    assert response.status_code == 200
    assert [item["transfer_id"] for item in response.json()["items"]] == [
        str(transfer_id)
    ]


def test_repeated_history_get_has_no_business_effect(history_api) -> None:
    client, factory, fixture = history_api
    add_transfer(factory, fixture)
    before = business_snapshot(factory)
    first = client.get("/api/v1/transfers")
    second = client.get("/api/v1/transfers")
    after = business_snapshot(factory)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert after == before


def test_query_failure_has_no_business_effect(history_api, monkeypatch) -> None:
    _client, factory, fixture = history_api
    add_transfer(factory, fixture)
    before = business_snapshot(factory)

    def fail_query(*_args, **_kwargs):
        raise RuntimeError("simulated query failure")

    with factory() as session, monkeypatch.context() as patch:
        patch.setattr(session, "execute", fail_query)
        with pytest.raises(RuntimeError, match="simulated query failure"):
            get_transfer_history(session)
    assert business_snapshot(factory) == before


def test_single_warehouse_invariant_rejects_zero_or_multiple() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(RuntimeError, match="exactly one"):
        get_transfer_history(session)
    with Session(engine) as session, session.begin():
        session.add_all([Warehouse(code="MAIN"), Warehouse(code="SECONDARY")])
    with Session(engine) as session, pytest.raises(RuntimeError, match="exactly one"):
        get_transfer_history(session)
    engine.dispose()
