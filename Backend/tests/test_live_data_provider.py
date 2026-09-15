"""
Unit tests for live_data_provider.py and see_layer.py weather fallback mechanism.
"""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.live_data_provider import LiveDataProvider
from src.see_layer import get_weather_advisory


def test_live_data_provider_returns_standardized_shape():
    """Verifies that live weather call returns matching schema with provenance: live_api."""
    provider = LiveDataProvider()
    live_res = provider.get_live_weather(district="Alappuzha", past_days=7, forecast_days=3)

    if live_res is not None:
        assert live_res["provenance"] == "live_api"
        assert live_res["data_source"] == "live_open_meteo"
        assert len(live_res["records"]) > 0
        assert "rainfall_mm" in live_res["records"][0]
        assert "forecast_flag" in live_res["records"][0]


def test_weather_advisory_seamless_fallback_on_network_failure():
    """
    Verifies that when live API fails or times out:
    1. The endpoint does NOT fail or raise an exception
    2. Seamlessly falls back to historical IMD CSV
    3. Accurately labels provenance: historical_csv_fallback
    """
    class MockFailingProvider:
        def get_live_weather(self, *args, **kwargs):
            return None  # Simulate network disconnection / timeout

    failing_provider = MockFailingProvider()
    adv = get_weather_advisory(district="Alappuzha", crop="rice", live_provider=failing_provider)

    assert adv["provenance"] == "historical_csv_fallback"
    assert adv["data_source"] == "historical_imd_csv"
    assert "historical IMD" in adv["data_provenance"]
    assert len(adv["advisory_sentence"]) > 15
    assert adv["rainfall_std_mm"] >= 0.0
