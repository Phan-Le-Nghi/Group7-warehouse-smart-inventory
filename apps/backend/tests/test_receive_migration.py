from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from warehouse_api.config import get_settings


def alembic_config(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    return Config(root / "alembic.ini")


def test_receive_migration_preserves_legacy_row_and_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'legacy-migration.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, "20260919_0002")
    engine = create_engine(database_url)
    warehouse_id, sku_id, receive_id, line_id = (uuid4().hex for _ in range(4))
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO warehouses (id, code) VALUES (:id, 'LEGACY')"),
            {"id": warehouse_id},
        )
        connection.execute(
            text("INSERT INTO skus (id, code) VALUES (:id, 'LEGACY-SKU')"),
            {"id": sku_id},
        )
        connection.execute(
            text("INSERT INTO receives (id, warehouse_id) VALUES (:id, :warehouse_id)"),
            {"id": receive_id, "warehouse_id": warehouse_id},
        )
        connection.execute(
            text(
                "INSERT INTO receive_lines "
                "(id, receive_id, sku_id, actual_quantity) "
                "VALUES (:id, :receive_id, :sku_id, 16)"
            ),
            {"id": line_id, "receive_id": receive_id, "sku_id": sku_id},
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT expected_quantity, actual_quantity, quantity_discrepancy "
                "FROM receive_lines WHERE id = :id"
            ),
            {"id": line_id},
        ).one()
        assert row == (None, 16, None)
        receive_row = connection.execute(
            text(
                "SELECT expected_reference, document_reference, "
                "reference_match_status FROM receives WHERE id = :id"
            ),
            {"id": receive_id},
        ).one()
        assert receive_row == (None, None, None)

    command.downgrade(config, "20260919_0002")
    assert "expected_quantity" not in {
        column["name"] for column in inspect(engine).get_columns("receive_lines")
    }
    command.upgrade(config, "head")
    assert "expected_quantity" in {
        column["name"] for column in inspect(engine).get_columns("receive_lines")
    }
    engine.dispose()
    get_settings.cache_clear()


def test_receive_migration_refuses_to_downgrade_null_actual_quantity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'blocked-downgrade.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    warehouse_id, sku_id, receive_id, line_id = (uuid4().hex for _ in range(4))
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO warehouses (id, code) VALUES (:id, 'PREPARED')"),
            {"id": warehouse_id},
        )
        connection.execute(
            text("INSERT INTO skus (id, code) VALUES (:id, 'PREPARED-SKU')"),
            {"id": sku_id},
        )
        connection.execute(
            text(
                "INSERT INTO receives (id, warehouse_id, expected_reference) "
                "VALUES (:id, :warehouse_id, 'DELIVERY-001')"
            ),
            {"id": receive_id, "warehouse_id": warehouse_id},
        )
        connection.execute(
            text(
                "INSERT INTO receive_lines "
                "(id, receive_id, sku_id, expected_quantity, actual_quantity) "
                "VALUES (:id, :receive_id, :sku_id, 16, NULL)"
            ),
            {"id": line_id, "receive_id": receive_id, "sku_id": sku_id},
        )

    with pytest.raises(RuntimeError, match="actual_quantity IS NULL"):
        command.downgrade(config, "20260919_0002")

    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM receive_lines WHERE actual_quantity IS NULL")
            )
            == 1
        )
    engine.dispose()
    get_settings.cache_clear()
