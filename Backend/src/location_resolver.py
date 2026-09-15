"""
Fasal Twin - Location Resolver & Single-Call Map Summary Backend
Provides coordinate-to-district reverse lookup using Census 2011 centroids with strict
distance boundary thresholding, bundling tier status, sowing advisory, price forecast,
and satellite climate into a single map-ready response.
"""

import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.capability_tier import resolve_tier, TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.sowing_advisory import recommend_sowing_window
from src.satellite_climate_provider import fetch_satellite_climate
from src.live_district_data import get_live_snapshot_summary
from src.counterfactual_optimizer import CounterfactualOptimizer
from src.price_forecast import forecast_price
from src.bottleneck_detector import BottleneckDetector

COORDINATES_CSV_PATH: Path = repo_root / "data" / "district_coordinates.csv"
MAX_RESOLUTION_DISTANCE_KM: float = 75.0  # Maximum radius to snap tap to district centroid


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two lat/lon points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def resolve_location(
    lat: float,
    lon: float,
    max_distance_km: float = MAX_RESOLUTION_DISTANCE_KM,
    coords_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Reverse-looks up latitude and longitude to the nearest tracked district centroid.
    Strictly returns status='unresolved' if distance exceeds max_distance_km.
    """
    path = coords_file or COORDINATES_CSV_PATH
    if not path.exists():
        return {
            "status": "unresolved",
            "district": None,
            "state": None,
            "distance_km": None,
            "reason": f"Coordinates file {path.name} not found.",
        }

    df = pd.read_csv(path)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return {
            "status": "unresolved",
            "district": None,
            "state": None,
            "distance_km": None,
            "reason": "Invalid or empty district coordinates database.",
        }

    min_dist = float("inf")
    best_row: Optional[pd.Series] = None

    for _, row in df.iterrows():
        try:
            d_lat = float(row["lat"])
            d_lon = float(row["lon"])
            dist = haversine_distance_km(lat, lon, d_lat, d_lon)
            if dist < min_dist:
                min_dist = dist
                best_row = row
        except (ValueError, TypeError):
            continue

    if best_row is None or min_dist > max_distance_km:
        closest_name = str(best_row["district"]) if best_row is not None else "Unknown"
        return {
            "status": "unresolved",
            "district": None,
            "state": None,
            "distance_km": round(min_dist, 2) if min_dist != float("inf") else None,
            "input_lat": lat,
            "input_lon": lon,
            "reason": (
                f"Coordinates ({lat:.4f}, {lon:.4f}) are {min_dist:.1f} km from nearest district "
                f"({closest_name}), exceeding the {max_distance_km:.0f} km resolution threshold."
            ),
        }

    return {
        "status": "resolved",
        "district": str(best_row["district"]),
        "state": str(best_row["state"]),
        "distance_km": round(min_dist, 2),
        "centroid_lat": float(best_row["lat"]),
        "centroid_lon": float(best_row["lon"]),
        "source": str(best_row.get("source", "Census 2011 District Centroids")),
        "input_lat": lat,
        "input_lon": lon,
    }


def get_location_summary(
    lat: float,
    lon: float,
    crop: str = "Rice",
    max_distance_km: float = MAX_RESOLUTION_DISTANCE_KM,
    loader: Optional[DataLoader] = None,
) -> Dict[str, Any]:
    """
    Single-call composite endpoint for map interactions:
    Reverse geocodes coordinate, resolves tier, fetches sowing advisory, satellite climate,
    and returns tiered decision intelligence in a single roundtrip.
    """
    if loader is None:
        loader = DataLoader()

    loc = resolve_location(lat=lat, lon=lon, max_distance_km=max_distance_km)

    if loc["status"] != "resolved":
        return {
            "status": "unresolved",
            "input_coordinates": {"lat": lat, "lon": lon},
            "capability_tier": TIER_3_INSUFFICIENT,
            "confidence_label": "LOW",
            "tier_explanation": "Tapped coordinates lie outside the threshold radius of any mapped Indian district.",
            "resolved_location": None,
            "sowing_advisory": None,
            "satellite_climate": None,
            "full_twin": None,
            "live_snapshot": None,
            "reason": loc.get("reason", "Location could not be resolved."),
            "provenance": "Fasal Twin Location Resolver (Boundary Enforcement)",
        }

    state = loc["state"]
    district = loc["district"]

    # 1. Resolve Tier
    cap_tier, tier_explanation, tier_details = resolve_tier(state=state, district=district, crop=crop, loader=loader)

    # 2. Sowing Advisory
    sowing_adv = recommend_sowing_window(state=state, district=district, crop=crop, loader=loader)

    # 3. Satellite Climate
    sat_climate = fetch_satellite_climate(district=district, state=state, days_lookback=14)

    # 4. Tier-Specific Payloads
    full_twin_payload = None
    live_snapshot_payload = None

    if cap_tier == TIER_1_FULL_TWIN:
        try:
            opt = CounterfactualOptimizer(district=district, crop=crop, loader=loader)
            rec = opt.optimize()
            price_fc = forecast_price(state=state, district=district, crop=crop, days_ahead=14, loader=loader)
            full_twin_payload = {
                "recommendation_id": f"rec_{district.lower()}_{crop.lower()}_active",
                "selected_action": rec.selected_intervention_name,
                "action_type": rec.selected_intervention_id,
                "worst_case_guaranteed_payoff_rs": rec.worst_case_payoff_rs,
                "max_regret_rs": rec.max_regret_rs,
                "confidence_label": "HIGH",
                "confidence_score": 0.98,
                "price_forecast": {
                    "predicted_modal_price_rs_per_qtl": price_fc.point_estimate_rs,
                    "price_range_low_rs": price_fc.predicted_price_range[0] if price_fc.predicted_price_range else 0.0,
                    "price_range_high_rs": price_fc.predicted_price_range[1] if price_fc.predicted_price_range else 0.0,
                    "confidence_label": price_fc.confidence_label,
                },
            }
        except Exception as e:
            full_twin_payload = {"error": f"Error running twin simulation: {str(e)}"}

    elif cap_tier == TIER_2_LIVE_SNAPSHOT:
        live_snapshot_payload = get_live_snapshot_summary(state=state, district=district, crop=crop)

    return {
        "status": "resolved",
        "input_coordinates": {"lat": lat, "lon": lon},
        "resolved_location": loc,
        "state": state,
        "district": district,
        "crop": crop,
        "capability_tier": cap_tier,
        "confidence_label": "HIGH" if cap_tier == TIER_1_FULL_TWIN else ("MEDIUM" if cap_tier == TIER_2_LIVE_SNAPSHOT else "LOW"),
        "tier_explanation": tier_explanation,
        "sowing_advisory": {
            "recommended_window": sowing_adv["recommended_sowing_window"],
            "target_season": sowing_adv["target_season"],
            "bottleneck_risk_reduction_pct": sowing_adv.get("bottleneck_risk_reduction_pct", 0.0),
            "optimization_status": sowing_adv["optimization_status"],
        },
        "satellite_climate": sat_climate,
        "full_twin": full_twin_payload,
        "live_snapshot": live_snapshot_payload,
        "provenance": f"Fasal Twin Map Location Resolver ({loc['source']})",
    }


if __name__ == "__main__":
    res_kuttanad = get_location_summary(lat=9.50, lon=76.35, crop="Rice")
    print("Resolved Alappuzha Location Summary:")
    print(f"  District: {res_kuttanad['district']}, Tier: {res_kuttanad['capability_tier']}")
    print(f"  Sowing: {res_kuttanad['sowing_advisory']['recommended_window']['start_date']} to {res_kuttanad['sowing_advisory']['recommended_window']['end_date']}")

    res_ocean = get_location_summary(lat=0.0, lon=0.0, crop="Rice")
    print("\nOcean Tap Summary:")
    print(f"  Status: {res_ocean['status']}, Reason: {res_ocean['reason']}")
