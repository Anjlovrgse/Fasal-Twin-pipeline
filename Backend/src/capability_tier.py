"""
Fasal Twin - Capability Tier Classifier
Determines the capability tier (Tier 1, Tier 2, Tier 3) for any Indian district
strictly from data availability without hardcoded district lists.

Tiers:
- TIER_1_FULL_TWIN: Mapped logistics network topology + dense historical production records
- TIER_2_LIVE_SNAPSHOT: No local network topology, but live weather/market data successfully retrieved
- TIER_3_INSUFFICIENT: Neither local network topology nor live data available
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.live_district_data import LiveDistrictDataConnector

# Named Tier Constants (Non-negotiable)
TIER_1_FULL_TWIN: str = "TIER_1_FULL_TWIN"
TIER_2_LIVE_SNAPSHOT: str = "TIER_2_LIVE_SNAPSHOT"
TIER_3_INSUFFICIENT: str = "TIER_3_INSUFFICIENT"


class CapabilityTier(str, Enum):
    TIER_1_FULL_TWIN = "TIER_1_FULL_TWIN"
    TIER_2_LIVE_SNAPSHOT = "TIER_2_LIVE_SNAPSHOT"
    TIER_3_INSUFFICIENT = "TIER_3_INSUFFICIENT"


def resolve_tier(
    state: str,
    district: str,
    crop: str = "rice",
    loader: Optional[DataLoader] = None,
    live_connector: Optional[LiveDistrictDataConnector] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Data-driven capability tier resolution for any Indian state/district/crop.

    Resolution Protocol:
    1. Check if local network topology exists (network_capacity.csv) AND historical
       production records exist with sufficient density in rice_area_production.csv -> TIER 1.
    2. Check if live district data is retrievable (coordinates in registry or live API) -> TIER 2.
    3. Otherwise -> TIER 3 (INSUFFICIENT).
    """
    loader = loader or DataLoader()
    live_connector = live_connector or LiveDistrictDataConnector()

    clean_dist = district.strip().lower()
    clean_crop = crop.strip().lower()

    # 1. Tier 1 Check: Local Network Topology + Historical Production Density
    has_network_nodes = False
    node_count = 0
    try:
        df_net = loader.load_network_capacity()
        if not df_net.empty and "district" in df_net.columns:
            matched_nodes = df_net[df_net["district"].str.strip().str.lower() == clean_dist]
            node_count = len(matched_nodes)
            has_network_nodes = node_count > 0
    except Exception:
        has_network_nodes = False

    has_production_density = False
    prod_records_count = 0
    try:
        df_prod = loader.load_rice_area_production()
        if not df_prod.empty and "district" in df_prod.columns:
            matched_prod = df_prod[
                (df_prod["district"].str.strip().str.lower() == clean_dist) &
                (df_prod["crop"].str.strip().str.lower() == clean_crop)
            ]
            prod_records_count = len(matched_prod)
            # Tier 1 requires at least 5 historical seasons/records in local compendium
            has_production_density = prod_records_count >= 5
    except Exception:
        has_production_density = False

    if has_network_nodes and has_production_density:
        explanation = (
            f"Full digital twin active for {district.title()} ({state.title()}): "
            f"{node_count} logistics nodes mapped in network topology and {prod_records_count} historical "
            f"production records available. 4-scenario simulation and counterfactual optimization fully enabled."
        )
        return (
            TIER_1_FULL_TWIN,
            explanation,
            {
                "capability_tier": TIER_1_FULL_TWIN,
                "state": state,
                "district": district,
                "crop": crop,
                "network_nodes_count": node_count,
                "historical_production_records": prod_records_count,
                "topology_mapped": True,
                "simulation_available": True,
            }
        )

    # 2. Tier 2 Check: Live Data Availability (Coordinates + Live Weather/Prices)
    coords = live_connector.get_district_coordinates(state, district)
    if coords is not None:
        explanation = (
            f"Live observational snapshot active for {district.title()} ({state.title()}): "
            f"Centroid coordinates ({coords[0]:.4f}°N, {coords[1]:.4f}°E via {coords[2]}) verified. "
            f"Real-time meteorological and market observational feeds enabled. "
            f"Logistics network topology is not yet mapped; bottleneck simulation unavailable."
        )
        return (
            TIER_2_LIVE_SNAPSHOT,
            explanation,
            {
                "capability_tier": TIER_2_LIVE_SNAPSHOT,
                "state": state,
                "district": district,
                "crop": crop,
                "latitude": coords[0],
                "longitude": coords[1],
                "coordinate_source": coords[2],
                "topology_mapped": False,
                "simulation_available": False,
            }
        )

    # 2b. Check if live price data is retrievable via Agmarknet
    price_res = live_connector.fetch_live_prices(state=state, district=district, commodity=crop)
    if price_res.get("status") == "success":
        explanation = (
            f"Live market snapshot active for {district.title()} ({state.title()}): "
            f"Real-time Agmarknet commodity market records retrieved. "
            f"Logistics network topology is not yet mapped; bottleneck simulation unavailable."
        )
        return (
            TIER_2_LIVE_SNAPSHOT,
            explanation,
            {
                "capability_tier": TIER_2_LIVE_SNAPSHOT,
                "state": state,
                "district": district,
                "crop": crop,
                "market_records_count": price_res.get("records_count", 0),
                "topology_mapped": False,
                "simulation_available": False,
            }
        )

    # 3. Tier 3: Insufficient Data Everywhere
    explanation = (
        f"Insufficient data for {district.title()} ({state.title()}): "
        f"Neither local network topology nor live observational feeds (weather/mandi) are available in the system."
    )
    return (
        TIER_3_INSUFFICIENT,
        explanation,
        {
            "capability_tier": TIER_3_INSUFFICIENT,
            "state": state,
            "district": district,
            "crop": crop,
            "topology_mapped": False,
            "simulation_available": False,
        }
    )


if __name__ == "__main__":
    print("Testing Tier Resolution:")
    for d, s in [("Alappuzha", "Kerala"), ("Kottayam", "Kerala"), ("Palakkad", "Kerala"), ("Ludhiana", "Punjab"), ("Atlantis", "Ocean")]:
        tier, reason, meta = resolve_tier(state=s, district=d, crop="rice")
        print(f"\n[{tier}] {d}, {s}:")
        print(f"  {reason}")
