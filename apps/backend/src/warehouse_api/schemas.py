from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt, StringConstraints


class PutawayRequest(BaseModel):
    receive_line_id: UUID
    sku_id: UUID
    quantity: int
    destination_location_id: UUID


class PickAllocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_location_id: UUID
    quantity: StrictInt


class PickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pick_id: UUID
    allocations: list[PickAllocationRequest]


class PickLocationAvailability(BaseModel):
    id: UUID
    code: str
    available_quantity: int


class PickContextResponse(BaseModel):
    pick_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    sku: str
    requested_quantity: int
    outcome: str | None
    locations: list[PickLocationAvailability]
    warehouse_total: int


class PickAllocationResult(BaseModel):
    source_location_id: UUID
    source_location: str
    quantity: int
    remaining_source_quantity: int


class PickResponse(BaseModel):
    pick_id: UUID
    sku_id: UUID
    requested_quantity: int
    picked_quantity: int
    remaining_quantity: int
    outcome: str
    allocations: list[PickAllocationResult]
    confirmed_by_user_id: UUID
    confirmed_at: datetime
    warehouse_total: int


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: UUID
    source_location_id: UUID
    destination_location_id: UUID
    quantity: StrictInt


class TransferLocationAvailability(BaseModel):
    id: UUID
    code: str
    available_quantity: int


class TransferContextResponse(BaseModel):
    warehouse_id: UUID
    sku_id: UUID
    sku: str
    locations: list[TransferLocationAvailability]
    warehouse_total: int


class TransferStockResult(BaseModel):
    source_quantity: int
    destination_quantity: int
    warehouse_total: int


class TransferResponse(BaseModel):
    transfer_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    quantity: int
    source_location_id: UUID
    source_location: str
    destination_location_id: UUID
    destination_location: str
    transferred_by_user_id: UUID
    transferred_at: datetime
    stock: TransferStockResult


class StockResult(BaseModel):
    destination_quantity: int
    warehouse_total: int


class PutawayResponse(BaseModel):
    putaway_id: UUID
    receive_line_id: UUID
    sku_id: UUID
    quantity: int
    destination_location_id: UUID
    destination_location: str
    confirmed_at: datetime
    stock: StockResult


class LocationOption(BaseModel):
    id: UUID
    code: str


class PutawayContextResponse(BaseModel):
    receive_line_id: UUID
    sku_id: UUID
    sku: str
    actual_quantity: int
    confirmed_quantity: int
    eligible_quantity: int
    locations: list[LocationOption]


class ReceiveReferenceState(BaseModel):
    expected: str
    document: str | None
    match_status: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None


class ReceiveLineState(BaseModel):
    receive_line_id: UUID
    sku_id: UUID
    sku: str
    expected_quantity: int
    actual_quantity: int | None
    quantity_discrepancy: int | None


class ReceiveContextResponse(BaseModel):
    receive_id: UUID
    warehouse_id: UUID
    reference: ReceiveReferenceState
    recorded_at: datetime | None
    putaway_eligible: bool
    lines: list[ReceiveLineState]


class ReceiveRecordLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receive_line_id: UUID
    sku_id: UUID
    actual_quantity: StrictInt


class ReceiveRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receive_id: UUID
    document_reference: Annotated[str, StringConstraints(max_length=255)]
    lines: list[ReceiveRecordLineRequest]


class ReferenceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReferenceReviewResponse(BaseModel):
    receive_id: UUID
    match_status: str
    reviewed_by_user_id: UUID
    reviewed_at: datetime
    putaway_eligible: bool
