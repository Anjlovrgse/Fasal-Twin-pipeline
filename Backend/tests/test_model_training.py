"""
Unit tests for Step 19 model training discipline:
- Temporal train/test splitting
- Walk-forward temporal cross-validation
- Model serialization and deserialization via joblib
"""

import tempfile
from pathlib import Path
import pytest
import pandas as pd
from src.price_elasticity_model import PriceElasticityModel
from src.forecast_model import ForecastModel


def test_price_elasticity_temporal_split():
    """Verify that train/test split is strictly chronological without lookahead bias."""
    model = PriceElasticityModel(district="Alappuzha", crop="rice")
    model.fit(train_test_split_date="2023-12-31")

    assert model.is_fitted is True
    assert model.n_train > 0
    assert model.n_test > 0
    assert model.n_train + model.n_test == model.n_observations
    assert model.cutoff_date == "2023-12-31"
    assert model.r_squared > 0.0
    assert model.slope < 0.0  # Increased volume depresses open market price
    assert model.test_mae > 0.0


def test_price_elasticity_walk_forward_validation():
    """Verify that multi-fold walk-forward validation produces honest multi-season metrics."""
    model = PriceElasticityModel(district="Alappuzha", crop="rice")
    model.fit()

    wf = model.walk_forward_metrics
    assert wf.get("status") == "completed"
    assert wf.get("n_folds", 0) >= 3
    assert len(wf.get("folds", [])) >= 3

    for fold in wf["folds"]:
        assert "train_window" in fold
        assert "test_window" in fold
        assert fold["n_train"] >= 24
        assert fold["test_mae"] > 0.0


def test_price_elasticity_joblib_persistence():
    """Verify that PriceElasticityModel saves and loads accurately via joblib."""
    model = PriceElasticityModel(district="Alappuzha", crop="rice").fit()

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "test_price_model.joblib"
        model.save(filepath=save_path)
        assert save_path.exists()

        loaded = PriceElasticityModel.load(save_path)
        assert loaded.is_fitted is True
        assert loaded.district == model.district
        assert loaded.crop == model.crop
        assert loaded.n_observations == model.n_observations
        assert loaded.slope == pytest.approx(model.slope, rel=1e-5)
        assert loaded.r_squared == pytest.approx(model.r_squared, rel=1e-5)


def test_forecast_model_walk_forward_and_persistence():
    """Verify that ForecastModel runs walk-forward validation and serializes cleanly."""
    fmodel = ForecastModel(district="Alappuzha", crop="rice").fit(cutoff_year="2022-23", season="punja")

    assert fmodel.is_fitted is True
    assert fmodel.latest_production_tonnes > 0
    assert fmodel.baseline_weekly_tonnes > 0
    assert fmodel.test_mape_pct > 0.0

    wf = fmodel.walk_forward_metrics
    assert wf.get("status") == "completed"
    assert len(wf.get("folds", [])) >= 3

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "test_forecast_model.joblib"
        fmodel.save(filepath=save_path)
        assert save_path.exists()

        loaded_f = ForecastModel.load(save_path)
        assert loaded_f.is_fitted is True
        assert loaded_f.district == fmodel.district
        assert loaded_f.latest_production_tonnes == pytest.approx(fmodel.latest_production_tonnes, rel=1e-5)
        assert loaded_f.test_mape_pct == pytest.approx(fmodel.test_mape_pct, rel=1e-5)
