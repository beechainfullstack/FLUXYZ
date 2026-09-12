from datetime import datetime, timedelta, timezone

import exchange_calendars
import httpx
from pydantic import BaseModel, Field, TypeAdapter

from fluxyz.models import CoalReference, Commodity, Price
from fluxyz.settings import settings

SYMBOLS: dict[str, Commodity] = {"GLD": "gold", "USO": "oil", "BTU": "coal_proxy"}
CALENDAR = exchange_calendars.get_calendar("XNYS")
KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
SOLAR_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
EIA_URL = "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"


class ProviderError(Exception):
    pass


class Candle(BaseModel):
    datetime: datetime
    close: float
    volume: float | None = None


class Series(BaseModel):
    status: str = "ok"
    code: int | None = None
    values: list[Candle] = Field(default_factory=list)


class KpReading(BaseModel):
    time_tag: datetime
    kp: float = Field(alias="Kp", ge=0, le=9)


class SolarReading(BaseModel):
    time_tag: datetime
    current_class: str = Field(pattern=r"^[ABCMX]\d+(\.\d+)?$")
    max_time: datetime | None = None
    max_class: str | None = None


class EiaRow(BaseModel):
    period: str
    cost: str | float | None = None
    units: str = Field(alias="cost-units")


class EiaData(BaseModel):
    data: list[EiaRow]


class EiaResponse(BaseModel):
    response: EiaData


def is_market_open(now: datetime) -> bool:
    return bool(CALENDAR.is_open_on_minute(now.replace(second=0, microsecond=0)))


def get_prices(client: httpx.Client, backfill: bool) -> dict[str, list[Price] | ProviderError]:
    if not settings.twelve_data_api_key:
        raise ProviderError("Twelve Data key is not configured")
    response = client.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": ",".join(SYMBOLS),
            "interval": "5min",
            "timezone": "UTC",
            "outputsize": 2000 if backfill else 12,
            "apikey": settings.twelve_data_api_key,
        },
    )
    response.raise_for_status()
    payload = TypeAdapter(dict[str, object]).validate_python(response.json())
    result: dict[str, list[Price] | ProviderError] = {}
    now = datetime.now(timezone.utc)
    for symbol, commodity in SYMBOLS.items():
        series = Series.model_validate(payload.get(symbol, payload))
        if series.status == "error" or not series.values:
            result[symbol] = ProviderError(
                f"Twelve Data returned no usable {symbol} bars (code {series.code})"
            )
            continue
        result[symbol] = [
            Price(
                commodity=commodity,
                price=c.close,
                volume=c.volume,
                timestamp=c.datetime.replace(tzinfo=timezone.utc),
            )
            for c in series.values
            if c.datetime.replace(tzinfo=timezone.utc) + timedelta(minutes=5) <= now
        ]
    return result


def get_coal(client: httpx.Client) -> list[CoalReference]:
    if not settings.eia_api_key:
        raise ProviderError("EIA key is not configured")
    response = client.get(
        EIA_URL,
        params={
            "api_key": settings.eia_api_key,
            "frequency": "monthly",
            "data[0]": "cost",
            "facets[location][]": "US",
            "facets[sectorid][]": "99",
            "facets[fueltypeid][]": "COW",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 24,
        },
    )
    response.raise_for_status()
    rows = EiaResponse.model_validate(response.json()).response.data
    records = []
    for row in rows:
        try:
            price = float(row.cost) if row.cost is not None else 0
        except ValueError:
            continue
        if price > 0:
            records.append(
                CoalReference(
                    timestamp=datetime.fromisoformat(f"{row.period}-01T00:00:00+00:00"),
                    price=price,
                    period=row.period,
                    units=row.units,
                )
            )
    if not records:
        raise ProviderError("EIA returned no published coal cost observations")
    return records


def get_kp(client: httpx.Client, now: datetime) -> KpReading:
    response = client.get(KP_URL)
    response.raise_for_status()
    payload = response.json()
    if payload and isinstance(payload[0], list):
        headers = payload[0]
        payload = [dict(zip(headers, row, strict=True)) for row in payload[1:]]
    rows = TypeAdapter(list[KpReading]).validate_python(payload)
    eligible = [r for r in rows if r.time_tag.replace(tzinfo=timezone.utc) <= now]
    if not eligible:
        raise ProviderError("NOAA returned no Kp readings")
    latest = max(eligible, key=lambda r: r.time_tag)
    if now - latest.time_tag.replace(tzinfo=timezone.utc) > timedelta(hours=6):
        raise ProviderError("NOAA Kp reading is older than six hours")
    return latest


def get_solar(client: httpx.Client, now: datetime) -> SolarReading:
    response = client.get(SOLAR_URL)
    response.raise_for_status()
    rows = TypeAdapter(list[SolarReading]).validate_python(response.json())
    eligible = [r for r in rows if r.time_tag.replace(tzinfo=timezone.utc) <= now]
    if not eligible:
        raise ProviderError("NOAA returned no solar X-ray readings")
    latest = max(eligible, key=lambda r: r.time_tag)
    if now - latest.time_tag.replace(tzinfo=timezone.utc) > timedelta(minutes=30):
        raise ProviderError("NOAA solar reading is older than thirty minutes")
    return latest
