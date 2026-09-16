"""
Unit and integration tests for Forward Price Forecast Engine (Step 24 & 26).
Verifies uncertainty interval scaling, econometric traceability (based_on), and refusal logic.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.price_forecast import (
    forecast_price,
    compute_forecast_confidence_interval,
    PriceForecastResult,
)
from src.api import app


client = TestClient(app)


def test_tier_1_price_forecast_alappuzha():
    """Confirms Tier 1 district returns explicit price range and complete based_on traceability."""
    res = forecast_price(state="Kerala", district="Alappuzha", crop="rice", days_ahead=14)

    assert res.capability_tier == "TIER_1_FULL_TWIN"
    assert res.status == "forecast_available"
    assert res.predicted_price_range is not None
    assert len(res.predicted_price_range) == 2
    low_p, high_p = res.predicted_price_range
    assert low_p < high_p
    assert res.point_estimate_rs is not None
    assert low_p <= res.point_estimate_rs <= high_p
    assert res.confidence_label in ["HIGH", "MEDIUM", "LOW"]
    assert res.interval_width_rs > 0

    # Traceability checks
    based_on = res.based_on
    assert based_on["capability_tier"] == "TIER_1_FULL_TWIN"
    assert "elasticity_model_n" in based_on
    assert based_on["elasticity_model_n"] > 500
    assert "elasticity_model_r2" in based_on
    assert "baseline_modal_price_rs_per_qtl" in based_on
    assert "projected_price_impact_rs_per_qtl" in based_on

    # A LOW confidence label must never be silent: the guardrail only downgrades to
    # LOW when it has also flagged the underlying magnitude as implausible, so the
    # reason for distrust is always explicit and traceable, never implicit.
    if res.confidence_label == "LOW":
        assert based_on.get("implausible_magnitude") is True


def test_confidence_interval_width_scales_inversely_with_n():
    """
    Confirms that sample size N directly controls uncertainty bounds:
    A small sample size N=30 produces a wider confidence interval than a dense sample N=1500.
    """
    point = 2500.0
    rmse = 110.0
    r2 = 0.25

    # Dense dataset (e.g. Alappuzha N=1563)
    low_dense, high_dense, width_dense, label_dense, score_dense = compute_forecast_confidence_interval(
        point_estimate=point,
        n_observations=1563,
        rmse_rs=rmse,
        r_squared=r2,
    )

    # Sparse dataset (e.g. N=30)
    low_sparse, high_sparse, width_sparse, label_sparse, score_sparse = compute_forecast_confidence_interval(
        point_estimate=point,
        n_observations=30,
        rmse_rs=rmse,
        r_squared=0.05,
    )

    assert width_sparse > width_dense
    assert score_dense > score_sparse
    assert label_dense == "HIGH"
    assert label_sparse == "LOW"


def test_tier_2_price_forecast_refusal_palakkad():
    """Confirms Tier 2 district strictly refuses forward price prediction without mapped arrival graph."""
    res = forecast_price(state="Kerala", district="Palakkad", crop="rice", days_ahead=14)

    assert res.capability_tier == "TIER_2_LIVE_SNAPSHOT"
    assert res.status == "refused_insufficient_topology"
    assert res.predicted_price_range is None
    assert res.point_estimate_rs is None
    assert res.refusal_reason is not None
    assert "unmapped" in res.refusal_reason or "requires" in res.refusal_reason


def test_tier_3_price_forecast_refusal_atlantis():
    """Confirms Tier 3 unresolvable district refuses forward price prediction without crashing."""
    res = forecast_price(state="Ocean", district="Atlantis", crop="rice", days_ahead=14)

    assert res.capability_tier == "TIER_3_INSUFFICIENT"
    assert res.status == "refused_insufficient_topology"
    assert res.predicted_price_range is None
    assert res.refusal_reason is not None


def test_api_price_forecast_endpoint_tier_1():
    """Verifies GET /price-forecast/{state}/{district}/{crop} for Alappuzha."""
    resp = client.get("/price-forecast/Kerala/Alappuzha/rice?days_ahead=14")
    assert resp.status_code == 200
    data = resp.json()

    assert data["capability_tier"] == "TIER_1_FULL_TWIN"
    assert data["status"] == "forecast_available"
    assert data["predicted_price_range"] is not None
    assert data["point_estimate_rs"] is not None
    assert "based_on" in data
    assert "elasticity_model_n" in data["based_on"]


def test_api_price_forecast_endpoint_tier_2_refusal():
    """Verifies GET /price-forecast/{state}/{district}/{crop} for Palakkad."""
    resp = client.get("/price-forecast/Kerala/Palakkad/rice?days_ahead=14")
    assert resp.status_code == 200
    data = resp.json()

    assert data["capability_tier"] == "TIER_2_LIVE_SNAPSHOT"
    assert data["status"] == "refused_insufficient_topology"
    assert data["predicted_price_range"] is None
    assert data["refusal_reason"] is not None
