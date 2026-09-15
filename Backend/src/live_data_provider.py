"""
Fasal Twin - Live Data Provider (Resilience Layer)
Fetches real-time weather observations and short-term forecasts via Open-Meteo API
with strict timeout and retry policies, providing clean fallback to historical CSV data.
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.config import get_settings

# Regional district coordinates for Kerala
DISTRICT_COORDINATES: Dict[str, Tuple[float, float]] = {
    "alappuzha": (9.4981, 76.3388),
    "kottayam": (9.5916, 76.5222),
    "pathanamthitta": (9.2648, 76.7870),
    "ernakulam": (9.9816, 76.2999),
    "thrissur": (10.5276, 76.2144),
    "palakkad": (10.7867, 76.6548),
    "idukki": (9.8497, 76.9806),
    "kollam": (8.8932, 76.6141),
    "thiruvananthapuram": (8.5241, 76.9366),
    "malappuram": (11.0510, 76.0711),
    "kozhikode": (11.2588, 75.7804),
    "wayanad": (11.6854, 76.1320),
    "kannur": (11.8745, 75.3704),
    "kasaragod": (12.5102, 74.9852),
}


class LiveDataProvider:
    """
    Live external data provider with short timeouts and single-retry resilience.
    Accurately tags all outputs with provenance: "live_api".
    """

    def __init__(self, timeout_seconds: Optional[float] = None):
        self.settings = get_settings()
        self.timeout = timeout_seconds or self.settings.live_weather_timeout_seconds

    def get_live_weather(
        self,
        district: str = "Alappuzha",
        past_days: int = 14,
        forecast_days: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches current and trailing weather data from Open-Meteo.
        Returns standardized records matching weather_daily.csv shape + provenance: "live_api".
        If connection fails or times out, returns None to trigger historical fallback.
        """
        if not self.settings.live_weather_enabled:
            return None

        coords = DISTRICT_COORDINATES.get(district.lower().strip())
        if not coords:
            coords = DISTRICT_COORDINATES["alappuzha"]

        lat, lon = coords
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,rain_sum,temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Kolkata",
            "past_days": past_days,
            "forecast_days": forecast_days,
        }

        # Single retry on failure with short backoff
        for attempt in range(2):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    daily = data.get("daily", {})
                    times = daily.get("time", [])
                    precips = daily.get("precipitation_sum", [])

                    today_str = datetime.now().strftime("%Y-%m-%d")
                    records = []
                    for t_str, p_val in zip(times, precips):
                        precip_mm = round(float(p_val) if p_val is not None else 0.0, 1)
                        is_forecast = "forecast" if t_str >= today_str else "historical"
                        records.append({
                            "district": district,
                            "date": t_str,
                            "rainfall_mm": precip_mm,
                            "forecast_flag": is_forecast,
                            "source": "Open-Meteo Live API",
                        })

                    return {
                        "district": district,
                        "latitude": lat,
                        "longitude": lon,
                        "records_count": len(records),
                        "records": records,
                        "data_source": "live_open_meteo",
                        "provenance": "live_api",
                        "fetched_at": datetime.utcnow().isoformat(),
                    }

            except (requests.RequestException, Exception):
                if attempt == 0:
                    time.sleep(0.3)  # Brief backoff before single retry
                    continue

        return None


if __name__ == "__main__":
    provider = LiveDataProvider()
    live_res = provider.get_live_weather("Alappuzha")
    if live_res:
        print("Live Weather Received:")
        print(f"  District: {live_res['district']} ({live_res['latitude']}, {live_res['longitude']})")
        print(f"  Records: {live_res['records_count']} rows")
        print(f"  Provenance: {live_res['provenance']}")
        print(f"  Sample row: {live_res['records'][0]}")
    else:
        print("Live weather unavailable; fallback active.")
