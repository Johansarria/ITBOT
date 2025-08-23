import logging
from utils import logger_setup
import os


def test_setup_logging_idempotent(tmp_path):
    old_log_dir = logger_setup.LOG_DIR
    logger_setup.LOG_DIR = str(tmp_path)
    root = logging.getLogger()
    # Save and clear existing handlers to isolate test
    old_handlers = list(root.handlers)
    try:
        for h in list(root.handlers):
            root.removeHandler(h)

        # First call
        logger_setup.setup_logging()
        handlers_after_first = list(root.handlers)
        assert len(handlers_after_first) >= 2  # console + file handlers

        # Second call should not duplicate handlers
        logger_setup.setup_logging()
        handlers_after_second = list(root.handlers)
        assert len(handlers_after_second) == len(handlers_after_first)
    finally:
        # Restore previous handlers
        for h in list(root.handlers):
            root.removeHandler(h)
        for h in old_handlers:
            root.addHandler(h)
        logger_setup.LOG_DIR = old_log_dir
