import json
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import scripts.etl_pipeline as etl_module
from scripts.etl_pipeline import main, run_etl

from .sample_olist_data import write_sample_raw_files


class EtlPipelineTests(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path("tmp_etl_test")
        self.db_path = self.output_dir / "test.db"
        self.raw_tmp = TemporaryDirectory()
        self.raw_dir = Path(self.raw_tmp.name) / "raw"
        write_sample_raw_files(self.raw_dir)

    def tearDown(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.raw_tmp.cleanup()

    def test_run_etl_full_produces_all_outputs(self):
        counts = run_etl(
            raw_dir=str(self.raw_dir),
            output_dir=str(self.output_dir),
            db_path=str(self.db_path),
        )
        self.assertIn("seller_order_fact", counts)
        self.assertIn("seller_metrics", counts)
        self.assertIn("seller_report", counts)
        self.assertIn("seller_anomalies", counts)
        self.assertGreater(counts["seller_order_fact"], 0)
        self.assertGreater(counts["seller_metrics"], 0)
        self.assertGreater(counts["seller_report"], 0)
        metadata = self.output_dir / "run_metadata.json"
        self.assertTrue(metadata.is_file())
        self.assertTrue(json.loads(metadata.read_text())["run_id"])

    def test_failed_refresh_preserves_previous_outputs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        marker = self.output_dir / "previous-valid-output.txt"
        marker.write_text("keep me")
        with patch.object(etl_module, "_run_etl_once", side_effect=ValueError("broken stage")):
            with self.assertRaisesRegex(ValueError, "broken stage"):
                run_etl(
                    raw_dir=str(self.raw_dir),
                    output_dir=str(self.output_dir),
                    db_path=str(self.db_path),
                )
        self.assertEqual(marker.read_text(), "keep me")
        self.assertFalse((self.output_dir.parent / ".sellertrust-refresh.lock").exists())

    def test_concurrent_refresh_is_rejected(self):
        lock_path = self.output_dir.parent / ".sellertrust-refresh.lock"
        lock_path.mkdir(parents=True, exist_ok=True)
        try:
            with self.assertRaisesRegex(RuntimeError, "already in progress"):
                run_etl(
                    raw_dir=str(self.raw_dir),
                    output_dir=str(self.output_dir),
                    db_path=str(self.db_path),
                )
        finally:
            lock_path.rmdir()

    def test_run_etl_skip_sql_skips_db(self):
        counts = run_etl(
            raw_dir=str(self.raw_dir),
            output_dir=str(self.output_dir),
            db_path=str(self.db_path),
            skip_sql=True,
        )
        self.assertNotIn("seller_order_fact_sql", counts)
        self.assertFalse(self.db_path.exists())

    def test_run_etl_skip_anomaly_skips_anomaly_file(self):
        counts = run_etl(
            raw_dir=str(self.raw_dir),
            output_dir=str(self.output_dir),
            db_path=str(self.db_path),
            skip_anomaly=True,
        )
        self.assertNotIn("seller_anomalies", counts)
        self.assertFalse((self.output_dir / "seller_anomalies.csv").exists())

    def test_run_etl_skip_actions_skips_report(self):
        counts = run_etl(
            raw_dir=str(self.raw_dir),
            output_dir=str(self.output_dir),
            db_path=str(self.db_path),
            skip_actions=True,
        )
        self.assertNotIn("seller_report", counts)
        self.assertFalse((self.output_dir / "seller_report.csv").exists())

    def test_run_etl_returns_integer_counts(self):
        counts = run_etl(
            raw_dir=str(self.raw_dir),
            output_dir=str(self.output_dir),
            db_path=str(self.db_path),
        )
        for name, count in counts.items():
            self.assertIsInstance(count, int, f"{name} should be int")

    def test_main_returns_zero_on_success(self):
        result = main.__wrapped__() if hasattr(main, "__wrapped__") else None
        if result is None:
            old_argv = sys.argv
            sys.argv = [
                "etl_pipeline.py",
                "--raw-dir",
                str(self.raw_dir),
                "--output-dir",
                str(self.output_dir),
                "--db-path",
                str(self.db_path),
            ]
            try:
                result = main()
            finally:
                sys.argv = old_argv
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
