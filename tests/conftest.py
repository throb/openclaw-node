"""Pytest configuration and fixtures."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test token
os.environ["OPENCLAW_NODE_TOKEN"] = "test-token-12345"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def auth_token():
    """Test auth token."""
    return "test-token-12345"


@pytest.fixture
def sample_node_info():
    """Sample node registration data."""
    return {
        "node_id": "test-node",
        "plugins": ["explorer", "rv"],
        "platform": "linux",
    }
