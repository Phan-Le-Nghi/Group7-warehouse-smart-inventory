from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth import WAREHOUSE_STAFF, Actor, Role, get_actor
from warehouse_api.db import get_db_session
from warehouse_api.main import app
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
from warehouse_api.stock import ordered_location_ids


@dataclass(frozen=True, slots=True)
class PickFixture:
    pick_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    backroom_id: UUID
    sales_shelf_id: UUID
    actor: Actor
    unrelated_sku_id: UUID


@pytest.fixture
def pick_api() -> Iterator[tuple[TestClient, sessionmaker[Session], PickFixture]]:
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

    fixture = PickFixture(
        pick_id=uuid4(),
        warehouse_id=uuid4(),
        sku_id=uuid4(),
        backroom_id=uuid4(),
        sales_shelf_id=uuid4(),
        actor=Actor(uuid4(), "pick.warehouse_staff", WAREHOUSE_STAFF),
        unrelated_sku_id=uuid4(),
    )
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=fixture.actor.user_id,
                    login_identifier=fixture.actor.login_identifier,
                    password_hash="test-only",
                    role=fixture.actor.role.value,
                    is_active=True,
                ),
                Warehouse(id=fixture.warehouse_id, code="MAIN"),
                Sku(id=fixture.sku_id, code="PICK-SKU"),
                Sku(id=fixture.unrelated_sku_id, code="UNRELATED-SKU"),
            ]
        )
        session.flush()

        session.add_all(
            [
                InternalLocation(
                    id=fixture.backroom_id,
                    warehouse_id=fixture.warehouse_id,
                    code="BACKROOM",
                ),
                InternalLocation(
                    id=fixture.sales_shelf_id,
                    warehouse_id=fixture.warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()

        session.add(
            PickRequest(
                id=fixture.pick_id,
                warehouse_id=fixture.warehouse_id,
                sku_id=fixture.sku_id,
                requested_quantity=10,
            )
        )
        session.add_all(
            [
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.backroom_id,
                    quantity=12,
                ),
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.sales_shelf_id,
                    quantity=6,
                ),
                StockBalance(
                    sku_id=fixture.unrelated_sku_id,
                    location_id=fixture.backroom_id,
                    quantity=99,
                ),
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
    app.dependency_overrides[get_actor] = lambda: fixture.actor
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(
    fixture: PickFixture, allocations: list[dict[str, object]] | None = None
) -> dict[str, object]:
    return {
        "pick_id": str(fixture.pick_id),
        "allocations": allocations
        if allocations is not None
        else [{"source_location_id": str(fixture.backroom_id), "quantity": 10}],
    }


def snapshot(factory: sessionmaker[Session], fixture: PickFixture) -> dict[str, object]:
    with factory() as session:
        pick = session.get(PickRequest, fixture.pick_id)
        assert pick is not None
        balances = dict(
            session.execute(
                select(StockBalance.location_id, StockBalance.quantity).where(
                    StockBalance.sku_id == fixture.sku_id
                )
            ).all()
        )
        unrelated = session.scalar(
            select(StockBalance.quantity).where(
                StockBalance.sku_id == fixture.unrelated_sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        return {
            "outcome": pick.outcome,
            "allocation_count": session.scalar(
                select(func.count(PickAllocation.id)).where(
                    PickAllocation.pick_id == fixture.pick_id
                )
            ),
            "balances": balances,
            "unrelated": unrelated,
        }


def test_pick_context_reports_zero_for_missing_balance(pick_api) -> None:
    client, factory, fixture = pick_api
    with factory.begin() as session:
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.sales_shelf_id,
            )
        )
        assert balance is not None
        session.delete(balance)

    response = client.get(f"/api/v1/picks/context/{fixture.pick_id}")

    assert response.status_code == 200
    assert response.json()["requested_quantity"] == 10
    assert response.json()["warehouse_total"] == 12
    quantities = {
        item["code"]: item["available_quantity"]
        for item in response.json()["locations"]
    }
    assert quantities == {"BACKROOM": 12, "SALES_SHELF": 0}


def test_full_single_location_pick(pick_api) -> None:
    client, factory, fixture = pick_api

    response = client.post("/api/v1/picks", json=payload(fixture))

    assert response.status_code == 201
    assert response.json()["outcome"] == "FULLY_COMPLETED"
    assert response.json()["picked_quantity"] == 10
    assert response.json()["remaining_quantity"] == 0
    assert response.json()["warehouse_total"] == 8
    effects = snapshot(factory, fixture)
    assert effects["allocation_count"] == 1
    assert effects["balances"] == {
        fixture.backroom_id: 2,
        fixture.sales_shelf_id: 6,
    }
    assert effects["unrelated"] == 99


def test_full_multi_location_pick(pick_api) -> None:
    client, factory, fixture = pick_api
    allocations = [
        {"source_location_id": str(fixture.sales_shelf_id), "quantity": 3},
        {"source_location_id": str(fixture.backroom_id), "quantity": 7},
    ]

    response = client.post("/api/v1/picks", json=payload(fixture, allocations))

    assert response.status_code == 201
    assert response.json()["outcome"] == "FULLY_COMPLETED"
    assert {
        item["remaining_source_quantity"] for item in response.json()["allocations"]
    } == {
        3,
        5,
    }
    assert snapshot(factory, fixture)["allocation_count"] == 2


def test_partial_pick_records_one_immutable_result(pick_api) -> None:
    client, factory, fixture = pick_api
    request = payload(
        fixture,
        [{"source_location_id": str(fixture.backroom_id), "quantity": 6}],
    )

    first = client.post("/api/v1/picks", json=request)
    second = client.post("/api/v1/picks", json=request)

    assert first.status_code == 201
    assert first.json()["outcome"] == "PARTIAL_INSUFFICIENT"
    assert first.json()["remaining_quantity"] == 4
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PICK_ALREADY_RECORDED"
    effects = snapshot(factory, fixture)
    assert effects["allocation_count"] == 1
    assert effects["balances"][fixture.backroom_id] == 6


@pytest.mark.parametrize("quantity", ["1", 1.5, True])
def test_non_integer_quantity_is_invalid_quantity(pick_api, quantity) -> None:
    client, factory, fixture = pick_api
    request = payload(
        fixture,
        [{"source_location_id": str(fixture.backroom_id), "quantity": quantity}],
    )

    response = client.post("/api/v1/picks", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    assert snapshot(factory, fixture)["outcome"] is None


@pytest.mark.parametrize("quantity", [0, -1])
def test_non_positive_quantity_has_no_effect(pick_api, quantity) -> None:
    client, factory, fixture = pick_api
    request = payload(
        fixture,
        [{"source_location_id": str(fixture.backroom_id), "quantity": quantity}],
    )

    response = client.post("/api/v1/picks", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    assert snapshot(factory, fixture)["allocation_count"] == 0


@pytest.mark.parametrize("allocations", [[], "bad", [{}]])
def test_malformed_allocations_have_typed_error(pick_api, allocations) -> None:
    client, factory, fixture = pick_api
    request = payload(fixture)
    request["allocations"] = allocations

    response = client.post("/api/v1/picks", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ALLOCATIONS"
    assert snapshot(factory, fixture)["allocation_count"] == 0


def test_over_pick_and_duplicate_source_have_no_effect(pick_api) -> None:
    client, factory, fixture = pick_api
    over = client.post(
        "/api/v1/picks",
        json=payload(
            fixture,
            [{"source_location_id": str(fixture.backroom_id), "quantity": 11}],
        ),
    )
    duplicate = client.post(
        "/api/v1/picks",
        json=payload(
            fixture,
            [
                {"source_location_id": str(fixture.backroom_id), "quantity": 3},
                {"source_location_id": str(fixture.backroom_id), "quantity": 3},
            ],
        ),
    )

    assert over.status_code == 422
    assert over.json()["error"]["code"] == "PICK_EXCEEDS_REQUESTED_QUANTITY"
    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SOURCE_LOCATION"
    assert snapshot(factory, fixture)["allocation_count"] == 0


def test_foreign_source_is_invalid(pick_api) -> None:
    client, factory, fixture = pick_api
    foreign_id = uuid4()
    with factory.begin() as session:
        foreign_warehouse = Warehouse(code="FOREIGN")
        session.add(foreign_warehouse)
        session.flush()
        session.add(
            InternalLocation(
                id=foreign_id,
                warehouse_id=foreign_warehouse.id,
                code="BACKROOM",
            )
        )

    response = client.post(
        "/api/v1/picks",
        json=payload(
            fixture,
            [{"source_location_id": str(foreign_id), "quantity": 1}],
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SOURCE_LOCATION"
    assert snapshot(factory, fixture)["allocation_count"] == 0


def test_missing_or_stale_balance_is_insufficient_and_not_created(pick_api) -> None:
    client, factory, fixture = pick_api
    context = client.get(f"/api/v1/picks/context/{fixture.pick_id}")
    assert context.json()["warehouse_total"] == 18
    with factory.begin() as session:
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        assert balance is not None
        balance.quantity = 2

    stale = client.post("/api/v1/picks", json=payload(fixture))
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "INSUFFICIENT_SOURCE_STOCK"
    assert snapshot(factory, fixture)["balances"][fixture.backroom_id] == 2

    with factory.begin() as session:
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.sales_shelf_id,
            )
        )
        assert balance is not None
        session.delete(balance)
    missing = client.post(
        "/api/v1/picks",
        json=payload(
            fixture,
            [{"source_location_id": str(fixture.sales_shelf_id), "quantity": 1}],
        ),
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "INSUFFICIENT_SOURCE_STOCK"
    with factory() as session:
        assert (
            session.scalar(
                select(func.count(StockBalance.id)).where(
                    StockBalance.sku_id == fixture.sku_id,
                    StockBalance.location_id == fixture.sales_shelf_id,
                )
            )
            == 0
        )


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_wrong_role_is_forbidden(pick_api, role) -> None:
    client, factory, fixture = pick_api
    app.dependency_overrides[get_actor] = lambda: Actor(
        uuid4(), f"pick.{role.value.lower()}", role
    )

    response = client.post("/api/v1/picks", json=payload(fixture))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert snapshot(factory, fixture)["outcome"] is None


def test_missing_session_is_unauthorized(pick_api) -> None:
    client, factory, fixture = pick_api
    del app.dependency_overrides[get_actor]

    response = client.post("/api/v1/picks", json=payload(fixture))

    assert response.status_code == 401
    assert snapshot(factory, fixture)["outcome"] is None


def test_missing_pick_is_not_found(pick_api) -> None:
    client, _factory, fixture = pick_api
    request = payload(fixture)
    request["pick_id"] = str(uuid4())

    response = client.post("/api/v1/picks", json=request)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PICK_NOT_FOUND"


def test_missing_pick_context_is_not_found(pick_api) -> None:
    client, _factory, _fixture = pick_api

    response = client.get(f"/api/v1/picks/context/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PICK_NOT_FOUND"


def test_pick_context_requires_warehouse_staff(pick_api) -> None:
    client, _factory, fixture = pick_api
    app.dependency_overrides[get_actor] = lambda: Actor(
        uuid4(), "pick.manager", Role.MANAGER
    )
    forbidden = client.get(f"/api/v1/picks/context/{fixture.pick_id}")
    del app.dependency_overrides[get_actor]
    unauthorized = client.get(f"/api/v1/picks/context/{fixture.pick_id}")

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
    assert unauthorized.status_code == 401


def test_persistence_failure_rolls_back_all_writes(pick_api, monkeypatch) -> None:
    _client, factory, fixture = pick_api
    command = PickCommand.model_validate(payload(fixture))
    with factory() as session:
        monkeypatch.setattr(
            session,
            "flush",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("simulated persistence failure")
            ),
        )
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            confirm_pick(session, command, fixture.actor)
        session.rollback()

    effects = snapshot(factory, fixture)
    assert effects["outcome"] is None
    assert effects["allocation_count"] == 0
    assert effects["balances"][fixture.backroom_id] == 12


def test_source_ids_are_ordered_independently_of_client_order() -> None:
    first, second = uuid4(), uuid4()
    expected = sorted([first, second], key=str)

    assert ordered_location_ids([second, first]) == expected
    assert ordered_location_ids([first, second]) == expected


def test_pick_request_database_constraints(pick_api) -> None:
    _client, factory, fixture = pick_api
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            PickRequest(
                warehouse_id=fixture.warehouse_id,
                sku_id=fixture.sku_id,
                requested_quantity=0,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            PickRequest(
                warehouse_id=fixture.warehouse_id,
                sku_id=fixture.sku_id,
                requested_quantity=1,
                outcome="FULLY_COMPLETED",
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            PickRequest(
                warehouse_id=fixture.warehouse_id,
                sku_id=fixture.sku_id,
                requested_quantity=1,
                outcome="NOT_APPROVED",
                confirmed_by_user_id=fixture.actor.user_id,
                confirmed_at=datetime.now(UTC),
            )
        )
        session.flush()


def test_pick_allocation_database_constraints(pick_api) -> None:
    _client, factory, fixture = pick_api
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            PickAllocation(
                pick_id=fixture.pick_id,
                source_location_id=fixture.backroom_id,
                quantity=0,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add_all(
            [
                PickAllocation(
                    pick_id=fixture.pick_id,
                    source_location_id=fixture.backroom_id,
                    quantity=1,
                ),
                PickAllocation(
                    pick_id=fixture.pick_id,
                    source_location_id=fixture.backroom_id,
                    quantity=1,
                ),
            ]
        )
        session.flush()
