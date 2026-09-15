"""
Unit and integration tests for NASA POWER Satellite Climate Provider (Step 25).
Verifies agro-meteorological telemetry extraction, crop maturity refinement, and fallback handling.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.satellite_climate_provider import SatelliteClimateProvider, fetch_satellite_climate
from src.see_layer import get_crop_maturity_proxy
from src.api import app


client = TestClient(app)


@patch("requests.get")
def test_nasa_power_satellite_climate_success(mock_get):
    """Verifies that NASA POWER agroclimatology response is parsed into solar and thermal metrics."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {"20260901": 19.5, "20260902": 21.0, "20260903": 18.0},
                "T2M": {"20260901": 28.5, "20260902": 29.0, "20260903": 27.5},
                "RH2M": {"20260901": 78.0, "20260902": 75.0, "20260903": 82.0},
                "PRECTOTCORR": {"20260901": 4.5, "20260902": 0.0, "20260903": 12.0},
            }
        }
    }
    mock_get.return_value = mock_resp

    provider = SatelliteClimateProvider()
    res = provider.fetch_satellite_climate("Alappuzha", "Kerala", days_lookback=3)

    assert res["status"] == "success"
    assert res["district"] == "Alappuzha"
    assert res["mean_daily_solar_radiation_mj_m2"] == 19.5
    assert res["mean_temperature_c"] == 28.33
    assert res["accumulated_gdd_base10"] > 50.0
    assert res["solar_maturity_acceleration_ratio"] > 1.0
    assert "NASA POWER" in res["provenance"]
    assert "optical NDVI" in res["optical_vegetation_imagery_note"]


def test_nasa_power_satellite_climate_missing_coordinates():
    """Verifies missing district coordinates return clean unavailable without raising exceptions."""
    provider = SatelliteClimateProvider()
    res = provider.fetch_satellite_climate("Atlantis", "Ocean")

    assert res["status"] == "unavailable"
    assert "not found" in res["reason"]


@patch("requests.get")
def test_nasa_power_satellite_climate_timeout(mock_get):
    """Verifies network timeouts return clean unavailable status."""
    mock_get.side_effect = Exception("NASA POWER connection timed out")
    provider = SatelliteClimateProvider()
    res = provider.fetch_satellite_climate("Alappuzha", "Kerala")

    assert res["status"] == "unavailable"
    assert "timeout or network error" in res["reason"]


@patch("src.see_layer.fetch_satellite_climate")
def test_crop_maturity_refined_by_satellite_data(mock_sat):
    """Verifies that successful satellite climate telemetry refines crop maturity and upgrades provenance."""
    mock_sat.return_value = {
        "status": "success",
        "district": "Alappuzha",
        "mean_daily_solar_radiation_mj_m2": 21.2,
        "accumulated_gdd_base10": 240.0,
        "solar_maturity_acceleration_ratio": 1.10,
        "provenance": "NASA POWER Satellite Agroclimatology",
    }

    res = get_crop_maturity_proxy(district="Alappuzha", crop="rice", reference_date="2026-03-15")

    assert res["satellite_climate_data"] is not None
    assert res["provenance"] == "sowing_calendar_refined_by_satellite_climate_data"
    assert "NASA POWER" in res["source"]
    assert res["estimated_maturity_pct"] >= 90.0


@patch("src.see_layer.fetch_satellite_climate")
def test_crop_maturity_fallback_on_satellite_failure(mock_sat):
    """Verifies that satellite failure seamlessly falls back to calendar-only baseline without failing."""
    mock_sat.return_value = {"status": "unavailable", "reason": "NASA POWER API offline"}

    res = get_crop_maturity_proxy(district="Alappuzha", crop="rice", reference_date="2026-03-15")

    assert res["satellite_climate_data"] is None
    assert res["provenance"] == "sowing_calendar_baseline"
    assert res["source"] == "approximated from sowing calendar, not live satellite data"
    assert "Non-negotiable Principle 3" in res["data_provenance"]


def test_api_satellite_climate_endpoint():
    """Verifies GET /see/satellite-climate/{district} returns structured response."""
    with patch("src.api.fetch_satellite_climate") as mock_sat:
        mock_sat.return_value = {
            "status": "success",
            "district": "Alappuzha",
            "state": "Kerala",
            "latitude": 9.49,
            "longitude": 76.33,
            "days_observed": 14,
            "mean_daily_solar_radiation_mj_m2": 19.8,
            "mean_temperature_c": 28.5,
            "relative_humidity_pct": 77.0,
            "total_precipitation_mm": 35.0,
            "accumulated_gdd_base10": 259.0,
            "solar_maturity_acceleration_ratio": 1.07,
            "climate_data_type": "satellite_derived_agro_meteorology",
            "provenance": "NASA POWER Satellite Agroclimatology",
        }

        resp = client.get("/see/satellite-climate/Alappuzha?days_lookback=14")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["district"] == "Alappuzha"
        assert data["mean_daily_solar_radiation_mj_m2"] == 19.8
        assert "optical NDVI" in data["optical_vegetation_imagery_note"]
