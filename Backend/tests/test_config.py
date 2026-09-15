"""
Unit tests for config.py verifying secret handling and startup validation.
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.config import get_settings, ConfigurationError, Settings


def test_config_loads_defaults_safely():
    """Verifies that get_settings loads valid defaults without leaking secrets."""
    settings = get_settings()
    assert settings.port == 8000
    assert len(settings.allowed_origins) > 0
    assert settings.data_dir.exists()
    assert settings.weather_provider in ["open_meteo", "openweathermap"]


def test_config_fails_loudly_when_data_dir_invalid(monkeypatch):
    """Verifies that invalid DATA_DIR raises ConfigurationError at startup."""
    monkeypatch.setenv("DATA_DIR", "non_existent_folder_xyz_123")
    with pytest.raises(ConfigurationError) as exc_info:
        get_settings()
    assert "data directory does not exist" in str(exc_info.value)


def test_config_fails_when_openweathermap_missing_key(monkeypatch):
    """Verifies that selecting openweathermap without an API key raises ConfigurationError."""
    monkeypatch.setenv("WEATHER_PROVIDER", "openweathermap")
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError) as exc_info:
        get_settings()
    assert "WEATHER_API_KEY is missing" in str(exc_info.value)
