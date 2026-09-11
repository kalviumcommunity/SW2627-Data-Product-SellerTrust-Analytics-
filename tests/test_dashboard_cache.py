import json
import sqlite3
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.cache import dataset_version
from app.ui_state import get_dataset_version


class DashboardCacheTests(unittest.TestCase):
    def test_dataset_version_changes_after_published_file_changes(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "analytics.db"
            conn = sqlite3.connect(path)
            try:
                conn.execute("CREATE TABLE values_table (value TEXT)")
                conn.commit()
            finally:
                conn.close()
            first = dataset_version(path)
            time.sleep(0.001)
            conn = sqlite3.connect(path)
            try:
                conn.execute("INSERT INTO values_table VALUES ('new')")
                conn.commit()
            finally:
                conn.close()
            self.assertNotEqual(first, dataset_version(path))

    def test_dataset_version_label_reads_run_id(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run_metadata.json"
            path.write_text(json.dumps({"run_id": "run-cache-test"}), encoding="utf-8")
            self.assertEqual(get_dataset_version(path), "Dataset version: run-cache-test")


if __name__ == "__main__":
    unittest.main()
