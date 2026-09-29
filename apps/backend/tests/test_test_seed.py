from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_api.models import (
    InternalLocation,
    Sku,
    StockBalance,
    Transfer,
    Warehouse,
)
from warehouse_api.test_seed import (
    AUDIT_SKU_ID,
    BACKROOM_ID,
    SALES_SHELF_ID,
    WAREHOUSE_ID,
    _get_test_database_url,
    _reset_audit_fixture,
)


def test_runtime_test_seed_requires_explicit_test_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://example.invalid/warehouse"
    )

    with pytest.raises(RuntimeError, match="APP_ENV=test"):
        _get_test_database_url()


def test_audit_reset_removes_its_transfer_and_restores_balances(
    db_session: Session,
    user_factory,
) -> None:
    actor = user_factory()
    other_sku_id = UUID("00000000-0000-0000-0000-000000000503")
    db_session.add(Warehouse(id=WAREHOUSE_ID, code="MAIN"))
    db_session.flush()
    db_session.add_all(
        [
            InternalLocation(
                id=BACKROOM_ID,
                warehouse_id=WAREHOUSE_ID,
                code="BACKROOM",
            ),
            InternalLocation(
                id=SALES_SHELF_ID,
                warehouse_id=WAREHOUSE_ID,
                code="SALES_SHELF",
            ),
            Sku(id=AUDIT_SKU_ID, code="AUDIT-SKU-MISSING-BALANCE"),
            Sku(id=other_sku_id, code="UNRELATED-SKU"),
        ]
    )
    db_session.flush()
    for sku_id, key in (
        (AUDIT_SKU_ID, "adjustment-stale-approved-transfer"),
        (other_sku_id, "unrelated-transfer"),
    ):
        db_session.add(
            Transfer(
                warehouse_id=WAREHOUSE_ID,
                sku_id=sku_id,
                source_location_id=BACKROOM_ID,
                destination_location_id=SALES_SHELF_ID,
                quantity=1,
                transferred_by_user_id=actor.id,
                transferred_at=datetime.now(UTC),
                idempotency_key=key,
                request_fingerprint="a" * 64,
            )
        )
    db_session.add_all(
        [
            StockBalance(
                sku_id=AUDIT_SKU_ID,
                location_id=BACKROOM_ID,
                quantity=6,
            ),
            StockBalance(
                sku_id=AUDIT_SKU_ID,
                location_id=SALES_SHELF_ID,
                quantity=1,
            ),
        ]
    )
    db_session.flush()

    _reset_audit_fixture(db_session)
    db_session.flush()

    assert list(db_session.scalars(select(Transfer.sku_id))) == [other_sku_id]
    balances = dict(
        db_session.execute(
            select(StockBalance.location_id, StockBalance.quantity).where(
                StockBalance.sku_id == AUDIT_SKU_ID
            )
        ).all()
    )
    assert balances == {BACKROOM_ID: 7}
