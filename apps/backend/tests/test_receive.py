from collections.abc import Iterator
from dataclasses import dataclass
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warehouse_api.auth import Actor, Role, get_actor
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
    User,
    Warehouse,
)
from warehouse_api.receive import record_receive
from warehouse_api.schemas import ReceiveRecordRequest


@dataclass(frozen=True, slots=True)
class ReceiveFixture:
    receive_id: UUID
    line_ids: tuple[UUID, UUID]
    sku_ids: tuple[UUID, UUID]
    backroom_id: UUID
    actor: Actor


@pytest.fixture
def receive_api() -> Iterator[tuple[TestClient, sessionmaker[Session], ReceiveFixture]]:
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

    actor = Actor(uuid4(), "receive.staff", Role.WAREHOUSE_STAFF)
    fixture = ReceiveFixture(
        receive_id=uuid4(),
        line_ids=(uuid4(), uuid4()),
        sku_ids=(uuid4(), uuid4()),
        backroom_id=uuid4(),
        actor=actor,
    )
    with factory.begin() as session:
        warehouse = Warehouse(code="RECEIVE-WAREHOUSE")
        session.add(warehouse)
        session.flush()
        session.add(
            User(
                id=actor.user_id,
                login_identifier=actor.login_identifier,
                password_hash="test-only-not-a-real-hash",
                role=actor.role.value,
            )
        )
        skus = [
            Sku(id=fixture.sku_ids[0], code="REC-SKU-001"),
            Sku(id=fixture.sku_ids[1], code="REC-SKU-002"),
        ]
        session.add_all(skus)
        session.flush()
        receive = Receive(
            id=fixture.receive_id,
            warehouse_id=warehouse.id,
            expected_reference=" DELIVERY-001 ",
        )
        session.add(receive)
        session.flush()
        session.add_all(
            [
                ReceiveLine(
                    id=fixture.line_ids[0],
                    receive_id=receive.id,
                    sku_id=skus[0].id,
                    expected_quantity=16,
                ),
                ReceiveLine(
                    id=fixture.line_ids[1],
                    receive_id=receive.id,
                    sku_id=skus[1].id,
                    expected_quantity=5,
                ),
            ]
        )
        location = InternalLocation(
            id=fixture.backroom_id,
            warehouse_id=warehouse.id,
            code="BACKROOM",
        )
        session.add(location)
        session.flush()
        session.add_all(
            [
                StockBalance(sku_id=sku.id, location_id=location.id, quantity=0)
                for sku in skus
            ]
        )

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
    app.dependency_overrides[get_actor] = lambda: actor
    with TestClient(app) as client:
        yield client, factory, fixture
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def record_payload(
    fixture: ReceiveFixture,
    *,
    reference: str = "DELIVERY-001",
    quantities: tuple[int, int] = (16, 5),
) -> dict[str, object]:
    return {
        "receive_id": str(fixture.receive_id),
        "document_reference": reference,
        "lines": [
            {
                "receive_line_id": str(line_id),
                "sku_id": str(sku_id),
                "actual_quantity": quantity,
            }
            for line_id, sku_id, quantity in zip(
                fixture.line_ids, fixture.sku_ids, quantities, strict=True
            )
        ],
    }


def snapshot_effects(
    factory: sessionmaker[Session],
) -> tuple[int, int, int]:
    with factory() as session:
        return (
            int(session.scalar(select(func.sum(StockBalance.quantity))) or 0),
            int(session.scalar(select(func.count(PutawayAllocation.id))) or 0),
            int(session.scalar(select(func.count(ReceiveLine.actual_quantity))) or 0),
        )


def test_rec_001_004_008_013_014_records_matching_context_without_side_effects(
    receive_api,
) -> None:
    client, factory, fixture = receive_api
    before = snapshot_effects(factory)

    response = client.post("/api/v1/receives", json=record_payload(fixture))

    assert response.status_code == 201
    body = response.json()
    assert body["reference"] == {
        "expected": "DELIVERY-001",
        "document": "DELIVERY-001",
        "match_status": "REFERENCE_MATCH",
        "reviewed_by_user_id": None,
        "reviewed_at": None,
    }
    assert body["putaway_eligible"] is True
    assert [line["quantity_discrepancy"] for line in body["lines"]] == [0, 0]
    assert snapshot_effects(factory) == (before[0], before[1], 2)
    assert "authoritative_reference" not in body
    assert "completed_at" not in body
    assert "transfers" not in inspect(factory.kw["bind"]).get_table_names()
    assert "movements" not in inspect(factory.kw["bind"]).get_table_names()


@pytest.mark.parametrize(
    ("quantities", "expected_discrepancies"),
    [((14, 4), [-2, -1]), ((18, 7), [2, 2])],
)
def test_rec_002_003_persists_signed_discrepancy(
    receive_api, quantities, expected_discrepancies
) -> None:
    client, factory, fixture = receive_api

    response = client.post(
        "/api/v1/receives",
        json=record_payload(fixture, quantities=quantities),
    )

    assert response.status_code == 201
    response_by_id = {
        line["receive_line_id"]: line for line in response.json()["lines"]
    }
    for line_id, quantity, discrepancy in zip(
        fixture.line_ids, quantities, expected_discrepancies, strict=True
    ):
        assert response_by_id[str(line_id)]["actual_quantity"] == quantity
        assert response_by_id[str(line_id)]["quantity_discrepancy"] == discrepancy
    with factory() as session:
        persisted = session.scalars(select(ReceiveLine.actual_quantity)).all()
        assert sorted(persisted) == sorted(quantities)


def test_rec_005_reference_mismatch_preserves_both_values(receive_api) -> None:
    client, _factory, fixture = receive_api

    response = client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="delivery-001"),
    )

    assert response.status_code == 201
    assert response.json()["reference"]["expected"] == "DELIVERY-001"
    assert response.json()["reference"]["document"] == "delivery-001"
    assert response.json()["reference"]["match_status"] == "REFERENCE_MISMATCH"
    assert response.json()["putaway_eligible"] is False


@pytest.mark.parametrize("quantity", [-1, "sixteen", 1.5, True])
def test_rec_006_invalid_quantity_has_no_write(receive_api, quantity) -> None:
    client, factory, fixture = receive_api
    request = record_payload(fixture)
    request["lines"][0]["actual_quantity"] = quantity  # type: ignore[index]

    response = client.post("/api/v1/receives", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    assert snapshot_effects(factory)[2] == 0


def test_rec_007_missing_required_field_is_invalid_request(receive_api) -> None:
    client, factory, fixture = receive_api
    request = record_payload(fixture)
    del request["lines"][0]["actual_quantity"]  # type: ignore[index]

    response = client.post("/api/v1/receives", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert snapshot_effects(factory)[2] == 0


@pytest.mark.parametrize("role", [Role.MANAGER, Role.PURCHASING, Role.ADMIN])
def test_rec_009_wrong_role_is_forbidden(receive_api, role) -> None:
    client, factory, fixture = receive_api
    app.dependency_overrides[get_actor] = lambda: Actor(
        uuid4(), f"receive.{role.value.lower()}", role
    )

    response = client.post("/api/v1/receives", json=record_payload(fixture))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert snapshot_effects(factory)[2] == 0


def test_rec_010_missing_session_is_unauthorized(receive_api) -> None:
    client, factory, fixture = receive_api
    del app.dependency_overrides[get_actor]

    response = client.post("/api/v1/receives", json=record_payload(fixture))

    assert response.status_code == 401
    assert snapshot_effects(factory)[2] == 0


def test_rec_011_unknown_receive_and_foreign_line_are_atomic(receive_api) -> None:
    client, factory, fixture = receive_api
    unknown_request = record_payload(fixture)
    unknown_request["receive_id"] = str(uuid4())
    unknown = client.post("/api/v1/receives", json=unknown_request)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "RECEIVE_NOT_FOUND"

    mismatch_request = record_payload(fixture)
    mismatch_request["lines"][0]["receive_line_id"] = str(uuid4())  # type: ignore[index]
    mismatch = client.post("/api/v1/receives", json=mismatch_request)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "RECEIVE_CONTEXT_MISMATCH"
    assert snapshot_effects(factory)[2] == 0


def test_rec_012_persistence_failure_rolls_back(receive_api, monkeypatch) -> None:
    _client, factory, fixture = receive_api
    command = ReceiveRecordRequest.model_validate(record_payload(fixture))
    with factory() as session:
        original_flush = session.flush
        calls = 0

        def fail_final_flush(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("simulated persistence failure")
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(session, "flush", fail_final_flush)
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            record_receive(session, command, fixture.actor)
        session.rollback()

    assert snapshot_effects(factory)[2] == 0


def test_rec_015_019_match_remains_putaway_compatible(receive_api) -> None:
    client, _factory, fixture = receive_api
    recorded = client.post("/api/v1/receives", json=record_payload(fixture))
    assert recorded.status_code == 201

    context = client.get(f"/api/v1/putaways/context/{fixture.line_ids[0]}")

    assert context.status_code == 200
    assert context.json()["eligible_quantity"] == 16


def test_rec_016_acknowledges_mismatch_without_changing_references(receive_api) -> None:
    client, factory, fixture = receive_api
    client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="DELIVERY-OTHER"),
    )

    response = client.post(
        f"/api/v1/receives/{fixture.receive_id}/reference-review", json={}
    )

    assert response.status_code == 200
    assert response.json()["match_status"] == "REFERENCE_MISMATCH"
    assert response.json()["reviewed_by_user_id"] == str(fixture.actor.user_id)
    assert response.json()["putaway_eligible"] is True
    with factory() as session:
        receive = session.get(Receive, fixture.receive_id)
        assert receive is not None
        assert receive.expected_reference == "DELIVERY-001"
        assert receive.document_reference == "DELIVERY-OTHER"


def test_rec_017_018_unreviewed_mismatch_blocks_putaway(receive_api) -> None:
    client, factory, fixture = receive_api
    client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="DELIVERY-OTHER"),
    )

    context = client.get(f"/api/v1/putaways/context/{fixture.line_ids[0]}")
    confirmation = client.post(
        "/api/v1/putaways",
        headers={"Idempotency-Key": "unreviewed-mismatch"},
        json={
            "receive_line_id": str(fixture.line_ids[0]),
            "sku_id": str(fixture.sku_ids[0]),
            "quantity": 16,
            "destination_location_id": str(fixture.backroom_id),
        },
    )

    assert context.status_code == 409
    assert confirmation.status_code == 409
    assert context.json()["error"]["code"] == "REFERENCE_REVIEW_REQUIRED"
    assert confirmation.json()["error"]["code"] == "REFERENCE_REVIEW_REQUIRED"
    assert snapshot_effects(factory)[:2] == (0, 0)


def test_rec_019_reviewed_mismatch_becomes_putaway_compatible(receive_api) -> None:
    client, _factory, fixture = receive_api
    client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="DELIVERY-OTHER"),
    )
    client.post(f"/api/v1/receives/{fixture.receive_id}/reference-review", json={})

    context = client.get(f"/api/v1/putaways/context/{fixture.line_ids[0]}")

    assert context.status_code == 200
    assert context.json()["eligible_quantity"] == 16


def test_rec_020_duplicate_record_preserves_original_facts(receive_api) -> None:
    client, factory, fixture = receive_api
    first = client.post("/api/v1/receives", json=record_payload(fixture))

    duplicate = client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="CHANGED", quantities=(100, 100)),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RECEIVE_ALREADY_RECORDED"
    with factory() as session:
        receive = session.get(Receive, fixture.receive_id)
        assert receive is not None
        assert receive.document_reference == "DELIVERY-001"
        assert sorted(
            session.scalars(
                select(ReceiveLine.actual_quantity).where(
                    ReceiveLine.receive_id == fixture.receive_id
                )
            ).all()
        ) == [5, 16]


@pytest.mark.parametrize("mutation", ["omit", "duplicate"])
def test_rec_021_incomplete_or_duplicate_line_set_is_atomic(
    receive_api, mutation
) -> None:
    client, factory, fixture = receive_api
    request = record_payload(fixture)
    if mutation == "omit":
        request["lines"] = request["lines"][:1]  # type: ignore[index]
    else:
        request["lines"][1] = request["lines"][0].copy()  # type: ignore[index]

    response = client.post("/api/v1/receives", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INCOMPLETE_RECEIVE_CONTEXT"
    assert snapshot_effects(factory)[2] == 0


def test_unrecorded_prepared_line_is_blocked_from_putaway(receive_api) -> None:
    client, factory, fixture = receive_api

    response = client.get(f"/api/v1/putaways/context/{fixture.line_ids[0]}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RECEIVE_NOT_RECORDED"
    assert snapshot_effects(factory)[:2] == (0, 0)


def test_receive_context_returns_prepared_state(receive_api) -> None:
    client, _factory, fixture = receive_api

    response = client.get(f"/api/v1/receives/context/{fixture.receive_id}")

    assert response.status_code == 200
    assert response.json()["reference"]["expected"] == "DELIVERY-001"
    assert response.json()["recorded_at"] is None
    assert response.json()["putaway_eligible"] is False
    assert len(response.json()["lines"]) == 2


def test_unprepared_receive_context_is_rejected(receive_api) -> None:
    client, factory, fixture = receive_api
    with factory.begin() as session:
        receive = session.get(Receive, fixture.receive_id)
        assert receive is not None
        receive.expected_reference = None

    response = client.get(f"/api/v1/receives/context/{fixture.receive_id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RECEIVE_CONTEXT_NOT_PREPARED"


def test_reference_review_conflicts_are_typed(receive_api) -> None:
    client, _factory, fixture = receive_api
    before_record = client.post(
        f"/api/v1/receives/{fixture.receive_id}/reference-review", json={}
    )
    assert before_record.status_code == 409
    assert before_record.json()["error"]["code"] == "RECEIVE_NOT_RECORDED"

    client.post("/api/v1/receives", json=record_payload(fixture))
    match = client.post(
        f"/api/v1/receives/{fixture.receive_id}/reference-review", json={}
    )
    assert match.status_code == 409
    assert match.json()["error"]["code"] == "REFERENCE_REVIEW_NOT_REQUIRED"


def test_second_reference_review_is_a_typed_conflict(receive_api) -> None:
    client, _factory, fixture = receive_api
    client.post(
        "/api/v1/receives",
        json=record_payload(fixture, reference="DELIVERY-OTHER"),
    )
    first = client.post(
        f"/api/v1/receives/{fixture.receive_id}/reference-review", json={}
    )
    second = client.post(
        f"/api/v1/receives/{fixture.receive_id}/reference-review", json={}
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "REFERENCE_ALREADY_REVIEWED"
