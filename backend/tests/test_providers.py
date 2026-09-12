from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from fluxyz.models import Price
from fluxyz.providers import ProviderError, get_coal, get_kp, get_prices, get_solar, is_market_open
from fluxyz.settings import settings

NOW = datetime(2026, 9, 12, 16, tzinfo=timezone.utc)


def test_calendar_weekend_holiday_and_early_close() -> None:
    assert not is_market_open(NOW)
    assert is_market_open(datetime(2026, 9, 11, 15, tzinfo=timezone.utc))
    assert not is_market_open(datetime(2026, 9, 7, 15, tzinfo=timezone.utc))
    assert not is_market_open(datetime(2026, 11, 27, 19, tzinfo=timezone.utc))


def test_noaa_object_format_and_stale_solar() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "k-index" in request.url.path:
            return httpx.Response(200, json=[{"time_tag": "2026-09-12T15:00:00", "Kp": 5.33}])
        return httpx.Response(
            200,
            json=[
                {
                    "time_tag": "2026-09-12T14:00:00Z",
                    "current_class": "M1.0",
                }
            ],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert get_kp(client, NOW).kp == 5.33
        with pytest.raises(ProviderError, match="older than thirty"):
            get_solar(client, NOW)


def test_noaa_legacy_table_and_no_future_readings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                ["time_tag", "Kp"],
                ["2026-09-12 15:00:00", "2.67"],
                ["2026-09-12 18:00:00", "8"],
            ],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert get_kp(client, NOW).kp == 2.67
        with pytest.raises(ProviderError, match="older than six"):
            get_kp(client, NOW + timedelta(days=1))


def test_twelve_preserves_successful_symbols_when_one_is_not_entitled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "twelve_data_api_key", "test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timezone"] == "UTC"
        return httpx.Response(
            200,
            json={
                "GLD": {"values": [{"datetime": "2025-01-02 15:00:00", "close": "250.25"}]},
                "USO": {"values": [{"datetime": "2025-01-02 15:00:00", "close": "80.0"}]},
                "BTU": {"status": "error", "code": 403},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        data = get_prices(client, backfill=True)
        assert isinstance(data["BTU"], ProviderError)
        gold = data["GLD"]
        assert isinstance(gold, list)
        assert gold[0].timestamp.tzinfo == timezone.utc
        assert gold[0].source == "twelve_data"
        assert gold[0].price == 250.25


def test_eia_monthly_coal_cost_and_withheld_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "eia_api_key", "test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["frequency"] == "monthly"
        assert request.url.params["facets[fueltypeid][]"] == "COW"
        return httpx.Response(
            200,
            json={
                "response": {
                    "data": [
                        {
                            "period": "2026-06",
                            "cost": "48.35",
                            "cost-units": "dollars per short tons",
                        },
                        {"period": "2026-05", "cost": "w", "cost-units": "dollars per short tons"},
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        data = get_coal(client)
        assert len(data) == 1
        assert data[0].period == "2026-06"
        assert data[0].source == "eia"


def test_nonfinite_and_negative_prices_are_rejected() -> None:
    for value in (float("nan"), float("inf"), 0, -10):
        with pytest.raises(ValidationError):
            Price(commodity="gold", timestamp=NOW, price=value)
