"""
Fasal Twin - Counterfactual Optimizer & Robust Selection Engine
Simulates policy interventions under each reliability scenario and applies
both Wald Maximin Robust Optimization and Minimax Regret Decision Analysis.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import networkx as nx

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.network_model import load_network
from src.price_elasticity_model import PriceElasticityModel
from src.scenario_engine import ScenarioEngine, ScenarioResult
from src.bottleneck_detector import BottleneckDetector, ScenarioBottleneckReport


@dataclass
class InterventionOption:
    """Definition of a candidate logistics intervention."""
    intervention_id: str
    name: str
    description: str
    intervention_type: str  # 'do_nothing' | 'redirect_mandi' | 'staggered_holding' | 'direct_mill_offload'
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioOutcome:
    """Outcome of evaluating one intervention under one scenario."""
    scenario_name: str
    intervention_id: str
    intervention_name: str
    computable: bool
    bottleneck_reduction_tonnes: float
    remaining_overshoot_tonnes: float
    price_impact_rs_per_quintal: float
    price_protection_gain_rs: float
    logistics_cost_rs: float
    spoilage_avoidance_gain_rs: float
    net_economic_payoff_rs: float  # (Price Gain + Spoilage Avoided - Logistics Cost)
    regret_rs: float = 0.0  # (Best possible outcome in hindsight - this action's outcome)
    implausible_magnitude: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RobustRecommendation:
    """The final robust selection outcome across all scenarios."""
    district: str
    crop: str
    selected_intervention_id: str
    selected_intervention_name: str
    selection_criterion: str
    worst_case_payoff_rs: float  # Min payoff across all computable scenarios
    average_payoff_rs: float
    max_regret_rs: float = 0.0  # Maximum regret of selected action across scenarios
    minimax_regret_intervention_id: str = "INT-0"
    minimax_regret_intervention_name: str = "Do Nothing"
    minimax_regret_value_rs: float = 0.0
    scenario_outcomes: Dict[str, Dict[str, ScenarioOutcome]] = field(default_factory=dict)  # [scenario_name][intervention_id]
    computable_scenarios: List[str] = field(default_factory=list)
    uncomputable_scenarios: List[str] = field(default_factory=list)
    data_provenance: str = ""
    explanation_summary: str = ""


class CounterfactualOptimizer:
    """
    Robust Counterfactual Decision Engine for Regional Crop Flow Bottlenecks.

    Robust Selection Criterion:
    --------------------------
    We apply the classical Wald Maximin Principle:
        Intervention* = argmax_{i in Interventions} [ min_{s in Scenarios} Payoff(i, s) ]
    
    Alongside Minimax Regret:
        Regret(i, s) = max_{j} Payoff(j, s) - Payoff(i, s)
        Intervention_regret* = argmin_{i} [ max_{s} Regret(i, s) ]
    """

    def __init__(
        self,
        district: str = "Alappuzha",
        crop: str = "rice",
        loader: Optional[DataLoader] = None,
        graph: Optional[nx.DiGraph] = None,
    ):
        self.district = district
        self.crop = crop
        self.loader = loader or DataLoader()
        self.graph = graph or load_network(district=district, loader=self.loader)
        self.elasticity_model = PriceElasticityModel(district=district, crop=crop, loader=self.loader).fit()
        self.scenario_engine = ScenarioEngine(district=district, crop=crop, loader=self.loader, graph=self.graph)
        self.bottleneck_detector = BottleneckDetector(district=district, crop=crop, loader=self.loader, graph=self.graph)

        self.interventions: List[InterventionOption] = [
            InterventionOption(
                intervention_id="INT-0",
                name="Do Nothing (Status Quo)",
                description="Maintain default open-market flows without coordinated rerouting or holding.",
                intervention_type="do_nothing",
                parameters={},
            ),
            InterventionOption(
                intervention_id="INT-1",
                name="Dynamic Mandi Diversion (30% to Secondary Hubs)",
                description="Reroute 30% of peak inflow from congested principal mandis (M1/M3) to secondary markets (M2) and storage (S1/S2).",
                intervention_type="redirect_mandi",
                parameters={"diversion_ratio": 0.30, "target_nodes": ["M2", "S1", "S2"]},
            ),
            InterventionOption(
                intervention_id="INT-2",
                name="Staggered Farmgate Holding (5-Day Moisture-Managed Buffer)",
                description="Coordinate 5-day staggered farmgate/FPO holding using tarpaulin & aeration, smoothing peak arrival surge by 25%.",
                intervention_type="staggered_holding",
                parameters={"smoothing_ratio": 0.25, "holding_cost_per_tonne": 45.0},
            ),
            InterventionOption(
                intervention_id="INT-3",
                name="Direct Processor Offload (25% Direct-to-Mill)",
                description="Bypass mandi yards by routing 25% of FPO harvest directly to Supplyco Modern Rice Mills (P1/P2/P3).",
                intervention_type="direct_mill_offload",
                parameters={"direct_offload_ratio": 0.25, "target_processors": ["P1", "P2", "P3"]},
            ),
        ]

    def _simulate_intervention_on_scenario(
        self,
        intervention: InterventionOption,
        scenario_res: ScenarioResult,
        bottleneck_rep: ScenarioBottleneckReport,
    ) -> ScenarioOutcome:
        """Simulates economic and operational consequences of an intervention on a scenario."""
        if not scenario_res.computable:
            return ScenarioOutcome(
                scenario_name=scenario_res.scenario_name,
                intervention_id=intervention.intervention_id,
                intervention_name=intervention.name,
                computable=False,
                bottleneck_reduction_tonnes=0.0,
                remaining_overshoot_tonnes=0.0,
                price_impact_rs_per_quintal=0.0,
                price_protection_gain_rs=0.0,
                logistics_cost_rs=0.0,
                spoilage_avoidance_gain_rs=0.0,
                net_economic_payoff_rs=-999999.0,
                regret_rs=0.0,
                details={"reason": scenario_res.reason},
            )

        base_inflows = dict(scenario_res.forecast_inflow)
        capacities = dict(scenario_res.effective_capacities)
        total_overshoot_before = bottleneck_rep.total_overshoot_tonnes

        new_inflows = dict(base_inflows)
        extra_logistics_cost = 0.0
        diverted_tonnes = 0.0

        if intervention.intervention_type == "do_nothing":
            pass

        elif intervention.intervention_type == "redirect_mandi":
            ratio = intervention.parameters.get("diversion_ratio", 0.30)
            for src_mandi in ["M1", "M3"]:
                if src_mandi in new_inflows and new_inflows[src_mandi] > capacities.get(src_mandi, 0):
                    surplus = new_inflows[src_mandi] - capacities.get(src_mandi, 0)
                    to_divert = surplus * ratio
                    new_inflows[src_mandi] -= to_divert
                    diverted_tonnes += to_divert
                    new_inflows["M2"] = new_inflows.get("M2", 0.0) + (to_divert * 0.4)
                    new_inflows["S1"] = new_inflows.get("S1", 0.0) + (to_divert * 0.3)
                    new_inflows["S2"] = new_inflows.get("S2", 0.0) + (to_divert * 0.3)
                    extra_logistics_cost += to_divert * 180.0

        elif intervention.intervention_type == "staggered_holding":
            ratio = intervention.parameters.get("smoothing_ratio", 0.25)
            holding_cost_rate = intervention.parameters.get("holding_cost_per_tonne", 45.0)
            for node_id in list(new_inflows.keys()):
                held = new_inflows[node_id] * ratio
                new_inflows[node_id] -= held
                diverted_tonnes += held
                extra_logistics_cost += held * holding_cost_rate

        elif intervention.intervention_type == "direct_mill_offload":
            ratio = intervention.parameters.get("direct_offload_ratio", 0.25)
            fpo_nodes = [n for n in new_inflows if n.startswith("F")]
            for f in fpo_nodes:
                offloaded = new_inflows[f] * ratio
                new_inflows[f] -= offloaded
                diverted_tonnes += offloaded
                new_inflows["P1"] = new_inflows.get("P1", 0.0) + (offloaded * 0.4)
                new_inflows["P2"] = new_inflows.get("P2", 0.0) + (offloaded * 0.3)
                new_inflows["P3"] = new_inflows.get("P3", 0.0) + (offloaded * 0.3)
                extra_logistics_cost += offloaded * 210.0

        remaining_overshoot = sum(max(0.0, new_inflows[n] - capacities.get(n, 1.0)) for n in new_inflows)
        bottleneck_reduction = max(0.0, total_overshoot_before - remaining_overshoot)
        spoilage_avoidance = bottleneck_reduction * 0.035 * 26000.0

        # Compute total inflow across all nodes as proxy for mandi volume
        base_total_inflow = sum(base_inflows.values())
        new_total_inflow = sum(new_inflows.values())

        if self.elasticity_model.is_fitted:
            # Use total inflow values for price impact estimation
            impact = self.elasticity_model.estimate_price_impact(base_total_inflow, new_total_inflow)
            delta_price_rs_qtl = max(0.0, impact.get("delta_price_rs_per_quintal", 0.0))
            price_gain = delta_price_rs_qtl * (new_total_inflow * 10.0)
            # Debug prints for price calculation (retain original condition)
            if self.district == "Alappuzha" and self.crop.lower() == "rice" and intervention.intervention_id == "INT-2" and scenario_res.scenario_name == "baseline":
                print(f"elasticity impact dict: {impact}")
                print(f"Delta price (Rs per quintal): {delta_price_rs_qtl}")
                print(f"new_total_inflow (tonnes): {new_total_inflow}")
                print(f"price_gain = Delta price * (new_total_inflow * 10): {price_gain}")
        else:
            delta_price_rs_qtl = 0.0
            price_gain = 0.0

        net_payoff = (price_gain + spoilage_avoidance) - extra_logistics_cost

        # Determine if the outcome should be flagged as implausible
        MIN_ACCEPTABLE_TEST_R2 = 0.0
        MAX_PLAUSIBLE_PRICE_CHANGE_PCT = 50.0
        implausible = False
        if hasattr(self.elasticity_model, "test_r2"):
            if self.elasticity_model.test_r2 < MIN_ACCEPTABLE_TEST_R2:
                implausible = True
        pct_change = impact.get("pct_price_change", 0.0) if self.elasticity_model.is_fitted else 0.0
        if abs(pct_change) > MAX_PLAUSIBLE_PRICE_CHANGE_PCT:
            implausible = True

        return ScenarioOutcome(
            scenario_name=scenario_res.scenario_name,
            intervention_id=intervention.intervention_id,
            intervention_name=intervention.name,
            computable=True,
            bottleneck_reduction_tonnes=round(bottleneck_reduction, 2),
            remaining_overshoot_tonnes=round(remaining_overshoot, 2),
            price_impact_rs_per_quintal=round(delta_price_rs_qtl, 2),
            price_protection_gain_rs=round(price_gain, 2),
            logistics_cost_rs=round(extra_logistics_cost, 2),
            spoilage_avoidance_gain_rs=round(spoilage_avoidance, 2),
            net_economic_payoff_rs=round(net_payoff, 2),
            regret_rs=0.0,  # Will be filled after all options are evaluated for this scenario
            implausible_magnitude=implausible,
            details={
                "diverted_tonnes": round(diverted_tonnes, 2),
                "total_overshoot_before": round(total_overshoot_before, 2),
            },
        )

    def optimize(self) -> RobustRecommendation:
        """
        Runs all interventions across all computable scenarios and applies Maximin and Minimax Regret selection.
        """
        all_scenarios = self.scenario_engine.run_all_scenarios()
        all_bottlenecks = self.bottleneck_detector.detect_all_bottlenecks()

        computable_scenarios: List[str] = []
        uncomputable_scenarios: List[str] = []
        scenario_outcomes: Dict[str, Dict[str, ScenarioOutcome]] = {}

        for sc_name, sc_res in all_scenarios.items():
            if sc_res.computable:
                computable_scenarios.append(sc_name)
            else:
                uncomputable_scenarios.append(sc_name)

            scenario_outcomes[sc_name] = {}
            for int_opt in self.interventions:
                outcome = self._simulate_intervention_on_scenario(
                    int_opt, sc_res, all_bottlenecks[sc_name]
                )
                scenario_outcomes[sc_name][int_opt.intervention_id] = outcome

        # Calculate Regret per scenario: Regret(i, s) = Best_Payoff(s) - Payoff(i, s)
        scenario_best_payoffs: Dict[str, float] = {}
        for sc in computable_scenarios:
            best_p = max(
                scenario_outcomes[sc][i.intervention_id].net_economic_payoff_rs
                for i in self.interventions
            )
            scenario_best_payoffs[sc] = best_p
            for i in self.interventions:
                outcome_obj = scenario_outcomes[sc][i.intervention_id]
                regret_val = max(0.0, best_p - outcome_obj.net_economic_payoff_rs)
                outcome_obj.regret_rs = round(regret_val, 2)

        # Maximin and Minimax Regret Computation
        intervention_min_payoffs: Dict[str, float] = {}
        intervention_avg_payoffs: Dict[str, float] = {}
        intervention_max_regrets: Dict[str, float] = {}

        for int_opt in self.interventions:
            payoffs = [
                scenario_outcomes[sc][int_opt.intervention_id].net_economic_payoff_rs
                for sc in computable_scenarios
            ]
            regrets = [
                scenario_outcomes[sc][int_opt.intervention_id].regret_rs
                for sc in computable_scenarios
            ]
            if payoffs:
                intervention_min_payoffs[int_opt.intervention_id] = min(payoffs)
                intervention_avg_payoffs[int_opt.intervention_id] = sum(payoffs) / len(payoffs)
                intervention_max_regrets[int_opt.intervention_id] = max(regrets)
            else:
                intervention_min_payoffs[int_opt.intervention_id] = -999999.0
                intervention_avg_payoffs[int_opt.intervention_id] = -999999.0
                intervention_max_regrets[int_opt.intervention_id] = 999999.0

        # Pick Maximin action (best worst-case payoff)
        best_int_id = max(intervention_min_payoffs, key=lambda k: intervention_min_payoffs[k])
        best_option = next(i for i in self.interventions if i.intervention_id == best_int_id)
        worst_case_val = intervention_min_payoffs[best_int_id]
        avg_val = intervention_avg_payoffs[best_int_id]
        chosen_max_regret = intervention_max_regrets[best_int_id]

        # Pick Minimax Regret action (minimum maximum regret)
        minimax_int_id = min(intervention_max_regrets, key=lambda k: intervention_max_regrets[k])
        minimax_option = next(i for i in self.interventions if i.intervention_id == minimax_int_id)
        minimax_val = intervention_max_regrets[minimax_int_id]

        prov = (
            f"Evaluated {len(self.interventions)} candidate interventions across "
            f"{len(computable_scenarios)} computable scenarios ({', '.join(computable_scenarios)}) "
            f"using Maximin & Minimax Regret Decision Rules. "
            f"Elasticity model: {self.elasticity_model.data_provenance}"
        )

        summary = (
            f"Selected '{best_option.name}' via Maximin Robust Optimization. "
            f"Guarantees a worst-case safety floor of Rs {worst_case_val:,.2f} "
            f"(Average Rs {avg_val:,.2f}) with a maximum bounded hindsight regret of Rs {chosen_max_regret:,.2f} "
            f"across all tested stress scenarios."
        )

        return RobustRecommendation(
            district=self.district,
            crop=self.crop,
            selected_intervention_id=best_int_id,
            selected_intervention_name=best_option.name,
            selection_criterion="Maximin (Best Worst-Case Outcome Across Scenarios)",
            worst_case_payoff_rs=worst_case_val,
            average_payoff_rs=round(avg_val, 2),
            max_regret_rs=round(chosen_max_regret, 2),
            minimax_regret_intervention_id=minimax_int_id,
            minimax_regret_intervention_name=minimax_option.name,
            minimax_regret_value_rs=round(minimax_val, 2),
            scenario_outcomes=scenario_outcomes,
            computable_scenarios=computable_scenarios,
            uncomputable_scenarios=uncomputable_scenarios,
            data_provenance=prov,
            explanation_summary=summary,
        )


if __name__ == "__main__":
    optimizer = CounterfactualOptimizer(district="Alappuzha", crop="rice")
    rec = optimizer.optimize()
    print("\n" + "=" * 80)
    print(" COUNTERFACTUAL OPTIMIZATION & ROBUST SELECTION")
    print("=" * 80)
    print(f"District: {rec.district} | Crop: {rec.crop}")
    print(f"Maximin Selected: {rec.selected_intervention_name} ({rec.selected_intervention_id})")
    print(f"Worst-Case Payoff: Rs {rec.worst_case_payoff_rs:,.2f}")
    print(f"Max Regret:        Rs {rec.max_regret_rs:,.2f}")
    print(f"Minimax Regret Pick: {rec.minimax_regret_intervention_name} (Max Regret: Rs {rec.minimax_regret_value_rs:,.2f})")
    print("\nScenario Outcomes & Regret:")
    for sc in rec.computable_scenarios:
        print(f"\nScenario: {sc}")
        for i_id, outcome in rec.scenario_outcomes[sc].items():
            print(f"  {i_id} ({outcome.intervention_name[:35]:<35}): Payoff = Rs {outcome.net_economic_payoff_rs:11,.2f} | Regret = Rs {outcome.regret_rs:10,.2f}")
    print("=" * 80 + "\n")
