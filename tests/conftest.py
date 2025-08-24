import sys
import pytest
from config import settings  # Import the settings object
import database.database_manager as db_manager
import redis
import fakeredis
import time

# HACK: Force pytest to find the installed packages.
# This is needed because of a strange issue with the test environment.
sys.path.append('/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages')

@pytest.fixture(autouse=True, scope="function")
def patch_config_for_tests(monkeypatch):
    """
    Automatically patches essential config values for the entire test session.
    """
    # --- Patch Network Services for Local Testing ---
    # When running tests outside Docker, services like DB and Redis are on localhost.
    monkeypatch.setattr(settings, 'POSTGRES_HOST', "localhost")
    monkeypatch.setattr(settings, 'REDIS_HOST', "localhost") # This will be used by the fake client

    # --- Patch Sensitive/Environment-Specific Values ---
    monkeypatch.setattr(settings, 'TELEGRAM_BOT_TOKEN', "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr(settings, 'TELEGRAM_CHAT_ID', 12345)

@pytest.fixture(scope="function")
def in_memory_db(monkeypatch):
    """
    Fixture to set up a clean, in-memory SQLite database for each test.
    It patches the config, initializes the DB, and handles cleanup.
    """
    monkeypatch.setattr(settings, 'DB_TYPE', 'sqlite')
    # Pydantic will automatically see DB_TYPE is sqlite and use an in-memory db
    # No need to set DATABASE_URL directly if the logic in Settings is correct
    # monkeypatch.setattr(settings, 'DATABASE_URL', 'sqlite:///:memory:')
    
    # We must reset the db connection to force re-creation of the engine with the new settings
    db_manager.reset_db_connection()
    db_manager.init_db()

    yield  # The test runs here

    # Teardown: reset the database connection after the test
    db_manager.reset_db_connection()

@pytest.fixture(autouse=True)
def mock_redis_and_sleep(monkeypatch):
    """
    Automatically mocks redis.StrictRedis with fakeredis.FakeStrictRedis
    and time.sleep for all tests to prevent network calls and delays.
    """
    fake_redis_server = fakeredis.FakeServer()
    fake_strict_redis = fakeredis.FakeStrictRedis(server=fake_redis_server, decode_responses=True)

    def mock_strict_redis(*args, **kwargs):
        # The fakeredis instance is already created with decode_responses=True
        # We ignore the kwargs from the original call to ensure compatibility
        return fake_strict_redis

    monkeypatch.setattr(redis, 'StrictRedis', mock_strict_redis)
    monkeypatch.setattr(time, 'sleep', lambda *args, **kwargs: None)

    yield

    # Clear the fake redis database after each test
    fake_strict_redis.flushall()