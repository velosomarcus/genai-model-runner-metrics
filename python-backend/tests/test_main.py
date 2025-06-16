"""
Unit tests for the GenAI Model Runner Metrics API.

This module contains comprehensive unit tests for all endpoints and functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatRequest, Message, MetricLog, ErrorLog, LlamaCppMetrics
from app.config import get_settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = AsyncMock()
    mock_stream = AsyncMock()
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Test response"
    
    async def mock_stream_iter():
        yield mock_chunk
    
    mock_stream.__aiter__ = mock_stream_iter
    mock_client.chat.completions.create.return_value = mock_stream
    return mock_client


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_basic(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model_info" in data
    
    def test_health_check_with_model_info(self, client):
        """Test health check with model information."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.model = "test-model"
            mock_settings.base_url = "http://test.com"
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["model_info"]["model"] == "test-model"
    
    def test_health_check_llama_model(self, client):
        """Test health check with llama model."""
        with patch("app.main.settings") as mock_settings:
            mock_settings.model = "llama-7b"
            mock_settings.base_url = "http://llama.cpp"
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["model_info"]["modelType"] == "llama.cpp"
            assert "contextWindow" in data["model_info"]


class TestMetricsEndpoints:
    """Test metrics-related endpoints."""
    
    def test_get_metrics(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
    
    def test_get_metrics_summary(self, client):
        """Test metrics summary endpoint."""
        response = client.get("/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = [
            "total_requests", "average_response_time", "tokens_generated",
            "tokens_processed", "active_users", "error_rate"
        ]
        for field in required_fields:
            assert field in data
    
    def test_log_metrics(self, client):
        """Test metrics logging endpoint."""
        metric_log = MetricLog(
            message_id="test-123",
            tokens_in=10,
            tokens_out=20,
            response_time_ms=1500.0,
            first_token_ms=500.0
        )
        
        response = client.post("/metrics/log", json=metric_log.dict())
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_log_llamacpp_metrics(self, client):
        """Test LlamaCpp metrics logging."""
        llamacpp_metrics = LlamaCppMetrics(
            context_size=4096,
            prompt_eval_time=1000.0,
            tokens_per_second=15.5,
            memory_per_token=512.0,
            threads_used=4,
            batch_size=32
        )
        
        response = client.post("/metrics/llamacpp", json=llamacpp_metrics.dict())
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_log_error(self, client):
        """Test error logging endpoint."""
        error_log = ErrorLog(
            error_type="validation_error",
            status_code=400,
            input_length=100,
            timestamp="2023-01-01T00:00:00Z"
        )
        
        response = client.post("/metrics/error", json=error_log.dict())
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestChatEndpoint:
    """Test chat endpoint functionality."""
    
    def test_chat_without_openai_client(self, client):
        """Test chat endpoint when OpenAI client is not initialized."""
        chat_request = ChatRequest(
            message="Hello, world!",
            messages=[]
        )
        
        # Mock openai_client to be None
        with patch("app.main.openai_client", None):
            response = client.post("/chat", json=chat_request.dict())
            assert response.status_code == 500
            assert "OpenAI client not initialized" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chat_with_mock_client(self, client, mock_openai_client):
        """Test chat endpoint with mocked OpenAI client."""
        chat_request = ChatRequest(
            message="Hello, world!",
            messages=[
                Message(role="user", content="Previous message")
            ]
        )
        
        with patch("app.main.openai_client", mock_openai_client):
            response = client.post("/chat", json=chat_request.dict())
            assert response.status_code == 200
    
    def test_chat_markdown_format(self, client):
        """Test chat with markdown format request."""
        chat_request = ChatRequest(
            message="Explain Python in markdown",
            messages=[],
            format="markdown"
        )
        
        with patch("app.main.openai_client") as mock_client:
            mock_stream = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_stream
            
            response = client.post("/chat", json=chat_request.dict())
            # The response should be streaming, so we can't easily test content
            # but we can verify the call was made
            assert mock_client.chat.completions.create.called
    
    def test_chat_token_estimation(self, client):
        """Test token estimation functionality."""
        from app.main import estimate_tokens
        
        test_text = "Hello world, this is a test message"
        tokens = estimate_tokens(test_text)
        assert tokens == len(test_text) // 4
    
    def test_llama_model_detection(self, client):
        """Test llama model detection."""
        from app.main import is_llama_model
        
        assert is_llama_model("llama-7b", "http://test.com") == True
        assert is_llama_model("gpt-4", "http://llama.cpp") == True
        assert is_llama_model("gpt-4", "http://openai.com") == False
    
    def test_context_window_sizing(self, client):
        """Test context window size calculation."""
        from app.main import get_context_window_size
        
        assert get_context_window_size("llama-1B") == 2048
        assert get_context_window_size("llama-7B") == 4096
        assert get_context_window_size("llama-70B") == 8192
        assert get_context_window_size("unknown-model") == 4096


class TestCORSHandling:
    """Test CORS handling."""
    
    def test_options_request(self, client):
        """Test CORS preflight request."""
        response = client.options("/chat")
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert "POST" in response.headers["access-control-allow-methods"]


class TestDataModels:
    """Test Pydantic data models."""
    
    def test_message_model(self):
        """Test Message model validation."""
        message = Message(role="user", content="Hello")
        assert message.role == "user"
        assert message.content == "Hello"
    
    def test_chat_request_model(self):
        """Test ChatRequest model validation."""
        chat_request = ChatRequest(
            message="Hello",
            messages=[Message(role="user", content="Hi")],
            format="markdown"
        )
        assert chat_request.message == "Hello"
        assert len(chat_request.messages) == 1
        assert chat_request.format == "markdown"
    
    def test_chat_request_optional_fields(self):
        """Test ChatRequest with optional fields."""
        chat_request = ChatRequest(message="Hello")
        assert chat_request.messages == []
        assert chat_request.format is None
    
    def test_metric_log_model(self):
        """Test MetricLog model validation."""
        metric_log = MetricLog(
            message_id="test-123",
            tokens_in=10,
            tokens_out=20,
            response_time_ms=1500.0,
            first_token_ms=500.0
        )
        assert metric_log.message_id == "test-123"
        assert metric_log.tokens_in == 10
    
    def test_llamacpp_metrics_model(self):
        """Test LlamaCppMetrics model validation."""
        metrics = LlamaCppMetrics(
            context_size=4096,
            prompt_eval_time=1000.0,
            tokens_per_second=15.5,
            memory_per_token=512.0,
            threads_used=4,
            batch_size=32
        )
        assert metrics.context_size == 4096
        assert metrics.model_type == "llama.cpp"  # Default value


class TestConfiguration:
    """Test configuration management."""
    
    def test_settings_loading(self):
        """Test settings loading from environment."""
        # Clear the cache first
        get_settings.cache_clear()
        
        with patch.dict("os.environ", {
            "BASE_URL": "http://test.com",
            "MODEL": "test-model",
            "API_KEY": "test-key"
        }, clear=False):
            settings = get_settings()
            assert settings.base_url == "http://test.com"
            assert settings.model == "test-model"
            assert settings.api_key == "test-key"
        
        # Clear cache after test
        get_settings.cache_clear()
    
    def test_settings_defaults(self):
        """Test default settings values."""
        get_settings.cache_clear()  # Clear cache
        settings = get_settings()
        assert settings.port == 8080
        assert settings.metrics_port == 9090
        assert settings.tracing_enabled == False
        assert settings.otlp_endpoint == "jaeger:4318"
        get_settings.cache_clear()  # Clear cache after test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])