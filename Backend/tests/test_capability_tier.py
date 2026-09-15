"""
Unit tests for Capability Tier Classifier (Step 19 & 23).
Verifies data-driven tier resolution (Tier 1, Tier 2, Tier 3) without hardcoded district lists.
"""

from unittest.mock import MagicMock, patch
import pytest
from src.capability_tier import (
    resolve_tier,
    TIER_1_FULL_TWIN,
    TIER_2_LIVE_SNAPSHOT,
    TIER_3_INSUFFICIENT,
)
from src.data_loader import DataLoader
from src.live_district_data import LiveDistrictDataConnector


def test_tier_1_resolution_alappuzha():
    """Confirms Alappuzha resolves to Tier 1 based on mapped network topology and dense historical records."""
    tier, reason, meta = resolve_tier(state="Kerala", district="Alappuzha", crop="rice")
    assert tier == TIER_1_FULL_TWIN
    assert meta["capability_tier"] == TIER_1_FULL_TWIN
    assert meta["topology_mapped"] is True
    assert meta["simulation_available"] is True
    assert meta["network_nodes_count"] > 0
    assert meta["historical_production_records"] >= 5
    assert "Alappuzha" in reason


def test_tier_1_resolution_kottayam():
    """Confirms Kottayam resolves to Tier 1 based on local CSV rows."""
    tier, reason, meta = resolve_tier(state="Kerala", district="Kottayam", crop="rice")
    assert tier == TIER_1_FULL_TWIN
    assert meta["capability_tier"] == TIER_1_FULL_TWIN
    assert meta["topology_mapped"] is True
    assert meta["simulation_available"] is True


def test_tier_2_resolution_with_coordinates():
    """Confirms a district without local topology but with centroid coordinates resolves to Tier 2."""
    # Palakkad is in district_coordinates.csv but not in network_capacity.csv
    tier, reason, meta = resolve_tier(state="Kerala", district="Palakkad", crop="rice")
    assert tier == TIER_2_LIVE_SNAPSHOT
    assert meta["capability_tier"] == TIER_2_LIVE_SNAPSHOT
    assert meta["topology_mapped"] is False
    assert meta["simulation_available"] is False
    assert "latitude" in meta
    assert "longitude" in meta
    assert "Palakkad" in reason


def test_tier_2_resolution_with_mocked_live_market_fetch():
    """Confirms an unmapped district with live prices resolves to Tier 2 even if coordinates are missing."""
    mock_connector = MagicMock(spec=LiveDistrictDataConnector)
    mock_connector.get_district_coordinates.return_value = None
    mock_connector.fetch_live_prices.return_value = {
        "status": "success",
        "records_count": 4,
        "mean_modal_price_rs": 2150.0,
        "provenance": "data.gov.in Agmarknet API",
    }

    mock_loader = MagicMock(spec=DataLoader)
    import pandas as pd
    mock_loader.load_network_capacity.return_value = pd.DataFrame()
    mock_loader.load_rice_area_production.return_value = pd.DataFrame()

    tier, reason, meta = resolve_tier(
        state="Punjab",
        district="MockDistrict",
        crop="rice",
        loader=mock_loader,
        live_connector=mock_connector,
    )
    assert tier == TIER_2_LIVE_SNAPSHOT
    assert meta["capability_tier"] == TIER_2_LIVE_SNAPSHOT
    assert meta["topology_mapped"] is False
    assert meta["simulation_available"] is False


def test_tier_3_resolution_unknown_district():
    """Confirms an unknown district with no local data and no live feeds cleanly resolves to Tier 3."""
    mock_connector = MagicMock(spec=LiveDistrictDataConnector)
    mock_connector.get_district_coordinates.return_value = None
    mock_connector.fetch_live_prices.return_value = {"status": "no_data", "records": []}

    mock_loader = MagicMock(spec=DataLoader)
    import pandas as pd
    mock_loader.load_network_capacity.return_value = pd.DataFrame()
    mock_loader.load_rice_area_production.return_value = pd.DataFrame()

    tier, reason, meta = resolve_tier(
        state="Nowhere",
        district="Atlantis",
        crop="rice",
        loader=mock_loader,
        live_connector=mock_connector,
    )
    assert tier == TIER_3_INSUFFICIENT
    assert meta["capability_tier"] == TIER_3_INSUFFICIENT
    assert meta["topology_mapped"] is False
    assert meta["simulation_available"] is False
    assert "Insufficient data" in reason
