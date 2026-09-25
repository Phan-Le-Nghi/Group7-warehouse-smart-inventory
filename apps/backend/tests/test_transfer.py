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
    Sku,
    StockBalance,
    Transfer,
    User,
    Warehouse,
)
from warehouse_api.schemas import TransferRequest
from warehouse_api.transfer import confirm_transfer


@dataclass(frozen=True, slots=True)
class TransferFixture:
    warehouse_id: UUID
    sku_id: UUID
    unrelated_sku_id: UUID
    backroom_id: UUID
    shelf_id: UUID
    actor: Actor


@pytest.fixture
def transfer_api() -> Iterator[
    tuple[TestClient, sessionmaker[Session], TransferFixture]
]:
    database_url = getenv("TEST_DATABASE_URL")
    engine = (
        create_engine(database_url)
        if database_url
        else create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    fixture = TransferFixture(
        warehouse_id=uuid4(),
        sku_id=uuid4(),
        unrelated_sku_id=uuid4(),
        backroom_id=uuid4(),
        shelf_id=uuid4(),
        actor=Actor(uuid4(), "transfer.staff", WAREHOUSE_STAFF),
    )
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=fixture.actor.user_id,
                    login_identifier=fixture.actor.login_identifier,
                    password_hash="test-only",
                    role=fixture.actor.role.value,
                ),
                Warehouse(id=fixture.warehouse_id, code=f"W-{uuid4().hex}"),
                Sku(id=fixture.sku_id, code=f"SKU-{uuid4().hex}"),
                Sku(id=fixture.unrelated_sku_id, code=f"OTHER-{uuid4().hex}"),
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
                    id=fixture.shelf_id,
                    warehouse_id=fixture.warehouse_id,
                    code="SALES_SHELF",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.backroom_id,
                    quantity=12,
                ),
                StockBalance(
                    sku_id=fixture.sku_id,
                    location_id=fixture.shelf_id,
                    quantity=6,
                ),
                StockBalance(
                    sku_id=fixture.unrelated_sku_id,
                    location_id=fixture.backroom_id,
                    quantity=99,
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
    app.dependency_overrides[get_actor] = lambda: fixture.actor
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(fixture: TransferFixture, **changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "sku_id": str(fixture.sku_id),
        "source_location_id": str(fixture.backroom_id),
        "destination_location_id": str(fixture.shelf_id),
        "quantity": 4,
    }
    result.update(changes)
    return result


def balances(
    factory: sessionmaker[Session], fixture: TransferFixture
) -> dict[UUID, int]:
    with factory() as session:
        return dict(
            session.execute(
                select(StockBalance.location_id, StockBalance.quantity).where(
                    StockBalance.sku_id == fixture.sku_id
                )
            ).all()
        )


def test_valid_transfer_and_safe_replay(transfer_api) -> None:
    client, factory, fixture = transfer_api
    request = payload(fixture)
    headers = {"Idempotency-Key": "Transfer-Key-A"}
    first = client.post("/api/v1/transfers", json=request, headers=headers)
    replay = client.post("/api/v1/transfers", json=request, headers=headers)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["transfer_id"] == first.json()["transfer_id"]
    assert first.json()["stock"] == {
        "source_quantity": 8,
        "destination_quantity": 10,
        "warehouse_total": 18,
    }
    assert balances(factory, fixture) == {
        fixture.backroom_id: 8,
        fixture.shelf_id: 10,
    }
    with factory() as session:
        assert session.scalar(select(func.count(Transfer.id))) == 1
        assert (
            session.scalar(
                select(StockBalance.quantity).where(
                    StockBalance.sku_id == fixture.unrelated_sku_id,
                    StockBalance.location_id == fixture.backroom_id,
                )
            )
            == 99
        )


def test_same_key_different_command_conflicts(transfer_api) -> None:
    client, factory, fixture = transfer_api
    headers = {"Idempotency-Key": "same-key"}
    first = client.post("/api/v1/transfers", json=payload(fixture), headers=headers)
    assert first.status_code == 201
    conflict = client.post(
        "/api/v1/transfers", json=payload(fixture, quantity=3), headers=headers
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert balances(factory, fixture)[fixture.backroom_id] == 8


def test_missing_destination_is_created_atomically(transfer_api) -> None:
    client, factory, fixture = transfer_api
    with factory.begin() as session:
        destination = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.shelf_id,
            )
        )
        assert destination is not None
        session.delete(destination)
    response = client.post(
        "/api/v1/transfers",
        json=payload(fixture),
        headers={"Idempotency-Key": "missing-destination"},
    )
    assert response.status_code == 201
    assert balances(factory, fixture) == {
        fixture.backroom_id: 8,
        fixture.shelf_id: 4,
    }


def test_insufficient_or_missing_source_has_no_effect(transfer_api) -> None:
    client, factory, fixture = transfer_api
    with factory.begin() as session:
        source = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        assert source is not None
        source.quantity = 2
    insufficient = client.post(
        "/api/v1/transfers",
        json=payload(fixture),
        headers={"Idempotency-Key": "insufficient"},
    )
    assert insufficient.status_code == 409
    assert insufficient.json()["error"]["code"] == "INSUFFICIENT_SOURCE_STOCK"
    with factory() as session:
        assert session.scalar(select(func.count(Transfer.id))) == 0
    assert balances(factory, fixture)[fixture.backroom_id] == 2

    with factory.begin() as session:
        source = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.backroom_id,
            )
        )
        assert source is not None
        session.delete(source)
    missing = client.post(
        "/api/v1/transfers",
        json=payload(fixture, quantity=1),
        headers={"Idempotency-Key": "missing-source"},
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "INSUFFICIENT_SOURCE_STOCK"


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "1", True])
def test_invalid_quantity_is_typed_and_has_no_effect(transfer_api, quantity) -> None:
    client, factory, fixture = transfer_api
    response = client.post(
        "/api/v1/transfers",
        json=payload(fixture, quantity=quantity),
        headers={"Idempotency-Key": f"invalid-{quantity}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    assert balances(factory, fixture)[fixture.backroom_id] == 12


def test_same_location_and_invalid_key_have_no_effect(transfer_api) -> None:
    client, factory, fixture = transfer_api
    same = client.post(
        "/api/v1/transfers",
        json=payload(fixture, destination_location_id=str(fixture.backroom_id)),
        headers={"Idempotency-Key": "same-location"},
    )
    missing = client.post("/api/v1/transfers", json=payload(fixture))
    whitespace = client.post(
        "/api/v1/transfers",
        json=payload(fixture),
        headers={"Idempotency-Key": "   "},
    )
    no_quantity_payload = payload(fixture)
    del no_quantity_payload["quantity"]
    missing_quantity = client.post(
        "/api/v1/transfers",
        json=no_quantity_payload,
        headers={"Idempotency-Key": "missing-quantity"},
    )
    assert same.status_code == 422
    assert same.json()["error"]["code"] == "SAME_TRANSFER_LOCATION"
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "INVALID_REQUEST"
    assert whitespace.status_code == 422
    assert whitespace.json()["error"]["code"] == "INVALID_REQUEST"
    assert missing_quantity.status_code == 422
    assert missing_quantity.json()["error"]["code"] == "INVALID_QUANTITY"
    assert balances(factory, fixture)[fixture.backroom_id] == 12


def test_foreign_destination_is_invalid(transfer_api) -> None:
    client, factory, fixture = transfer_api
    foreign_id = uuid4()
    with factory.begin() as session:
        warehouse = Warehouse(code=f"FOREIGN-{uuid4().hex}")
        session.add(warehouse)
        session.flush()
        session.add(
            InternalLocation(id=foreign_id, warehouse_id=warehouse.id, code="BACKROOM")
        )
    response = client.post(
        "/api/v1/transfers",
        json=payload(fixture, destination_location_id=str(foreign_id)),
        headers={"Idempotency-Key": "foreign"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DESTINATION_LOCATION"


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_wrong_role_is_forbidden(transfer_api, role) -> None:
    client, factory, fixture = transfer_api
    app.dependency_overrides[get_actor] = lambda: Actor(uuid4(), "wrong.role", role)
    response = client.post(
        "/api/v1/transfers",
        json=payload(fixture),
        headers={"Idempotency-Key": "forbidden"},
    )
    assert response.status_code == 403
    assert balances(factory, fixture)[fixture.backroom_id] == 12


def test_context_and_unauthenticated_access(transfer_api) -> None:
    client, _factory, fixture = transfer_api
    context = client.get(f"/api/v1/transfers/context/{fixture.sku_id}")
    assert context.status_code == 200
    assert context.json()["warehouse_total"] == 18
    del app.dependency_overrides[get_actor]
    unauthorized = client.get(f"/api/v1/transfers/context/{fixture.sku_id}")
    assert unauthorized.status_code == 401


def test_failure_rolls_back_claim_destination_and_stock(
    transfer_api, monkeypatch
) -> None:
    _client, factory, fixture = transfer_api
    with factory.begin() as session:
        destination = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == fixture.sku_id,
                StockBalance.location_id == fixture.shelf_id,
            )
        )
        assert destination is not None
        session.delete(destination)
    command = TransferRequest.model_validate(payload(fixture))
    with factory() as session:
        original_flush = session.flush
        calls = 0

        def fail_after_changes(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("simulated persistence failure")
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(session, "flush", fail_after_changes)
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            confirm_transfer(session, command, fixture.actor, "rollback")
        session.rollback()
    with factory() as session:
        assert session.scalar(select(func.count(Transfer.id))) == 0
        assert (
            session.scalar(
                select(func.count(StockBalance.id)).where(
                    StockBalance.sku_id == fixture.sku_id,
                    StockBalance.location_id == fixture.shelf_id,
                )
            )
            == 0
        )


def test_transfer_database_constraints(transfer_api) -> None:
    _client, factory, fixture = transfer_api
    base = dict(
        warehouse_id=fixture.warehouse_id,
        sku_id=fixture.sku_id,
        source_location_id=fixture.backroom_id,
        destination_location_id=fixture.shelf_id,
        transferred_by_user_id=fixture.actor.user_id,
        transferred_at=datetime.now(UTC),
        request_fingerprint="a" * 64,
    )
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(Transfer(**base, quantity=0, idempotency_key="bad-quantity"))
        session.flush()
    with pytest.raises(IntegrityError), factory.begin() as session:
        session.add(
            Transfer(
                **(base | {"destination_location_id": fixture.backroom_id}),
                quantity=1,
                idempotency_key="bad-location",
            )
        )
        session.flush()
