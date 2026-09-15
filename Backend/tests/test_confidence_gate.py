"""
Unit tests for confidence_gate.py verifying honest confidence labeling and disagreement matrix.
"""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.confidence_gate import ConfidenceGate, DisagreementMatrix
from src.counterfactual_optimizer import RobustRecommendation, ScenarioOutcome


def test_confidence_gate_returns_disagreement_matrix_when_scenarios_diverge():
    """
    Non-negotiable Principle: When scenarios diverge or confidence is low,
    the gate must return the structured DisagreementMatrix, not an arbitrary single pick.
    """
    # Create mock recommendation where baseline favors INT-1, but weather_shifted favors INT-2
    mock_rec = RobustRecommendation(
        district="Alappuzha",
        crop="rice",
        selected_intervention_id="INT-2",
        selected_intervention_name="Staggered Holding",
        selection_criterion="Maximin",
        worst_case_payoff_rs=50000.0,
        average_payoff_rs=120000.0,
        scenario_outcomes={
            "baseline": {
                "INT-1": ScenarioOutcome("baseline", "INT-1", "Mandi Diversion", True, 500, 100, 10, 50000, 10000, 20000, 60000, {}),
                "INT-2": ScenarioOutcome("baseline", "INT-2", "Staggered Holding", True, 400, 200, 8, 40000, 12000, 15000, 43000, {}),
            },
            "weather_shifted": {
                "INT-1": ScenarioOutcome("weather_shifted", "INT-1", "Mandi Diversion", True, 300, 400, 5, 25000, 15000, 10000, 20000, {}),
                "INT-2": ScenarioOutcome("weather_shifted", "INT-2", "Staggered Holding", True, 700, 100, 15, 70000, 15000, 30000, 85000, {}),
            },
        },
        computable_scenarios=["baseline", "weather_shifted"],
        uncomputable_scenarios=[],
        data_provenance="Test provenance",
        explanation_summary="Test summary",
    )

    # Sparse data summary (low observations)
    sparse_price_summary = {
        "district": "Alappuzha",
        "crop": "rice",
        "is_fitted": True,
        "n_observations": 35,  # Sparse
        "r_squared": 0.15,
        "slope": -0.5,
    }

    gate = ConfidenceGate()
    assessment = gate.evaluate(mock_rec, sparse_price_summary)

    # Must classify as LOW or MEDIUM with structured disagreement matrix
    assert not assessment.scenario_consensus
    assert assessment.disagreement_matrix is not None
    assert isinstance(assessment.disagreement_matrix, DisagreementMatrix)
    assert len(assessment.disagreement_matrix.competing_interventions) == 2
    assert "INT-1" in assessment.disagreement_matrix.competing_interventions
    assert "INT-2" in assessment.disagreement_matrix.competing_interventions
    assert assessment.disagreement_matrix.scenario_picks["baseline"]["intervention_id"] == "INT-1"
    assert assessment.disagreement_matrix.scenario_picks["weather_shifted"]["intervention_id"] == "INT-2"


def test_insufficient_data_produces_no_action_verdict():
    """Verifies that an unfitted or severely deficient dataset produces LOW confidence and NO_ACTION_RECOMMENDED."""
    mock_rec = RobustRecommendation(
        district="UnknownDistrict",
        crop="rice",
        selected_intervention_id="INT-0",
        selected_intervention_name="Do Nothing",
        selection_criterion="Maximin",
        worst_case_payoff_rs=0.0,
        average_payoff_rs=0.0,
        scenario_outcomes={"baseline": {}},
        computable_scenarios=["baseline"],
        uncomputable_scenarios=["weather_shifted", "adjacent_shock", "capacity_shock"],
        data_provenance="No data",
        explanation_summary="No data",
    )

    unfitted_price_summary = {
        "district": "UnknownDistrict",
        "crop": "rice",
        "is_fitted": False,
        "n_observations": 5,
        "r_squared": None,
    }

    gate = ConfidenceGate()
    assessment = gate.evaluate(mock_rec, unfitted_price_summary)

    assert assessment.confidence_label == "LOW"
    assert assessment.recommendation is None  # Never silently recommend when confidence is LOW
    assert assessment.disagreement_matrix is not None
    assert assessment.disagreement_matrix.action_verdict == "NO_ACTION_RECOMMENDED"
