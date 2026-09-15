"""
Unit tests for scenario_engine.py verifying 4-scenario dynamics and honesty guarantees.
"""

import sys
import tempfile
from pathlib import Path
import pytest
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.scenario_engine import ScenarioEngine, CAPACITY_SHOCK_REDUCTION_RATIO


def test_adjacent_shock_returns_not_computable_for_single_district():
    """
    Non-negotiable Principle: If only 1 district exists, forecast_adjacent_shock
    must return not_computable instead of inventing an arbitrary shock.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create single district mandi data
        single_dist_mandi = pd.DataFrame({
            "district": ["Alappuzha"] * 30,
            "market": ["Alappuzha Mandi"] * 30,
            "crop": ["rice"] * 30,
            "date": pd.date_range("2023-01-01", periods=30, freq="D").strftime("%Y-%m-%d"),
            "arrival_qty_tonnes": [50.0] * 30,
            "modal_price_rs_per_quintal": [2600] * 30,
            "source": ["test"] * 30,
        })
        single_dist_mandi.to_csv(tmp_path / "mandi_arrivals_prices.csv", index=False)

        # Copy over valid network and production files
        real_loader = DataLoader()
        real_loader.load_rice_area_production().to_csv(tmp_path / "rice_area_production.csv", index=False)
        real_loader.load_weather_daily().to_csv(tmp_path / "weather_daily.csv", index=False)
        real_loader.load_network_capacity().to_csv(tmp_path / "network_capacity.csv", index=False)
        real_loader.load_network_edges().to_csv(tmp_path / "network_edges.csv", index=False)

        loader = DataLoader(data_dir=str(tmp_path))
        engine = ScenarioEngine(district="Alappuzha", crop="rice", loader=loader)

        result = engine.forecast_adjacent_shock()

        assert not result.computable
        assert result.status == "not_computable"
        assert "Only one district" in result.reason
        assert "Refused to fabricate" in result.data_provenance


def test_capacity_shock_applies_documented_constant():
    """Verifies that capacity shock applies the exact 30% reduction."""
    engine = ScenarioEngine(district="Alappuzha", crop="rice")
    result = engine.forecast_capacity_shock()

    assert result.computable
    assert result.parameters["capacity_shock_reduction_ratio"] == CAPACITY_SHOCK_REDUCTION_RATIO

    # Check nominal vs effective capacity for M1
    nominal_cap = engine.graph.nodes["M1"]["capacity_tonnes"]
    effective_cap = result.effective_capacities["M1"]
    expected_effective = round(nominal_cap * (1.0 - CAPACITY_SHOCK_REDUCTION_RATIO), 2)

    assert effective_cap == expected_effective
