"""
Unit and integration tests for API hardening:
- Typed Pydantic response models
- /health/detailed multi-source check
- /priority-view multi-district dashboard
- /model-performance/{district}/{crop} model card
- /backtest/.../replay chronological sequence
- Standardized error response envelope
"""

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_api_health_detailed_returns_all_sources():
    """Verify that /health/detailed reports status for all CSVs, DB, and live weather API."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()

    assert data["system_status"] in ["healthy", "degraded"]
    assert "rice_area_production.csv" in data["data_sources"]
    assert "mandi_arrivals_prices.csv" in data["data_sources"]
    assert "weather_daily.csv" in data["data_sources"]
    assert "outcomes.db" in data["data_sources"]
    assert "open_meteo_live_api" in data["data_sources"]
    assert data["data_sources"]["rice_area_production.csv"]["record_count"] > 0
    assert data["total_sources_checked"] >= 7


def test_api_priority_view_structure():
    """Verify that /priority-view returns ranked districts with typed structure."""
    response = client.get("/priority-view?crop=rice")
    assert response.status_code == 200
    data = response.json()

    assert data["crop"] == "rice"
    assert data["total_districts"] >= 2
    assert len(data["districts_ranked"]) >= 2
    top = data["districts_ranked"][0]
    assert top["priority_rank"] == 1
    assert "bottleneck_risk_score" in top
    assert "top_bottleneck_node" in top
    assert "confidence_tier" in top


def test_api_model_performance_endpoint():
    """Verify that /model-performance/{district}/{crop} returns model card metrics."""
    response = client.get("/model-performance/Alappuzha/rice")
    assert response.status_code == 200
    data = response.json()

    assert data["district"] == "Alappuzha"
    assert data["crop"] == "rice"
    assert "price_elasticity_model" in data
    assert "flow_forecast_model" in data
    assert "limitations" in data
    assert len(data["limitations"]) >= 4

    p_model = data["price_elasticity_model"]
    assert p_model["status"] == "fitted"
    assert p_model["n_observations"] > 500
    assert len(p_model["walk_forward_folds"]) >= 3

    f_model = data["flow_forecast_model"]
    assert f_model["status"] == "fitted"
    assert f_model["latest_production_tonnes"] > 0


def test_api_backtest_replay_endpoint():
    """Verify that /backtest/{district}/{crop}/{year}/replay returns ordered chronological sequence."""
    response = client.get("/backtest/Alappuzha/rice/2022-23/replay")
    assert response.status_code == 200
    data = response.json()

    assert data["district"] == "Alappuzha"
    assert data["status"] == "validated"
    assert data["total_weeks"] >= 10
    assert len(data["replay_timeline"]) == data["total_weeks"]

    first_week = data["replay_timeline"][0]
    assert first_week["week"] == 1
    assert "flow_predicted_tonnes" in first_week
    assert "flow_actual_tonnes" in first_week
    assert "is_accurate" in first_week


def test_api_standardized_error_envelope():
    """Verify that 404 and 422 errors return the uniform {error_type, message, affected_resource, timestamp} shape."""
    # Test 404 on explainability for non-existent ID
    response = client.get("/explain/non_existent_rec_id_999")
    assert response.status_code == 404
    data = response.json()

    assert data["error_type"] == "HTTPException"
    assert "not found" in data["message"].lower()
    assert data["affected_resource"] == "/explain/non_existent_rec_id_999"
    assert "timestamp" in data

    # Test 422 on invalid query parameters
    resp_invalid = client.get("/see/price-trend/Alappuzha/Alappuzha%20Mandi/rice?days=999")
    assert resp_invalid.status_code == 422
    data_inv = resp_invalid.json()
    assert data_inv["error_type"] == "RequestValidationError"
    assert "timestamp" in data_inv
