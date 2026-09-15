"""
Unit tests for data_loader.py verifying strict schema contracts and honesty principles.
"""

import sys
import tempfile
from pathlib import Path
import pytest
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader, SchemaValidationError, MissingDataFileError, InsufficientDataError


def test_missing_required_column_raises_schema_validation_error():
    """Verifies that a CSV missing a required column raises SchemaValidationError, not a generic exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create invalid rice_area_production.csv missing 'productivity_kg_ha'
        bad_df = pd.DataFrame({
            "district": ["Alappuzha"],
            "crop": ["rice"],
            "year": ["2020-21"],
            "season": ["punja"],
            "area_ha": [40000],
            "production_tonnes": [100000],
            # 'productivity_kg_ha' is intentionally missing
            "source": ["test"],
        })
        bad_df.to_csv(tmp_path / "rice_area_production.csv", index=False)

        loader = DataLoader(data_dir=str(tmp_path))
        with pytest.raises(SchemaValidationError) as exc_info:
            loader.load_rice_area_production()

        assert "Missing required columns" in str(exc_info.value)
        assert "productivity_kg_ha" in str(exc_info.value)


def test_missing_data_file_raises_named_error():
    """Verifies that a missing required CSV raises MissingDataFileError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = DataLoader(data_dir=str(tmpdir))
        with pytest.raises(MissingDataFileError) as exc_info:
            loader.load_rice_area_production()

        assert "rice_area_production.csv" in str(exc_info.value)


def test_valid_data_loads_and_reports_quality():
    """Verifies that valid project data produces transparent quality reports."""
    loader = DataLoader()
    report = loader.data_quality_report(district="Alappuzha", crop="rice")

    assert "files" in report
    assert "rice_area_production.csv" in report["files"]
    assert report["files"]["rice_area_production.csv"]["status"] == "loaded"
    assert report["files"]["rice_area_production.csv"]["verdict"] in ["dense", "sparse"]
    assert report["files"]["mandi_arrivals_prices.csv"]["verdict"] == "dense"
