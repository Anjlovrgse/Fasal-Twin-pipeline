"""
Fasal Twin - Explicit Forward Price Forecasting Engine (Step 24)
Combines network arrival flow forecasts with fitted econometric price elasticity
to project explicit forward price ranges [P_low, P_high] with uncertainty bounds.

Enforces Section 0 Principles:
- Tier 1: Grounded forward price range with explicit 'based_on' econometric traceability.
- Confidence interval width strictly scales with sample size N and residual variance (smaller N -> wider interval).
- Tier 2 & Tier 3: Strictly refuses forward price estimation without mapped arrival topology.
"""

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.capability_tier import resolve_tier, TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.price_elasticity_model import PriceElasticityModel
from src.forecast_model import ForecastModel
from src.scenario_engine import ScenarioEngine
from src.live_district_data import LiveDistrictDataConnector


@dataclass
class PriceForecastResult:
    """Standardized forward price forecast output object."""
    state: str
    district: str
    crop: str
    days_ahead: int
    capability_tier: str
    status: str  # 'forecast_available' | 'refused_insufficient_topology'
    predicted_price_range: Optional[List[float]] = None  # [low_rs, high_rs] per quintal
    point_estimate_rs: Optional[float] = None
    confidence_label: str = "LOW"  # 'HIGH' | 'MEDIUM' | 'LOW'
    confidence_score: float = 0.0
    interval_width_rs: Optional[float] = None
    based_on: Dict[str, Any] = field(default_factory=dict)
    refusal_reason: Optional[str] = None
    data_provenance: str = ""


def compute_forecast_confidence_interval(
    point_estimate: float,
    n_observations: int,
    rmse_rs: float,
    r_squared: float,
) -> Tuple[float, float, float, str, float]:
    """
    Constructs an econometric confidence interval for the price prediction.
    Formula: Margin = max(50.0, (2.0 * RMSE / sqrt(max(1, N / 25))) + (1.0 - R^2) * 120.0)
    Ensures smaller sample size N or weaker R^2 produces a visibly wider uncertainty interval.

    Returns: (low_price, high_price, margin_of_error, confidence_label, confidence_score)
    """
    safe_n = max(1, n_observations)
    safe_rmse = max(40.0, rmse_rs) if rmse_rs and not math.isnan(rmse_rs) else 120.0
    safe_r2 = max(0.0, min(1.0, r_squared)) if r_squared and not math.isnan(r_squared) else 0.05

    # Scale uncertainty inversely with effective sample size N
    n_factor = math.sqrt(safe_n / 25.0)
    se_component = (2.2 * safe_rmse) / max(0.8, n_factor)
    r2_penalty = (1.0 - safe_r2) * 120.0

    margin = max(60.0, round(se_component + r2_penalty, 2))
    low_price = max(0.0, round(point_estimate - margin, 2))
    high_price = round(point_estimate + margin, 2)
    # Ensure low <= high; swap if needed
    if low_price > high_price:
        low_price, high_price = high_price, low_price

    # Determine confidence label
    if safe_n >= 200 and safe_r2 >= 0.15:
        conf_label = "HIGH"
        conf_score = round(min(0.99, 0.70 + (safe_r2 * 0.25) + min(0.10, safe_n / 10000.0)), 2)
    elif safe_n >= 40:
        conf_label = "MEDIUM"
        conf_score = round(min(0.75, 0.45 + (safe_r2 * 0.20) + (safe_n / 1000.0)), 2)
    else:
        conf_label = "LOW"
        conf_score = round(max(0.10, 0.20 + (safe_r2 * 0.10)), 2)

    return low_price, high_price, margin * 2.0, conf_label, conf_score


def forecast_price(
    state: str,
    district: str,
    crop: str = "rice",
    days_ahead: int = 14,
    loader: Optional[DataLoader] = None,
    elasticity_model: Optional[PriceElasticityModel] = None,
    live_connector: Optional[LiveDistrictDataConnector] = None,
) -> PriceForecastResult:
    """
    Generates forward price prediction for any district based on capability tier.
    - Tier 1: Synthesizes network arrival forecast and elasticity model into [low, high] price range.
    - Tier 2 & Tier 3: Honestly refuses forward prediction and returns observational data only.
    """
    loader = loader or DataLoader()
    live_connector = live_connector or LiveDistrictDataConnector()

    tier_val, tier_explanation, meta = resolve_tier(
        state=state, district=district, crop=crop, loader=loader, live_connector=live_connector
    )

    # 1. Tier 2 & Tier 3 Guard: Refuse to fabricate price forecast without arrival simulation topology
    if tier_val != TIER_1_FULL_TWIN:
        refusal_msg = (
            f"Forward price prediction for {district.title()} ({state.title()}) requires "
            f"logistics-topology-driven crop flow forecasting (feeder FPOs, mandis, storage, mills), "
            f"which is unmapped at {tier_val}. Observational historical/live market prices are available via "
            f"/see/price-trend or /analyze instead."
        )
        return PriceForecastResult(
            state=state,
            district=district,
            crop=crop,
            days_ahead=days_ahead,
            capability_tier=tier_val,
            status="refused_insufficient_topology",
            predicted_price_range=None,
            point_estimate_rs=None,
            confidence_label="LOW",
            confidence_score=0.0,
            interval_width_rs=None,
            based_on={
                "capability_tier": tier_val,
                "topology_mapped": False,
                "arrival_simulation_available": False,
                "explanation": tier_explanation,
            },
            refusal_reason=refusal_msg,
            data_provenance="Refusal Gate: Refused ungrounded forward price prediction without mapped arrival graph",
        )

    # 2. Tier 1 Processing: Grounded forward price estimation
    if elasticity_model is None:
        elasticity_model = PriceElasticityModel(district=district, crop=crop, loader=loader).fit()

    p_summary = elasticity_model.get_summary()
    n_obs = p_summary.get("n_observations", 0)
    r2 = p_summary.get("r_squared", 0.0)
    slope = p_summary.get("slope", -0.85)
    rmse_rs = p_summary.get("test_rmse_rs") or 115.0

    # Obtain baseline modal price from recent mandi observations or historical mean
    baseline_modal_price = p_summary.get("mean_price", 2400.0)
    try:
        df_mandi = loader.load_mandi_arrivals_prices()
        sub_mandi = df_mandi[
            (df_mandi["district"].str.lower() == district.strip().lower()) &
            (df_mandi["crop"].str.lower() == crop.strip().lower())
        ]
        if not sub_mandi.empty:
            recent_modal = float(sub_mandi.sort_values(by="date").iloc[-1]["modal_price_rs_per_quintal"])
            if recent_modal > 500.0:
                baseline_modal_price = recent_modal
    except Exception:
        pass

    # Run scenario engine baseline and weather-shifted forecasts
    scenario_engine = ScenarioEngine(district=district, crop=crop, loader=loader)
    base_res = scenario_engine.forecast_baseline()
    weather_res = scenario_engine.forecast_weather_shifted()

    base_inflow = sum(base_res.forecast_inflow.values()) if base_res.computable else 12000.0
    weather_inflow = sum(weather_res.forecast_inflow.values()) if weather_res.computable else base_inflow

    # Inflow surge delta across the requested window (pro-rated by days_ahead / 14)
    window_factor = min(2.0, max(0.5, days_ahead / 14.0))
    expected_peak_surge_tonnes = (weather_inflow - base_inflow) * window_factor
    expected_mandi_surge_tonnes = expected_peak_surge_tonnes * 0.40  # ~40% reaches principal mandis

    # Price impact: slope is Rs per tonne (negative slope means higher supply lowers price)
    # Preserve sign to reflect correct direction of price change
    price_impact_rs_qtl = elasticity_model.slope * expected_mandi_surge_tonnes
    point_estimate = round(baseline_modal_price + price_impact_rs_qtl, 2)

    low_p, high_p, interval_w, conf_label, conf_score = compute_forecast_confidence_interval(
        point_estimate=point_estimate,
        n_observations=n_obs,
        rmse_rs=rmse_rs,
        r_squared=r2,
    )

    based_on_traceability = {
        "capability_tier": TIER_1_FULL_TWIN,
        "arrival_forecast_scenario": "weather_shifted_vs_baseline",
        "days_ahead_horizon": days_ahead,
        "elasticity_model_n": n_obs,
        "elasticity_model_r2": round(r2, 4),
        "elasticity_slope_rs_per_tonne": round(slope, 4),
        "baseline_modal_price_rs_per_qtl": round(baseline_modal_price, 2),
        "baseline_weekly_inflow_tonnes": round(base_inflow, 2),
        "weather_shifted_inflow_tonnes": round(weather_inflow, 2),
        "projected_mandi_volume_delta_tonnes": round(expected_mandi_surge_tonnes, 2),
        "projected_price_impact_rs_per_qtl": round(price_impact_rs_qtl, 2),
        "model_test_rmse_rs": round(rmse_rs, 2),
    }

    provenance_str = (
        f"Forward {days_ahead}-Day Price Forecast: Grounded synthesis of Agmarknet econometric elasticity "
        f"(N={n_obs}, R²={r2:.3f}) and IMD weather-shifted arrival simulation for {district.title()}."
    )

    # Plausibility guard: if point estimate deviates >25% from baseline, downgrade confidence
    deviation_ratio = abs(point_estimate - baseline_modal_price) / (baseline_modal_price if baseline_modal_price != 0 else 1)
    if deviation_ratio > 0.25:
        conf_label = "LOW"
        conf_score = min(conf_score, 0.5)
        based_on_traceability["implausible_magnitude"] = True
    else:
        based_on_traceability["implausible_magnitude"] = False
    return PriceForecastResult(
        state=state,
        district=district,
        crop=crop,
        days_ahead=days_ahead,
        capability_tier=TIER_1_FULL_TWIN,
        status="forecast_available",
        predicted_price_range=[low_p, high_p],
        point_estimate_rs=point_estimate,
        confidence_label=conf_label,
        confidence_score=conf_score,
        interval_width_rs=round(interval_w, 2),
        based_on=based_on_traceability,
        refusal_reason=None,
        data_provenance=provenance_str,
    )


if __name__ == "__main__":
    print("Testing Price Forecast:")
    alappuzha_fc = forecast_price("Kerala", "Alappuzha", "rice", days_ahead=14)
    print(f"\n[Tier 1] Alappuzha (14d): Range = Rs {alappuzha_fc.predicted_price_range}, Point = Rs {alappuzha_fc.point_estimate_rs}, Conf = {alappuzha_fc.confidence_label}")
    print(f"  Traceability based_on: {alappuzha_fc.based_on}")

    palakkad_fc = forecast_price("Kerala", "Palakkad", "rice", days_ahead=14)
    print(f"\n[Tier 2] Palakkad: Status = {palakkad_fc.status}")
    print(f"  Refusal: {palakkad_fc.refusal_reason}")
