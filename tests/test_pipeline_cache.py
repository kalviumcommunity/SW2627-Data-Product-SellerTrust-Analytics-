import shutil
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd

from src.pipeline_cache import load_cached_csv, profile_pipeline, run_pipeline_cached


class LoadCachedCsvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.csv_path = self.tmp / "test.csv"
        self.df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        self.df.to_csv(self.csv_path, index=False)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_load_csv_returns_correct_data(self):
        result = load_cached_csv(self.csv_path, use_parquet_cache=False)
        pd.testing.assert_frame_equal(result, self.df)

    def test_parquet_cache_created(self):
        load_cached_csv(self.csv_path, use_parquet_cache=True)
        parquet_path = self.csv_path.with_suffix(".parquet")
        self.assertTrue(parquet_path.exists())

    def test_parquet_cache_loaded_on_second_call(self):
        load_cached_csv(self.csv_path, use_parquet_cache=True)
        parquet_path = self.csv_path.with_suffix(".parquet")
        mtime = parquet_path.stat().st_mtime
        time.sleep(0.05)
        load_cached_csv(self.csv_path, use_parquet_cache=True)
        self.assertEqual(parquet_path.stat().st_mtime, mtime)

    def test_cache_invalidated_when_csv_newer(self):
        load_cached_csv(self.csv_path, use_parquet_cache=True)
        parquet_path = self.csv_path.with_suffix(".parquet")
        mtime_before = parquet_path.stat().st_mtime
        time.sleep(0.05)
        self.csv_path.touch()
        load_cached_csv(self.csv_path, use_parquet_cache=True)
        self.assertGreater(parquet_path.stat().st_mtime, mtime_before)


class ProfilePipelineTests(unittest.TestCase):
    def test_profile_returns_string(self):
        result = profile_pipeline("data/raw", "tmp_profile_test", top_n=5)
        self.assertIsInstance(result, str)
        self.assertIn("function calls", result)
        shutil.rmtree("tmp_profile_test", ignore_errors=True)


class RunPipelineCachedTests(unittest.TestCase):
    def test_cached_run_returns_same_output(self):
        result1 = run_pipeline_cached("data/raw", "tmp_cached_pipeline")
        result2 = run_pipeline_cached("data/raw", "tmp_cached_pipeline")
        self.assertIs(result1, result2)
        self.assertIn("seller_order_fact", result1)
        self.assertIn("seller_metrics", result1)
        shutil.rmtree("tmp_cached_pipeline", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
