"""
Fasal Twin - Live District Data Connector
Connects to official public APIs to fetch real-time market prices, meteorological
observations, and agricultural trends for any Indian district.

Data Sources:
1. Mandi Prices: data.gov.in Agmarknet Open Government Data API
2. Weather: Open-Meteo API (via Census/SOI district centroid coordinates)
3. Production: Local DES compendiums / OGD India statistical datasets
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
import numpy as np
import pandas as pd

# Alias mappings for state and commodity names as they appear in the public API
STATE_ALIASES = {
    "Kerala": "Keralam",
    "Keralam": "Kerala",
    # Additional mappings can be added here
}

COMMODITY_ALIASES = {
    "Rice": ["rice", "paddy", "paddy(dhan)(common)", "paddy(common)"],
    "Paddy": ["paddy", "rice", "paddy(dhan)(common)", "paddy(common)"],
    # Additional mappings can be added here
}


# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.config import get_settings

logger = logging.getLogger("fasal-twin.live-data")
DATA_DIR = repo_root / "data"
COORDINATES_FILE = DATA_DIR / "district_coordinates.csv"
DATA_GOV_IN_AGMARKNET_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"


class LiveDistrictDataConnector:
    """
    General connector for real-time market, weather, and crop signals across any Indian district.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.data_gov_in_api_key
        self._coords_df: Optional[pd.DataFrame] = None

    def _load_coordinates(self) -> pd.DataFrame:
        """Loads district centroid coordinate registry."""
        if self._coords_df is None:
            if COORDINATES_FILE.exists():
                self._coords_df = pd.read_csv(COORDINATES_FILE)
            else:
                self._coords_df = pd.DataFrame(columns=["district", "state", "lat", "lon", "source"])
        return self._coords_df

    def get_district_coordinates(self, state: str, district: str) -> Optional[Tuple[float, float, str]]:
        """
        Resolves district and state to latitude and longitude centroids.
        Returns: (lat, lon, source) or None
        """
        df = self._load_coordinates()
        if df.empty:
            return None

        # Filter by district (case-insensitive)
        sub = df[df["district"].str.lower() == district.strip().lower()]
        if sub.empty:
            # Try fuzzy/contains match
            sub = df[df["district"].str.lower().str.contains(district.strip().lower())]

        if not sub.empty:
            if state:
                state_sub = sub[sub["state"].str.lower() == state.strip().lower()]
                if not state_sub.empty:
                    sub = state_sub
            row = sub.iloc[0]
            return float(row["lat"]), float(row["lon"]), str(row["source"])

        return None

    def fetch_live_prices(self, state: str, district: str, commodity: str = "Rice") -> Dict[str, Any]:
        """
        Fetches official real-time mandi prices from data.gov.in Agmarknet resource.
        Principle 1 & 2: Returns clean no_data if not found; never substitutes state data as district data.
        """
        if not self.api_key:
            return {
                "status": "no_data",
                "reason": "DATA_GOV_IN_API_KEY is not configured.",
                "provenance": "data.gov.in Agmarknet API (Key missing)",
                "records": [],
            }

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FasalTwin/1.0"}
        url = f"https://api.data.gov.in/resource/{DATA_GOV_IN_AGMARKNET_RESOURCE}"
        
        # Resolve state using alias mapping if available
        state_clean = state.strip().title()
        # Apply alias mapping: if the provided state has a known alias, include both variants
        alias = STATE_ALIASES.get(state_clean)
        if alias:
            state_candidates = [state_clean, alias]
        else:
            state_candidates = [state_clean]
        # Additional explicit multi-name handling (e.g., Odisha/Orissa) can remain if needed
        if state_clean in ("Odisha", "Orissa"):
            state_candidates = ["Odisha", "Orissa"]
        elif state_clean in ("Chhattisgarh", "Chattisgarh"):
            state_candidates = ["Chattisgarh", "Chhattisgarh"]

        try:
            for s_cand in state_candidates:
                params = {
                    "api-key": self.api_key,
                    "format": "json",
                    "limit": "50",
                    "filters[state]": s_cand,
                    "filters[district]": district.strip().title(),
                }
                resp = requests.get(url, params=params, headers=headers, timeout=6.0)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("records", [])
                    if records:
                        target_comm = (commodity or "").lower().strip()
                        prices = []
                        arrivals = []
                        formatted_records = []
                        for r in records:
                            rec_comm_raw = str(r.get("commodity", "")).lower()
                            # Determine possible commodity alias terms for matching
                            alias_terms = COMMODITY_ALIASES.get(commodity.title(), [commodity.lower()])
                            # If any alias term appears in the record's commodity field, treat as a match
                            if not any(term in rec_comm_raw for term in alias_terms):
                                continue
                            # No further commodity filtering needed – record matches desired commodity
                            # (target_comm logic retained for backward compatibility)
                            if target_comm:
                                if target_comm not in alias_terms:
                                    continue

                            try:
                                modal_p = float(r.get("modal_price", 0.0))
                                arr_q = float(r.get("arrival_quantity", 0.0) or r.get("arrival_qty", 0.0))
                                mkt = r.get("market", "Local Mandi")
                                dt = r.get("arrival_date", str(pd.Timestamp.now().date()))
                                if modal_p > 0:
                                    prices.append(modal_p)
                                    arrivals.append(arr_q)
                                    formatted_records.append({
                                        "market": mkt,
                                        "date": dt,
                                        "commodity": r.get("commodity", commodity),
                                        "variety": r.get("variety", "Standard"),
                                        "modal_price_rs_per_quintal": modal_p,
                                        "arrival_qty_tonnes": arr_q if arr_q > 0 else None,
                                        "arrival_data_available": arr_q > 0,
                                    })
                            except (ValueError, TypeError):
                                continue

                        if formatted_records:
                            mean_p = float(np.mean(prices))
                            latest_p = float(prices[-1])
                            tot_arr = float(np.sum(arrivals))
                            return {
                                "status": "success",
                                "state": state,
                                "district": district,
                                "commodity": commodity,
                                "records_count": len(formatted_records),
                                "mean_modal_price_rs": round(mean_p, 2),
                                "latest_modal_price_rs": round(latest_p, 2),
                                "total_arrivals_tonnes": round(tot_arr, 2),
                                "records": formatted_records,
                                "provenance": "api.data.gov.in Agmarknet Real-Time Agricultural Commodity API",
                            }

            # Provide a specific explanation for Kerala rice/paddy absence
            if state_clean in ("Kerala", "Keralam") and commodity.title() in ("Rice", "Paddy"):
                # Include generic zero-record phrase plus specific explanation
                reason_msg = (
                    "Zero Agmarknet market records reported for {district}, {state} ({commodity}). "
                    "No open-market Agmarknet listings for Rice in Kerala — Kerala's paddy economy is primarily procured via Supplyco at MSP rather than traded through open mandis. See supplyco_procurement.csv for this crop instead."
                ).format(district=district, state=state, commodity=commodity)
            else:
                reason_msg = f"Zero Agmarknet market records reported for {district}, {state} ({commodity})."
            return {
                "status": "no_data",
                "state": state,
                "district": district,
                "commodity": commodity,
                "reason": reason_msg,
                "provenance": "api.data.gov.in Agmarknet Open Government Data Portal",
                "records": [],
            }
        except Exception as exc:
            logger.warning(f"data.gov.in live fetch failed for {district}: {exc}")
            return {
                "status": "no_data",
                "state": state,
                "district": district,
                "commodity": commodity,
                "reason": f"Live Agmarknet API unreachable or timed out ({str(exc)[:40]}).",
                "provenance": "api.data.gov.in Agmarknet Open Government Data Portal",
                "records": [],
            }

    def fetch_live_weather(self, state: str, district: str) -> Dict[str, Any]:
        """
        Fetches live meteorological observations and 7-day forecasts from Open-Meteo
        using verified centroid coordinates from district_coordinates.csv.
        """
        coords = self.get_district_coordinates(state, district)
        if coords is None:
            return {
                "status": "no_data",
                "state": state,
                "district": district,
                "reason": f"District coordinates not found in district_coordinates.csv for '{district}, {state}'.",
                "provenance": "Census 2011 District Centroid Registry",
            }

        lat, lon, coord_source = coords
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
            f"&timezone=auto&past_days=14&forecast_days=7"
        )

        try:
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                precip = daily.get("precipitation_sum", [])
                if precip:
                    precip_clean = [float(p) for p in precip if p is not None]
                    var_mm = float(np.var(precip_clean)) if precip_clean else 0.0
                    std_mm = float(np.std(precip_clean)) if precip_clean else 0.0
                    heavy_rain_days = sum(1 for p in precip_clean if p > 25.0)

                    surge_factor = 1.0 + min(0.65, (std_mm / 20.0) * 0.35 + (heavy_rain_days * 0.08))
                    shift_days = int(round((surge_factor - 1.0) * 28.0))

                    if std_mm < 3.0:
                        advisory = f"Rainfall in {district} is normal (Std Dev: {std_mm:.1f} mm). No major harvest disruption detected."
                    else:
                        advisory = (
                            f"Elevated rainfall variability in {district} (Std Dev: {std_mm:.1f} mm). "
                            f"Convective precipitation may cause an estimated ~{shift_days}-day arrival compression surge."
                        )

                    return {
                        "status": "success",
                        "state": state,
                        "district": district,
                        "latitude": lat,
                        "longitude": lon,
                        "rainfall_variance_mm2": round(var_mm, 2),
                        "rainfall_std_mm": round(std_mm, 2),
                        "heavy_rain_days_count": heavy_rain_days,
                        "weather_surge_multiplier": round(surge_factor, 3),
                        "estimated_harvest_shift_days": shift_days,
                        "advisory_sentence": advisory,
                        "provenance": f"Open-Meteo Live API ({lat:.4f}°N, {lon:.4f}°E via {coord_source})",
                    }

            return {
                "status": "no_data",
                "state": state,
                "district": district,
                "reason": f"Open-Meteo returned status {resp.status_code}",
                "provenance": "Open-Meteo Open Meteorological API",
            }
        except Exception as exc:
            logger.warning(f"Open-Meteo live weather fetch failed for {district}: {exc}")
            return {
                "status": "no_data",
                "state": state,
                "district": district,
                "reason": f"Live meteorological service timed out or offline ({str(exc)[:40]}).",
                "provenance": "Open-Meteo Open Meteorological API",
            }

    def fetch_live_production_trend(self, state: str, district: str, crop: str = "rice") -> Dict[str, Any]:
        """
        Retrieves crop production context for the district.
        Checks local compendium if available, otherwise reports lower-density state/district statistical baseline.
        """
        local_rice_file = DATA_DIR / "rice_area_production.csv"
        if local_rice_file.exists():
            df = pd.read_csv(local_rice_file)
            sub = df[
                (df["district"].str.lower() == district.strip().lower()) &
                (df["crop"].str.lower() == crop.strip().lower())
            ]
            if not sub.empty:
                latest = sub.sort_values(by="year").iloc[-1]
                return {
                    "status": "success",
                    "state": state,
                    "district": district,
                    "crop": crop,
                    "historical_seasons_count": len(sub),
                    "latest_season": str(latest.get("season", "Annual")),
                    "latest_year": str(latest.get("year", "Latest")),
                    "latest_production_tonnes": float(latest.get("production_tonnes", 0.0)),
                    "productivity_kg_ha": float(latest.get("productivity_kg_ha", 0.0)),
                    "density_tier": "DENSE" if len(sub) >= 20 else "SPARSE",
                    "provenance": str(latest.get("source", "Department of Economics & Statistics")),
                }

        # Baseline national/state proxy with lower density label
        return {
            "status": "limited_data",
            "state": state,
            "district": district,
            "crop": crop,
            "historical_seasons_count": 0,
            "latest_production_tonnes": 0.0,
            "density_tier": "INSUFFICIENT",
            "notice": f"Historical compendium dataset not pre-loaded for {district}, {state}.",
            "provenance": "General Directorate of Economics & Statistics / Ministry of Agriculture",
        }

    def fetch_tier_2_snapshot(self, state: str, district: str, crop: str = "rice") -> Dict[str, Any]:
        """
        Synthesizes live price, live weather, and production trend into an honest Tier 2 snapshot.
        """
        price_info = self.fetch_live_prices(state=state, district=district, commodity=crop)
        weather_info = self.fetch_live_weather(state=state, district=district)
        prod_info = self.fetch_live_production_trend(state=state, district=district, crop=crop)

        has_price = price_info.get("status") == "success"
        has_weather = weather_info.get("status") == "success"

        return {
            "capability_tier": "TIER_2_LIVE_SNAPSHOT",
            "state": state,
            "district": district,
            "crop": crop,
            "timestamp": pd.Timestamp.now().isoformat() + "Z",
            "topology_status": "NOT_MAPPED",
            "simulation_status": "UNAVAILABLE",
            "notice": (
                f"Full 4-scenario bottleneck simulation and counterfactual optimization require mapped local "
                f"logistics network topology (feeder FPOs, mandis, storage, mills), which is currently unmapped for {district}. "
                f"Real-time observational market and meteorological snapshot provided above."
            ),
            "live_prices": price_info,
            "live_weather": weather_info,
            "production_trend": prod_info,
            "provenance_summary": {
                "prices_source": price_info.get("provenance", "api.data.gov.in"),
                "weather_source": weather_info.get("provenance", "Open-Meteo"),
                "production_source": prod_info.get("provenance", "DES"),
            },
        }


def fetch_live_prices(state: str, district: str, commodity: str = "Rice") -> Dict[str, Any]:
    """Module-level helper to fetch live prices for a district."""
    connector = LiveDistrictDataConnector()
    return connector.fetch_live_prices(state=state, district=district, commodity=commodity)


def fetch_live_weather(state: str, district: str) -> Dict[str, Any]:
    """Module-level helper to fetch live weather for a district."""
    connector = LiveDistrictDataConnector()
    return connector.fetch_live_weather(state=state, district=district)


def get_live_snapshot_summary(
    state: str,
    district: str,
    crop: str = "rice",
    connector: Optional[LiveDistrictDataConnector] = None,
) -> Dict[str, Any]:
    """Module-level function returning structured Tier 2 live snapshot summary."""
    connector = connector or LiveDistrictDataConnector()
    return connector.fetch_tier_2_snapshot(state=state, district=district, crop=crop)


if __name__ == "__main__":
    connector = LiveDistrictDataConnector()
    print("Testing Palakkad (Kerala):")
    snapshot = connector.fetch_tier_2_snapshot(state="Kerala", district="Palakkad", crop="rice")
    print(f"Weather: {snapshot['live_weather'].get('status')} - {snapshot['live_weather'].get('advisory_sentence')}")
    print(f"Prices:  {snapshot['live_prices'].get('status')}")
    print(f"Tier:    {snapshot['capability_tier']}")
