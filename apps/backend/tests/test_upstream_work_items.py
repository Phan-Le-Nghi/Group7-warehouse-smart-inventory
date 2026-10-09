from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import warehouse_api.receive as receive_service
from warehouse_api.auth import Actor, Role, get_actor
from warehouse_api.main import app
from warehouse_api.models import (
    InternalLocation,
    PickAllocation,
    PickRequest,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    Warehouse,
)


def set_actor(role: Role) -> None:
    app.dependency_overrides[get_actor] = lambda: Actor(
        user_id=uuid4(), login_identifier=f"test.{role.value.lower()}", role=role
    )


@pytest.fixture
def upstream_data(
    session_factory: sessionmaker[Session],
) -> dict[str, UUID]:
    with session_factory.begin() as session:
        warehouse = Warehouse(code="UPSTREAM-WAREHOUSE")
        first = Sku(code="SKU-ZULU")
        second = Sku(code="SKU-ALPHA")
        backroom = InternalLocation(warehouse_id=warehouse.id, code="BACKROOM")
        shelf = InternalLocation(warehouse_id=warehouse.id, code="SALES_SHELF")
        session.add_all([warehouse, first, second])
        session.flush()
        backroom.warehouse_id = warehouse.id
        shelf.warehouse_id = warehouse.id
        session.add_all([backroom, shelf])
        session.flush()
        session.add(
            StockBalance(sku_id=second.id, location_id=backroom.id, quantity=12)
        )
        return {
            "warehouse_id": warehouse.id,
            "first_sku_id": first.id,
            "second_sku_id": second.id,
            "backroom_id": backroom.id,
        }


def count(session: Session, model: type) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_sku_catalog_is_ordered_read_only_and_role_limited(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
) -> None:
    with session_factory() as session:
        before = (count(session, Sku), count(session, StockBalance))

    for role in (Role.PURCHASING, Role.MANAGER):
        set_actor(role)
        response = api_client.get("/api/v1/skus")
        assert response.status_code == 200
        assert [item["sku"] for item in response.json()["items"]] == [
            "SKU-ALPHA",
            "SKU-ZULU",
        ]

    for role in (Role.WAREHOUSE_STAFF, Role.ADMIN):
        set_actor(role)
        response = api_client.get("/api/v1/skus")
        assert response.status_code == 403

    app.dependency_overrides.pop(get_actor, None)
    assert api_client.get("/api/v1/skus").status_code == 401
    with session_factory() as session:
        assert (count(session, Sku), count(session, StockBalance)) == before


def test_purchasing_creates_multiline_receive_without_stock_effect(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
) -> None:
    set_actor(Role.PURCHASING)
    response = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": "  DELIVERY-UPSTREAM-001  ",
            "lines": [
                {
                    "sku_id": str(upstream_data["first_sku_id"]),
                    "expected_quantity": 5,
                },
                {
                    "sku_id": str(upstream_data["second_sku_id"]),
                    "expected_quantity": 7,
                },
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["expected_reference"] == "DELIVERY-UPSTREAM-001"
    assert body["recorded_at"] is None
    assert [line["expected_quantity"] for line in body["lines"]] == [5, 7]

    with session_factory() as session:
        receive = session.get(Receive, UUID(body["receive_id"]))
        assert receive is not None
        assert receive.document_reference is None
        assert receive.reference_match_status is None
        assert receive.recorded_by_user_id is None
        assert receive.reference_reviewed_at is None
        lines = session.scalars(
            select(ReceiveLine).where(ReceiveLine.receive_id == receive.id)
        ).all()
        assert len(lines) == 2
        assert all(line.actual_quantity is None for line in lines)
        assert all(line.quantity_discrepancy is None for line in lines)
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 12
        assert count(session, PutawayAllocation) == 0


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"expected_reference": "", "lines": []}, "INVALID_REFERENCE"),
        ({"expected_reference": "   ", "lines": []}, "INVALID_REFERENCE"),
        ({"expected_reference": "R" * 256, "lines": []}, "INVALID_REFERENCE"),
        ({"expected_reference": "R", "lines": []}, "INVALID_LINES"),
    ],
)
def test_prepare_receive_rejects_invalid_context(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
    payload: dict[str, object],
    code: str,
) -> None:
    set_actor(Role.PURCHASING)
    response = api_client.post("/api/v1/receives/prepared", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    with session_factory() as session:
        assert count(session, Receive) == 0


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5, "bad"])
def test_prepare_receive_requires_strict_positive_quantity(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
    quantity: object,
) -> None:
    set_actor(Role.PURCHASING)
    response = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": "R-QUANTITY",
            "lines": [
                {
                    "sku_id": str(upstream_data["first_sku_id"]),
                    "expected_quantity": quantity,
                }
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    with session_factory() as session:
        assert count(session, Receive) == 0


def test_prepare_receive_rejects_duplicate_and_unknown_skus_atomically(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
) -> None:
    set_actor(Role.PURCHASING)
    line = {"sku_id": str(upstream_data["first_sku_id"]), "expected_quantity": 1}
    duplicate = api_client.post(
        "/api/v1/receives/prepared",
        json={"expected_reference": "R-DUP", "lines": [line, line]},
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SKU"

    unknown = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": "R-UNKNOWN",
            "lines": [line, {"sku_id": str(uuid4()), "expected_quantity": 2}],
        },
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "SKU_NOT_FOUND"
    with session_factory() as session:
        assert count(session, Receive) == 0
        assert count(session, ReceiveLine) == 0


def test_prepare_receive_rolls_back_when_a_line_write_fails(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_receive_line = ReceiveLine
    duplicate_id = uuid4()

    def conflicting_receive_line(**values: object) -> ReceiveLine:
        return original_receive_line(id=duplicate_id, **values)

    monkeypatch.setattr(receive_service, "ReceiveLine", conflicting_receive_line)
    set_actor(Role.PURCHASING)
    with pytest.raises(IntegrityError):
        api_client.post(
            "/api/v1/receives/prepared",
            json={
                "expected_reference": "R-WRITE-FAILURE",
                "lines": [
                    {
                        "sku_id": str(upstream_data["first_sku_id"]),
                        "expected_quantity": 1,
                    },
                    {
                        "sku_id": str(upstream_data["second_sku_id"]),
                        "expected_quantity": 2,
                    },
                ],
            },
        )
    with session_factory() as session:
        assert count(session, Receive) == 0
        assert count(session, ReceiveLine) == 0


@pytest.mark.parametrize(
    ("role", "status_code"),
    [
        (Role.PURCHASING, 201),
        (Role.WAREHOUSE_STAFF, 403),
        (Role.MANAGER, 403),
        (Role.ADMIN, 403),
    ],
)
def test_prepare_receive_role_matrix(
    api_client: TestClient,
    upstream_data: dict[str, UUID],
    role: Role,
    status_code: int,
) -> None:
    set_actor(role)
    response = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": f"ROLE-{role.value}",
            "lines": [
                {
                    "sku_id": str(upstream_data["first_sku_id"]),
                    "expected_quantity": 1,
                }
            ],
        },
    )
    assert response.status_code == status_code


def test_prepare_receive_requires_authentication(
    api_client: TestClient, upstream_data: dict[str, UUID]
) -> None:
    app.dependency_overrides.pop(get_actor, None)
    response = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": "AUTH",
            "lines": [
                {
                    "sku_id": str(upstream_data["first_sku_id"]),
                    "expected_quantity": 1,
                }
            ],
        },
    )
    assert response.status_code == 401


def test_created_receive_enters_queue_then_hands_off_to_putaway(
    api_client: TestClient, upstream_data: dict[str, UUID]
) -> None:
    set_actor(Role.PURCHASING)
    created = api_client.post(
        "/api/v1/receives/prepared",
        json={
            "expected_reference": "DELIVERY-FLOW",
            "lines": [
                {
                    "sku_id": str(upstream_data["second_sku_id"]),
                    "expected_quantity": 4,
                }
            ],
        },
    ).json()
    line = created["lines"][0]

    set_actor(Role.WAREHOUSE_STAFF)
    queue = api_client.get("/api/v1/receives").json()["items"]
    assert [item["expected_reference"] for item in queue] == ["DELIVERY-FLOW"]
    recorded = api_client.post(
        "/api/v1/receives",
        json={
            "receive_id": created["receive_id"],
            "document_reference": "DELIVERY-FLOW",
            "lines": [
                {
                    "receive_line_id": line["receive_line_id"],
                    "sku_id": line["sku_id"],
                    "actual_quantity": 4,
                }
            ],
        },
    )
    assert recorded.status_code == 201
    assert api_client.get("/api/v1/receives").json()["items"] == []
    putaway = api_client.get("/api/v1/putaways/eligible-lines").json()["items"]
    assert putaway[0]["receive_line_id"] == line["receive_line_id"]


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5, "bad"])
def test_pick_request_requires_strict_positive_quantity(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
    quantity: object,
) -> None:
    set_actor(Role.MANAGER)
    response = api_client.post(
        "/api/v1/picks/requests",
        json={
            "sku_id": str(upstream_data["second_sku_id"]),
            "requested_quantity": quantity,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"
    with session_factory() as session:
        assert count(session, PickRequest) == 0


@pytest.mark.parametrize(
    ("role", "status_code"),
    [
        (Role.MANAGER, 201),
        (Role.WAREHOUSE_STAFF, 403),
        (Role.PURCHASING, 403),
        (Role.ADMIN, 403),
    ],
)
def test_pick_request_role_matrix(
    api_client: TestClient,
    upstream_data: dict[str, UUID],
    role: Role,
    status_code: int,
) -> None:
    set_actor(role)
    response = api_client.post(
        "/api/v1/picks/requests",
        json={
            "sku_id": str(upstream_data["second_sku_id"]),
            "requested_quantity": 4,
        },
    )
    assert response.status_code == status_code


def test_manager_creates_actionable_pick_without_stock_or_allocation_effect(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
    upstream_data: dict[str, UUID],
) -> None:
    set_actor(Role.MANAGER)
    response = api_client.post(
        "/api/v1/picks/requests",
        json={
            "sku_id": str(upstream_data["second_sku_id"]),
            "requested_quantity": 4,
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["outcome"] is None
    with session_factory() as session:
        pick = session.get(PickRequest, UUID(created["pick_id"]))
        assert pick is not None
        assert pick.confirmed_by_user_id is None
        assert pick.confirmed_at is None
        assert count(session, PickAllocation) == 0
        assert session.scalar(select(func.sum(StockBalance.quantity))) == 12

    set_actor(Role.WAREHOUSE_STAFF)
    queue = api_client.get("/api/v1/picks").json()["items"]
    assert queue[0]["pick_id"] == created["pick_id"]
    executed = api_client.post(
        "/api/v1/picks",
        json={
            "pick_id": created["pick_id"],
            "allocations": [
                {
                    "source_location_id": str(upstream_data["backroom_id"]),
                    "quantity": 4,
                }
            ],
        },
    )
    assert executed.status_code == 201
    assert executed.json()["outcome"] == "FULLY_COMPLETED"
    assert api_client.get("/api/v1/picks").json()["items"] == []


def test_pick_request_rejects_unknown_sku_and_requires_authentication(
    api_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    set_actor(Role.MANAGER)
    unknown = api_client.post(
        "/api/v1/picks/requests",
        json={"sku_id": str(uuid4()), "requested_quantity": 1},
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "SKU_NOT_FOUND"
    with session_factory() as session:
        assert count(session, PickRequest) == 0

    app.dependency_overrides.pop(get_actor, None)
    unauthenticated = api_client.post(
        "/api/v1/picks/requests",
        json={"sku_id": str(uuid4()), "requested_quantity": 1},
    )
    assert unauthenticated.status_code == 401
