import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from pydantic import ValidationError

from fluxyz import agent, store
from fluxyz.astronomy import astronomical_signal
from fluxyz.models import Observation, SourceHealth
from fluxyz.providers import (
    SYMBOLS,
    ProviderError,
    get_coal,
    get_kp,
    get_prices,
    get_solar,
    is_market_open,
)
from fluxyz.service import build_dashboard, cached_dashboard
from fluxyz.settings import settings

logger = logging.getLogger("fluxyz.ingestion")


def health(source: str, error: Exception | None = None) -> None:
    now = datetime.now(timezone.utc)
    previous = next((s for s in store.sources() if s.source == source), None)
    message = "Live source · last poll succeeded"
    if error:
        if isinstance(error, ProviderError):
            message = str(error)
        elif isinstance(error, httpx.HTTPStatusError):
            message = f"Provider HTTP {error.response.status_code}; last good data retained"
        else:
            message = "Provider request or response failed validation; last good data retained"
        logger.warning("%s: %s", source, message)
    store.save(
        "source_health",
        [
            SourceHealth(
                source=source,
                status="error" if error else "ok",
                last_attempt=now,
                last_success=previous.last_success
                if error and previous
                else (None if error else now),
                message=message,
            )
        ],
    )


def due(source: str, seconds: int, now: datetime) -> bool:
    previous = next((s for s in store.sources() if s.source == source), None)
    if previous is None or previous.last_attempt is None:
        return True
    return (now - previous.last_attempt.replace(tzinfo=timezone.utc)).total_seconds() >= seconds


def cycle() -> None:
    now = datetime.now(timezone.utc)
    existing = store.prices()
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        if not existing or is_market_open(now):
            try:
                last = max((p.timestamp for p in existing), default=now - timedelta(days=30))
                fetched = get_prices(client, backfill=now - last > timedelta(hours=1))
                for symbol, records in fetched.items():
                    if isinstance(records, ProviderError):
                        health(f"twelve_data:{symbol}", records)
                    elif records:
                        store.save("commodity_prices", list(records))
                        health(f"twelve_data:{symbol}")
            except (httpx.HTTPError, ValidationError, ProviderError) as error:
                for symbol in SYMBOLS:
                    health(f"twelve_data:{symbol}", error)
        if due("eia", 86400, now):
            try:
                store.save("coal_reference", list(get_coal(client)))
                health("eia")
            except (httpx.HTTPError, ValidationError, ProviderError) as error:
                health("eia", error)
        signal = astronomical_signal(now)
        try:
            kp = get_kp(client, now)
            signal.kp_index = kp.kp
            signal.kp_timestamp = kp.time_tag.replace(tzinfo=timezone.utc)
            health("noaa_kp")
        except (httpx.HTTPError, ValidationError, ProviderError) as error:
            health("noaa_kp", error)
        try:
            solar = get_solar(client, now)
            signal.solar_flare_class = solar.current_class
            signal.solar_timestamp = solar.time_tag
            signal.flare_peak_class = solar.max_class
            signal.flare_peak_timestamp = solar.max_time
            health("noaa_solar")
        except (httpx.HTTPError, ValidationError, ProviderError) as error:
            health("noaa_solar", error)
        store.save("universal_signals", [signal])
        health("astronomy")
        cached_dashboard.cache_clear()
        try:
            text = agent.generate(client, build_dashboard("1w"), "", commentary=True)
            store.save(
                "observations",
                [
                    Observation(
                        id=str(uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        text=text,
                        model=settings.gemini_model,
                    )
                ],
            )
            health("gemini")
        except (httpx.HTTPError, ValidationError, ProviderError) as error:
            health("gemini", error)
        cached_dashboard.cache_clear()
