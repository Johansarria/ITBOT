import sys
# HACK: Force pytest to find the installed packages.
# This is needed because of a strange issue with the test environment.
sys.path.append('/home/jules/.pyenv/versions/3.12.11/lib/python3.12/site-packages')

import pytest
import config

@pytest.fixture(autouse=True, scope="function")
def patch_config_for_tests(monkeypatch):
    """
    Automatically patches essential config values for the entire test session
    before any modules are imported.
    """
    monkeypatch.setattr(config, 'TELEGRAM_TOKEN', "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr(config, 'TELEGRAM_CHAT_ID', 12345)
    # The MLflow URI needs to be set for collection, but it's better
    # to handle that in the code itself as previously done. If that fails,
    # we can set an environment variable here.
    # import os
    # monkeypatch.setenv("MLFLOW_TRACKING_URI", "file:./mlruns_test")
