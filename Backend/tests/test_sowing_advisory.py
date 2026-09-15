"""
Unit and integration tests for Fasal Twin Sowing Window Advisory (src/sowing_advisory.py).
Verifies:
1. Tier 1 Alappuzha network topology bottleneck-avoidance optimization.
2. Sowing date clustering with predicted peak harvest window scores worse than spreading the load.
3. Tier 2 and Tier 3 clean degradation to calendar-only baseline.
4. FastAPI REST route GET /sowing-advisory/{state}/{district}/{crop}.
"""

import pytest
from fastapi.testclient import TestClient

from src.sowing_advisory import recommend_sowing_window
from src.capability_tier import TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.api import app

client = TestClient(app)


def test_tier1_alappuzha_sowing_optimization():
    """
    Verifies that Tier 1 (Alappuzha) optimizes sowing window using network topology,
    and proves that a clustered sowing date scores worse than an early staggered window.
    """
    adv = recommend_sowing_window(state="Kerala", district="Alappuzha", crop="rice", target_season="punja")

    assert adv["capability_tier"] == TIER_1_FULL_TWIN
    assert adv["optimization_status"] == "optimized_via_network_topology"
    assert adv["confidence_label"] == "HIGH"
    assert adv["confidence_score"] >= 0.85
    assert adv["bottleneck_risk_reduction_pct"] > 50.0

    candidates = adv["candidate_windows_evaluated"]
    assert len(candidates) == 3

    # Find the nominal clustered window and the early staggered window
    nominal_win = next(c for c in candidates if "Nominal" in c["window_name"])
    early_win = next(c for c in candidates if "Early" in c["window_name"])

    # Core Logic Test: Clustered sowing creates peak overshoot and scores lower
    assert nominal_win["optimization_score"] < early_win["optimization_score"], (
        f"Expected early window score ({early_win['optimization_score']}) to exceed "
        f"clustered nominal window score ({nominal_win['optimization_score']})"
    )
    assert nominal_win["simulated_peak_overshoot_tonnes"] > early_win["simulated_peak_overshoot_tonnes"]
    assert nominal_win["harvest_cluster_overlap_risk"] == "CRITICAL_HIGH"
    assert early_win["harvest_cluster_overlap_risk"] == "LOW"

    # Evidence chain should have specific citations
    assert len(adv["evidence_chain"]) >= 2
    assert any("EARAS" in item["source"] or "Compendium" in item["source"] or "Scenario" in item["source"] for item in adv["evidence_chain"])


def test_tier2_palakkad_calendar_fallback():
    """
    Verifies that Tier 2 (Palakkad) honestly degrades to calendar baseline with unmapped topology notice.
    """
    adv = recommend_sowing_window(state="Kerala", district="Palakkad", crop="rice")

    assert adv["capability_tier"] == TIER_2_LIVE_SNAPSHOT
    assert adv["optimization_status"] == "unavailable_unmapped_topology"
    assert "not currently mapped" in adv["notice"]
    assert adv["bottleneck_risk_reduction_pct"] == 0.0
    assert adv["confidence_label"] == "MEDIUM"


def test_tier3_atlantis_insufficient():
    """
    Verifies that Tier 3 (Atlantis) returns transparent insufficiency.
    """
    adv = recommend_sowing_window(state="Ocean", district="Atlantis", crop="rice")

    assert adv["capability_tier"] == TIER_3_INSUFFICIENT
    assert adv["optimization_status"] == "unavailable_unmapped_topology"
    assert adv["confidence_label"] == "LOW"


def test_sowing_advisory_api_endpoint():
    """
    Verifies FastAPI GET /sowing-advisory endpoint contract.
    """
    response = client.get("/sowing-advisory/Kerala/Alappuzha/rice?target_season=punja")
    assert response.status_code == 200
    data = response.json()

    assert data["district"] == "Alappuzha"
    assert data["capability_tier"] == "TIER_1_FULL_TWIN"
    assert "recommended_sowing_window" in data
    assert "nominal_sowing_window" in data
    assert data["bottleneck_risk_reduction_pct"] > 0
