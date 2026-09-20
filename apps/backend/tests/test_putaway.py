from collections.abc import Iterator
from dataclasses import dataclass
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth import WAREHOUSE_STAFF, Actor, get_actor
from warehouse_api.db import get_db_session
from warehouse_api.main import app
from warehouse_api.models import (
    Base,
    InternalLocation,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    Warehouse,
)


@dataclass(frozen=True, slots=True)
class PutawayFixture:
    receive_line_id: UUID
    sku_id: UUID
    backroom_id: UUID
    sales_shelf_id: UUID


@pytest.fixture
def api() -> Iterator[tuple[TestClient, sessionmaker[Session], PutawayFixture]]:
    test_database_url = getenv("TEST_DATABASE_URL")
    if test_database_url:
        engine = create_engine(test_database_url)
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    fixture = PutawayFixture(uuid4(), uuid4(), uuid4(), uuid4())
    with factory.begin() as session:
        warehouse = Warehouse(id=uuid4(), code="MAIN")
        session.add(warehouse)
        session.flush()

        backroom = InternalLocation(
            id=fixture.backroom_id, warehouse_id=warehouse.id, code="BACKROOM"
        )
        sales_shelf = InternalLocation(
            id=fixture.sales_shelf_id,
            warehouse_id=warehouse.id,
            code="SALES_SHELF",
        )
        session.add_all([backroom, sales_shelf])
        session.flush()

        sku = Sku(id=fixture.sku_id, code="SKU-001")
        session.add(sku)
        session.flush()

        receive = Receive(id=uuid4(), warehouse_id=warehouse.id)
        session.add(receive)
        session.flush()

        receive_line = ReceiveLine(
            id=fixture.receive_line_id,
            receive_id=receive.id,
            sku_id=sku.id,
            actual_quantity=16,
        )
        session.add(receive_line)
        session.flush()

        session.add_all(
            [
                StockBalance(sku_id=sku.id, location_id=backroom.id, quantity=0),
                StockBalance(sku_id=sku.id, location_id=sales_shelf.id, quantity=0),
            ]
        )
        session.flush()

    def override_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_actor] = lambda: Actor(
        user_id=uuid4(),
        login_identifier="test.warehouse_staff",
        role=WAREHOUSE_STAFF,
    )
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(fixture: PutawayFixture, **changes: object) -> dict[str, object]:
    request: dict[str, object] = {
        "receive_line_id": str(fixture.receive_line_id),
        "sku_id": str(fixture.sku_id),
        "quantity": 16,
        "destination_location_id": str(fixture.backroom_id),
    }
    request.update(changes)
    return request


def test_put_001_happy_path_posts_16_to_backroom(api) -> None:
    """TEST-PUT-001: allocation, location stock, derived total, Receive unchanged."""
    client, factory, fixture = api

    response = client.post(
        "/api/v1/putaways",
        json=payload(fixture),
        headers={"Idempotency-Key": "TEST-PUT-001"},
    )

    assert response.status_code == 201
    assert response.json()["stock"] == {
        "destination_quantity": 16,
        "warehouse_total": 16,
    }
    with factory() as session:
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 1
        balances = dict(
            session.execute(
                select(InternalLocation.code, StockBalance.quantity)
                .join(StockBalance, StockBalance.location_id == InternalLocation.id)
                .where(StockBalance.sku_id == fixture.sku_id)
            ).all()
        )
        assert balances == {"BACKROOM": 16, "SALES_SHELF": 0}
        receive_line = session.get(ReceiveLine, fixture.receive_line_id)
        assert receive_line is not None
        assert receive_line.actual_quantity == 16


def test_put_002_invalid_destination_has_no_data_effect(api) -> None:
    """TEST-PUT-002: an untracked destination is rejected and rolled back."""
    client, factory, fixture = api

    response = client.post(
        "/api/v1/putaways",
        json=payload(fixture, destination_location_id=str(uuid4())),
        headers={"Idempotency-Key": "TEST-PUT-002"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DESTINATION"
    with factory() as session:
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 0
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 0


def test_put_003_duplicate_idempotency_key_does_not_double_count(api) -> None:
    """TEST-PUT-003: same key and payload returns one allocation and +16 once."""
    client, factory, fixture = api
    request = payload(fixture)
    headers = {"Idempotency-Key": "TEST-PUT-003"}

    first = client.post("/api/v1/putaways", json=request, headers=headers)
    replay = client.post("/api/v1/putaways", json=request, headers=headers)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["putaway_id"] == first.json()["putaway_id"]
    with factory() as session:
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 1
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 16


def test_put_004_allocation_above_remaining_has_no_data_effect(api) -> None:
    """TEST-PUT-004: over-allocation is rejected without allocation or stock."""
    client, factory, fixture = api

    response = client.post(
        "/api/v1/putaways",
        json=payload(fixture, quantity=17),
        headers={"Idempotency-Key": "TEST-PUT-004"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == ("PUTAWAY_EXCEEDS_ELIGIBLE_QUANTITY")
    with factory() as session:
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 0
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 0


def test_put_005_has_no_transfer_or_movement_write_path(api) -> None:
    """TEST-PUT-005: the slice introduces no Transfer or Movement persistence."""
    client, factory, fixture = api

    response = client.post(
        "/api/v1/putaways",
        json=payload(fixture),
        headers={"Idempotency-Key": "TEST-PUT-005"},
    )

    assert response.status_code == 201
    table_names = set(inspect(factory.kw["bind"]).get_table_names())
    assert "transfers" not in table_names
    assert "movements" not in table_names


def test_idempotency_key_reuse_with_different_payload_is_a_conflict(api) -> None:
    client, factory, fixture = api
    headers = {"Idempotency-Key": "different-payload"}
    first = client.post("/api/v1/putaways", json=payload(fixture), headers=headers)
    conflict = client.post(
        "/api/v1/putaways",
        json=payload(fixture, destination_location_id=str(fixture.sales_shelf_id)),
        headers=headers,
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    with factory() as session:
        assert session.scalar(select(func.count(PutawayAllocation.id))) == 1
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 16


def test_context_reports_eligible_quantity_and_tracked_locations(api) -> None:
    client, _factory, fixture = api

    response = client.get(f"/api/v1/putaways/context/{fixture.receive_line_id}")

    assert response.status_code == 200
    assert response.json()["sku"] == "SKU-001"
    assert response.json()["eligible_quantity"] == 16
    assert {item["code"] for item in response.json()["locations"]} == {
        "BACKROOM",
        "SALES_SHELF",
    }
