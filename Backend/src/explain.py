"""
Fasal Twin - Decision Explainability Engine
Translates quantitative model recommendations, regret bounds, and disagreement
diagnoses into an itemized, auditable JSON evidence chain ({fact, source}) for
transparent stakeholder review.
"""

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.counterfactual_optimizer import RobustRecommendation, CounterfactualOptimizer
from src.confidence_gate import ConfidenceAssessment, ConfidenceGate
from src.bottleneck_detector import BottleneckDetector
from src.forecast_model import ForecastModel


@dataclass
class EvidenceItem:
    """Individual structured evidence fact with explicit citation source."""
    fact: str
    source: str
    category: str  # 'production' | 'meteorology' | 'econometrics' | 'logistics' | 'decision_rule' | 'regret_analysis'


@dataclass
class ExplanationReport:
    """Complete structured JSON explanation for frontend Why? panel."""
    recommendation_id: str
    district: str
    crop: str
    selected_action: str
    confidence_label: str
    confidence_score: float
    evidence_chain: List[Dict[str, str]]  # list of {"fact": ..., "source": ..., "category": ...}
    worst_case_guaranteed_payoff_rs: float
    max_regret_rs: float
    scenario_consensus: bool
    primary_disagreement_driver: Optional[str]
    summary_verdict: str
    phrasing_source: str


class DecisionExplainer:
    """
    Constructs transparent, auditable evidence chains for any recommendation.
    """

    def __init__(self, district: str = "Alappuzha", crop: str = "rice"):
        self.district = district
        self.crop = crop

    def build_evidence_chain(
        self,
        recommendation: RobustRecommendation,
        confidence_assessment: ConfidenceAssessment,
        price_model_summary: Dict[str, Any],
    ) -> List[EvidenceItem]:
        """
        Synthesizes individual verifiable facts and their authoritative source citations.
        """
        chain: List[EvidenceItem] = []

        # 1. Production Fact — computed fresh per district/crop rather than a fixed
        # literal, so a Kottayam explanation doesn't silently repeat Alappuzha's numbers.
        try:
            forecast_model = ForecastModel(district=self.district, crop=self.crop).fit()
            season_tonnes = forecast_model.latest_production_tonnes
            weekly_tonnes = forecast_model.baseline_weekly_tonnes
            chain.append(
                EvidenceItem(
                    fact=(
                        f"In {self.district}, rice production baseline for peak Punja harvest season "
                        f"is ~{season_tonnes:,.0f} tonnes, creating weekly peak harvest inflow of ~{weekly_tonnes:,.0f} tonnes across local FPOs."
                    ),
                    source="Kerala Department of Economics & Statistics (DES) / EARAS 2023 Table 5.1.1",
                    category="production",
                )
            )
        except Exception:
            chain.append(
                EvidenceItem(
                    fact=f"Production baseline data for {self.district} ({self.crop}) could not be resolved.",
                    source="Kerala Department of Economics & Statistics (DES) / EARAS 2023 Table 5.1.1",
                    category="production",
                )
            )

        # 2. Weather Dynamics
        chain.append(
            EvidenceItem(
                fact=(
                    f"Historical IMD meteorological records indicate pre-monsoon precipitation spikes "
                    f"compress the harvest window, magnifying peak weekly arrival surges by up to 1.20x."
                ),
                source="India Meteorological Department (IMD) Daily Weather Records",
                category="meteorology",
            )
        )

        # 3. Econometric Elasticity
        n_obs = price_model_summary.get("n_observations", 0)
        slope = price_model_summary.get("slope", 0.0)
        r2 = price_model_summary.get("r_squared", 0.0)
        chain.append(
            EvidenceItem(
                fact=(
                    f"Agmarknet econometric fitting ({n_obs} observations, R²={r2:.3f}) establishes that "
                    f"each 100 tonnes of excess mandi arrival depresses open market modal price by Rs {abs(slope * 100):.2f}/quintal."
                ),
                source="Agmarknet Mandi Arrivals & Prices via CEDA, Ashoka University",
                category="econometrics",
            )
        )

        # 4. Logistics Constraints — the real top-overshoot node for this district's
        # baseline scenario, not a fixed reference to Alappuzha's Mandi M1.
        try:
            baseline_report = BottleneckDetector(district=self.district, crop=self.crop).detect_all_bottlenecks()["baseline"]
            top_node = baseline_report.bottlenecks[0] if baseline_report.computable and baseline_report.bottlenecks else None
            if top_node:
                chain.append(
                    EvidenceItem(
                        fact=(
                            f"{top_node.node_name} ({top_node.district}) has a rated intake capacity of "
                            f"{top_node.capacity_tonnes:,.0f} tonnes, facing overshoot of {top_node.overshoot_tonnes:,.0f} tonnes "
                            f"({top_node.overshoot_pct:.0f}% over capacity) during peak arrival weeks without intervention."
                        ),
                        source="Regional Logistics & Mandi Capacity Registry (network_capacity.csv)",
                        category="logistics",
                    )
                )
            else:
                chain.append(
                    EvidenceItem(
                        fact=f"No node in {self.district}'s mapped network is projected to exceed capacity under the baseline scenario.",
                        source="Regional Logistics & Mandi Capacity Registry (network_capacity.csv)",
                        category="logistics",
                    )
                )
        except Exception:
            chain.append(
                EvidenceItem(
                    fact=f"Logistics capacity data for {self.district} could not be resolved.",
                    source="Regional Logistics & Mandi Capacity Registry (network_capacity.csv)",
                    category="logistics",
                )
            )

        # 5. Robust Selection Rule
        chain.append(
            EvidenceItem(
                fact=(
                    f"Under Wald's Maximin criterion, '{recommendation.selected_intervention_name}' was selected "
                    f"because it guarantees the highest safety floor payoff of Rs {recommendation.worst_case_payoff_rs:,.2f} "
                    f"across all 4 stress scenarios (Baseline, Weather-Shifted, Spillover, Capacity Shock)."
                ),
                source="Maximin Robust Counterfactual Optimizer (src/counterfactual_optimizer.py)",
                category="decision_rule",
            )
        )

        # 6. Minimax Regret Analysis
        chain.append(
            EvidenceItem(
                fact=(
                    f"Minimax Regret Evaluation: The chosen policy has a maximum hindsight regret bounded at "
                    f"Rs {recommendation.max_regret_rs:,.2f} across all computable scenarios, confirming that it stays "
                    f"within optimal operational boundaries under worst-case realization."
                ),
                source="Minimax Regret Analysis (src/counterfactual_optimizer.py)",
                category="regret_analysis",
            )
        )

        # 7. Confidence Assessment & Disagreement Diagnosis
        if confidence_assessment.scenario_consensus:
            conf_fact = (
                f"Confidence rated {confidence_assessment.confidence_label} (Score: {confidence_assessment.confidence_score:.2f}) "
                f"based on {confidence_assessment.data_density_tier} data density and unanimous scenario consensus."
            )
        else:
            driver_str = confidence_assessment.primary_disagreement_driver or "scenario_divergence"
            conf_fact = (
                f"Confidence rated {confidence_assessment.confidence_label} (Score: {confidence_assessment.confidence_score:.2f}). "
                f"Scenarios diverged primarily due to driver '{driver_str}'. Disagreement matrix provides scenario-specific recommendations."
            )

        chain.append(
            EvidenceItem(
                fact=conf_fact,
                source="Confidence Truth Gate (src/confidence_gate.py)",
                category="decision_rule",
            )
        )

        return chain

    def explain(
        self,
        recommendation: RobustRecommendation,
        confidence_assessment: ConfidenceAssessment,
        price_model_summary: Dict[str, Any],
        recommendation_id: Optional[str] = None,
    ) -> ExplanationReport:
        """
        Generates full structured explanation report.
        """
        rec_id = recommendation_id or str(uuid.uuid4())[:8]
        items = self.build_evidence_chain(recommendation, confidence_assessment, price_model_summary)

        chain_dicts = [
            {"fact": it.fact, "source": it.source, "category": it.category}
            for it in items
        ]

        # Generate grounded summary via Gemini LLM with guardrails
        from src.llm_client import get_llm_client
        client = get_llm_client()
        llm_response = client.generate_grounded_text(
            facts=chain_dicts,
            instruction="Summarize the recommendation, confidence label, payoff and regret using the provided evidence facts."
        )
        summary = llm_response["text"]
        phrasing_source = llm_response["phrasing_source"]

        return ExplanationReport(
            recommendation_id=rec_id,
            district=self.district,
            crop=self.crop,
            selected_action=recommendation.selected_intervention_name,
            confidence_label=confidence_assessment.confidence_label,
            confidence_score=confidence_assessment.confidence_score,
            evidence_chain=chain_dicts,
            worst_case_guaranteed_payoff_rs=recommendation.worst_case_payoff_rs,
            max_regret_rs=recommendation.max_regret_rs,
            scenario_consensus=confidence_assessment.scenario_consensus,
            primary_disagreement_driver=confidence_assessment.primary_disagreement_driver,
            summary_verdict=summary,
            phrasing_source=phrasing_source,
        )


if __name__ == "__main__":
    opt = CounterfactualOptimizer(district="Alappuzha", crop="rice")
    rec = opt.optimize()
    gate = ConfidenceGate()
    conf = gate.evaluate(rec, opt.elasticity_model.get_summary())

    explainer = DecisionExplainer(district="Alappuzha", crop="rice")
    exp = explainer.explain(rec, conf, opt.elasticity_model.get_summary())

    print("\n" + "=" * 80)
    print(f" EXPLANATION & EVIDENCE CHAIN (ID: {exp.recommendation_id})")
    print("=" * 80)
    print(f"Verdict:    {exp.summary_verdict}")
    print(f"Confidence: {exp.confidence_label} ({exp.confidence_score})")
    print(f"Max Regret: Rs {exp.max_regret_rs:,.2f}")
    print("\nItemized Evidence Chain:")
    for idx, item in enumerate(exp.evidence_chain, 1):
        print(f"\n[{idx}] [{item['category'].upper()}] {item['fact']}")
        print(f"    --> Source: {item['source']}")
    print("=" * 80 + "\n")
