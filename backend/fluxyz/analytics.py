import math
from bisect import bisect_right
from datetime import datetime, timedelta
from statistics import mean

from fluxyz.models import Commodity, PairResult, Price, Signal, SignalComparison

PAIRS: tuple[tuple[Commodity, Commodity], ...] = (
    ("gold", "oil"),
    ("gold", "coal_proxy"),
    ("oil", "coal_proxy"),
)
MIN_SAMPLES = 12


def pearson(x: list[float], y: list[float], minimum: int = MIN_SAMPLES) -> float | None:
    if len(x) != len(y) or len(x) < minimum:
        return None
    mx, my = mean(x), mean(y)
    xx = sum((v - mx) ** 2 for v in x)
    yy = sum((v - my) ** 2 for v in y)
    if xx <= 1e-20 or yy <= 1e-20:
        return None
    r = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.sqrt(xx * yy)
    return round(max(-1.0, min(1.0, r)), 4)


def aligned(
    prices: list[Price], left: Commodity, right: Commodity
) -> list[tuple[datetime, float, float]]:
    xs = {p.timestamp: p.price for p in prices if p.commodity == left}
    ys = {p.timestamp: p.price for p in prices if p.commodity == right}
    return [(t, xs[t], ys[t]) for t in sorted(xs.keys() & ys.keys())]


def correlations(prices: list[Price]) -> list[PairResult]:
    results = []
    for left, right in PAIRS:
        rows = aligned(prices, left, right)
        xs, ys = [r[1] for r in rows], [r[2] for r in rows]
        rx, ry = [], []
        for previous, current in zip(rows, rows[1:], strict=False):
            if current[0] - previous[0] == timedelta(minutes=5):
                rx.append(math.log(current[1] / previous[1]))
                ry.append(math.log(current[2] / previous[2]))
        rolling = []
        for end in range(MIN_SAMPLES, len(rows) + 1):
            chunk = rows[end - MIN_SAMPLES : end]
            if chunk[-1][0] - chunk[0][0] > timedelta(minutes=55):
                continue
            value = pearson([r[1] for r in chunk], [r[2] for r in chunk])
            if value is not None:
                rolling.append((chunk[-1][0].isoformat(), value))
        half = len(rows) // 2
        results.append(
            PairResult(
                pair=f"{left}:{right}",
                left=left,
                right=right,
                price_r=pearson(xs, ys),
                return_r=pearson(rx, ry),
                samples=len(rows),
                return_samples=len(rx),
                previous_price_r=pearson(xs[:half], ys[:half]),
                rolling=rolling[-500:],
            )
        )
    return results


def compare_signals(prices: list[Price], signals: list[Signal]) -> list[SignalComparison]:
    signals = sorted(signals, key=lambda s: s.timestamp)
    times = [s.timestamp for s in signals]
    results = []
    for left, right in PAIRS:
        rows = aligned(prices, left, right)
        groups: dict[str, tuple[list[float], list[float]]] = {
            "Seasonal proximity ≤ 7 days": ([], []),
            "Elevated Kp ≥ 5": ([], []),
            "Solar X-ray class M / X": ([], []),
        }
        for start in range(0, len(rows) - MIN_SAMPLES + 1, MIN_SAMPLES):
            window = rows[start : start + MIN_SAMPLES]
            if window[-1][0] - window[0][0] != timedelta(minutes=55):
                continue
            matched = []
            for timestamp, _, _ in window:
                i = bisect_right(times, timestamp) - 1
                if i >= 0 and timestamp - times[i] <= timedelta(minutes=15):
                    matched.append(signals[i])
            if len(matched) != MIN_SAMPLES:
                continue
            value = pearson([r[1] for r in window], [r[2] for r in window])
            if value is None:
                continue
            seasonal: list[bool | None] = [s.days_to_event <= 7 for s in matched]
            kp: list[bool | None] = [
                s.kp_index >= 5 if s.kp_index is not None else None for s in matched
            ]
            solar: list[bool | None] = [
                s.solar_flare_class.startswith(("M", "X")) if s.solar_flare_class else None
                for s in matched
            ]
            for buckets, flags in zip(groups.values(), (seasonal, kp, solar), strict=True):
                if None in flags:
                    continue
                event, baseline = buckets
                (event if any(flags) else baseline).append(abs(value))
        for name, (event, baseline) in groups.items():
            enough = len(event) >= 5 and len(baseline) >= 5
            results.append(
                SignalComparison(
                    signal=name,
                    pair=f"{left}:{right}",
                    event_windows=len(event),
                    baseline_windows=len(baseline),
                    event_mean_abs_r=round(mean(event), 4) if event else None,
                    baseline_mean_abs_r=round(mean(baseline), 4) if baseline else None,
                    delta=round(mean(event) - mean(baseline), 4) if enough else None,
                    status="observational comparison" if enough else "insufficient matched windows",
                )
            )
    return results
