from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from warehouse_api.config import get_settings


def test_adjustment_migration_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'adjustment-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    config = Config(root / "alembic.ini")
    command.upgrade(config, "20260926_0007")
    engine = create_engine(database_url)
    legacy_tables = set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) - legacy_tables == {"adjust_requests"}
    assert {column["name"] for column in inspector.get_columns("adjust_requests")} == {
        "id",
        "audit_recheck_id",
        "sku_id",
        "location_id",
        "recheck_system_quantity_snapshot",
        "recheck_physical_quantity_snapshot",
        "requested_change",
        "reason",
        "status",
        "requested_by_user_id",
        "requested_at",
        "idempotency_key",
        "request_fingerprint",
    }
    assert {
        item["name"] for item in inspector.get_check_constraints("adjust_requests")
    } == {
        "ck_adjust_requests_change_consistent",
        "ck_adjust_requests_change_nonzero",
        "ck_adjust_requests_fingerprint_length",
        "ck_adjust_requests_physical_snapshot_nonnegative",
        "ck_adjust_requests_reason_length",
        "ck_adjust_requests_reason_trimmed",
        "ck_adjust_requests_status",
        "ck_adjust_requests_system_snapshot_nonnegative",
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("adjust_requests")
    } == {
        "uq_adjust_requests_audit_recheck_id",
        "uq_adjust_requests_idempotency_key",
    }
    assert {
        item["referred_table"] for item in inspector.get_foreign_keys("adjust_requests")
    } == {"audit_rechecks", "skus", "internal_locations", "users"}
    assert {
        item["options"].get("ondelete")
        for item in inspector.get_foreign_keys("adjust_requests")
    } == {"RESTRICT"}
    assert {item["name"] for item in inspector.get_indexes("adjust_requests")} == {
        "ix_adjust_requests_requested_by_user_id"
    }

    command.downgrade(config, "20260926_0007")
    assert set(inspect(engine).get_table_names()) == legacy_tables
    command.upgrade(config, "head")
    assert "adjust_requests" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
