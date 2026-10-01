from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class Filters(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    origin: str | None = None
    destination: str | None = None
    lane: str | None = None
    carrier: str | None = None
    recommended_carrier: str | None = None
    rate_type: Literal["Contract", "Spot", "Owned"] | None = None
    recommended_rate_type: Literal["Contract", "Spot", "Owned"] | None = None
    min_saving: float = Field(0, ge=0)
    search: str | None = None
    shipment_ids: list[str] | None = Field(None, max_length=100)

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must precede end_date")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    filters: Filters = Field(default_factory=Filters)
    context: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    intent: Literal[
        "OVERALL_SAVINGS",
        "TIME_SAVINGS",
        "TOP_LANES",
        "LANE_ANALYSIS",
        "LANE_COMPARISON",
        "CARRIER_ANALYSIS",
        "CARRIER_COMPARISON",
        "SHIPMENT_LOOKUP",
        "TOP_SHIPMENTS",
        "RATE_ANALYSIS",
        "TREND_ANALYSIS",
        "SUMMARY",
        "FILTER_COMMAND",
    ]
    filters: Filters = Field(default_factory=Filters)
    entities: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(5, ge=1, le=50)


class AIResponse(BaseModel):
    answer: str
    intent: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    table: list[dict[str, Any]] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    chart: dict[str, Any] | None = None
    confidence: Literal["high", "unsupported"] = "high"
    data_scope: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    provider: str = "mock"
