"""Create the approved US-ADJ-001 Adjust request schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0008"
down_revision: str | Sequence[str] | None = "20260926_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adjust_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_recheck_id", sa.Uuid(), nullable=False),
        sa.Column("sku_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("recheck_system_quantity_snapshot", sa.Integer(), nullable=False),
        sa.Column("recheck_physical_quantity_snapshot", sa.Integer(), nullable=False),
        sa.Column("requested_change", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "recheck_system_quantity_snapshot >= 0",
            name="ck_adjust_requests_system_snapshot_nonnegative",
        ),
        sa.CheckConstraint(
            "recheck_physical_quantity_snapshot >= 0",
            name="ck_adjust_requests_physical_snapshot_nonnegative",
        ),
        sa.CheckConstraint(
            "requested_change = recheck_physical_quantity_snapshot - "
            "recheck_system_quantity_snapshot",
            name="ck_adjust_requests_change_consistent",
        ),
        sa.CheckConstraint(
            "requested_change <> 0",
            name="ck_adjust_requests_change_nonzero",
        ),
        sa.CheckConstraint(
            "length(reason) BETWEEN 1 AND 500",
            name="ck_adjust_requests_reason_length",
        ),
        sa.CheckConstraint(
            "reason = trim(reason)",
            name="ck_adjust_requests_reason_trimmed",
        ),
        sa.CheckConstraint(
            "status = 'PENDING_MANAGER_DECISION'",
            name="ck_adjust_requests_status",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_adjust_requests_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["audit_recheck_id"], ["audit_rechecks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["location_id"], ["internal_locations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audit_recheck_id", name="uq_adjust_requests_audit_recheck_id"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_adjust_requests_idempotency_key"
        ),
    )
    op.create_index(
        op.f("ix_adjust_requests_requested_by_user_id"),
        "adjust_requests",
        ["requested_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_adjust_requests_requested_by_user_id"),
        table_name="adjust_requests",
    )
    op.drop_table("adjust_requests")
