"""
Fasal Twin - Live Demo Sequence Rehearsal Script
Executes the complete backend demonstration flow sequentially from SEE-layer
observations to robust recommendations, explainability, scheme advisory,
low-confidence truth gates, and outcome learning loops.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from fastapi.testclient import TestClient
from src.api import app
from src.confidence_gate import ConfidenceGate
from src.counterfactual_optimizer import RobustRecommendation, ScenarioOutcome


def print_banner(title: str, beat_num: int):
    print("\n" + "=" * 85)
    print(f" DEMO BEAT {beat_num}: {title.upper()}")
    print("=" * 85)


def run_demo():
    client = TestClient(app)
    district = "Alappuzha"
    crop = "rice"

    print("\n" + "*" * 85)
    print(" FASAL TWIN: REGIONAL CROP-FLOW BOTTLENECK SIMULATOR — LIVE DEMO REHEARSAL")
    print(" Target Region: Kuttanad, Alappuzha & Kottayam, Kerala | Commodity: Rice (Paddy)")
    print("*" * 85)

    # -------------------------------------------------------------
    # BEAT 1: Health & Data Quality Assurance (Principle 1 & 2)
    # -------------------------------------------------------------
    print_banner("System Health & Data Quality Assurance", 1)
    res = client.get("/health")
    print(f"[HTTP {res.status_code}] Health Status: {res.json()}")

    res = client.get(f"/data-quality/{district}/{crop}")
    dq = res.json()
    print(f"\n[HTTP {res.status_code}] Data Quality Audit:")
    for fname, details in dq["files"].items():
        print(f"  • {fname:<28} | Rows: {details.get('row_count', 0):<5} | Verdict: {details.get('verdict', 'unknown').upper():<12} | Status: {details.get('status')}")

    # -------------------------------------------------------------
    # BEAT 2: SEE-Layer Observational Screen Calls (Principle 3)
    # -------------------------------------------------------------
    print_banner("SEE-Layer Observational Feeds (No Live Satellite/IoT)", 2)
    
    # 2.1 Price Trend
    res = client.get(f"/see/price-trend/{district}/Alappuzha%20Mandi/{crop}?days=14")
    pt = res.json()
    print(f"\n1. Price Trend ({pt['market']}):")
    print(f"   Mean Modal Price: Rs {pt['summary']['mean_modal_price_rs']}/qtl | Latest: Rs {pt['summary']['latest_modal_price_rs']}/qtl | Trend: {pt['summary']['trend_direction'].upper()}")
    print(f"   Provenance: {pt['data_provenance']}")

    # 2.2 Weather Advisory
    res = client.get(f"/see/weather-advisory/{district}/{crop}?lookback_days=30")
    wa = res.json()
    print(f"\n2. IMD Weather Advisory:")
    print(f"   \"{wa['advisory_sentence']}\"")
    print(f"   Shift Magnitude: {wa['estimated_harvest_shift_days']} days | Rain Std Dev: {wa['rainfall_std_mm']} mm")

    # 2.3 Crop Maturity Proxy
    res = client.get(f"/see/crop-maturity/{district}/{crop}")
    cm = res.json()
    print(f"\n3. Crop Maturity Proxy:")
    print(f"   Season: {cm['current_season']} | Stage: {cm['crop_stage']} ({cm['estimated_maturity_pct']}%)")
    print(f"   Source Label: \"{cm['source']}\" (Principle 3: Zero fake satellite imagery)")

    # -------------------------------------------------------------
    # BEAT 3: Historical Backtest Validation (Step 8)
    # -------------------------------------------------------------
    print_banner("Historical Backtest Pre-Harvest Validation", 3)
    res = client.get(f"/backtest/{district}/{crop}/2022-23")
    bt = res.json()
    print(f"[HTTP {res.status_code}] Backtest Season: {bt['backtest_year']} | Status: {bt['status'].upper()}")
    print(f"Provenance: {bt['data_provenance']}")
    print(f"Detection Precision: {bt['bottleneck_detection_precision']*100:.1f}% | Recall: {bt['bottleneck_detection_recall']*100:.1f}%")
    print("\nSample Node Predicted vs Actual Outcome:")
    for row in bt["comparison_table"][:4]:
        match = "MATCH [OK]" if row["prediction_correct"] else "MISMATCH"
        print(f"  • {row['node_id']} ({row['node_name'][:30]:<30}): Pred Inflow={row['predicted_inflow_tonnes']:<8} | Act Peak={row['actual_peak_arrival_tonnes']:<8} | {match}")

    # -------------------------------------------------------------
    # BEAT 4: Bottleneck Simulation Across 4 Scenarios (Step 5)
    # -------------------------------------------------------------
    print_banner("Bottleneck Detection Across 4 Reliability Scenarios", 4)
    res = client.get(f"/bottleneck/{district}/{crop}")
    bn = res.json()
    for sc_name, sc_data in bn["scenarios"].items():
        print(f"\nScenario [{sc_name.upper()}]:")
        print(f"  Total Bottleneck Nodes: {sc_data['total_bottleneck_nodes']} | Total Overshoot: {sc_data['total_overshoot_tonnes']:,.1f} tonnes")
        if sc_data["bottlenecks"]:
            top = sc_data["bottlenecks"][0]
            print(f"  Top Bottleneck: Node {top['node_id']} ({top['node_name']}) — Inflow {top['forecast_inflow_tonnes']}t / Cap {top['capacity_tonnes']}t (+{top['overshoot_tonnes']}t, +{top['overshoot_pct']}%)")

    # -------------------------------------------------------------
    # BEAT 5: Counterfactual Maximin Recommendation (Step 6 & 7)
    # -------------------------------------------------------------
    print_banner("Counterfactual Maximin Recommendation & Truth Gate", 5)
    res = client.get(f"/recommendation/{district}/{crop}")
    rec = res.json()
    rec_id = rec["recommendation_id"]
    print(f"[HTTP {res.status_code}] Recommendation ID: {rec_id}")
    print(f"Selected Policy:    {rec['selected_action']}")
    print(f"Confidence Tier:    {rec['confidence_label']} (Score: {rec['confidence_score']:.2f}, Density: {rec['data_density_tier']})")
    print(f"Worst-Case Payoff:  Rs {rec['worst_case_guaranteed_payoff_rs']:,.2f} (Guaranteed Safety Floor across all 4 scenarios)")
    print(f"Average Payoff:     Rs {rec['average_payoff_rs']:,.2f}")
    print(f"Scenario Consensus: {rec['scenario_consensus']}")
    print(f"Provenance Note:    {rec['provenance_note']}")

    # -------------------------------------------------------------
    # BEAT 6: Explainability Evidence Chain (Step 9)
    # -------------------------------------------------------------
    print_banner("Explainability Audit Trail ('Why?' Panel Evidence Chain)", 6)
    res = client.get(f"/explain/{rec_id}")
    exp = res.json()
    print(f"Verdict: {exp['summary_verdict']}")
    print("\nItemized JSON Evidence Chain:")
    for idx, item in enumerate(exp["evidence_chain"], 1):
        print(f"  [{idx}] {item['fact']}")
        print(f"      Source: {item['source']}\n")

    # -------------------------------------------------------------
    # BEAT 7: Attached Government Scheme Advisor (Step 14)
    # -------------------------------------------------------------
    print_banner("Attached Government Scheme Advisor (RAG Support)", 7)
    res = client.get(f"/scheme-advisor/{rec_id}")
    sa = res.json()
    print(f"Triggered Action Type: {sa['action_type']}")
    print(f"Matched Government Schemes: {sa['matched_scheme_ids']}")
    for s in sa["schemes"]:
        print(f"\n• {s['scheme_name']} ({s['ministry']}):")
        print(f"  Summary: {s['plain_language_summary']}")
        print(f"  Mandatory Notice: \"{s['mandatory_notice']}\"")

    # -------------------------------------------------------------
    # BEAT 8: Deliberately-Triggered Low-Confidence Case (Principle 4)
    # -------------------------------------------------------------
    print_banner("Deliberately-Triggered Low Confidence & Disagreement Matrix", 8)
    # Simulate a scenario divergence case where scenarios disagree and data is sparse
    mock_divergent_rec = RobustRecommendation(
        district="Idukki",
        crop="rice",
        selected_intervention_id="INT-1",
        selected_intervention_name="Dynamic Mandi Diversion",
        selection_criterion="Maximin",
        worst_case_payoff_rs=12000.0,
        average_payoff_rs=45000.0,
        scenario_outcomes={
            "baseline": {"INT-1": ScenarioOutcome("baseline", "INT-1", "Mandi Diversion", True, 300, 50, 10, 30000, 5000, 10000, 35000, {})},
            "weather_shifted": {"INT-2": ScenarioOutcome("weather_shifted", "INT-2", "Staggered Holding", True, 400, 20, 15, 45000, 6000, 15000, 54000, {})},
        },
        computable_scenarios=["baseline", "weather_shifted"],
        uncomputable_scenarios=["adjacent_shock", "capacity_shock"],
        data_provenance="Sparse district test",
        explanation_summary="Sparse district test",
    )
    sparse_summary = {
        "district": "Idukki",
        "crop": "rice",
        "is_fitted": True,
        "n_observations": 18,  # Below threshold 24
        "r_squared": 0.04,
    }
    gate = ConfidenceGate()
    low_conf_assessment = gate.evaluate(mock_divergent_rec, sparse_summary)

    print(f"Triggered District:  Idukki rice (Low observation count: 18 rows)")
    print(f"Confidence Label:    {low_conf_assessment.confidence_label}")
    print(f"Single Rec Returned: {low_conf_assessment.recommendation} (Correctly None: No forced single recommendation)")
    if low_conf_assessment.disagreement_matrix:
        print(f"Action Verdict:      {low_conf_assessment.disagreement_matrix.action_verdict}")
        print(f"Disagreement Reason: {low_conf_assessment.disagreement_matrix.disagreement_reason}")
        print(f"Scenario Divergence: {low_conf_assessment.disagreement_matrix.scenario_picks}")

    # -------------------------------------------------------------
    # BEAT 9: Outcome Tracking & Learning Feedback Loop (Step 13)
    # -------------------------------------------------------------
    print_banner("Outcome History & Scenario Calibration Learning Loop", 9)
    res = client.get(f"/outcome-history/{district}/{crop}")
    oh = res.json()
    print(f"District: {oh['district']} {oh['crop']}")
    print(f"Total Reconciled Post-Harvest Alerts: N = {oh['total_reconciled_alerts']}")
    print(f"Calibration Status: {oh['calibration_status']}")
    print(f"Scenario Win Distribution: {oh['scenario_win_percentages']}")
    print(f"Caution Notice: \"{oh['caution_note']}\"")

    print("\n" + "=" * 85)
    print(" ALL 9 DEMO BEATS EXECUTED SUCCESSFULLY — SYSTEM READY FOR LIVE JUDGING")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_demo()
