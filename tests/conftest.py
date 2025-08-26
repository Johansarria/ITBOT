import os

# Set dummy environment variables BEFORE any other imports.
# This is critical to prevent pydantic ValidationErrors during pytest collection,
# as other modules might import the application's settings object.
os.environ['TELEGRAM_BOT_TOKEN'] = '1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
os.environ['TELEGRAM_CHAT_ID'] = '12345'
os.environ['BINANCE_API_KEY'] = 'dummy_api_key_for_tests'
os.environ['BINANCE_SECRET_KEY'] = 'dummy_secret_key_for_tests'
os.environ['DB_TYPE'] = 'sqlite'  # Default to in-memory sqlite for tests

# Now it is safe to import other modules.
import pytest
import time
import redis
import fakeredis
import database.database_manager as db_manager
from config import settings
from unittest.mock import MagicMock



# --- Global Test Setup: Mock external services at import time ---

# Patch redis to use fakeredis for all tests, preventing real network calls.
# This must be done here (globally) and not in a fixture to prevent import-time side effects.
fake_redis_server = fakeredis.FakeServer()
fake_strict_redis = fakeredis.FakeStrictRedis(server=fake_redis_server, decode_responses=True)
redis.StrictRedis = lambda *args, **kwargs: fake_strict_redis

# Patch time.sleep to prevent tests from actually waiting.
time.sleep = lambda *args, **kwargs: None


@pytest.fixture(autouse=True, scope="function")
def test_setup_and_teardown(monkeypatch):
    """
    This fixture runs for every test. It handles:
    1.  Patching essential config values.
    2.  Clearing the fake redis DB after each test.
    """
    # --- Patch Config Values ---
    monkeypatch.setattr(settings, 'POSTGRES_HOST', "localhost")
    monkeypatch.setattr(settings, 'REDIS_HOST', "localhost")
    monkeypatch.setattr(settings, 'TELEGRAM_BOT_TOKEN', "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr(settings, 'TELEGRAM_CHAT_ID', 12345)

    yield # The test runs here

    # --- Teardown ---
    # Clear the fake redis database after each test to ensure isolation
    fake_strict_redis.flushall()


from database.models import Base

@pytest.fixture(scope="function")
def in_memory_db(monkeypatch):
    """
    Fixture to set up a clean, in-memory SQLite database for each test.
    It patches the config, initializes the DB, and handles cleanup by dropping all tables.
    """
    monkeypatch.setattr(settings, 'DB_TYPE', 'sqlite')
    # Pydantic will automatically see DB_TYPE is sqlite and use an in-memory db.
    # We must reset the db connection to force re-creation of the engine with the new settings.
    db_manager.reset_db_connection()
    engine = db_manager.get_engine()
    Base.metadata.create_all(engine) # Use create_all for a clean setup

    yield  # The test runs here

    # Teardown: drop all tables to ensure test isolation
    Base.metadata.drop_all(engine)
    db_manager.reset_db_connection()