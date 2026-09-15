"""
Fasal Twin - Outcome Tracker & Learning Feedback Loop
Maintains an append-only log of recommendations and reconciles forecasts
against actual observed arrivals, tracking scenario accuracy over time.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader

DB_PATH: Path = repo_root / "data" / "outcomes.db"


class OutcomeTracker:
    """
    Append-only recommendation logger and post-harvest outcome reconciler.
    Non-negotiable Principle: Honestly reports calibration sample size N without claiming false maturity.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._is_memory = str(self.db_path) == ":memory:"
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connected SQLite connection."""
        if self._is_memory and self._shared_conn is not None:
            return self._shared_conn
        return sqlite3.connect(self.db_path)

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        """Closes connection if not an in-memory test database."""
        if not self._is_memory:
            conn.close()

    def _init_db(self) -> None:
        """Initializes SQLite tables for append-only alert logging and reconciliation."""
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_logs (
                    recommendation_id TEXT PRIMARY KEY,
                    district TEXT NOT NULL,
                    crop TEXT NOT NULL,
                    chosen_action TEXT NOT NULL,
                    chosen_intervention_id TEXT NOT NULL,
                    confidence_label TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    scenario_outputs_json TEXT NOT NULL,
                    logged_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outcome_reconciliations (
                    recommendation_id TEXT PRIMARY KEY,
                    reconciled_at TEXT NOT NULL,
                    actual_arrivals_json TEXT NOT NULL,
                    closest_scenario TEXT NOT NULL,
                    scenario_errors_json TEXT NOT NULL,
                    FOREIGN KEY(recommendation_id) REFERENCES recommendation_logs(recommendation_id)
                )
            """)
            conn.commit()
        finally:
            self._close_connection(conn)

    def log_alert(
        self,
        recommendation_id: str,
        district: str,
        crop: str,
        chosen_action: str,
        chosen_intervention_id: str,
        confidence_label: str,
        confidence_score: float,
        scenario_outputs: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Logs an alert/recommendation to the append-only database.
        """
        ts = timestamp or datetime.utcnow().isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO recommendation_logs (
                    recommendation_id, district, crop, chosen_action,
                    chosen_intervention_id, confidence_label, confidence_score,
                    scenario_outputs_json, logged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recommendation_id,
                district,
                crop,
                chosen_action,
                chosen_intervention_id,
                confidence_label,
                float(confidence_score),
                json.dumps(scenario_outputs),
                ts,
            ))
            conn.commit()
        finally:
            self._close_connection(conn)

    def reconcile_outcome(
        self,
        recommendation_id: str,
        actual_node_arrivals: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Compares actual observed node arrivals against all 4 scenarios logged for that alert.
        Identifies the scenario with the lowest Mean Absolute Error (MAE).
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT district, crop, scenario_outputs_json FROM recommendation_logs
                WHERE recommendation_id = ?
            """, (recommendation_id,))
            row = cursor.fetchone()

            if not row:
                raise KeyError(f"Recommendation ID '{recommendation_id}' not found in logs.")

            district, crop, sc_json = row
            sc_outputs = json.loads(sc_json)

            scenario_maes: Dict[str, float] = {}

            for sc_name, sc_data in sc_outputs.items():
                forecast_inflows = sc_data.get("forecast_inflow", {})
                if not forecast_inflows:
                    continue

                common_nodes = set(forecast_inflows.keys()) & set(actual_node_arrivals.keys())
                if not common_nodes:
                    continue

                errors = [abs(forecast_inflows[n] - actual_node_arrivals[n]) for n in common_nodes]
                scenario_maes[sc_name] = round(float(np.mean(errors)), 2)

            if not scenario_maes:
                closest_scenario = "unknown"
            else:
                closest_scenario = min(scenario_maes, key=lambda k: scenario_maes[k])

            reconciled_ts = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO outcome_reconciliations (
                    recommendation_id, reconciled_at, actual_arrivals_json,
                    closest_scenario, scenario_errors_json
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                recommendation_id,
                reconciled_ts,
                json.dumps(actual_node_arrivals),
                closest_scenario,
                json.dumps(scenario_maes),
            ))
            conn.commit()

            return {
                "recommendation_id": recommendation_id,
                "district": district,
                "crop": crop,
                "closest_scenario": closest_scenario,
                "scenario_maes": scenario_maes,
                "reconciled_at": reconciled_ts,
            }
        finally:
            self._close_connection(conn)

    def scenario_accuracy_summary(self, district: str = "Alappuzha", crop: str = "rice") -> Dict[str, Any]:
        """
        Aggregates how often each scenario was the closest match historically.
        Explicitly reports sample size N.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.closest_scenario, COUNT(*)
                FROM outcome_reconciliations r
                JOIN recommendation_logs l ON r.recommendation_id = l.recommendation_id
                WHERE LOWER(l.district) = LOWER(?) AND LOWER(l.crop) = LOWER(?)
                GROUP BY r.closest_scenario
            """, (district, crop))
            counts = dict(cursor.fetchall())

            cursor.execute("""
                SELECT COUNT(*) FROM outcome_reconciliations r
                JOIN recommendation_logs l ON r.recommendation_id = l.recommendation_id
                WHERE LOWER(l.district) = LOWER(?) AND LOWER(l.crop) = LOWER(?)
            """, (district, crop))
            total_reconciled = cursor.fetchone()[0]
        finally:
            self._close_connection(conn)

        scenario_wins = {
            "baseline": counts.get("baseline", 0),
            "weather_shifted": counts.get("weather_shifted", 0),
            "adjacent_shock": counts.get("adjacent_shock", 0),
            "capacity_shock": counts.get("capacity_shock", 0),
        }

        if total_reconciled > 0:
            scenario_proportions = {
                k: round((v / total_reconciled) * 100.0, 1) for k, v in scenario_wins.items()
            }
        else:
            scenario_proportions = {k: 0.0 for k in scenario_wins}

        calibration_status = (
            "MATURE_CALIBRATION" if total_reconciled >= 30
            else ("EMERGING_BASELINE" if total_reconciled >= 5 else "INSUFFICIENT_SAMPLE_SIZE")
        )

        provenance = (
            f"Scenario accuracy calibration based on N = {total_reconciled} reconciled post-harvest alerts "
            f"for {district} {crop}. Status: {calibration_status}."
        )

        return {
            "district": district,
            "crop": crop,
            "total_reconciled_alerts": total_reconciled,
            "calibration_status": calibration_status,
            "scenario_win_counts": scenario_wins,
            "scenario_win_percentages": scenario_proportions,
            "data_provenance": provenance,
            "caution_note": (
                "Caution: Sample size N is too small to reweight scenario blending automatically. "
                "Displayed for transparent auditability only."
                if total_reconciled < 30
                else "Calibrated: Historical scenario weights can be utilized for Bayesian scenario blending."
            ),
        }


if __name__ == "__main__":
    tracker = OutcomeTracker()

    # Log a mock alert
    test_id = "rec-test-001"
    tracker.log_alert(
        recommendation_id=test_id,
        district="Alappuzha",
        crop="rice",
        chosen_action="Staggered Farmgate Holding",
        chosen_intervention_id="INT-2",
        confidence_label="HIGH",
        confidence_score=0.98,
        scenario_outputs={
            "baseline": {"forecast_inflow": {"M1": 7200.0, "M3": 6050.0}},
            "weather_shifted": {"forecast_inflow": {"M1": 8650.0, "M3": 7270.0}},
            "adjacent_shock": {"forecast_inflow": {"M1": 9700.0, "M3": 8150.0}},
            "capacity_shock": {"forecast_inflow": {"M1": 7200.0, "M3": 6050.0}},
        }
    )

    # Reconcile with actual observed data
    rec_res = tracker.reconcile_outcome(
        recommendation_id=test_id,
        actual_node_arrivals={"M1": 8400.0, "M3": 7100.0}
    )
    print("Reconciled Outcome:", rec_res)

    summary = tracker.scenario_accuracy_summary(district="Alappuzha", crop="rice")
    print("\nScenario Accuracy Summary:")
    print(summary)
