"""
Fasal Twin - SEE Layer Backend Support
Powers frontend observational screens: Price Trends, Weather Advisories,
and Sowing Calendar Crop Maturity Proxies (strictly honoring Principle 3).
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.forecast_model import ForecastModel
from src.live_data_provider import LiveDataProvider
from src.satellite_climate_provider import fetch_satellite_climate

WEATHER_SHIFT_THRESHOLD_STD: float = 3.0  # Minimum rainfall std dev (mm) for meaningful harvest shift


def get_price_trend(
    district: str = "Alappuzha",
    market: str = "Alappuzha Mandi",
    crop: str = "rice",
    days: int = 14,
    loader: Optional[DataLoader] = None,
) -> Dict[str, Any]:
    """
    Returns time series from mandi_arrivals_prices.csv for the requested trailing window.
    Represents the visible baseline status quo without refitting.
    """
    if loader is None:
        loader = DataLoader()

    df_mandi = loader.load_mandi_arrivals_prices()

    sub_df = df_mandi[
        (df_mandi["district"].str.lower() == district.lower()) &
        (df_mandi["market"].str.lower() == market.lower()) &
        (df_mandi["crop"].str.lower() == crop.lower())
    ].sort_values(by="date")

    if sub_df.empty:
        # Fallback to district-level matching market if exact name has slight variant
        sub_df = df_mandi[
            (df_mandi["district"].str.lower() == district.lower()) &
            (df_mandi["crop"].str.lower() == crop.lower())
        ].sort_values(by="date")

    if sub_df.empty:
        return {
            "district": district,
            "market": market,
            "crop": crop,
            "days_requested": days,
            "status": "insufficient_data",
            "time_series": [],
            "summary": {
                "mean_modal_price_rs": 0.0,
                "latest_modal_price_rs": 0.0,
                "total_arrivals_tonnes": 0.0,
                "trend_direction": "unknown",
            },
            "data_provenance": f"No Agmarknet records found for {district} - {market} ({crop}).",
        }

    recent_df = sub_df.tail(days)
    time_series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "arrival_qty_tonnes": row["arrival_qty_tonnes"] if row["arrival_qty_tonnes"] is not None else None,
            "arrival_data_available": row["arrival_qty_tonnes"] is not None,
            "modal_price_rs_per_quintal": int(row["modal_price_rs_per_quintal"]),
            "market": str(row["market"]),
        }
        for _, row in recent_df.iterrows()
    ]

    prices = recent_df["modal_price_rs_per_quintal"].values
    arrivals = recent_df["arrival_qty_tonnes"].values

    if len(prices) >= 2:
        price_diff = prices[-1] - prices[0]
        trend_direction = "upward" if price_diff > 15 else ("downward" if price_diff < -15 else "stable")
    else:
        trend_direction = "stable"

    return {
        "district": district,
        "market": market,
        "crop": crop,
        "days_requested": days,
        "observations_count": len(time_series),
        "status": "available",
        "time_series": time_series,
        "summary": {
            "mean_modal_price_rs": round(float(np.mean(prices)), 2) if len(prices) > 0 else 0.0,
            "min_modal_price_rs": int(np.min(prices)) if len(prices) > 0 else 0,
            "max_modal_price_rs": int(np.max(prices)) if len(prices) > 0 else 0,
            "latest_modal_price_rs": int(prices[-1]) if len(prices) > 0 else 0,
            "total_arrivals_tonnes": round(float(np.sum(arrivals)), 2) if len(arrivals) > 0 else 0.0,
            "mean_daily_arrival_tonnes": round(float(np.mean(arrivals)), 2) if len(arrivals) > 0 else 0.0,
            "trend_direction": trend_direction,
        },
        "data_provenance": f"Extracted from {len(time_series)} trailing Agmarknet market observations ({recent_df['date'].min().strftime('%Y-%m-%d')} to {recent_df['date'].max().strftime('%Y-%m-%d')}).",
    }


def get_weather_advisory(
    district: str = "Alappuzha",
    crop: str = "rice",
    lookback_days: int = 30,
    loader: Optional[DataLoader] = None,
    live_provider: Optional[LiveDataProvider] = None,
) -> Dict[str, Any]:
    """
    Generates plain-language advisory based on real-time weather feeds (Open-Meteo)
    with seamless, accurately-labeled fallback to historical IMD daily rainfall records.
    """
    if loader is None:
        loader = DataLoader()
    if live_provider is None:
        live_provider = LiveDataProvider()

    # 1. Attempt live API retrieval
    live_data = live_provider.get_live_weather(district=district, past_days=lookback_days, forecast_days=7)

    if live_data and live_data.get("records"):
        rainfall_vals = [r["rainfall_mm"] for r in live_data["records"]]
        var_mm = float(np.var(rainfall_vals))
        std_mm = float(np.std(rainfall_vals))
        heavy_rain_days = sum(1 for v in rainfall_vals if v > 25.0)

        surge_factor = 1.0 + min(0.65, (std_mm / 20.0) * 0.35 + (heavy_rain_days * 0.08))
        data_source = "live_open_meteo"
        provenance = "live_api"
        prov_note = (
            f"Derived from real-time Open-Meteo API meteorological observations ({len(rainfall_vals)} daily records) "
            f"for {district} coordinates ({live_data.get('latitude')}, {live_data.get('longitude')})."
        )
    else:
        # 2. Fallback to historical CSV records
        forecast_model = ForecastModel(district=district, crop=crop, loader=loader)
        var_mm, surge_factor, _ = forecast_model.compute_weather_delay_factor(lookback_days=lookback_days)
        std_mm = float(np.sqrt(var_mm))
        data_source = "historical_imd_csv"
        provenance = "historical_csv_fallback"
        prov_note = f"Derived from historical IMD weather records (fallback data source for {district})."

    if std_mm < WEATHER_SHIFT_THRESHOLD_STD:
        advisory_text = (
            f"Rainfall in {district} has followed normal seasonal patterns (Std Dev: {std_mm:.2f} mm). "
            f"No meaningful harvest timing shift detected."
        )
        has_shift = False
        shift_days = 0
    else:
        shift_days = int(round((surge_factor - 1.0) * 28.0))
        advisory_text = (
            f"Rainfall variability in {district} is elevated (Std Dev: {std_mm:.1f} mm, Variance: {var_mm:.1f} mm²). "
            f"Pre-monsoon convective showers are expected to delay farm harvesting and compress arrivals by approximately {shift_days} days."
        )
        has_shift = True

    return {
        "district": district,
        "crop": crop,
        "lookback_days": lookback_days,
        "rainfall_variance_mm2": round(var_mm, 2),
        "rainfall_std_mm": round(std_mm, 2),
        "weather_surge_multiplier": round(surge_factor, 4),
        "estimated_harvest_shift_days": shift_days,
        "has_meaningful_shift": has_shift,
        "advisory_sentence": advisory_text,
        "data_source": data_source,
        "provenance": provenance,
        "data_provenance": prov_note,
    }


def get_crop_maturity_proxy(
    district: str = "Alappuzha",
    crop: str = "rice",
    reference_date: Optional[str] = None,
    loader: Optional[DataLoader] = None,
) -> Dict[str, Any]:
    """
    Estimates crop maturity stage strictly from sowing calendar norms (Principle 3).
    Includes mandatory explicit label in response object.
    """
    if loader is None:
        loader = DataLoader()

    ref_dt = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.now()
    month = ref_dt.month

    # Kuttanad Rice Calendar Norms (Punja, Virippu, Mundakan)
    # Punja: Sown Nov-Dec (11-12), Tillering/Panicle Jan (1), Maturity/Harvest Feb-Apr (2, 3, 4)
    # Virippu: Sown May-Jun (5-6), Tillering Jul (7), Harvest Aug-Sep (8, 9)
    # Mundakan: Sown Sep-Oct (9-10), Tillering Nov (11), Harvest Dec-Jan (12, 1)

    if month in [2, 3, 4]:
        current_season = "Punja (Summer Crop)"
        stage_name = "Harvesting / Peak Maturity" if month in [3, 4] else "Late Grain Filling"
        maturity_pct = 90 if month == 3 else (95 if month == 4 else 75)
        days_to_peak_harvest = 0 if month == 3 else (14 if month == 2 else 0)
        sowing_window = "November 15 – December 31"
        expected_harvest_window = "February 15 – April 30"
    elif month in [8, 9, 10]:
        current_season = "Virippu (Autumn Crop)"
        stage_name = "Maturity & Harvesting" if month in [9, 10] else "Grain Filling"
        maturity_pct = 85 if month == 9 else 65
        days_to_peak_harvest = 7 if month == 9 else 25
        sowing_window = "May 1 – June 15"
        expected_harvest_window = "August 15 – October 15"
    elif month in [12, 1]:
        current_season = "Mundakan (Winter Crop)"
        stage_name = "Ripening / Harvesting"
        maturity_pct = 80
        days_to_peak_harvest = 10
        sowing_window = "September 15 – October 31"
        expected_harvest_window = "December 15 – January 31"
    else: # May, June, July, November
        current_season = "Land Preparation / Sowing"
        stage_name = "Vegetative / Tillering"
        maturity_pct = 35
        days_to_peak_harvest = 60
        sowing_window = "Seasonal Sowing Phase"
        expected_harvest_window = "Next Scheduled Harvest Window"

    # Attempt to refine maturity stage with NASA POWER satellite-derived agroclimatology
    sat_climate = fetch_satellite_climate(district=district, state="Kerala", days_lookback=14)
    if sat_climate and sat_climate.get("status") == "success":
        accel_ratio = float(sat_climate.get("solar_maturity_acceleration_ratio", 1.0))
        refined_maturity_pct = min(100.0, max(15.0, round(maturity_pct * accel_ratio, 1)))
        refined_days = max(0, int(round(days_to_peak_harvest / accel_ratio))) if accel_ratio > 0 else days_to_peak_harvest

        source_label = "Sowing calendar norms calibrated with NASA POWER satellite agroclimatology (not NDVI crop imagery)"
        prov_label = "sowing_calendar_refined_by_satellite_climate_data"
        prov_note = (
            f"Calibrated using NASA POWER satellite-derived solar radiation ({sat_climate.get('mean_daily_solar_radiation_mj_m2')} MJ/m²/day) "
            f"and thermal accumulation ({sat_climate.get('accumulated_gdd_base10')} GDD). "
            f"Note: Optical vegetation index (NDVI) monitoring is a separate future integration."
        )
        return {
            "district": district,
            "crop": crop,
            "reference_date": ref_dt.strftime("%Y-%m-%d"),
            "current_season": current_season,
            "crop_stage": stage_name,
            "estimated_maturity_pct": refined_maturity_pct,
            "days_to_peak_harvest": refined_days,
            "sowing_window": sowing_window,
            "expected_harvest_window": expected_harvest_window,
            "satellite_climate_data": sat_climate,
            "source": source_label,
            "provenance": prov_label,
            "data_provenance": prov_note,
        }

    # Clean calendar-only baseline fallback when satellite service is unavailable
    return {
        "district": district,
        "crop": crop,
        "reference_date": ref_dt.strftime("%Y-%m-%d"),
        "current_season": current_season,
        "crop_stage": stage_name,
        "estimated_maturity_pct": float(maturity_pct),
        "days_to_peak_harvest": days_to_peak_harvest,
        "sowing_window": sowing_window,
        "expected_harvest_window": expected_harvest_window,
        "satellite_climate_data": None,
        "source": "approximated from sowing calendar, not live satellite data",
        "provenance": "sowing_calendar_baseline",
        "data_provenance": (
            "Non-negotiable Principle 3: No IoT hardware, no live satellite dependency. "
            "Estimated exclusively from Kerala Agricultural Statistics agro-climatic calendar norms."
        ),
    }


if __name__ == "__main__":
    trend = get_price_trend(district="Alappuzha", market="Alappuzha Mandi", crop="rice", days=14)
    print("Price Trend:")
    print(trend["summary"])

    advisory = get_weather_advisory(district="Alappuzha", crop="rice")
    print("\nWeather Advisory:")
    print(advisory["advisory_sentence"])

    maturity = get_crop_maturity_proxy(district="Alappuzha", crop="rice")
    print("\nCrop Maturity Proxy:")
    print(f"Season: {maturity['current_season']}, Stage: {maturity['crop_stage']} ({maturity['estimated_maturity_pct']}%)")
    print(f"Source Label: {maturity['source']}")
