from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt, StringConstraints


class PutawayRequest(BaseModel):
    receive_line_id: UUID
    sku_id: UUID
    quantity: int
    destination_location_id: UUID


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
