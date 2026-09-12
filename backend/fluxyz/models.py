from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Commodity = Literal["gold", "oil", "coal_proxy"]


class TimedModel(BaseModel):
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Price(TimedModel):
    commodity: Commodity
    price: float = Field(gt=0, allow_inf_nan=False)
    volume: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    source: str = "twelve_data"


class CoalReference(TimedModel):
    price: float = Field(gt=0, allow_inf_nan=False)
    period: str
    units: str
    description: str = "US electric power sector · all coal products · monthly fuel receipts cost"
    source: str = "eia"


class Signal(TimedModel):
    days_to_solstice: float
    days_to_event: float
    nearest_event: str
    event_timestamp: datetime
    kp_index: float | None = Field(default=None, ge=0, le=9)
    kp_timestamp: datetime | None = None
    solar_flare_class: str | None = None
    solar_timestamp: datetime | None = None
    flare_peak_class: str | None = None
    flare_peak_timestamp: datetime | None = None

    @field_validator("event_timestamp", "kp_timestamp", "solar_timestamp", "flare_peak_timestamp")
    @classmethod
    def optional_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Observation(TimedModel):
    id: str
    text: str
    model: str
    kind: str = "observation"


class SourceHealth(BaseModel):
    source: str
    status: Literal["pending", "ok", "error"] = "pending"
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    message: str = "Awaiting first poll"


class PairResult(BaseModel):
    pair: str
    left: Commodity
    right: Commodity
    price_r: float | None
    return_r: float | None
    samples: int
    return_samples: int
    previous_price_r: float | None = None
    rolling: list[tuple[str, float]] = Field(default_factory=list)


class SignalComparison(BaseModel):
    signal: str
    pair: str
    event_windows: int
    baseline_windows: int
    event_mean_abs_r: float | None
    baseline_mean_abs_r: float | None
    delta: float | None
    status: str


class Dashboard(BaseModel):
    generated_at: datetime
    range: str
    market_open: bool
    prices: dict[str, list[Price]]
    correlations: list[PairResult]
    signal_tests: list[SignalComparison]
    signals: Signal | None
    coal_reference: CoalReference | None
    observations: list[Observation]
    sources: list[SourceHealth]
    first_observation_at: datetime | None
    collection_hours: float
    first_day_note: str
    methodology: str
