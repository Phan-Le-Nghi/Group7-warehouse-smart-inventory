from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

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
        "decided_by_user_id",
        "decided_at",
        "rejection_reason",
        "applied_stock_before",
        "applied_stock_after",
        "decision_idempotency_key",
        "decision_request_fingerprint",
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
        "ck_adjust_requests_decision_state",
        "ck_adjust_requests_applied_before_nonnegative",
        "ck_adjust_requests_applied_after_nonnegative",
        "ck_adjust_requests_applied_stock_consistent",
        "ck_adjust_requests_rejection_reason_normalized",
        "ck_adjust_requests_decision_fingerprint_length",
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("adjust_requests")
    } == {
        "uq_adjust_requests_audit_recheck_id",
        "uq_adjust_requests_idempotency_key",
        "uq_adjust_requests_decision_idempotency_key",
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


def test_adjustment_migration_refuses_terminal_row_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'terminal-adjustment.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[1]
    config = Config(root / "alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    value = "0" * 32
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO adjust_requests ("
                "id, audit_recheck_id, sku_id, location_id, "
                "recheck_system_quantity_snapshot, "
                "recheck_physical_quantity_snapshot, requested_change, reason, "
                "status, requested_by_user_id, requested_at, idempotency_key, "
                "request_fingerprint, decided_by_user_id, decided_at, "
                "applied_stock_before, applied_stock_after, "
                "decision_idempotency_key, decision_request_fingerprint"
                ") VALUES ("
                ":id, :source, :sku, :location, 10, 8, -2, 'reason', "
                "'APPLIED', :requester, CURRENT_TIMESTAMP, 'create-key', :fp, "
                ":decider, CURRENT_TIMESTAMP, 10, 8, 'decision-key', :dfp)"
            ),
            {
                "id": "1" * 32,
                "source": "2" * 32,
                "sku": "3" * 32,
                "location": "4" * 32,
                "requester": "5" * 32,
                "decider": "6" * 32,
                "fp": value * 2,
                "dfp": "d" * 64,
            },
        )
    with pytest.raises(RuntimeError, match="terminal Adjust requests"):
        command.downgrade(config, "20260927_0008")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM adjust_requests"))
    command.downgrade(config, "20260927_0008")
    command.upgrade(config, "head")
    engine.dispose()
    get_settings.cache_clear()
