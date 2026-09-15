"""
Unit tests for Live District Data Connector (Step 20 & 23).
Verifies real-time API integrations, timeout resilience, and honest no-data reporting.
"""

from unittest.mock import MagicMock, patch
import pytest
from src.live_district_data import LiveDistrictDataConnector, get_live_snapshot_summary


def test_get_district_coordinates_resolution():
    """Verifies district coordinate centroid lookup from CSV registry."""
    connector = LiveDistrictDataConnector()
    # Palakkad, Kerala
    coords = connector.get_district_coordinates(state="Kerala", district="Palakkad")
    assert coords is not None
    lat, lon, src = coords
    assert 10.0 <= lat <= 11.5
    assert 76.0 <= lon <= 77.5
    assert "Census" in src or "Survey" in src

    # Ludhiana, Punjab
    coords_pb = connector.get_district_coordinates(state="Punjab", district="Ludhiana")
    assert coords_pb is not None
    assert coords_pb[0] > 30.0

    # Non-existent district
    coords_none = connector.get_district_coordinates(state="Ocean", district="Atlantis")
    assert coords_none is None


@patch("requests.get")
def test_fetch_live_prices_success(mock_get):
    """Verifies that valid data.gov.in Agmarknet response is correctly parsed."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "records": [
            {
                "state": "Kerala",
                "district": "Palakkad",
                "market": "Palakkad Mandi",
                "commodity": "Rice",
                "modal_price": "2350",
                "arrival_quantity": "120.5",
                "arrival_date": "2026-09-10",
            },
            {
                "state": "Kerala",
                "district": "Palakkad",
                "market": "Alathur Mandi",
                "commodity": "Rice",
                "modal_price": "2400",
                "arrival_quantity": "85.0",
                "arrival_date": "2026-09-11",
            },
        ]
    }
    mock_get.return_value = mock_resp

    connector = LiveDistrictDataConnector()
    res = connector.fetch_live_prices(state="Kerala", district="Palakkad", commodity="Rice")

    assert res["status"] == "success"
    assert res["records_count"] == 2
    assert res["mean_modal_price_rs"] == 2375.0
    assert res["total_arrivals_tonnes"] == 205.5
    assert "Agmarknet" in res["provenance"]


@patch("requests.get")
def test_fetch_live_prices_empty_returns_clean_no_data(mock_get):
    """Verifies zero records return a clean no_data response without fabricating rows or substituting state data."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"records": []}
    mock_get.return_value = mock_resp

    connector = LiveDistrictDataConnector()
    res = connector.fetch_live_prices(state="Kerala", district="Idukki", commodity="Rice")

    assert res["status"] == "no_data"
    assert res["records"] == []
    assert "Zero Agmarknet market records reported" in res["reason"]
    assert "api.data.gov.in" in res["provenance"]


@patch("requests.get")
def test_fetch_live_prices_timeout_handling(mock_get):
    """Verifies network timeouts return clean no_data without raising unhandled exceptions."""
    mock_get.side_effect = Exception("Connection timed out (ReadTimeoutError)")

    connector = LiveDistrictDataConnector()
    res = connector.fetch_live_prices(state="Kerala", district="Thrissur", commodity="Rice")

    assert res["status"] == "no_data"
    assert "timed out" in res["reason"]
    assert res["records"] == []


def test_fetch_live_weather_missing_coordinates():
    """Verifies missing coordinates return clean no_data without crashing."""
    connector = LiveDistrictDataConnector()
    res = connector.fetch_live_weather(state="Fantasy", district="Narnia")

    assert res["status"] == "no_data"
    assert "coordinates not found" in res["reason"]


@patch("requests.get")
def test_fetch_live_weather_success(mock_get):
    """Verifies Open-Meteo daily precipitation signals are computed into variance and harvest surge factors."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "daily": {
            "precipitation_sum": [5.0, 12.0, 35.0, 0.0, 0.0, 4.0, 28.0, 15.0, 2.0, 0.0, 0.0, 5.0, 18.0, 8.0],
            "temperature_2m_max": [31.0] * 14,
            "temperature_2m_min": [24.0] * 14,
        }
    }
    mock_get.return_value = mock_resp

    connector = LiveDistrictDataConnector()
    res = connector.fetch_live_weather(state="Kerala", district="Palakkad")

    assert res["status"] == "success"
    assert res["rainfall_variance_mm2"] > 0
    assert res["weather_surge_multiplier"] >= 1.0
    assert "advisory_sentence" in res
    assert "Open-Meteo" in res["provenance"]


def test_tier_2_snapshot_summary_structure():
    """Verifies get_live_snapshot_summary composite response structure."""
    with patch.object(LiveDistrictDataConnector, "fetch_live_prices") as mock_p, \
         patch.object(LiveDistrictDataConnector, "fetch_live_weather") as mock_w:
        mock_p.return_value = {"status": "success", "records_count": 2, "mean_modal_price_rs": 2200.0, "provenance": "Agmarknet"}
        mock_w.return_value = {"status": "success", "weather_surge_multiplier": 1.12, "provenance": "Open-Meteo"}

        snapshot = get_live_snapshot_summary(state="Kerala", district="Palakkad", crop="rice")

        assert snapshot["capability_tier"] == "TIER_2_LIVE_SNAPSHOT"
        assert snapshot["topology_status"] == "NOT_MAPPED"
        assert snapshot["simulation_status"] == "UNAVAILABLE"
        assert "unmapped" in snapshot["notice"]
        assert "live_prices" in snapshot
        assert "live_weather" in snapshot
        assert "production_trend" in snapshot
        assert "provenance_summary" in snapshot
