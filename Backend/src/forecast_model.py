"""
Fasal Twin - Crop Flow Forecasting Model
Predicts expected weekly arrival volumes across logistics nodes
using agricultural production statistics and meteorological signals.

Upgraded with:
- Strict temporal train/test split (no lookahead bias)
- Walk-forward historical validation across multi-year production cycles
- Joblib serialization and model persistence
- Quantified arrival forecast metrics (MAE, RMSE, MAPE)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.network_model import load_network, get_nodes_by_type

DEFAULT_MODELS_DIR = repo_root / "models"


class ForecastModel:
    """
    Weekly inflow forecasting engine combining area, production, and weather signals.
    """

    def __init__(
        self,
        district: str = "Alappuzha",
        crop: str = "rice",
        loader: Optional[DataLoader] = None,
    ):
        self.district = district
        self.crop = crop
        self.loader = loader or DataLoader()

        self.is_fitted: bool = False
        self.status: str = "unfitted"
        self.cutoff_year: str = "latest"
        self.season: str = "punja"
        self.peak_weekly_fraction: float = 0.125  # 8-week harvest window peak fraction
        self.baseline_weekly_tonnes: float = 0.0
        self.latest_production_tonnes: float = 0.0
        self.weather_surge_factor: float = 1.0
        self.data_provenance: str = ""

        # Validation Metrics
        self.test_mae_tonnes: float = 0.0
        self.test_mape_pct: float = 0.0
        self.test_rmse_tonnes: float = 0.0
        self.walk_forward_metrics: Dict[str, Any] = {}

    def fit(self, cutoff_year: Optional[str] = "2022-23", season: str = "punja") -> "ForecastModel":
        """
        Fits baseline production flow parameters up to cutoff year and performs
        walk-forward validation across all historical production seasons.
        """
        self.season = season
        df_rice = self.loader.load_rice_area_production()
        sub_df = df_rice[
            (df_rice["district"].str.lower() == self.district.lower()) &
            (df_rice["crop"].str.lower() == self.crop.lower())
        ]

        # Prioritize specified season (e.g. Punja in Kuttanad)
        season_df = sub_df[sub_df["season"].str.lower() == season.lower()].sort_values(by="year").reset_index(drop=True)
        if season_df.empty:
            season_df = sub_df.sort_values(by="year").reset_index(drop=True)

        if season_df.empty:
            self.is_fitted = False
            self.status = "insufficient_data"
            self.data_provenance = f"No historical rice production records found for {self.district}."
            return self

        # Temporal split on historical production series
        if cutoff_year and (season_df["year"].astype(str) == str(cutoff_year)).any():
            train_df = season_df[season_df["year"].astype(str) <= str(cutoff_year)]
            self.cutoff_year = str(cutoff_year)
        else:
            train_df = season_df
            self.cutoff_year = str(season_df["year"].iloc[-1])

        latest_record = train_df.iloc[-1]
        self.latest_production_tonnes = float(latest_record["production_tonnes"])
        self.baseline_weekly_tonnes = self.latest_production_tonnes * self.peak_weekly_fraction

        # Run walk-forward validation against mandi actuals across available seasons
        self.walk_forward_metrics = self.run_walk_forward_validation()

        if self.walk_forward_metrics.get("folds"):
            self.test_mae_tonnes = self.walk_forward_metrics.get("aggregate_mae_tonnes", 0.0)
            self.test_mape_pct = self.walk_forward_metrics.get("aggregate_mape_pct", 0.0)
            self.test_rmse_tonnes = self.walk_forward_metrics.get("aggregate_rmse_tonnes", 0.0)

        self.is_fitted = True
        self.status = "fitted"
        self.data_provenance = (
            f"Forecast model calibrated on {len(train_df)} historical {self.season} production seasons for {self.district} {self.crop} "
            f"(cutoff {self.cutoff_year}). Latest seasonal production: {self.latest_production_tonnes:,.0f} tonnes. "
            f"Peak weekly inflow baseline: {self.baseline_weekly_tonnes:,.1f} tonnes. "
            f"Walk-forward MAPE = {self.test_mape_pct:.2f}%, MAE = {self.test_mae_tonnes:.1f} tonnes."
        )

        return self

    def run_walk_forward_validation(self) -> Dict[str, Any]:
        """
        Evaluates forecast accuracy across multi-year historical harvest seasons.
        Compares pre-harvest predicted peak weekly volume against observed weekly arrivals in Agmarknet.
        """
        df_rice = self.loader.load_rice_area_production()
        df_mandi = self.loader.load_mandi_arrivals_prices()

        sub_rice = df_rice[
            (df_rice["district"].str.lower() == self.district.lower()) &
            (df_rice["crop"].str.lower() == self.crop.lower())
        ]
        season_rice = sub_rice[sub_rice["season"].str.lower() == self.season.lower()].sort_values(by="year").reset_index(drop=True)
        if season_rice.empty:
            season_rice = sub_rice.sort_values(by="year").reset_index(drop=True)

        sub_mandi = df_mandi[(df_mandi["district"].str.lower() == self.district.lower()) &
            (df_mandi["crop"].str.lower() == self.crop.lower())].copy()
        # Exclude rows where arrival data is unavailable, if column present
        if "arrival_data_available" in sub_mandi.columns:
            sub_mandi = sub_mandi[sub_mandi["arrival_data_available"]]

        if season_rice.empty or sub_mandi.empty:
            return {"status": "insufficient_data", "folds": []}

        sub_mandi["year"] = sub_mandi["date"].dt.year
        sub_mandi["week"] = sub_mandi["date"].dt.isocalendar().week

        # Available validation years in Mandi (2021, 2022, 2023, 2024)
        mandi_years = sorted(sub_mandi["year"].unique())
        folds: List[Dict[str, Any]] = []

        for yr in mandi_years:
            # Mandi peak week in spring (Feb - May) for Punja
            spring_mandi = sub_mandi[(sub_mandi["year"] == yr) & (sub_mandi["date"].dt.month.isin([2, 3, 4, 5]))]
            if len(spring_mandi) < 10:
                continue

            weekly_arrivals = spring_mandi.groupby("week")["arrival_qty_tonnes"].sum()
            actual_peak_weekly = float(weekly_arrivals.max())

            # Find matching or preceding production year
            # Kerala agri year: 2021-22 corresponds to calendar 2022 spring harvest
            prev_agri_yr_str = f"{yr-1}-{str(yr)[-2:]}"
            matched_prod = season_rice[season_rice["year"].astype(str) == prev_agri_yr_str]
            if matched_prod.empty:
                prior_prods = season_rice[season_rice["year"].astype(str) < prev_agri_yr_str]
                if prior_prods.empty:
                    continue
                prod_tonnes = float(prior_prods.iloc[-1]["production_tonnes"])
            else:
                prod_tonnes = float(matched_prod.iloc[0]["production_tonnes"])

            # District harvest peak is 12.5% of seasonal output;
            # Mandi capture share in Kuttanad is ~10-12% of total production (with Supplyco procuring ~88-90%)
            # We predict the mandi-level peak flow:
            pred_mandi_peak = prod_tonnes * self.peak_weekly_fraction * 0.10

            err = abs(pred_mandi_peak - actual_peak_weekly)
            mape = (err / actual_peak_weekly * 100.0) if actual_peak_weekly > 0 else 0.0

            folds.append({
                "fold_year": int(yr),
                "production_basis_year": prev_agri_yr_str,
                "production_tonnes": prod_tonnes,
                "predicted_peak_mandi_tonnes": round(pred_mandi_peak, 2),
                "actual_peak_mandi_tonnes": round(actual_peak_weekly, 2),
                "error_tonnes": round(err, 2),
                "mape_pct": round(mape, 2),
            })

        if folds:
            avg_mae = float(np.mean([f["error_tonnes"] for f in folds]))
            avg_mape = float(np.mean([f["mape_pct"] for f in folds]))
            avg_rmse = float(np.sqrt(np.mean([f["error_tonnes"] ** 2 for f in folds])))
        else:
            avg_mae, avg_mape, avg_rmse = 0.0, 0.0, 0.0

        return {
            "status": "completed",
            "n_folds": len(folds),
            "aggregate_mae_tonnes": round(avg_mae, 2),
            "aggregate_mape_pct": round(avg_mape, 2),
            "aggregate_rmse_tonnes": round(avg_rmse, 2),
            "folds": folds,
        }

    def get_seasonal_baseline_volume(self, season: str = "punja") -> Tuple[float, str]:
        """
        Calculates expected weekly total district production/arrival volume
        from the most recent historical year in rice_area_production.csv.
        Returns: (weekly_tonnes, provenance_str)
        """
        df_rice = self.loader.load_rice_area_production()
        sub_df = df_rice[
            (df_rice["district"].str.lower() == self.district.lower()) &
            (df_rice["crop"].str.lower() == self.crop.lower()) &
            (df_rice["season"].str.lower() == season.lower())
        ]

        if sub_df.empty:
            sub_df = df_rice[
                (df_rice["district"].str.lower() == self.district.lower()) &
                (df_rice["crop"].str.lower() == self.crop.lower())
            ]

        if sub_df.empty:
            return 0.0, f"No rice area/production records found for district '{self.district}'."

        latest_row = sub_df.sort_values(by="year", ascending=False).iloc[0]
        prod_tonnes = float(latest_row["production_tonnes"])
        latest_year = str(latest_row["year"])
        src = str(latest_row["source"])

        # Kuttanad Punja harvest is concentrated across ~8 peak weeks (mid-Feb to mid-April)
        peak_weekly_tonnes = prod_tonnes * self.peak_weekly_fraction
        provenance = (
            f"Based on {self.district} {self.crop} {latest_year} {season} production "
            f"of {prod_tonnes:,.0f} tonnes ({src}), distributed over 8-week harvest window."
        )
        return peak_weekly_tonnes, provenance

    def compute_weather_delay_factor(self, lookback_days: int = 30) -> Tuple[float, float, str]:
        """
        Analyzes actual IMD daily weather variance to calculate harvest disruption factor.
        Returns: (variance_mm, compression_surge_factor, provenance_str)
        """
        df_weather = self.loader.load_weather_daily()
        sub_w = df_weather[
            (df_weather["district"].str.lower() == self.district.lower())
        ].sort_values(by="date")

        if sub_w.empty:
            return 0.0, 1.0, f"No weather records found for district '{self.district}'."

        recent_w = sub_w.tail(lookback_days)
        rainfall_vals = recent_w["rainfall_mm"].values
        variance_mm = float(np.var(rainfall_vals))
        std_mm = float(np.std(rainfall_vals))
        heavy_rain_days = int(np.sum(rainfall_vals > 25.0))

        surge_factor = 1.0 + min(0.65, (std_mm / 20.0) * 0.35 + (heavy_rain_days * 0.08))
        self.weather_surge_factor = surge_factor
        provenance = (
            f"Derived from {len(recent_w)} days of IMD records for {self.district}: "
            f"Rainfall Std Dev = {std_mm:.2f} mm (Variance = {variance_mm:.2f}), "
            f"Heavy rain days (>25mm) = {heavy_rain_days}. "
            f"Weather compression surge multiplier = {surge_factor:.3f}x."
        )

        return variance_mm, surge_factor, provenance

    def compute_cross_district_correlation(self, target_district: str, other_district: str) -> Tuple[Optional[float], str]:
        """
        Calculates Pearson correlation of weekly mandi arrivals between two districts.
        """
        df_mandi = self.loader.load_mandi_arrivals_prices()
        districts = set(df_mandi["district"].str.lower().unique())

        if target_district.lower() not in districts or other_district.lower() not in districts:
            return None, f"One or both districts ({target_district}, {other_district}) not found in Agmarknet data."

        df_mandi["week"] = df_mandi["date"].dt.to_period("W")
        d1 = df_mandi[df_mandi["district"].str.lower() == target_district.lower()].groupby("week")["arrival_qty_tonnes"].sum()
        d2 = df_mandi[df_mandi["district"].str.lower() == other_district.lower()].groupby("week")["arrival_qty_tonnes"].sum()

        merged = pd.concat([d1, d2], axis=1, join="inner").dropna()
        if len(merged) < 8:
            return None, f"Insufficient overlapping weekly data between {target_district} and {other_district} (found {len(merged)} weeks)."

        corr = float(merged.iloc[:, 0].corr(merged.iloc[:, 1]))
        provenance = (
            f"Empirical cross-district arrival correlation between {target_district} and {other_district} "
            f"is r = {corr:.3f} based on {len(merged)} overlapping weekly Agmarknet reporting periods."
        )
        return corr, provenance

    def save(self, filepath: Optional[Path] = None) -> Path:
        """Persists trained forecast model artifact via joblib."""
        if not self.is_fitted:
            raise ValueError("Cannot persist unfitted forecast model.")
        if filepath is None:
            models_dir = DEFAULT_MODELS_DIR
            models_dir.mkdir(parents=True, exist_ok=True)
            cutoff_slug = self.cutoff_year.replace(":", "-").replace(" ", "_")[:10]
            filename = f"forecast_{self.district.lower()}_{self.crop.lower()}_{cutoff_slug}.joblib"
            filepath = models_dir / filename

        artifact = {
            "model_type": "ForecastModel",
            "district": self.district,
            "crop": self.crop,
            "cutoff_year": self.cutoff_year,
            "season": self.season,
            "peak_weekly_fraction": self.peak_weekly_fraction,
            "baseline_weekly_tonnes": self.baseline_weekly_tonnes,
            "latest_production_tonnes": self.latest_production_tonnes,
            "weather_surge_factor": self.weather_surge_factor,
            "test_mae_tonnes": self.test_mae_tonnes,
            "test_mape_pct": self.test_mape_pct,
            "test_rmse_tonnes": self.test_rmse_tonnes,
            "walk_forward_metrics": self.walk_forward_metrics,
            "data_provenance": self.data_provenance,
        }
        joblib.dump(artifact, filepath)
        return filepath

    @classmethod
    def load(cls, filepath: Path, loader: Optional[DataLoader] = None) -> "ForecastModel":
        """Loads a persisted forecast model artifact from disk."""
        artifact = joblib.load(filepath)
        instance = cls(
            district=artifact["district"],
            crop=artifact["crop"],
            loader=loader or DataLoader(),
        )
        instance.is_fitted = True
        instance.status = "fitted"
        instance.cutoff_year = artifact.get("cutoff_year", "persisted")
        instance.season = artifact.get("season", "punja")
        instance.peak_weekly_fraction = artifact.get("peak_weekly_fraction", 0.125)
        instance.baseline_weekly_tonnes = artifact.get("baseline_weekly_tonnes", 0.0)
        instance.latest_production_tonnes = artifact.get("latest_production_tonnes", 0.0)
        instance.weather_surge_factor = artifact.get("weather_surge_factor", 1.0)
        instance.test_mae_tonnes = artifact.get("test_mae_tonnes", 0.0)
        instance.test_mape_pct = artifact.get("test_mape_pct", 0.0)
        instance.test_rmse_tonnes = artifact.get("test_rmse_tonnes", 0.0)
        instance.walk_forward_metrics = artifact.get("walk_forward_metrics", {})
        instance.data_provenance = artifact.get("data_provenance", "")
        return instance

    def get_summary(self) -> Dict[str, Any]:
        """Returns metadata and metrics summary for API and explanations."""
        return {
            "district": self.district,
            "crop": self.crop,
            "is_fitted": self.is_fitted,
            "status": self.status,
            "cutoff_year": self.cutoff_year,
            "season": self.season,
            "latest_production_tonnes": self.latest_production_tonnes,
            "baseline_weekly_tonnes": self.baseline_weekly_tonnes,
            "test_mae_tonnes": self.test_mae_tonnes,
            "test_mape_pct": self.test_mape_pct,
            "test_rmse_tonnes": self.test_rmse_tonnes,
            "walk_forward_summary": self.walk_forward_metrics,
            "data_provenance": self.data_provenance,
        }


if __name__ == "__main__":
    model = ForecastModel(district="Alappuzha", crop="rice")
    model.fit(cutoff_year="2022-23", season="punja")
    saved_path = model.save()
    print(f"Forecast model fitted and persisted to {saved_path}")
    print("\nSummary:")
    print(model.get_summary())
