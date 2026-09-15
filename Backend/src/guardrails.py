"""
Fasal Twin - Reliability Guardrails (Layer 4)
Enforces physical plausibility bounds on agricultural forecasts and validates
temporal integrity for historical backtesting.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader, FasalTwinDataError

# Named validation constants
MIN_PRE_HARVEST_RECORDS: int = 24
MIN_PRE_HARVEST_WEEKS: int = 8
MAX_YIELD_BUFFER_MULTIPLIER: float = 1.35  # Max biological yield expansion above historical record
MAX_PEAK_WEEK_FRACTION: float = 0.30       # Max plausible portion of total season arriving in 1 week


class ImplausibleForecastError(FasalTwinDataError):
    """
    Raised when a forecast exceeds the biological or physical production ceiling
    derived from historical sown area and maximum yield.
    """
    def __init__(self, forecast_value: float, ceiling_value: float, district: str, crop: str, reason: str):
        self.forecast_value = forecast_value
        self.ceiling_value = ceiling_value
        self.district = district
        self.crop = crop
        self.reason = reason
        super().__init__(
            f"[ImplausibleForecastError] Forecast of {forecast_value:,.1f} tonnes for {district} {crop} "
            f"violates physical ceiling of {ceiling_value:,.1f} tonnes. Reason: {reason}"
        )


def calculate_physical_ceiling(district: str, crop: str, loader: Optional[DataLoader] = None) -> Tuple[float, float, str]:
    """
    Derives the physical weekly arrival ceiling for a district and crop
    using rice_area_production.csv historical max productivity and latest sown area.
    Returns: (max_seasonal_tonnes, max_weekly_ceiling_tonnes, provenance_str)
    """
    if loader is None:
        loader = DataLoader()

    df_rice = loader.load_rice_area_production()
    sub_df = df_rice[
        (df_rice["district"].str.lower() == district.lower()) &
        (df_rice["crop"].str.lower() == crop.lower())
    ]

    if sub_df.empty:
        # If district not found, fallback to state-level upper bound
        sub_df = df_rice[df_rice["crop"].str.lower() == crop.lower()]

    if sub_df.empty:
        raise FasalTwinDataError(f"No production records found to derive physical ceiling for {district} {crop}.")

    max_historical_prod_kg_ha = float(sub_df["productivity_kg_ha"].max())
    # Peak seasonal area (e.g. Punja in Kuttanad/Alappuzha)
    punja_df = sub_df[sub_df["season"].str.lower() == "punja"]
    if not punja_df.empty:
        current_area_ha = float(punja_df.sort_values(by="year", ascending=False).iloc[0]["area_ha"])
    else:
        current_area_ha = float(sub_df["area_ha"].max())

    # Maximum plausible seasonal production = max productivity * area * buffer
    max_prod_tonnes_ha = (max_historical_prod_kg_ha / 1000.0) * MAX_YIELD_BUFFER_MULTIPLIER
    max_seasonal_tonnes = current_area_ha * max_prod_tonnes_ha
    # Maximum plausible arrival in a single peak week
    max_weekly_ceiling = max_seasonal_tonnes * MAX_PEAK_WEEK_FRACTION

    provenance = (
        f"Ceiling derived from {district} max historical productivity ({max_historical_prod_kg_ha:,.0f} kg/ha) "
        f"× peak sown area ({current_area_ha:,.0f} ha) × {MAX_YIELD_BUFFER_MULTIPLIER}x biological buffer "
        f"× {MAX_PEAK_WEEK_FRACTION*100:.0f}% peak-week concentration = {max_weekly_ceiling:,.1f} tonnes/week."
    )

    return max_seasonal_tonnes, max_weekly_ceiling, provenance


def validate_forecast(
    forecast_tonnes_total: float,
    district: str,
    crop: str,
    loader: Optional[DataLoader] = None,
) -> float:
    """
    Checks forecast predicted arrival tonnage against maximum plausible yield.
    Raises ImplausibleForecastError if violated.
    """
    _, max_weekly_ceiling, prov = calculate_physical_ceiling(district, crop, loader)

    if forecast_tonnes_total > max_weekly_ceiling:
        raise ImplausibleForecastError(
            forecast_value=forecast_tonnes_total,
            ceiling_value=max_weekly_ceiling,
            district=district,
            crop=crop,
            reason=f"Predicted volume exceeds maximum physical ceiling ({prov})",
        )

    return max_weekly_ceiling


def validate_backtest_window(
    district: str,
    crop: str,
    year: str,
    loader: Optional[DataLoader] = None,
) -> Tuple[bool, int, str]:
    """
    Confirms there is genuinely sufficient pre-harvest data before backtesting.
    Returns: (is_valid, record_count, reason_or_prov)
    """
    if loader is None:
        loader = DataLoader()

    df_mandi = loader.load_mandi_arrivals_prices()
    sub_df = df_mandi[
        (df_mandi["district"].str.lower() == district.lower()) &
        (df_mandi["crop"].str.lower() == crop.lower())
    ]

    try:
        if "-" in year:
            start_yr = int(year.split("-")[0])
            cal_yr = start_yr + 1
        else:
            cal_yr = int(year)
    except Exception:
        cal_yr = 2023

    pre_records = sub_df[sub_df["date"].dt.year < cal_yr]
    count = len(pre_records)

    if count < MIN_PRE_HARVEST_RECORDS:
        return (
            False,
            count,
            f"Insufficient pre-harvest records ({count} found, minimum required: {MIN_PRE_HARVEST_RECORDS}).",
        )

    return (
        True,
        count,
        f"Sufficient pre-harvest window validated: {count} Agmarknet records prior to {cal_yr}.",
    )
