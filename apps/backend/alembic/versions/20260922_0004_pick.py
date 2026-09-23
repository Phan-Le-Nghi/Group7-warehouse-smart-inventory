"""Create the approved US-PICK-001 schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_0004"
down_revision: str | Sequence[str] | None = "20260922_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pick_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("sku_id", sa.Uuid(), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("confirmed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "requested_quantity > 0", name="ck_pick_requests_requested_positive"
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('FULLY_COMPLETED', 'PARTIAL_INSUFFICIENT')",
            name="ck_pick_requests_outcome",
        ),
        sa.CheckConstraint(
            "(outcome IS NULL AND confirmed_by_user_id IS NULL AND "
            "confirmed_at IS NULL) OR "
            "(outcome IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND "
            "confirmed_at IS NOT NULL)",
            name="ck_pick_requests_confirmation_complete",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pick_requests_confirmed_by_user_id"),
        "pick_requests",
        ["confirmed_by_user_id"],
    )
    op.create_index(op.f("ix_pick_requests_sku_id"), "pick_requests", ["sku_id"])
    op.create_index(
        op.f("ix_pick_requests_warehouse_id"), "pick_requests", ["warehouse_id"]
    )

    op.create_table(
        "pick_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pick_id", sa.Uuid(), nullable=False),
        sa.Column("source_location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name="ck_pick_allocations_quantity_positive"
        ),
        sa.ForeignKeyConstraint(["pick_id"], ["pick_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["internal_locations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pick_id",
            "source_location_id",
            name="uq_pick_allocations_pick_source",
        ),
    )
    op.create_index(
        op.f("ix_pick_allocations_pick_id"), "pick_allocations", ["pick_id"]
    )
    op.create_index(
        op.f("ix_pick_allocations_source_location_id"),
        "pick_allocations",
        ["source_location_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pick_allocations_source_location_id"),
        table_name="pick_allocations",
    )
    op.drop_index(op.f("ix_pick_allocations_pick_id"), table_name="pick_allocations")
    op.drop_table("pick_allocations")
    op.drop_index(op.f("ix_pick_requests_warehouse_id"), table_name="pick_requests")
    op.drop_index(op.f("ix_pick_requests_sku_id"), table_name="pick_requests")
    op.drop_index(
        op.f("ix_pick_requests_confirmed_by_user_id"), table_name="pick_requests"
    )
    op.drop_table("pick_requests")
