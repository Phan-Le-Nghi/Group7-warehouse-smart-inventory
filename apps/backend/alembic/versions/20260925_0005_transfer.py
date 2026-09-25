"""Create the approved US-TRF-001 Transfer schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0005"
down_revision: str | Sequence[str] | None = "20260922_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("sku_id", sa.Uuid(), nullable=False),
        sa.Column("source_location_id", sa.Uuid(), nullable=False),
        sa.Column("destination_location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("transferred_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_transfers_quantity_positive"),
        sa.CheckConstraint(
            "source_location_id <> destination_location_id",
            name="ck_transfers_different_locations",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["internal_locations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_location_id"],
            ["internal_locations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transferred_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_transfers_idempotency_key"),
    )
    op.create_index(op.f("ix_transfers_warehouse_id"), "transfers", ["warehouse_id"])
    op.create_index(op.f("ix_transfers_sku_id"), "transfers", ["sku_id"])
    op.create_index(
        op.f("ix_transfers_source_location_id"),
        "transfers",
        ["source_location_id"],
    )
    op.create_index(
        op.f("ix_transfers_destination_location_id"),
        "transfers",
        ["destination_location_id"],
    )
    op.create_index(
        "ix_transfers_warehouse_transferred_at",
        "transfers",
        ["warehouse_id", "transferred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_transfers_warehouse_transferred_at", table_name="transfers")
    op.drop_index(op.f("ix_transfers_destination_location_id"), table_name="transfers")
    op.drop_index(op.f("ix_transfers_source_location_id"), table_name="transfers")
    op.drop_index(op.f("ix_transfers_sku_id"), table_name="transfers")
    op.drop_index(op.f("ix_transfers_warehouse_id"), table_name="transfers")
    op.drop_table("transfers")
