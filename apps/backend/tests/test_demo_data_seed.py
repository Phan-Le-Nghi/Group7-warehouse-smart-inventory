from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warehouse_api.demo_data_seed import (
    DEMO_BACKROOM_ID,
    DEMO_QUANTITY,
    DEMO_RECEIVE_ID,
    DEMO_RECEIVE_LINE_ID,
    DEMO_SKU_ID,
    DEMO_WAREHOUSE_ID,
    main,
    seed_demo_data,
    seed_demo_dataset,
)
from warehouse_api.models import (
    InternalLocation,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    User,
    Warehouse,
)


def test_demo_dataset_is_idempotent_and_preserves_putaway_effects(
    db_session: Session,
) -> None:
    password = "test-only-demo-password"

    first = seed_demo_dataset(db_session, password)
    assert first.users.created == 4
    assert first.data.created == 6
    assert db_session.scalar(select(func.count(StockBalance.id))) == 0
    assert db_session.scalar(select(func.count(PutawayAllocation.id))) == 0

    allocation_id = uuid4()
    db_session.add_all(
        [
            PutawayAllocation(
                id=allocation_id,
                receive_line_id=DEMO_RECEIVE_LINE_ID,
                sku_id=DEMO_SKU_ID,
                quantity=5,
                destination_location_id=DEMO_BACKROOM_ID,
                idempotency_key="demo-test-putaway",
                request_fingerprint="a" * 64,
            ),
            StockBalance(
                sku_id=DEMO_SKU_ID,
                location_id=DEMO_BACKROOM_ID,
                quantity=5,
            ),
        ]
    )
    db_session.flush()

    second = seed_demo_dataset(db_session, password)

    assert second.users.unchanged == 4
    assert second.data.created == 0
    assert second.data.unchanged == 6
    assert db_session.scalar(select(func.count(Warehouse.id))) == 1
    assert db_session.scalar(select(func.count(InternalLocation.id))) == 2
    assert db_session.scalar(select(func.count(Sku.id))) == 1
    assert db_session.scalar(select(func.count(Receive.id))) == 1
    assert db_session.scalar(select(func.count(ReceiveLine.id))) == 1
    assert db_session.scalar(select(func.count(PutawayAllocation.id))) == 1
    assert db_session.get(PutawayAllocation, allocation_id).quantity == 5
    balance = db_session.scalar(
        select(StockBalance).where(
            StockBalance.sku_id == DEMO_SKU_ID,
            StockBalance.location_id == DEMO_BACKROOM_ID,
        )
    )
    assert balance is not None
    assert balance.quantity == 5
    line = db_session.get(ReceiveLine, DEMO_RECEIVE_LINE_ID)
    assert line is not None
    assert line.actual_quantity == DEMO_QUANTITY


def test_demo_dataset_fails_instead_of_overwriting_natural_key_conflict(
    db_session: Session,
) -> None:
    db_session.add(Warehouse(code="MAIN"))
    db_session.flush()

    with pytest.raises(RuntimeError, match="natural key already uses another ID"):
        seed_demo_dataset(db_session, "test-only-demo-password")

    warehouse = db_session.scalar(select(Warehouse).where(Warehouse.code == "MAIN"))
    assert warehouse is not None
    assert warehouse.id != DEMO_WAREHOUSE_ID


def test_demo_data_seed_is_disabled_in_production(
    db_session: Session, monkeypatch
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "must-not-be-used")

    with pytest.raises(RuntimeError, match="disabled"):
        main()

    with pytest.raises(RuntimeError, match="disabled"):
        seed_demo_data(db_session)


def test_demo_dataset_does_not_print_secrets_or_database_url(
    db_session: Session, capsys
) -> None:
    password = "secret-that-must-not-be-printed"

    seed_demo_dataset(db_session, password)

    captured = capsys.readouterr()
    assert password not in captured.out
    assert password not in captured.err
    assert "DATABASE_URL" not in captured.out
    assert "DATABASE_URL" not in captured.err


def test_demo_receive_is_recorded_but_has_no_initial_stock(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")

    receive = db_session.get(Receive, DEMO_RECEIVE_ID)
    line = db_session.get(ReceiveLine, DEMO_RECEIVE_LINE_ID)
    staff = db_session.scalar(
        select(User).where(User.login_identifier == "demo.warehouse_staff")
    )
    assert receive is not None
    assert line is not None
    assert staff is not None
    assert receive.warehouse_id == DEMO_WAREHOUSE_ID
    assert receive.reference_match_status == "REFERENCE_MATCH"
    assert receive.recorded_by_user_id == staff.id
    assert receive.recorded_at is not None
    assert line.actual_quantity == DEMO_QUANTITY
    assert line.quantity_discrepancy == 0
    assert db_session.scalar(select(func.count(StockBalance.id))) == 0
