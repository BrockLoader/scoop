"""Live integration tests.

These hit the actual retailer sites. They are NOT part of the default
pytest run — invoke explicitly with:

    pytest -m live

Add the marker in this conftest.
"""
import os
import sys

import pytest

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def vcr_env():
    """Skip when SKIP_LIVE=1."""
    if os.environ.get("SKIP_LIVE") == "1":
        pytest.skip("SKIP_LIVE=1")