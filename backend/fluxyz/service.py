from datetime import datetime, timedelta, timezone
from functools import lru_cache
from time import monotonic

from fluxyz import store
from fluxyz.analytics import compare_signals, correlations
from fluxyz.models import Dashboard
from fluxyz.providers import is_market_open

METHODOLOGY = (
    "Pearson r on exact timestamp-aligned, completed 5-minute proxy closes; minimum 12 pairs. "
    "Return r uses log returns on consecutive 5-minute bars, excluding overnight gaps. "
    "Chart ranges end at the latest stored market bar; 1D covers the latest trading session. "
    "Rolling r uses 12 consecutive bars (one hour). Signal comparisons use non-overlapping "
    "12-bar windows, with a signal observed at or before every bar and no more than 15 minutes "
    "old. Event windows contain seasonal proximity ≤7 days, Kp ≥5, or M/X solar X-ray readings; "
    "baseline windows contain no such event. At least five event and five baseline windows "
    "are required per comparison. Differences are exploratory, not significance tests; "
    "autocorrelation, multiple comparisons, trend and common drivers can confound results."
)


@lru_cache(maxsize=6)
def cached_dashboard(window: str, bucket: int) -> Dashboard:
    return build_dashboard(window)


def dashboard(window: str = "1w") -> Dashboard:
    return cached_dashboard(window, int(monotonic() / 30))


def build_dashboard(window: str = "1w") -> Dashboard:
    now = datetime.now(timezone.utc)
    all_prices = store.prices()
    all_signals = store.signals()
    if all_prices:
        latest = max(p.timestamp for p in all_prices)
        if window == "1d":
            since = latest.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            since = latest - timedelta(days=7 if window == "1w" else 30)
        selected = [p for p in all_prices if p.timestamp >= since]
    else:
        selected = []
    first = all_signals[0].timestamp if all_signals else None
    hours = max(0, (now - first).total_seconds() / 3600) if first else 0
    comparisons = compare_signals(all_prices, all_signals)
    ready = [c for c in comparisons if c.delta is not None]
    if hours < 24:
        note = (
            f"Collection has run for {hours:.1f} hours. A first-day assessment is pending "
            "24 hours of observations and sufficient overlapping market bars. No universal-signal "
            "association can be reported yet. Historical price backfill is not signal history."
        )
    elif not ready:
        note = (
            "At least one day has elapsed, but there are not yet five event and five baseline "
            "windows with matched market and signal readings. No defensible signal association "
            "can be reported. Closed markets and seasonal coverage may require more time."
        )
    else:
        note = (
            f"{len(ready)} exploratory signal/pair comparisons have sufficient window counts. "
            "See the measured differences and sample sizes below. These are observed "
            "coincidences, not evidence of causation or statistical significance."
        )
    return Dashboard(
        generated_at=now,
        range=window,
        market_open=is_market_open(now),
        prices={
            key: [p for p in selected if p.commodity == key]
            for key in ("gold", "oil", "coal_proxy")
        },
        correlations=correlations(selected),
        signal_tests=comparisons,
        signals=all_signals[-1] if all_signals else None,
        coal_reference=store.latest_coal(),
        observations=store.observations(),
        sources=store.sources(),
        first_observation_at=first,
        collection_hours=round(hours, 2),
        first_day_note=note,
        methodology=METHODOLOGY,
    )
