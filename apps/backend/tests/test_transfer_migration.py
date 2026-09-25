from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from warehouse_api.config import get_settings


def test_transfer_migration_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'transfer-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    config = Config(root / "alembic.ini")
    command.upgrade(config, "20260922_0004")
    engine = create_engine(database_url)
    legacy_tables = set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) - legacy_tables == {"transfers"}
    assert {column["name"] for column in inspector.get_columns("transfers")} == {
        "id",
        "warehouse_id",
        "sku_id",
        "source_location_id",
        "destination_location_id",
        "quantity",
        "transferred_by_user_id",
        "transferred_at",
        "idempotency_key",
        "request_fingerprint",
    }
    assert {item["name"] for item in inspector.get_check_constraints("transfers")} == {
        "ck_transfers_different_locations",
        "ck_transfers_quantity_positive",
    }
    assert {item["name"] for item in inspector.get_unique_constraints("transfers")} == {
        "uq_transfers_idempotency_key"
    }

    command.downgrade(config, "20260922_0004")
    assert set(inspect(engine).get_table_names()) == legacy_tables
    command.upgrade(config, "head")
    assert "transfers" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
