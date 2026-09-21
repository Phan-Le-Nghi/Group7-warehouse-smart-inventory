"""Add the approved US-REC-001 recording context."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0003"
down_revision: str | Sequence[str] | None = "20260919_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("receives") as batch_op:
        batch_op.add_column(
            sa.Column("expected_reference", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("document_reference", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("reference_match_status", sa.String(length=24), nullable=True)
        )
        batch_op.add_column(sa.Column("recorded_by_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("reference_reviewed_by_user_id", sa.Uuid(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "reference_reviewed_at", sa.DateTime(timezone=True), nullable=True
            )
        )
        batch_op.create_foreign_key(
            "fk_receives_recorded_by_user_id_users",
            "users",
            ["recorded_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_receives_reference_reviewed_by_user_id_users",
            "users",
            ["reference_reviewed_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_receives_expected_reference_nonempty",
            "expected_reference IS NULL OR length(trim(expected_reference)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_receives_document_reference_nonempty",
            "document_reference IS NULL OR length(trim(document_reference)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_receives_reference_match_status",
            "reference_match_status IS NULL OR "
            "reference_match_status IN ('REFERENCE_MATCH', 'REFERENCE_MISMATCH')",
        )
        batch_op.create_check_constraint(
            "ck_receives_reference_review_pair",
            "(reference_reviewed_by_user_id IS NULL AND "
            "reference_reviewed_at IS NULL) OR "
            "(reference_reviewed_by_user_id IS NOT NULL AND "
            "reference_reviewed_at IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_receives_reference_review_mismatch",
            "reference_reviewed_by_user_id IS NULL OR "
            "reference_match_status = 'REFERENCE_MISMATCH'",
        )

    op.create_index(
        op.f("ix_receives_recorded_by_user_id"),
        "receives",
        ["recorded_by_user_id"],
    )
    op.create_index(
        op.f("ix_receives_reference_reviewed_by_user_id"),
        "receives",
        ["reference_reviewed_by_user_id"],
    )

    with op.batch_alter_table("receive_lines") as batch_op:
        batch_op.add_column(sa.Column("expected_quantity", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("quantity_discrepancy", sa.Integer(), nullable=True)
        )
        batch_op.alter_column(
            "actual_quantity", existing_type=sa.Integer(), nullable=True
        )
        batch_op.drop_constraint("ck_receive_line_actual_nonnegative", type_="check")
        batch_op.create_check_constraint(
            "ck_receive_line_actual_nonnegative",
            "actual_quantity IS NULL OR actual_quantity >= 0",
        )
        batch_op.create_check_constraint(
            "ck_receive_line_expected_nonnegative",
            "expected_quantity IS NULL OR expected_quantity >= 0",
        )
        batch_op.create_check_constraint(
            "ck_receive_line_discrepancy_consistent",
            "quantity_discrepancy IS NULL OR "
            "(actual_quantity IS NOT NULL AND expected_quantity IS NOT NULL AND "
            "quantity_discrepancy = actual_quantity - expected_quantity)",
        )


def downgrade() -> None:
    connection = op.get_bind()
    null_actual_count = connection.scalar(
        sa.text("SELECT count(*) FROM receive_lines WHERE actual_quantity IS NULL")
    )
    if null_actual_count:
        raise RuntimeError(
            "Cannot downgrade US-REC-001: receive_lines contains rows with "
            "actual_quantity IS NULL. Record or explicitly remove those prepared "
            "test rows before downgrading; the migration will not fabricate values."
        )

    with op.batch_alter_table("receive_lines") as batch_op:
        batch_op.drop_constraint(
            "ck_receive_line_discrepancy_consistent", type_="check"
        )
        batch_op.drop_constraint("ck_receive_line_expected_nonnegative", type_="check")
        batch_op.drop_constraint("ck_receive_line_actual_nonnegative", type_="check")
        batch_op.alter_column(
            "actual_quantity", existing_type=sa.Integer(), nullable=False
        )
        batch_op.create_check_constraint(
            "ck_receive_line_actual_nonnegative", "actual_quantity >= 0"
        )
        batch_op.drop_column("quantity_discrepancy")
        batch_op.drop_column("expected_quantity")

    op.drop_index(
        op.f("ix_receives_reference_reviewed_by_user_id"), table_name="receives"
    )
    op.drop_index(op.f("ix_receives_recorded_by_user_id"), table_name="receives")
    with op.batch_alter_table("receives") as batch_op:
        batch_op.drop_constraint("ck_receives_reference_review_mismatch", type_="check")
        batch_op.drop_constraint("ck_receives_reference_review_pair", type_="check")
        batch_op.drop_constraint("ck_receives_reference_match_status", type_="check")
        batch_op.drop_constraint(
            "ck_receives_document_reference_nonempty", type_="check"
        )
        batch_op.drop_constraint(
            "ck_receives_expected_reference_nonempty", type_="check"
        )
        batch_op.drop_constraint(
            "fk_receives_reference_reviewed_by_user_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_receives_recorded_by_user_id_users", type_="foreignkey"
        )
        batch_op.drop_column("reference_reviewed_at")
        batch_op.drop_column("reference_reviewed_by_user_id")
        batch_op.drop_column("recorded_at")
        batch_op.drop_column("recorded_by_user_id")
        batch_op.drop_column("reference_match_status")
        batch_op.drop_column("document_reference")
        batch_op.drop_column("expected_reference")
