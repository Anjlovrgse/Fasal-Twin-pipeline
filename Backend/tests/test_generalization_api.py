"""
Integration tests for Generalization Endpoints (/analyze and /coverage).
Verifies multi-tier routing, schema conformance, and demonstration stability.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from src.api import app


client = TestClient(app)


def test_analyze_endpoint_tier_1_alappuzha():
    """
    Verifies that querying flagship district Alappuzha returns full Tier 1 digital twin simulation
    with complete recommendation, explanation, and scheme advice.
    """
    resp = client.get("/analyze/Kerala/Alappuzha/rice")
    assert resp.status_code == 200
    data = resp.json()

    assert data["capability_tier"] == "TIER_1_FULL_TWIN"
    assert data["district"] == "Alappuzha"
    assert data["state"] == "Kerala"
    assert data["full_twin_recommendation"] is not None
    assert "recommendation_id" in data["full_twin_recommendation"]
    assert "worst_case_guaranteed_payoff_rs" in data["full_twin_recommendation"]
    assert data["explanation"] is not None
    assert data["scheme_advice"] is not None
    assert data["live_snapshot"] is None
    assert "Tier 1 Digital Twin" in data["provenance"]


def test_analyze_endpoint_tier_2_snapshot_palakkad():
    """
    Verifies that querying an unmapped district (Palakkad) returns an honest Tier 2 observational snapshot
    without attempting a simulated network flow or crashing.
    """
    with patch("src.live_district_data.LiveDistrictDataConnector.fetch_live_prices") as mock_p, \
         patch("src.live_district_data.LiveDistrictDataConnector.fetch_live_weather") as mock_w:
        mock_p.return_value = {
            "status": "success",
            "state": "Kerala",
            "district": "Palakkad",
            "commodity": "rice",
            "records_count": 3,
            "mean_modal_price_rs": 2300.0,
            "provenance": "data.gov.in Agmarknet API",
        }
        mock_w.return_value = {
            "status": "success",
            "state": "Kerala",
            "district": "Palakkad",
            "weather_surge_multiplier": 1.05,
            "advisory_sentence": "Normal rainfall pattern in Palakkad.",
            "provenance": "Open-Meteo Live API",
        }

        resp = client.get("/analyze/Kerala/Palakkad/rice")
        assert resp.status_code == 200
        data = resp.json()

        assert data["capability_tier"] == "TIER_2_LIVE_SNAPSHOT"
        assert data["district"] == "Palakkad"
        assert data["full_twin_recommendation"] is None
        assert data["live_snapshot"] is not None
        assert data["live_snapshot"]["topology_status"] == "NOT_MAPPED"
        assert data["live_snapshot"]["simulation_status"] == "UNAVAILABLE"
        assert "Tier 2 Live Snapshot" in data["provenance"]


def test_analyze_endpoint_tier_3_insufficient_atlantis():
    """
    Verifies that querying an unknown/uncovered district cleanly returns Tier 3 without crashing.
    """
    resp = client.get("/analyze/Ocean/Atlantis/rice")
    assert resp.status_code == 200
    data = resp.json()

    assert data["capability_tier"] == "TIER_3_INSUFFICIENT"
    assert data["district"] == "Atlantis"
    assert data["full_twin_recommendation"] is None
    assert data["live_snapshot"] is None
    assert data["insufficient_details"] is not None
    assert "Tier 3 Insufficiency Gate" in data["provenance"]


def test_coverage_endpoint_structure_and_counts():
    """
    Verifies /coverage returns complete registry of Tier 1 mapped twins and Tier 2 supported coordinates.
    """
    resp = client.get("/coverage")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_districts_tracked"] >= 2
    assert data["tier_1_full_twins_count"] >= 2
    assert data["tier_2_live_snapshots_count"] > 0

    t1_names = [d["district"].lower() for d in data["tier_1_districts"]]
    assert "alappuzha" in t1_names
    assert "kottayam" in t1_names

    # Check Tier 1 district schema
    alappuzha_item = next(d for d in data["tier_1_districts"] if d["district"].lower() == "alappuzha")
    assert alappuzha_item["capability_tier"] == "TIER_1_FULL_TWIN"
    assert alappuzha_item["network_nodes_count"] > 0
    assert alappuzha_item["historical_records_count"] >= 5

    # Check Tier 2 district schema
    t2_names = [d["district"].lower() for d in data["tier_2_districts"]]
    assert "palakkad" in t2_names
    assert "ludhiana" in t2_names
    palakkad_item = next(d for d in data["tier_2_districts"] if d["district"].lower() == "palakkad")
    assert palakkad_item["capability_tier"] == "TIER_2_LIVE_SNAPSHOT"
    assert palakkad_item["network_nodes_count"] == 0
