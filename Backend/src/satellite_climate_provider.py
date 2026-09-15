"""
Fasal Twin - NASA POWER Satellite Agroclimatology Provider (Step 25)
Retrieves satellite/reanalysis-derived solar radiation, thermal flux, and moisture
parameters from NASA POWER (power.larc.nasa.gov) by district coordinates.

Precise Scoping & Honesty Contract:
- This is satellite-derived agro-meteorological CLIMATE data.
- This is NOT direct optical/SAR vegetation index (NDVI) crop canopy imagery.
- Provenance is explicitly tagged as 'nasa_power_satellite'.
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
import numpy as np
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.live_district_data import LiveDistrictDataConnector

logger = logging.getLogger("fasal-twin.satellite-climate")


class SatelliteClimateProvider:
    """
    Integrates NASA POWER Daily Agroclimatology API for real-time solar radiation,
    temperature flux, and accumulated thermal units.
    """

    def __init__(self, live_connector: Optional[LiveDistrictDataConnector] = None):
        self.live_connector = live_connector or LiveDistrictDataConnector()

    def fetch_satellite_climate(
        self,
        district: str,
        state: Optional[str] = None,
        days_lookback: int = 14,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves satellite-derived agroclimate parameters from NASA POWER.
        Returns clean 'unavailable' dictionary on network failure or missing coordinates.
        """
        state_str = state or "Kerala"
        coords = self.live_connector.get_district_coordinates(state_str, district)
        if coords is None:
            return {
                "status": "unavailable",
                "district": district,
                "state": state_str,
                "reason": f"District coordinates for '{district}' not found in registry.",
                "provenance": "NASA POWER Satellite Agroclimatology (Coordinates unmapped)",
            }

        lat, lon, coord_src = coords

        # Format dates for NASA POWER (YYYYMMDD)
        # Note: NASA POWER has ~2-3 days data processing latency; request trailing window ending 3 days ago
        now = datetime.utcnow()
        if not end_date:
            end_dt = now - timedelta(days=3)
            end_str = end_dt.strftime("%Y%m%d")
        else:
            end_str = end_date.replace("-", "")

        if not start_date:
            start_dt = (now - timedelta(days=days_lookback + 3))
            start_str = start_dt.strftime("%Y%m%d")
        else:
            start_str = start_date.replace("-", "")

        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN,T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR",
            "community": "AG",
            "longitude": f"{lon:.4f}",
            "latitude": f"{lat:.4f}",
            "start": start_str,
            "end": end_str,
            "format": "JSON",
        }

        try:
            resp = requests.get(url, params=params, timeout=4.0)
            if resp.status_code == 200:
                payload = resp.json()
                properties = payload.get("properties", {})
                param_data = properties.get("parameter", {})

                sw_down = param_data.get("ALLSKY_SFC_SW_DWN", {})
                t2m = param_data.get("T2M", {})
                t2m_max = param_data.get("T2M_MAX", {})
                t2m_min = param_data.get("T2M_MIN", {})
                rh2m = param_data.get("RH2M", {})
                precip = param_data.get("PRECTOTCORR", {})

                # Filter valid numbers (NASA POWER uses -999.0 for missing)
                sw_vals = [v for v in sw_down.values() if v is not None and v > -900]
                t2m_vals = [v for v in t2m.values() if v is not None and v > -900]
                rh_vals = [v for v in rh2m.values() if v is not None and v > -900]
                precip_vals = [v for v in precip.values() if v is not None and v > -900]

                if sw_vals and t2m_vals:
                    mean_sw = float(np.mean(sw_vals))
                    mean_t = float(np.mean(t2m_vals))
                    mean_rh = float(np.mean(rh_vals)) if rh_vals else 75.0
                    tot_precip = float(np.sum(precip_vals)) if precip_vals else 0.0

                    # Calculate Growing Degree Days (Base 10°C) accumulated over window
                    gdd_accum = sum(max(0.0, v - 10.0) for v in t2m_vals)

                    # Solar radiation acceleration factor: Normal tropical paddy baseline ~18.5 MJ/m2/day
                    solar_maturity_acceleration_ratio = round(min(1.20, max(0.85, mean_sw / 18.5)), 3)

                    return {
                        "status": "success",
                        "district": district,
                        "state": state_str,
                        "latitude": lat,
                        "longitude": lon,
                        "days_observed": len(sw_vals),
                        "mean_daily_solar_radiation_mj_m2": round(mean_sw, 2),
                        "mean_temperature_c": round(mean_t, 2),
                        "relative_humidity_pct": round(mean_rh, 1),
                        "total_precipitation_mm": round(tot_precip, 2),
                        "accumulated_gdd_base10": round(gdd_accum, 1),
                        "solar_maturity_acceleration_ratio": solar_maturity_acceleration_ratio,
                        "climate_data_type": "satellite_derived_agro_meteorology",
                        "optical_vegetation_imagery_note": "NASA POWER provides satellite-derived solar/climate flux; optical NDVI crop canopy imagery is a future roadmap integration.",
                        "provenance": f"NASA POWER Satellite Agroclimatology ({lat:.4f}°N, {lon:.4f}°E via {coord_src})",
                    }

            return {
                "status": "unavailable",
                "district": district,
                "state": state_str,
                "reason": f"NASA POWER returned HTTP {resp.status_code}",
                "provenance": "NASA POWER Satellite Agroclimatology",
            }
        except Exception as exc:
            logger.warning(f"NASA POWER fetch failed for {district}: {exc}")
            return {
                "status": "unavailable",
                "district": district,
                "state": state_str,
                "reason": f"NASA POWER service timeout or network error ({str(exc)[:40]}).",
                "provenance": "NASA POWER Satellite Agroclimatology (Offline/Timeout)",
            }


def fetch_satellite_climate(
    district: str,
    state: Optional[str] = "Kerala",
    days_lookback: int = 14,
) -> Dict[str, Any]:
    """Module-level convenience function for fetching NASA POWER satellite climate data."""
    provider = SatelliteClimateProvider()
    return provider.fetch_satellite_climate(district=district, state=state, days_lookback=days_lookback)


if __name__ == "__main__":
    print("Testing NASA POWER Satellite Climate Provider:")
    sat = fetch_satellite_climate("Alappuzha", "Kerala", days_lookback=14)
    print(f"Status: {sat['status']}")
    if sat["status"] == "success":
        print(f"Mean Solar Radiation: {sat['mean_daily_solar_radiation_mj_m2']} MJ/m2/day")
        print(f"Mean Temp: {sat['mean_temperature_c']} °C | Accumulated GDD: {sat['accumulated_gdd_base10']}")
        print(f"Solar Maturity Ratio: {sat['solar_maturity_acceleration_ratio']}")
        print(f"Provenance: {sat['provenance']}")
    else:
        print(f"Reason: {sat.get('reason')}")
