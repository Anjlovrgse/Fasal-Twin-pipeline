"""
Unit tests for guardrails.py verifying biological yield ceilings and implausible forecast rejection.
"""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.guardrails import (
    validate_forecast,
    calculate_physical_ceiling,
    validate_backtest_window,
    ImplausibleForecastError,
    MIN_PRE_HARVEST_RECORDS,
)
from src.scenario_engine import ScenarioEngine


def test_guardrail_rejects_implausible_forecast():
    """
    Verifies that a forecast exceeding physical yield ceilings raises ImplausibleForecastError.
    """
    _, max_ceiling, _ = calculate_physical_ceiling("Alappuzha", "rice")

    # Construct an absurd forecast (10x of ceiling)
    absurd_forecast = max_ceiling * 5.0

    with pytest.raises(ImplausibleForecastError) as exc_info:
        validate_forecast(absurd_forecast, "Alappuzha", "rice")

    assert "violates physical ceiling" in str(exc_info.value)
    assert exc_info.value.forecast_value == absurd_forecast


def test_scenario_engine_marks_implausible_forecast_as_rejected():
    """
    Verifies that when a forecast violates physical ceilings, scenario_engine
    catches ImplausibleForecastError and marks scenario status as 'rejected_implausible'.
    """
    engine = ScenarioEngine(district="Alappuzha", crop="rice")

    # Artificially override forecast_model baseline to return 100,000 tonnes/week (exceeding ceiling)
    engine.forecast_model.get_seasonal_baseline_volume = lambda season="punja": (100000.0, "Mock absurd forecast")

    result = engine.forecast_baseline()

    assert not result.computable
    assert result.status == "rejected_implausible"
    assert "violates physical ceiling" in result.reason or "exceeds maximum" in result.reason
    assert "Guardrails Layer 4" in result.data_provenance


def test_validate_backtest_window_thresholds():
    """Verifies that validate_backtest_window checks the MIN_PRE_HARVEST_RECORDS threshold."""
    is_valid, count, msg = validate_backtest_window("Alappuzha", "rice", "2022-23")
    assert is_valid
    assert count >= MIN_PRE_HARVEST_RECORDS
