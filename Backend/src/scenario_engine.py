"""
Fasal Twin - 4-Scenario Reliability Engine
Simulates crop flow dynamics under 4 distinct conditions:
1. Baseline (historical seasonal trend)
2. Weather-Shifted (harvest window compressed by actual rainfall variance)
3. Adjacent Shock (cross-district spillover using real Agmarknet correlation)
4. Capacity Shock (infrastructure throughput reduction by documented named constant)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import networkx as nx
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.network_model import load_network, get_nodes_by_type
from src.forecast_model import ForecastModel
from src.guardrails import validate_forecast, ImplausibleForecastError

# Named constant for capacity shock (Section 3, Step 4)
# In Kuttanad, severe canal waterlogging and high humidity typically reduce
# warehouse and mandi daily turnaround capacity by 30%.
CAPACITY_SHOCK_REDUCTION_RATIO: float = 0.30


@dataclass
class ScenarioResult:
    """Standardized result object for each reliability scenario."""
    scenario_name: str
    computable: bool
    status: str  # 'computable' | 'not_computable' | 'insufficient_data'
    reason: Optional[str] = None
    forecast_inflow: Dict[str, float] = field(default_factory=dict)
    effective_capacities: Dict[str, float] = field(default_factory=dict)
    data_provenance: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


class ScenarioEngine:
    """
    Executes and coordinates the 4 reliability scenarios for regional crop flow.
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
        self.forecast_model = ForecastModel(district=district, crop=crop, loader=self.loader)

    def _allocate_inflows_to_nodes(self, total_tonnes: float) -> Dict[str, float]:
        """
        Distributes district total weekly production across nodes according to network topology:
        FPOs receive farmgate supply, and route downstream to Mandis, Storages, and Mills.
        """
        inflows: Dict[str, float] = {}

        # First distribute to FPOs based on capacity proportion
        fpo_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "fpo"]
        if not fpo_nodes:
            # If no FPOs, distribute directly to Mandis
            mandi_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "mandi"]
            total_cap = sum(self.graph.nodes[m]["capacity_tonnes"] for m in mandi_nodes) or 1.0
            for m in mandi_nodes:
                inflows[m] = round(total_tonnes * (self.graph.nodes[m]["capacity_tonnes"] / total_cap), 2)
            return inflows

        total_fpo_cap = sum(self.graph.nodes[f]["capacity_tonnes"] for f in fpo_nodes) or 1.0
        for f in fpo_nodes:
            inflows[f] = round(total_tonnes * (self.graph.nodes[f]["capacity_tonnes"] / total_fpo_cap), 2)

        # Mandis receive outflow from connected FPOs (historical ~60% goes to Mandis, 25% storage, 15% mill)
        mandi_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "mandi"]
        for m in mandi_nodes:
            # Find incoming edges from FPOs
            in_edges = [u for u, v in self.graph.in_edges(m) if self.graph.nodes[u].get("node_type") == "fpo"]
            if in_edges:
                m_inflow = sum(inflows.get(u, 0.0) * 0.60 for u in in_edges)
            else:
                m_inflow = total_tonnes * 0.25
            inflows[m] = round(m_inflow, 2)

        # Storage nodes receive from FPOs & Mandis
        storage_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "storage"]
        for s in storage_nodes:
            in_fpos = [u for u, v in self.graph.in_edges(s) if self.graph.nodes[u].get("node_type") == "fpo"]
            s_inflow = sum(inflows.get(u, 0.0) * 0.25 for u in in_fpos) if in_fpos else (total_tonnes * 0.15)
            inflows[s] = round(s_inflow, 2)

        # Processors receive from Mandis & Storage
        processor_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "processor"]
        for p in processor_nodes:
            inflows[p] = round(total_tonnes * 0.15, 2)

        return inflows

    def _get_node_capacities(self, shock_reduction: float = 0.0) -> Dict[str, float]:
        """Returns effective node capacities, with optional shock reduction."""
        caps: Dict[str, float] = {}
        for n, d in self.graph.nodes(data=True):
            nominal_cap = float(d.get("capacity_tonnes", 0.0))
            effective_cap = nominal_cap * (1.0 - shock_reduction)
            caps[n] = round(effective_cap, 2)
        return caps

    def forecast_baseline(self) -> ScenarioResult:
        """
        Scenario 1: Baseline Historical Inflow.
        Uses historical seasonal rice production trends.
        """
        try:
            weekly_volume, prov = self.forecast_model.get_seasonal_baseline_volume(season="punja")
            if weekly_volume <= 0.0:
                return ScenarioResult(
                    scenario_name="baseline",
                    computable=False,
                    status="insufficient_data",
                    reason=f"No baseline production data available for {self.district} {self.crop}.",
                    data_provenance=prov,
                )

            # Guardrail check against biological ceiling
            validate_forecast(weekly_volume, self.district, self.crop, self.loader)

            inflows = self._allocate_inflows_to_nodes(weekly_volume)
            capacities = self._get_node_capacities(shock_reduction=0.0)

            return ScenarioResult(
                scenario_name="baseline",
                computable=True,
                status="computable",
                forecast_inflow=inflows,
                effective_capacities=capacities,
                data_provenance=f"Scenario 1 (Baseline): {prov}",
                parameters={"total_weekly_tonnes": round(weekly_volume, 2)},
            )
        except ImplausibleForecastError as exc:
            return ScenarioResult(
                scenario_name="baseline",
                computable=False,
                status="rejected_implausible",
                reason=exc.reason,
                data_provenance="Guardrails Layer 4: Rejected physically implausible baseline forecast.",
            )

    def forecast_weather_shifted(self) -> ScenarioResult:
        """
        Scenario 2: Weather-Shifted Harvest Window.
        Uses actual IMD rainfall variance to compress harvest arrivals into peak surge weeks.
        """
        try:
            base_volume, base_prov = self.forecast_model.get_seasonal_baseline_volume(season="punja")
            if base_volume <= 0.0:
                return ScenarioResult(
                    scenario_name="weather_shifted",
                    computable=False,
                    status="insufficient_data",
                    reason=f"No baseline data for {self.district}.",
                    data_provenance=base_prov,
                )

            variance_mm, surge_factor, w_prov = self.forecast_model.compute_weather_delay_factor()
            shifted_volume = base_volume * surge_factor

            # Guardrail check against biological ceiling
            validate_forecast(shifted_volume, self.district, self.crop, self.loader)

            inflows = self._allocate_inflows_to_nodes(shifted_volume)
            capacities = self._get_node_capacities(shock_reduction=0.0)

            return ScenarioResult(
                scenario_name="weather_shifted",
                computable=True,
                status="computable",
                forecast_inflow=inflows,
                effective_capacities=capacities,
                data_provenance=f"Scenario 2 (Weather-Shifted): {w_prov} Applied to {base_prov}",
                parameters={
                    "rainfall_variance_mm": round(variance_mm, 2),
                    "weather_surge_multiplier": round(surge_factor, 4),
                    "shifted_weekly_tonnes": round(shifted_volume, 2),
                },
            )
        except ImplausibleForecastError as exc:
            return ScenarioResult(
                scenario_name="weather_shifted",
                computable=False,
                status="rejected_implausible",
                reason=exc.reason,
                data_provenance="Guardrails Layer 4: Rejected physically implausible weather-shifted forecast.",
            )

    def forecast_adjacent_shock(self) -> ScenarioResult:
        """
        Scenario 3: Adjacent District Spillover Shock.
        Uses empirical cross-district arrival correlation from Agmarknet.
        Non-negotiable Principle: If only 1 district is loaded, returns not_computable.
        """
        try:
            df_mandi = self.loader.load_mandi_arrivals_prices()
            all_districts = [d for d in df_mandi["district"].unique() if d.lower() != self.district.lower()]

            if not all_districts:
                return ScenarioResult(
                    scenario_name="adjacent_shock",
                    computable=False,
                    status="not_computable",
                    reason=(
                        f"Only one district ({self.district}) is present in loaded Agmarknet data. "
                        f"Cross-district spillover correlation cannot be computed without adjacent district data."
                    ),
                    data_provenance="Non-negotiable Principle 1 & 4: Refused to fabricate adjacent district shock magnitude.",
                )

            # Use the closest adjacent district (e.g. Kottayam)
            adjacent_dist = all_districts[0]
            corr, corr_prov = self.forecast_model.compute_cross_district_correlation(self.district, adjacent_dist)

            if corr is None:
                return ScenarioResult(
                    scenario_name="adjacent_shock",
                    computable=False,
                    status="not_computable",
                    reason=f"Could not compute correlation with {adjacent_dist}: {corr_prov}",
                    data_provenance=corr_prov,
                )

            base_volume, base_prov = self.forecast_model.get_seasonal_baseline_volume(season="punja")
            spillover_multiplier = 1.0 + max(0.0, corr * 0.35)
            shock_volume = base_volume * spillover_multiplier

            # Guardrail check against biological ceiling
            validate_forecast(shock_volume, self.district, self.crop, self.loader)

            inflows = self._allocate_inflows_to_nodes(shock_volume)
            capacities = self._get_node_capacities(shock_reduction=0.0)

            return ScenarioResult(
                scenario_name="adjacent_shock",
                computable=True,
                status="computable",
                forecast_inflow=inflows,
                effective_capacities=capacities,
                data_provenance=f"Scenario 3 (Adjacent Shock): {corr_prov}",
                parameters={
                    "adjacent_district": adjacent_dist,
                    "correlation_r": round(corr, 4),
                    "spillover_multiplier": round(spillover_multiplier, 4),
                    "shock_weekly_tonnes": round(shock_volume, 2),
                },
            )
        except ImplausibleForecastError as exc:
            return ScenarioResult(
                scenario_name="adjacent_shock",
                computable=False,
                status="rejected_implausible",
                reason=exc.reason,
                data_provenance="Guardrails Layer 4: Rejected physically implausible adjacent shock forecast.",
            )

    def forecast_capacity_shock(self) -> ScenarioResult:
        """
        Scenario 4: Capacity Shock.
        Reduces node capacity by documented constant CAPACITY_SHOCK_REDUCTION_RATIO (30%).
        """
        try:
            base_volume, base_prov = self.forecast_model.get_seasonal_baseline_volume(season="punja")
            if base_volume <= 0.0:
                return ScenarioResult(
                    scenario_name="capacity_shock",
                    computable=False,
                    status="insufficient_data",
                    reason=f"No baseline data for {self.district}.",
                    data_provenance=base_prov,
                )

            # Guardrail check against biological ceiling
            validate_forecast(base_volume, self.district, self.crop, self.loader)

            inflows = self._allocate_inflows_to_nodes(base_volume)
            capacities = self._get_node_capacities(shock_reduction=CAPACITY_SHOCK_REDUCTION_RATIO)

            return ScenarioResult(
                scenario_name="capacity_shock",
                computable=True,
                status="computable",
                forecast_inflow=inflows,
                effective_capacities=capacities,
                data_provenance=(
                    f"Scenario 4 (Capacity Shock): Node throughput reduced by "
                    f"{CAPACITY_SHOCK_REDUCTION_RATIO*100:.0f}% due to documented regional canal/storage waterlogging constraint."
                ),
                parameters={
                    "capacity_shock_reduction_ratio": CAPACITY_SHOCK_REDUCTION_RATIO,
                    "base_weekly_tonnes": round(base_volume, 2),
                },
            )
        except ImplausibleForecastError as exc:
            return ScenarioResult(
                scenario_name="capacity_shock",
                computable=False,
                status="rejected_implausible",
                reason=exc.reason,
                data_provenance="Guardrails Layer 4: Rejected physically implausible capacity shock forecast.",
            )

    def run_all_scenarios(self) -> Dict[str, ScenarioResult]:
        """Runs all 4 scenarios and returns dictionary of results."""
        return {
            "baseline": self.forecast_baseline(),
            "weather_shifted": self.forecast_weather_shifted(),
            "adjacent_shock": self.forecast_adjacent_shock(),
            "capacity_shock": self.forecast_capacity_shock(),
        }


if __name__ == "__main__":
    engine = ScenarioEngine(district="Alappuzha", crop="rice")
    results = engine.run_all_scenarios()
    print("Scenario Results Summary:")
    for name, res in results.items():
        status_tag = "[OK]" if res.computable else f"[{res.status.upper()}]"
        print(f"\n{status_tag} Scenario: {name}")
        print(f"  Provenance: {res.data_provenance}")
        if res.computable:
            print(f"  Params: {res.parameters}")
            print(f"  Sample Node Inflows: {list(res.forecast_inflow.items())[:3]}")
        else:
            print(f"  Reason: {res.reason}")
