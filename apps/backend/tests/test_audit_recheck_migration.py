from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from warehouse_api.config import get_settings


def test_audit_recheck_migration_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'audit-recheck-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    config = Config(root / "alembic.ini")
    command.upgrade(config, "20260926_0006")
    engine = create_engine(database_url)
    legacy_tables = set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) - legacy_tables == {"audit_rechecks"}
    assert {column["name"] for column in inspector.get_columns("audit_rechecks")} == {
        "id",
        "audit_line_id",
        "recheck_system_quantity",
        "recheck_physical_quantity",
        "recheck_quantity_discrepancy",
        "result",
        "performed_by_user_id",
        "performed_at",
        "idempotency_key",
        "request_fingerprint",
    }
    assert {
        item["name"] for item in inspector.get_check_constraints("audit_rechecks")
    } == {
        "ck_audit_rechecks_discrepancy_consistent",
        "ck_audit_rechecks_fingerprint_length",
        "ck_audit_rechecks_physical_quantity_range",
        "ck_audit_rechecks_result",
        "ck_audit_rechecks_result_consistent",
        "ck_audit_rechecks_system_quantity_nonnegative",
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("audit_rechecks")
    } == {
        "uq_audit_rechecks_audit_line_id",
        "uq_audit_rechecks_idempotency_key",
    }
    assert {
        item["referred_table"] for item in inspector.get_foreign_keys("audit_rechecks")
    } == {"audit_lines", "users"}
    assert {
        item["options"].get("ondelete")
        for item in inspector.get_foreign_keys("audit_rechecks")
    } == {"RESTRICT"}
    assert {item["name"] for item in inspector.get_indexes("audit_rechecks")} == {
        "ix_audit_rechecks_performed_by_user_id"
    }

    command.downgrade(config, "20260926_0006")
    assert set(inspect(engine).get_table_names()) == legacy_tables
    command.upgrade(config, "head")
    assert "audit_rechecks" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
