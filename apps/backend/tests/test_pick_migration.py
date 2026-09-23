from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from warehouse_api.config import get_settings


def alembic_config(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    return Config(root / "alembic.ini")


def test_pick_migration_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'pick-migration.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, "20260922_0003")
    engine = create_engine(database_url)
    legacy_tables = set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    upgraded_tables = set(inspect(engine).get_table_names())
    assert upgraded_tables - legacy_tables == {"pick_requests", "pick_allocations"}
    request_columns = {
        column["name"] for column in inspect(engine).get_columns("pick_requests")
    }
    assert "picked_quantity" not in request_columns
    assert {
        "id",
        "warehouse_id",
        "sku_id",
        "requested_quantity",
        "outcome",
        "confirmed_by_user_id",
        "confirmed_at",
    } == request_columns

    command.downgrade(config, "20260922_0003")
    assert set(inspect(engine).get_table_names()) == legacy_tables
    command.upgrade(config, "head")
    assert {"pick_requests", "pick_allocations"}.issubset(
        inspect(engine).get_table_names()
    )
    engine.dispose()
    get_settings.cache_clear()
