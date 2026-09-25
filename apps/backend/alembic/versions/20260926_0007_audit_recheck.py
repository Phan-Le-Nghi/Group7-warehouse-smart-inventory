"""Create the approved US-AUD-002 Audit recheck schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260926_0007"
down_revision: str | Sequence[str] | None = "20260926_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_rechecks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_line_id", sa.Uuid(), nullable=False),
        sa.Column("recheck_system_quantity", sa.Integer(), nullable=False),
        sa.Column("recheck_physical_quantity", sa.Integer(), nullable=False),
        sa.Column("recheck_quantity_discrepancy", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("performed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "recheck_system_quantity >= 0",
            name="ck_audit_rechecks_system_quantity_nonnegative",
        ),
        sa.CheckConstraint(
            "recheck_physical_quantity >= 0 AND "
            "recheck_physical_quantity <= 2147483647",
            name="ck_audit_rechecks_physical_quantity_range",
        ),
        sa.CheckConstraint(
            "recheck_quantity_discrepancy = "
            "recheck_physical_quantity - recheck_system_quantity",
            name="ck_audit_rechecks_discrepancy_consistent",
        ),
        sa.CheckConstraint(
            "result IN ('MATCH', 'MISMATCH')",
            name="ck_audit_rechecks_result",
        ),
        sa.CheckConstraint(
            "(recheck_quantity_discrepancy = 0 AND result = 'MATCH') OR "
            "(recheck_quantity_discrepancy <> 0 AND result = 'MISMATCH')",
            name="ck_audit_rechecks_result_consistent",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_audit_rechecks_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["audit_line_id"], ["audit_lines.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["performed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_line_id", name="uq_audit_rechecks_audit_line_id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_audit_rechecks_idempotency_key"
        ),
    )
    op.create_index(
        op.f("ix_audit_rechecks_performed_by_user_id"),
        "audit_rechecks",
        ["performed_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audit_rechecks_performed_by_user_id"),
        table_name="audit_rechecks",
    )
    op.drop_table("audit_rechecks")
