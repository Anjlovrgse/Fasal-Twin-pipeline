"""
Unit tests for outcome_tracker.py verifying logging, reconciliation, and honest sample size reporting.
"""

import sys
import tempfile
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.outcome_tracker import OutcomeTracker


def test_outcome_tracker_logging_and_reconciliation():
    """Verifies that an alert is logged and reconciled against observed arrivals."""
    tracker = OutcomeTracker(db_path=Path(":memory:"))

    rec_id = "rec-test-unit-1"
    tracker.log_alert(
        recommendation_id=rec_id,
        district="Alappuzha",
        crop="rice",
        chosen_action="Staggered Holding",
        chosen_intervention_id="INT-2",
        confidence_label="HIGH",
        confidence_score=0.95,
        scenario_outputs={
            "baseline": {"forecast_inflow": {"M1": 7000.0, "M3": 6000.0}},
            "weather_shifted": {"forecast_inflow": {"M1": 8500.0, "M3": 7200.0}},
        }
    )

    # Reconcile with actual arrivals close to weather_shifted
    rec_res = tracker.reconcile_outcome(
        recommendation_id=rec_id,
        actual_node_arrivals={"M1": 8400.0, "M3": 7100.0}
    )

    assert rec_res["closest_scenario"] == "weather_shifted"
    assert rec_res["scenario_maes"]["weather_shifted"] < rec_res["scenario_maes"]["baseline"]

    # Summary check
    summary = tracker.scenario_accuracy_summary(district="Alappuzha", crop="rice")
    assert summary["total_reconciled_alerts"] == 1
    assert summary["calibration_status"] == "INSUFFICIENT_SAMPLE_SIZE"
    assert "Caution: Sample size N is too small" in summary["caution_note"]
