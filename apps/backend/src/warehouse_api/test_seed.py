"""Reset documented browser fixtures in a dedicated test database only."""

import argparse
import json
from os import getenv
from uuid import UUID

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from warehouse_api.models import (
    InternalLocation,
    PutawayAllocation,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    Warehouse,
)

WAREHOUSE_ID = UUID("00000000-0000-0000-0000-000000000001")
SKU_ID = UUID("00000000-0000-0000-0000-000000000002")
RECEIVE_ID = UUID("00000000-0000-0000-0000-000000000003")
RECEIVE_LINE_ID = UUID("00000000-0000-0000-0000-000000000004")
BACKROOM_ID = UUID("00000000-0000-0000-0000-000000000005")
SALES_SHELF_ID = UUID("00000000-0000-0000-0000-000000000006")
RECEIVE_MATCH_ID = UUID("00000000-0000-0000-0000-000000000103")
RECEIVE_MATCH_LINE_ID = UUID("00000000-0000-0000-0000-000000000104")
RECEIVE_MATCH_SKU_ID = UUID("00000000-0000-0000-0000-000000000102")
RECEIVE_MISMATCH_ID = UUID("00000000-0000-0000-0000-000000000113")
RECEIVE_MISMATCH_LINE_ID = UUID("00000000-0000-0000-0000-000000000114")
RECEIVE_MISMATCH_SKU_ID = UUID("00000000-0000-0000-0000-000000000112")


def _reset_receive_fixtures(session: Session) -> None:
    warehouse = session.get(Warehouse, WAREHOUSE_ID)
    if warehouse is None:
        warehouse = Warehouse(id=WAREHOUSE_ID, code="MAIN")
        session.add(warehouse)
    for receive_id, line_id, sku_id, sku_code in (
        (
            RECEIVE_MATCH_ID,
            RECEIVE_MATCH_LINE_ID,
            RECEIVE_MATCH_SKU_ID,
            "REC-SKU-MATCH",
        ),
        (
            RECEIVE_MISMATCH_ID,
            RECEIVE_MISMATCH_LINE_ID,
            RECEIVE_MISMATCH_SKU_ID,
            "REC-SKU-MISMATCH",
        ),
    ):
        session.execute(
            delete(PutawayAllocation).where(
                PutawayAllocation.receive_line_id == line_id
            )
        )
        sku = session.get(Sku, sku_id)
        if sku is None:
            sku = Sku(id=sku_id, code=sku_code)
            session.add(sku)
        receive = session.get(Receive, receive_id)
        if receive is None:
            receive = Receive(id=receive_id, warehouse_id=WAREHOUSE_ID)
            session.add(receive)
        receive.expected_reference = "DELIVERY-001"
        receive.document_reference = None
        receive.reference_match_status = None
        receive.recorded_by_user_id = None
        receive.recorded_at = None
        receive.reference_reviewed_by_user_id = None
        receive.reference_reviewed_at = None
        line = session.get(ReceiveLine, line_id)
        if line is None:
            line = ReceiveLine(
                id=line_id,
                receive_id=receive_id,
                sku_id=sku_id,
            )
            session.add(line)
        line.expected_quantity = 16
        line.actual_quantity = None
        line.quantity_discrepancy = None
        balance = session.scalar(
            select(StockBalance).where(
                StockBalance.sku_id == sku_id,
                StockBalance.location_id == BACKROOM_ID,
            )
        )
        if balance is None:
            session.add(
                StockBalance(sku_id=sku_id, location_id=BACKROOM_ID, quantity=0)
            )
        else:
            balance.quantity = 0


def seed_test_fixture() -> None:
    test_database_url = getenv("TEST_DATABASE_URL")
    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is required for the test-only seed")

    engine = create_engine(test_database_url)
    with Session(engine) as session, session.begin():
        session.execute(
            delete(PutawayAllocation).where(
                PutawayAllocation.receive_line_id == RECEIVE_LINE_ID
            )
        )

        if session.get(Warehouse, WAREHOUSE_ID) is None:
            session.add(Warehouse(id=WAREHOUSE_ID, code="MAIN"))
        if session.get(Sku, SKU_ID) is None:
            session.add(Sku(id=SKU_ID, code="SKU-001"))
        if session.get(Receive, RECEIVE_ID) is None:
            session.add(Receive(id=RECEIVE_ID, warehouse_id=WAREHOUSE_ID))
        if session.get(ReceiveLine, RECEIVE_LINE_ID) is None:
            session.add(
                ReceiveLine(
                    id=RECEIVE_LINE_ID,
                    receive_id=RECEIVE_ID,
                    sku_id=SKU_ID,
                    actual_quantity=16,
                )
            )

        for location_id, code in (
            (BACKROOM_ID, "BACKROOM"),
            (SALES_SHELF_ID, "SALES_SHELF"),
        ):
            if session.get(InternalLocation, location_id) is None:
                session.add(
                    InternalLocation(
                        id=location_id, warehouse_id=WAREHOUSE_ID, code=code
                    )
                )
            balance = session.scalar(
                select(StockBalance).where(
                    StockBalance.sku_id == SKU_ID,
                    StockBalance.location_id == location_id,
                )
            )
            if balance is None:
                session.add(
                    StockBalance(sku_id=SKU_ID, location_id=location_id, quantity=0)
                )
            else:
                balance.quantity = 0
        _reset_receive_fixtures(session)
    engine.dispose()


def reset_receive_fixtures() -> None:
    test_database_url = getenv("TEST_DATABASE_URL")
    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is required for the test-only seed")
    engine = create_engine(test_database_url)
    with Session(engine) as session, session.begin():
        _reset_receive_fixtures(session)
    engine.dispose()


def receive_effect_snapshot(receive_id: UUID) -> dict[str, int]:
    test_database_url = getenv("TEST_DATABASE_URL")
    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is required for the test-only snapshot")
    engine = create_engine(test_database_url)
    with Session(engine) as session:
        line_ids = select(ReceiveLine.id).where(ReceiveLine.receive_id == receive_id)
        sku_ids = select(ReceiveLine.sku_id).where(ReceiveLine.receive_id == receive_id)
        result = {
            "stock_quantity": int(
                session.scalar(
                    select(func.coalesce(func.sum(StockBalance.quantity), 0)).where(
                        StockBalance.sku_id.in_(sku_ids)
                    )
                )
                or 0
            ),
            "putaway_count": int(
                session.scalar(
                    select(func.count(PutawayAllocation.id)).where(
                        PutawayAllocation.receive_line_id.in_(line_ids)
                    )
                )
                or 0
            ),
        }
    engine.dispose()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receive-only", action="store_true")
    parser.add_argument("--snapshot", type=UUID)
    arguments = parser.parse_args()
    if arguments.snapshot:
        print(json.dumps(receive_effect_snapshot(arguments.snapshot)))
    elif arguments.receive_only:
        reset_receive_fixtures()
        print("US-REC-001 test fixtures reset")
    else:
        seed_test_fixture()
        print(
            "Browser test fixtures ready: "
            f"putaway_receive_line_id={RECEIVE_LINE_ID}; "
            f"receive_id={RECEIVE_MATCH_ID}"
        )
