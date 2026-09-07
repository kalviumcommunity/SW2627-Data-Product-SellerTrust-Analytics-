import unittest
from pathlib import Path

from src.config_loader import _defaults, get_config, load_config, reload_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_config_returns_dict(self):
        config = load_config()
        self.assertIsInstance(config, dict)

    def test_load_config_has_trust_score_weights(self):
        config = load_config()
        self.assertIn("trust_score_weights", config)
        weights = config["trust_score_weights"]
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_load_config_has_action_thresholds(self):
        config = load_config()
        self.assertIn("action_thresholds", config)
        thresholds = config["action_thresholds"]
        self.assertIn("escalate_score", thresholds)
        self.assertIn("coach_score", thresholds)

    def test_load_config_has_risk_tier_bins(self):
        config = load_config()
        self.assertIn("risk_tier_bins", config)
        bins = config["risk_tier_bins"]
        self.assertEqual(len(bins["bins"]), 5)
        self.assertEqual(len(bins["labels"]), 4)

    def test_load_config_has_anomaly_detection(self):
        config = load_config()
        self.assertIn("anomaly_detection", config)

    def test_load_config_missing_file_returns_defaults(self):
        config = load_config(Path("nonexistent/config.yaml"))
        self.assertIn("trust_score_weights", config)
        self.assertAlmostEqual(sum(config["trust_score_weights"].values()), 1.0, places=6)

    def test_defaults_has_all_required_keys(self):
        defaults = _defaults()
        required = ["trust_score_weights", "action_thresholds", "risk_tier_bins", "anomaly_detection"]
        for key in required:
            self.assertIn(key, defaults)

    def test_get_config_caches_result(self):
        config1 = get_config()
        config2 = get_config()
        self.assertIs(config1, config2)

    def test_reload_config_refreshes(self):
        config1 = get_config()
        config2 = reload_config()
        self.assertIsNot(config1, config2)
        self.assertEqual(config1, config2)

    def test_load_config_with_real_yaml(self):
        config_path = Path("src/config/thresholds.yaml")
        if config_path.is_file():
            config = load_config(config_path)
            self.assertIn("trust_score_weights", config)


if __name__ == "__main__":
    unittest.main()
