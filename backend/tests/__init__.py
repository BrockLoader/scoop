"""pytest config — asyncio mode."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live: live integration tests against retailer sites")