
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
