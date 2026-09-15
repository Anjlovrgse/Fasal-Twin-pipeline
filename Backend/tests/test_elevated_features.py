"""
Unit tests for Step 21 elevated features:
- Minimax Regret score calculations
- Multi-district priority view ranking
- Alert-fatigue suppression thresholds
- Disagreement driver diagnosis
- Chronological backtest replay sequence
"""

import pytest
from src.counterfactual_optimizer import CounterfactualOptimizer
from src.bottleneck_detector import (
    BottleneckDetector,
    get_multi_district_priority_ranking,
    ALERT_OVERSHOOT_TONNES_THRESHOLD,
)
from src.scenario_engine import ScenarioResult
from src.confidence_gate import ConfidenceGate
from src.backtest import HistoricalBacktester


def test_regret_score_and_minimax_regret():
    """Verify that regret is computed per scenario and Minimax Regret selects a valid policy."""
    optimizer = CounterfactualOptimizer(district="Alappuzha", crop="rice")
    rec = optimizer.optimize()

    assert rec.worst_case_payoff_rs > 0
    assert rec.max_regret_rs >= 0.0
    assert rec.minimax_regret_intervention_id is not None
    assert rec.minimax_regret_value_rs >= 0.0

    # Ensure regret for optimal action in a scenario is zero
    for sc in rec.computable_scenarios:
        best_p = max(rec.scenario_outcomes[sc][i.intervention_id].net_economic_payoff_rs for i in optimizer.interventions)
        for i in optimizer.interventions:
            out = rec.scenario_outcomes[sc][i.intervention_id]
            expected_regret = max(0.0, round(best_p - out.net_economic_payoff_rs, 2))
            assert out.regret_rs == pytest.approx(expected_regret, abs=0.1)


def test_alert_fatigue_threshold_suppresses_marginal_or_low_confidence_alerts():
    """
    Test that a low-magnitude overshoot (< ALERT_OVERSHOOT_TONNES_THRESHOLD)
    or a LOW confidence assessment suppresses the active alert flag.
    """
    detector = BottleneckDetector(district="Alappuzha", crop="rice")

    # Synthetic scenario with 1 large overshoot and 1 marginal overshoot
    scenario_res = ScenarioResult(
        scenario_name="test_scenario",
        computable=True,
        status="computable",
        reason=None,
        forecast_inflow={"M1": 1300.0, "M2": 450.0},  # M1 cap=1200 (overshoot=100t), M2 cap=400 (overshoot=50t)
        effective_capacities={"M1": 1200.0, "M2": 400.0},
        data_provenance="Test",
    )

    # 1. At HIGH confidence, but overshoot is 100t (< 250t threshold) -> should NOT be active alert
    rep_high = detector.detect_scenario_bottlenecks(scenario_res, confidence_label="HIGH")
    assert rep_high.total_bottleneck_nodes == 2
    assert rep_high.active_alerts_count == 0
    assert all(b.is_active_alert is False for b in rep_high.bottlenecks)

    # 2. At HIGH confidence with overshoot 500t (>= 250t threshold) -> SHOULD be active alert
    scenario_res_large = ScenarioResult(
        scenario_name="large_overshoot",
        computable=True,
        status="computable",
        reason=None,
        forecast_inflow={"M1": 1700.0},  # cap=1200 (overshoot=500t)
        effective_capacities={"M1": 1200.0},
        data_provenance="Test",
    )
    rep_large = detector.detect_scenario_bottlenecks(scenario_res_large, confidence_label="HIGH")
    assert rep_large.active_alerts_count == 1
    assert rep_large.bottlenecks[0].is_active_alert is True

    # 3. At LOW confidence, even with 500t overshoot, active alert is suppressed to prevent fatigue
    rep_low = detector.detect_scenario_bottlenecks(scenario_res_large, confidence_label="LOW")
    assert rep_low.active_alerts_count == 0
    assert rep_low.bottlenecks[0].is_active_alert is False


def test_multi_district_priority_ranking():
    """Verify that multi-district priority ranking ranks loaded districts descending by risk score."""
    rankings = get_multi_district_priority_ranking(crop="rice")
    assert len(rankings) >= 2
    assert rankings[0]["priority_rank"] == 1
    assert rankings[0]["bottleneck_risk_score"] >= rankings[1]["bottleneck_risk_score"]
    assert "Alappuzha" in [r["district"] for r in rankings]
    assert "Kottayam" in [r["district"] for r in rankings]


def test_explain_disagreement_driver_diagnosis():
    """Verify that ConfidenceGate diagnoses the primary driver when confidence is LOW."""
    gate = ConfidenceGate()

    # Test insufficient data diagnosis
    opt = CounterfactualOptimizer(district="Idukki", crop="rice")
    rec = opt.optimize()
    conf = gate.evaluate(rec, opt.elasticity_model.get_summary())

    assert conf.confidence_label == "LOW"
    assert conf.disagreement_matrix is not None
    assert conf.disagreement_matrix.primary_disagreement_driver == "insufficient_data"
    assert "minimum threshold" in conf.disagreement_matrix.primary_disagreement_explanation


def test_chronological_backtest_replay():
    """Verify that run_backtest_replay generates an ordered timeline of weeks and states."""
    backtester = HistoricalBacktester(district="Alappuzha", crop="rice")
    replay = backtester.run_backtest_replay(target_year="2022-23")

    assert replay.status == "validated"
    assert replay.total_weeks >= 10
    assert len(replay.replay_timeline) == replay.total_weeks
    assert replay.overall_accuracy_pct > 50.0

    # Ensure chronological week numbering
    for idx, pt in enumerate(replay.replay_timeline):
        assert pt.week == idx + 1
        assert pt.predicted_state in ["NORMAL", "WARNING", "CRITICAL_BOTTLENECK"]
        assert pt.actual_state in ["NORMAL", "WARNING", "CRITICAL_BOTTLENECK"]
        assert pt.flow_predicted_tonnes >= 0
        assert pt.flow_actual_tonnes >= 0
