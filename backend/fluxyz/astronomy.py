import math
from datetime import datetime, timedelta, timezone

from fluxyz.models import Signal

EVENTS = (
    ("March equinox", (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057)),
    ("June solstice", (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030)),
    ("September equinox", (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078)),
    ("December solstice", (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032)),
)
PERIODIC = (
    (485, 324.96, 1934.136),
    (203, 337.23, 32964.467),
    (199, 342.08, 20.186),
    (182, 27.85, 445267.112),
    (156, 73.14, 45036.886),
    (136, 171.52, 22518.443),
    (77, 222.54, 65928.934),
    (74, 296.72, 3034.906),
    (70, 243.58, 9037.513),
    (58, 119.81, 33718.147),
    (52, 297.17, 150.678),
    (50, 21.02, 2281.226),
    (45, 247.54, 29929.562),
    (44, 325.15, 31555.956),
    (29, 60.93, 4443.417),
    (18, 155.12, 67555.328),
    (17, 288.79, 4562.452),
    (16, 198.04, 62894.029),
    (14, 199.76, 31436.921),
    (12, 95.39, 14577.848),
    (12, 287.11, 31931.756),
    (12, 320.81, 34777.259),
    (9, 227.73, 1222.114),
    (8, 15.45, 16859.074),
)


def season_dates(year: int) -> list[tuple[str, datetime]]:
    """Meeus chapter 27 periodic approximation; modern UTC accuracy within minutes."""
    y = (year - 2000) / 1000
    dates = []
    for name, coefficients in EVENTS:
        jde0 = sum(coefficient * y**i for i, coefficient in enumerate(coefficients))
        t = (jde0 - 2451545.0) / 36525
        w = math.radians(35999.373 * t - 2.47)
        correction = 1 + 0.0334 * math.cos(w) + 0.0007 * math.cos(2 * w)
        s = sum(a * math.cos(math.radians(b + c * t)) for a, b, c in PERIODIC)
        jd = jde0 + 0.00001 * s / correction
        utc = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(
            days=jd - 2451545.0, seconds=-69.184
        )
        dates.append((name, utc))
    return dates


def astronomical_signal(now: datetime) -> Signal:
    dates = [event for year in range(now.year - 1, now.year + 2) for event in season_dates(year)]
    name, event_time = min(dates, key=lambda event: abs((event[1] - now).total_seconds()))
    solstice = min(
        (event for event in dates if "solstice" in event[0]),
        key=lambda event: abs((event[1] - now).total_seconds()),
    )
    return Signal(
        timestamp=now,
        days_to_solstice=abs((solstice[1] - now).total_seconds()) / 86400,
        days_to_event=abs((event_time - now).total_seconds()) / 86400,
        nearest_event=name,
        event_timestamp=event_time,
    )
