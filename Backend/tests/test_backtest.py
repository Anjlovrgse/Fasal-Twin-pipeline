"""
Unit tests for backtest.py verifying strict pre-harvest data isolation and error handling.
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
from src.backtest import HistoricalBacktester


def test_insufficient_pre_harvest_data_returns_explicit_insufficiency():
    """
    Non-negotiable Principle: Backtesting against a year without enough pre-harvest data
    must return status='insufficient_history' rather than silently improvising.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Only 5 records in pre-harvest window (min required is 24)
        sparse_mandi = pd.DataFrame({
            "district": ["Alappuzha"] * 5,
            "market": ["Alappuzha Mandi"] * 5,
            "crop": ["rice"] * 5,
            "date": ["2020-01-01", "2020-01-10", "2020-02-01", "2021-03-01", "2021-04-01"],
            "arrival_qty_tonnes": [50.0, 60.0, 45.0, 70.0, 80.0],
            "modal_price_rs_per_quintal": [2500, 2520, 2480, 2600, 2650],
            "source": ["test"] * 5,
        })
        sparse_mandi.to_csv(tmp_path / "mandi_arrivals_prices.csv", index=False)

        real_loader = DataLoader()
        real_loader.load_rice_area_production().to_csv(tmp_path / "rice_area_production.csv", index=False)
        real_loader.load_weather_daily().to_csv(tmp_path / "weather_daily.csv", index=False)
        real_loader.load_network_capacity().to_csv(tmp_path / "network_capacity.csv", index=False)
        real_loader.load_network_edges().to_csv(tmp_path / "network_edges.csv", index=False)

        loader = DataLoader(data_dir=str(tmp_path))
        backtester = HistoricalBacktester(district="Alappuzha", crop="rice", loader=loader)

        result = backtester.run_backtest(target_year="2021-22")

        assert result.status == "insufficient_history"
        assert "Insufficient temporal window" in result.reason
        assert "Refusing to report unvalidated backtest" in result.reason


def test_valid_historical_year_runs_validated_backtest():
    """Verifies that running on an adequately populated historical year yields validated status."""
    backtester = HistoricalBacktester(district="Alappuzha", crop="rice")
    result = backtester.run_backtest(target_year="2022-23")

    assert result.status == "validated"
    assert result.pre_harvest_records_count >= 24
    assert len(result.comparison_table) > 0
    assert 0.0 <= result.bottleneck_detection_precision <= 1.0
    assert 0.0 <= result.bottleneck_detection_recall <= 1.0
