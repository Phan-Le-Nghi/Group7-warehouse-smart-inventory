from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from warehouse_api.config import get_settings


def test_audit_migration_cycles_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'audit-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    config = Config(root / "alembic.ini")
    command.upgrade(config, "20260925_0005")
    engine = create_engine(database_url)
    legacy_tables = set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) - legacy_tables == {
        "audit_sessions",
        "audit_lines",
    }
    assert {column["name"] for column in inspector.get_columns("audit_sessions")} == {
        "id",
        "warehouse_id",
        "scope_type",
        "result",
        "status",
        "audited_by_user_id",
        "audited_at",
        "idempotency_key",
        "request_fingerprint",
    }
    assert {column["name"] for column in inspector.get_columns("audit_lines")} == {
        "id",
        "audit_id",
        "sku_id",
        "location_id",
        "system_quantity",
        "physical_quantity",
        "quantity_discrepancy",
        "result",
    }
    assert {
        item["name"] for item in inspector.get_check_constraints("audit_sessions")
    } == {
        "ck_audit_sessions_fingerprint_length",
        "ck_audit_sessions_result",
        "ck_audit_sessions_result_status_consistent",
        "ck_audit_sessions_scope_type",
        "ck_audit_sessions_status",
    }
    assert {
        item["name"] for item in inspector.get_check_constraints("audit_lines")
    } == {
        "ck_audit_lines_discrepancy_consistent",
        "ck_audit_lines_physical_quantity_nonnegative",
        "ck_audit_lines_result",
        "ck_audit_lines_result_consistent",
        "ck_audit_lines_system_quantity_nonnegative",
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("audit_sessions")
    } == {"uq_audit_sessions_idempotency_key"}
    assert {
        item["name"] for item in inspector.get_unique_constraints("audit_lines")
    } == {"uq_audit_lines_audit_sku_location"}
    assert {item["name"] for item in inspector.get_foreign_keys("audit_lines")} == {
        None
    }
    assert {
        item["referred_table"] for item in inspector.get_foreign_keys("audit_lines")
    } == {
        "audit_sessions",
        "internal_locations",
        "skus",
    }
    assert {item["name"] for item in inspector.get_indexes("audit_sessions")} == {
        "ix_audit_sessions_audited_by_user_id",
        "ix_audit_sessions_warehouse_audited_at",
        "ix_audit_sessions_warehouse_id",
    }

    command.downgrade(config, "20260925_0005")
    assert set(inspect(engine).get_table_names()) == legacy_tables
    command.upgrade(config, "head")
    assert {"audit_sessions", "audit_lines"}.issubset(inspect(engine).get_table_names())
    engine.dispose()
    get_settings.cache_clear()
