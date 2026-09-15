"""
Fasal Twin - Data Loader & Schema Enforcement Engine
Enforces strict schema validation, transparent data density reporting,
and custom named error handling without silent imputation.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class FasalTwinDataError(Exception):
    """Base exception for Fasal Twin data validation errors."""
    pass


class MissingDataFileError(FasalTwinDataError):
    """Raised when a required data file is not found on disk."""
    pass


class SchemaValidationError(FasalTwinDataError):
    """Raised when a CSV schema does not match the exact expected contract."""
    pass


class InsufficientDataError(FasalTwinDataError):
    """Raised when data density is too sparse to perform reliable modeling."""
    pass


# Exact schema definitions required by the data contract
EXPECTED_SCHEMAS: Dict[str, List[str]] = {
    "rice_area_production.csv": [
        "district", "crop", "year", "season", "area_ha", "production_tonnes", "productivity_kg_ha", "source"
    ],
    "mandi_arrivals_prices.csv": [
        "district", "market", "crop", "date", "arrival_qty_tonnes", "modal_price_rs_per_quintal", "source"
    ],
    "weather_daily.csv": [
        "district", "date", "rainfall_mm", "forecast_flag", "source"
    ],
    "network_capacity.csv": [
        "node_id", "node_name", "node_type", "district", "capacity_tonnes", "lat", "lon"
    ],
    "network_edges.csv": [
        "from_node_id", "to_node_id", "distance_km", "transit_hours", "transport_cost_per_tonne"
    ],
    "supplyco_procurement.csv": [
        "krishibhavan", "season", "procured_qty_tonnes", "pending_qty_tonnes", "source"
    ],
}


class DataLoader:
    """
    Central Data Ingestion and Validation Engine.
    All models and scenario pipelines must access data solely through this loader.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to repo data/ directory
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        self._cached_dfs: Dict[str, pd.DataFrame] = {}

    def _validate_and_load_csv(self, filename: str, is_optional: bool = False) -> pd.DataFrame:
        filepath = self.data_dir / filename
        if not filepath.exists():
            if is_optional:
                return pd.DataFrame()
            raise MissingDataFileError(
                f"[FasalTwinDataError] Required data file '{filename}' was not found at '{filepath}'. "
                f"Principle 1: Stop step and provide missing file."
            )

        try:
            df = pd.read_csv(filepath)
        except Exception as exc:
            raise FasalTwinDataError(f"Failed to read CSV file '{filename}': {str(exc)}") from exc

        expected_cols = EXPECTED_SCHEMAS.get(filename)
        if expected_cols is not None:
            actual_cols = list(df.columns)
            missing_cols = [col for col in expected_cols if col not in actual_cols]
            if missing_cols:
                raise SchemaValidationError(
                    f"[SchemaValidationError] File '{filename}' failed schema validation! "
                    f"Missing required columns: {missing_cols}. "
                    f"Expected exact columns: {expected_cols}, Actual columns: {actual_cols}."
                )

        return df

    def load_rice_area_production(self) -> pd.DataFrame:
        if "rice_area_production" not in self._cached_dfs:
            df = self._validate_and_load_csv("rice_area_production.csv")
            self._cached_dfs["rice_area_production"] = df
        return self._cached_dfs["rice_area_production"].copy()

    def load_mandi_arrivals_prices(self) -> pd.DataFrame:
        if "mandi_arrivals_prices" not in self._cached_dfs:
            df = self._validate_and_load_csv("mandi_arrivals_prices.csv")
            df["date"] = pd.to_datetime(df["date"])
            self._cached_dfs["mandi_arrivals_prices"] = df
        return self._cached_dfs["mandi_arrivals_prices"].copy()

    def load_weather_daily(self) -> pd.DataFrame:
        if "weather_daily" not in self._cached_dfs:
            df = self._validate_and_load_csv("weather_daily.csv")
            df["date"] = pd.to_datetime(df["date"])
            self._cached_dfs["weather_daily"] = df
        return self._cached_dfs["weather_daily"].copy()

    def load_network_capacity(self) -> pd.DataFrame:
        if "network_capacity" not in self._cached_dfs:
            df = self._validate_and_load_csv("network_capacity.csv")
            valid_types = {"fpo", "mandi", "storage", "processor"}
            invalid_types = set(df["node_type"].unique()) - valid_types
            if invalid_types:
                raise SchemaValidationError(
                    f"Invalid node_type in network_capacity.csv: {invalid_types}. Allowed types: {valid_types}"
                )
            self._cached_dfs["network_capacity"] = df
        return self._cached_dfs["network_capacity"].copy()

    def load_network_edges(self) -> pd.DataFrame:
        if "network_edges" not in self._cached_dfs:
            df = self._validate_and_load_csv("network_edges.csv")
            self._cached_dfs["network_edges"] = df
        return self._cached_dfs["network_edges"].copy()

    def load_supplyco_procurement(self) -> pd.DataFrame:
        if "supplyco_procurement" not in self._cached_dfs:
            df = self._validate_and_load_csv("supplyco_procurement.csv", is_optional=True)
            self._cached_dfs["supplyco_procurement"] = df
        return self._cached_dfs["supplyco_procurement"].copy()

    def data_quality_report(self, district: Optional[str] = None, crop: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a transparent quality report per file and per column.
        Never imputes missing values. Returns density verdict: 'dense', 'sparse', or 'insufficient'.
        """
        report: Dict[str, Any] = {
            "district_filter": district,
            "crop_filter": crop,
            "files": {}
        }

        files_to_check = [
            ("rice_area_production.csv", self.load_rice_area_production, False),
            ("mandi_arrivals_prices.csv", self.load_mandi_arrivals_prices, False),
            ("weather_daily.csv", self.load_weather_daily, False),
            ("network_capacity.csv", self.load_network_capacity, False),
            ("network_edges.csv", self.load_network_edges, False),
            ("supplyco_procurement.csv", self.load_supplyco_procurement, True),
        ]

        for fname, load_fn, is_opt in files_to_check:
            try:
                df = load_fn()
            except MissingDataFileError:
                report["files"][fname] = {
                    "status": "missing",
                    "verdict": "insufficient",
                    "row_count": 0,
                    "columns": {}
                }
                continue

            if df.empty and is_opt:
                report["files"][fname] = {
                    "status": "optional_empty",
                    "verdict": "insufficient",
                    "row_count": 0,
                    "columns": {}
                }
                continue

            # Apply district/crop filter if applicable
            filtered_df = df
            if district and "district" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["district"].str.lower() == district.lower()]
            if crop and "crop" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["crop"].str.lower() == crop.lower()]

            row_count = len(filtered_df)
            col_reports = {}
            for col in EXPECTED_SCHEMAS.get(fname, list(df.columns)):
                if col in filtered_df.columns:
                    missing_pct = round(float(filtered_df[col].isna().mean() * 100), 2)
                    col_reports[col] = {
                        "missing_pct": missing_pct,
                        "present_count": int(filtered_df[col].notna().sum()),
                    }
                else:
                    col_reports[col] = {
                        "missing_pct": 100.0,
                        "present_count": 0,
                        "status": "missing_column"
                    }

            # Year coverage determination
            year_min, year_max = None, None
            if "year" in filtered_df.columns and not filtered_df.empty:
                years = filtered_df["year"].astype(str).tolist()
                year_min, year_max = min(years), max(years)
            elif "date" in filtered_df.columns and not filtered_df.empty:
                dates = pd.to_datetime(filtered_df["date"])
                year_min, year_max = int(dates.dt.year.min()), int(dates.dt.year.max())

            # Verdict rule
            if row_count == 0:
                verdict = "insufficient"
            else:
                max_missing = max([c["missing_pct"] for c in col_reports.values()]) if col_reports else 0.0
                if max_missing > 40.0 or row_count < 24:
                    verdict = "insufficient"
                elif max_missing > 5.0 or row_count < 100:
                    verdict = "sparse"
                else:
                    verdict = "dense"

            report["files"][fname] = {
                "status": "loaded",
                "row_count": row_count,
                "year_min": year_min,
                "year_max": year_max,
                "verdict": verdict,
                "columns": col_reports
            }

        return report

    def print_summary_table(self, district: Optional[str] = None, crop: Optional[str] = None) -> None:
        """Prints a human-readable data quality report table to stdout."""
        report = self.data_quality_report(district, crop)
        print("\n" + "=" * 85)
        print(f" FASAL TWIN DATA QUALITY REPORT (District: {district or 'ALL'}, Crop: {crop or 'ALL'})")
        print("=" * 85)
        print(f"{'File Name':<30} | {'Rows':<8} | {'Year Range':<15} | {'Verdict':<12} | {'Status':<10}")
        print("-" * 85)
        for fname, details in report["files"].items():
            rows = details.get("row_count", 0)
            y_min = details.get("year_min")
            y_max = details.get("year_max")
            y_range = f"{y_min} to {y_max}" if y_min is not None and y_max is not None else "-"
            verdict = details.get("verdict", "unknown").upper()
            status = details.get("status", "unknown")
            print(f"{fname:<30} | {rows:<8} | {y_range:<15} | {verdict:<12} | {status:<10}")
        print("=" * 85 + "\n")


if __name__ == "__main__":
    loader = DataLoader()
    loader.print_summary_table()
    loader.print_summary_table(district="Alappuzha", crop="rice")
