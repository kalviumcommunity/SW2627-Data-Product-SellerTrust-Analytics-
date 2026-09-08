import logging
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.logging_config import configure_pipeline_logging


class PipelineLoggingTests(unittest.TestCase):
    def test_logging_writes_date_stamped_file_without_stream_handler(self):
        with TemporaryDirectory() as temporary_directory:
            logger = configure_pipeline_logging(temporary_directory, level="DEBUG")
            try:
                logger.debug("debug row count: 3")
                for handler in logger.handlers:
                    handler.flush()

                log_path = Path(temporary_directory) / f"pipeline_{datetime.now():%Y%m%d}.log"
                self.assertTrue(log_path.is_file())
                self.assertIn("debug row count: 3", log_path.read_text(encoding="utf-8"))
                self.assertFalse(any(type(handler) is logging.StreamHandler for handler in logger.handlers))
            finally:
                for handler in logger.handlers[:]:
                    logger.removeHandler(handler)
                    handler.close()

    def test_invalid_log_level_is_rejected(self):
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ValueError):
                configure_pipeline_logging(temporary_directory, level="not-a-level")


if __name__ == "__main__":
    unittest.main()
