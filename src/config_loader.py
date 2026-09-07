"""Centralized configuration loader for Seller Trust Analytics.

Reads from src/config/thresholds.yaml and provides defaults if the file
is missing or incomplete. All hardcoded magic numbers should flow through here.
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "thresholds.yaml"


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    """Load configuration from YAML file with safe defaults."""
    config_path = Path(path)
    if not config_path.is_file():
        return _defaults()

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    merged = _defaults()
    _deep_merge(merged, data)
    return merged


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _defaults() -> dict:
    return {
        "trust_score_weights": {
            "delivery_performance": 0.30,
            "review_quality": 0.30,
            "cancellation_score": 0.20,
            "negative_review_score": 0.20,
        },
        "min_orders_for_risk_score": 5,
        "action_thresholds": {
            "escalate_score": 45,
            "coach_score": 65,
            "monitor_score": 80,
            "escalate_anomaly_count": 3,
        },
        "risk_tier_bins": {
            "bins": [-0.01, 45, 60, 75, 100],
            "labels": ["High-Risk", "Return-Prone", "Inconsistent", "Reliable"],
        },
        "anomaly_detection": {
            "zscore_threshold": 3.0,
            "iqr_multiplier": 1.5,
        },
    }


_config: dict | None = None


def get_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    """Return cached config. Call reload_config() to refresh."""
    global _config
    if _config is None:
        _config = load_config(path)
    return _config


def reload_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    """Force reload config from disk."""
    global _config
    _config = load_config(path)
    return _config
