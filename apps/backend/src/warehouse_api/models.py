from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(trim(login_identifier)) > 0",
            name="ck_users_login_identifier_nonempty",
        ),
        CheckConstraint(
            "login_identifier = lower(trim(login_identifier))",
            name="ck_users_login_identifier_normalized",
        ),
        CheckConstraint(
            "role IN ('WAREHOUSE_STAFF', 'MANAGER', 'PURCHASING', 'ADMIN')",
            name="ck_users_role",
        ),
        UniqueConstraint("login_identifier", name="uq_users_login_identifier"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    login_identifier: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "length(session_token_hash) = 32",
            name="ck_auth_sessions_token_hash_length",
        ),
        CheckConstraint(
            "expires_at > created_at", name="ck_auth_sessions_expiry_after_creation"
        ),
        UniqueConstraint("session_token_hash", name="uq_auth_sessions_token_hash"),
        Index(
            "ix_auth_sessions_active_expiry",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)


class InternalLocation(Base):
    __tablename__ = "internal_locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_location_warehouse_code"),
        CheckConstraint(
            "code IN ('BACKROOM', 'SALES_SHELF')", name="ck_location_tracked_code"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))


class Sku(Base):
    __tablename__ = "skus"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)


class Receive(Base):
    __tablename__ = "receives"
    __table_args__ = (
        CheckConstraint(
            "expected_reference IS NULL OR length(trim(expected_reference)) > 0",
            name="ck_receives_expected_reference_nonempty",
        ),
        CheckConstraint(
            "document_reference IS NULL OR length(trim(document_reference)) > 0",
            name="ck_receives_document_reference_nonempty",
        ),
        CheckConstraint(
            "reference_match_status IS NULL OR "
            "reference_match_status IN ('REFERENCE_MATCH', 'REFERENCE_MISMATCH')",
            name="ck_receives_reference_match_status",
        ),
        CheckConstraint(
            "(reference_reviewed_by_user_id IS NULL AND "
            "reference_reviewed_at IS NULL) OR "
            "(reference_reviewed_by_user_id IS NOT NULL AND "
            "reference_reviewed_at IS NOT NULL)",
            name="ck_receives_reference_review_pair",
        ),
        CheckConstraint(
            "reference_reviewed_by_user_id IS NULL OR "
            "reference_match_status = 'REFERENCE_MISMATCH'",
            name="ck_receives_reference_review_mismatch",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    expected_reference: Mapped[str | None] = mapped_column(String(255))
    document_reference: Mapped[str | None] = mapped_column(String(255))
    reference_match_status: Mapped[str | None] = mapped_column(String(24))
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reference_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class ReceiveLine(Base):
    __tablename__ = "receive_lines"
    __table_args__ = (
        CheckConstraint(
            "actual_quantity IS NULL OR actual_quantity >= 0",
            name="ck_receive_line_actual_nonnegative",
        ),
        CheckConstraint(
            "expected_quantity IS NULL OR expected_quantity >= 0",
            name="ck_receive_line_expected_nonnegative",
        ),
        CheckConstraint(
            "quantity_discrepancy IS NULL OR "
            "(actual_quantity IS NOT NULL AND expected_quantity IS NOT NULL AND "
            "quantity_discrepancy = actual_quantity - expected_quantity)",
            name="ck_receive_line_discrepancy_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receive_id: Mapped[UUID] = mapped_column(
        ForeignKey("receives.id", ondelete="RESTRICT"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="RESTRICT"), index=True
    )
    expected_quantity: Mapped[int | None] = mapped_column(Integer)
    actual_quantity: Mapped[int | None] = mapped_column(Integer)
    quantity_discrepancy: Mapped[int | None] = mapped_column(Integer)


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("sku_id", "location_id", name="uq_stock_sku_location"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("internal_locations.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)


class PickRequest(Base):
    __tablename__ = "pick_requests"
    __table_args__ = (
        CheckConstraint(
            "requested_quantity > 0", name="ck_pick_requests_requested_positive"
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('FULLY_COMPLETED', 'PARTIAL_INSUFFICIENT')",
            name="ck_pick_requests_outcome",
        ),
        CheckConstraint(
            "(outcome IS NULL AND confirmed_by_user_id IS NULL AND "
            "confirmed_at IS NULL) OR "
            "(outcome IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND "
            "confirmed_at IS NOT NULL)",
            name="ck_pick_requests_confirmation_complete",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="RESTRICT"), index=True
    )
    requested_quantity: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str | None] = mapped_column(String(32))
    confirmed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PickAllocation(Base):
    __tablename__ = "pick_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pick_allocations_quantity_positive"),
        UniqueConstraint(
            "pick_id",
            "source_location_id",
            name="uq_pick_allocations_pick_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pick_id: Mapped[UUID] = mapped_column(
        ForeignKey("pick_requests.id", ondelete="RESTRICT"), index=True
    )
    source_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("internal_locations.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_transfers_quantity_positive"),
        CheckConstraint(
            "source_location_id <> destination_location_id",
            name="ck_transfers_different_locations",
        ),
        UniqueConstraint("idempotency_key", name="uq_transfers_idempotency_key"),
        Index(
            "ix_transfers_warehouse_transferred_at",
            "warehouse_id",
            "transferred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="RESTRICT"), index=True
    )
    source_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("internal_locations.id", ondelete="RESTRICT"), index=True
    )
    destination_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("internal_locations.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    transferred_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    transferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_fingerprint: Mapped[str] = mapped_column(String(64))


class PutawayAllocation(Base):
    __tablename__ = "putaway_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_putaway_quantity_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receive_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("receive_lines.id", ondelete="RESTRICT"), index=True
    )
    sku_id: Mapped[UUID] = mapped_column(
        ForeignKey("skus.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    destination_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("internal_locations.id", ondelete="RESTRICT"), index=True
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
