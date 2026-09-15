"""
Fasal Twin - Final Backend System Readiness & Sign-Off Diagnostic
Executes comprehensive end-to-end verification across:
1. Environment & Configuration Integrity
2. Repository Data Loader Quality Audit
3. Tier 1 Flagship Digital Twin & Robust Decision Engine
4. Tier 2 Live Snapshot Observational Feeds
5. Tier 3 Transparent Insufficiency Gate
6. Explicit Forward Price Prediction & Uncertainty Traceability
7. NASA POWER Satellite Climate Telemetry & Fallback
8. Forward-Looking Sowing Window Advisory & Bottleneck Prevention
9. Grounded Farmer Query Layer with Strict Out-of-Scope Guardrail
10. Location Coordinate Resolver & Map Endpoint Support
11. Complete Pytest Test Suite Execution (84 tests)
"""

import sys
import os
import subprocess
from pathlib import Path

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.config import get_settings
from src.data_loader import DataLoader
from src.capability_tier import resolve_tier, TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.counterfactual_optimizer import CounterfactualOptimizer
from src.confidence_gate import ConfidenceGate
from src.explain import DecisionExplainer
from src.scheme_advisor import SchemeAdvisor
from src.live_district_data import get_live_snapshot_summary
from src.price_forecast import forecast_price
from src.satellite_climate_provider import fetch_satellite_climate
from src.sowing_advisory import recommend_sowing_window
from src.farmer_query import answer_farmer_query
from src.location_resolver import resolve_location, get_location_summary


def print_banner(text: str):
    print("\n" + "=" * 90)
    print(f"  {text}")
    print("=" * 90)


def run_readiness_check() -> bool:
    all_passed = True
    print_banner("FASAL TWIN — PRODUCTION BACKEND SYSTEM READINESS DIAGNOSTIC")

    # -------------------------------------------------------------
    # 1. Configuration & Secrets Check
    # -------------------------------------------------------------
    print("\n[CHECK 1/11] Environment & Configuration Security:")
    try:
        settings = get_settings()
        print(f"  [OK] Server Host: {settings.host}:{settings.port} | Data Dir: {settings.data_dir}")
        if settings.data_gov_in_api_key:
            print(f"  [OK] DATA_GOV_IN_API_KEY: Configured (length: {len(settings.data_gov_in_api_key)})")
        else:
            print("  [WARN] DATA_GOV_IN_API_KEY: Not set (optional, non-blocking fallback active)")
        if settings.weather_api_key:
            print("  [OK] WEATHER_API_KEY: Configured")
        else:
            print("  [INFO] WEATHER_API_KEY: Not set (Open-Meteo and IMD fallbacks active)")
    except Exception as exc:
        print(f"  [FAIL] Configuration loading error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 2. Data Loader & Repository Quality Audit
    # -------------------------------------------------------------
    print("\n[CHECK 2/11] Data Quality & Density Audit:")
    try:
        loader = DataLoader()
        quality = loader.data_quality_report(district="Alappuzha", crop="rice")
        for fname, frep in quality["files"].items():
            print(f"  [OK] {fname:<30}: {frep['row_count']} rows | Verdict: {frep['verdict']}")
    except Exception as exc:
        print(f"  [FAIL] Data quality audit failed: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 3. Tier 1 Flagship Path (Alappuzha Digital Twin)
    # -------------------------------------------------------------
    print("\n[CHECK 3/11] Tier 1 Flagship Simulation (Alappuzha Rice):")
    try:
        tier, reason, meta = resolve_tier("Kerala", "Alappuzha", "rice")
        assert tier == TIER_1_FULL_TWIN, f"Expected Tier 1, got {tier}"

        optimizer = CounterfactualOptimizer(district="Alappuzha", crop="rice")
        rec = optimizer.optimize()

        gate = ConfidenceGate()
        conf = gate.evaluate(rec, optimizer.elasticity_model.get_summary())

        explainer = DecisionExplainer(district="Alappuzha", crop="rice")
        exp = explainer.explain(rec, conf, optimizer.elasticity_model.get_summary())

        action_type = "staggered_holding" if "INT-2" in rec.selected_intervention_id else "redirect_mandi"
        advisor = SchemeAdvisor()
        advice = advisor.advise_for_recommendation(action_type=action_type)

        print(f"  [OK] Capability Tier: {tier}")
        print(f"  [OK] Selected Action: {rec.selected_intervention_name}")
        print(f"  [OK] Worst-Case Guaranteed Payoff: Rs {rec.worst_case_payoff_rs:,.2f}")
        print(f"  [OK] Confidence Label: {conf.confidence_label} (Score: {conf.confidence_score})")
        print(f"  [OK] Evidence Chain Items: {len(exp.evidence_chain)} facts with provenance citations")
        print(f"  [OK] Attached Schemes: {advice['matched_scheme_ids']} (with mandatory Krishi Bhavan notice)")
    except Exception as exc:
        print(f"  [FAIL] Tier 1 pipeline error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 4. Tier 2 Live Observational Snapshot Path (Palakkad)
    # -------------------------------------------------------------
    print("\n[CHECK 4/11] Tier 2 Live Snapshot Path (Palakkad):")
    try:
        tier2, reason2, meta2 = resolve_tier("Kerala", "Palakkad", "rice")
        assert tier2 == TIER_2_LIVE_SNAPSHOT, f"Expected Tier 2, got {tier2}"

        snapshot = get_live_snapshot_summary("Kerala", "Palakkad", "rice")
        print(f"  [OK] Capability Tier: {tier2}")
        print(f"  [OK] Topology Status: {snapshot['topology_status']} | Simulation: {snapshot['simulation_status']}")
        print(f"  [OK] Weather Signal: {snapshot['live_weather'].get('status')}")
        print(f"  [OK] Honest Notice: {snapshot['notice'][:70]}...")
    except Exception as exc:
        print(f"  [FAIL] Tier 2 pipeline error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 5. Tier 3 Transparent Insufficiency Path (Atlantis)
    # -------------------------------------------------------------
    print("\n[CHECK 5/11] Tier 3 Transparent Insufficiency Path (Atlantis):")
    try:
        tier3, reason3, meta3 = resolve_tier("Ocean", "Atlantis", "rice")
        assert tier3 == TIER_3_INSUFFICIENT, f"Expected Tier 3, got {tier3}"
        print(f"  [OK] Capability Tier: {tier3}")
        print(f"  [OK] Insufficiency Reason: {reason3}")
    except Exception as exc:
        print(f"  [FAIL] Tier 3 pipeline error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 6. Explicit Forward Price Prediction & Uncertainty Traceability
    # -------------------------------------------------------------
    print("\n[CHECK 6/11] Explicit Forward Price Range Forecasting:")
    try:
        fc_t1 = forecast_price("Kerala", "Alappuzha", "rice", days_ahead=14)
        print(f"  [OK] Tier 1 Alappuzha Price Range: Rs {fc_t1.predicted_price_range} (Point: Rs {fc_t1.point_estimate_rs})")
        print(f"  [OK] Traceability 'based_on' Keys: {list(fc_t1.based_on.keys())}")
        print(f"  [OK] Confidence Label: {fc_t1.confidence_label} | Width: Rs {fc_t1.interval_width_rs}")

        fc_t2 = forecast_price("Kerala", "Palakkad", "rice", days_ahead=14)
        assert fc_t2.status == "refused_insufficient_topology"
        print(f"  [OK] Tier 2 Palakkad Forward Price Refusal: [REFUSED] - {fc_t2.refusal_reason[:65]}...")
    except Exception as exc:
        print(f"  [FAIL] Price forecast check error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 7. NASA POWER Satellite Climate Telemetry
    # -------------------------------------------------------------
    print("\n[CHECK 7/11] NASA POWER Satellite Climate Provider:")
    try:
        sat = fetch_satellite_climate("Alappuzha", "Kerala", days_lookback=14)
        if sat.get("status") == "success":
            print(f"  [OK] Status: SUCCESS | Real NASA POWER satellite telemetry active")
            print(f"  [OK] Solar Radiation: {sat.get('mean_daily_solar_radiation_mj_m2')} MJ/m²/day | Temp: {sat.get('mean_temperature_c')} °C")
            print(f"  [OK] Accumulated GDD: {sat.get('accumulated_gdd_base10')} | Provenance: {sat.get('provenance')}")
        else:
            print(f"  [INFO] Status: UNAVAILABLE ({sat.get('reason')}) | Seamless calendar fallback active")
    except Exception as exc:
        print(f"  [FAIL] Satellite climate check error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 8. Sowing Window Advisory & Bottleneck Prevention (Step 28)
    # -------------------------------------------------------------
    print("\n[CHECK 8/11] Forward-Looking Sowing Window Advisory:")
    try:
        sow_t1 = recommend_sowing_window("Kerala", "Alappuzha", "rice", target_season="punja")
        print(f"  [OK] Tier 1 Window: {sow_t1['recommended_sowing_window']['start_date']} to {sow_t1['recommended_sowing_window']['end_date']}")
        print(f"  [OK] Bottleneck Risk Reduction: {sow_t1['bottleneck_risk_reduction_pct']}% vs nominal clustered peak")
        print(f"  [OK] Confidence: {sow_t1['confidence_label']} (Score: {sow_t1['confidence_score']})")

        sow_t2 = recommend_sowing_window("Kerala", "Palakkad", "rice")
        assert sow_t2["optimization_status"] == "unavailable_unmapped_topology"
        print(f"  [OK] Tier 2 Palakkad Calendar Fallback: [CLEAN FALLBACK] - {sow_t2['notice'][:60]}...")
    except Exception as exc:
        print(f"  [FAIL] Sowing advisory check error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 9. Grounded Farmer Query Layer & Guardrail (Step 29)
    # -------------------------------------------------------------
    print("\n[CHECK 9/11] Grounded Farmer Query Layer & Strict Guardrail:")
    try:
        # Grounded Query
        q_in = answer_farmer_query("Kerala", "Alappuzha", "rice", "What is the 14-day price forecast?")
        assert q_in["out_of_scope"] is False
        print(f"  [OK] Grounded Price Query: {q_in['answer'][:75]}...")

        # Out of Scope Query
        q_out = answer_farmer_query("Kerala", "Alappuzha", "rice", "What pesticide kills stem borer?")
        assert q_out["out_of_scope"] is True
        print(f"  [OK] Out-of-Scope Pesticide Guardrail: [REJECTED (out_of_scope=True)] - {q_out['answer'][:60]}...")
    except Exception as exc:
        print(f"  [FAIL] Farmer query layer check error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 10. Location Coordinate Resolver & Map Endpoint Support (Step 30)
    # -------------------------------------------------------------
    print("\n[CHECK 10/11] Location Coordinate Resolver & Map Support:")
    try:
        loc_res = resolve_location(lat=9.498, lon=76.338)
        assert loc_res["status"] == "resolved" and loc_res["district"] == "Alappuzha"
        print(f"  [OK] Centroid Match: {loc_res['district']} ({loc_res['state']}) at distance {loc_res['distance_km']} km")

        loc_out = resolve_location(lat=0.0, lon=0.0, max_distance_km=75.0)
        assert loc_out["status"] == "unresolved"
        print(f"  [OK] Out-of-Bounds Rejection: [UNRESOLVED] - {loc_out['reason'][:60]}...")

        loc_sum = get_location_summary(lat=9.50, lon=76.35, crop="Rice")
        assert loc_sum["capability_tier"] == TIER_1_FULL_TWIN
        print(f"  [OK] Map Summary Payload: Tier 1 Twin attached with Price: Rs {loc_sum['full_twin']['price_forecast']['predicted_modal_price_rs_per_qtl']}")
    except Exception as exc:
        print(f"  [FAIL] Location resolver check error: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # 11. Full Pytest Test Suite
    # -------------------------------------------------------------
    print("\n[CHECK 11/11] Automated Pytest Test Suite Execution:")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "tests/"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if res.returncode == 0:
            lines = [l for l in res.stdout.split("\n") if "passed" in l]
            summary_line = lines[-1] if lines else "All tests passed"
            print(f"  [OK] Test Suite Result: {summary_line.strip()}")
        else:
            print(f"  [FAIL] Pytest encountered errors:\n{res.stdout[-400:]}")
            all_passed = False
    except Exception as exc:
        print(f"  [FAIL] Could not run pytest: {exc}")
        all_passed = False

    # -------------------------------------------------------------
    # Final Sign-off Verdict
    # -------------------------------------------------------------
    print_banner(
        "DIAGNOSTIC VERDICT: ALL SYSTEMS OPERATIONAL — BACKEND READY FOR FRONTEND"
        if all_passed else
        "DIAGNOSTIC VERDICT: FAILURES DETECTED — BACKEND REQUIRES REMEDIATION"
    )
    return all_passed


if __name__ == "__main__":
    success = run_readiness_check()
    sys.exit(0 if success else 1)
