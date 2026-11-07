from pydantic import BaseModel, Field


class HelpRequest(BaseModel):
    request_id: str = Field(min_length=1)
    origin_fog: str = Field(min_length=1)
    required_stations: int = Field(gt=0)
    required_power_kw: float = Field(gt=0)


class HelpResponse(BaseModel):
    request_id: str
    origin_fog: str
    proposer_fog: str
    zone: str
    status: str
    available_stations: int
    available_power_kw: float
    reason: str