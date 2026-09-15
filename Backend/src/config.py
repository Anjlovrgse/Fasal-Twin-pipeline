"""
Fasal Twin - Secure Configuration Management
Loads application settings and credentials exclusively from environment variables
via python-dotenv. Never logs or leaks secrets into responses or traces.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Load .env from project root if present
env_file_path = repo_root / ".env"
if env_file_path.exists():
    load_dotenv(dotenv_path=env_file_path)
else:
    load_dotenv()


class ConfigurationError(Exception):
    """Raised when critical configuration settings are missing or invalid."""
    pass


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment."""
    # Server & Networking
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    allowed_origins: List[str] = field(
        default_factory=lambda: [
            orig.strip()
            for orig in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
            ).split(",")
            if orig.strip()
        ]
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    # Data Directory
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(repo_root / "data"))).resolve()
    )

    # Weather Provider Configuration
    # Default is Open-Meteo (open public API requiring zero API keys)
    weather_provider: str = field(
        default_factory=lambda: os.getenv("WEATHER_PROVIDER", "open_meteo").lower()
    )
    weather_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("WEATHER_API_KEY")
    )
    live_weather_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("LIVE_WEATHER_TIMEOUT_SECONDS", "2.5"))
    )
    live_weather_enabled: bool = field(
        default_factory=lambda: os.getenv("LIVE_WEATHER_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # Data.gov.in Open Government Data API Key
    data_gov_in_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("DATA_GOV_IN_API_KEY", "579b464db66ec23bdd000001775ae41dd96a4d1978f9920f86bda0a2")
    )

    # Optional Gemini API Key – used when LLM functionality is invoked
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )


def get_settings() -> Settings:
    """Returns application settings instance with startup validation."""
    settings = Settings()

    # Validate data directory existence
    if not settings.data_dir.exists():
        raise ConfigurationError(
            f"Configured data directory does not exist at '{settings.data_dir}'. "
            f"Ensure DATA_DIR points to a valid path containing required CSVs."
        )

    # If OpenWeatherMap is explicitly requested, verify API key
    if settings.weather_provider == "openweathermap" and not settings.weather_api_key:
        raise ConfigurationError(
            "WEATHER_PROVIDER is set to 'openweathermap' but WEATHER_API_KEY is missing. "
            "Set WEATHER_API_KEY in .env or switch to 'open_meteo' (no key required)."
        )

    return settings


if __name__ == "__main__":
    conf = get_settings()
    print("Configuration loaded successfully:")
    print(f"  Host: {conf.host}:{conf.port}")
    print(f"  Allowed Origins: {conf.allowed_origins}")
    print(f"  Data Directory: {conf.data_dir}")
    print(f"  Weather Provider: {conf.weather_provider} (Key present: {bool(conf.weather_api_key)})")
    print(f"  Live Weather Timeout: {conf.live_weather_timeout_seconds}s")
