import pytest
import logging
import json
import io
from unittest.mock import MagicMock, patch

from utils.logger_setup import setup_logging, JsonFormatter, ConsoleFormatter
from utils.structured_logger import StructuredLogger

@pytest.fixture
def setup_test_logging():
    """Fixture to set up and tear down logging for tests."""
    # Redirect console output to a string buffer
    string_io = io.StringIO()

    # Get the root logger and remove existing handlers to ensure a clean slate
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Setup logging with our test handler
    test_console_handler = logging.StreamHandler(string_io)
    test_console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(test_console_handler)

    # Also add a file handler for json tests
    test_file_handler = logging.FileHandler('test_log.log', mode='w')
    test_file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(test_file_handler)

    root_logger.setLevel(logging.INFO)

    yield string_io, 'test_log.log' # Provide the buffer and filename to the test

    # Teardown: remove our test handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Clean up the test log file
    import os
    if os.path.exists('test_log.log'):
        os.remove('test_log.log')

def test_console_formatter(setup_test_logging):
    """Test that the ConsoleFormatter produces colored, readable text."""
    string_io, _ = setup_test_logging

    logger = logging.getLogger("test_console")
    logger.info("This is an info message.")

    output = string_io.getvalue()
    assert "INFO" in output
    assert "This is an info message." in output
    # Check for ANSI color codes
    assert "\x1b[37m" in output # WHITE
    assert "\x1b[0m" in output # RESET

def test_json_formatter(setup_test_logging):
    """Test that the JsonFormatter produces valid JSON."""
    _, log_file = setup_test_logging

    logger = logging.getLogger("test_json")
    test_details = {"user": "test_user", "action": "login"}
    logger.warning("User action.", extra={'details': test_details})

    with open(log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry['level'] == "WARNING"
    assert log_entry['message'] == "User action."
    assert log_entry['name'] == "test_json"
    assert log_entry['user'] == "test_user"
    assert log_entry['action'] == "login"

def test_structured_logger_integration(setup_test_logging):
    """Test that the StructuredLogger works correctly with the formatters."""
    string_io, log_file = setup_test_logging

    s_logger = StructuredLogger("structured_test")
    s_logger.info("TEST_EVENT", "Structured log message.", details={"id": 123})

    # Check console output
    console_output = string_io.getvalue()
    assert "INFO" in console_output
    assert "Structured log message." in console_output

    # Check JSON file output
    with open(log_file, 'r') as f:
        log_entry = json.loads(f.readline())

    assert log_entry['level'] == "INFO"
    assert log_entry['event_type'] == "TEST_EVENT"
    assert log_entry['message'] == "Structured log message."
    assert log_entry['id'] == 123
    assert 'event_id' in log_entry
