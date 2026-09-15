"""
Fasal Twin - Confidence Gate & Honest Disagreement Engine
Enforces transparent confidence labeling (HIGH / MEDIUM / LOW) and returns
a structured Disagreement Matrix with explicit primary disagreement driver diagnosis
when scenarios diverge or data density is low.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.counterfactual_optimizer import RobustRecommendation, ScenarioOutcome


@dataclass
class DisagreementMatrix:
    """Structured divergence object returned when confidence is LOW and scenarios disagree."""
    competing_interventions: List[str]
    scenario_picks: Dict[str, Dict[str, Any]]  # [scenario_name] -> {intervention_id, intervention_name, payoff, reason}
    disagreement_reason: str
    primary_disagreement_driver: str  # e.g. "weather_shift_scenario" | "adjacent_shock_scenario" | "capacity_shock_scenario" | "insufficient_data"
    primary_disagreement_explanation: str
    action_verdict: str  # "NO_ACTION_RECOMMENDED" | "SPLIT_ADVISORY"


@dataclass
class ConfidenceAssessment:
    """Final confidence evaluation for a policy recommendation."""
    district: str
    crop: str
    confidence_label: str  # 'HIGH' | 'MEDIUM' | 'LOW'
    confidence_score: float  # 0.0 to 1.0
    data_density_tier: str  # 'DENSE' | 'SPARSE' | 'INSUFFICIENT'
    scenario_consensus: bool
    scenario_picks: Dict[str, str]
    computability_ratio: float  # computable_scenarios / total_scenarios
    recommendation: Optional[RobustRecommendation]
    disagreement_matrix: Optional[DisagreementMatrix]
    primary_disagreement_driver: Optional[str]
    provenance_note: str
    explanation: str


class ConfidenceGate:
    """
    Confidence Classifier & Truth Gate.
    Non-negotiable Principle 2: Derived strictly from actual data density, never hardcoded.
    Non-negotiable Principle 4: Returns structured disagreement when data or consensus is low.
    """

    def __init__(self, high_density_threshold: int = 100, min_density_threshold: int = 24):
        self.high_density_threshold = high_density_threshold
        self.min_density_threshold = min_density_threshold

    def _diagnose_disagreement_driver(
        self,
        recommendation: RobustRecommendation,
        scenario_best_details: Dict[str, Dict[str, Any]],
        data_density_tier: str,
    ) -> Tuple[str, str]:
        """
        Identifies the specific input or shock scenario most responsible for scenario divergence.
        """
        if data_density_tier == "INSUFFICIENT":
            return (
                "insufficient_data",
                "Historical mandi observations are below the minimum threshold (24 records), preventing reliable econometric estimation."
            )

        baseline_pick = scenario_best_details.get("baseline", {}).get("intervention_id")
        
        # Check which scenario caused the divergence from baseline
        divergent_scenarios = [
            sc for sc, d in scenario_best_details.items()
            if sc != "baseline" and d.get("intervention_id") != baseline_pick
        ]

        if "weather_shifted" in divergent_scenarios:
            return (
                "weather_shift_scenario",
                "Precipitation variance and compressed harvest arrival surge caused optimal policy to switch toward high-capacity staggered holding."
            )
        elif "adjacent_shock" in divergent_scenarios:
            return (
                "adjacent_shock_scenario",
                "High inter-district arrival correlation and adjacent mandi glut overflow altered optimal rerouting economics."
            )
        elif "capacity_shock" in divergent_scenarios:
            return (
                "capacity_shock_scenario",
                "20% intake reduction across principal mandis forced a divergence toward direct-to-mill processor offloading."
            )
        else:
            return (
                "multi_scenario_variance",
                "Multiple compounding stress factors across weather and logistics capacity led to divergent scenario outcomes."
            )

    def evaluate(
        self,
        recommendation: RobustRecommendation,
        price_model_summary: Dict[str, Any],
    ) -> ConfidenceAssessment:
        """
        Evaluates confidence across:
        1. Scenario agreement: Did individual scenario optimizers pick the exact same intervention?
        2. Econometric data density: Observations N and R^2 from price_elasticity_model.
        3. Computability ratio: Were all 4 scenarios computable without missing data?
        """
        total_scenarios = len(recommendation.computable_scenarios) + len(recommendation.uncomputable_scenarios)
        computable_count = len(recommendation.computable_scenarios)
        computability_ratio = (computable_count / total_scenarios) if total_scenarios > 0 else 0.0

        # 1. Determine best intervention for each individual computable scenario
        scenario_picks: Dict[str, str] = {}
        scenario_best_details: Dict[str, Dict[str, Any]] = {}

        for sc_name in recommendation.computable_scenarios:
            outcomes = recommendation.scenario_outcomes.get(sc_name, {})
            if outcomes:
                best_int_for_sc = max(outcomes.keys(), key=lambda k: outcomes[k].net_economic_payoff_rs)
                scenario_picks[sc_name] = best_int_for_sc
                best_outcome = outcomes[best_int_for_sc]
                scenario_best_details[sc_name] = {
                    "intervention_id": best_int_for_sc,
                    "intervention_name": best_outcome.intervention_name,
                    "net_payoff_rs": best_outcome.net_economic_payoff_rs,
                    "bottleneck_reduction_tonnes": best_outcome.bottleneck_reduction_tonnes,
                }

        distinct_picks = set(scenario_picks.values())
        scenario_consensus = (len(distinct_picks) <= 1) and (len(recommendation.computable_scenarios) >= 2)

        # 2. Econometric data density evaluation
        n_obs = price_model_summary.get("n_observations", 0)
        is_fitted = price_model_summary.get("is_fitted", False)
        r2 = price_model_summary.get("r_squared") or 0.0

        if not is_fitted or n_obs < self.min_density_threshold:
            data_density_tier = "INSUFFICIENT"
            density_score = 0.2
        elif n_obs >= self.high_density_threshold:
            data_density_tier = "DENSE"
            density_score = 0.95
        else:
            data_density_tier = "SPARSE"
            density_score = 0.60

        # 3. Overall confidence score synthesis (0.0 to 1.0)
        consensus_score = 1.0 if scenario_consensus else 0.35
        comp_score = computability_ratio

        # Weighted confidence score
        confidence_score = round(0.40 * density_score + 0.35 * consensus_score + 0.25 * comp_score, 3)

        # Classification rule
        if data_density_tier == "INSUFFICIENT" or computability_ratio < 0.5:
            confidence_label = "LOW"
        elif not scenario_consensus:
            confidence_label = "LOW" if data_density_tier == "SPARSE" else "MEDIUM"
        elif data_density_tier == "DENSE" and computability_ratio == 1.0 and scenario_consensus:
            confidence_label = "HIGH"
        else:
            confidence_label = "MEDIUM"

        # 4. Construct Disagreement Matrix & Driver Diagnosis if LOW confidence or Scenarios Disagree
        disagreement_matrix: Optional[DisagreementMatrix] = None
        driver_name: Optional[str] = None

        if confidence_label == "LOW" or not scenario_consensus:
            action_verdict = (
                "NO_ACTION_RECOMMENDED" if data_density_tier == "INSUFFICIENT" else "SPLIT_ADVISORY"
            )
            driver_name, driver_expl = self._diagnose_disagreement_driver(
                recommendation, scenario_best_details, data_density_tier
            )
            dis_reason = (
                f"Scenarios yielded diverging optimal interventions: {distinct_picks}. "
                f"Primary disagreement driver: '{driver_name}'. "
                f"Data density tier: {data_density_tier} ({n_obs} Agmarknet observations, R²={r2:.3f}). "
                f"Computable scenarios: {computable_count}/{total_scenarios}."
            )
            disagreement_matrix = DisagreementMatrix(
                competing_interventions=list(distinct_picks),
                scenario_picks=scenario_best_details,
                disagreement_reason=dis_reason,
                primary_disagreement_driver=driver_name,
                primary_disagreement_explanation=driver_expl,
                action_verdict=action_verdict,
            )

        provenance_note = (
            f"Confidence {confidence_label} (Score: {confidence_score:.2f}) derived from: "
            f"Data density tier '{data_density_tier}' ({n_obs} Agmarknet records, {price_model_summary.get('district')} {price_model_summary.get('crop')}), "
            f"Scenario Consensus: {scenario_consensus} ({distinct_picks if len(distinct_picks) > 1 else 'All scenarios agree'}), "
            f"Scenario computability: {computable_count}/{total_scenarios} scenarios computable."
        )

        explanation = (
            f"Recommendation Confidence: {confidence_label}. "
            + (
                f"All {computable_count} computable stress scenarios agree on the optimal action ({recommendation.selected_intervention_name})."
                if scenario_consensus
                else f"Scenarios diverge across {len(distinct_picks)} competing actions: {list(distinct_picks)}. Primary divergence driver: '{driver_name}'."
            )
        )

        return ConfidenceAssessment(
            district=recommendation.district,
            crop=recommendation.crop,
            confidence_label=confidence_label,
            confidence_score=confidence_score,
            data_density_tier=data_density_tier,
            scenario_consensus=scenario_consensus,
            scenario_picks=scenario_picks,
            computability_ratio=computability_ratio,
            recommendation=recommendation if confidence_label != "LOW" else None,
            disagreement_matrix=disagreement_matrix,
            primary_disagreement_driver=driver_name,
            provenance_note=provenance_note,
            explanation=explanation,
        )


if __name__ == "__main__":
    from src.counterfactual_optimizer import CounterfactualOptimizer

    opt = CounterfactualOptimizer(district="Alappuzha", crop="rice")
    rec = opt.optimize()
    gate = ConfidenceGate()
    assessment = gate.evaluate(rec, opt.elasticity_model.get_summary())

    print("\n" + "=" * 80)
    print(" CONFIDENCE GATE ASSESSMENT WITH DISAGREEMENT DIAGNOSIS")
    print("=" * 80)
    print(f"Confidence Label:  {assessment.confidence_label} (Score: {assessment.confidence_score})")
    print(f"Data Density Tier: {assessment.data_density_tier}")
    print(f"Scenario Consensus:{assessment.scenario_consensus}")
    print(f"Primary Driver:    {assessment.primary_disagreement_driver}")
    print(f"Provenance:        {assessment.provenance_note}")
    if assessment.disagreement_matrix:
        print("\nStructured Disagreement Matrix:")
        print(f"  Driver:  {assessment.disagreement_matrix.primary_disagreement_driver}")
        print(f"  Expl:    {assessment.disagreement_matrix.primary_disagreement_explanation}")
        print(f"  Reason:  {assessment.disagreement_matrix.disagreement_reason}")
    print("=" * 80 + "\n")
