
from pydantic import BaseModel, Field
from typing import Literal


class HelpRequest(BaseModel):
    request_id: str = Field(min_length=1)
    origin_fog: str = Field(min_length=1)
    required_piles: int = Field(gt=0)
    required_power_kw: float = Field(gt=0)


class HelpResponse(BaseModel):
    request_id: str
    origin_fog: str
    proposer_fog: str
    zone: str
    status: str
    available_piles: int
    available_power_kw: float
    reason: str


class HoldRequest(BaseModel):
    request_id: str = Field(min_length=1)
    origin_fog: str = Field(min_length=1)
    required_piles: int = Field(gt=0)
    required_power_kw: float = Field(gt=0)
    ttl_seconds: int = Field(default=120, ge=1, le=600)


class HoldResponse(BaseModel):
    hold_id: str
    request_id: str
    origin_fog: str
    proposer_fog: str
    pile_ids: list[str]
    status: Literal["HOLD"]
    expires_at: str


class ConfirmRequest(BaseModel):
    hold_id: str = Field(min_length=1)


class ConfirmResponse(BaseModel):
    hold_id: str
    request_id: str
    origin_fog: str
    proposer_fog: str
    pile_ids: list[str]
    status: Literal["CONFIRMED"]


class CancelRequest(BaseModel):
    hold_id: str = Field(min_length=1)


class CancelResponse(BaseModel):
    hold_id: str
    request_id: str
    origin_fog: str
    proposer_fog: str
    pile_ids: list[str]
    status: Literal["CANCELLED"]


class ActivateRequest(BaseModel):
    hold_id: str = Field(min_length=1)


class ActivateResponse(BaseModel):
    hold_id: str
    request_id: str
    origin_fog: str
    proposer_fog: str
    pile_ids: list[str]
    status: Literal["ACTIVE"]


class CompleteRequest(BaseModel):
    hold_id: str = Field(min_length=1)


class CompleteResponse(BaseModel):
    hold_id: str
    request_id: str
    origin_fog: str
    proposer_fog: str
    pile_ids: list[str]
    status: Literal["COMPLETED"]


class LocalSessionRequest(BaseModel):
    vehicle_id: str = Field(min_length=1)
    station_id: str | None = None
    required_power_kw: float = Field(default=22.0, gt=0)


class LocalSessionResponse(BaseModel):
    session_id: str
    vehicle_id: str
    fog_id: str
    station_id: str
    pile_id: str
    power_kw: float
    status: Literal["ACTIVE"]
    created_at: str
