from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_api.db import session_scope
from warehouse_api.demo_seed import SeedResult, seed_demo_users
from warehouse_api.models import (
    InternalLocation,
    PickRequest,
    Receive,
    ReceiveLine,
    Sku,
    StockBalance,
    User,
    Warehouse,
)

DEMO_WAREHOUSE_ID = UUID("bf2a6045-f376-5f56-b0ca-2e13695d26ca")
DEMO_BACKROOM_ID = UUID("1d89fe90-31a9-5044-b340-6a646ed770b7")
DEMO_SALES_SHELF_ID = UUID("236456ff-fd86-5df1-9829-a781892dacfe")
DEMO_SKU_ID = UUID("ba633e2e-57f2-5011-b710-1614ef29f629")
DEMO_RECEIVE_ID = UUID("435cd10b-4cfe-53a4-bbcf-f63735a8292e")
DEMO_RECEIVE_LINE_ID = UUID("daf594b9-9c1e-51ec-adf0-0055cb3a8ff3")
RECEIVE_SMOKE_SKU_ID = UUID("a759b6c3-0b45-5914-9a41-f95add39a816")
RECEIVE_SMOKE_ID = UUID("e34f5e8e-4b3a-55a1-9485-d411a1ede3a8")
RECEIVE_SMOKE_LINE_ID = UUID("e60fab3e-b0b4-549c-a53d-289e6456c2d4")
PICK_SMOKE_ID = UUID("d88066ff-46b8-5722-ba29-b11cfa01816d")
PICK_SMOKE_SKU_ID = UUID("82a38c49-10fb-5168-bdcb-0359f606ee3f")
PICK_SMOKE_BACKROOM_STOCK_ID = UUID("8b37bd4e-6a61-59fb-8809-5ac87d9f4128")
PICK_SMOKE_SALES_SHELF_STOCK_ID = UUID("c0f35328-197b-5494-932e-5b7f619e3e27")
TRANSFER_SMOKE_SKU_ID = UUID("e3008bde-52db-5009-86d1-9dc3ec7cddcd")
TRANSFER_SMOKE_BACKROOM_STOCK_ID = UUID("28f91941-c1e2-593d-a6f7-82b3535a8551")
TRANSFER_SMOKE_SALES_SHELF_STOCK_ID = UUID("294299a3-4a25-5ba7-bd7d-ca69dcb6fe10")

DEMO_RECORDED_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
DEMO_REFERENCE = "DEMO-RECEIVE-001"
DEMO_QUANTITY = 16
RECEIVE_SMOKE_REFERENCE = "DEMO-RECEIVE-SMOKE-001"
RECEIVE_SMOKE_QUANTITY = 12
PICK_SMOKE_REQUESTED_QUANTITY = 10
PICK_SMOKE_BACKROOM_QUANTITY = 6
PICK_SMOKE_SALES_SHELF_QUANTITY = 4
TRANSFER_SMOKE_BACKROOM_QUANTITY = 12
TRANSFER_SMOKE_SALES_SHELF_QUANTITY = 6
TRANSFER_SMOKE_QUANTITY = 4


@dataclass(frozen=True, slots=True)
class DemoDataSeedResult:
    created: int = 0
    unchanged: int = 0


@dataclass(frozen=True, slots=True)
class DemoDatasetSeedResult:
    users: SeedResult
    data: DemoDataSeedResult


def _ensure_not_production() -> None:
    if getenv("APP_ENV", "development").strip().lower() == "production":
        raise RuntimeError("Demo data seed is disabled when APP_ENV=production")


def _normalized_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, datetime) and isinstance(expected, datetime):
        return _normalized_datetime(actual) == _normalized_datetime(expected)
    return actual == expected


def _ensure_row(
    session: Session,
    model: type,
    row_id: UUID,
    values: dict[str, object],
    label: str,
    natural_key_clause=None,
    preserved_fields: frozenset[str] = frozenset(),
) -> bool:
    by_id = session.get(model, row_id)
    by_natural_key = (
        session.scalar(select(model).where(natural_key_clause))
        if natural_key_clause is not None
        else None
    )
    if by_id is not None and by_natural_key is not None and by_id is not by_natural_key:
        raise RuntimeError(
            f"Demo seed conflict for {label}: deterministic ID and natural key "
            "refer to different rows"
        )

    row = by_id or by_natural_key
    if row is None:
        session.add(model(id=row_id, **values))
        session.flush()
        return True
    if row.id != row_id:
        raise RuntimeError(
            f"Demo seed conflict for {label}: natural key already uses another ID"
        )

    conflicts = [
        field
        for field, expected in values.items()
        if field not in preserved_fields
        if not _values_match(getattr(row, field), expected)
    ]
    if conflicts:
        joined = ", ".join(sorted(conflicts))
        raise RuntimeError(
            f"Demo seed conflict for {label}: existing fields differ: {joined}"
        )
    return False


def seed_demo_data(session: Session) -> DemoDataSeedResult:
    _ensure_not_production()
    staff = session.scalar(
        select(User).where(User.login_identifier == "demo.warehouse_staff")
    )
    if staff is None or staff.role != "WAREHOUSE_STAFF" or not staff.is_active:
        raise RuntimeError("Active demo Warehouse Staff user is required")

    created = 0
    created += _ensure_row(
        session,
        Warehouse,
        DEMO_WAREHOUSE_ID,
        {"code": "MAIN"},
        "Warehouse MAIN",
        Warehouse.code == "MAIN",
    )
    created += _ensure_row(
        session,
        InternalLocation,
        DEMO_BACKROOM_ID,
        {"warehouse_id": DEMO_WAREHOUSE_ID, "code": "BACKROOM"},
        "MAIN/BACKROOM",
        (InternalLocation.warehouse_id == DEMO_WAREHOUSE_ID)
        & (InternalLocation.code == "BACKROOM"),
    )
    created += _ensure_row(
        session,
        InternalLocation,
        DEMO_SALES_SHELF_ID,
        {"warehouse_id": DEMO_WAREHOUSE_ID, "code": "SALES_SHELF"},
        "MAIN/SALES_SHELF",
        (InternalLocation.warehouse_id == DEMO_WAREHOUSE_ID)
        & (InternalLocation.code == "SALES_SHELF"),
    )
    created += _ensure_row(
        session,
        Sku,
        DEMO_SKU_ID,
        {"code": "DEMO-SKU-001"},
        "SKU DEMO-SKU-001",
        Sku.code == "DEMO-SKU-001",
    )
    created += _ensure_row(
        session,
        Sku,
        RECEIVE_SMOKE_SKU_ID,
        {"code": "DEMO-SKU-RECEIVE-SMOKE-001"},
        "SKU DEMO-SKU-RECEIVE-SMOKE-001",
        Sku.code == "DEMO-SKU-RECEIVE-SMOKE-001",
    )
    created += _ensure_row(
        session,
        Sku,
        PICK_SMOKE_SKU_ID,
        {"code": "DEMO-SKU-PICK-SMOKE-001"},
        "SKU DEMO-SKU-PICK-SMOKE-001",
        Sku.code == "DEMO-SKU-PICK-SMOKE-001",
    )
    created += _ensure_row(
        session,
        Sku,
        TRANSFER_SMOKE_SKU_ID,
        {"code": "DEMO-SKU-TRANSFER-SMOKE-001"},
        "SKU DEMO-SKU-TRANSFER-SMOKE-001",
        Sku.code == "DEMO-SKU-TRANSFER-SMOKE-001",
    )
    created += _ensure_row(
        session,
        Receive,
        DEMO_RECEIVE_ID,
        {
            "warehouse_id": DEMO_WAREHOUSE_ID,
            "expected_reference": DEMO_REFERENCE,
            "document_reference": DEMO_REFERENCE,
            "reference_match_status": "REFERENCE_MATCH",
            "recorded_by_user_id": staff.id,
            "recorded_at": DEMO_RECORDED_AT,
            "reference_reviewed_by_user_id": None,
            "reference_reviewed_at": None,
        },
        "Receive DEMO-RECEIVE-001",
    )
    created += _ensure_row(
        session,
        ReceiveLine,
        DEMO_RECEIVE_LINE_ID,
        {
            "receive_id": DEMO_RECEIVE_ID,
            "sku_id": DEMO_SKU_ID,
            "expected_quantity": DEMO_QUANTITY,
            "actual_quantity": DEMO_QUANTITY,
            "quantity_discrepancy": 0,
        },
        "Receive line DEMO-RECEIVE-001/DEMO-SKU-001",
    )
    # Only expected context is seed-owned for the smoke Receive. Recording fields
    # are intentionally omitted so a later seed run preserves real user input.
    created += _ensure_row(
        session,
        Receive,
        RECEIVE_SMOKE_ID,
        {
            "warehouse_id": DEMO_WAREHOUSE_ID,
            "expected_reference": RECEIVE_SMOKE_REFERENCE,
        },
        "Receive DEMO-RECEIVE-SMOKE-001",
    )
    created += _ensure_row(
        session,
        ReceiveLine,
        RECEIVE_SMOKE_LINE_ID,
        {
            "receive_id": RECEIVE_SMOKE_ID,
            "sku_id": RECEIVE_SMOKE_SKU_ID,
            "expected_quantity": RECEIVE_SMOKE_QUANTITY,
        },
        "Receive line DEMO-RECEIVE-SMOKE-001/DEMO-SKU-RECEIVE-SMOKE-001",
    )
    # Confirmation fields and stock quantities become user-owned operational
    # state. They are initial values only and must never be reset by a rerun.
    created += _ensure_row(
        session,
        PickRequest,
        PICK_SMOKE_ID,
        {
            "warehouse_id": DEMO_WAREHOUSE_ID,
            "sku_id": PICK_SMOKE_SKU_ID,
            "requested_quantity": PICK_SMOKE_REQUESTED_QUANTITY,
            "outcome": None,
            "confirmed_by_user_id": None,
            "confirmed_at": None,
        },
        "Pick DEMO-PICK-SMOKE-001",
        preserved_fields=frozenset({"outcome", "confirmed_by_user_id", "confirmed_at"}),
    )
    created += _ensure_row(
        session,
        StockBalance,
        PICK_SMOKE_BACKROOM_STOCK_ID,
        {
            "sku_id": PICK_SMOKE_SKU_ID,
            "location_id": DEMO_BACKROOM_ID,
            "quantity": PICK_SMOKE_BACKROOM_QUANTITY,
        },
        "Pick smoke stock MAIN/BACKROOM",
        (StockBalance.sku_id == PICK_SMOKE_SKU_ID)
        & (StockBalance.location_id == DEMO_BACKROOM_ID),
        preserved_fields=frozenset({"quantity"}),
    )
    created += _ensure_row(
        session,
        StockBalance,
        PICK_SMOKE_SALES_SHELF_STOCK_ID,
        {
            "sku_id": PICK_SMOKE_SKU_ID,
            "location_id": DEMO_SALES_SHELF_ID,
            "quantity": PICK_SMOKE_SALES_SHELF_QUANTITY,
        },
        "Pick smoke stock MAIN/SALES_SHELF",
        (StockBalance.sku_id == PICK_SMOKE_SKU_ID)
        & (StockBalance.location_id == DEMO_SALES_SHELF_ID),
        preserved_fields=frozenset({"quantity"}),
    )
    # Transfer stock is staging state only. Once a real Transfer changes these
    # quantities, subsequent seed runs must preserve that operational state.
    created += _ensure_row(
        session,
        StockBalance,
        TRANSFER_SMOKE_BACKROOM_STOCK_ID,
        {
            "sku_id": TRANSFER_SMOKE_SKU_ID,
            "location_id": DEMO_BACKROOM_ID,
            "quantity": TRANSFER_SMOKE_BACKROOM_QUANTITY,
        },
        "Transfer smoke stock MAIN/BACKROOM",
        (StockBalance.sku_id == TRANSFER_SMOKE_SKU_ID)
        & (StockBalance.location_id == DEMO_BACKROOM_ID),
        preserved_fields=frozenset({"quantity"}),
    )
    created += _ensure_row(
        session,
        StockBalance,
        TRANSFER_SMOKE_SALES_SHELF_STOCK_ID,
        {
            "sku_id": TRANSFER_SMOKE_SKU_ID,
            "location_id": DEMO_SALES_SHELF_ID,
            "quantity": TRANSFER_SMOKE_SALES_SHELF_QUANTITY,
        },
        "Transfer smoke stock MAIN/SALES_SHELF",
        (StockBalance.sku_id == TRANSFER_SMOKE_SKU_ID)
        & (StockBalance.location_id == DEMO_SALES_SHELF_ID),
        preserved_fields=frozenset({"quantity"}),
    )
    session.flush()
    return DemoDataSeedResult(created=created, unchanged=16 - created)


def seed_demo_dataset(session: Session, password: str) -> DemoDatasetSeedResult:
    users = seed_demo_users(session, password)
    data = seed_demo_data(session)
    return DemoDatasetSeedResult(users=users, data=data)


def main() -> None:
    _ensure_not_production()
    password = getenv("DEMO_USER_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_USER_PASSWORD is required")

    with session_scope() as session:
        result = seed_demo_dataset(session, password)
    print(
        "Demo dataset ready: "
        f"users_created={result.users.created}, "
        f"users_updated={result.users.updated}, "
        f"users_unchanged={result.users.unchanged}, "
        f"data_created={result.data.created}, "
        f"data_unchanged={result.data.unchanged}; "
        f"receive_id={DEMO_RECEIVE_ID}; "
        f"receive_line_id={DEMO_RECEIVE_LINE_ID}; "
        f"receive_smoke_id={RECEIVE_SMOKE_ID}; "
        f"receive_smoke_line_id={RECEIVE_SMOKE_LINE_ID}; "
        f"pick_smoke_id={PICK_SMOKE_ID}; "
        f"transfer_smoke_sku_id={TRANSFER_SMOKE_SKU_ID}"
    )


if __name__ == "__main__":
    main()
