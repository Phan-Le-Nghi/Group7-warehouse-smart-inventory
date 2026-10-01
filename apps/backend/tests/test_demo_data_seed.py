from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, Role
from warehouse_api.demo_data_seed import (
    DEMO_BACKROOM_ID,
    DEMO_QUANTITY,
    DEMO_RECEIVE_ID,
    DEMO_RECEIVE_LINE_ID,
    DEMO_SALES_SHELF_ID,
    DEMO_SKU_ID,
    DEMO_WAREHOUSE_ID,
    PICK_SMOKE_BACKROOM_QUANTITY,
    PICK_SMOKE_BACKROOM_STOCK_ID,
    PICK_SMOKE_ID,
    PICK_SMOKE_REQUESTED_QUANTITY,
    PICK_SMOKE_SALES_SHELF_QUANTITY,
    PICK_SMOKE_SALES_SHELF_STOCK_ID,
    PICK_SMOKE_SKU_ID,
    RECEIVE_SMOKE_ID,
    RECEIVE_SMOKE_LINE_ID,
    RECEIVE_SMOKE_QUANTITY,
    RECEIVE_SMOKE_REFERENCE,
    RECEIVE_SMOKE_SKU_ID,
    TRANSFER_SMOKE_BACKROOM_QUANTITY,
    TRANSFER_SMOKE_BACKROOM_STOCK_ID,
    TRANSFER_SMOKE_QUANTITY,
    TRANSFER_SMOKE_SALES_SHELF_QUANTITY,
    TRANSFER_SMOKE_SALES_SHELF_STOCK_ID,
    TRANSFER_SMOKE_SKU_ID,
    main,
    seed_demo_data,
    seed_demo_dataset,
)
from warehouse_api.models import (
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
from warehouse_api.pick import confirm_pick
from warehouse_api.receive import record_receive
from warehouse_api.schemas import PickRequest as PickCommand
from warehouse_api.schemas import ReceiveRecordRequest, TransferRequest
from warehouse_api.transfer import confirm_transfer


def test_demo_dataset_is_idempotent_and_preserves_putaway_effects(
    db_session: Session,
) -> None:
    password = "test-only-demo-password"

    first = seed_demo_dataset(db_session, password)
    assert first.users.created == 4
    assert first.data.created == 16
    assert db_session.scalar(select(func.count(StockBalance.id))) == 4
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
    assert second.data.unchanged == 16
    assert db_session.scalar(select(func.count(Warehouse.id))) == 1
    assert db_session.scalar(select(func.count(InternalLocation.id))) == 2
    assert db_session.scalar(select(func.count(Sku.id))) == 4
    assert db_session.scalar(select(func.count(Receive.id))) == 2
    assert db_session.scalar(select(func.count(ReceiveLine.id))) == 2
    assert db_session.scalar(select(func.count(PutawayAllocation.id))) == 1
    assert db_session.scalar(select(func.count(StockBalance.id))) == 5
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
    assert (
        db_session.scalar(
            select(func.count(StockBalance.id)).where(
                StockBalance.sku_id == DEMO_SKU_ID
            )
        )
        == 0
    )


def test_receive_smoke_context_is_prepared_but_unrecorded(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    rerun = seed_demo_dataset(db_session, "test-only-demo-password")

    receive = db_session.get(Receive, RECEIVE_SMOKE_ID)
    line = db_session.get(ReceiveLine, RECEIVE_SMOKE_LINE_ID)

    assert rerun.data.created == 0
    assert rerun.data.unchanged == 16
    assert receive is not None
    assert line is not None
    assert receive.warehouse_id == DEMO_WAREHOUSE_ID
    assert receive.expected_reference == RECEIVE_SMOKE_REFERENCE
    assert receive.document_reference is None
    assert receive.reference_match_status is None
    assert receive.recorded_by_user_id is None
    assert receive.recorded_at is None
    assert receive.reference_reviewed_by_user_id is None
    assert receive.reference_reviewed_at is None
    assert line.receive_id == RECEIVE_SMOKE_ID
    assert line.sku_id == RECEIVE_SMOKE_SKU_ID
    assert line.expected_quantity == RECEIVE_SMOKE_QUANTITY
    assert line.actual_quantity is None
    assert line.quantity_discrepancy is None


def test_demo_seed_preserves_user_recorded_receive_smoke_facts(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    staff = db_session.scalar(
        select(User).where(User.login_identifier == "demo.warehouse_staff")
    )
    assert staff is not None

    record_receive(
        db_session,
        ReceiveRecordRequest.model_validate(
            {
                "receive_id": RECEIVE_SMOKE_ID,
                "document_reference": "USER-RECORDED-DOCUMENT",
                "lines": [
                    {
                        "receive_line_id": RECEIVE_SMOKE_LINE_ID,
                        "sku_id": RECEIVE_SMOKE_SKU_ID,
                        "actual_quantity": 10,
                    }
                ],
            }
        ),
        Actor(staff.id, staff.login_identifier, Role.WAREHOUSE_STAFF),
    )
    recorded_at = db_session.get(Receive, RECEIVE_SMOKE_ID).recorded_at

    result = seed_demo_dataset(db_session, "test-only-demo-password")

    assert result.data.created == 0
    assert result.data.unchanged == 16
    receive = db_session.get(Receive, RECEIVE_SMOKE_ID)
    line = db_session.get(ReceiveLine, RECEIVE_SMOKE_LINE_ID)
    assert receive is not None
    assert line is not None
    assert receive.document_reference == "USER-RECORDED-DOCUMENT"
    assert receive.reference_match_status == "REFERENCE_MISMATCH"
    assert receive.recorded_by_user_id == staff.id
    assert receive.recorded_at == recorded_at
    assert line.actual_quantity == 10
    assert line.quantity_discrepancy == 10 - RECEIVE_SMOKE_QUANTITY


def test_pick_smoke_fixture_is_created_unconfirmed_with_multi_location_stock(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")

    pick = db_session.get(PickRequest, PICK_SMOKE_ID)
    sku = db_session.get(Sku, PICK_SMOKE_SKU_ID)
    backroom = db_session.get(StockBalance, PICK_SMOKE_BACKROOM_STOCK_ID)
    sales_shelf = db_session.get(StockBalance, PICK_SMOKE_SALES_SHELF_STOCK_ID)

    assert pick is not None
    assert sku is not None
    assert backroom is not None
    assert sales_shelf is not None
    assert sku.code == "DEMO-SKU-PICK-SMOKE-001"
    assert pick.warehouse_id == DEMO_WAREHOUSE_ID
    assert pick.sku_id == PICK_SMOKE_SKU_ID
    assert pick.requested_quantity == PICK_SMOKE_REQUESTED_QUANTITY
    assert pick.outcome is None
    assert pick.confirmed_by_user_id is None
    assert pick.confirmed_at is None
    assert backroom.sku_id == PICK_SMOKE_SKU_ID
    assert backroom.location_id == DEMO_BACKROOM_ID
    assert backroom.quantity == PICK_SMOKE_BACKROOM_QUANTITY
    assert sales_shelf.sku_id == PICK_SMOKE_SKU_ID
    assert sales_shelf.location_id == DEMO_SALES_SHELF_ID
    assert sales_shelf.quantity == PICK_SMOKE_SALES_SHELF_QUANTITY
    assert (
        db_session.scalar(
            select(func.count(PickAllocation.id)).where(
                PickAllocation.pick_id == PICK_SMOKE_ID
            )
        )
        == 0
    )


def test_pick_smoke_fixture_second_seed_does_not_duplicate_rows(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    result = seed_demo_dataset(db_session, "test-only-demo-password")

    assert result.data.created == 0
    assert result.data.unchanged == 16
    assert (
        db_session.scalar(
            select(func.count(PickRequest.id)).where(PickRequest.id == PICK_SMOKE_ID)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(StockBalance.id)).where(
                StockBalance.sku_id == PICK_SMOKE_SKU_ID
            )
        )
        == 2
    )


def test_demo_seed_preserves_confirmed_pick_allocations_and_reduced_stock(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    staff = db_session.scalar(
        select(User).where(User.login_identifier == "demo.warehouse_staff")
    )
    assert staff is not None

    confirm_pick(
        db_session,
        PickCommand.model_validate(
            {
                "pick_id": PICK_SMOKE_ID,
                "allocations": [
                    {
                        "source_location_id": DEMO_BACKROOM_ID,
                        "quantity": PICK_SMOKE_BACKROOM_QUANTITY,
                    },
                    {
                        "source_location_id": DEMO_SALES_SHELF_ID,
                        "quantity": PICK_SMOKE_SALES_SHELF_QUANTITY,
                    },
                ],
            }
        ),
        Actor(staff.id, staff.login_identifier, Role.WAREHOUSE_STAFF),
    )
    db_session.expire_all()
    confirmed_pick = db_session.get(PickRequest, PICK_SMOKE_ID)
    assert confirmed_pick is not None
    confirmed_at = confirmed_pick.confirmed_at
    allocation_ids = tuple(
        db_session.scalars(
            select(PickAllocation.id)
            .where(PickAllocation.pick_id == PICK_SMOKE_ID)
            .order_by(PickAllocation.id)
        )
    )

    result = seed_demo_dataset(db_session, "test-only-demo-password")

    assert result.data.created == 0
    assert result.data.unchanged == 16
    pick = db_session.get(PickRequest, PICK_SMOKE_ID)
    assert pick is not None
    assert pick.outcome == "FULLY_COMPLETED"
    assert pick.confirmed_by_user_id == staff.id
    assert pick.confirmed_at == confirmed_at
    assert (
        tuple(
            db_session.scalars(
                select(PickAllocation.id)
                .where(PickAllocation.pick_id == PICK_SMOKE_ID)
                .order_by(PickAllocation.id)
            )
        )
        == allocation_ids
    )
    assert len(allocation_ids) == 2
    assert db_session.get(StockBalance, PICK_SMOKE_BACKROOM_STOCK_ID).quantity == 0
    assert db_session.get(StockBalance, PICK_SMOKE_SALES_SHELF_STOCK_ID).quantity == 0


def test_transfer_smoke_fixture_is_created_without_a_transfer(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")

    sku = db_session.get(Sku, TRANSFER_SMOKE_SKU_ID)
    backroom = db_session.get(StockBalance, TRANSFER_SMOKE_BACKROOM_STOCK_ID)
    sales_shelf = db_session.get(StockBalance, TRANSFER_SMOKE_SALES_SHELF_STOCK_ID)

    assert sku is not None
    assert backroom is not None
    assert sales_shelf is not None
    assert sku.code == "DEMO-SKU-TRANSFER-SMOKE-001"
    assert backroom.sku_id == TRANSFER_SMOKE_SKU_ID
    assert backroom.location_id == DEMO_BACKROOM_ID
    assert backroom.quantity == TRANSFER_SMOKE_BACKROOM_QUANTITY
    assert sales_shelf.sku_id == TRANSFER_SMOKE_SKU_ID
    assert sales_shelf.location_id == DEMO_SALES_SHELF_ID
    assert sales_shelf.quantity == TRANSFER_SMOKE_SALES_SHELF_QUANTITY
    assert (
        db_session.scalar(
            select(func.count(Transfer.id)).where(
                Transfer.sku_id == TRANSFER_SMOKE_SKU_ID
            )
        )
        == 0
    )


def test_transfer_smoke_fixture_second_seed_does_not_duplicate_rows(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    result = seed_demo_dataset(db_session, "test-only-demo-password")

    assert result.data.created == 0
    assert result.data.unchanged == 16
    assert (
        db_session.scalar(
            select(func.count(Sku.id)).where(Sku.id == TRANSFER_SMOKE_SKU_ID)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(StockBalance.id)).where(
                StockBalance.sku_id == TRANSFER_SMOKE_SKU_ID
            )
        )
        == 2
    )


def test_demo_seed_preserves_completed_transfer_and_changed_stock(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, "test-only-demo-password")
    staff = db_session.scalar(
        select(User).where(User.login_identifier == "demo.warehouse_staff")
    )
    assert staff is not None

    transfer_result = confirm_transfer(
        db_session,
        TransferRequest.model_validate(
            {
                "sku_id": TRANSFER_SMOKE_SKU_ID,
                "source_location_id": DEMO_BACKROOM_ID,
                "destination_location_id": DEMO_SALES_SHELF_ID,
                "quantity": TRANSFER_SMOKE_QUANTITY,
            }
        ),
        Actor(staff.id, staff.login_identifier, Role.WAREHOUSE_STAFF),
        "demo-transfer-smoke-preservation-test",
    )
    transfer_id = transfer_result.response.transfer_id

    result = seed_demo_dataset(db_session, "test-only-demo-password")

    assert result.data.created == 0
    assert result.data.unchanged == 16
    transfer = db_session.get(Transfer, transfer_id)
    assert transfer is not None
    assert transfer.sku_id == TRANSFER_SMOKE_SKU_ID
    assert transfer.quantity == TRANSFER_SMOKE_QUANTITY
    assert transfer.source_location_id == DEMO_BACKROOM_ID
    assert transfer.destination_location_id == DEMO_SALES_SHELF_ID
    assert (
        db_session.get(StockBalance, TRANSFER_SMOKE_BACKROOM_STOCK_ID).quantity
        == TRANSFER_SMOKE_BACKROOM_QUANTITY - TRANSFER_SMOKE_QUANTITY
    )
    assert (
        db_session.get(StockBalance, TRANSFER_SMOKE_SALES_SHELF_STOCK_ID).quantity
        == TRANSFER_SMOKE_SALES_SHELF_QUANTITY + TRANSFER_SMOKE_QUANTITY
    )
    assert (
        db_session.scalar(
            select(func.count(Transfer.id)).where(
                Transfer.sku_id == TRANSFER_SMOKE_SKU_ID
            )
        )
        == 1
    )
