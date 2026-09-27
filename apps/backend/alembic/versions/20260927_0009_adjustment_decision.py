"""Add the approved US-ADJ-002 Manager decision evidence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0009"
down_revision: str | Sequence[str] | None = "20260927_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recreate_mode() -> str:
    return "always" if op.get_bind().dialect.name == "sqlite" else "auto"


def upgrade() -> None:
    with op.batch_alter_table("adjust_requests", recreate=_recreate_mode()) as batch_op:
        batch_op.add_column(sa.Column("decided_by_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("rejection_reason", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(sa.Column("applied_stock_before", sa.Integer()))
        batch_op.add_column(sa.Column("applied_stock_after", sa.Integer()))
        batch_op.add_column(
            sa.Column("decision_idempotency_key", sa.String(length=255))
        )
        batch_op.add_column(
            sa.Column("decision_request_fingerprint", sa.String(length=64))
        )
        batch_op.drop_constraint("ck_adjust_requests_status", type_="check")
        batch_op.create_check_constraint(
            "ck_adjust_requests_status",
            "status IN ('PENDING_MANAGER_DECISION', 'APPLIED', 'REJECTED')",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_decision_state",
            "(status = 'PENDING_MANAGER_DECISION' AND "
            "decided_by_user_id IS NULL AND decided_at IS NULL AND "
            "rejection_reason IS NULL AND applied_stock_before IS NULL AND "
            "applied_stock_after IS NULL AND decision_idempotency_key IS NULL AND "
            "decision_request_fingerprint IS NULL) OR "
            "(status = 'APPLIED' AND decided_by_user_id IS NOT NULL AND "
            "decided_at IS NOT NULL AND rejection_reason IS NULL AND "
            "applied_stock_before IS NOT NULL AND applied_stock_after IS NOT NULL AND "
            "decision_idempotency_key IS NOT NULL AND "
            "decision_request_fingerprint IS NOT NULL) OR "
            "(status = 'REJECTED' AND decided_by_user_id IS NOT NULL AND "
            "decided_at IS NOT NULL AND rejection_reason IS NOT NULL AND "
            "applied_stock_before IS NULL AND applied_stock_after IS NULL AND "
            "decision_idempotency_key IS NOT NULL AND "
            "decision_request_fingerprint IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_applied_before_nonnegative",
            "applied_stock_before IS NULL OR applied_stock_before >= 0",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_applied_after_nonnegative",
            "applied_stock_after IS NULL OR applied_stock_after >= 0",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_applied_stock_consistent",
            "status <> 'APPLIED' OR "
            "applied_stock_after = applied_stock_before + requested_change",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_rejection_reason_normalized",
            "rejection_reason IS NULL OR "
            "(length(rejection_reason) BETWEEN 1 AND 500 AND "
            "rejection_reason = trim(rejection_reason))",
        )
        batch_op.create_check_constraint(
            "ck_adjust_requests_decision_fingerprint_length",
            "decision_request_fingerprint IS NULL OR "
            "length(decision_request_fingerprint) = 64",
        )
        batch_op.create_foreign_key(
            "fk_adjust_requests_decided_by_user_id_users",
            "users",
            ["decided_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_adjust_requests_decision_idempotency_key",
            ["decision_idempotency_key"],
        )


def downgrade() -> None:
    terminal_count = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM adjust_requests "
            "WHERE status IN ('APPLIED', 'REJECTED')"
        )
    )
    if terminal_count:
        raise RuntimeError(
            "Cannot downgrade US-ADJ-002 while terminal Adjust requests exist"
        )

    with op.batch_alter_table("adjust_requests", recreate=_recreate_mode()) as batch_op:
        batch_op.drop_constraint(
            "uq_adjust_requests_decision_idempotency_key", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_adjust_requests_decided_by_user_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "ck_adjust_requests_decision_fingerprint_length", type_="check"
        )
        batch_op.drop_constraint(
            "ck_adjust_requests_rejection_reason_normalized", type_="check"
        )
        batch_op.drop_constraint(
            "ck_adjust_requests_applied_stock_consistent", type_="check"
        )
        batch_op.drop_constraint(
            "ck_adjust_requests_applied_after_nonnegative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_adjust_requests_applied_before_nonnegative", type_="check"
        )
        batch_op.drop_constraint("ck_adjust_requests_decision_state", type_="check")
        batch_op.drop_constraint("ck_adjust_requests_status", type_="check")
        batch_op.create_check_constraint(
            "ck_adjust_requests_status", "status = 'PENDING_MANAGER_DECISION'"
        )
        batch_op.drop_column("decision_request_fingerprint")
        batch_op.drop_column("decision_idempotency_key")
        batch_op.drop_column("applied_stock_after")
        batch_op.drop_column("applied_stock_before")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("decided_at")
        batch_op.drop_column("decided_by_user_id")
