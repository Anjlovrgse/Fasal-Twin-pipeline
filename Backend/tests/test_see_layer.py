"""
Unit tests for see_layer.py verifying price trend, weather advisory, and maturity proxy.
"""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.see_layer import get_price_trend, get_weather_advisory, get_crop_maturity_proxy


def test_see_price_trend_returns_real_time_series():
    """Verifies that get_price_trend extracts authentic mandi points."""
    trend = get_price_trend("Alappuzha", "Alappuzha Mandi", "rice", days=14)
    assert trend["status"] == "available"
    assert len(trend["time_series"]) > 0
    assert trend["summary"]["mean_modal_price_rs"] > 2000.0


def test_see_weather_advisory_generates_grounded_sentence():
    """Verifies that get_weather_advisory derives statistical shifts or no-shift messages."""
    advisory = get_weather_advisory("Alappuzha", "rice", lookback_days=30)
    assert "advisory_sentence" in advisory
    assert len(advisory["advisory_sentence"]) > 10
    assert "rainfall_variance_mm2" in advisory


def test_see_crop_maturity_contains_mandatory_source_label():
    """
    Non-negotiable Principle 3: Must explicitly label that maturity is approximated
    from sowing calendar / satellite climate, not fake optical NDVI crop imagery.
    """
    maturity = get_crop_maturity_proxy("Alappuzha", "rice")
    assert ("approximated from sowing calendar" in maturity["source"] or
            "calibrated with NASA POWER satellite agroclimatology" in maturity["source"])
    assert ("Non-negotiable Principle 3" in maturity["data_provenance"] or
            "NASA POWER" in maturity["data_provenance"])
    assert 0 <= maturity["estimated_maturity_pct"] <= 100
