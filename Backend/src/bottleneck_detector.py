"""
Fasal Twin - Bottleneck Detector
Identifies and ranks logistics nodes where forecast crop inflows exceed capacity
across all reliability scenarios, enforcing alert-fatigue suppression thresholds
and providing multi-district priority rankings.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import networkx as nx

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.network_model import load_network
from src.scenario_engine import ScenarioEngine, ScenarioResult
from src.capability_tier import resolve_tier, TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT

# Named Alert Fatigue Threshold Constant (Non-negotiable requirement)
# Overshoots below 250 tonnes or at LOW confidence are suppressed as non-critical advisory
ALERT_OVERSHOOT_TONNES_THRESHOLD: float = 250.0


@dataclass
class BottleneckNode:
    """Represents a specific bottleneck node detected in the network."""
    node_id: str
    node_name: str
    node_type: str
    district: str
    capacity_tonnes: float
    forecast_inflow_tonnes: float
    overshoot_tonnes: float
    overshoot_pct: float
    utilization_ratio: float
    rank: int
    is_active_alert: bool = True  # True if overshoot >= ALERT_OVERSHOOT_TONNES_THRESHOLD


@dataclass
class ScenarioBottleneckReport:
    """Bottleneck detection results for a specific scenario."""
    scenario_name: str
    computable: bool
    status: str
    reason: Optional[str]
    bottlenecks: List[BottleneckNode]
    total_bottleneck_nodes: int
    active_alerts_count: int
    total_overshoot_tonnes: float
    max_utilization_ratio: float
    data_provenance: str


class BottleneckDetector:
    """
    Evaluates scenario forecasts against logistics capacity constraints
    with alert-fatigue filtering.
    """

    def __init__(
        self,
        district: str = "Alappuzha",
        crop: str = "rice",
        loader: Optional[DataLoader] = None,
        graph: Optional[nx.DiGraph] = None,
        alert_threshold_tonnes: float = ALERT_OVERSHOOT_TONNES_THRESHOLD,
    ):
        self.district = district
        self.crop = crop
        self.loader = loader or DataLoader()
        self.graph = graph or load_network(district=district, loader=self.loader)
        self.scenario_engine = ScenarioEngine(district=district, crop=crop, loader=self.loader, graph=self.graph)
        self.alert_threshold_tonnes = alert_threshold_tonnes

    def detect_scenario_bottlenecks(
        self,
        scenario_res: ScenarioResult,
        confidence_label: str = "HIGH",
    ) -> ScenarioBottleneckReport:
        """
        Detects and ranks bottlenecks for a single scenario result.
        Filters active alerts using the alert-fatigue threshold and confidence tier.
        """
        if not scenario_res.computable:
            return ScenarioBottleneckReport(
                scenario_name=scenario_res.scenario_name,
                computable=False,
                status=scenario_res.status,
                reason=scenario_res.reason,
                bottlenecks=[],
                total_bottleneck_nodes=0,
                active_alerts_count=0,
                total_overshoot_tonnes=0.0,
                max_utilization_ratio=0.0,
                data_provenance=scenario_res.data_provenance,
            )

        inflows = scenario_res.forecast_inflow
        capacities = scenario_res.effective_capacities

        overshoots: List[Dict[str, Any]] = []
        max_util = 0.0

        for node_id, inflow in inflows.items():
            cap = capacities.get(node_id, 1.0)
            if cap <= 0:
                continue
            util_ratio = inflow / cap
            max_util = max(max_util, util_ratio)

            if inflow > cap:
                node_data = self.graph.nodes.get(node_id, {})
                overshoot_tonnes = inflow - cap
                overshoot_pct = (overshoot_tonnes / cap) * 100.0

                # Alert Fatigue Filter:
                # Active alert iff overshoot >= threshold AND confidence != 'LOW'
                is_active = (
                    overshoot_tonnes >= self.alert_threshold_tonnes and
                    confidence_label.upper() in ["HIGH", "MEDIUM"]
                )

                overshoots.append({
                    "node_id": node_id,
                    "node_name": node_data.get("node_name", node_id),
                    "node_type": node_data.get("node_type", "unknown"),
                    "district": node_data.get("district", self.district),
                    "capacity_tonnes": round(cap, 2),
                    "forecast_inflow_tonnes": round(inflow, 2),
                    "overshoot_tonnes": round(overshoot_tonnes, 2),
                    "overshoot_pct": round(overshoot_pct, 2),
                    "utilization_ratio": round(util_ratio, 4),
                    "is_active_alert": is_active,
                })

        # Rank strictly by overshoot_tonnes descending
        overshoots.sort(key=lambda x: x["overshoot_tonnes"], reverse=True)

        ranked_bottlenecks = [
            BottleneckNode(
                node_id=item["node_id"],
                node_name=item["node_name"],
                node_type=item["node_type"],
                district=item["district"],
                capacity_tonnes=item["capacity_tonnes"],
                forecast_inflow_tonnes=item["forecast_inflow_tonnes"],
                overshoot_tonnes=item["overshoot_tonnes"],
                overshoot_pct=item["overshoot_pct"],
                utilization_ratio=item["utilization_ratio"],
                rank=idx + 1,
                is_active_alert=item["is_active_alert"],
            )
            for idx, item in enumerate(overshoots)
        ]

        total_overshoot = sum(b.overshoot_tonnes for b in ranked_bottlenecks)
        active_alerts = sum(1 for b in ranked_bottlenecks if b.is_active_alert)

        return ScenarioBottleneckReport(
            scenario_name=scenario_res.scenario_name,
            computable=True,
            status="computable",
            reason=None,
            bottlenecks=ranked_bottlenecks,
            total_bottleneck_nodes=len(ranked_bottlenecks),
            active_alerts_count=active_alerts,
            total_overshoot_tonnes=round(total_overshoot, 2),
            max_utilization_ratio=round(max_util, 4),
            data_provenance=scenario_res.data_provenance,
        )

    def detect_all_bottlenecks(self, confidence_label: str = "HIGH") -> Dict[str, ScenarioBottleneckReport]:
        """Runs bottleneck detection across all 4 scenarios."""
        scenario_results = self.scenario_engine.run_all_scenarios()
        reports: Dict[str, ScenarioBottleneckReport] = {}
        for sc_name, sc_res in scenario_results.items():
            reports[sc_name] = self.detect_scenario_bottlenecks(sc_res, confidence_label=confidence_label)
        return reports


def get_multi_district_priority_ranking(
    crop: str = "rice",
    districts: Optional[List[str]] = None,
    loader: Optional[DataLoader] = None,
) -> List[Dict[str, Any]]:
    """
    Computes a multi-district bottleneck severity ranking for the regional officer's priority view.
    Ranks districts descending by composite bottleneck risk score.
    """
    loader = loader or DataLoader()
    if districts is None:
        # Load unique districts from production data
        try:
            df_rice = loader.load_rice_area_production()
            districts = sorted(df_rice["district"].unique().tolist())
        except Exception:
            districts = ["Alappuzha", "Kottayam"]

    ranking_list: List[Dict[str, Any]] = []

    for dist in districts:
        try:
            detector = BottleneckDetector(district=dist, crop=crop, loader=loader)
            reports = detector.detect_all_bottlenecks()
            base_rep = reports.get("baseline")

            if not base_rep or not base_rep.computable:
                # Thin data / non-computable district
                ranking_list.append({
                    "district": dist,
                    "crop": crop,
                    "bottleneck_risk_score": 0.0,
                    "total_overshoot_tonnes": 0.0,
                    "active_alerts_count": 0,
                    "max_utilization_ratio": 0.0,
                    "top_bottleneck_node": "None",
                    "top_bottleneck_overshoot_tonnes": 0.0,
                    "confidence_tier": "INSUFFICIENT",
                    "computable": False,
                    "reason": base_rep.reason if base_rep else "No baseline data available",
                })
                continue

            # Calculate total district node capacity
            total_cap = sum(b.capacity_tonnes for b in base_rep.bottlenecks)
            if total_cap <= 0:
                total_cap = 5000.0

            top_node = base_rep.bottlenecks[0].node_name if base_rep.bottlenecks else "None"
            top_overshoot = base_rep.bottlenecks[0].overshoot_tonnes if base_rep.bottlenecks else 0.0

            tier_val, _, _ = resolve_tier(state="Kerala", district=dist, crop=crop, loader=loader)
            conf_tier = "HIGH" if tier_val == TIER_1_FULL_TWIN else ("MEDIUM" if tier_val == TIER_2_LIVE_SNAPSHOT else "INSUFFICIENT")

            # Composite bottleneck risk score (0.0-1.0): weighted blend of peak node
            # utilization, district-wide overshoot relative to total capacity, and
            # active alert count. Weighted toward utilization since a single
            # severely overloaded node is the sharpest early-warning signal.
            utilization_component = min(1.0, base_rep.max_utilization_ratio)
            overshoot_component = min(1.0, base_rep.total_overshoot_tonnes / total_cap) if total_cap > 0 else 0.0
            alert_component = min(1.0, base_rep.active_alerts_count / 5.0)
            risk_score = (
                0.5 * utilization_component + 0.3 * overshoot_component + 0.2 * alert_component
            )

            ranking_list.append({
                "district": dist,
                "crop": crop,
                "bottleneck_risk_score": round(risk_score, 2),
                "total_overshoot_tonnes": base_rep.total_overshoot_tonnes,
                "active_alerts_count": base_rep.active_alerts_count,
                "max_utilization_ratio": base_rep.max_utilization_ratio,
                "top_bottleneck_node": top_node,
                "top_bottleneck_overshoot_tonnes": top_overshoot,
                "confidence_tier": conf_tier,
                "computable": True,
                "reason": None,
            })
        except Exception as exc:
            ranking_list.append({
                "district": dist,
                "crop": crop,
                "bottleneck_risk_score": 0.0,
                "total_overshoot_tonnes": 0.0,
                "active_alerts_count": 0,
                "max_utilization_ratio": 0.0,
                "top_bottleneck_node": "None",
                "top_bottleneck_overshoot_tonnes": 0.0,
                "confidence_tier": "INSUFFICIENT",
                "computable": False,
                "reason": str(exc),
            })

    # Sort descending by risk score
    ranking_list.sort(key=lambda x: x["bottleneck_risk_score"], reverse=True)

    # Assign priority ranks
    for idx, item in enumerate(ranking_list):
        item["priority_rank"] = idx + 1

    return ranking_list


if __name__ == "__main__":
    detector = BottleneckDetector(district="Alappuzha", crop="rice")
    reports = detector.detect_all_bottlenecks()
    print("\n" + "=" * 80)
    print(" BOTTLENECK DETECTION WITH ALERT-FATIGUE FILTER")
    print("=" * 80)
    for sc_name, rep in reports.items():
        print(f"\nScenario: {sc_name} (Computable: {rep.computable})")
        print(f"Total Overshoot: {rep.total_overshoot_tonnes:,.1f} t | Total Nodes: {rep.total_bottleneck_nodes} | Active Alerts: {rep.active_alerts_count}")
        for b in rep.bottlenecks[:3]:
            print(f"  #{b.rank} {b.node_id} ({b.node_name}): Overshoot={b.overshoot_tonnes}t, Alert={b.is_active_alert}")

    print("\n" + "=" * 80)
    print(" MULTI-DISTRICT PRIORITY RANKING")
    print("=" * 80)
    priorities = get_multi_district_priority_ranking(crop="rice")
    for p in priorities:
        print(f"Rank #{p.get('priority_rank')}: {p['district']} | Risk Score: {p['bottleneck_risk_score']} | Top Node: {p['top_bottleneck_node']} (+{p['top_bottleneck_overshoot_tonnes']}t) | Confidence: {p['confidence_tier']}")
    print("=" * 80 + "\n")
