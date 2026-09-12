from datetime import datetime, timedelta, timezone

import pytest

from fluxyz.analytics import compare_signals, correlations, pearson
from fluxyz.astronomy import astronomical_signal, season_dates
from fluxyz.models import Price

BASE = datetime(2026, 9, 10, 14, tzinfo=timezone.utc)


def prices(count: int = 24) -> list[Price]:
    return [
        Price(
            commodity=commodity,
            price=float(100 + i * multiplier),
            timestamp=BASE + timedelta(minutes=5 * i),
        )
        for i in range(count)
        for commodity, multiplier in [("gold", 1), ("oil", 2), ("coal_proxy", -1)]
    ]


def test_pearson_perfect_inverse_constant_and_insufficient() -> None:
    x = list(map(float, range(12)))
    assert pearson(x, x) == 1
    assert pearson(x, x[::-1]) == -1
    assert pearson(x, [1.0] * 12) is None
    assert pearson(x[:3], x[:3]) is None
    assert pearson(x, x[:3]) is None


def test_correlations_align_timestamps_without_forward_filling() -> None:
    data = prices()
    removed = data.pop(1)
    results = correlations(data)
    assert results[0].samples == 23
    assert results[0].price_r == 1
    assert results[1].price_r == -1
    assert results[0].return_samples == 22
    assert removed.commodity == "oil"


def test_overnight_gap_excluded_from_returns_and_rolling() -> None:
    data = prices()
    for row in data:
        if row.timestamp >= BASE + timedelta(hours=1):
            row.timestamp += timedelta(days=1)
    result = correlations(data)[0]
    assert result.samples == 24
    assert result.return_samples == 22
    assert len(result.rolling) == 2


def test_missing_signal_history_never_backfills_current_reading() -> None:
    future = astronomical_signal(BASE + timedelta(days=1))
    comparisons = compare_signals(prices(), [future])
    assert all(c.event_windows == c.baseline_windows == 0 for c in comparisons)
    assert all(c.delta is None for c in comparisons)


def test_matched_nonoverlapping_event_and_baseline_windows() -> None:
    data = [
        Price(commodity=commodity, price=float(100 + i), timestamp=BASE + timedelta(minutes=5 * i))
        for i in range(120)
        for commodity in ("gold", "oil", "coal_proxy")
    ]
    signals = []
    for i in range(120):
        signal = astronomical_signal(BASE + timedelta(minutes=5 * i))
        signal.kp_index = 6 if i < 60 else 2
        signal.solar_flare_class = "M1.0" if i < 60 else "B1.0"
        signals.append(signal)
    rows = compare_signals(data, signals)
    kp = next(c for c in rows if c.signal == "Elevated Kp ≥ 5")
    assert kp.event_windows == kp.baseline_windows == 5
    assert kp.delta == 0


def test_astronomy_matches_known_2025_equinox_and_year_boundary() -> None:
    known = datetime(2025, 9, 22, 18, 19, tzinfo=timezone.utc)
    calculated = dict(season_dates(2025))["September equinox"]
    assert abs((calculated - known).total_seconds()) < 600
    january = astronomical_signal(datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert january.nearest_event == "December solstice"
    assert 10 < january.days_to_event < 12
    assert january.days_to_solstice == pytest.approx(january.days_to_event)
