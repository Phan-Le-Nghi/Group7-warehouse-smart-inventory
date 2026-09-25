"""Create the approved US-AUD-001 Audit schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260926_0006"
down_revision: str | Sequence[str] | None = "20260925_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("audited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('SELECTED_PAIRS', 'WHOLE_WAREHOUSE')",
            name="ck_audit_sessions_scope_type",
        ),
        sa.CheckConstraint(
            "result IN ('MATCH', 'MISMATCH')",
            name="ck_audit_sessions_result",
        ),
        sa.CheckConstraint(
            "status IN ('MATCH_COMPLETED', 'MISMATCH_RECORDED')",
            name="ck_audit_sessions_status",
        ),
        sa.CheckConstraint(
            "(result = 'MATCH' AND status = 'MATCH_COMPLETED') OR "
            "(result = 'MISMATCH' AND status = 'MISMATCH_RECORDED')",
            name="ck_audit_sessions_result_status_consistent",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_audit_sessions_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["audited_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_audit_sessions_idempotency_key"
        ),
    )
    op.create_index(
        op.f("ix_audit_sessions_warehouse_id"),
        "audit_sessions",
        ["warehouse_id"],
    )
    op.create_index(
        op.f("ix_audit_sessions_audited_by_user_id"),
        "audit_sessions",
        ["audited_by_user_id"],
    )
    op.create_index(
        "ix_audit_sessions_warehouse_audited_at",
        "audit_sessions",
        ["warehouse_id", "audited_at"],
    )

    op.create_table(
        "audit_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_id", sa.Uuid(), nullable=False),
        sa.Column("sku_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("system_quantity", sa.Integer(), nullable=False),
        sa.Column("physical_quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_discrepancy", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "system_quantity >= 0",
            name="ck_audit_lines_system_quantity_nonnegative",
        ),
        sa.CheckConstraint(
            "physical_quantity >= 0",
            name="ck_audit_lines_physical_quantity_nonnegative",
        ),
        sa.CheckConstraint(
            "quantity_discrepancy = physical_quantity - system_quantity",
            name="ck_audit_lines_discrepancy_consistent",
        ),
        sa.CheckConstraint(
            "result IN ('MATCH', 'MISMATCH')",
            name="ck_audit_lines_result",
        ),
        sa.CheckConstraint(
            "(quantity_discrepancy = 0 AND result = 'MATCH') OR "
            "(quantity_discrepancy <> 0 AND result = 'MISMATCH')",
            name="ck_audit_lines_result_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["audit_id"], ["audit_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["location_id"], ["internal_locations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audit_id",
            "sku_id",
            "location_id",
            name="uq_audit_lines_audit_sku_location",
        ),
    )
    op.create_index(op.f("ix_audit_lines_sku_id"), "audit_lines", ["sku_id"])
    op.create_index(op.f("ix_audit_lines_location_id"), "audit_lines", ["location_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_lines_location_id"), table_name="audit_lines")
    op.drop_index(op.f("ix_audit_lines_sku_id"), table_name="audit_lines")
    op.drop_table("audit_lines")
    op.drop_index("ix_audit_sessions_warehouse_audited_at", table_name="audit_sessions")
    op.drop_index(
        op.f("ix_audit_sessions_audited_by_user_id"),
        table_name="audit_sessions",
    )
    op.drop_index(op.f("ix_audit_sessions_warehouse_id"), table_name="audit_sessions")
    op.drop_table("audit_sessions")
