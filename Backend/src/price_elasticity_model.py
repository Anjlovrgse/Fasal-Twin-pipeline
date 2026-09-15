"""
Fasal Twin - Explainable Price Elasticity Model
Fits an interpretable linear and log-log econometric regression to estimate
price impact from mandi arrival volumes per district and crop.

Upgraded with:
- Strict temporal train/test splitting (no future data leakage, no random shuffle)
- Multi-fold temporal walk-forward validation (honest repeated estimation)
- Joblib model serialization and startup persistence
- Directly exposes data density, R^2, MAE, RMSE, and sample size for the confidence gate.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader, InsufficientDataError

# Non-negotiable minimum observation threshold
MIN_OBSERVATIONS_THRESHOLD = 24
DEFAULT_MODELS_DIR = repo_root / "models"


class PriceElasticityModel:
    """
    Econometric model estimating price responsiveness to volume surges.
    Non-negotiable Principle: Never fabricate a fit when observations < MIN_OBSERVATIONS_THRESHOLD.
    """

    def __init__(
        self,
        district: str = "Alappuzha",
        crop: str = "rice",
        min_observations: int = MIN_OBSERVATIONS_THRESHOLD,
        loader: Optional[DataLoader] = None,
    ):
        self.district = district
        self.crop = crop
        self.min_observations = min_observations
        self.loader = loader or DataLoader()

        self.is_fitted: bool = False
        self.status: str = "unfitted"  # 'fitted' | 'insufficient_data'
        self.n_observations: int = 0
        self.n_train: int = 0
        self.n_test: int = 0
        self.cutoff_date: str = "latest"

        # Regression Parameters
        self.r_squared: float = 0.0
        self.slope: float = 0.0
        self.intercept: float = 0.0
        self.elasticity: float = 0.0  # Log-log elasticity (% dP / % dQ)
        self.mean_price: float = 0.0
        self.mean_arrivals: float = 0.0

        # Evaluation Metrics (Test Set & Walk-Forward)
        self.test_mae: float = 0.0
        self.test_rmse: float = 0.0
        self.test_r2: float = 0.0
        self.walk_forward_metrics: Dict[str, Any] = {}

        self.data_provenance: str = ""
        self._linear_model: Optional[LinearRegression] = None
        self._log_model: Optional[LinearRegression] = None

    def _prepare_data(self, df_mandi: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Filters and sorts mandi data chronologically."""
        if df_mandi is None:
            df_mandi = self.loader.load_mandi_arrivals_prices()

        sub_df = df_mandi[
            (df_mandi["district"].str.lower() == self.district.lower()) &
            (df_mandi["crop"].str.lower() == self.crop.lower()) &
            (df_mandi["arrival_qty_tonnes"] > 0) &
            (df_mandi["modal_price_rs_per_quintal"] > 0)
        ].copy()
        # Filter out rows where arrival data is not available, if column exists
        if "arrival_data_available" in sub_df.columns:
            sub_df = sub_df[sub_df["arrival_data_available"]]

        if "date" in sub_df.columns:
            sub_df["date"] = pd.to_datetime(sub_df["date"])
            sub_df = sub_df.sort_values(by="date").reset_index(drop=True)

        return sub_df

    def fit(
        self,
        df_mandi: Optional[pd.DataFrame] = None,
        train_test_split_date: Optional[str] = "2023-12-31",
    ) -> "PriceElasticityModel":
        """
        Fits linear and log-log regressions using strict temporal train/test partitioning.
        Evaluates test set performance without random data shuffling.
        """
        sub_df = self._prepare_data(df_mandi)
        self.n_observations = len(sub_df)

        if self.n_observations < self.min_observations:
            self.is_fitted = False
            self.status = "insufficient_data"
            self.data_provenance = (
                f"Insufficient Agmarknet observations for {self.district} {self.crop}: "
                f"found {self.n_observations} rows, minimum required is {self.min_observations}."
            )
            return self

        # Temporal Train/Test Split
        if train_test_split_date and "date" in sub_df.columns:
            split_dt = pd.to_datetime(train_test_split_date)
            train_df = sub_df[sub_df["date"] <= split_dt].copy()
            test_df = sub_df[sub_df["date"] > split_dt].copy()
            self.cutoff_date = train_test_split_date

            # If split yields insufficient train data, fallback to 80/20 temporal index split
            if len(train_df) < self.min_observations:
                split_idx = int(len(sub_df) * 0.8)
                train_df = sub_df.iloc[:split_idx].copy()
                test_df = sub_df.iloc[split_idx:].copy()
                self.cutoff_date = str(train_df["date"].max().date()) if "date" in train_df.columns else "temporal-80pct"
        else:
            split_idx = int(len(sub_df) * 0.8)
            train_df = sub_df.iloc[:split_idx].copy()
            test_df = sub_df.iloc[split_idx:].copy()
            self.cutoff_date = str(train_df["date"].max().date()) if "date" in train_df.columns else "temporal-80pct"

        self.n_train = len(train_df)
        self.n_test = len(test_df)

        # Train features
        Q_train = train_df["arrival_qty_tonnes"].values.reshape(-1, 1)
        P_train = train_df["modal_price_rs_per_quintal"].values

        lin_reg = LinearRegression()
        lin_reg.fit(Q_train, P_train)

        self._linear_model = lin_reg
        self.slope = float(lin_reg.coef_[0])
        self.intercept = float(lin_reg.intercept_)
        self.r_squared = float(lin_reg.score(Q_train, P_train))
        self.mean_price = float(np.mean(P_train))
        self.mean_arrivals = float(np.mean(Q_train))

        # Log-log regression on training data
        log_Q_train = np.log(Q_train)
        log_P_train = np.log(P_train)
        log_reg = LinearRegression()
        log_reg.fit(log_Q_train, log_P_train)
        self._log_model = log_reg
        self.elasticity = float(log_reg.coef_[0])

        # Test set evaluation
        if self.n_test > 0:
            Q_test = test_df["arrival_qty_tonnes"].values.reshape(-1, 1)
            P_test = test_df["modal_price_rs_per_quintal"].values
            P_pred = lin_reg.predict(Q_test)

            self.test_mae = float(mean_absolute_error(P_test, P_pred))
            self.test_rmse = float(np.sqrt(mean_squared_error(P_test, P_pred)))
            self.test_r2 = float(r2_score(P_test, P_pred)) if len(P_test) > 1 else 0.0
        else:
            self.test_mae = 0.0
            self.test_rmse = 0.0
            self.test_r2 = 0.0

        # Execute walk-forward validation across historical temporal slices
        self.walk_forward_metrics = self.run_walk_forward_validation(sub_df)

        self.is_fitted = True
        self.status = "fitted"

        min_year = sub_df["date"].dt.year.min() if "date" in sub_df.columns else "N/A"
        max_year = sub_df["date"].dt.year.max() if "date" in sub_df.columns else "N/A"

        self.data_provenance = (
            f"Fitted on {self.n_train} temporal training records (tested on {self.n_test} holdout records) "
            f"from Agmarknet mandi data covering {min_year} to {max_year} for {self.district} {self.crop}. "
            f"Train R² = {self.r_squared:.4f}, Test R² = {self.test_r2:.4f}, Test MAE = Rs {self.test_mae:.2f}/qtl, "
            f"Slope = {self.slope:.4f} Rs/qtl per tonne, Elasticity = {self.elasticity:.4f}."
        )

        return self

    def run_walk_forward_validation(self, sub_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Walk-Forward Cross-Validation:
        Iteratively trains on expanding historical windows and evaluates on the subsequent season/year.
        Prevents lookahead bias and provides an honest multi-period evaluation.
        """
        if sub_df is None:
            sub_df = self._prepare_data()

        if len(sub_df) < self.min_observations or "date" not in sub_df.columns:
            return {"status": "insufficient_data_for_walk_forward", "folds": []}

        sub_df["year"] = sub_df["date"].dt.year
        unique_years = sorted(sub_df["year"].unique())

        folds: List[Dict[str, Any]] = []
        # Walk-forward requires at least 1 prior training year and 1 testing year
        if len(unique_years) < 2:
            # Fallback to 3 sequential temporal block folds
            n_records = len(sub_df)
            block_size = n_records // 4
            for fold_idx in range(1, 4):
                train_slice = sub_df.iloc[: (fold_idx + 1) * block_size]
                test_slice = sub_df.iloc[(fold_idx + 1) * block_size : min(n_records, (fold_idx + 2) * block_size)]
                if len(train_slice) < self.min_observations or len(test_slice) < 5:
                    continue
                Q_tr = train_slice["arrival_qty_tonnes"].values.reshape(-1, 1)
                P_tr = train_slice["modal_price_rs_per_quintal"].values
                Q_te = test_slice["arrival_qty_tonnes"].values.reshape(-1, 1)
                P_te = test_slice["modal_price_rs_per_quintal"].values

                m = LinearRegression().fit(Q_tr, P_tr)
                preds = m.predict(Q_te)
                folds.append({
                    "fold_index": fold_idx,
                    "train_window": f"Block 0 to {fold_idx}",
                    "test_window": f"Block {fold_idx + 1}",
                    "n_train": len(train_slice),
                    "n_test": len(test_slice),
                    "train_r2": round(float(m.score(Q_tr, P_tr)), 4),
                    "test_r2": round(float(r2_score(P_te, preds)), 4) if len(P_te) > 1 else 0.0,
                    "test_mae": round(float(mean_absolute_error(P_te, preds)), 2),
                    "test_rmse": round(float(np.sqrt(mean_squared_error(P_te, preds))), 2),
                    "slope": round(float(m.coef_[0]), 4),
                })
        else:
            for i in range(1, len(unique_years)):
                test_yr = unique_years[i]
                train_df = sub_df[sub_df["year"] < test_yr]
                test_df = sub_df[sub_df["year"] == test_yr]

                if len(train_df) < self.min_observations or len(test_df) < 5:
                    continue

                Q_tr = train_df["arrival_qty_tonnes"].values.reshape(-1, 1)
                P_tr = train_df["modal_price_rs_per_quintal"].values
                Q_te = test_df["arrival_qty_tonnes"].values.reshape(-1, 1)
                P_te = test_df["modal_price_rs_per_quintal"].values

                m = LinearRegression().fit(Q_tr, P_tr)
                preds = m.predict(Q_te)

                folds.append({
                    "fold_index": len(folds) + 1,
                    "train_window": f"<= {unique_years[i-1]}",
                    "test_window": f"Year {test_yr}",
                    "n_train": len(train_df),
                    "n_test": len(test_df),
                    "train_r2": round(float(m.score(Q_tr, P_tr)), 4),
                    "test_r2": round(float(r2_score(P_te, preds)), 4) if len(P_te) > 1 else 0.0,
                    "test_mae": round(float(mean_absolute_error(P_te, preds)), 2),
                    "test_rmse": round(float(np.sqrt(mean_squared_error(P_te, preds))), 2),
                    "slope": round(float(m.coef_[0]), 4),
                })

        if folds:
            avg_r2 = float(np.mean([f["test_r2"] for f in folds]))
            avg_mae = float(np.mean([f["test_mae"] for f in folds]))
            avg_rmse = float(np.mean([f["test_rmse"] for f in folds]))
        else:
            avg_r2, avg_mae, avg_rmse = 0.0, 0.0, 0.0

        return {
            "status": "completed",
            "n_folds": len(folds),
            "aggregate_test_r2": round(avg_r2, 4),
            "aggregate_test_mae_rs": round(avg_mae, 2),
            "aggregate_test_rmse_rs": round(avg_rmse, 2),
            "folds": folds,
        }

    def predict_price(self, arrival_qty_tonnes: float) -> float:
        """Predicts modal price (Rs/quintal) for a given arrival volume."""
        if not self.is_fitted:
            raise InsufficientDataError(
                f"Cannot predict price: Model for {self.district} {self.crop} has status '{self.status}'."
            )
        pred = self.intercept + self.slope * arrival_qty_tonnes
        return max(500.0, float(pred))

    def estimate_price_impact(
        self,
        base_arrival_tonnes: float,
        intervention_arrival_tonnes: float,
        base_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Translates a change in arrival volume into price and revenue impact.
        Returns: {delta_qty, delta_price, new_price, base_price, pct_price_change, provenance}
        """
        if not self.is_fitted:
            return {
                "computable": False,
                "status": self.status,
                "reason": self.data_provenance,
            }

        effective_base_price = base_price if base_price is not None else self.predict_price(base_arrival_tonnes)
        delta_qty = intervention_arrival_tonnes - base_arrival_tonnes
        delta_price = self.slope * delta_qty
        new_price = max(500.0, effective_base_price + delta_price)
        pct_price_change = ((new_price - effective_base_price) / effective_base_price) * 100.0

        return {
            "computable": True,
            "base_arrival_tonnes": round(base_arrival_tonnes, 2),
            "intervention_arrival_tonnes": round(intervention_arrival_tonnes, 2),
            "delta_qty_tonnes": round(delta_qty, 2),
            "base_price_rs_per_quintal": round(effective_base_price, 2),
            "new_price_rs_per_quintal": round(new_price, 2),
            "delta_price_rs_per_quintal": round(delta_price, 2),
            "pct_price_change": round(pct_price_change, 2),
            "r_squared": round(self.r_squared, 4),
            "test_mae_rs": round(self.test_mae, 2),
            "elasticity": round(self.elasticity, 4),
            "data_provenance": self.data_provenance,
        }

    def save(self, filepath: Optional[Path] = None) -> Path:
        """Persists trained model artifact via joblib."""
        if not self.is_fitted:
            raise ValueError("Cannot persist unfitted model.")
        if filepath is None:
            models_dir = DEFAULT_MODELS_DIR
            models_dir.mkdir(parents=True, exist_ok=True)
            cutoff_slug = self.cutoff_date.replace(":", "-").replace(" ", "_")[:10]
            filename = f"price_elasticity_{self.district.lower()}_{self.crop.lower()}_{cutoff_slug}.joblib"
            filepath = models_dir / filename

        artifact = {
            "model_type": "PriceElasticityModel",
            "district": self.district,
            "crop": self.crop,
            "cutoff_date": self.cutoff_date,
            "n_observations": self.n_observations,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "r_squared": self.r_squared,
            "slope": self.slope,
            "intercept": self.intercept,
            "elasticity": self.elasticity,
            "mean_price": self.mean_price,
            "mean_arrivals": self.mean_arrivals,
            "test_mae": self.test_mae,
            "test_rmse": self.test_rmse,
            "test_r2": self.test_r2,
            "walk_forward_metrics": self.walk_forward_metrics,
            "data_provenance": self.data_provenance,
            "linear_model": self._linear_model,
            "log_model": self._log_model,
        }
        joblib.dump(artifact, filepath)
        return filepath

    @classmethod
    def load(cls, filepath: Path, loader: Optional[DataLoader] = None) -> "PriceElasticityModel":
        """Loads a persisted model artifact from disk."""
        artifact = joblib.load(filepath)
        instance = cls(
            district=artifact["district"],
            crop=artifact["crop"],
            loader=loader or DataLoader(),
        )
        instance.is_fitted = True
        instance.status = "fitted"
        instance.cutoff_date = artifact.get("cutoff_date", "persisted")
        instance.n_observations = artifact["n_observations"]
        instance.n_train = artifact.get("n_train", instance.n_observations)
        instance.n_test = artifact.get("n_test", 0)
        instance.r_squared = artifact["r_squared"]
        instance.slope = artifact["slope"]
        instance.intercept = artifact["intercept"]
        instance.elasticity = artifact["elasticity"]
        instance.mean_price = artifact["mean_price"]
        instance.mean_arrivals = artifact["mean_arrivals"]
        instance.test_mae = artifact.get("test_mae", 0.0)
        instance.test_rmse = artifact.get("test_rmse", 0.0)
        instance.test_r2 = artifact.get("test_r2", 0.0)
        instance.walk_forward_metrics = artifact.get("walk_forward_metrics", {})
        instance.data_provenance = artifact["data_provenance"]
        instance._linear_model = artifact["linear_model"]
        instance._log_model = artifact.get("log_model")
        return instance

    def get_summary(self) -> Dict[str, Any]:
        """Returns model metadata and parameters for confidence scoring and explanations."""
        return {
            "district": self.district,
            "crop": self.crop,
            "is_fitted": self.is_fitted,
            "status": self.status,
            "cutoff_date": self.cutoff_date,
            "n_observations": self.n_observations,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "r_squared": round(self.r_squared, 4) if self.is_fitted else None,
            "slope": round(self.slope, 4) if self.is_fitted else None,
            "intercept": round(self.intercept, 2) if self.is_fitted else None,
            "elasticity": round(self.elasticity, 4) if self.is_fitted else None,
            "mean_price": round(self.mean_price, 2) if self.is_fitted else None,
            "test_mae_rs": round(self.test_mae, 2) if self.is_fitted else None,
            "test_rmse_rs": round(self.test_rmse, 2) if self.is_fitted else None,
            "test_r2": round(self.test_r2, 4) if self.is_fitted else None,
            "walk_forward_summary": self.walk_forward_metrics,
            "data_provenance": self.data_provenance,
        }


if __name__ == "__main__":
    model = PriceElasticityModel(district="Alappuzha", crop="rice")
    model.fit(train_test_split_date="2023-12-31")
    saved_path = model.save()
    print(f"Model fitted and persisted to {saved_path}")
    print("\nSummary:")
    print(model.get_summary())
