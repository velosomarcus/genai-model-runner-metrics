"""Test configuration and fixtures."""

import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "BASE_URL": "http://test-api.com/v1",
        "MODEL": "test-model",
        "API_KEY": "test-api-key",
        "TRACING_ENABLED": "false",
        "PORT": "8080",
        "METRICS_PORT": "9090"
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return {
        "message_id": "test-123",
        "tokens_in": 25,
        "tokens_out": 150,
        "response_time_ms": 2500.0,
        "first_token_ms": 800.0
    }