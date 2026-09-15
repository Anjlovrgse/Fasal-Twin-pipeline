"""
Unit and integration tests for Fasal Twin Location Resolver (src/location_resolver.py).
Verifies:
1. Coordinate reverse-lookup to Census 2011 district centroids.
2. Strict distance boundary thresholding returning status='unresolved' for points far away.
3. Single-call get_location_summary for Tier 1 (Alappuzha), Tier 2 (Palakkad), and Unresolved locations.
4. FastAPI REST route GET /location-summary.
"""

import pytest
from fastapi.testclient import TestClient

from src.location_resolver import resolve_location, get_location_summary, haversine_distance_km
from src.capability_tier import TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.api import app

client = TestClient(app)


def test_haversine_distance():
    """
    Verifies Haversine distance accuracy.
    """
    # Alappuzha to Kottayam centroid is ~22 km
    dist = haversine_distance_km(9.4981, 76.3388, 9.5916, 76.5222)
    assert 20.0 < dist < 25.0


def test_resolve_location_valid_alappuzha():
    """
    Verifies that coordinates close to Alappuzha resolve accurately.
    """
    res = resolve_location(lat=9.498, lon=76.338)
    assert res["status"] == "resolved"
    assert res["district"] == "Alappuzha"
    assert res["state"] == "Kerala"
    assert res["distance_km"] < 2.0


def test_resolve_location_valid_kottayam():
    """
    Verifies that coordinates close to Kottayam resolve accurately.
    """
    res = resolve_location(lat=9.590, lon=76.520)
    assert res["status"] == "resolved"
    assert res["district"] == "Kottayam"
    assert res["state"] == "Kerala"
    assert res["distance_km"] < 2.0


def test_resolve_location_out_of_bounds_unresolved():
    """
    CRITICAL TEST: Ensures that tapping a coordinate far from any tracked district
    (e.g., 0.0, 0.0 or Arabian sea) returns status='unresolved' rather than snapping blindly.
    """
    res = resolve_location(lat=0.0, lon=0.0, max_distance_km=75.0)
    assert res["status"] == "unresolved"
    assert res["district"] is None
    assert "exceeding the 75 km resolution threshold" in res["reason"]


def test_get_location_summary_tier1_alappuzha():
    """
    Verifies composite location summary for Tier 1 flagship.
    """
    summary = get_location_summary(lat=9.50, lon=76.35, crop="Rice")
    assert summary["status"] == "resolved"
    assert summary["district"] == "Alappuzha"
    assert summary["capability_tier"] == TIER_1_FULL_TWIN
    assert summary["confidence_label"] == "HIGH"
    assert summary["sowing_advisory"] is not None
    assert summary["full_twin"] is not None
    assert summary["full_twin"]["selected_action"] is not None
    assert summary["full_twin"]["price_forecast"] is not None


def test_get_location_summary_tier2_palakkad():
    """
    Verifies composite location summary for Tier 2 district.
    """
    summary = get_location_summary(lat=10.78, lon=76.65, crop="Rice")
    assert summary["status"] == "resolved"
    assert summary["district"] == "Palakkad"
    assert summary["capability_tier"] == TIER_2_LIVE_SNAPSHOT
    assert summary["confidence_label"] == "MEDIUM"
    assert summary["sowing_advisory"] is not None
    assert summary["live_snapshot"] is not None


def test_get_location_summary_unresolved():
    """
    Verifies composite location summary for unresolvable coordinate.
    """
    summary = get_location_summary(lat=0.0, lon=0.0, crop="Rice")
    assert summary["status"] == "unresolved"
    assert summary["capability_tier"] == TIER_3_INSUFFICIENT
    assert summary["confidence_label"] == "LOW"
    assert summary["resolved_location"] is None


def test_location_summary_api_endpoint():
    """
    Verifies FastAPI GET /location-summary route.
    """
    # 1. Valid coordinates
    r_valid = client.get("/location-summary?lat=9.50&lon=76.35&crop=Rice")
    assert r_valid.status_code == 200
    d_valid = r_valid.json()
    assert d_valid["status"] == "resolved"
    assert d_valid["district"] == "Alappuzha"
    assert d_valid["capability_tier"] == "TIER_1_FULL_TWIN"

    # 2. Out of bounds coordinates
    r_invalid = client.get("/location-summary?lat=0.0&lon=0.0&crop=Rice")
    assert r_invalid.status_code == 200
    d_invalid = r_invalid.json()
    assert d_invalid["status"] == "unresolved"
    assert d_invalid["capability_tier"] == "TIER_3_INSUFFICIENT"
